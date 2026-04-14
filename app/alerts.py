from __future__ import annotations

from app.kakao_notifier import KakaoNotifier
from app.models import NaverListing, PollResult
from app.naver import NaverSearchClient
from app.storage import (
    create_alert_event,
    existing_listing_ids,
    get_active_watches,
    has_snapshot_history,
    mark_alert_failed,
    mark_alert_sent,
    save_snapshot,
)


def format_listing_message(label: str, listing: NaverListing) -> str:
    lines = [
        f"[부동산알리미] 신규 매물",
        f"조건: {label}",
        listing.title or listing.complex_name or f"매물 {listing.listing_id}",
    ]
    if listing.price_text:
        lines.append(f"가격: {listing.price_text}")
    if listing.trade_type:
        lines.append(f"거래유형: {listing.trade_type}")
    if listing.area_text:
        lines.append(f"면적: {listing.area_text}")
    if listing.floor_text:
        lines.append(f"층: {listing.floor_text}")
    if listing.detail_url:
        lines.append(f"링크: {listing.detail_url}")
    return "\n".join(lines)


class AlertService:
    def __init__(self, notifier: KakaoNotifier) -> None:
        self.notifier = notifier
        self.naver_client = NaverSearchClient()

    def poll_all(self) -> list[PollResult]:
        results: list[PollResult] = []
        for watch_id, label, search_url, resolved_search_url in get_active_watches():
            effective_search_url = str(resolved_search_url or search_url)
            results.append(self.poll_watch(int(watch_id), str(label), effective_search_url))
        return results

    def poll_watch(self, watch_id: int, label: str, search_url: str) -> PollResult:
        listings = self.naver_client.fetch_listings(search_url)
        known_ids = existing_listing_ids(watch_id)
        baseline_created = not has_snapshot_history(watch_id)

        new_listings = []
        if baseline_created:
            new_listings = []
        else:
            new_listings = [listing for listing in listings if listing.listing_id not in known_ids]

        save_snapshot(watch_id, search_url, listings)

        for listing in new_listings:
            message = format_listing_message(label, listing)
            created = create_alert_event(watch_id, listing, message)
            if not created:
                continue
            try:
                self.notifier.send_text(message, web_url=listing.detail_url or search_url)
            except Exception as exc:
                mark_alert_failed(watch_id, listing.listing_id, str(exc))
                raise
            else:
                mark_alert_sent(watch_id, listing.listing_id)

        return PollResult(
            watch_id=watch_id,
            label=label,
            search_url=search_url,
            total_count=len(listings),
            baseline_created=baseline_created,
            new_listings=new_listings,
        )
