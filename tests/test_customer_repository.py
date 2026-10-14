import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from flowforge.db.base import Base
from flowforge.models import Customer
from flowforge.repositories.customer import (
    get_customer_by_id,
    list_customers,
)


def create_test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_get_customer_by_id_returns_customer():
    with create_test_session() as session:
        customer = Customer(
            email="alice@example.com",
            full_name="Alice Smith",
        )
        session.add(customer)
        session.commit()

        result = get_customer_by_id(session, customer.id)

        assert result is not None
        assert result.id == customer.id
        assert result.email == "alice@example.com"


def test_get_customer_by_id_returns_none_for_missing_customer():
    with create_test_session() as session:
        result = get_customer_by_id(session, uuid.uuid4())

        assert result is None


def test_list_customers_supports_pagination():
    with create_test_session() as session:
        session.add_all(
            [
                Customer(email="alice@example.com", full_name="Alice"),
                Customer(email="bob@example.com", full_name="Bob"),
                Customer(email="carol@example.com", full_name="Carol"),
            ]
        )
        session.commit()

        first_page = list_customers(session, limit=2, offset=0)
        second_page = list_customers(session, limit=2, offset=2)

        assert len(first_page) == 2
        assert len(second_page) == 1
        assert len({customer.id for customer in first_page + second_page}) == 3
