from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flowforge.models import Customer


def get_customer_by_id(
    session: Session,
    customer_id: UUID,
) -> Customer | None:
    """Return a customer by ID, or None if not found."""
    statement = select(Customer).where(Customer.id == customer_id)
    return session.scalar(statement)


def list_customers(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Customer]:
    """Return a page of customers."""
    statement = select(Customer).order_by(Customer.id).limit(limit).offset(offset)
    return list(session.scalars(statement).all())


def get_customer_by_email(
    session: Session,
    email: str,
) -> Customer | None:
    statement = select(Customer).where(
        func.lower(Customer.email) == email.strip().lower()
    )
    return session.scalar(statement)


def create_customer(
    session: Session,
    *,
    email: str,
    full_name: str,
    phone: str | None = None,
) -> Customer:
    customer = Customer(
        email=email,
        full_name=full_name,
        phone=phone,
    )
    session.add(customer)
    session.flush()
    return customer
