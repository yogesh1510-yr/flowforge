import uuid
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Table, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from flowforge.db.base import Base
from flowforge.db.session import get_db_session
from flowforge.models import Product, ProductCategory
from flowforge.main import app
from flowforge.models import Product


@pytest.fixture
def session_factory():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    tables = [
        cast(Table, ProductCategory.__table__),
        cast(Table, Product.__table__),
    ]
    Base.metadata.create_all(test_engine, tables=tables)

    factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    yield factory

    test_engine.dispose()


@pytest.fixture
def client(session_factory):
    def override_get_db_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_create_product_returns_201(client):
    response = client.post(
        "/products",
        json={
            "sku": "MOUSE-001",
            "name": "Wireless Mouse",
            "description": "Wireless USB mouse",
            "category_id": None,
            "current_price": "29.99",
            "currency": "usd",
            "status": "active",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "MOUSE-001"
    assert data["currency"] == "USD"
    assert data["current_price"] == "29.99"
    assert "id" in data


def test_list_products_returns_products(client, session_factory):
    with session_factory() as session:
        session.add_all(
            [
                Product(
                    sku="MOUSE-001",
                    name="Wireless Mouse",
                    current_price="29.99",
                    currency="USD",
                ),
                Product(
                    sku="KEYBOARD-001",
                    name="Keyboard",
                    current_price="49.99",
                    currency="USD",
                ),
            ]
        )
        session.commit()

    response = client.get("/products")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_product_returns_404_when_missing(client):
    response = client.get(f"/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_list_products_rejects_invalid_limit(client):
    response = client.get("/products?limit=101")

    assert response.status_code == 422


def test_create_product_rejects_invalid_price(client):
    response = client.post(
        "/products",
        json={
            "sku": "MOUSE-NEGATIVE",
            "name": "Invalid Product",
            "current_price": "-1.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 422


def test_create_product_rejects_invalid_currency(client):
    response = client.post(
        "/products",
        json={
            "sku": "MOUSE-CURRENCY",
            "name": "Invalid Currency Product",
            "current_price": "29.99",
            "currency": "123",
        },
    )

    assert response.status_code == 422


def test_create_product_rejects_duplicate_sku(client):
    payload = {
        "sku": "MOUSE-DUPLICATE",
        "name": "Wireless Mouse",
        "current_price": "29.99",
        "currency": "USD",
    }

    first_response = client.post("/products", json=payload)
    second_response = client.post("/products", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_product_rejects_missing_category(client):
    response = client.post(
        "/products",
        json={
            "sku": "MOUSE-CATEGORY",
            "name": "Wireless Mouse",
            "current_price": "29.99",
            "currency": "USD",
            "category_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product category not found"
