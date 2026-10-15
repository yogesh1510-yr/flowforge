"""Idempotent demo-data seeder for FlowForge.

Creates missing demo records only. Never deletes or resets existing data.
Run from the project root with: python scripts/seed.py
"""

from datetime import datetime, timezone
from decimal import Decimal
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowforge.core.enums import (
    CustomerStatus,
    InventoryMovementType,
    OrderStatus,
    ProductStatus,
    WarehouseStatus,
)
from flowforge.db.session import get_session_factory
from flowforge.models.customer import Customer
from flowforge.models.catalog import Product, ProductCategory
from flowforge.models.warehouse import Warehouse
from flowforge.models.inventory import Inventory, InventoryMovement
from flowforge.models.order import Order, OrderItem, OrderEvent

CUSTOMERS = [
    {
        "email": "aarav.sharma@example.com",
        "full_name": "Aarav Sharma",
        "phone": "+919876540101",
    },
    {
        "email": "priya.nair@example.com",
        "full_name": "Priya Nair",
        "phone": "+919876540102",
    },
    {
        "email": "rohan.mehta@example.com",
        "full_name": "Rohan Mehta",
        "phone": "+919876540103",
    },
]

CATEGORIES = [
    {"name": "Electronics", "slug": "electronics", "parent": None},
    {
        "name": "Computer Accessories",
        "slug": "computer-accessories",
        "parent": "electronics",
    },
    {"name": "Office Equipment", "slug": "office-equipment", "parent": "electronics"},
]

PRODUCTS = [
    {
        "sku": "FF-LAPTOP-001",
        "name": "Business Laptop",
        "description": "Demo business laptop",
        "category": "electronics",
        "price": Decimal("65000.00"),
        "currency": "INR",
    },
    {
        "sku": "FF-MOUSE-001",
        "name": "Wireless Mouse",
        "description": "Demo wireless mouse",
        "category": "computer-accessories",
        "price": Decimal("1200.00"),
        "currency": "INR",
    },
    {
        "sku": "FF-KEYBOARD-001",
        "name": "Mechanical Keyboard",
        "description": "Demo mechanical keyboard",
        "category": "computer-accessories",
        "price": Decimal("3500.00"),
        "currency": "INR",
    },
    {
        "sku": "FF-MONITOR-001",
        "name": "27-inch Monitor",
        "description": "Demo external monitor",
        "category": "office-equipment",
        "price": Decimal("18000.00"),
        "currency": "INR",
    },
    {
        "sku": "FF-WEBCAM-001",
        "name": "HD Webcam",
        "description": "Demo USB webcam",
        "category": "computer-accessories",
        "price": Decimal("2500.00"),
        "currency": "INR",
    },
]

WAREHOUSES = [
    {
        "code": "FF-BLR-01",
        "name": "Bengaluru Central Warehouse",
        "address_line1": "Industrial Area, Peenya",
        "city": "Bengaluru",
        "country_code": "IN",
        "timezone": "Asia/Kolkata",
    },
    {
        "code": "FF-MAA-01",
        "name": "Chennai Regional Warehouse",
        "address_line1": "Ambattur Industrial Estate",
        "city": "Chennai",
        "country_code": "IN",
        "timezone": "Asia/Kolkata",
    },
]

# Stock is added only when the corresponding inventory record is new.
STOCK = {
    ("FF-BLR-01", "FF-LAPTOP-001"): 4,
    ("FF-MAA-01", "FF-LAPTOP-001"): 3,
    ("FF-BLR-01", "FF-MOUSE-001"): 50,
    ("FF-MAA-01", "FF-MOUSE-001"): 30,
    ("FF-BLR-01", "FF-KEYBOARD-001"): 25,
    ("FF-MAA-01", "FF-KEYBOARD-001"): 20,
    ("FF-BLR-01", "FF-MONITOR-001"): 6,
    ("FF-MAA-01", "FF-MONITOR-001"): 4,
    ("FF-BLR-01", "FF-WEBCAM-001"): 15,
    ("FF-MAA-01", "FF-WEBCAM-001"): 15,
}

ORDERS = [
    {
        "number": "FF-SEED-1001",
        "customer": "aarav.sharma@example.com",
        "items": [
            ("FF-LAPTOP-001", 2),
            ("FF-MOUSE-001", 3),
        ],
    },
    {
        "number": "FF-SEED-1002",
        "customer": "priya.nair@example.com",
        "items": [
            ("FF-MONITOR-001", 9999),
        ],
    },
    {
        "number": "FF-SEED-1003",
        "customer": "rohan.mehta@example.com",
        "items": [
            ("FF-KEYBOARD-001", 1),
        ],
    },
]

SHIPPING_ADDRESS = {
    "recipient_name": "FlowForge Demo Customer",
    "address_line1": "100 Demo Street",
    "city": "Bengaluru",
    "state": "Karnataka",
    "postal_code": "560001",
    "country_code": "IN",
}


def get_or_create(
    session: Session,
    model,
    lookup: dict,
    values: dict,
):
    """Return an existing record or insert a new one."""
    instance = session.scalar(select(model).filter_by(**lookup))

    if instance is not None:
        return instance, False

    instance = model(**values)
    session.add(instance)
    session.flush()
    return instance, True


def seed_customers(session: Session) -> dict[str, Customer]:
    result = {}

    for data in CUSTOMERS:
        customer, created = get_or_create(
            session,
            Customer,
            {"email": data["email"]},
            {**data, "status": CustomerStatus.ACTIVE},
        )
        result[customer.email] = customer
        print(f"{'Created' if created else 'Exists'} customer: {customer.email}")

    return result


def seed_categories(session: Session) -> dict[str, ProductCategory]:
    result = {}

    for data in CATEGORIES:
        parent = result.get(data["parent"]) if data["parent"] else None

        category, created = get_or_create(
            session,
            ProductCategory,
            {"slug": data["slug"]},
            {
                "name": data["name"],
                "slug": data["slug"],
                "parent_id": parent.id if parent else None,
            },
        )

        result[data["slug"]] = category
        print(f"{'Created' if created else 'Exists'} category: {category.slug}")

    return result


def seed_products(
    session: Session,
    categories: dict[str, ProductCategory],
) -> dict[str, Product]:
    result = {}

    for data in PRODUCTS:
        category = categories[data["category"]]

        product, created = get_or_create(
            session,
            Product,
            {"sku": data["sku"]},
            {
                "sku": data["sku"],
                "name": data["name"],
                "description": data["description"],
                "category_id": category.id,
                "current_price": data["price"],
                "currency": data["currency"],
                "status": ProductStatus.ACTIVE,
            },
        )

        result[product.sku] = product
        print(f"{'Created' if created else 'Exists'} product: {product.sku}")

    return result


def seed_warehouses(session: Session) -> dict[str, Warehouse]:
    result = {}

    for data in WAREHOUSES:
        warehouse, created = get_or_create(
            session,
            Warehouse,
            {"code": data["code"]},
            {**data, "status": WarehouseStatus.ACTIVE},
        )

        result[warehouse.code] = warehouse
        print(f"{'Created' if created else 'Exists'} warehouse: {warehouse.code}")

    return result


def seed_inventory(
    session: Session,
    products: dict[str, Product],
    warehouses: dict[str, Warehouse],
) -> None:
    for (warehouse_code, sku), quantity in STOCK.items():
        warehouse = warehouses[warehouse_code]
        product = products[sku]

        inventory, created = get_or_create(
            session,
            Inventory,
            {
                "warehouse_id": warehouse.id,
                "product_id": product.id,
            },
            {
                "warehouse_id": warehouse.id,
                "product_id": product.id,
                "on_hand_quantity": quantity,
                "reserved_quantity": 0,
            },
        )

        if created and quantity > 0:
            inventory_repository_movement = InventoryMovement(
                inventory_id=inventory.id,
                movement_type=InventoryMovementType.RECEIPT,
                quantity_delta=quantity,
                reference_type="seed",
                reason="Initial demo stock",
            )
            session.add(inventory_repository_movement)

        print(
            f"{'Created' if created else 'Exists'} inventory: "
            f"{warehouse_code}/{sku}"
        )


def seed_orders(
    session: Session,
    customers: dict[str, Customer],
    products: dict[str, Product],
) -> None:
    for data in ORDERS:
        existing = session.scalar(
            select(Order).where(Order.order_number == data["number"])
        )

        if existing is not None:
            print(f"Exists order: {data['number']}")
            continue

        line_items = []
        subtotal = Decimal("0.00")

        for sku, quantity in data["items"]:
            product = products[sku]
            line_total = (product.current_price * quantity).quantize(Decimal("0.01"))
            subtotal += line_total

            line_items.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "line_total": line_total,
                }
            )

        order = Order(
            order_number=data["number"],
            customer_id=customers[data["customer"]].id,
            status=OrderStatus.PENDING,
            currency="INR",
            subtotal=subtotal,
            tax_amount=Decimal("0.00"),
            shipping_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=subtotal,
            shipping_address_snapshot=SHIPPING_ADDRESS,
        )

        session.add(order)
        session.flush()

        for line in line_items:
            product = line["product"]
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    sku_snapshot=product.sku,
                    product_name_snapshot=product.name,
                    quantity=line["quantity"],
                    unit_price=product.current_price,
                    line_total=line["line_total"],
                )
            )

        session.add(
            OrderEvent(
                order_id=order.id,
                event_type="order.created",
                event_version=1,
                payload={
                    "source": "seed",
                    "order_number": data["number"],
                    "item_count": len(line_items),
                },
                occurred_at=datetime.now(timezone.utc),
            )
        )

        session.flush()
        print(f"Created order: {data['number']}")


def main() -> None:
    factory = get_session_factory()

    with factory() as session:
        try:
            with session.begin():
                customers = seed_customers(session)
                categories = seed_categories(session)
                products = seed_products(session, categories)
                warehouses = seed_warehouses(session)
                seed_inventory(session, products, warehouses)
                seed_orders(session, customers, products)

            print("\nSeed completed successfully.")

        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    main()
