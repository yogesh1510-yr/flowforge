from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from flowforge.api.schemas.warehouse import WarehouseCreate, WarehouseRead
from flowforge.db.session import get_db_session
from flowforge.services import warehouse as warehouse_service

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


@router.get("", response_model=list[WarehouseRead])
def list_warehouses(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[WarehouseRead]:
    warehouses = warehouse_service.list_warehouses(
        session,
        limit=limit,
        offset=offset,
    )
    return TypeAdapter(list[WarehouseRead]).validate_python(warehouses)


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(
    warehouse_id: UUID,
    session: Session = Depends(get_db_session),
) -> WarehouseRead:
    warehouse = warehouse_service.get_warehouse(
        session,
        warehouse_id,
    )

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found",
        )

    return WarehouseRead.model_validate(warehouse)


@router.post("", response_model=WarehouseRead, status_code=201)
def create_warehouse(
    payload: WarehouseCreate,
    session: Session = Depends(get_db_session),
) -> WarehouseRead:
    try:
        warehouse = warehouse_service.create_warehouse(
            session,
            code=payload.code,
            name=payload.name,
            address_line1=payload.address_line1,
            city=payload.city,
            country_code=payload.country_code,
            timezone=payload.timezone,
            status=payload.status,
        )
    except warehouse_service.DuplicateWarehouseCodeError as exc:
        raise HTTPException(
            status_code=409,
            detail="Warehouse code already exists",
        ) from exc

    return WarehouseRead.model_validate(warehouse)
