"""YouTube **live** ingestion via yt-dlp — no API key, no OAuth, no quota.

Why this module exists: :mod:`livelift.ingest.youtube` needs ``YOUTUBE_API_KEY``.
Without a key that path cannot run at all, and the project cannot hold a real
session. yt-dlp reads the same public live chat that any visitor sees in the
browser, so a live-fire session is possible today. Select it with
``INGEST_YOUTUBE_BACKEND=ytdlp`` (default stays ``api``).

MEASURED ON A REAL LIVE STREAM (2026-09-09, yt-dlp 2026.08.19, video
``6ekwo7H_BJU``, ~860 concurrent viewers; commands in
``docs/research/2026-09-09-youtube-ytdlp-live.md``):

- chat: 100 text messages in 151 s (34 of them arriving during the run
  = **13.5 tin/phút**), every one with a unique ``id`` and an absolute
  ``timestampUsec``; Vietnamese diacritics intact.
- **delivery lag: p50 24 s, p90 37 s, min 12 s** — measured as
  ``arrival_wall_clock − message timestamp``. The lag is inherent to yt-dlp's
  live-chat downloader, which sleeps the continuation's ``timeoutMs`` *before*
  flushing the batch it already holds (``yt_dlp/downloader/youtube_live_chat.py``
  ``parse_actions_live``), so a message waits roughly two poll intervals.
  This does NOT bias block attribution: ``ts_utc`` is YouTube's own
  ``timestampUsec``, not the arrival time. It does mean the operator dashboard
  runs ~25 s behind, and that a run must outlive its last block by ~1 minute.
- viewers: ``concurrent_view_count`` is real and moves (863 → 892 → 908 over
  60 s), ~1.7 s per refresh after the first call of the process.
- on connect YouTube replays a **backlog** of recent chat (observed 66 messages
  reaching 329 s back). They are emitted with their true timestamps — a restart
  therefore backfills its own gap, and the server's ``(platform, ext_id)``
  idempotency makes the overlap free.

WINDOWS, load-bearing: yt-dlp writes the chat to ``<id>.live_chat.json.part``
and renames it when the stream ends. Holding that file open makes the rename
fail (``WinError 32``) — verified: yt-dlp retried 3× and exited rc=1 with the
data already on disk. The tailer therefore opens, reads, and CLOSES the file on
every poll, and treats "Unable to rename file" in the log as a clean end.

PRIVACY: yt-dlp's file carries ``authorName`` and ``authorExternalChannelId``.
:func:`parse_live_chat_actions` reads only ``id``, ``timestampUsec`` and the
message runs — no author field is ever put in a :class:`RawComment` — and the
file itself lives in a private temp directory that is deleted as soon as the
process ends (or the generator is cancelled). Text is scrubbed downstream by
:class:`livelift.ingest.base.ApiSink`, exactly as on the API path.

LEGAL / ToS — READ BEFORE USING THIS ON A REAL SESSION. This path conflicts
with YouTube's Terms of Service, and the project does not pretend otherwise:

- the ToS forbid accessing the Service "bằng bất kỳ phương thức tự động nào
  (như rô bốt, mạng botnet hoặc chương trình tự động thu thập dữ liệu)" except
  "(a) trong trường hợp công cụ tìm kiếm công khai, theo tệp robot.txt của
  YouTube; hoặc (b) được YouTube cho phép trước bằng văn bản"
  (https://www.youtube.com/t/terms, checked 2026-09-09);
- and ``https://www.youtube.com/robots.txt`` (same day) disallows exactly the
  two paths yt-dlp's live-chat downloader calls — ``/live_chat`` and
  ``/youtubei/`` — so the robots.txt exception does not cover us.

Nothing here downloads video and nothing non-public is read, but the *access
method* is not sanctioned. Consequences the team must accept, in order:

1. The correct fix is a ``YOUTUBE_API_KEY``: free, no billing, no app review,
   ~10 minutes in Google Cloud Console. That — not this module — is the path a
   published experiment should run on.
2. Use this module for the team's OWN broadcast, for technical validation, and
   as an emergency fallback when a key dies mid-session. Never to harvest other
   people's streams at scale, and never for redistributing chat.
3. If any data collected this way reaches the paper, the collection method must
   be declared in the methods/ethics section. Do not launder it as "API data".

Full evidence and the API-vs-yt-dlp comparison:
``docs/research/2026-09-09-youtube-ytdlp-live.md``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
import sys
import tempfile
import time
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from json import JSONDecodeError, loads
from pathlib import Path
from typing import Any, Protocol

from livelift.config import get_settings
from livelift.ingest.base import Backoff, RawComment, RawReaction, RawTick

# Deliberate intra-package reuse: emoji/custom-emoji handling and the
# renderer→reaction mapping must stay identical between the VOD replay path
# and this live path.
from livelift.ingest.youtube_replay import ERR_BOT_CHECK, REACTION_RENDERERS, parse_purchase_amount
from livelift.ingest.youtube_replay import _runs_to_text as runs_to_text

logger = logging.getLogger(__name__)

#: How often the tailer looks for new bytes. yt-dlp flushes once per chat
#: fragment (~10 s), so anything below ~1 s only costs syscalls.
TAIL_POLL_S = 0.5
#: Long pause for errors that a retry cannot fix by itself (bot check) —
#: mirrors AUTH_BACKOFF_S on the API path: keep the process alive and loud
#: rather than dying, so the operator sees it in every heartbeat.
BLOCKED_BACKOFF_S = 60.0
RELAUNCH_BASE_S = 5.0
RELAUNCH_CAP_S = 60.0
#: Ids remembered to avoid re-posting the backlog after a relaunch. ~5 min of
#: a very busy room; the server dedupes anyway, this just saves the POSTs.
SEEN_IDS_MAX = 5000
#: Tail of the yt-dlp log kept for error classification (chars).
LOG_TAIL_CHARS = 4000
#: Prefix of the per-run temp directories, so a later run can recognize them.
TEMP_PREFIX = "livelift-ytchat-"
#: A hard-killed runner (``kill -9``, a killed container, ``timeout``) never
#: gets to clean up — measured: 121 KB of raw chat with author names left
#: behind. The next client startup sweeps such leftovers. Only directories
#: untouched for this long are removed; an active download writes every ~10 s,
#: so a session running in parallel is never disturbed.
STALE_TEMP_AFTER_S = 1800.0

ERR_NOT_LIVE = (
    "Video không ở trạng thái phát trực tiếp (không có khung chat trực tiếp). "
    "Kiểm tra lại VIDEO_ID; nếu phiên đã kết thúc hãy dùng đường phân tích VOD "
    "(chat replay) thay vì ingest trực tiếp."
)
ERR_NO_CHAT = "Luồng này không bật chat trực tiếp — không có bình luận để thu."
ERR_UNAVAILABLE = "Không mở được video — id sai, video riêng tư hoặc đã bị xóa."
ERR_YTDLP_MISSING = "Thiếu thư viện yt-dlp trong môi trường chạy — cài bằng: pip install yt-dlp"
ERR_VIEWERS_HIDDEN = (
    "Kênh này ẩn số người xem đồng thời — KHÔNG có tín hiệu 'ticks'. "
    "Hệ thống không ghi số 0 giả; năng lực 'nhịp phiên' và 'tỷ lệ nhấp' sẽ báo THIẾU "
    "trong ma trận tín hiệu."
)

# Substrings observed in real yt-dlp output; each maps to a handling class.
_FATAL_MARKERS = (
    "Video unavailable",
    "Private video",
    "This video is not available",
    "Incomplete YouTube ID",
    "is not a valid URL",
    "members-only",
)
_BOT_MARKERS = ("Sign in to confirm", "not a bot", "confirm you", "cookies")
_WAIT_MARKERS = (
    "not currently live",
    "will begin in",
    "Premieres in",
    "This live event",
    "is offline",
)
# Verified on Windows: the rename can lose to any reader; the chat bytes are
# already flushed to disk at that point, so this is a completed download.
_RENAME_MARKER = "Unable to rename file"


def _video_url(source_id: str) -> str:
    """Accept either a bare video id or a full watch URL."""
    if source_id.startswith(("http://", "https://")):
        return source_id
    return f"https://www.youtube.com/watch?v={source_id}"


def parse_live_chat_actions(line: str) -> list[RawComment]:
    """Parse ONE line of yt-dlp's ``.live_chat.json`` into comments.

    Handles both shapes, which yt-dlp deliberately keeps compatible:

    - live: ``{"replayChatItemAction": {"actions": [...]}, "videoOffsetTimeMsec":
      "...", "isLive": true}`` (offset is relative to the *downloader's* start
      and is negative for the connect backlog — unusable as a clock, ignored);
    - replay/VOD: the raw ``replayChatItemAction`` with a real video offset.

    Both carry ``liveChatTextMessageRenderer.timestampUsec`` (absolute epoch
    microseconds) and ``.id``, which is what a live session needs, so the same
    parser serves both. A line may hold several actions — all are returned,
    unlike the offset-only VOD parser which reads the first.

    Returns ``[]`` for non-text events (memberships, paid stickers, viewer
    engagement notices, placeholders) and malformed lines.

    PRIVACY: ``authorName`` / ``authorExternalChannelId`` are present in the
    renderer and are never read here.
    """
    line = line.strip()
    if not line:
        return []
    try:
        obj = loads(line)
    except (JSONDecodeError, UnicodeDecodeError):
        return []
    if not isinstance(obj, dict):
        return []

    replay = obj.get("replayChatItemAction")
    actions = replay.get("actions") if isinstance(replay, dict) else None
    if not isinstance(actions, list):
        return []

    out: list[RawComment] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        item = (action.get("addChatItemAction") or {}).get("item")
        if not isinstance(item, dict):
            continue
        renderer = item.get("liveChatTextMessageRenderer")
        if not isinstance(renderer, dict):
            continue  # membership / sticker / placeholder — not a chat message
        ext_id = renderer.get("id")
        ts_usec = renderer.get("timestampUsec")
        if not ext_id or ts_usec is None:
            continue
        try:
            ts = datetime.fromtimestamp(int(ts_usec) / 1_000_000, UTC)
        except (TypeError, ValueError, OSError, OverflowError):
            continue
        text = runs_to_text(renderer.get("message") or {})
        if not text.strip():
            continue
        out.append(
            RawComment(
                platform="youtube",
                ext_id=str(ext_id),
                ts_utc=ts,
                text=text,
                author_ext_id=None,  # dropped at normalization — never transmitted
            )
        )
    return out


def parse_live_chat_reaction_actions(line: str) -> list[RawReaction]:
    """Parse ONE ``.live_chat.json`` line into paid/reaction events.

    Same line shapes as :func:`parse_live_chat_actions`; recognizes the
    renderers in :data:`livelift.ingest.youtube_replay.REACTION_RENDERERS`
    (Super Chat, paid sticker, membership, gift purchase) via their absolute
    ``timestampUsec`` + ``id``. Gift REDEMPTIONS are excluded there — one
    purchase, many recipient announcements — and likes never appear in the
    chat stream at all: that absence is declared in the signal matrix, never
    written as 0.

    NOTE: the live runner does not pump this parser yet — the ingest loop
    still delivers comments and ticks only, so the reactions signal for a live
    YouTube session honestly reads THIẾU until the pump is wired (followup).

    PRIVACY: only ``id``, ``timestampUsec`` and ``purchaseAmountText`` are
    read; author name/channel fields are never touched.
    """
    line = line.strip()
    if not line:
        return []
    try:
        obj = loads(line)
    except (JSONDecodeError, UnicodeDecodeError):
        return []
    if not isinstance(obj, dict):
        return []

    replay = obj.get("replayChatItemAction")
    actions = replay.get("actions") if isinstance(replay, dict) else None
    if not isinstance(actions, list):
        return []

    out: list[RawReaction] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        item = (action.get("addChatItemAction") or {}).get("item")
        if not isinstance(item, dict):
            continue
        for renderer_key, kind in REACTION_RENDERERS.items():
            renderer = item.get(renderer_key)
            if not isinstance(renderer, dict):
                continue
            ext_id = renderer.get("id")
            ts_usec = renderer.get("timestampUsec")
            if not ext_id or ts_usec is None:
                continue
            try:
                ts = datetime.fromtimestamp(int(ts_usec) / 1_000_000, UTC)
            except (TypeError, ValueError, OSError, OverflowError):
                continue
            amount, currency = parse_purchase_amount(
                (renderer.get("purchaseAmountText") or {}).get("simpleText")
            )
            out.append(
                RawReaction(
                    platform="youtube",
                    ext_id=str(ext_id),
                    ts_utc=ts,
                    kind=kind,
                    amount=amount,
                    currency=currency,
                )
            )
            break
    return out


class ChatProcess(Protocol):
    """The slice of :class:`asyncio.subprocess.Process` this module uses."""

    returncode: int | None

    async def wait(self) -> int: ...

    def kill(self) -> None: ...


ChatLauncher = Callable[[str, Path], Awaitable[ChatProcess]]
MetadataFetch = Callable[[str], Awaitable[dict[str, Any]]]


async def _launch_ytdlp(video_id: str, out_dir: Path) -> asyncio.subprocess.Process:
    """Start ``python -m yt_dlp`` writing the live chat into ``out_dir``.

    ``sys.executable -m yt_dlp`` (not a ``yt-dlp`` console script on PATH) so
    the process always uses this venv's yt-dlp — no new dependency, no PATH
    assumption.

    stdout+stderr go to a FILE, not a pipe: nothing reads the pipe while the
    tail loop runs, and a full pipe buffer would deadlock a download that is
    meant to last the whole broadcast.
    """
    settings = get_settings()
    log_path = out_dir / "ytdlp.log"
    args = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--skip-download",
        "--write-subs",
        "--sub-langs",
        "live_chat",
        "--no-playlist",
        "--no-progress",
        "--no-warnings",
        # Chat fragments 503 intermittently (see youtube_replay.py); retry
        # inside the run instead of tearing the whole stream down.
        "--fragment-retries",
        "5",
        "-o",
        str(out_dir / "%(id)s.%(ext)s"),
        _video_url(video_id),
    ]
    if settings.ytdlp_cookies_from_browser:
        args[3:3] = ["--cookies-from-browser", settings.ytdlp_cookies_from_browser]
    log_handle = log_path.open("wb")
    try:
        return await asyncio.create_subprocess_exec(
            *args, stdout=log_handle, stderr=asyncio.subprocess.STDOUT
        )
    finally:
        # The child holds its own descriptor; this copy must not stay open or
        # the log file cannot be replaced/removed later on Windows.
        log_handle.close()


async def _fetch_metadata(video_id: str) -> dict[str, Any]:
    """One yt-dlp metadata extraction, off the event loop.

    ``process=False`` skips format selection and the player-JS work — measured
    identical output for the two fields we need (``live_status``,
    ``concurrent_view_count``) at 1.7 s per call, and it keeps the request
    footprint on YouTube as small as possible.

    Deliberately NOT passing ``player_skip``/``skip`` extractor args: measured
    on 2026-09-09 that they trip YouTube's "Sign in to confirm you're not a
    bot" check while the plain call succeeds.
    """
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover — environment error
        raise RuntimeError(ERR_YTDLP_MISSING) from exc

    settings = get_settings()
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noprogress": True,
        "noplaylist": True,
    }
    if settings.ytdlp_cookies_from_browser:
        opts["cookiesfrombrowser"] = (settings.ytdlp_cookies_from_browser,)

    def _run() -> dict[str, Any]:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(_video_url(video_id), download=False, process=False) or {}

    return await asyncio.to_thread(_run)


def classify_exit(returncode: int | None, log_tail: str) -> tuple[str, str]:
    """Decide what a finished yt-dlp process means.

    Returns ``(kind, message)`` where kind is:

    - ``"ended"``  — the broadcast/chat finished normally: stop the loop;
    - ``"blocked"`` — YouTube's anti-bot check: keep looping slowly with a
      loud message (a fast retry cannot fix it, dying loses the session);
    - ``"wait"``   — not live yet / temporarily offline: relaunch with backoff;
    - ``"fatal"``  — wrong or inaccessible video: raise, do not spin;
    - ``"retry"``  — anything else (network, 5xx): relaunch with backoff.
    """
    if _RENAME_MARKER in log_tail:
        # Windows: reader vs. rename race. The chat bytes are already on disk.
        return "ended", "kết thúc (không đổi tên được file tạm — dữ liệu đã đọc xong)"
    if returncode == 0:
        return "ended", "chat trực tiếp đã đóng (luồng kết thúc)"
    if "No module named yt_dlp" in log_tail:
        # Config error, not an outage: retrying every 60 s forever would only
        # bury the one line that says what to fix.
        return "fatal", ERR_YTDLP_MISSING
    if any(m in log_tail for m in _BOT_MARKERS):
        return "blocked", ERR_BOT_CHECK
    if any(m in log_tail for m in _FATAL_MARKERS):
        return "fatal", ERR_UNAVAILABLE
    if any(m in log_tail for m in _WAIT_MARKERS):
        return "wait", "luồng chưa phát trực tiếp — chờ và thử lại"
    return "retry", f"yt-dlp thoát mã {returncode}"


class YouTubeYtdlpClient:
    """Live chat + concurrent viewers for one YouTube broadcast, via yt-dlp.

    Same surface as :class:`livelift.ingest.youtube.YouTubeLiveChatClient` so
    :mod:`livelift.ingest.runner` can use either: ``iter_comments``,
    ``iter_viewers``, ``get_active_live_chat_id``, ``last_error``, ``aclose``.

    ``chat_launcher`` and ``metadata_fetch`` are injection seams — the tests
    drive the whole loop with a fake process that writes real chat lines, so
    no test touches the network.
    """

    def __init__(
        self,
        *,
        chat_launcher: ChatLauncher | None = None,
        metadata_fetch: MetadataFetch | None = None,
        workdir: str | Path | None = None,
        tail_poll_s: float = TAIL_POLL_S,
    ) -> None:
        self._launch = chat_launcher or _launch_ytdlp
        self._metadata = metadata_fetch or _fetch_metadata
        self._workdir = Path(workdir) if workdir is not None else None
        self._tail_poll_s = tail_poll_s
        self._seen: deque[str] = deque(maxlen=SEEN_IDS_MAX)
        self._seen_set: set[str] = set()
        self._temp_dirs: list[Path] = []
        self._closed = False
        #: Outcome of the most recent yt-dlp lifetime, set by :meth:`_run_once`.
        self._last_exit: tuple[str, str] = ("retry", "chưa chạy lần nào")
        #: The yt-dlp process currently downloading chat, if any.
        self._proc: ChatProcess | None = None
        #: Most recent error description (None = healthy); the runner heartbeat
        #: prints it every 60 s.
        self.last_error: str | None = None
        #: True once a live viewer count was seen to be hidden — the reason the
        #: 'ticks' signal will be missing in the coverage matrix.
        self.viewers_hidden = False
        # A previous runner may have been killed before it could delete its
        # raw chat; clean that up now rather than leaving it on disk forever.
        sweep_stale_temp_dirs(self._workdir)

    # -- interface parity with the API client --------------------------------

    async def get_active_live_chat_id(self, video_id: str) -> str:
        """Preflight: confirm the video is live and has a live chat.

        yt-dlp has no ``activeLiveChatId`` concept — YouTube's chat continuation
        token is handled inside the downloader and never surfaces. This returns
        the video id itself so callers keep one interface; the value of the call
        is the CHECK, which fails with an actionable Vietnamese message.
        """
        info = await self._metadata(video_id)
        status = info.get("live_status")
        if status not in ("is_live", "is_upcoming"):
            raise RuntimeError(f"{ERR_NOT_LIVE} (live_status={status!r})")
        subs = info.get("subtitles") or {}
        if "live_chat" not in subs:
            raise RuntimeError(ERR_NO_CHAT)
        return str(video_id)

    async def iter_comments(self, video_id: str) -> AsyncIterator[RawComment]:
        """Yield live chat messages until the broadcast's chat closes.

        One yt-dlp process per attempt, tailed from disk; on any recoverable
        exit the process is relaunched with exponential backoff and the loop
        continues. Duplicates from the reconnect backlog are dropped in-process.
        """
        backoff = Backoff(base_s=RELAUNCH_BASE_S, cap_s=RELAUNCH_CAP_S)
        try:
            while not self._closed:
                out_dir = self._new_temp_dir()
                try:
                    async for comment in self._run_once(video_id, out_dir):
                        yield comment
                    kind, message = self._last_exit
                except OSError as exc:
                    # Failing to SPAWN yt-dlp (no fd, no memory, no temp space)
                    # is exactly what the relaunch loop exists for — a blip must
                    # not end a 90-minute session.
                    kind, message = "retry", f"không khởi động được yt-dlp: {type(exc).__name__}"
                finally:
                    self._cleanup(out_dir)
                if kind == "ended":
                    logger.info("live chat kết thúc: %s", message)
                    self.last_error = None
                    return
                if kind == "fatal":
                    raise RuntimeError(message)
                self.last_error = message
                delay = BLOCKED_BACKOFF_S if kind == "blocked" else backoff.next_delay()
                logger.warning(
                    "yt-dlp live chat dừng (%s: %s) — chạy lại sau %.0fs", kind, message, delay
                )
                await asyncio.sleep(delay)
        finally:
            self._cleanup_all()

    async def _run_once(self, video_id: str, out_dir: Path) -> AsyncIterator[RawComment]:
        """One yt-dlp lifetime: launch, tail to disk, drain, classify."""
        proc = await self._launch(video_id, out_dir)
        # Tracked so :meth:`aclose` can kill it even when this generator is
        # abandoned rather than closed — see the note there.
        self._proc = proc
        pos = 0
        pending = b""
        try:
            while True:
                data, pos = _read_new_bytes(out_dir, pos)
                if data:
                    pending += data
                    *lines, pending = pending.split(b"\n")
                    for raw in lines:
                        for comment in parse_live_chat_actions(raw.decode("utf-8", "replace")):
                            if self._mark_seen(comment.ext_id):
                                self.last_error = None
                                yield comment
                    continue  # keep draining while bytes keep coming
                if proc.returncode is not None:
                    break
                await asyncio.sleep(self._tail_poll_s)
            # Final drain: the .part has just been renamed to its final name.
            data, pos = _read_new_bytes(out_dir, pos)
            for raw in (pending + data).split(b"\n"):
                for comment in parse_live_chat_actions(raw.decode("utf-8", "replace")):
                    if self._mark_seen(comment.ext_id):
                        yield comment
        finally:
            await _kill(proc)
            if self._proc is proc:
                self._proc = None
        self._last_exit = classify_exit(proc.returncode, _log_tail(out_dir))

    async def iter_viewers(self, video_id: str, every_s: float = 30.0) -> AsyncIterator[RawTick]:
        """Yield concurrent-viewer snapshots from yt-dlp metadata refreshes.

        HONESTY RULE: when a channel hides its viewer count, yt-dlp returns no
        ``concurrent_view_count`` and this yields NOTHING — never a 0. With no
        ticks stored, :func:`livelift.core.signals.assess` reports the ``ticks``
        signal as missing and marks "nhịp phiên" / "tỷ lệ nhấp" unavailable,
        which is the truthful outcome. ``last_error`` says so in Vietnamese so
        the operator sees it in the heartbeat instead of discovering a flat
        line after the session.
        """
        backoff = Backoff(base_s=every_s, cap_s=max(every_s, RELAUNCH_CAP_S))
        while not self._closed:
            try:
                info = await self._metadata(video_id)
            except Exception as exc:  # noqa: BLE001 — a poll failure must not kill the run
                delay = backoff.next_delay()
                self.last_error = f"đếm người xem lỗi: {type(exc).__name__}"
                logger.warning(
                    "viewer poll failed: %s; thử lại sau %.1fs", type(exc).__name__, delay
                )
                await asyncio.sleep(delay)
                continue
            backoff.reset()
            status = info.get("live_status")
            viewers = info.get("concurrent_view_count")
            if viewers is not None:
                self.viewers_hidden = False
                self.last_error = None
                yield RawTick(platform="youtube", ts_utc=datetime.now(UTC), viewers=float(viewers))
            elif status in ("is_live", "is_upcoming"):
                if not self.viewers_hidden:
                    logger.warning("%s", ERR_VIEWERS_HIDDEN)
                self.viewers_hidden = True
                self.last_error = ERR_VIEWERS_HIDDEN
            else:
                logger.info(
                    "buổi phát đã kết thúc (live_status=%s); dừng vòng đếm người xem", status
                )
                return
            await asyncio.sleep(every_s)

    async def aclose(self) -> None:
        """Stop the download and delete every raw-chat file this client made.

        Must not rely on ``iter_comments``' own ``finally``: when the runner
        cancels the comment pump, the exception is raised in the *consumer*,
        which leaves the async generator merely suspended — Python finalizes it
        later (or never, at interpreter exit). Measured in a live-fire run: a
        yt-dlp process kept downloading and a temp directory with 182 KB of raw
        chat (author names included) survived the run. Killing the tracked
        process here is what makes the privacy promise hold on shutdown.
        """
        self._closed = True
        proc, self._proc = self._proc, None
        try:
            if proc is not None:
                await _kill(proc)
        finally:
            # Deleting the raw chat happens even if the kill path blows up or
            # this coroutine is itself cancelled.
            self._cleanup_all()

    # -- internals -----------------------------------------------------------

    def _mark_seen(self, ext_id: str) -> bool:
        """True the first time an id is seen (bounded memory)."""
        if ext_id in self._seen_set:
            return False
        if len(self._seen) == self._seen.maxlen:
            self._seen_set.discard(self._seen[0])
        self._seen.append(ext_id)
        self._seen_set.add(ext_id)
        return True

    def _new_temp_dir(self) -> Path:
        """A private directory for one yt-dlp lifetime.

        The chat file inside holds RAW comments with author names, so it never
        goes under ``data/`` and is removed as soon as the process is done.
        """
        parent = self._workdir
        if parent is not None:
            parent.mkdir(parents=True, exist_ok=True)
        path = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX, dir=str(parent) if parent else None))
        self._temp_dirs.append(path)
        return path

    def _cleanup(self, path: Path) -> None:
        """Remove one run's directory, retrying briefly.

        On Windows the files stay locked for a moment after the process that
        held them dies, and a single silent ``ignore_errors`` rmtree would then
        leave raw chat on disk. The last failure is logged loudly (path only —
        never contents) so a leak is visible instead of silent.
        """
        for attempt in range(3):
            shutil.rmtree(path, ignore_errors=True)
            if not path.exists():
                break
            time.sleep(0.1 * (attempt + 1))
        if path.exists():
            logger.error(
                "KHÔNG xóa được thư mục tạm chứa chat thô: %s — xóa thủ công ngay "
                "(file này chứa tên người bình luận)",
                path,
            )
        if path in self._temp_dirs:
            self._temp_dirs.remove(path)

    def _cleanup_all(self) -> None:
        for path in list(self._temp_dirs):
            self._cleanup(path)


def sweep_stale_temp_dirs(parent: Path | None = None, now: float | None = None) -> int:
    """Delete raw-chat directories left by runs that were killed before cleanup.

    Returns how many were removed. A directory counts as abandoned only when
    nothing inside it has been touched for :data:`STALE_TEMP_AFTER_S`, so a
    session running right now in another process is never deleted underneath it.
    """
    base = parent if parent is not None else Path(tempfile.gettempdir())
    now = time.time() if now is None else now
    removed = 0
    try:
        candidates = [p for p in base.glob(TEMP_PREFIX + "*") if p.is_dir()]
    except OSError:
        return 0
    for path in candidates:
        try:
            newest = max(
                (p.stat().st_mtime for p in path.rglob("*")),
                default=path.stat().st_mtime,
            )
        except OSError:
            continue
        if now - newest < STALE_TEMP_AFTER_S:
            continue  # still being written: an active run
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            removed += 1
    if removed:
        logger.warning(
            "đã dọn %d thư mục chat thô còn sót lại từ lần chạy bị kill đột ngột trước đó",
            removed,
        )
    return removed


async def _kill(proc: ChatProcess) -> None:
    """Stop a chat process and reap it; never raises."""
    if proc.returncode is not None:
        return
    with contextlib.suppress(Exception):
        proc.kill()
    with contextlib.suppress(Exception):
        await proc.wait()


def _chat_file(out_dir: Path) -> Path | None:
    """The live chat file: ``<id>.live_chat.json.part`` while downloading,
    ``<id>.live_chat.json`` after yt-dlp renames it at the end."""
    part = sorted(out_dir.glob("*.live_chat.json.part"))
    if part:
        return part[0]
    final = sorted(out_dir.glob("*.live_chat.json"))
    return final[0] if final else None


def _read_new_bytes(out_dir: Path, pos: int) -> tuple[bytes, int]:
    """Read whatever is new since ``pos``, then CLOSE the file.

    Closing every time is not tidiness: on Windows an open handle makes
    yt-dlp's final rename fail with ``WinError 32`` (verified — 3 retries then
    rc=1). Binary mode keeps the byte offset valid across the rename and lets
    a multi-byte character split across two reads survive: only complete
    ``\\n``-terminated lines are decoded by the caller.
    """
    path = _chat_file(out_dir)
    if path is None:
        return b"", pos
    try:
        with path.open("rb") as fh:
            fh.seek(pos)
            data = fh.read()
    except OSError:
        # File is mid-rename, or briefly locked; the next poll picks it up.
        return b"", pos
    return data, pos + len(data)


def _log_tail(out_dir: Path) -> str:
    try:
        text = (out_dir / "ytdlp.log").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-LOG_TAIL_CHARS:]
