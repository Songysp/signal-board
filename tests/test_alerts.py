from __future__ import annotations

from app.alerts import format_listing_message
from app.alerts import format_result_change_message
from app.alerts import AlertService
from app.models import NaverListing


def test_format_listing_message_labels_complex_search_results() -> None:
    message = format_listing_message(
        "송도 매매",
        NaverListing(
            listing_id="complex:123",
            result_level="complex",
            title="테스트단지 단지 결과",
            price_text="매매 5억~6억",
            trade_type="매매",
            area_text="84~110㎡",
            result_count=2,
            detail_url="https://fin.land.naver.com/complexes/123",
        ),
    )

    assert "[부동산알리미] 신규 검색 결과" in message
    assert "유형: 단지/클러스터 검색 결과" in message
    assert "테스트단지 단지 결과" in message
    assert "검색 결과 수: 2" in message


def test_format_result_change_message_lists_changed_fields() -> None:
    message = format_result_change_message(
        "송도 매매",
        NaverListing(
            listing_id="complex:123",
            result_level="complex",
            title="테스트단지 단지 결과",
            price_text="매매 5억~6억",
            trade_type="매매",
            area_text="84~110㎡",
            result_count=3,
            detail_url="https://fin.land.naver.com/complexes/123",
        ),
        {
            "price_text": "매매 4억~5억",
            "trade_type": "매매",
            "area_text": "84~110㎡",
            "result_count": 2,
        },
    )

    assert "[부동산알리미] 검색 결과 변화" in message
    assert "가격: 매매 4억~5억 -> 매매 5억~6억" in message
    assert "검색 결과 수: 2 -> 3" in message


def test_alert_service_sends_optional_slack_message() -> None:
    calls = []

    class FakeSlackNotifier:
        is_configured = True

        def send_text(self, message):
            calls.append(message)

    service = AlertService(notifier=object(), slack_notifier=FakeSlackNotifier())
    service._send_slack_if_configured("hello")

    assert calls == ["hello"]
