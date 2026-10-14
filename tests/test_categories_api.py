from collections.abc import Generator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from flowforge.db.base import Base
from flowforge.db.session import get_db_session
from flowforge.main import app
from flowforge.models import ProductCategory


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    test_engine: Engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    tables = [
        cast(Table, ProductCategory.__table__),
    ]
    Base.metadata.create_all(test_engine, tables=tables)

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db_session, None)
    test_engine.dispose()


def test_list_categories_returns_empty_list(client: TestClient) -> None:
    response = client.get("/categories")

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_category(client: TestClient) -> None:
    create_response = client.post(
        "/categories",
        json={"name": "Electronics", "slug": "electronics"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Electronics"
    assert created["slug"] == "electronics"
    assert created["parent_id"] is None
    assert "id" in created
    assert "created_at" in created

    get_response = client.get(f"/categories/{created['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_create_category_rejects_duplicate_slug(
    client: TestClient,
) -> None:
    payload = {"name": "Electronics", "slug": "electronics"}

    first_response = client.post("/categories", json=payload)
    second_response = client.post(
        "/categories",
        json={"name": "Consumer Electronics", "slug": "electronics"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_category_rejects_missing_parent(
    client: TestClient,
) -> None:
    from uuid import uuid4

    response = client.post(
        "/categories",
        json={
            "name": "Laptops",
            "slug": "laptops",
            "parent_id": str(uuid4()),
        },
    )

    assert response.status_code == 404


def test_get_missing_category_returns_404(client: TestClient) -> None:
    from uuid import uuid4

    response = client.get(f"/categories/{uuid4()}")

    assert response.status_code == 404


def test_create_category_rejects_invalid_slug(
    client: TestClient,
) -> None:
    response = client.post(
        "/categories",
        json={"name": "Home Kitchen", "slug": "Home Kitchen"},
    )

    assert response.status_code == 422
