from decimal import Decimal

import pytest
from pydantic import ValidationError

from flowforge.api.schemas.product import ProductCreate


def test_product_create_normalizes_currency_and_strings():
    product = ProductCreate(
        sku="  SKU-001  ",
        name="  Wireless Mouse  ",
        current_price="29.99",
        currency="usd",
    )

    assert product.sku == "SKU-001"
    assert product.name == "Wireless Mouse"
    assert product.current_price == Decimal("29.99")
    assert product.currency == "USD"


@pytest.mark.parametrize("currency", ["US", "123", "USDD"])
def test_product_create_rejects_invalid_currency(currency):
    with pytest.raises(ValidationError):
        ProductCreate(
            sku="SKU-001",
            name="Wireless Mouse",
            current_price="29.99",
            currency=currency,
        )


def test_product_create_rejects_negative_price():
    with pytest.raises(ValidationError):
        ProductCreate(
            sku="SKU-001",
            name="Wireless Mouse",
            current_price="-1.00",
            currency="USD",
        )


def test_product_create_rejects_blank_name():
    with pytest.raises(ValidationError):
        ProductCreate(
            sku="SKU-001",
            name="   ",
            current_price="29.99",
            currency="USD",
        )
