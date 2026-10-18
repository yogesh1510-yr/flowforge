"""Project Debezium order events into the shared PostgreSQL order-state table."""

import os

import psycopg
from pyspark.sql import SparkSession

from flowforge.analytics.order_projection import transform_order_event
from flowforge.analytics.order_projection_writer import upsert_order

KAFKA = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "flowforge.public.orders")
CHECKPOINT = os.getenv(
    "ORDER_PROJECTION_CHECKPOINT",
    "/opt/spark-data/checkpoints/order-projection",
)

DB_HOST = os.getenv("SINK_DB_HOST", "postgres")
DB_PORT = os.getenv("SINK_DB_PORT", "5432")
DB_NAME = os.getenv("SINK_DB_NAME", "flowforge")
DB_USER = os.getenv("SINK_DB_USER", "flowforge")
DB_PASSWORD = os.getenv("SINK_DB_PASSWORD", "flowforge_dev_only")

# The target is fixed to analytics.order_state by the projection writer SQL.
DB_DSN = (
    f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
    f"user={DB_USER} password={DB_PASSWORD}"
)

spark = SparkSession.builder.appName("FlowForgeOrderProjectionTest").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

kafka_stream = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", KAFKA)
    .option("subscribe", TOPIC)
    .option("startingOffsets", "earliest")
    .load()
)

events = kafka_stream.selectExpr(
    "topic",
    "partition AS kafka_partition",
    "offset AS kafka_offset",
    "CAST(value AS STRING) AS raw_json",
)


def write_projection_batch(batch_df, batch_id):
    """Transform and transactionally apply one Spark micro-batch."""
    if not batch_df.take(1):
        return

    processed = 0
    ignored = 0

    # The batch transaction commits only after every supported event succeeds.
    # If processing fails, psycopg rolls back the batch and Spark can retry it.
    with psycopg.connect(DB_DSN) as connection:
        for row in batch_df.toLocalIterator():
            record = transform_order_event(
                row["raw_json"],
                topic=row["topic"],
                partition=row["kafka_partition"],
                offset=row["kafka_offset"],
            )

            if record is None:
                ignored += 1
                continue

            upsert_order(connection, record)
            processed += 1

    print(
        f"Projection batch {batch_id} committed: "
        f"{processed} order events applied; {ignored} ignored."
    )


query = (
    events.writeStream.foreachBatch(write_projection_batch)
    .option("checkpointLocation", CHECKPOINT)
    .trigger(processingTime="10 seconds")
    .start()
)

print(
    f"Projecting {TOPIC} into analytics.order_state. "
    f"Checkpoint: {CHECKPOINT}. Press Ctrl+C to stop."
)
query.awaitTermination()
