from __future__ import annotations

import pytest

from app.naver import NaverFetchError, NaverSearchClient, parse_search_filters


class _NullJsonResponse:
    def json(self):
        return None


class _JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_parse_search_filters_rejects_unsupported_legacy_ms_format() -> None:
    with pytest.raises(NaverFetchError, match="unsupported ms format"):
        parse_search_filters("https://new.land.naver.com/complexes?ms=2ANHjm&a=APT&b=A1")


def test_parse_search_filters_rejects_unsupported_fin_center_format() -> None:
    with pytest.raises(NaverFetchError, match="unsupported center format"):
        parse_search_filters("https://fin.land.naver.com/map?center=3zou4n-2ANHjm&zoom=15")


def test_fetch_listings_treats_naver_null_response_as_empty_list() -> None:
    client = NaverSearchClient()

    client._build_mobile_article_params = lambda filters: {}  # type: ignore[method-assign]
    client._get = lambda url, params=None: _NullJsonResponse()  # type: ignore[method-assign]

    assert client.fetch_listings("https://new.land.naver.com/complexes/1?ms=37,127,15") == []


def test_fetch_listings_falls_back_to_complex_results_when_articles_are_empty() -> None:
    client = NaverSearchClient()

    def fake_get(url, params=None):
        if url.endswith("/articleList"):
            return _NullJsonResponse()
        if url.endswith("/complexList"):
            return _JsonResponse(
                {
                    "result": [
                        {
                            "hscpNo": "123",
                            "hscpNm": "테스트단지",
                            "hscpTypeNm": "아파트",
                            "dealCnt": 2,
                            "totalAtclCnt": 2,
                            "dealPrcMin": "5<em class='txt_unit'>억</em>",
                            "dealPrcMax": "6<em class='txt_unit'>억</em>",
                            "minSpc": "84.5",
                            "maxSpc": "110.2",
                        }
                    ]
                }
            )
        return _JsonResponse({})

    client._build_mobile_article_params = lambda filters: {}  # type: ignore[method-assign]
    client._get = fake_get  # type: ignore[method-assign]

    listings = client.fetch_listings("https://new.land.naver.com/complexes?ms=37,127,15&b=A1")

    assert len(listings) == 1
    assert listings[0].listing_id == "complex:123"
    assert listings[0].result_level == "complex"
    assert listings[0].title == "테스트단지 단지 결과"
    assert listings[0].price_text == "매매 5억~6억"
    assert listings[0].area_text == "84.5~110.2㎡"
