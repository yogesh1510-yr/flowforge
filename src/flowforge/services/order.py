from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from flowforge.core.enums import CustomerStatus, OrderStatus, ProductStatus
from flowforge.models import Order
from flowforge.repositories import customer as customer_repository
from flowforge.repositories import order as order_repository
from flowforge.repositories import product as product_repository

CENT = Decimal("0.01")


class OrderNotFoundError(Exception):
    pass


class OrderValidationError(Exception):
    pass


class InvalidOrderTransitionError(Exception):
    pass


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def get_order(session: Session, order_id: UUID) -> Order | None:
    return order_repository.get_order_by_id(session, order_id)


def list_orders(
    session: Session,
    *,
    customer_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Order]:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("Offset must be non-negative")

    return order_repository.list_orders(
        session,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )


def create_order(
    session: Session,
    *,
    customer_id: UUID,
    currency: str,
    shipping_address_snapshot: dict[str, str],
    items: list[dict],
    tax_amount: Decimal = Decimal("0"),
    shipping_amount: Decimal = Decimal("0"),
    discount_amount: Decimal = Decimal("0"),
) -> Order:
    if not items:
        raise OrderValidationError("An order must contain at least one item")

    customer = customer_repository.get_customer_by_id(session, customer_id)
    if customer is None or customer.status != CustomerStatus.ACTIVE:
        raise OrderValidationError("Active customer not found")

    currency = currency.upper()
    prepared_items: list[dict] = []
    subtotal = Decimal("0")

    for item in items:
        quantity = item["quantity"]
        if quantity <= 0:
            raise OrderValidationError("Item quantity must be positive")

        product = product_repository.get_product_by_id(
            session,
            item["product_id"],
        )
        if product is None or product.status != ProductStatus.ACTIVE:
            raise OrderValidationError("Active product not found")

        if product.currency != currency:
            raise OrderValidationError("All products must use the order currency")

        unit_price = _money(Decimal(product.current_price))
        line_total = _money(unit_price * quantity)
        subtotal += line_total

        prepared_items.append(
            {
                "product_id": product.id,
                "sku_snapshot": product.sku,
                "product_name_snapshot": product.name,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    subtotal = _money(subtotal)
    tax_amount = _money(tax_amount)
    shipping_amount = _money(shipping_amount)
    discount_amount = _money(discount_amount)

    if min(tax_amount, shipping_amount, discount_amount) < 0:
        raise OrderValidationError("Order amounts cannot be negative")
    if discount_amount > subtotal + tax_amount + shipping_amount:
        raise OrderValidationError("Discount exceeds order charges")

    total_amount = _money(subtotal + tax_amount + shipping_amount - discount_amount)
    order_number = f"FF-{uuid4().hex[:16].upper()}"
    occurred_at = datetime.now(timezone.utc)

    try:
        order = order_repository.create_order(
            session,
            order_number=order_number,
            customer_id=customer_id,
            currency=currency,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            shipping_address_snapshot=shipping_address_snapshot,
            items=prepared_items,
        )

        order_repository.create_order_event(
            session,
            order_id=order.id,
            event_type="order.created",
            payload={
                "order_number": order_number,
                "status": OrderStatus.PENDING.value,
                "item_count": len(prepared_items),
                "total_amount": str(total_amount),
                "currency": currency,
            },
            occurred_at=occurred_at,
        )

        session.commit()
        return order_repository.get_order_by_id(session, order.id) or order

    except IntegrityError:
        session.rollback()
        raise


_ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING: set(),
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING},
    OrderStatus.PROCESSING: set(),
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def update_order_status(
    session: Session,
    order_id: UUID,
    new_status: OrderStatus,
) -> Order:
    try:
        order = order_repository.get_order_by_id(session, order_id)

        if order is None:
            raise OrderNotFoundError(str(order_id))

        # Normalize database values to enums before comparing.
        current_status = OrderStatus(order.status)
        target_status = OrderStatus(new_status)

        allowed_statuses = _ALLOWED_TRANSITIONS.get(current_status, set())

        if target_status not in allowed_statuses:
            raise InvalidOrderTransitionError(
                f"Cannot transition from {current_status.value} "
                f"to {target_status.value}"
            )

        occurred_at = datetime.now(timezone.utc)

        order.status = target_status

        order_repository.create_order_event(
            session,
            order_id=order.id,
            event_type="order.status_changed",
            payload={
                "from_status": current_status.value,
                "to_status": target_status.value,
            },
            occurred_at=occurred_at,
        )

        session.commit()

        return order_repository.get_order_by_id(session, order.id) or order

    except (OrderNotFoundError, InvalidOrderTransitionError):
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise


def list_order_events(
    session: Session,
    order_id: UUID,
    *,
    limit: int = 100,
    offset: int = 0,
):
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("Offset must be non-negative")

    if order_repository.get_order_by_id(session, order_id) is None:
        raise OrderNotFoundError(str(order_id))

    return order_repository.list_order_events(
        session,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )
