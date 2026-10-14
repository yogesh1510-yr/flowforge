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


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    parent: Mapped["ProductCategory | None"] = relationship(
        back_populates="children", remote_side="ProductCategory.id"
    )
    children: Mapped[list["ProductCategory"]] = relationship(back_populates="parent")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="RESTRICT"),
    )
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        String(20),
        default=ProductStatus.ACTIVE,
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

    category: Mapped["ProductCategory | None"] = relationship(back_populates="products")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")
    inventory_records: Mapped[list["Inventory"]] = relationship(
        back_populates="product"
    )

    __table_args__ = (
        CheckConstraint("current_price >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint(
            f"status IN ({enum_values(ProductStatus)})", name="ck_products_status"
        ),
    )


# ---------------------------------------------------------------------------
# Warehouses and inventory
# ---------------------------------------------------------------------------

