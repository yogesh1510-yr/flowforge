import pytest

from flowforge.services import product as product_service


def test_get_product_delegates_to_repository(monkeypatch):
    expected_product = object()

    def fake_get_product(session, product_id):
        return expected_product

    monkeypatch.setattr(
        product_service.product_repository,
        "get_product_by_id",
        fake_get_product,
    )

    result = product_service.get_product(
        session=None,
        product_id=None,
    )

    assert result is expected_product


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_list_products_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="limit"):
        product_service.list_products(
            session=None,
            limit=limit,
        )


def test_list_products_rejects_negative_offset():
    with pytest.raises(ValueError, match="offset"):
        product_service.list_products(
            session=None,
            offset=-1,
        )
