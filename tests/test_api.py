from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main
from app.models import PollResult
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
    assert "loadWatchResults" in response.text
    assert "renderPreviewResults" in response.text
    assert "resultFilter" in response.text
    assert "applyResultFilter" in response.text
    assert "runWatchPoll" in response.text
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


def test_watch_results_endpoint_returns_list(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "list_current_results",
        lambda watch_id, limit=100: [
            (
                "complex:123",
                "complex",
                "테스트단지 단지 결과",
                "매매 5억~6억",
                "매매",
                "84~110㎡",
                None,
                "테스트단지",
                "https://fin.land.naver.com/complexes/123",
                3,
                "first",
                "last",
                "snapshot",
            )
        ],
    )

    assert app is not None
    response = TestClient(app).get("/watches/7/results")

    assert response.status_code == 200
    assert response.json()[0]["external_listing_id"] == "complex:123"
    assert response.json()[0]["result_count"] == 3


def test_poll_single_watch_endpoint(monkeypatch) -> None:
    class FakeAlertService:
        def __init__(self, notifier, slack_notifier=None):
            pass

        def poll_watch(self, watch_id, label, search_url):
            assert watch_id == 7
            assert label == "테스트"
            assert search_url == "resolved"
            return PollResult(
                watch_id=7,
                label="테스트",
                search_url="https://new.land.naver.com/",
                total_count=0,
                baseline_created=False,
                new_listings=[],
                changed_listings=[],
            )

    monkeypatch.setattr(main, "get_watch", lambda watch_id: (7, "테스트", "source", "resolved", True))
    monkeypatch.setattr(main, "AlertService", FakeAlertService)
    monkeypatch.setattr(main, "_build_notifier", lambda: object())
    monkeypatch.setattr(main, "_build_slack_notifier", lambda: None)

    assert app is not None
    response = TestClient(app).post("/watches/7/poll")

    assert response.status_code == 200
    assert response.json()["watch_id"] == 7


def test_poll_single_watch_rejects_inactive_watch(monkeypatch) -> None:
    monkeypatch.setattr(main, "get_watch", lambda watch_id: (7, "테스트", "source", "resolved", False))

    assert app is not None
    response = TestClient(app).post("/watches/7/poll")

    assert response.status_code == 400
