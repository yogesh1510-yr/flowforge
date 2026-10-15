from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from flowforge.db.session import get_db_session
from flowforge.main import app
from flowforge.api.schemas.dashboard import (
    DashboardSummary,
    LowStockItem,
    OrderStatusSummary,
    RecentMovement,
)
from flowforge.services import dashboard as dashboard_service


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_get_db_session() -> Generator[Session, None, None]:
        # Dashboard service functions are mocked in these API tests.
        yield None  # type: ignore[misc]

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_dashboard_summary_returns_metrics(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = DashboardSummary(
        total_orders=3,
        active_orders=2,
        total_order_value=Decimal("137100.00"),
        orders_by_status=[
            OrderStatusSummary(
                status="confirmed",
                count=1,
                order_value=Decimal("133600.00"),
            ),
            OrderStatusSummary(
                status="cancelled",
                count=1,
                order_value=Decimal("3500.00"),
            ),
            OrderStatusSummary(
                status="pending",
                count=1,
                order_value=Decimal("0.00"),
            ),
        ],
    )

    monkeypatch.setattr(
        dashboard_service,
        "get_summary",
        lambda session: summary,
    )

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["total_orders"] == 3
    assert data["active_orders"] == 2
    assert data["total_order_value"] == "137100.00"
    assert len(data["orders_by_status"]) == 3


def test_dashboard_low_stock_returns_available_quantity(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = LowStockItem(
        inventory_id=uuid4(),
        warehouse_code="FF-BLR-01",
        product_id=uuid4(),
        sku="FF-LAPTOP-001",
        product_name="Laptop",
        on_hand_quantity=4,
        reserved_quantity=3,
        available_quantity=1,
    )

    def fake_get_low_stock(
        session: Session,
        *,
        threshold: int = 5,
        limit: int = 50,
    ) -> list[LowStockItem]:
        assert threshold == 2
        assert limit == 10
        return [item]

    monkeypatch.setattr(
        dashboard_service,
        "get_low_stock",
        fake_get_low_stock,
    )

    response = client.get(
        "/dashboard/low-stock",
        params={"threshold": 2, "limit": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["on_hand_quantity"] == 4
    assert data[0]["reserved_quantity"] == 3
    assert data[0]["available_quantity"] == 1


def test_dashboard_low_stock_rejects_negative_threshold(
    client: TestClient,
) -> None:
    response = client.get(
        "/dashboard/low-stock",
        params={"threshold": -1},
    )

    assert response.status_code == 422


def test_dashboard_low_stock_rejects_limit_over_maximum(
    client: TestClient,
) -> None:
    response = client.get(
        "/dashboard/low-stock",
        params={"limit": 501},
    )

    assert response.status_code == 422


def test_dashboard_recent_movements_returns_records(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    movement = RecentMovement(
        movement_id=uuid4(),
        sku="FF-LAPTOP-001",
        warehouse_code="FF-BLR-01",
        movement_type="dispatch",
        quantity_delta=-2,
        reference_type="order",
        reference_id=uuid4(),
        reason="Order shipped",
        created_at=datetime.now(timezone.utc),
    )

    def fake_get_recent_movements(
        session: Session,
        *,
        limit: int = 20,
    ) -> list[RecentMovement]:
        assert limit == 5
        return [movement]

    monkeypatch.setattr(
        dashboard_service,
        "get_recent_movements",
        fake_get_recent_movements,
    )

    response = client.get(
        "/dashboard/recent-movements",
        params={"limit": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sku"] == "FF-LAPTOP-001"
    assert data[0]["movement_type"] == "dispatch"
    assert data[0]["quantity_delta"] == -2


def test_dashboard_recent_movements_rejects_invalid_limit(
    client: TestClient,
) -> None:
    response = client.get(
        "/dashboard/recent-movements",
        params={"limit": 101},
    )

    assert response.status_code == 422
    