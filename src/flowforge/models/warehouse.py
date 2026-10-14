"""SQLAlchemy models for the FlowForge platform."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge.db.base import Base
from flowforge.core.enums import (
    CustomerStatus,
    InventoryMovementType,
    OrderStatus,
    ProductStatus,
    ReservationStatus,
    WarehouseStatus,
)


def enum_values(enum_class: type) -> str:
    """Return enum values as a SQL-safe, quoted list."""
    return ", ".join(
        "'" + str(member.value).replace("'", "''") + "'"
        for member in enum_class
    )


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(250), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country_code: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[WarehouseStatus] = mapped_column(
        String(20),
        default=WarehouseStatus.ACTIVE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    inventory_records: Mapped[list["Inventory"]] = relationship(
        back_populates="warehouse"
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_values(WarehouseStatus)})", name="ck_warehouses_status"
        ),
    )

