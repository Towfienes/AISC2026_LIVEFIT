"""Application configuration, loaded from environment / .env.

All I/O-facing settings live here. Pure/statistical modules never read config —
they take explicit parameters, so they stay testable without an environment.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    livelift_env: str = "dev"
    database_url: str = "postgresql://livelift:livelift@localhost:5432/livelift"
    redis_url: str = "redis://localhost:6379/0"

    youtube_api_key: str = ""
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    facebook_graph_version: str = "v23.0"
    # Opt-in workaround for YouTube's anti-bot check on VOD replay analysis:
    # "chrome" / "edge" / "firefox" — yt-dlp reads the local browser's login
    # cookies (nothing leaves the machine except the normal YouTube request).
    ytdlp_cookies_from_browser: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
