from __future__ import annotations

import pytest

from app.slack_notifier import SlackMessageError, SlackNotifier


class FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def test_slack_notifier_skips_when_not_configured() -> None:
    result = SlackNotifier(webhook_url=None).send_text("hello")

    assert result["skipped"] is True


def test_slack_notifier_posts_text(monkeypatch) -> None:
    calls = []

    def fake_post(url, json, timeout, verify):
        calls.append((url, json, timeout, verify))
        return FakeResponse(200, "ok")

    monkeypatch.setattr("app.slack_notifier.requests.post", fake_post)

    result = SlackNotifier(webhook_url="https://hooks.slack.test/services/x").send_text("hello")

    assert result == {"ok": True}
    assert calls[0][1] == {"text": "hello"}


def test_slack_notifier_raises_on_non_ok_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.slack_notifier.requests.post",
        lambda *args, **kwargs: FakeResponse(500, "bad"),
    )

    with pytest.raises(SlackMessageError):
        SlackNotifier(webhook_url="https://hooks.slack.test/services/x").send_text("hello")
