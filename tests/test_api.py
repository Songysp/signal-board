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
    assert "setWatchActive" in response.text
    assert "현재 결과" in response.text
    assert "관리 토큰" in response.text


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
    monkeypatch.setattr(
        main,
        "list_watches",
        lambda: [
            (
                7,
                "테스트",
                "https://new.land.naver.com/",
                "new.land.legacy",
                "https://new.land.naver.com/",
                True,
                "created",
                "checked",
                20,
                3,
            )
        ],
    )

    assert app is not None
    response = TestClient(app).get("/watches")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["current_result_count"] == 20
    assert response.json()[0]["alert_event_count"] == 3


def test_update_watch_active_endpoint(monkeypatch) -> None:
    calls = []

    def fake_set_watch_active(watch_id, is_active):
        calls.append((watch_id, is_active))
        return True

    monkeypatch.setattr(main, "set_watch_active", fake_set_watch_active)

    assert app is not None
    response = TestClient(app).patch("/watches/7/active", json={"is_active": False})

    assert response.status_code == 200
    assert response.json() == {"id": 7, "is_active": False}
    assert calls == [(7, False)]


def test_write_endpoint_requires_admin_token_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "admin_token", "secret")
    monkeypatch.setattr(main, "add_watch", lambda label, search_url: 1)

    assert app is not None
    response = TestClient(app).post(
        "/watches",
        json={"label": "테스트", "search_url": "https://new.land.naver.com/"},
    )

    assert response.status_code == 401


def test_write_endpoint_accepts_admin_token_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "admin_token", "secret")
    monkeypatch.setattr(main, "add_watch", lambda label, search_url: 1)

    assert app is not None
    response = TestClient(app).post(
        "/watches",
        headers={"X-SignalBoard-Token": "secret"},
        json={"label": "테스트", "search_url": "https://new.land.naver.com/"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": 1}


def test_update_watch_active_endpoint_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(main, "set_watch_active", lambda watch_id, is_active: False)

    assert app is not None
    response = TestClient(app).patch("/watches/999/active", json={"is_active": False})

    assert response.status_code == 404


def test_alerts_endpoint_returns_list(monkeypatch) -> None:
    monkeypatch.setattr(main, "list_alert_events", lambda limit=50: [])

    assert app is not None
    response = TestClient(app).get("/alerts")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
