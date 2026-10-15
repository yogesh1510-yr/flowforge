from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flowforge.models.catalog import Product
from flowforge.models.inventory import Inventory, InventoryMovement
from flowforge.models.order import Order
from flowforge.models.warehouse import Warehouse


def get_order_summary(session: Session) -> list[tuple]:
    statement = (
        select(
            Order.status,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
        )
        .group_by(Order.status)
        .order_by(Order.status)
    )
    return list(session.execute(statement).all())


def get_low_stock(
    session: Session,
    *,
    threshold: int,
    limit: int,
) -> list[tuple]:
    available = Inventory.on_hand_quantity - Inventory.reserved_quantity

    statement = (
        select(
            Inventory.id,
            Warehouse.code,
            Product.id,
            Product.sku,
            Product.name,
            Inventory.on_hand_quantity,
            Inventory.reserved_quantity,
            available.label("available_quantity"),
        )
        .join(Warehouse, Warehouse.id == Inventory.warehouse_id)
        .join(Product, Product.id == Inventory.product_id)
        .where(available <= threshold)
        .order_by(available.asc(), Product.sku.asc())
        .limit(limit)
    )
    return list(session.execute(statement).all())


def get_recent_movements(
    session: Session,
    *,
    limit: int,
) -> list[tuple]:
    statement = (
        select(
            InventoryMovement.id,
            Product.sku,
            Warehouse.code,
            InventoryMovement.movement_type,
            InventoryMovement.quantity_delta,
            InventoryMovement.reference_type,
            InventoryMovement.reference_id,
            InventoryMovement.reason,
            InventoryMovement.created_at,
        )
        .join(
            Inventory,
            Inventory.id == InventoryMovement.inventory_id,
        )
        .join(Product, Product.id == Inventory.product_id)
        .join(Warehouse, Warehouse.id == Inventory.warehouse_id)
        .order_by(
            InventoryMovement.created_at.desc(),
            InventoryMovement.id.desc(),
        )
        .limit(limit)
    )
    return list(session.execute(statement).all())
