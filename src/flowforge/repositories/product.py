from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowforge.models import Product,ProductCategory
from decimal import Decimal
from flowforge.core.enums import ProductStatus


def get_product_by_id(
    session: Session,
    product_id: UUID,
) -> Product | None:
    """Return a product by ID, or None if not found."""
    statement = select(Product).where(Product.id == product_id)
    return session.scalar(statement)


def get_product_by_sku(
    session: Session,
    sku: str,
) -> Product | None:
    """Return a product by SKU, or None if not found."""
    statement = select(Product).where(Product.sku == sku)
    return session.scalar(statement)


def list_products(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Product]:
    """Return a page of products."""
    statement = select(Product).order_by(Product.id).limit(limit).offset(offset)
    return list(session.scalars(statement).all())



def get_category_by_id(
    session: Session,
    category_id: UUID,
) -> ProductCategory | None:
    """Return a category by ID, or None if not found."""
    statement = select(ProductCategory).where(
        ProductCategory.id == category_id
    )
    return session.scalar(statement)


def create_product(
    session: Session,
    *,
    sku: str,
    name: str,
    description: str | None,
    category_id: UUID | None,
    current_price: Decimal,
    currency: str,
    status: ProductStatus,
) -> Product:
    """Add a product to the current transaction."""
    product = Product(
        sku=sku,
        name=name,
        description=description,
        category_id=category_id,
        current_price=current_price,
        currency=currency,
        status=status,
    )
    session.add(product)
    session.flush()
    return product

