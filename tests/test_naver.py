from __future__ import annotations

from app.naver import NaverSearchClient


class _NullJsonResponse:
    def json(self):
        return None


def test_fetch_listings_treats_naver_null_response_as_empty_list() -> None:
    client = NaverSearchClient()

    client._build_mobile_article_params = lambda filters: {}  # type: ignore[method-assign]
    client._get = lambda url, params=None: _NullJsonResponse()  # type: ignore[method-assign]

    assert client.fetch_listings("https://new.land.naver.com/complexes/1?ms=37,127,15") == []
