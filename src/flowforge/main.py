from fastapi import FastAPI, HTTPException, Depends

from flowforge.db.engine import check_database_connection, dispose_database_engine

from sqlalchemy import text
from sqlalchemy.orm import Session

from flowforge.db.session import get_db_session
from flowforge.api.customers import router as customers_router
from flowforge.api.products import router as products_router
from flowforge.api.categories import router as categories_router
from flowforge.api.warehouses import router as warehouses_router
from flowforge.api.inventory import router as inventory_router
from flowforge.api.reservations import router as reservations_router
from flowforge.api.orders import router as orders_router
from flowforge.api.order_intelligence import router as order_intelligence_router
from flowforge.api.fulfillment import router as fulfillment_router
from flowforge.api.dashboard import router as dashboard_router
from flowforge.core.observability import RequestLoggingMiddleware

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import os

import logging


class RequestContextDefaults(logging.Filter):
    """Ensure every log record has the fields expected by our formatter."""

    def filter(self, record: logging.LogRecord) -> bool:
        defaults = {
            "request_id": "-",
            "method": "-",
            "path": "-",
            "status_code": "-",
            "duration_ms": "-",
        }

        for field, default in defaults.items():
            if not hasattr(record, field):
                setattr(record, field, default)

        return True


handler = logging.StreamHandler()
handler.addFilter(RequestContextDefaults())
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s "
        "request_id=%(request_id)s method=%(method)s "
        "path=%(path)s status_code=%(status_code)s "
        "duration_ms=%(duration_ms)s"
    )
)

logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        dispose_database_engine()


docs_enabled = os.getenv("FLOWFORGE_ENV", "dev").strip().lower() != "prod"

app = FastAPI(
    title="FlowForge",
    description="Real-Time Order Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

app.include_router(customers_router)
app.include_router(products_router)
app.include_router(categories_router)
app.include_router(warehouses_router)
app.include_router(inventory_router)
app.include_router(reservations_router)
app.include_router(orders_router)
app.include_router(order_intelligence_router)
app.include_router(fulfillment_router)
app.include_router(dashboard_router)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "flowforge-api",
    }


@app.get("/ready", tags=["Health"])
def readiness_check() -> dict[str, str]:
    if not check_database_connection():
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        )

    return {
        "status": "ready",
        "database": "connected",
    }


@app.get("/db-check")
def db_check(
    session: Session = Depends(get_db_session),
) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database query failed",
        ) from exc
