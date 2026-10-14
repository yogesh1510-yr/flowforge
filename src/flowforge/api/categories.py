from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from flowforge.api.schemas.category import CategoryCreate, CategoryRead
from flowforge.db.session import get_db_session
from flowforge.services import category as category_service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[CategoryRead]:
    categories = category_service.list_categories(
        session,
        limit=limit,
        offset=offset,
    )
    return TypeAdapter(list[CategoryRead]).validate_python(categories)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: UUID,
    session: Session = Depends(get_db_session),
) -> CategoryRead:
    category = category_service.get_category(session, category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    return CategoryRead.model_validate(category)


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(
    payload: CategoryCreate,
    session: Session = Depends(get_db_session),
) -> CategoryRead:
    try:
        category = category_service.create_category(
            session,
            name=payload.name,
            slug=payload.slug,
            parent_id=payload.parent_id,
        )
    except category_service.DuplicateCategorySlugError as exc:
        raise HTTPException(
            status_code=409,
            detail="Category slug already exists",
        ) from exc
    except category_service.ParentCategoryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Parent category not found",
        ) from exc

    return CategoryRead.model_validate(category)
