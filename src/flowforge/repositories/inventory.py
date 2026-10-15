from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowforge.core.enums import InventoryMovementType
from flowforge.models import Inventory, InventoryMovement


def get_inventory_by_id(
    session: Session,
    inventory_id: UUID,
    *,
    for_update: bool = False,
) -> Inventory | None:
    statement = select(Inventory).where(Inventory.id == inventory_id)

    if for_update:
        statement = statement.with_for_update()

    return session.scalar(statement)


def get_inventory_by_product_and_warehouse(
    session: Session,
    *,
    product_id: UUID,
    warehouse_id: UUID,
    for_update: bool = False,
) -> Inventory | None:
    statement = select(Inventory).where(
        Inventory.product_id == product_id,
        Inventory.warehouse_id == warehouse_id,
    )

    if for_update:
        statement = statement.with_for_update()

    return session.scalar(statement)


def list_inventory(
    session: Session,
    *,
    warehouse_id: UUID | None = None,
    product_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Inventory]:
    statement = select(Inventory)

    if warehouse_id is not None:
        statement = statement.where(Inventory.warehouse_id == warehouse_id)

    if product_id is not None:
        statement = statement.where(Inventory.product_id == product_id)

    statement = (
        statement.order_by(Inventory.warehouse_id, Inventory.product_id)
        .limit(limit)
        .offset(offset)
    )

    return list(session.scalars(statement).all())


def create_inventory(
    session: Session,
    *,
    warehouse_id: UUID,
    product_id: UUID,
) -> Inventory:
    inventory = Inventory(
        warehouse_id=warehouse_id,
        product_id=product_id,
        on_hand_quantity=0,
        reserved_quantity=0,
    )
    session.add(inventory)
    session.flush()
    return inventory


def create_movement(
    session: Session,
    *,
    inventory_id: UUID,
    movement_type: InventoryMovementType,
    quantity_delta: int,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    reason: str | None = None,
):
    movement = InventoryMovement(
        inventory_id=inventory_id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        reference_type=reference_type,
        reference_id=reference_id,
        reason=reason,
    )
    session.add(movement)
    session.flush()
    return movement


def list_movements(
    session: Session,
    *,
    inventory_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[InventoryMovement]:
    statement = (
        select(InventoryMovement)
        .where(InventoryMovement.inventory_id == inventory_id)
        .order_by(InventoryMovement.created_at.desc(), InventoryMovement.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())


def list_inventory_for_products_for_update(
    session: Session,
    *,
    product_ids: set[UUID],
) -> list[Inventory]:
    """Fetch and lock stock rows in a deterministic order."""
    if not product_ids:
        return []

    statement = (
        select(Inventory)
        .where(Inventory.product_id.in_(product_ids))
        .order_by(Inventory.id)
        .with_for_update()
    )
    return list(session.scalars(statement).all())
