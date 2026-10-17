import json
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from kafka.structs import TopicPartition

from flowforge.streaming.consumer import describe_event, main


def test_describe_order_creation_event():
    event = {
        "payload": {
            "op": "c",
            "source": {"db": "flowforge", "table": "orders"},
            "before": None,
            "after": {
                "order_number": "FF-TEST-001",
                "status": "pending",
            },
        }
    }

    result = describe_event(event)

    assert result["operation"] == "c"
    assert result["table"] == "orders"
    assert result["database"] == "flowforge"
    assert result["order_number"] == "FF-TEST-001"
    assert result["status_before"] is None
    assert result["status_after"] == "pending"


def test_describe_order_update_event():
    event = {
        "payload": {
            "op": "u",
            "source": {"db": "flowforge", "table": "orders"},
            "before": {
                "order_number": "FF-TEST-002",
                "status": "pending",
            },
            "after": {
                "order_number": "FF-TEST-002",
                "status": "confirmed",
            },
        }
    }

    result = describe_event(event)

    assert result["operation"] == "u"
    assert result["order_number"] == "FF-TEST-002"
    assert result["status_before"] == "pending"
    assert result["status_after"] == "confirmed"


def test_describe_order_delete_event():
    event = {
        "payload": {
            "op": "d",
            "source": {"db": "flowforge", "table": "orders"},
            "before": {
                "order_number": "FF-TEST-003",
                "status": "cancelled",
            },
            "after": None,
        }
    }

    result = describe_event(event)

    assert result["operation"] == "d"
    assert result["order_number"] == "FF-TEST-003"
    assert result["status_before"] == "cancelled"
    assert result["status_after"] is None


def test_describe_unwrapped_debezium_event():
    event = {
        "op": "r",
        "source": {"db": "flowforge", "table": "orders"},
        "before": None,
        "after": {
            "order_number": "FF-TEST-004",
            "status": "shipped",
        },
    }

    result = describe_event(event)

    assert result["operation"] == "r"
    assert result["order_number"] == "FF-TEST-004"
    assert result["status_after"] == "shipped"


@patch("flowforge.streaming.consumer.signal.signal")
@patch("flowforge.streaming.consumer.KafkaConsumer")
@patch("flowforge.streaming.consumer.KafkaProducer")
def test_consumer_sends_malformed_message_to_dlq_before_commit(
    mock_producer_class,
    mock_consumer_class,
    mock_signal,
):
    message = SimpleNamespace(
        topic="flowforge.public.orders",
        partition=0,
        offset=12,
        key=b'{"order_number":"FF-TEST-BAD"}',
        value=b'{"payload": invalid-json',
    )

    mock_consumer = MagicMock()
    mock_consumer.__iter__.return_value = iter([message])
    mock_consumer_class.return_value = mock_consumer

    mock_producer = MagicMock()
    mock_producer_class.return_value = mock_producer

    def commit_and_stop(offsets):
        from flowforge.streaming import consumer as consumer_module

        consumer_module.STOP = True

    mock_consumer.commit.side_effect = commit_and_stop

    try:
        with patch("flowforge.streaming.consumer.STOP", False):
            main()
    finally:
        from flowforge.streaming import consumer as consumer_module

        consumer_module.STOP = False

    mock_producer.send.assert_called_once()
    assert mock_producer.send.call_args.args[0] == "flowforge.dlq.orders"
    mock_producer.send.return_value.get.assert_called_once_with(timeout=10)

    mock_consumer.commit.assert_called_once()
    committed_offsets = mock_consumer.commit.call_args.args[0]
    partition = TopicPartition("flowforge.public.orders", 0)
    assert committed_offsets[partition].offset == 13

    mock_consumer.close.assert_called_once()
    mock_producer.close.assert_called_once()


@patch("flowforge.streaming.consumer.signal.signal")
@patch("flowforge.streaming.consumer.KafkaConsumer")
@patch("flowforge.streaming.consumer.KafkaProducer")
def test_consumer_does_not_commit_when_dlq_publish_fails(
    mock_producer_class,
    mock_consumer_class,
    mock_signal,
):
    message = SimpleNamespace(
        topic="flowforge.public.orders",
        partition=0,
        offset=15,
        key=None,
        value=b'{"payload": invalid-json',
    )

    mock_consumer = MagicMock()
    mock_consumer.__iter__.return_value = iter([message])
    mock_consumer_class.return_value = mock_consumer

    mock_producer = MagicMock()
    mock_producer.send.return_value.get.side_effect = RuntimeError(
        "DLQ delivery failed"
    )
    mock_producer_class.return_value = mock_producer

    try:
        with patch("flowforge.streaming.consumer.STOP", False):
            with pytest.raises(RuntimeError, match="DLQ delivery failed"):
                main()
    finally:
        from flowforge.streaming import consumer as consumer_module

        consumer_module.STOP = False

    mock_consumer.commit.assert_not_called()
    mock_consumer.close.assert_called_once()
    mock_producer.close.assert_called_once()


