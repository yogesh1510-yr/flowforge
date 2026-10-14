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


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[CustomerStatus] = mapped_column(
        String(20),
        default=CustomerStatus.ACTIVE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    addresses: Mapped[list["CustomerAddress"]] = relationship(back_populates="customer")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_values(CustomerStatus)})", name="ck_customers_status"
        ),
        Index("uq_customers_email_lower", func.lower(email), unique=True),
    )


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    label: Mapped[str | None] = mapped_column(String(50))
    recipient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(250), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(250))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state_region: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country_code: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    customer: Mapped["Customer"] = relationship(back_populates="addresses")


# ---------------------------------------------------------------------------
# Product catalog
# ---------------------------------------------------------------------------

