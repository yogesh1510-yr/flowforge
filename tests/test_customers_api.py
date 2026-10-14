import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Table, create_engine, engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from typing import cast

from flowforge.api.customers import router
from flowforge.db.base import Base
from flowforge.db.session import get_db_session
from flowforge.main import app
from flowforge.models import Customer


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    tables = [cast(Table, Customer.__table__)]
    Base.metadata.create_all(engine, tables=tables)

    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    yield factory

    engine.dispose()


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


def test_list_customers_returns_customers(client, session_factory):
    with session_factory() as session:
        session.add_all(
            [
                Customer(
                    email="alice@example.com",
                    full_name="Alice Smith",
                ),
                Customer(
                    email="bob@example.com",
                    full_name="Bob Jones",
                ),
            ]
        )
        session.commit()

    response = client.get("/customers")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert {customer["email"] for customer in data} == {
        "alice@example.com",
        "bob@example.com",
    }


def test_get_customer_returns_customer(client, session_factory):
    with session_factory() as session:
        customer = Customer(
            email="alice@example.com",
            full_name="Alice Smith",
        )
        session.add(customer)
        session.commit()
        customer_id = customer.id

    response = client.get(f"/customers/{customer_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(customer_id)
    assert response.json()["full_name"] == "Alice Smith"


def test_get_customer_returns_404_when_missing(client):
    response = client.get(f"/customers/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_list_customers_rejects_invalid_limit(client):
    response = client.get("/customers?limit=101")

    assert response.status_code == 422


def test_get_customer_rejects_invalid_uuid(client):
    response = client.get("/customers/not-a-uuid")

    assert response.status_code == 422


def test_create_customer_returns_201(client):
    response = client.post(
        "/customers",
        json={
            "email": "new-customer@example.com",
            "full_name": "New Customer",
            "phone": None,
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new-customer@example.com"
    assert response.json()["full_name"] == "New Customer"
    assert "id" in response.json()


def test_create_customer_rejects_invalid_email(client):
    response = client.post(
        "/customers",
        json={
            "email": "xab",
            "full_name": "Invalid Email",
            "phone": None,
        },
    )

    assert response.status_code == 422


def test_create_customer_rejects_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "full_name": "Duplicate Customer",
        "phone": None,
    }

    first_response = client.post("/customers", json=payload)
    second_response = client.post("/customers", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
