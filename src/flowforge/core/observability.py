import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("flowforge.http")


import re
from uuid import uuid4

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def get_request_id(value: str | None) -> str:
    """Accept safe request IDs; generate one when missing or invalid."""
    if value and _REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid4())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = get_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
