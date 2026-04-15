from __future__ import annotations

import hashlib
import json

from app.kakao_notifier import KakaoNotifier
from app.models import NaverListing, PollResult
from app.naver import NaverSearchClient
from app.storage import (
    create_alert_event,
    existing_listing_ids,
    get_current_listing_states,
    get_active_watches,
    has_snapshot_history,
    mark_alert_failed,
    mark_alert_sent,
    save_snapshot,
)


def format_listing_message(label: str, listing: NaverListing) -> str:
    is_complex_result = listing.result_level == "complex"
    headline = "[부동산알리미] 신규 검색 결과" if is_complex_result else "[부동산알리미] 신규 매물"
    fallback_title = "검색 결과" if is_complex_result else f"매물 {listing.listing_id}"
    lines = [
        headline,
        f"조건: {label}",
        listing.title or listing.complex_name or fallback_title,
    ]
    if is_complex_result:
        lines.append("유형: 단지/클러스터 검색 결과")
    if listing.price_text:
        lines.append(f"가격: {listing.price_text}")
    if listing.trade_type:
        lines.append(f"거래유형: {listing.trade_type}")
    if listing.area_text:
        lines.append(f"면적: {listing.area_text}")
    if listing.result_count is not None:
        lines.append(f"검색 결과 수: {listing.result_count}")
    if listing.floor_text:
        lines.append(f"층: {listing.floor_text}")
    if listing.detail_url:
        lines.append(f"링크: {listing.detail_url}")
    return "\n".join(lines)


def format_result_change_message(label: str, listing: NaverListing, previous: dict) -> str:
    lines = [
        "[부동산알리미] 검색 결과 변화",
        f"조건: {label}",
        listing.title or listing.complex_name or "검색 결과",
        "유형: 단지/클러스터 검색 결과",
    ]
    changes = _result_changes(previous, listing)
    for field_label, old_value, new_value in changes:
        lines.append(f"{field_label}: {old_value or '-'} -> {new_value or '-'}")
    if listing.detail_url:
        lines.append(f"링크: {listing.detail_url}")
    return "\n".join(lines)


def _result_changes(previous: dict, listing: NaverListing) -> list[tuple[str, object | None, object | None]]:
    fields = [
        ("가격", "price_text", listing.price_text),
        ("거래유형", "trade_type", listing.trade_type),
        ("면적", "area_text", listing.area_text),
        ("검색 결과 수", "result_count", listing.result_count),
    ]
    changes: list[tuple[str, object | None, object | None]] = []
    for label, key, new_value in fields:
        old_value = previous.get(key)
        if old_value != new_value:
            changes.append((label, old_value, new_value))
    return changes


def _change_event_type(listing: NaverListing) -> str:
    payload = {
        "price_text": listing.price_text,
        "trade_type": listing.trade_type,
        "area_text": listing.area_text,
        "result_count": listing.result_count,
    }
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    return f"changed_result:{digest}"


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
        current_states = get_current_listing_states(watch_id)
        known_ids = set(current_states)
        baseline_created = not has_snapshot_history(watch_id)

        new_listings = []
        changed_listings = []
        if baseline_created:
            new_listings = []
        else:
            new_listings = [listing for listing in listings if listing.listing_id not in known_ids]
            changed_listings = [
                listing
                for listing in listings
                if listing.listing_id in current_states
                and listing.result_level == "complex"
                and _result_changes(current_states[listing.listing_id], listing)
            ]

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

        for listing in changed_listings:
            previous = current_states[listing.listing_id]
            message = format_result_change_message(label, listing, previous)
            event_type = _change_event_type(listing)
            created = create_alert_event(watch_id, listing, message, event_type=event_type)
            if not created:
                continue
            try:
                self.notifier.send_text(message, web_url=listing.detail_url or search_url)
            except Exception as exc:
                mark_alert_failed(watch_id, listing.listing_id, str(exc), event_type=event_type)
                raise
            else:
                mark_alert_sent(watch_id, listing.listing_id, event_type=event_type)

        return PollResult(
            watch_id=watch_id,
            label=label,
            search_url=search_url,
            total_count=len(listings),
            baseline_created=baseline_created,
            new_listings=new_listings,
            changed_listings=changed_listings,
        )
