"""Transactional integration tests for the isolated PostgreSQL order projection."""

import os
from uuid import uuid4

import psycopg
import pytest

from flowforge.analytics.order_projection_writer import upsert_order


@pytest.fixture
def db_connection():
    dsn = os.getenv("FLOWFORGE_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip(
            "Set FLOWFORGE_TEST_DATABASE_URL to run PostgreSQL integration tests"
        )

    connection = psycopg.connect(dsn)
    connection.autocommit = False

    try:
        # Ensure all test writes are rolled back, even if an assertion fails.
        yield connection
    finally:
        connection.rollback()
        connection.close()


def make_record(order_id, *, status, lsn, offset, deleted=False):
    from datetime import datetime, timezone
    from decimal import Decimal

    now = datetime.now(timezone.utc)

    return {
        "order_id": order_id,
        "order_number": f"IT-{str(order_id)[:8]}",
        "customer_id": uuid4(),
        "status": status,
        "currency": "INR",
        "subtotal": Decimal("100.00"),
        "tax_amount": Decimal("18.00"),
        "shipping_amount": Decimal("10.00"),
        "discount_amount": Decimal("0.00"),
        "total_amount": Decimal("128.00"),
        "created_at": now,
        "updated_at": now,
        "source_lsn": lsn,
        "source_txid": 900001,
        "source_topic": "flowforge.test.orders",
        "source_partition": 0,
        "source_offset": offset,
        "is_deleted": deleted,
    }


def read_order(connection, order_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT status, source_lsn, source_offset, is_deleted
            FROM analytics.order_state_test
            WHERE order_id = %s
            """,
            (order_id,),
        )
        return cursor.fetchone()


def test_insert_update_duplicate_stale_and_soft_delete(db_connection):
    order_id = uuid4()

    # 1. Initial insert
    initial = make_record(order_id, status="pending", lsn=100, offset=1)
    upsert_order(db_connection, initial)
    assert read_order(db_connection, order_id) == ("pending", 100, 1, False)

    # 2. Newer source LSN updates the projection
    newer = make_record(order_id, status="confirmed", lsn=200, offset=2)
    upsert_order(db_connection, newer)
    assert read_order(db_connection, order_id) == ("confirmed", 200, 2, False)

    # 3. Replaying the same event must not change the state
    upsert_order(db_connection, newer)
    assert read_order(db_connection, order_id) == ("confirmed", 200, 2, False)

    # 4. An older event must not overwrite newer state
    stale = make_record(order_id, status="pending", lsn=150, offset=3)
    upsert_order(db_connection, stale)
    assert read_order(db_connection, order_id) == ("confirmed", 200, 2, False)

    # 5. A newer delete is represented as a soft delete
    deleted = make_record(order_id, status="confirmed", lsn=300, offset=4, deleted=True)
    upsert_order(db_connection, deleted)
    assert read_order(db_connection, order_id) == ("confirmed", 300, 4, True)


def test_equal_lsn_uses_offset_only_for_same_topic_and_partition(db_connection):
    order_id = uuid4()

    initial = make_record(order_id, status="pending", lsn=500, offset=10)
    upsert_order(db_connection, initial)

    # Same LSN and same Kafka partition: later offset may advance the state.
    later = make_record(order_id, status="confirmed", lsn=500, offset=11)
    upsert_order(db_connection, later)
    assert read_order(db_connection, order_id) == ("confirmed", 500, 11, False)

    # Same LSN but a different partition: ordering is ambiguous, so reject it.
    conflicting = make_record(order_id, status="pending", lsn=500, offset=99)
    conflicting["source_partition"] = 1
    upsert_order(db_connection, conflicting)

    assert read_order(db_connection, order_id) == ("confirmed", 500, 11, False)


def test_older_snapshot_cannot_overwrite_newer_update(db_connection):
    order_id = uuid4()

    # A newer streaming update has already reached the projection.
    update = make_record(order_id, status="confirmed", lsn=600, offset=20)
    upsert_order(db_connection, update)

    # A snapshot record with an older LSN must not replace it.
    snapshot = make_record(order_id, status="pending", lsn=500, offset=21)
    upsert_order(db_connection, snapshot)

    assert read_order(db_connection, order_id) == ("confirmed", 600, 20, False)
