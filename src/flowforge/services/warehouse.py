from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from uuid import UUID

from flowforge.core.enums import WarehouseStatus
from flowforge.models import Warehouse
from flowforge.repositories import warehouse as warehouse_repository


class DuplicateWarehouseCodeError(Exception):
    """Raised when a warehouse code already exists."""


def get_warehouse(
    session: Session,
    warehouse_id: UUID,
) -> Warehouse | None:
    return warehouse_repository.get_warehouse_by_id(
        session,
        warehouse_id,
    )


def list_warehouses(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Warehouse]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")

    if offset < 0:
        raise ValueError("Offset must be non-negative")

    return warehouse_repository.list_warehouses(
        session,
        limit=limit,
        offset=offset,
    )


def create_warehouse(
    session: Session,
    *,
    code: str,
    name: str,
    address_line1: str,
    city: str,
    country_code: str,
    timezone: str,
    status: WarehouseStatus = WarehouseStatus.ACTIVE,
) -> Warehouse:
    normalized_code = code.strip().upper()

    existing = warehouse_repository.get_warehouse_by_code(
        session,
        normalized_code,
    )
    if existing is not None:
        raise DuplicateWarehouseCodeError(normalized_code)

    try:
        warehouse = warehouse_repository.create_warehouse(
            session,
            code=normalized_code,
            name=name.strip(),
            address_line1=address_line1.strip(),
            city=city.strip(),
            country_code=country_code.strip().upper(),
            timezone=timezone.strip(),
            status=status,
        )
        session.commit()
        return warehouse

    except IntegrityError as exc:
        session.rollback()

        # Handle a duplicate code caused by a concurrent request.
        existing = warehouse_repository.get_warehouse_by_code(
            session,
            normalized_code,
        )
        if existing is not None:
            raise DuplicateWarehouseCodeError(normalized_code) from exc

        # The integrity error was unrelated to a duplicate code.
        raise
