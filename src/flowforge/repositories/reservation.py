from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowforge.core.enums import ReservationStatus
from flowforge.models import InventoryReservation


def get_reservation_by_id(
    session: Session,
    reservation_id: UUID,
    *,
    for_update: bool = False,
) -> InventoryReservation | None:
    statement = select(InventoryReservation).where(
        InventoryReservation.id == reservation_id
    )
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def create_reservation(
    session: Session,
    *,
    order_item_id: UUID,
    inventory_id: UUID,
    quantity: int,
    expires_at,
) -> InventoryReservation:
    reservation = InventoryReservation(
        order_item_id=order_item_id,
        inventory_id=inventory_id,
        quantity=quantity,
        expires_at=expires_at,
        status=ReservationStatus.RESERVED,
    )
    session.add(reservation)
    session.flush()
    return reservation


def list_reservations(
    session: Session,
    *,
    inventory_id: UUID | None = None,
    order_item_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[InventoryReservation]:
    statement = select(InventoryReservation)

    if inventory_id is not None:
        statement = statement.where(InventoryReservation.inventory_id == inventory_id)
    if order_item_id is not None:
        statement = statement.where(InventoryReservation.order_item_id == order_item_id)

    statement = (
        statement.order_by(
            InventoryReservation.created_at.desc(),
            InventoryReservation.id,
        )
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())
