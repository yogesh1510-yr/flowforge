from uuid import UUID,uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from flowforge.core.enums import InventoryMovementType
from flowforge.models import Inventory, InventoryMovement
from flowforge.models.inventory import InventoryMovementType
from flowforge.repositories import inventory as inventory_repository
from flowforge.repositories import product as product_repository
from flowforge.repositories import warehouse as warehouse_repository


class InventoryNotFoundError(Exception):
    pass


class StockConflictError(Exception):
    pass


class RelatedResourceNotFoundError(Exception):
    pass


def list_inventory(
    session: Session,
    *,
    warehouse_id: UUID | None = None,
    product_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Inventory]:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("Offset must be non-negative")

    return inventory_repository.list_inventory(
        session,
        warehouse_id=warehouse_id,
        product_id=product_id,
        limit=limit,
        offset=offset,
    )


def list_movements(
    session: Session,
    inventory_id: UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[InventoryMovement]:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("Offset must be non-negative")

    if inventory_repository.get_inventory_by_id(session, inventory_id) is None:
        raise InventoryNotFoundError(str(inventory_id))

    return inventory_repository.list_movements(
        session,
        inventory_id=inventory_id,
        limit=limit,
        offset=offset,
    )


def receive_stock(
    session: Session,
    *,
    warehouse_id: UUID,
    product_id: UUID,
    quantity: int,
    reason: str | None = None,
) -> Inventory:
    if quantity <= 0:
        raise ValueError("Receipt quantity must be greater than zero")

    if warehouse_repository.get_warehouse_by_id(session, warehouse_id) is None:
        raise RelatedResourceNotFoundError("Warehouse not found")

    if product_repository.get_product_by_id(session, product_id) is None:
        raise RelatedResourceNotFoundError("Product not found")

    try:
        inventory = inventory_repository.get_inventory_by_product_and_warehouse(
            session,
            product_id=product_id,
            warehouse_id=warehouse_id,
            for_update=True,
        )

        if inventory is None:
            inventory = inventory_repository.create_inventory(
                session,
                warehouse_id=warehouse_id,
                product_id=product_id,
            )

        inventory.on_hand_quantity += quantity

        inventory_repository.create_movement(
            session,
            inventory_id=inventory.id,
            movement_type=InventoryMovementType.RECEIPT,
            quantity_delta=quantity,
            reason=reason,
        )

        session.commit()
        session.refresh(inventory)
        return inventory

    except IntegrityError:
        session.rollback()
        raise


def adjust_stock(
    session: Session,
    *,
    inventory_id: UUID,
    quantity_delta: int,
    reason: str,
) -> Inventory:
    if quantity_delta == 0:
        raise ValueError("Quantity delta must not be zero")
    if not reason.strip():
        raise ValueError("Adjustment reason is required")

    try:
        inventory = inventory_repository.get_inventory_by_id(
            session,
            inventory_id,
            for_update=True,
        )

        if inventory is None:
            raise InventoryNotFoundError(str(inventory_id))

        new_quantity = inventory.on_hand_quantity + quantity_delta

        if new_quantity < inventory.reserved_quantity:
            raise StockConflictError(
                "Adjustment would reduce stock below reserved quantity"
            )

        if new_quantity < 0:
            raise StockConflictError("Insufficient stock for adjustment")

        inventory.on_hand_quantity = new_quantity

        inventory_repository.create_movement(
            session,
            inventory_id=inventory.id,
            movement_type=InventoryMovementType.ADJUSTMENT,
            quantity_delta=quantity_delta,
            reason=reason.strip(),
        )

        session.commit()
        session.refresh(inventory)
        return inventory

    except (InventoryNotFoundError, StockConflictError):
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise

def transfer_stock(
    session: Session,
    source_warehouse_id: UUID,
    destination_warehouse_id: UUID,
    product_id: UUID,
    quantity: int,
    reason: str | None = None,
) -> dict:
    """Transfer available stock between warehouses atomically."""
    try:
        if quantity <= 0:
            raise StockConflictError(
                "Transfer quantity must be greater than zero"
            )

        if source_warehouse_id == destination_warehouse_id:
            raise StockConflictError(
                "Source and destination warehouses must be different"
            )

        # Find both inventory records before locking them.
        source = inventory_repository.get_inventory_by_product_and_warehouse(
            session,
            warehouse_id=source_warehouse_id,
            product_id=product_id,
        )
        destination = inventory_repository.get_inventory_by_product_and_warehouse(
            session,
            warehouse_id=destination_warehouse_id,
            product_id=product_id,
        )

        if source is None:
            raise InventoryNotFoundError(
                "Source warehouse has no inventory record for this product"
            )

        if destination is None:
            raise InventoryNotFoundError(
                "Destination warehouse has no inventory record for this product"
            )

        # Lock both rows in the same order to reduce deadlock risk.
        locked_inventory = {}

        for inventory_id in sorted(
            {source.id, destination.id},
            key=str,
        ):
            inventory = inventory_repository.get_inventory_by_id(
                session,
                inventory_id,
                for_update=True,
            )

            if inventory is None:
                raise InventoryNotFoundError(
                    "Inventory record no longer exists"
                )

            locked_inventory[inventory_id] = inventory

        source = locked_inventory[source.id]
        destination = locked_inventory[destination.id]

        available_quantity = (
            source.on_hand_quantity - source.reserved_quantity
        )

        if available_quantity < quantity:
            raise StockConflictError(
                f"Insufficient available stock: {available_quantity} "
                f"available, {quantity} requested"
            )

        # Use one reference ID to link both movement records.
        transfer_id = uuid4()

        source.on_hand_quantity -= quantity
        destination.on_hand_quantity += quantity

        movement_reason = reason or (
            f"Stock transfer {transfer_id}"
        )

        inventory_repository.create_movement(
            session,
            inventory_id=source.id,
            movement_type=InventoryMovementType.TRANSFER_OUT,
            quantity_delta=-quantity,
            reference_type="stock_transfer",
            reference_id=transfer_id,
            reason=movement_reason,
        )

        inventory_repository.create_movement(
            session,
            inventory_id=destination.id,
            movement_type=InventoryMovementType.TRANSFER_IN,
            quantity_delta=quantity,
            reference_type="stock_transfer",
            reference_id=transfer_id,
            reason=movement_reason,
        )

        session.commit()

        session.refresh(source)
        session.refresh(destination)

        return {
            "transfer_id": transfer_id,
            "product_id": product_id,
            "quantity": quantity,
            "source_inventory": source,
            "destination_inventory": destination,
        }

    except Exception:
        session.rollback()
        raise