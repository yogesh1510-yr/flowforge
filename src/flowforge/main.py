from fastapi import FastAPI, HTTPException

from flowforge.db.engine import check_database_connection

app = FastAPI(
    title="FlowForge",
    description="Real-Time Order Intelligence Platform",
    version="0.1.0",
)


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
