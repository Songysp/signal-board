from __future__ import annotations

from app.alerts import format_listing_message
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
            detail_url="https://fin.land.naver.com/complexes/123",
        ),
    )

    assert "[부동산알리미] 신규 검색 결과" in message
    assert "유형: 단지/클러스터 검색 결과" in message
    assert "테스트단지 단지 결과" in message
