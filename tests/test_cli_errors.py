from __future__ import annotations

from app.cli import _format_naver_error


def test_format_naver_error_for_unsupported_host() -> None:
    message = _format_naver_error(Exception("Unsupported Naver host: example.com"))

    assert "지원하지 않는 네이버 URL" in message


def test_format_naver_error_for_missing_coordinates() -> None:
    message = _format_naver_error(Exception("Search URL does not include center coordinates."))

    assert "지도 중심 좌표" in message
