from __future__ import annotations

import pytest

from app.naver import NaverSearchClient
from app.naver import NaverFetchError


class _NullJsonResponse:
    def json(self):
        return None


class _JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_fetch_listings_treats_naver_null_response_as_empty_list() -> None:
    client = NaverSearchClient()

    client._build_mobile_article_params = lambda filters: {}  # type: ignore[method-assign]
    client._get = lambda url, params=None: _NullJsonResponse()  # type: ignore[method-assign]

    assert client.fetch_listings("https://new.land.naver.com/complexes/1?ms=37,127,15") == []


def test_fetch_listings_stops_when_complex_results_exist_but_articles_are_empty() -> None:
    client = NaverSearchClient()

    def fake_get(url, params=None):
        if url.endswith("/articleList"):
            return _NullJsonResponse()
        if url.endswith("/complexList"):
            return _JsonResponse({"result": [{"hscpNm": "테스트단지", "totalAtclCnt": 2}]})
        return _JsonResponse({})

    client._build_mobile_article_params = lambda filters: {}  # type: ignore[method-assign]
    client._get = fake_get  # type: ignore[method-assign]

    with pytest.raises(NaverFetchError, match="false total=0"):
        client.fetch_listings("https://new.land.naver.com/complexes/1?ms=37,127,15")
