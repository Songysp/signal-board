from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> dict[str, str]:
    env_path = Path(".env")
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        normalized = value.strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
            normalized = normalized[1:-1]
        values[key.strip()] = normalized
    return values


@dataclass(slots=True)
class Settings:
    app_name: str = "SignalBoard"
    database_url: str | None = None
    kakao_rest_api_key: str | None = None
    kakao_client_secret: str | None = None
    kakao_access_token: str | None = None
    kakao_refresh_token: str | None = None
    kakao_redirect_uri: str = "http://127.0.0.1:8765/kakao/callback"
    skip_ssl_verify: bool = False


def load_settings() -> Settings:
    dotenv = _load_dotenv()
    return Settings(
        app_name=os.getenv("APP_NAME", dotenv.get("APP_NAME", "SignalBoard")),
        database_url=os.getenv("DATABASE_URL", dotenv.get("DATABASE_URL")),
        kakao_rest_api_key=os.getenv("KAKAO_REST_API_KEY", dotenv.get("KAKAO_REST_API_KEY")),
        kakao_client_secret=os.getenv("KAKAO_CLIENT_SECRET", dotenv.get("KAKAO_CLIENT_SECRET")),
        kakao_access_token=os.getenv("KAKAO_ACCESS_TOKEN", dotenv.get("KAKAO_ACCESS_TOKEN")),
        kakao_refresh_token=os.getenv("KAKAO_REFRESH_TOKEN", dotenv.get("KAKAO_REFRESH_TOKEN")),
        kakao_redirect_uri=os.getenv(
            "KAKAO_REDIRECT_URI",
            dotenv.get("KAKAO_REDIRECT_URI", "http://127.0.0.1:8765/kakao/callback"),
        ),
        skip_ssl_verify=os.getenv("SKIP_SSL_VERIFY", dotenv.get("SKIP_SSL_VERIFY", "0")) in {"1", "true", "TRUE"},
    )


settings = load_settings()
