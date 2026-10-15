from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowforge.core.enums import (
    InventoryMovementType,
    OrderStatus,
    ReservationStatus,
)
from flowforge.models import InventoryReservation, Order, OrderItem
from flowforge.repositories import inventory as inventory_repository
from flowforge.repositories import order as order_repository
from flowforge.repositories import reservation as reservation_repository


class FulfillmentError(Exception):
    pass


class FulfillmentOrderNotFoundError(FulfillmentError):
    pass


class FulfillmentConflictError(FulfillmentError):
    pass


class InsufficientInventoryError(FulfillmentError):
    pass


def _get_locked_order(session: Session, order_id: UUID) -> Order:
    statement = select(Order).where(Order.id == order_id).with_for_update()
    order = session.scalar(statement)
    if order is None:
        raise FulfillmentOrderNotFoundError(str(order_id))
    return order


def _get_order_items(
    session: Session,
    order_id: UUID,
) -> list[OrderItem]:
    statement = (
        select(OrderItem)
        .where(OrderItem.order_id == order_id)
        .order_by(OrderItem.product_id, OrderItem.id)
    )
    return list(session.scalars(statement).all())


def _record_order_event(
    session: Session,
    *,
    order_id: UUID,
    event_type: str,
    payload: dict,
) -> None:
    order_repository.create_order_event(
        session,
        order_id=order_id,
        event_type=event_type,
        payload=payload,
        occurred_at=datetime.now(timezone.utc),
    )


def confirm_order(
    session: Session,
    order_id: UUID,
) -> Order:
    """Reserve all order items across warehouses atomically."""
    try:
        order = _get_locked_order(session, order_id)

        if order.status != OrderStatus.PENDING:
            raise FulfillmentConflictError("Only pending orders can be confirmed")

        items = _get_order_items(session, order.id)

        if not items:
            raise FulfillmentConflictError("Cannot confirm an order without items")

        # Lock all relevant inventory rows before planning allocations.
        product_ids = {item.product_id for item in items}

        inventory_rows = inventory_repository.list_inventory_for_products_for_update(
            session,
            product_ids=product_ids,
        )

        inventory_by_product: dict[UUID, list] = {}

        for inventory in inventory_rows:
            inventory_by_product.setdefault(inventory.product_id, []).append(inventory)

        # Track available stock as allocations are planned.
        # This prevents duplicate order items from overallocating stock.
        remaining_available = {
            inventory.id: (inventory.on_hand_quantity - inventory.reserved_quantity)
            for inventory in inventory_rows
        }

        allocations = []

        # Plan every allocation before creating any reservations.
        for item in items:
            remaining_quantity = item.quantity

            for inventory in inventory_by_product.get(item.product_id, []):
                available = remaining_available[inventory.id]

                if available <= 0:
                    continue

                allocated_quantity = min(
                    remaining_quantity,
                    available,
                )

                allocations.append(
                    {
                        "item": item,
                        "inventory": inventory,
                        "quantity": allocated_quantity,
                    }
                )

                remaining_available[inventory.id] -= allocated_quantity
                remaining_quantity -= allocated_quantity

                if remaining_quantity == 0:
                    break

            if remaining_quantity > 0:
                raise InsufficientInventoryError(
                    f"Insufficient stock for product {item.product_id}"
                )

        # Apply the complete allocation plan in this transaction.
        event_allocations = []

        for allocation in allocations:
            item = allocation["item"]
            inventory = allocation["inventory"]
            quantity = allocation["quantity"]

            inventory.reserved_quantity += quantity

            reservation = reservation_repository.create_reservation(
                session,
                order_item_id=item.id,
                inventory_id=inventory.id,
                quantity=quantity,
                expires_at=None,
            )

            event_allocations.append(
                {
                    "order_item_id": str(item.id),
                    "reservation_id": str(reservation.id),
                    "warehouse_id": str(inventory.warehouse_id),
                    "product_id": str(item.product_id),
                    "quantity": quantity,
                }
            )

        order.status = OrderStatus.CONFIRMED

        _record_order_event(
            session,
            order_id=order.id,
            event_type="order.confirmed",
            payload={"allocations": event_allocations},
        )

        session.commit()
        return order

    except Exception:
        session.rollback()
        raise


def cancel_order(
    session: Session,
    order_id: UUID,
) -> Order:
    """Cancel a pending or confirmed order and release reservations."""
    try:
        order = _get_locked_order(session, order_id)

        if order.status not in {
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
        }:
            raise FulfillmentConflictError(
                "Only pending or confirmed orders can be cancelled"
            )

        released = []

        if order.status == OrderStatus.CONFIRMED:
            items = _get_order_items(session, order.id)
            item_ids = {item.id for item in items}

            statement = (
                select(InventoryReservation)
                .where(
                    InventoryReservation.order_item_id.in_(item_ids),
                    InventoryReservation.status == ReservationStatus.RESERVED,
                )
                .order_by(InventoryReservation.inventory_id, InventoryReservation.id)
                .with_for_update()
            )
            reservations = list(session.scalars(statement).all())

            inventory_ids = {reservation.inventory_id for reservation in reservations}
            locked_inventory = {}

            # Lock inventory rows in deterministic UUID order.
            for inventory_id in sorted(inventory_ids, key=str):
                inventory = inventory_repository.get_inventory_by_id(
                    session,
                    inventory_id,
                    for_update=True,
                )
                if inventory is None:
                    raise FulfillmentConflictError(
                        "Reserved inventory record no longer exists"
                    )
                locked_inventory[inventory_id] = inventory

            for reservation in reservations:
                inventory = locked_inventory[reservation.inventory_id]
                inventory.reserved_quantity -= reservation.quantity
                reservation.status = ReservationStatus.RELEASED
                released.append(str(reservation.id))

        order.status = OrderStatus.CANCELLED

        _record_order_event(
            session,
            order_id=order.id,
            event_type="order.cancelled",
            payload={"released_reservation_ids": released},
        )

        session.commit()
        return order

    except Exception:
        session.rollback()
        raise


def ship_order(
    session: Session,
    order_id: UUID,
) -> Order:
    """Consume all reserved stock and mark the order shipped atomically."""
    try:
        order = _get_locked_order(session, order_id)

        if order.status != OrderStatus.PROCESSING:
            raise FulfillmentConflictError("Only processing orders can be shipped")

        items = _get_order_items(session, order.id)

        if not items:
            raise FulfillmentConflictError("Cannot ship an order without items")

        item_ids = {item.id for item in items}

        # Lock active reservations for this order's items.
        statement = (
            select(InventoryReservation)
            .where(
                InventoryReservation.order_item_id.in_(item_ids),
                InventoryReservation.status == ReservationStatus.RESERVED,
            )
            .order_by(
                InventoryReservation.inventory_id,
                InventoryReservation.id,
            )
            .with_for_update()
        )

        reservations = list(session.scalars(statement).all())

        # Verify that every order item is reserved in exactly
        # the quantity that was ordered.
        reserved_by_item = {}

        for reservation in reservations:
            reserved_by_item[reservation.order_item_id] = (
                reserved_by_item.get(reservation.order_item_id, 0)
                + reservation.quantity
            )

        for item in items:
            reserved_quantity = reserved_by_item.get(item.id, 0)

            if reserved_quantity != item.quantity:
                raise FulfillmentConflictError(
                    f"Active reservations for order item {item.id} "
                    f"total {reserved_quantity}, but {item.quantity} "
                    "were ordered"
                )

        # Lock inventory records in a deterministic order.
        inventory_ids = {reservation.inventory_id for reservation in reservations}

        locked_inventory = {}

        for inventory_id in sorted(inventory_ids, key=str):
            inventory = inventory_repository.get_inventory_by_id(
                session,
                inventory_id,
                for_update=True,
            )

            if inventory is None:
                raise FulfillmentConflictError(
                    "Reserved inventory record no longer exists"
                )

            locked_inventory[inventory_id] = inventory

        # Consume reserved stock and record each dispatch.
        consumed = []

        for reservation in reservations:
            inventory = locked_inventory[reservation.inventory_id]
            quantity = reservation.quantity

            if (
                inventory.reserved_quantity < quantity
                or inventory.on_hand_quantity < quantity
            ):
                raise FulfillmentConflictError(
                    "Inventory quantities do not cover the reservation"
                )

            inventory.reserved_quantity -= quantity
            inventory.on_hand_quantity -= quantity
            reservation.status = ReservationStatus.CONSUMED

            inventory_repository.create_movement(
                session,
                inventory_id=inventory.id,
                movement_type=InventoryMovementType.DISPATCH,
                quantity_delta=-quantity,
                reason=f"Shipment for order {order.order_number}",
            )

            consumed.append(
                {
                    "reservation_id": str(reservation.id),
                    "order_item_id": str(reservation.order_item_id),
                    "warehouse_id": str(inventory.warehouse_id),
                    "quantity": quantity,
                }
            )

        # Update order status and write its event in the same transaction.
        order.status = OrderStatus.SHIPPED

        _record_order_event(
            session,
            order_id=order.id,
            event_type="order.shipped",
            payload={"consumed_reservations": consumed},
        )

        session.commit()
        return order

    except Exception:
        session.rollback()
        raise
