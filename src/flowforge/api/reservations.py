from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from flowforge.api.schemas.reservation import ReservationCreate, ReservationRead
from flowforge.db.session import get_db_session
from flowforge.services import reservation as reservation_service

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.get("", response_model=list[ReservationRead])
def list_reservations(
    inventory_id: UUID | None = None,
    order_item_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[ReservationRead]:
    reservations = reservation_service.list_reservations(
        session,
        inventory_id=inventory_id,
        order_item_id=order_item_id,
        limit=limit,
        offset=offset,
    )
    return TypeAdapter(list[ReservationRead]).validate_python(reservations)


@router.post("", response_model=ReservationRead, status_code=201)
def create_reservation(
    payload: ReservationCreate,
    session: Session = Depends(get_db_session),
) -> ReservationRead:
    try:
        reservation = reservation_service.create_reservation(
            session,
            order_item_id=payload.order_item_id,
            inventory_id=payload.inventory_id,
            quantity=payload.quantity,
            expires_at=payload.expires_at,
        )
    except reservation_service.ReservationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except reservation_service.InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except reservation_service.ReservationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Reservation conflicts with existing data",
        ) from exc

    return ReservationRead.model_validate(reservation)


@router.post("/{reservation_id}/release", response_model=ReservationRead)
def release_reservation(
    reservation_id: UUID,
    session: Session = Depends(get_db_session),
) -> ReservationRead:
    try:
        reservation = reservation_service.release_reservation(
            session,
            reservation_id,
        )
    except reservation_service.ReservationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except reservation_service.ReservationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ReservationRead.model_validate(reservation)


@router.post("/{reservation_id}/consume", response_model=ReservationRead)
def consume_reservation(
    reservation_id: UUID,
    session: Session = Depends(get_db_session),
) -> ReservationRead:
    try:
        reservation = reservation_service.consume_reservation(
            session,
            reservation_id,
        )
    except reservation_service.ReservationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except reservation_service.ReservationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ReservationRead.model_validate(reservation)
