from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock
from sqlalchemy.orm import Session

import pytest

from flowforge.services import product as product_service


def test_create_product_rejects_duplicate_sku(monkeypatch):
    monkeypatch.setattr(
        product_service.product_repository,
        "get_product_by_sku",
        lambda session, sku: object(),
    )

    with pytest.raises(product_service.DuplicateProductSKUError):
        product_service.create_product(
            session=Mock(spec=Session),
            sku="SKU-001",
            name="Wireless Mouse",
            current_price=Decimal("29.99"),
            currency="USD",
        )


def test_create_product_rejects_missing_category(monkeypatch):
    monkeypatch.setattr(
        product_service.product_repository,
        "get_product_by_sku",
        lambda session, sku: None,
    )
    monkeypatch.setattr(
        product_service.product_repository,
        "get_category_by_id",
        lambda session, category_id: None,
    )

    with pytest.raises(product_service.ProductCategoryNotFoundError):
        product_service.create_product(
            session=Mock(spec=Session),
            sku="SKU-001",
            name="Wireless Mouse",
            current_price=Decimal("29.99"),
            currency="USD",
            category_id=uuid4(),
        )
