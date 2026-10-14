from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowforge.models import ProductCategory


def get_category_by_id(
    session: Session,
    category_id: UUID,
) -> ProductCategory | None:
    statement = select(ProductCategory).where(ProductCategory.id == category_id)
    return session.scalar(statement)


def get_category_by_slug(
    session: Session,
    slug: str,
) -> ProductCategory | None:
    statement = select(ProductCategory).where(ProductCategory.slug == slug)
    return session.scalar(statement)


def list_categories(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[ProductCategory]:
    statement = (
        select(ProductCategory)
        .order_by(ProductCategory.name, ProductCategory.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())


def create_category(
    session: Session,
    *,
    name: str,
    slug: str,
    parent_id: UUID | None = None,
) -> ProductCategory:
    category = ProductCategory(
        name=name,
        slug=slug,
        parent_id=parent_id,
    )
    session.add(category)
    session.flush()
    return category
