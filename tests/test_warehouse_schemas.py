import pytest
from pydantic import ValidationError

from flowforge.api.schemas.warehouse import WarehouseCreate


def valid_warehouse_payload() -> dict[str, str]:
    return {
        "code": "wh-bengaluru",
        "name": "Bengaluru Warehouse",
        "address_line1": "12 Industrial Road",
        "city": "Bengaluru",
        "country_code": "in",
        "timezone": "Asia/Kolkata",
    }


def test_warehouse_create_normalizes_code_and_country():
    warehouse = WarehouseCreate(**valid_warehouse_payload())

    assert warehouse.code == "WH-BENGALURU"
    assert warehouse.country_code == "IN"


def test_warehouse_create_defaults_to_active():
    warehouse = WarehouseCreate(**valid_warehouse_payload())

    assert warehouse.status.value == "active"


def test_warehouse_create_rejects_blank_name():
    payload = valid_warehouse_payload()
    payload["name"] = "   "

    with pytest.raises(ValidationError):
        WarehouseCreate(**payload)


@pytest.mark.parametrize("country_code", ["I", "IND", "1N", "éé"])
def test_warehouse_create_rejects_invalid_country_code(country_code):
    payload = valid_warehouse_payload()
    payload["country_code"] = country_code

    with pytest.raises(ValidationError):
        WarehouseCreate(**payload)
