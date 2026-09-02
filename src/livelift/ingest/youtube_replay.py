"""YouTube VOD chat-replay ingestion via yt-dlp.

A finished livestream (VOD) can carry a *chat replay*: yt-dlp downloads it as
a ``.live_chat.json`` sidecar file (one JSON object per line) when asked for
the ``live_chat`` "subtitle" track. This module downloads that file, parses it
into ``(offset_seconds, text)`` pairs, and synthesizes comment-tempo ticks.

PRIVACY (hard rule 1): the downloaded file contains author names and channel
ids. The parser extracts ONLY the video offset and the message text — no
author field ever leaves :func:`parse_live_chat_line`. Callers must scrub the
text (``livelift.ingest.pii.scrub``) before any store, and must delete the
downloaded file right after parsing (the route does both).

An analysis built from a replay is OBSERVATIONAL — there was no assignment
schedule during the original broadcast, so no experiment language may ever be
attached to it (see the observational guard in ``api/routes/reports.py``).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# yt-dlp is imported lazily inside download_chat_replay so that parsing and
# tests work without the package installed.

ERR_NO_CHAT = "Video này không còn/không bật chat replay"
ERR_UNAVAILABLE = "Không tải được video — URL sai, video riêng tư hoặc đã bị xóa"
ERR_NETWORK = "Lỗi mạng khi tải chat replay — thử lại sau"
ERR_BOT_CHECK = (
    "YouTube yêu cầu xác minh không phải bot từ mạng này. Cách xử lý: đặt "
    "YTDLP_COOKIES_FROM_BROWSER=chrome (hoặc edge/firefox) trong .env để dùng cookie "
    "đăng nhập YouTube sẵn có trên trình duyệt của bạn, rồi thử lại"
)
ERR_YTDLP_MISSING = (
    "Thiếu thư viện yt-dlp — cài bằng: pip install 'livelift[server]' hoặc pip install yt-dlp"
)


@dataclass(frozen=True)
class DownloadResult:
    """Outcome of a chat-replay download attempt.

    ``chat_path`` is None exactly when ``error`` is set. ``error`` is a
    Vietnamese, user-facing message (surfaced verbatim in the job detail).
    """

    chat_path: Path | None
    video_title: str
    duration_s: float
    error: str | None = None


def _runs_to_text(message: dict[str, Any]) -> str:
    """Concatenate text/emoji runs of a chat message into one string.

    Standard emoji carry the character itself in ``emojiId``; custom channel
    emoji only have shortcuts (``:name:``), so the first shortcut is used.
    """
    parts: list[str] = []
    for run in message.get("runs") or []:
        if "text" in run:
            parts.append(str(run["text"]))
        elif "emoji" in run:
            emoji = run["emoji"] or {}
            if emoji.get("isCustomEmoji"):
                shortcuts = emoji.get("shortcuts") or []
                if shortcuts:
                    parts.append(str(shortcuts[0]))
            elif emoji.get("emojiId"):
                parts.append(str(emoji["emojiId"]))
    return "".join(parts)


def parse_live_chat_line(line: str) -> tuple[float, str] | None:
    """Parse ONE line of yt-dlp's ``.live_chat.json`` format.

    Returns ``(offset_seconds, text)`` for plain text chat messages
    (``liveChatTextMessageRenderer``), or ``None`` for anything else:
    memberships, paid stickers, deleted items, malformed lines. The offset
    msec value appears as str or int depending on yt-dlp version — both are
    handled.

    PRIVACY: author name / channel id fields present in the renderer are
    deliberately ignored — only the offset and the message text are returned.
    """
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict):
        return None

    replay = obj.get("replayChatItemAction") or {}
    offset_raw = replay.get("videoOffsetTimeMsec", obj.get("videoOffsetTimeMsec"))
    if offset_raw is None:
        return None
    try:
        offset_s = float(offset_raw) / 1000.0
    except (TypeError, ValueError):
        return None

    actions = replay.get("actions") or []
    if not actions:
        return None
    item = ((actions[0].get("addChatItemAction") or {}).get("item")) or {}
    renderer = item.get("liveChatTextMessageRenderer")
    if renderer is None:
        return None  # membership, sticker, paid message, ... — not a text chat
    text = _runs_to_text(renderer.get("message") or {})
    if not text.strip():
        return None
    return (offset_s, text)


def parse_live_chat_file(path: str | Path) -> list[tuple[float, str]]:
    """Parse a whole ``.live_chat.json`` file into ``(offset_s, text)`` pairs
    sorted by offset (the file itself is not guaranteed to be ordered)."""
    out: list[tuple[float, str]] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parsed = parse_live_chat_line(line)
            if parsed is not None:
                out.append(parsed)
    out.sort(key=lambda pair: pair[0])
    return out


def download_chat_replay(
    url: str, out_dir: str | Path, cookies_from_browser: str | None = None
) -> DownloadResult:
    """Download the chat replay of a YouTube VOD into ``out_dir``.

    Uses the yt-dlp Python API with ``skip_download`` — only metadata and the
    ``live_chat`` subtitle track are fetched. Returns a :class:`DownloadResult`
    whose ``error`` (Vietnamese) is set when the video is unavailable, has no
    chat replay, or the network fails. yt-dlp is imported lazily so the rest
    of this module works without it installed.

    ``cookies_from_browser`` ("chrome"/"edge"/"firefox"): opt-in workaround for
    YouTube's anti-bot check. yt-dlp reads the login cookies of the LOCAL
    browser profile; nothing is transmitted anywhere except to YouTube itself,
    exactly as when the user opens the video in that browser. Off by default —
    the operator enables it explicitly via YTDLP_COOKIES_FROM_BROWSER in .env.
    """
    try:
        import yt_dlp
    except ImportError:
        return DownloadResult(
            chat_path=None, video_title="", duration_s=0.0, error=ERR_YTDLP_MISSING
        )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    opts: dict = {
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": ["live_chat"],
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        # YouTube intermittently 503s the live_chat track (measured in the
        # 02/09 live-fire: the same chat that had just downloaded fine from
        # another process got a 503 on the immediate retry). Back off and
        # retry instead of failing the whole job on one transient response.
        "retries": 5,
        "fragment_retries": 5,
        "retry_sleep_functions": {"http": lambda n: min(5 * (n + 1), 30)},
    }
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc)
        if "Sign in to confirm" in msg or "not a bot" in msg:
            return DownloadResult(
                chat_path=None, video_title="", duration_s=0.0, error=ERR_BOT_CHECK
            )
        transient = (
            "urlopen error" in msg
            or "Network" in msg
            or "timed out" in msg
            # 5xx/429 are YouTube-side throttles, not a bad URL. Reporting them
            # as "URL sai" sent the operator hunting a typo that did not exist
            # (incident 02/09 — the misdiagnosis cost a debugging round).
            or "503" in msg
            or "Service Unavailable" in msg
            or "429" in msg
            or "Too Many Requests" in msg
            or "502" in msg
        )
        if transient:
            return DownloadResult(chat_path=None, video_title="", duration_s=0.0, error=ERR_NETWORK)
        return DownloadResult(chat_path=None, video_title="", duration_s=0.0, error=ERR_UNAVAILABLE)
    except OSError:
        return DownloadResult(chat_path=None, video_title="", duration_s=0.0, error=ERR_NETWORK)

    info = info or {}
    title = str(info.get("title") or "")
    duration_s = float(info.get("duration") or 0.0)
    chat_path = out_dir / f"{info.get('id')}.live_chat.json"
    if not chat_path.exists():
        # Video exists but has no chat replay track (disabled or expired).
        return DownloadResult(
            chat_path=None, video_title=title, duration_s=duration_s, error=ERR_NO_CHAT
        )
    return DownloadResult(chat_path=chat_path, video_title=title, duration_s=duration_s, error=None)


def synth_ticks_from_comments(
    comments: list[tuple[float, str]], duration_s: float, tick_s: int = 30
) -> list[tuple[float, float]]:
    """Bucket comments into ``tick_s`` windows and return
    ``(bucket_start_s, comment_rate_per_min)`` for every bucket in the video.

    HONESTY NOTE: concurrent viewer counts are NOT available retroactively for
    a VOD — YouTube only exposes them during the live broadcast. A replay
    analysis therefore charts *comment tempo only*; the viewers series stays
    null/zero and must be labeled as unavailable in any UI. Do not fabricate
    a viewers curve from the comment rate.
    """
    if tick_s <= 0:
        raise ValueError("tick_s must be positive")
    horizon = max(float(duration_s), max((c[0] for c in comments), default=0.0))
    n_buckets = max(1, math.ceil(horizon / tick_s)) if horizon > 0 else 1
    counts = [0] * n_buckets
    for offset_s, _text in comments:
        idx = min(int(offset_s // tick_s), n_buckets - 1)
        if idx >= 0:
            counts[idx] += 1
    per_min = 60.0 / tick_s
    return [(float(i * tick_s), count * per_min) for i, count in enumerate(counts)]
