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

    # --- Chống mất dữ liệu ở chế độ kho 'memory' (sự cố 11/09/2026) -------
    # Ngày 11/09/2026 tiến trình API khởi động lại lúc 13:05:53 và 13 phiên
    # live thật + 17.535 bình luận biến mất vĩnh viễn, vì kho chỉ nằm trong
    # RAM. Ảnh chụp định kỳ là lưới an toàn cho chế độ đó; nó KHÔNG thay thế
    # STORE_BACKEND=postgres cho phiên live thật.
    #
    # Mặc định BẬT: một cơ chế an toàn phải mặc định bảo vệ, người dùng phải
    # chủ động tắt mới mất. Chỉ áp dụng cho kho 'memory'.
    store_snapshot_enabled: bool = True
    store_snapshot_path: str = "data/snapshot/livelift-store.json"
    # 30 giây = mức mất tối đa khi tiến trình chết đột ngột. Tắt máy có trật
    # tự luôn chụp lần cuối nên không mất gì.
    store_snapshot_interval_s: float = 30.0

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
    # Which YouTube live-ingest path the runner uses:
    #   "api"   — livelift.ingest.youtube, needs YOUTUBE_API_KEY (default: old
    #             behavior is never changed by adding this setting);
    #   "ytdlp" — livelift.ingest.youtube_ytdlp, reads the public live chat via
    #             yt-dlp with NO key and no quota (higher delivery lag, see that
    #             module's docstring). This is the path a team without
    #             credentials can run a live session on today.
    ingest_youtube_backend: str = "api"
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""
    # Graph API version. v25.0 (released 18/02/2026, sunsets 29/07/2028) is the
    # newest version that has been stable for months; the previous default
    # v23.0 sunsets 08/10/2027 and is four releases behind. Nothing we read
    # (live_videos, comments, live_views) changed in v24–v26 — checked
    # 2026-09-09 against the v25.0/v26.0 changelogs.
    facebook_graph_version: str = "v25.0"
    # Optional, only for scripts/kiem_tra_facebook.py: with the app id+secret
    # the checker can call /debug_token and report the token's real expiry and
    # granted permissions. Never needed by the ingest runner itself — the
    # secret must NOT be deployed to the ingest host.
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    # Opt-in workaround for YouTube's anti-bot check on VOD replay analysis:
    # "chrome" / "edge" / "firefox" — yt-dlp reads the local browser's login
    # cookies (nothing leaves the machine except the normal YouTube request).
    ytdlp_cookies_from_browser: str = ""

    # Shopee Open Platform v2 (OFFICIAL API — hợp ToS). partner_id/partner_key
    # đến từ tài khoản Open Platform của nhóm; shop_id/access_token đến từ luồng
    # ủy quyền OAuth của CHÍNH shop mình. access_token chỉ sống 4 giờ và phải
    # làm mới bằng refresh_token — xem docs/nen-tang-ho-tro.md §4.
    shopee_partner_id: str = ""
    shopee_partner_key: str = ""
    shopee_shop_id: str = ""
    shopee_access_token: str = ""
    shopee_refresh_token: str = ""
    # Cổng API theo vùng: "global" (gồm Việt Nam), "china", "brazil", "sandbox".
    # Shopee KHÔNG có host riêng cho .vn — VN đi qua partner.shopeemobile.com.
    shopee_region: str = "global"


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
