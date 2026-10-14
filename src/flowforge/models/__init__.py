"""Model package: import all models so SQLAlchemy registers their tables."""

from flowforge.models.customer import Customer, CustomerAddress
from flowforge.models.catalog import Product, ProductCategory
from flowforge.models.warehouse import Warehouse
from flowforge.models.inventory import (
    Inventory,
    InventoryMovement,
    InventoryReservation,
)
from flowforge.models.order import Order, OrderEvent, OrderItem

__all__ = [
    "Customer",
    "CustomerAddress",
    "Product",
    "ProductCategory",
    "Warehouse",
    "Inventory",
    "InventoryReservation",
    "InventoryMovement",
    "Order",
    "OrderItem",
    "OrderEvent",
]
