from unittest.mock import patch

from fastapi.testclient import TestClient

from flowforge.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "flowforge-api",
    }


def test_health_check_succeeds_when_database_is_unavailable() -> None:
    with patch(
        "flowforge.main.check_database_connection",
        return_value=False,
    ):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
