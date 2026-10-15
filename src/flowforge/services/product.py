from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from flowforge.core.enums import ProductStatus
from flowforge.models import Product
from flowforge.repositories import product as product_repository


def get_product(
    session: Session,
    product_id: UUID,
) -> Product | None:
    """Retrieve a product by ID."""
    return product_repository.get_product_by_id(
        session,
        product_id,
    )


def list_products(
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:
    """Retrieve a paginated list of products."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    if offset < 0:
        raise ValueError("offset must be non-negative")

    return product_repository.list_products(
        session,
        limit=limit,
        offset=offset,
    )


class DuplicateProductSKUError(Exception):
    """Raised when a product SKU already exists."""


class ProductCategoryNotFoundError(Exception):
    """Raised when the requested category does not exist."""


def create_product(
    session: Session,
    *,
    sku: str,
    name: str,
    description: str | None = None,
    category_id: UUID | None = None,
    current_price: Decimal,
    currency: str,
    status: ProductStatus = ProductStatus.ACTIVE,
) -> Product:
    normalized_sku = sku.strip()
    normalized_name = name.strip()

    if product_repository.get_product_by_sku(session, normalized_sku):
        raise DuplicateProductSKUError("A product with this SKU already exists")

    if category_id is not None:
        category = product_repository.get_category_by_id(
            session,
            category_id,
        )
        if category is None:
            raise ProductCategoryNotFoundError("Product category not found")

    try:
        product = product_repository.create_product(
            session,
            sku=normalized_sku,
            name=normalized_name,
            description=description.strip() if description else None,
            category_id=category_id,
            current_price=current_price,
            currency=currency,
            status=status,
        )
        session.commit()
        return product

    except IntegrityError as exc:
        session.rollback()

        # The database constraint is the final safeguard against
        # two concurrent requests creating the same SKU.
        if product_repository.get_product_by_sku(session, normalized_sku):
            raise DuplicateProductSKUError(
                "A product with this SKU already exists"
            ) from exc

        if (
            category_id is not None
            and product_repository.get_category_by_id(session, category_id) is None
        ):
            raise ProductCategoryNotFoundError("Product category not found") from exc

        # Do not misreport unrelated integrity violations as duplicates.
        raise
