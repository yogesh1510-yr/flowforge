"""Consume Debezium CDC events and route malformed messages to a DLQ."""

import base64
import json
import logging
import os
import signal

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from kafka.structs import OffsetAndMetadata, TopicPartition

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("flowforge.streaming.consumer")

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = os.getenv("KAFKA_TOPIC", "flowforge.public.orders")
DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", "flowforge.dlq.orders")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "flowforge-order-consumer")
DLQ_ACK_TIMEOUT_SECONDS = 10

STOP = False


def request_stop(signum, frame):
    """Request graceful shutdown."""
    global STOP
    STOP = True


def describe_event(raw_message):
    """Extract useful fields from a Debezium event."""
    if not isinstance(raw_message, dict):
        raise ValueError("CDC event must be a JSON object")

    payload = raw_message.get("payload", raw_message)
    if not isinstance(payload, dict):
        raise ValueError("CDC payload must be a JSON object")

    source = payload.get("source") or {}
    before = payload.get("before") or {}
    after = payload.get("after") or {}

    if not all(isinstance(value, dict) for value in (source, before, after)):
        raise ValueError("CDC source, before, and after must be JSON objects")

    return {
        "operation": payload.get("op"),
        "table": source.get("table"),
        "database": source.get("db"),
        "order_number": (after or before).get("order_number"),
        "status_before": before.get("status"),
        "status_after": after.get("status"),
    }


def commit_message(consumer, message):
    """Commit the next offset only after the message has been handled."""
    partition = TopicPartition(message.topic, message.partition)
    consumer.commit({partition: OffsetAndMetadata(message.offset + 1, "", -1)})


def publish_to_dlq(producer, message, error):
    """Publish a recoverable copy of a malformed message and await its acknowledgement."""
    dead_letter = {
        "original_topic": message.topic,
        "original_partition": message.partition,
        "original_offset": message.offset,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "key_base64": (
            base64.b64encode(message.key).decode("ascii")
            if message.key is not None
            else None
        ),
        "value_base64": (
            base64.b64encode(message.value).decode("ascii")
            if message.value is not None
            else None
        ),
    }

    # .get() waits for Kafka's delivery result. An exception means we must
    # not commit the source offset.
    producer.send(DLQ_TOPIC, value=dead_letter).get(timeout=DLQ_ACK_TIMEOUT_SECONDS)

    logger.warning(
        "Published malformed CDC message to DLQ topic=%s "
        "source_topic=%s partition=%s offset=%s error=%s",
        DLQ_TOPIC,
        message.topic,
        message.partition,
        message.offset,
        type(error).__name__,
    )


def main():
    """Consume CDC events, route malformed messages, and commit safe offsets."""
    global STOP
    STOP = False

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    consumer = None
    producer = None

    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS.split(","),
            group_id=GROUP_ID,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda value: value,
            key_deserializer=lambda value: value,
            consumer_timeout_ms=1000,
        )

        producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            acks="all",
            enable_idempotence=True,
        )

        logger.info(
            "Listening on topic=%s bootstrap_servers=%s group_id=%s dlq_topic=%s",
            TOPIC,
            BOOTSTRAP_SERVERS,
            GROUP_ID,
            DLQ_TOPIC,
        )

        while not STOP:
            for message in consumer:
                if STOP:
                    break

                try:
                    raw_event = json.loads(message.value.decode("utf-8"))
                    event_key = (
                        json.loads(message.key.decode("utf-8"))
                        if message.key is not None
                        else None
                    )
                    event = describe_event(raw_event)

                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                    TypeError,
                    ValueError,
                    AttributeError,
                ) as exc:
                    # A bad record must reach the DLQ before its source
                    # offset can be committed. If publishing fails, the
                    # exception propagates and the source offset stays uncommitted.
                    publish_to_dlq(producer, message, exc)
                    commit_message(consumer, message)
                    continue

                logger.info(
                    "CDC topic=%s partition=%s offset=%s key=%s event=%s",
                    message.topic,
                    message.partition,
                    message.offset,
                    event_key,
                    json.dumps(event, default=str),
                )

                # This consumer's current processing is parsing and logging,
                # not durable business processing.
                commit_message(consumer, message)

    except KafkaError:
        logger.exception("Kafka consumer encountered a Kafka error")
        raise

    finally:
        if consumer is not None:
            consumer.close()
        if producer is not None:
            producer.close()
        logger.info("Kafka consumer stopped")


if __name__ == "__main__":
    main()
