from datetime import datetime, timezone
from uuid import UUID


from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from flowforge.core.enums import (
    InventoryMovementType,
    OrderStatus,
    ReservationStatus,
)
from flowforge.models.inventory import InventoryReservation
from flowforge.models.order import Order, OrderItem
from flowforge.repositories import inventory as inventory_repository
from flowforge.repositories import reservation as reservation_repository


class ReservationNotFoundError(Exception):
    pass


class ReservationConflictError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


def create_reservation(
    session: Session,
    *,
    order_item_id: UUID,
    inventory_id: UUID,
    quantity: int,
    expires_at: datetime | None = None,
) -> InventoryReservation:
    if quantity <= 0:
        raise ValueError("Reservation quantity must be greater than zero")

    if expires_at is not None:
        if expires_at.tzinfo is None:
            raise ValueError("expires_at must include a timezone")
        if expires_at <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")

    try:
        # Serialize manual reservations with order confirmation. Both paths
        # lock the order first, avoiding a partial reservation during allocation.
        order_and_item = session.execute(
            select(Order, OrderItem)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(OrderItem.id == order_item_id)
            .with_for_update(of=Order)
        ).one_or_none()
        if order_and_item is None:
            raise ReservationNotFoundError("Order item not found")

        order, order_item = order_and_item
        if order.status != OrderStatus.PENDING:
            raise ReservationConflictError(
                "Reservations can only be added to pending orders"
            )

        inventory = inventory_repository.get_inventory_by_id(
            session,
            inventory_id,
            for_update=True,
        )
        if inventory is None:
            raise ReservationNotFoundError("Inventory not found")

        if inventory.product_id != order_item.product_id:
            raise ReservationConflictError(
                "Inventory product does not match the order item"
            )

        already_reserved = session.scalar(
            select(func.coalesce(func.sum(InventoryReservation.quantity), 0)).where(
                InventoryReservation.order_item_id == order_item_id,
                InventoryReservation.status == ReservationStatus.RESERVED,
            )
        )
        if already_reserved + quantity > order_item.quantity:
            raise ReservationConflictError(
                "Reservation would exceed the order item quantity"
            )

        available = inventory.on_hand_quantity - inventory.reserved_quantity
        if quantity > available:
            raise InsufficientStockError("Insufficient available stock")

        reservation = reservation_repository.create_reservation(
            session,
            order_item_id=order_item_id,
            inventory_id=inventory_id,
            quantity=quantity,
            expires_at=expires_at,
        )
        inventory.reserved_quantity += quantity
        session.commit()
        session.refresh(reservation)
        return reservation

    except (
        ReservationNotFoundError,
        ReservationConflictError,
        InsufficientStockError,
        ValueError,
    ):
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise


def _transition_reservation(
    session: Session,
    reservation_id: UUID,
    target_status: ReservationStatus,
) -> InventoryReservation:
    try:
        reservation = reservation_repository.get_reservation_by_id(
            session,
            reservation_id,
            for_update=True,
        )
        if reservation is None:
            raise ReservationNotFoundError("Reservation not found")

        if reservation.status != ReservationStatus.RESERVED:
            raise ReservationConflictError(
                f"Cannot transition reservation from {reservation.status}"
            )

        inventory = inventory_repository.get_inventory_by_id(
            session,
            reservation.inventory_id,
            for_update=True,
        )
        if inventory is None:
            raise ReservationNotFoundError("Inventory not found")

        if target_status == ReservationStatus.RELEASED:
            inventory.reserved_quantity -= reservation.quantity

        elif target_status == ReservationStatus.CONSUMED:
            inventory.reserved_quantity -= reservation.quantity
            inventory.on_hand_quantity -= reservation.quantity

            inventory_repository.create_movement(
                session,
                inventory_id=inventory.id,
                movement_type=InventoryMovementType.DISPATCH,
                quantity_delta=-reservation.quantity,
                reason=f"Consumed reservation {reservation.id}",
            )

        reservation.status = target_status
        session.commit()
        session.refresh(reservation)
        return reservation

    except (ReservationNotFoundError, ReservationConflictError):
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise


def release_reservation(
    session: Session,
    reservation_id: UUID,
) -> InventoryReservation:
    return _transition_reservation(
        session,
        reservation_id,
        ReservationStatus.RELEASED,
    )


def consume_reservation(
    session: Session,
    reservation_id: UUID,
) -> InventoryReservation:
    return _transition_reservation(
        session,
        reservation_id,
        ReservationStatus.CONSUMED,
    )


def list_reservations(
    session: Session,
    *,
    inventory_id: UUID | None = None,
    order_item_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[InventoryReservation]:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("Offset must be non-negative")

    return reservation_repository.list_reservations(
        session,
        inventory_id=inventory_id,
        order_item_id=order_item_id,
        limit=limit,
        offset=offset,
    )


def expire_reservations(
    session: Session,
    now: datetime | None = None,
    limit: int = 500,
) -> int:
    """Expire due reservations and release their reserved stock atomically."""
    try:
        if limit < 1:
            raise ValueError("limit must be greater than zero")

        current_time = now or datetime.now(timezone.utc)

        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        # Find due reservations that are still active.
        # SKIP LOCKED lets multiple workers process separate batches.
        statement = (
            select(InventoryReservation)
            .where(
                InventoryReservation.status == ReservationStatus.RESERVED,
                InventoryReservation.expires_at.is_not(None),
                InventoryReservation.expires_at <= current_time,
            )
            .order_by(
                InventoryReservation.inventory_id,
                InventoryReservation.id,
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        reservations = list(session.scalars(statement).all())

        if not reservations:
            session.commit()
            return 0

        # Calculate the total reserved quantity to release per inventory row.
        release_by_inventory = {}

        for reservation in reservations:
            release_by_inventory[reservation.inventory_id] = (
                release_by_inventory.get(reservation.inventory_id, 0)
                + reservation.quantity
            )

        # Lock inventory rows in a deterministic order.
        locked_inventory = {}

        for inventory_id in sorted(
            release_by_inventory,
            key=str,
        ):
            inventory = inventory_repository.get_inventory_by_id(
                session,
                inventory_id,
                for_update=True,
            )

            if inventory is None:
                raise ReservationConflictError(
                    "Inventory record for an expiring reservation " "no longer exists"
                )

            quantity_to_release = release_by_inventory[inventory_id]

            if inventory.reserved_quantity < quantity_to_release:
                raise ReservationConflictError(
                    "Reserved inventory is insufficient to expire " "these reservations"
                )

            locked_inventory[inventory_id] = inventory

        # Release stock and transition each reservation exactly once.
        for inventory_id, quantity in release_by_inventory.items():
            locked_inventory[inventory_id].reserved_quantity -= quantity

        for reservation in reservations:
            reservation.status = ReservationStatus.EXPIRED

        session.commit()
        return len(reservations)

    except Exception:
        session.rollback()
        raise
