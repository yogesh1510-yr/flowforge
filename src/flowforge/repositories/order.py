from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from flowforge.models import Order, OrderEvent, OrderItem


def get_order_by_id(
    session: Session,
    order_id: UUID,
) -> Order | None:
    statement = (
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    return session.scalar(statement)


def get_order_by_number(
    session: Session,
    order_number: str,
) -> Order | None:
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    return session.scalar(statement)


def list_orders(
    session: Session,
    *,
    customer_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Order]:
    statement = select(Order).options(selectinload(Order.items))

    if customer_id is not None:
        statement = statement.where(Order.customer_id == customer_id)

    statement = (
        statement.order_by(Order.created_at.desc(), Order.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())


def create_order(
    session: Session,
    *,
    order_number: str,
    customer_id: UUID,
    currency: str,
    subtotal,
    tax_amount,
    shipping_amount,
    discount_amount,
    total_amount,
    shipping_address_snapshot: dict,
    items: list[dict],
) -> Order:
    order = Order(
        order_number=order_number,
        customer_id=customer_id,
        currency=currency,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        shipping_address_snapshot=shipping_address_snapshot,
    )
    session.add(order)
    session.flush()

    for item in items:
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                sku_snapshot=item["sku_snapshot"],
                product_name_snapshot=item["product_name_snapshot"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                line_total=item["line_total"],
            )
        )

    session.flush()
    return order


def create_order_event(
    session: Session,
    *,
    order_id: UUID,
    event_type: str,
    payload: dict,
    occurred_at,
) -> OrderEvent:
    event = OrderEvent(
        order_id=order_id,
        event_type=event_type,
        event_version=1,
        payload=payload,
        occurred_at=occurred_at,
    )
    session.add(event)
    session.flush()
    return event


def list_order_events(
    session: Session,
    *,
    order_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[OrderEvent]:
    statement = (
        select(OrderEvent)
        .where(OrderEvent.order_id == order_id)
        .order_by(OrderEvent.occurred_at, OrderEvent.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())
