from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    assert app is not None
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_preview_search_endpoint_uses_configured_url() -> None:
    assert app is not None
    response = TestClient(app).post("/preview-search", json={"limit": 1})

    assert response.status_code == 200
    assert "total" in response.json()


def test_watches_endpoint_returns_list() -> None:
    assert app is not None
    response = TestClient(app).get("/watches")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_alerts_endpoint_returns_list() -> None:
    assert app is not None
    response = TestClient(app).get("/alerts")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
