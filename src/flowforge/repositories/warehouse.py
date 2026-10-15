from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowforge.models import Warehouse
from flowforge.core.enums import WarehouseStatus


def get_warehouse_by_id(
    session: Session,
    warehouse_id: UUID,
) -> Warehouse | None:
    statement = select(Warehouse).where(Warehouse.id == warehouse_id)
    return session.scalar(statement)


def get_warehouse_by_code(
    session: Session,
    code: str,
) -> Warehouse | None:
    statement = select(Warehouse).where(Warehouse.code == code)
    return session.scalar(statement)


def list_warehouses(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Warehouse]:
    statement = (
        select(Warehouse)
        .order_by(Warehouse.code, Warehouse.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())


def create_warehouse(
    session: Session,
    *,
    code: str,
    name: str,
    address_line1: str,
    city: str,
    country_code: str,
    timezone: str,
    status:WarehouseStatus,
) -> Warehouse:
    warehouse = Warehouse(
        code=code,
        name=name,
        address_line1=address_line1,
        city=city,
        country_code=country_code,
        timezone=timezone,
        status=status,
    )
    session.add(warehouse)
    session.flush()
    return warehouse
