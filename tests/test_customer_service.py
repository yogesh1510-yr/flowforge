import uuid

import pytest

from flowforge.services import customer as customer_service


def test_get_customer_delegates_to_repository(monkeypatch):
    customer_id = uuid.uuid4()
    expected_customer = object()

    def fake_get_customer(session, requested_id):
        assert requested_id == customer_id
        return expected_customer

    monkeypatch.setattr(
        customer_service.customer_repository,
        "get_customer_by_id",
        fake_get_customer,
    )

    result = customer_service.get_customer(
        session=None,
        customer_id=customer_id,
    )

    assert result is expected_customer


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_list_customers_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="limit"):
        customer_service.list_customers(
            session=None,
            limit=limit,
        )


def test_list_customers_rejects_negative_offset():
    with pytest.raises(ValueError, match="offset"):
        customer_service.list_customers(
            session=None,
            offset=-1,
        )
