from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


from flowforge.db.session import get_db_session
from flowforge.api.schemas.inventory import (
    StockTransfer,
    StockTransferResult,
)
from flowforge.services.inventory import (
    InventoryNotFoundError,
    StockConflictError,
    transfer_stock,
)

from flowforge.api.schemas.inventory import (
    InventoryMovementRead,
    InventoryRead,
    StockAdjustment,
    StockReceipt,
)
from flowforge.db.session import get_db_session
from flowforge.services import inventory as inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=list[InventoryRead])
def list_inventory(
    warehouse_id: UUID | None = None,
    product_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[InventoryRead]:
    records = inventory_service.list_inventory(
        session,
        warehouse_id=warehouse_id,
        product_id=product_id,
        limit=limit,
        offset=offset,
    )
    return TypeAdapter(list[InventoryRead]).validate_python(records)


@router.get(
    "/{inventory_id}/movements",
    response_model=list[InventoryMovementRead],
)
def get_inventory_movements(
    inventory_id: UUID,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[InventoryMovementRead]:
    try:
        movements = inventory_service.list_movements(
            session,
            inventory_id,
            limit=limit,
            offset=offset,
        )
    except inventory_service.InventoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Inventory not found") from exc

    return TypeAdapter(list[InventoryMovementRead]).validate_python(movements)


@router.post("/receipts", response_model=InventoryRead)
def receive_stock(
    payload: StockReceipt,
    session: Session = Depends(get_db_session),
) -> InventoryRead:
    try:
        inventory = inventory_service.receive_stock(
            session,
            warehouse_id=payload.warehouse_id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            reason=payload.reason,
        )
    except inventory_service.RelatedResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Inventory conflict; retry the request",
        ) from exc

    return InventoryRead.model_validate(inventory)


@router.post("/adjustments", response_model=InventoryRead)
def adjust_stock(
    payload: StockAdjustment,
    session: Session = Depends(get_db_session),
) -> InventoryRead:
    try:
        inventory = inventory_service.adjust_stock(
            session,
            inventory_id=payload.inventory_id,
            quantity_delta=payload.quantity_delta,
            reason=payload.reason,
        )
    except inventory_service.InventoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Inventory not found") from exc
    except inventory_service.StockConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Inventory conflict") from exc

    return InventoryRead.model_validate(inventory)


@router.post(
    "/transfers",
    response_model=StockTransferResult,
    status_code=201,
)
def transfer_inventory_stock(
    payload: StockTransfer,
    session: Session = Depends(get_db_session),
):
    try:
        return transfer_stock(
            session=session,
            source_warehouse_id=payload.source_warehouse_id,
            destination_warehouse_id=payload.destination_warehouse_id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            reason=payload.reason,
        )
    except InventoryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except StockConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
