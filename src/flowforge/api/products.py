from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from flowforge.api.schemas.product import ProductCreate, ProductRead
from flowforge.db.session import get_db_session
from flowforge.services import product as product_service

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductRead])
def list_products(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[ProductRead]:
    products = product_service.list_products(
        session,
        limit=limit,
        offset=offset,
    )
    return TypeAdapter(list[ProductRead]).validate_python(products)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: UUID,
    session: Session = Depends(get_db_session),
) -> ProductRead:
    product = product_service.get_product(session, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return ProductRead.model_validate(product)


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    session: Session = Depends(get_db_session),
) -> ProductRead:
    try:
        product = product_service.create_product(
            session,
            sku=payload.sku,
            name=payload.name,
            description=payload.description,
            category_id=payload.category_id,
            current_price=payload.current_price,
            currency=payload.currency,
            status=payload.status,
        )
    except product_service.DuplicateProductSKUError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except product_service.ProductCategoryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return ProductRead.model_validate(product)
