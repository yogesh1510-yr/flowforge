from uuid import UUID

from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError

from flowforge.models import Customer
from flowforge.repositories import customer as customer_repository


def get_customer(
    session: Session,
    customer_id: UUID,
) -> Customer | None:
    """Retrieve a customer by ID."""
    return customer_repository.get_customer_by_id(
        session,
        customer_id,
    )


def list_customers(
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Customer]:
    """Retrieve a paginated list of customers."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    if offset < 0:
        raise ValueError("offset must be non-negative")

    return customer_repository.list_customers(
        session,
        limit=limit,
        offset=offset,
    )


class DuplicateCustomerEmailError(Exception):
    """Raised when a customer email is already registered."""


def create_customer(
    session: Session,
    *,
    email: str,
    full_name: str,
    phone: str | None = None,
) -> Customer:
    normalized_email = email.strip().lower()

    if customer_repository.get_customer_by_email(
        session,
        normalized_email,
    ):
        raise DuplicateCustomerEmailError("A customer with this email already exists")

    try:
        customer = customer_repository.create_customer(
            session,
            email=normalized_email,
            full_name=full_name.strip(),
            phone=phone.strip() if phone else None,
        )
        session.commit()
        return customer
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateCustomerEmailError(
            "A customer with this email already exists"
        ) from exc
