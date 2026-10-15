from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from flowforge.api.schemas.order import (
    OrderCreate,
    OrderRead,
    OrderStatusUpdate,
    OrderEventRead,
)
from flowforge.db.session import get_db_session
from flowforge.services import order as order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=list[OrderRead])
def list_orders(
    customer_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[OrderRead]:
    orders = order_service.list_orders(
        session,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )
    return TypeAdapter(list[OrderRead]).validate_python(orders)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: UUID,
    session: Session = Depends(get_db_session),
) -> OrderRead:
    order = order_service.get_order(session, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderRead.model_validate(order)


@router.post("", response_model=OrderRead, status_code=201)
def create_order(
    payload: OrderCreate,
    session: Session = Depends(get_db_session),
) -> OrderRead:
    try:
        order = order_service.create_order(
            session,
            customer_id=payload.customer_id,
            currency=payload.currency,
            shipping_address_snapshot=payload.shipping_address_snapshot,
            items=[item.model_dump() for item in payload.items],
            tax_amount=payload.tax_amount,
            shipping_amount=payload.shipping_amount,
            discount_amount=payload.discount_amount,
        )
    except order_service.OrderValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Order conflicts with existing data",
        ) from exc

    return OrderRead.model_validate(order)


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    session: Session = Depends(get_db_session),
) -> OrderRead:
    try:
        order = order_service.update_order_status(
            session,
            order_id,
            payload.status,
        )
    except order_service.OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc
    except order_service.InvalidOrderTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Order conflict") from exc

    return OrderRead.model_validate(order)


@router.get("/{order_id}/events", response_model=list[OrderEventRead])
def get_order_events(
    order_id: UUID,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[OrderEventRead]:
    try:
        events = order_service.list_order_events(
            session,
            order_id,
            limit=limit,
            offset=offset,
        )
    except order_service.OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Order not found") from exc

    return TypeAdapter(list[OrderEventRead]).validate_python(events)
