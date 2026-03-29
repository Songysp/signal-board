from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SignalBoard"
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    kakao_access_token: str | None = Field(default=None, alias="KAKAO_ACCESS_TOKEN")


settings = Settings()
