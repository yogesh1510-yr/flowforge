import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowforge.core.observability import RequestLoggingMiddleware


@pytest.fixture
def app_with_logging() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"ok": True}

    @app.get("/failure")
    def failing_endpoint():
        raise RuntimeError("test failure")

    return app


def test_request_id_is_returned(
    app_with_logging: FastAPI,
) -> None:
    with TestClient(app_with_logging) as client:
        response = client.get("/test")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_supplied_request_id_is_preserved(
    app_with_logging: FastAPI,
) -> None:
    request_id = "test-request-123"

    with TestClient(app_with_logging) as client:
        response = client.get(
            "/test",
            headers={"X-Request-ID": request_id},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_request_completion_is_logged(
    app_with_logging: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="flowforge.http"):
        with TestClient(app_with_logging) as client:
            response = client.get("/test")

    assert response.status_code == 200
    assert "request_completed" in caplog.text

    record = next(
        (
            item
            for item in caplog.records
            if item.name == "flowforge.http"
            and item.getMessage() == "request_completed"
        ),
        None,
    )

    assert record is not None
    assert getattr(record, "request_id", None)
    assert getattr(record, "method", None) == "GET"
    assert getattr(record, "path", None) == "/test"
    assert getattr(record, "status_code", None) == 200
    assert getattr(record, "duration_ms", -1) >= 0


def test_unhandled_error_is_logged(
    app_with_logging: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="flowforge.http"):
        with TestClient(app_with_logging) as client:
            with pytest.raises(RuntimeError, match="test failure"):
                client.get("/failure")

    assert "request_failed" in caplog.text
    assert "test failure" in caplog.text


def test_invalid_request_id_is_replaced(
    app_with_logging: FastAPI,
) -> None:
    with TestClient(app_with_logging) as client:
        response = client.get(
            "/test",
            headers={"X-Request-ID": "bad request\ninjected"},
        )

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert request_id != "bad request\ninjected"
    assert len(request_id) <= 128


def test_overlong_request_id_is_replaced(
    app_with_logging: FastAPI,
) -> None:
    with TestClient(app_with_logging) as client:
        response = client.get(
            "/test",
            headers={"X-Request-ID": "a" * 129},
        )

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert request_id != "a" * 129
    assert len(request_id) <= 128
