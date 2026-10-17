from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

GET_BY_ID_SQL = text("""
    SELECT
        order_id,
        order_number,
        customer_id,
        status,
        currency,
        subtotal,
        tax_amount,
        shipping_amount,
        discount_amount,
        total_amount,
        created_at,
        updated_at,
        order_age_seconds,
        source_topic,
        source_partition,
        source_offset,
        projected_at
    FROM analytics.order_intelligence_test
    WHERE order_id = :order_id
""")


GET_BY_NUMBER_SQL = text("""
    SELECT
        order_id,
        order_number,
        customer_id,
        status,
        currency,
        subtotal,
        tax_amount,
        shipping_amount,
        discount_amount,
        total_amount,
        created_at,
        updated_at,
        order_age_seconds,
        source_topic,
        source_partition,
        source_offset,
        projected_at
    FROM analytics.order_intelligence_test
    WHERE order_number = :order_number
""")


def get_by_id(session: Session, order_id: UUID):
    return (
        session.execute(GET_BY_ID_SQL, {"order_id": order_id}).mappings().one_or_none()
    )


def get_by_number(session: Session, order_number: str):
    return (
        session.execute(GET_BY_NUMBER_SQL, {"order_number": order_number})
        .mappings()
        .one_or_none()
    )


def list_orders(
    session: Session,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    order_number: str | None = None,
):
    conditions = []
    params = {
        "limit": limit,
        "offset": offset,
    }

    if status is not None:
        conditions.append("status = :status")
        params["status"] = status

    if order_number is not None:
        conditions.append("order_number ILIKE :order_number")
        params["order_number"] = f"%{order_number}%"

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = text(f"""
        SELECT
            order_id,
            order_number,
            customer_id,
            status,
            currency,
            subtotal,
            tax_amount,
            shipping_amount,
            discount_amount,
            total_amount,
            created_at,
            updated_at,
            order_age_seconds,
            source_topic,
            source_partition,
            source_offset,
            projected_at
        FROM analytics.order_intelligence_test
        {where_clause}
        ORDER BY updated_at DESC, order_number ASC
        LIMIT :limit OFFSET :offset
    """)

    return session.execute(query, params).mappings().all()


SUMMARY_TOTALS_SQL = text("""
    SELECT
        COUNT(*) AS total_orders,
        MAX(projected_at) AS latest_projection_at,
        MAX(updated_at) AS latest_order_updated_at
    FROM analytics.order_intelligence_test
""")

SUMMARY_STATUS_SQL = text("""
    SELECT status, COUNT(*) AS order_count
    FROM analytics.order_intelligence_test
    GROUP BY status
    ORDER BY status
""")

SUMMARY_CURRENCY_SQL = text("""
    SELECT currency, SUM(total_amount) AS total_value
    FROM analytics.order_intelligence_test
    GROUP BY currency
    ORDER BY currency
""")


def get_summary(session: Session) -> dict:
    totals = session.execute(SUMMARY_TOTALS_SQL).mappings().one()

    statuses = session.execute(SUMMARY_STATUS_SQL).mappings().all()
    currencies = session.execute(SUMMARY_CURRENCY_SQL).mappings().all()

    return {
        "total_orders": totals["total_orders"],
        "orders_by_status": {row["status"]: row["order_count"] for row in statuses},
        "total_value_by_currency": {
            row["currency"]: row["total_value"] for row in currencies
        },
        "latest_projection_at": totals["latest_projection_at"],
        "latest_order_updated_at": totals["latest_order_updated_at"],
    }
