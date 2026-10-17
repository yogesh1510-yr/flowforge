
"""Read Debezium CDC messages from Kafka and persist raw events to PostgreSQL."""

import os
import re

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    coalesce,
    col,
    current_timestamp,
    get_json_object,
)

KAFKA = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "flowforge.public.orders")
CHECKPOINT = os.getenv(
    "SPARK_CHECKPOINT",
    "/tmp/flowforge-spark-checkpoints/orders",
)

DB_HOST = os.getenv("SINK_DB_HOST", "postgres")
DB_PORT = os.getenv("SINK_DB_PORT", "5432")
DB_NAME = os.getenv("SINK_DB_NAME", "flowforge")
DB_USER = os.getenv("SINK_DB_USER", "flowforge")
DB_PASSWORD = os.getenv("SINK_DB_PASSWORD", "flowforge_dev_only")

TARGET_TABLE = os.getenv(
    "SINK_TABLE",
    "analytics.raw_order_cdc_events",
)
STAGING_TABLE = os.getenv(
    "SINK_STAGING_TABLE",
    "analytics.raw_order_cdc_events_staging",
)

ALLOWED_TARGETS = {
    "analytics.raw_order_cdc_events",
    "analytics.raw_test_cdc_events",
}
ALLOWED_STAGING_TABLES = {
    "analytics.raw_order_cdc_events_staging",
    "analytics.raw_test_cdc_events_staging",
}

# Validate table identifiers before inserting them into SQL.
if TARGET_TABLE not in ALLOWED_TARGETS:
    raise ValueError(f"Unsupported sink table: {TARGET_TABLE}")

if STAGING_TABLE not in ALLOWED_STAGING_TABLES:
    raise ValueError(f"Unsupported staging table: {STAGING_TABLE}")

if TARGET_TABLE == "analytics.raw_order_cdc_events" and (
    STAGING_TABLE != "analytics.raw_order_cdc_events_staging"
):
    raise ValueError("Production sink requires its matching staging table")

if TARGET_TABLE == "analytics.raw_test_cdc_events" and (
    STAGING_TABLE != "analytics.raw_test_cdc_events_staging"
):
    raise ValueError("Test sink requires its matching staging table")

spark = SparkSession.builder.appName("FlowForgeCDCStreaming").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# Read CDC records from Kafka continuously.
kafka_stream = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", KAFKA)
    .option("subscribe", TOPIC)
    .option("startingOffsets", "earliest")
    .load()
)

raw = kafka_stream.selectExpr(
    "topic",
    "partition AS kafka_partition",
    "offset AS kafka_offset",
    "CAST(key AS STRING) AS kafka_key",
    "CAST(value AS STRING) AS raw_json",
    "timestamp AS kafka_timestamp",
)

# Support direct Debezium envelopes and envelopes nested under "payload".
events = raw.select(
    col("topic"),
    col("kafka_partition"),
    col("kafka_offset"),
    col("kafka_key"),
    col("raw_json"),
    coalesce(
        get_json_object("raw_json", "$.payload.op"),
        get_json_object("raw_json", "$.op"),
    ).alias("operation"),
    coalesce(
        get_json_object("raw_json", "$.payload.source.table"),
        get_json_object("raw_json", "$.source.table"),
    ).alias("source_table"),
    coalesce(
        get_json_object("raw_json", "$.payload.ts_ms"),
        get_json_object("raw_json", "$.ts_ms"),
    )
    .cast("long")
    .alias("source_ts_ms"),
    col("kafka_timestamp"),
    current_timestamp().alias("ingested_at"),
)

jdbc_url = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"


def write_batch(batch_df, batch_id):
    if batch_df.isEmpty():
        return

    record_count = batch_df.count()
    print(
        f"Writing Spark batch {batch_id}: {record_count} records "
        f"to {TARGET_TABLE}"
    )

    # Step 1: Append the batch to its configured staging table.
    (
        batch_df.write.format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", STAGING_TABLE)
        .option("user", DB_USER)
        .option("password", DB_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .mode("append")
        .save()
    )

    # Step 2: Obtain the JDBC driver and create a database connection.
    jvm = spark.sparkContext._jvm
    thread = jvm.java.lang.Thread.currentThread()
    class_loader = thread.getContextClassLoader()
    driver_class = class_loader.loadClass("org.postgresql.Driver")
    driver = driver_class.newInstance()

    properties = jvm.java.util.Properties()
    properties.setProperty("user", DB_USER)
    properties.setProperty("password", DB_PASSWORD)

    connection = driver.connect(jdbc_url, properties)

    if connection is None:
        raise RuntimeError("PostgreSQL JDBC driver rejected the sink URL")

    statement = None

    try:
        connection.setAutoCommit(False)
        statement = connection.createStatement()

        # Step 3: Merge idempotently into the configured target.
        merge_sql = f"""
            INSERT INTO {TARGET_TABLE} (
                topic,
                kafka_partition,
                kafka_offset,
                kafka_key,
                raw_json,
                operation,
                source_table,
                source_ts_ms,
                kafka_timestamp,
                ingested_at
            )
            SELECT
                topic,
                kafka_partition,
                kafka_offset,
                kafka_key,
                raw_json,
                operation,
                source_table,
                source_ts_ms,
                kafka_timestamp,
                ingested_at
            FROM {STAGING_TABLE}
            ON CONFLICT (topic, kafka_partition, kafka_offset)
            DO NOTHING
        """

        statement.executeUpdate(merge_sql)
        statement.executeUpdate(f"TRUNCATE TABLE {STAGING_TABLE}")
        connection.commit()

        print(
            f"Merged Spark batch {batch_id} successfully "
            f"into {TARGET_TABLE}."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        if statement is not None:
            statement.close()
        connection.close()


query = (
    events.writeStream.foreachBatch(write_batch)
    .option("checkpointLocation", CHECKPOINT)
    .trigger(processingTime="10 seconds")
    .start()
)

print(f"Streaming from {TOPIC}. Press Ctrl+C to stop.")
query.awaitTermination()
