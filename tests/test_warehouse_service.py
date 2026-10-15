from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from flowforge.services import warehouse as warehouse_service


def test_list_warehouses_rejects_invalid_limit():
    session = Mock(spec=Session)

    with pytest.raises(ValueError, match="Limit"):
        warehouse_service.list_warehouses(session, limit=101)


def test_list_warehouses_rejects_negative_offset():
    session = Mock(spec=Session)

    with pytest.raises(ValueError, match="[Oo]ffset"):
        warehouse_service.list_warehouses(session, offset=-1)


def test_create_warehouse_rejects_duplicate_code(monkeypatch):
    session = Mock(spec=Session)
    existing = object()

    monkeypatch.setattr(
        warehouse_service.warehouse_repository,
        "get_warehouse_by_code",
        lambda session, code: existing,
    )

    with pytest.raises(warehouse_service.DuplicateWarehouseCodeError):
        warehouse_service.create_warehouse(
            session,
            code="WH-BENGALURU",
            name="Bengaluru Warehouse",
            address_line1="12 Industrial Road",
            city="Bengaluru",
            country_code="IN",
            timezone="Asia/Kolkata",
        )

    session.commit.assert_not_called()
