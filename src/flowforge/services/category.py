from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from flowforge.models import ProductCategory
from flowforge.repositories import category as category_repository


class DuplicateCategorySlugError(Exception):
    """Raised when a category slug is already in use."""


class ParentCategoryNotFoundError(Exception):
    """Raised when the requested parent category does not exist."""


def get_category(
    session: Session,
    category_id: UUID,
) -> ProductCategory | None:
    return category_repository.get_category_by_id(
        session,
        category_id,
    )


def list_categories(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[ProductCategory]:
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")

    if offset < 0:
        raise ValueError("Offset must be non-negative")

    return category_repository.list_categories(
        session,
        limit=limit,
        offset=offset,
    )


def create_category(
    session: Session,
    *,
    name: str,
    slug: str,
    parent_id: UUID | None = None,
) -> ProductCategory:
    normalized_name = name.strip()
    normalized_slug = slug.strip()

    existing = category_repository.get_category_by_slug(
        session,
        normalized_slug,
    )
    if existing is not None:
        raise DuplicateCategorySlugError(normalized_slug)

    if parent_id is not None:
        parent = category_repository.get_category_by_id(
            session,
            parent_id,
        )
        if parent is None:
            raise ParentCategoryNotFoundError(str(parent_id))

    try:
        category = category_repository.create_category(
            session,
            name=normalized_name,
            slug=normalized_slug,
            parent_id=parent_id,
        )
        session.commit()
        return category

    except IntegrityError as exc:
        session.rollback()

        # Handle a duplicate slug caused by a concurrent request.
        existing = category_repository.get_category_by_slug(
            session,
            normalized_slug,
        )
        if existing is not None:
            raise DuplicateCategorySlugError(normalized_slug) from exc

        # Handle a parent category deleted by another transaction.
        if parent_id is not None:
            parent = category_repository.get_category_by_id(
                session,
                parent_id,
            )
            if parent is None:
                raise ParentCategoryNotFoundError(
                    str(parent_id)
                ) from exc

        raise
