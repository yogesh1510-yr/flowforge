from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from flowforge.api.schemas.order import OrderRead
from flowforge.db.session import get_db_session
from flowforge.services import fulfillment as fulfillment_service

router = APIRouter(prefix="/orders", tags=["Fulfillment"])


def _handle_fulfillment_error(exc: Exception) -> HTTPException:
    if isinstance(exc, fulfillment_service.FulfillmentOrderNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))

    if isinstance(exc, fulfillment_service.InsufficientInventoryError):
        return HTTPException(status_code=409, detail=str(exc))

    if isinstance(exc, fulfillment_service.FulfillmentConflictError):
        return HTTPException(status_code=409, detail=str(exc))

    return HTTPException(status_code=409, detail="Fulfillment conflict")


@router.post("/{order_id}/confirm", response_model=OrderRead)
def confirm_order(
    order_id: UUID,
    session: Session = Depends(get_db_session),
) -> OrderRead:
    try:
        order = fulfillment_service.confirm_order(session, order_id)
    except fulfillment_service.FulfillmentError as exc:
        raise _handle_fulfillment_error(exc) from exc

    return OrderRead.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: UUID,
    session: Session = Depends(get_db_session),
) -> OrderRead:
    try:
        order = fulfillment_service.cancel_order(session, order_id)
    except fulfillment_service.FulfillmentError as exc:
        raise _handle_fulfillment_error(exc) from exc

    return OrderRead.model_validate(order)


@router.post("/{order_id}/ship", response_model=OrderRead)
def ship_order(
    order_id: UUID,
    session: Session = Depends(get_db_session),
) -> OrderRead:
    try:
        order = fulfillment_service.ship_order(session, order_id)
    except fulfillment_service.FulfillmentError as exc:
        raise _handle_fulfillment_error(exc) from exc

    return OrderRead.model_validate(order)
