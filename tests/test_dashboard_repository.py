from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from flowforge.db.base import Base
from flowforge.models.catalog import Product, ProductCategory
from flowforge.models.inventory import Inventory
from flowforge.models.warehouse import Warehouse
from flowforge.repositories.dashboard import get_low_stock


@pytest.fixture
def db_session():
    engine: Engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    tables = [
        ProductCategory.__table__,
        Product.__table__,
        Warehouse.__table__,
        Inventory.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)

    with Session(engine) as session:
        yield session

    engine.dispose()


def test_low_stock_uses_available_quantity(db_session: Session) -> None:
    warehouse = Warehouse(
        code="TEST-BLR",
        name="Test Warehouse",
        address_line1="1 Test Street",
        city="Bengaluru",
        country_code="IN",
        timezone="Asia/Kolkata",
    )
    product = Product(
        sku="TEST-LAPTOP",
        name="Test Laptop",
        current_price=Decimal("50000.00"),
        currency="INR",
    )

    db_session.add_all([warehouse, product])
    db_session.flush()

    inventory = Inventory(
        warehouse_id=warehouse.id,
        product_id=product.id,
        on_hand_quantity=8,
        reserved_quantity=6,
    )
    db_session.add(inventory)
    db_session.commit()

    results = get_low_stock(db_session, threshold=2, limit=10)

    assert len(results) == 1
    row = results[0]
    assert row[3] == "TEST-LAPTOP"
    assert row[5] == 8
    assert row[6] == 6
    assert row[7] == 2


def test_low_stock_excludes_inventory_above_threshold(
    db_session: Session,
) -> None:
    warehouse = Warehouse(
        code="TEST-MAA",
        name="Test Warehouse",
        address_line1="2 Test Street",
        city="Chennai",
        country_code="IN",
        timezone="Asia/Kolkata",
    )
    product = Product(
        sku="TEST-MOUSE",
        name="Test Mouse",
        current_price=Decimal("1200.00"),
        currency="INR",
    )

    db_session.add_all([warehouse, product])
    db_session.flush()

    db_session.add(
        Inventory(
            warehouse_id=warehouse.id,
            product_id=product.id,
            on_hand_quantity=10,
            reserved_quantity=2,
        )
    )
    db_session.commit()

    results = get_low_stock(db_session, threshold=5, limit=10)

    assert results == []
