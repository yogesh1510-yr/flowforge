from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from flowforge.api.schemas.dashboard import (
    DashboardSummary,
    LowStockItem,
    RecentMovement,
)
from flowforge.db.session import get_db_session
from flowforge.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    session: Session = Depends(get_db_session),
):
    return dashboard_service.get_summary(session)


@router.get("/low-stock", response_model=list[LowStockItem])
def get_dashboard_low_stock(
    threshold: int = Query(default=5, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_db_session),
):
    return dashboard_service.get_low_stock(
        session,
        threshold=threshold,
        limit=limit,
    )


@router.get(
    "/recent-movements",
    response_model=list[RecentMovement],
)
def get_dashboard_recent_movements(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db_session),
):
    return dashboard_service.get_recent_movements(
        session,
        limit=limit,
    )
