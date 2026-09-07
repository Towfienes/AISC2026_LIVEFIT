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
    # 127.0.0.1, NOT "localhost": on Windows localhost resolves to ::1 first
    # while Docker publishes only 127.0.0.1:5432, so psycopg waits out the
    # IPv6 connect timeout before falling back — measured 2m10s vs 0.5s
    # (incident 27/08). Every CLI looked hung.
    database_url: str = "postgresql://livelift:livelift@127.0.0.1:5432/livelift"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # Shared secret for the write endpoints POST /sessions/{id}/comments and
    # /ticks. Empty (default) = auth disabled (dev/demo). When set, ApiSink
    # attaches "Authorization: Bearer <token>" automatically.
    ingest_token: str = ""

    # PREREGISTRATION.md §7 (no peeking): ISO date (YYYY-MM-DD, UTC). While the
    # current UTC date is BEFORE this date, /experiment/summary withholds every
    # inferential field (estimate, p, CI) and serves operational numbers only.
    # Empty (default) = no freeze (dev/demo). A malformed value fails CLOSED:
    # the lock stays on until the configuration is fixed.
    results_freeze_until: str = ""

    youtube_api_key: str = ""
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    facebook_graph_version: str = "v23.0"
    # Opt-in workaround for YouTube's anti-bot check on VOD replay analysis:
    # "chrome" / "edge" / "firefox" — yt-dlp reads the local browser's login
    # cookies (nothing leaves the machine except the normal YouTube request).
    ytdlp_cookies_from_browser: str = ""


def _prefer_ipv4_loopback(url: str) -> str:
    """Rewrite a ``localhost`` host to ``127.0.0.1``.

    On Windows ``localhost`` resolves to ``::1`` first, but Docker publishes
    only ``127.0.0.1:5432``; psycopg then waits out the full IPv6 connect
    timeout before falling back — measured 2m10s vs 0.5s (incident 27/08).
    Every CLI looked hung. The two spellings mean the same host here, so we
    normalize rather than let a stale .env cost two minutes per command.
    """
    return url.replace("@localhost:", "@127.0.0.1:").replace("//localhost:", "//127.0.0.1:")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    return s.model_copy(
        update={
            "database_url": _prefer_ipv4_loopback(s.database_url),
            "redis_url": _prefer_ipv4_loopback(s.redis_url),
        }
    )
