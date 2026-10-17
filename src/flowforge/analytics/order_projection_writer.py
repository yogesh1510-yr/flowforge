"""PostgreSQL writer for the isolated order-state projection."""

from typing import Any

UPSERT_SQL = """
INSERT INTO analytics.order_state_test (
    order_id, order_number, customer_id, status, currency,
    subtotal, tax_amount, shipping_amount, discount_amount, total_amount,
    created_at, updated_at, source_lsn, source_txid,
    source_topic, source_partition, source_offset, is_deleted, projected_at
)
VALUES (
    %(order_id)s, %(order_number)s, %(customer_id)s, %(status)s, %(currency)s,
    %(subtotal)s, %(tax_amount)s, %(shipping_amount)s,
    %(discount_amount)s, %(total_amount)s,
    %(created_at)s, %(updated_at)s, %(source_lsn)s, %(source_txid)s,
    %(source_topic)s, %(source_partition)s, %(source_offset)s,
    %(is_deleted)s, now()
)
ON CONFLICT (order_id) DO UPDATE SET
    order_number = EXCLUDED.order_number,
    customer_id = EXCLUDED.customer_id,
    status = EXCLUDED.status,
    currency = EXCLUDED.currency,
    subtotal = EXCLUDED.subtotal,
    tax_amount = EXCLUDED.tax_amount,
    shipping_amount = EXCLUDED.shipping_amount,
    discount_amount = EXCLUDED.discount_amount,
    total_amount = EXCLUDED.total_amount,
    created_at = EXCLUDED.created_at,
    updated_at = EXCLUDED.updated_at,
    source_lsn = EXCLUDED.source_lsn,
    source_txid = EXCLUDED.source_txid,
    source_topic = EXCLUDED.source_topic,
    source_partition = EXCLUDED.source_partition,
    source_offset = EXCLUDED.source_offset,
    is_deleted = EXCLUDED.is_deleted,
    projected_at = now()
WHERE
    analytics.order_state_test.source_lsn IS NOT NULL
    AND EXCLUDED.source_lsn IS NOT NULL
    AND (
        EXCLUDED.source_lsn >
            analytics.order_state_test.source_lsn
        OR (
            EXCLUDED.source_lsn =
                analytics.order_state_test.source_lsn
            AND EXCLUDED.source_topic =
                analytics.order_state_test.source_topic
            AND EXCLUDED.source_partition =
                analytics.order_state_test.source_partition
            AND EXCLUDED.source_offset >
                analytics.order_state_test.source_offset
        )
    )
"""


def _validate_order_record(record: dict) -> None:
    """Reject records without trustworthy source ordering metadata."""
    if not isinstance(record, dict):
        raise ValueError("Order record must be a dictionary")

    for field in ("source_lsn", "source_partition", "source_offset"):
        value = record.get(field)

        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field} must be an integer")

        if value < 0:
            raise ValueError(f"{field} cannot be negative")

    topic = record.get("source_topic")
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("source_topic must be a non-empty string")

    if record.get("is_deleted") not in (True, False):
        raise ValueError("is_deleted must be a boolean")


def upsert_order(connection: Any, record: dict) -> None:
    """
    Upsert one transformed order using the caller's transaction.

    A higher source LSN takes precedence. For events with the same LSN,
    Kafka offset is used only when topic and partition also match.

    This function does not commit or roll back the caller's transaction.
    """
    _validate_order_record(record)

    with connection.cursor() as cursor:
        cursor.execute(UPSERT_SQL, record)
