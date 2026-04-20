from __future__ import annotations

from dataclasses import dataclass

import requests


class SlackMessageError(RuntimeError):
    pass


@dataclass(slots=True)
class SlackNotifier:
    webhook_url: str | None
    skip_ssl_verify: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send_text(self, text: str) -> dict:
        if not self.webhook_url:
            return {"skipped": True, "reason": "SLACK_WEBHOOK_URL is not set"}

        try:
            response = requests.post(
                self.webhook_url,
                json={"text": text},
                timeout=20,
                verify=not self.skip_ssl_verify,
            )
        except requests.RequestException as exc:
            raise SlackMessageError(str(exc)) from exc

        if response.status_code != 200 or response.text.strip().lower() != "ok":
            raise SlackMessageError(f"HTTP {response.status_code}: {response.text}")

        return {"ok": True}
