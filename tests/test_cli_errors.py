from __future__ import annotations

import pytest
import typer

from app.cli import _format_naver_error
from app.cli import _validate_poll_interval


def test_format_naver_error_for_unsupported_host() -> None:
    message = _format_naver_error(Exception("Unsupported Naver host: example.com"))

    assert "지원하지 않는 네이버 URL" in message


def test_format_naver_error_for_missing_coordinates() -> None:
    message = _format_naver_error(Exception("Search URL does not include center coordinates."))

    assert "지도 중심 좌표" in message


def test_poll_interval_below_four_hours_requires_explicit_fast_mode() -> None:
    with pytest.raises(typer.Exit):
        _validate_poll_interval(600, allow_fast_poll=False)


def test_poll_interval_below_four_hours_can_be_allowed_for_development() -> None:
    _validate_poll_interval(600, allow_fast_poll=True)
