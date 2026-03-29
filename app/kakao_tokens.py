from __future__ import annotations

import json
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning


class KakaoTokenError(RuntimeError):
    pass


TOKEN_FILE = Path(".signalboard.tokens.json")


@dataclass(slots=True)
class KakaoTokenManager:
    rest_api_key: str
    redirect_uri: str
    access_token: str | None = None
    refresh_token: str | None = None
    client_secret: str | None = None
    skip_ssl_verify: bool = False
    token_file: Path = TOKEN_FILE

    def __post_init__(self) -> None:
        if self.skip_ssl_verify:
            disable_warnings(InsecureRequestWarning)
        self.load_token()

    def build_authorize_url(self, *, scope: str = "talk_message") -> str:
        query = urlencode(
            {
                "client_id": self.rest_api_key,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": scope,
            }
        )
        return f"https://kauth.kakao.com/oauth/authorize?{query}"

    def login(self, *, open_browser: bool = True, timeout_seconds: int = 180) -> dict:
        auth_url = self.build_authorize_url()
        if open_browser:
            webbrowser.open(auth_url)
        code = self.receive_authorization_code(auth_url=auth_url, timeout_seconds=timeout_seconds)
        return self.exchange_code(code)

    def receive_authorization_code(self, *, auth_url: str, timeout_seconds: int = 180) -> str:
        parsed = urlparse(self.redirect_uri)
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise KakaoTokenError("KAKAO_REDIRECT_URI must point to localhost or 127.0.0.1.")

        result: dict[str, str] = {}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                query = parse_qs(urlparse(self.path).query)
                if "code" in query:
                    result["code"] = query["code"][0]
                    body = "SignalBoard Kakao login complete. You can return to the terminal."
                    self.send_response(200)
                else:
                    result["error"] = query.get("error", ["unknown_error"])[0]
                    body = f"SignalBoard Kakao login failed: {result['error']}"
                    self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer((parsed.hostname, parsed.port or 80), CallbackHandler)
        server.timeout = timeout_seconds

        start = time.time()
        while time.time() - start < timeout_seconds and "code" not in result and "error" not in result:
            server.handle_request()
        server.server_close()

        if "error" in result:
            raise KakaoTokenError(f"Kakao login failed: {result['error']}")
        if "code" not in result:
            raise KakaoTokenError(f"Timed out waiting for Kakao callback. Open this URL manually: {auth_url}")
        return result["code"]

    def exchange_code(self, code: str) -> dict:
        payload = self._post_form(
            "https://kauth.kakao.com/oauth/token",
            {
                "grant_type": "authorization_code",
                "client_id": self.rest_api_key,
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
        )
        self._save_token_payload(payload, fallback_refresh_token=None)
        return payload

    def refresh_access_token(self) -> dict:
        if not self.refresh_token:
            raise KakaoTokenError("No refresh token is available.")
        payload = self._post_form(
            "https://kauth.kakao.com/oauth/token",
            {
                "grant_type": "refresh_token",
                "client_id": self.rest_api_key,
                "refresh_token": self.refresh_token,
            },
        )
        self._save_token_payload(payload, fallback_refresh_token=self.refresh_token)
        return payload

    def ensure_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        if self.refresh_token:
            self.refresh_access_token()
            if self.access_token:
                return self.access_token
        raise KakaoTokenError(
            "No access token is available. Run kakao-login or kakao-exchange-code to create one first."
        )

    def load_token(self) -> dict:
        if not self.token_file.exists():
            return {}
        payload = json.loads(self.token_file.read_text(encoding="utf-8"))
        self.access_token = payload.get("access_token") or self.access_token
        self.refresh_token = payload.get("refresh_token") or self.refresh_token
        return payload

    def save_token(self) -> None:
        payload = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }
        self.token_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_token_payload(self, payload: dict, *, fallback_refresh_token: str | None) -> None:
        self.access_token = payload.get("access_token")
        self.refresh_token = payload.get("refresh_token") or fallback_refresh_token
        self.save_token()

    def _post_form(self, url: str, form: dict[str, str]) -> dict:
        request_form = dict(form)
        if self.client_secret:
            request_form["client_secret"] = self.client_secret
        headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
        try:
            response = requests.post(
                url,
                data=request_form,
                headers=headers,
                timeout=20,
                verify=not self.skip_ssl_verify,
            )
        except requests.RequestException as exc:
            raise KakaoTokenError(str(exc)) from exc
        if response.status_code != 200:
            raise KakaoTokenError(f"HTTP {response.status_code}: {response.text}")
        return response.json()
