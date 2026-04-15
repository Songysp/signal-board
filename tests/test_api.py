from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main
from app.main import app


def test_health_endpoint() -> None:
    assert app is not None
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_endpoint_returns_html() -> None:
    assert app is not None
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "SignalBoard" in response.text
    assert "감시 URL 등록" in response.text
    assert "검색 결과 변화" in response.text
    assert "renderAlerts" in response.text


def test_preview_search_endpoint_uses_configured_url(monkeypatch) -> None:
    class FakeNaverSearchClient:
        def fetch_listings(self, search_url):
            return []

    monkeypatch.setattr(main, "NaverSearchClient", FakeNaverSearchClient)

    assert app is not None
    response = TestClient(app).post("/preview-search", json={"limit": 1})

    assert response.status_code == 200
    assert "total" in response.json()


def test_watches_endpoint_returns_list(monkeypatch) -> None:
    monkeypatch.setattr(main, "list_watches", lambda: [])

    assert app is not None
    response = TestClient(app).get("/watches")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_alerts_endpoint_returns_list(monkeypatch) -> None:
    monkeypatch.setattr(main, "list_alert_events", lambda limit=50: [])

    assert app is not None
    response = TestClient(app).get("/alerts")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
