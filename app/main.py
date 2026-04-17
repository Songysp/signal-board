from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.alerts import AlertService
from app.config import settings
from app.kakao_notifier import KakaoMessageError, KakaoNotifier
from app.kakao_tokens import KakaoTokenManager
from app.naver import NaverFetchError, NaverSearchClient
from app.storage import add_watch, get_watch, list_alert_events, list_current_results, list_watches, set_watch_active
from app.web import render_dashboard

try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = object  # type: ignore[assignment]

    def Field(default=None, **_: Any):  # type: ignore[no-redef]
        return default


class WatchCreate(BaseModel):
    label: str = Field(min_length=1)
    search_url: str = Field(min_length=1)


class PreviewRequest(BaseModel):
    search_url: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class KakaoTestRequest(BaseModel):
    message: str = "[부동산알리미] SignalBoard API 알림 테스트\n카카오 나에게 메시지 연결이 정상입니다."


class WatchActiveUpdate(BaseModel):
    is_active: bool


def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


def create_app() -> Any:
    try:
        from fastapi import Depends, FastAPI, Header, HTTPException
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install API dependencies first: python -m pip install -e .[api]") from exc

    api = FastAPI(title=settings.app_name, version="0.1.0")

    def require_admin_token(x_signalboard_token: str | None = Header(default=None)) -> None:
        if not settings.admin_token:
            return
        if x_signalboard_token != settings.admin_token:
            raise HTTPException(status_code=401, detail="admin token required")

    @api.get("/health")
    def api_health() -> dict[str, str]:
        return health()

    @api.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return render_dashboard()

    @api.get("/watches")
    def get_watches() -> list[dict]:
        try:
            rows = list_watches()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="PostgreSQL connection failed") from exc
        return [
            {
                "id": row[0],
                "label": row[1],
                "search_url": row[2],
                "source_version": row[3],
                "resolved_search_url": row[4],
                "is_active": row[5],
                "created_at": row[6],
                "last_checked_at": row[7],
                "current_result_count": row[8],
                "alert_event_count": row[9],
            }
            for row in rows
        ]

    @api.post("/watches", dependencies=[Depends(require_admin_token)])
    def create_watch(payload: WatchCreate) -> dict[str, int]:
        try:
            watch_id = add_watch(payload.label, payload.search_url)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"id": watch_id}

    @api.patch("/watches/{watch_id}/active", dependencies=[Depends(require_admin_token)])
    def update_watch_active(watch_id: int, payload: WatchActiveUpdate) -> dict[str, object]:
        try:
            updated = set_watch_active(watch_id, payload.is_active)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="PostgreSQL connection failed") from exc
        if not updated:
            raise HTTPException(status_code=404, detail="watch not found")
        return {"id": watch_id, "is_active": payload.is_active}

    @api.post("/poll", dependencies=[Depends(require_admin_token)])
    def poll() -> list[dict]:
        try:
            results = AlertService(_build_notifier()).poll_all()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return [asdict(result) for result in results]

    @api.post("/watches/{watch_id}/poll", dependencies=[Depends(require_admin_token)])
    def poll_watch(watch_id: int) -> dict:
        try:
            watch = get_watch(watch_id)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="PostgreSQL connection failed") from exc
        if not watch:
            raise HTTPException(status_code=404, detail="watch not found")
        if not watch[4]:
            raise HTTPException(status_code=400, detail="watch is inactive")
        try:
            result = AlertService(_build_notifier()).poll_watch(
                int(watch[0]),
                str(watch[1]),
                str(watch[3] or watch[2]),
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return asdict(result)

    @api.get("/alerts")
    def get_alerts(limit: int = 50) -> list[dict]:
        try:
            rows = list_alert_events(limit=max(1, min(limit, 200)))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="PostgreSQL connection failed") from exc
        return [
            {
                "id": row[0],
                "watch_target_id": row[1],
                "watch_label": row[2],
                "external_listing_id": row[3],
                "event_type": row[4],
                "status": row[5],
                "message": row[6],
                "failure_reason": row[7],
                "created_at": row[8],
                "sent_at": row[9],
            }
            for row in rows
        ]

    @api.get("/watches/{watch_id}/results")
    def get_watch_results(watch_id: int, limit: int = 100) -> list[dict]:
        try:
            rows = list_current_results(watch_id, limit=max(1, min(limit, 200)))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="PostgreSQL connection failed") from exc
        return [
            {
                "external_listing_id": row[0],
                "result_level": row[1],
                "title": row[2],
                "price_text": row[3],
                "trade_type": row[4],
                "area_text": row[5],
                "floor_text": row[6],
                "complex_name": row[7],
                "source_url": row[8],
                "result_count": row[9],
                "first_seen_at": row[10],
                "last_seen_at": row[11],
                "last_snapshot_at": row[12],
            }
            for row in rows
        ]

    @api.post("/preview-search")
    def preview_search(payload: PreviewRequest) -> dict:
        search_url = payload.search_url or settings.naver_search_url
        if not search_url:
            raise HTTPException(status_code=400, detail="search_url is required or NAVER_SEARCH_URL must be set")
        try:
            listings = NaverSearchClient().fetch_listings(search_url)
        except NaverFetchError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "total": len(listings),
            "listings": [asdict(listing) for listing in listings[: payload.limit]],
        }

    @api.post("/kakao/test", dependencies=[Depends(require_admin_token)])
    def send_kakao_test(payload: KakaoTestRequest) -> dict[str, str]:
        try:
            _build_notifier().send_text(payload.message)
        except KakaoMessageError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"status": "sent"}

    return api


def _build_notifier() -> KakaoNotifier:
    if not settings.kakao_rest_api_key:
        raise KakaoMessageError("KAKAO_REST_API_KEY is not set")
    token_manager = KakaoTokenManager(
        rest_api_key=settings.kakao_rest_api_key,
        redirect_uri=settings.kakao_redirect_uri,
        access_token=settings.kakao_access_token,
        refresh_token=settings.kakao_refresh_token,
        client_secret=settings.kakao_client_secret,
        skip_ssl_verify=settings.skip_ssl_verify,
    )
    return KakaoNotifier(token_manager=token_manager)


try:
    app = create_app()
except RuntimeError:
    app = None
