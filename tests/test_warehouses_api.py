from collections.abc import Generator
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from flowforge.db.base import Base
from flowforge.db.session import get_db_session
from flowforge.main import app
from flowforge.models import Warehouse


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    test_engine: Engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    tables = [cast(Table, Warehouse.__table__)]
    Base.metadata.create_all(test_engine, tables=tables)

    testing_session_local = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        session = testing_session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        test_engine.dispose()


def warehouse_payload() -> dict[str, str]:
    return {
        "code": "wh-bengaluru",
        "name": "Bengaluru Warehouse",
        "address_line1": "12 Industrial Road",
        "city": "Bengaluru",
        "country_code": "in",
        "timezone": "Asia/Kolkata",
        "status": "active",
    }


def test_list_warehouses_returns_empty_list(client: TestClient) -> None:
    response = client.get("/warehouses")

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_warehouse(client: TestClient) -> None:
    create_response = client.post(
        "/warehouses",
        json=warehouse_payload(),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == "WH-BENGALURU"
    assert created["country_code"] == "IN"
    assert created["name"] == "Bengaluru Warehouse"
    assert "id" in created
    assert "created_at" in created

    get_response = client.get(f"/warehouses/{created['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_create_warehouse_rejects_duplicate_code(
    client: TestClient,
) -> None:
    first = client.post("/warehouses", json=warehouse_payload())
    second = client.post("/warehouses", json=warehouse_payload())

    assert first.status_code == 201
    assert second.status_code == 409


def test_get_missing_warehouse_returns_404(
    client: TestClient,
) -> None:
    response = client.get(f"/warehouses/{uuid4()}")

    assert response.status_code == 404


def test_create_warehouse_rejects_invalid_country_code(
    client: TestClient,
) -> None:
    payload = warehouse_payload()
    payload["country_code"] = "IND"

    response = client.post("/warehouses", json=payload)

    assert response.status_code == 422


def test_list_warehouses_rejects_invalid_limit(
    client: TestClient,
) -> None:
    response = client.get("/warehouses?limit=101")

    assert response.status_code == 422
