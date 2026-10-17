from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from flowforge.api.schemas.order_intelligence import OrderIntelligenceRead
from flowforge.db.session import get_db_session
from flowforge.repositories import order_intelligence as repository
from flowforge.api.schemas.order_intelligence_summary import (
    OrderIntelligenceSummary,
)

router = APIRouter(
    prefix="/order-intelligence",
    tags=["Order Intelligence"],
)


@router.get("/by-id/{order_id}", response_model=OrderIntelligenceRead)
def get_order_intelligence_by_id(
    order_id: UUID,
    session: Session = Depends(get_db_session),
) -> OrderIntelligenceRead:
    record = repository.get_by_id(session, order_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order intelligence record not found",
        )
    return OrderIntelligenceRead.model_validate(record)


@router.get("/by-number/{order_number}", response_model=OrderIntelligenceRead)
def get_order_intelligence_by_number(
    order_number: str,
    session: Session = Depends(get_db_session),
) -> OrderIntelligenceRead:
    record = repository.get_by_number(session, order_number)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order intelligence record not found",
        )
    return OrderIntelligenceRead.model_validate(record)


@router.get("", response_model=list[OrderIntelligenceRead])
def list_order_intelligence(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        min_length=1,
        max_length=30,
    ),
    order_number: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    session: Session = Depends(get_db_session),
) -> list[OrderIntelligenceRead]:
    records = repository.list_orders(
        session,
        limit=limit,
        offset=offset,
        status=status_filter,
        order_number=order_number,
    )
    return [OrderIntelligenceRead.model_validate(record) for record in records]


@router.get("/summary", response_model=OrderIntelligenceSummary)
def get_order_intelligence_summary(
    session: Session = Depends(get_db_session),
) -> OrderIntelligenceSummary:
    summary = repository.get_summary(session)
    return OrderIntelligenceSummary.model_validate(summary)
