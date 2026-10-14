from fastapi import FastAPI, HTTPException, Depends

from flowforge.db.engine import check_database_connection

from sqlalchemy import text
from sqlalchemy.orm import Session

from flowforge.db.session import get_db_session
from flowforge.api.customers import router as customers_router
from flowforge.api.products import router as products_router
from flowforge.api.categories import router as categories_router

app = FastAPI(
    title="FlowForge",
    description="Real-Time Order Intelligence Platform",
    version="0.1.0",
)

app.include_router(customers_router)
app.include_router(products_router)
app.include_router(categories_router)


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