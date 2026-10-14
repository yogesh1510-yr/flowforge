from uuid import UUID
from pydantic import TypeAdapter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from flowforge.db.session import get_db_session
from flowforge.services import customer as customer_service
from flowforge.api.schemas.customer import CustomerCreate, CustomerRead
from flowforge.services.customer import DuplicateCustomerEmailError

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[CustomerRead]:
    customers = customer_service.list_customers(
        session,
        limit=limit,
        offset=offset,
    )

    return TypeAdapter(list[CustomerRead]).validate_python(customers)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: UUID,
    session: Session = Depends(get_db_session),
) -> CustomerRead:
    customer = customer_service.get_customer(session, customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return CustomerRead.model_validate(customer)


@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(
    payload: CustomerCreate,
    session: Session = Depends(get_db_session),
) -> CustomerRead:
    try:
        customer = customer_service.create_customer(
            session,
            email=payload.email,
            full_name=payload.full_name,
            phone=payload.phone,
        )
    except DuplicateCustomerEmailError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return CustomerRead.model_validate(customer)
