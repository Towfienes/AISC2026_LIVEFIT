"""Normalized ingest primitives shared by every platform client.

Data flow (HARD project rule 1 — plan §1.4, description §11.3):

    platform API ──parse──> RawComment (raw text, in memory only)
                     │
                     ▼
              ApiSink.post_comment
                     │  scrub() runs HERE, inside the ingest process,
                     │  before ANY transmit or log line
                     ▼
              LiveLift API  (receives only scrubbed text + PII kind counts)

Two privacy invariants are enforced in this module:

1. ``scrub()`` is applied to the comment text inside :class:`ApiSink` before
   the HTTP request is built. Raw text never leaves the ingest process and is
   never logged — log lines carry lengths and counts only. The payload's
   ``text`` field therefore ALWAYS holds scrubbed text (the API re-scrubs as
   defense in depth; scrubbing is idempotent).
2. The author's external id is never transmitted (description §11.2: no
   per-person behavior chains). Platform parsers set ``author_ext_id`` to
   ``None`` at normalization time, and the sink payload has no author field
   at all, so even a mis-parsed comment cannot leak an author id.

Timestamps: ``ts_utc`` is the *platform* timestamp, parsed to an aware UTC
datetime. The server keeps it as the event time when present (block
attribution near a boundary follows the platform clock, not the delivery
delay); without it the server clock stamps the row.

Durability: a POST that fails all retries is appended to a local JSONL spool
file (``<spool_dir>/<session_id>.jsonl``) instead of being dropped. Records
hold only scrubbed payloads. Replay them later with
``python -m livelift.ingest.spool_replay`` — the server's (platform, ext_id)
idempotency makes re-sending safe.

Kho chết giữa phiên (sự cố 13/09/2026 — gói D-ĐỘ-BỀN). Khi cơ sở dữ liệu chết
mà API vẫn sống, mỗi POST trả 5xx sau khi chờ hết timeout. Cách cũ — luôn thử
đủ ``max_tries`` lần cho MỌI bản ghi — biến một sự cố kho thành một sự cố thu
thập: vòng đọc bình luận đứng lại hàng chục giây cho mỗi bình luận, đúng lúc
livestream đang đông nhất. Vì thế sink có hai trạng thái:

* **bình thường** — thử ``max_tries`` lần rồi mới spool;
* **chế độ spool** — sau :data:`SPOOL_MODE_AFTER_FAILURES` lần POST liên tiếp
  hỏng vì phía máy chủ (5xx hoặc đứt mạng), mọi bản ghi đi THẲNG vào file
  spool không chờ, và cứ :data:`SPOOL_MODE_PROBE_EVERY_S` giây mới thử lại
  một lần để dò xem máy chủ sống chưa. Nhịp đọc bình luận vì thế không đổi.

Phân loại lỗi (điều quan trọng nhất của gói này): 5xx và lỗi mạng là lỗi TẠM
THỜI — bản ghi phải được GIỮ trong spool; 401/403/404/409 là lỗi cấu hình —
vẫn giữ, vì sửa token/khởi động lại kho xong là nạp bù được; chỉ 400/422
(payload sai) mới bị vứt, vì gửi lại đúng payload đó thì vẫn sai, và một bản
ghi "độc" nằm trong spool sẽ làm mọi lần nạp bù sau này báo thất bại.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

from livelift.ingest.pii import scrub

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bí mật trong URL không được ra log của httpx — MỌI nền tảng
# ---------------------------------------------------------------------------

_BI_MAT_TRONG_QUERY = re.compile(
    r"(?i)\b(access_token|refresh_token|sign|key|api_key|apikey|client_secret|app_secret"
    r"|appsecret_proof)=[^&\s\"'<>]*"
)
"""Tham số bí mật mà các nền tảng đặt trong query string.

* Shopee: ``access_token``/``sign`` bắt buộc nằm trong query (lược đồ ký HMAC).
* YouTube Data API: khoá ``YOUTUBE_API_KEY`` đi bằng tham số ``key=``
  (``youtube.py``). Trước kiểm toán 17/09/2026 bộ lọc chỉ nằm trong
  ``shopee.py`` và chỉ biết ba tên của Shopee, nên runner CLI (mức INFO) vẫn in
  nguyên ``key=AIza...`` ra terminal mỗi lần poll người xem.

``\b`` giữ cho ``pageToken=``/``nextPageToken=`` (không bí mật) không bị đụng."""


class _GiauBiMatTrongLogHttpx(logging.Filter):
    """Che giá trị các tham số trong :data:`_BI_MAT_TRONG_QUERY` ở log ``httpx``.

    ``httpx`` ghi ``HTTP Request: GET <URL đầy đủ>`` ở mức INFO; runner CLI chạy
    ở mức INFO, và log đó hay bị dán vào nhật ký sự cố. Bộ lọc gắn vào logger
    ``httpx`` nên chạy TRƯỚC mọi handler; không bao giờ chặn bản ghi, chỉ sửa chữ.
    Nó nằm ở ``base.py`` — mô-đun mọi client nền tảng đều import — để không nền
    tảng nào phải nhớ tự cài.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 — bản ghi hỏng: để logging tự báo
            return True
        redacted = _BI_MAT_TRONG_QUERY.sub(r"\1=***", message)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


def _cai_bo_loc_log_httpx() -> None:
    """Gắn :class:`_GiauBiMatTrongLogHttpx` vào logger ``httpx`` (một lần)."""
    httpx_logger = logging.getLogger("httpx")
    if not any(isinstance(f, _GiauBiMatTrongLogHttpx) for f in httpx_logger.filters):
        httpx_logger.addFilter(_GiauBiMatTrongLogHttpx())


_cai_bo_loc_log_httpx()

# HTTP statuses that mean "fix your credentials/quota", where retrying fast
# only burns quota and floods logs (401 unauthorized, 403 forbidden/quota).
AUTH_STATUSES: frozenset[int] = frozenset({401, 403})

# Payload hỏng: gửi lại y hệt thì vẫn hỏng. Đây là những mã DUY NHẤT được phép
# làm mất một bản ghi — và mất thì phải kêu to (log ERROR), không im lặng.
PERMANENT_STATUSES: frozenset[int] = frozenset({400, 422})

SERVER_ERROR_MIN = 500
"""Từ mã này trở lên là "phía máy chủ hỏng" — luôn tạm thời, luôn giữ bản ghi."""

SPOOL_MODE_AFTER_FAILURES = 2
"""Số lần POST liên tiếp hỏng vì phía máy chủ trước khi chuyển sang chế độ spool."""

SPOOL_MODE_PROBE_EVERY_S = 30.0
"""Đang ở chế độ spool thì bao lâu mới thử gửi thật một lần để dò máy chủ."""

DEFAULT_SPOOL_DIR = Path("data") / "spool"


def http_status(exc: Exception) -> int | None:
    """Status code of an :class:`httpx.HTTPStatusError`, ``None`` for
    transport-level errors (DNS, timeout, connect)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None


class Backoff:
    """Exponential backoff with a ceiling. ``reset()`` after any success so a
    long-running loop recovers its fast cadence once the outage ends."""

    def __init__(self, base_s: float = 2.0, cap_s: float = 60.0) -> None:
        self._base_s = base_s
        self._cap_s = cap_s
        self._failures = 0

    def next_delay(self) -> float:
        delay = min(self._base_s * (2**self._failures), self._cap_s)
        self._failures += 1
        return delay

    def reset(self) -> None:
        self._failures = 0


@dataclass(frozen=True)
class RawComment:
    """A normalized comment from any platform. ``text`` is raw (unscrubbed)
    and must therefore never be persisted, transmitted, or logged directly —
    only :class:`ApiSink` (which scrubs first) may consume it.

    ``author_ext_id`` exists for in-process de-duplication only; parsers set
    it to ``None`` and it is never transmitted.
    """

    platform: str
    ext_id: str
    ts_utc: datetime
    text: str
    author_ext_id: str | None = None

    def __post_init__(self) -> None:
        if self.ts_utc.tzinfo is None:
            raise ValueError("RawComment.ts_utc must be timezone-aware (UTC)")


@dataclass(frozen=True)
class RawTick:
    """A viewer-count snapshot from any platform."""

    platform: str
    ts_utc: datetime
    viewers: float

    def __post_init__(self) -> None:
        if self.ts_utc.tzinfo is None:
            raise ValueError("RawTick.ts_utc must be timezone-aware (UTC)")


@dataclass(frozen=True)
class RawReaction:
    """A paid/visible audience event: Super Chat, gift, sticker, membership,
    like (schema value reserved — no current source provides likes).

    ``amount``/``currency`` are the PUBLIC purchase string the platform prints
    for everyone (e.g. "50.000 ₫") — not PII. There is deliberately NO author
    field on this type: parsers never read who sent the money (hard rule 1).
    """

    platform: str
    ext_id: str
    ts_utc: datetime
    kind: str  # superchat | gift | sticker | membership | like
    amount: float | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if self.ts_utc.tzinfo is None:
            raise ValueError("RawReaction.ts_utc must be timezone-aware (UTC)")


class IngestSink(Protocol):
    """Destination for normalized ingest events. Implementations must never
    raise out of ``post_*`` — a sink failure must not kill the read loop."""

    async def post_comment(self, comment: RawComment) -> bool:
        """Deliver one comment. Returns True on success, False on failure."""
        ...

    async def post_tick(self, tick: RawTick) -> bool:
        """Deliver one viewer snapshot. Returns True on success."""
        ...


def _to_utc_iso(ts: datetime) -> str:
    return ts.astimezone(UTC).isoformat()


class ApiSink:
    """Posts scrubbed events to the LiveLift API.

    - ``POST {api_url}/sessions/{session_id}/comments``
    - ``POST {api_url}/sessions/{session_id}/ticks``

    Retries each POST up to ``max_tries`` times with exponential backoff and
    NEVER raises: on final failure it appends the (already scrubbed) payload
    to the local spool file and returns ``False`` so the caller's read loop
    keeps running. ``spool_dir=None`` disables spooling.

    Auth: when ``token`` is None the INGEST_TOKEN setting is read; a non-empty
    token becomes an ``Authorization: Bearer`` header on every POST. Pass
    ``token=""`` to force auth off regardless of the environment.

    Trạng thái công khai cho người vận hành (heartbeat của runner đọc):
    ``spool_mode``, ``spooled``, ``dropped``, ``last_error``, ``spool_path``.
    """

    def __init__(
        self,
        api_url: str,
        session_id: str,
        client: httpx.AsyncClient | None = None,
        max_tries: int = 3,
        base_delay_s: float = 0.5,
        timeout_s: float = 10.0,
        spool_dir: str | os.PathLike[str] | None = DEFAULT_SPOOL_DIR,
        token: str | None = None,
        spool_mode_after: int = SPOOL_MODE_AFTER_FAILURES,
        probe_every_s: float = SPOOL_MODE_PROBE_EVERY_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base = api_url.rstrip("/")
        self._session_id = session_id
        self._client = client or httpx.AsyncClient(timeout=timeout_s)
        self._owns_client = client is None
        self._max_tries = max_tries
        self._base_delay_s = base_delay_s
        self._spool_path = (
            Path(spool_dir) / f"{session_id}.jsonl" if spool_dir is not None else None
        )
        if token is None:
            from livelift.config import get_settings  # lazy: needs pydantic-settings

            token = get_settings().ingest_token
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

        # --- trạng thái "phía máy chủ đang chết" -----------------------------
        self._spool_mode_after = max(1, int(spool_mode_after))
        self._probe_every_s = float(probe_every_s)
        self._clock = clock
        self._server_failures = 0
        self._spool_mode_since: float | None = None
        self._next_probe_at = 0.0
        self.spooled = 0
        """Số bản ghi đã ghi vào spool trong vòng đời sink này (đếm thật)."""
        self.dropped = 0
        """Số bản ghi bị vứt hẳn (payload sai, hoặc không ghi nổi spool)."""
        self.last_error: str | None = None
        """Mô tả tiếng Việt của sự cố gần nhất; None khi đang khỏe."""

    # --- trạng thái công khai -------------------------------------------------

    @property
    def spool_mode(self) -> bool:
        """True khi sink đã bỏ cuộc với máy chủ và đang ghi thẳng vào spool."""
        return self._spool_mode_since is not None

    @property
    def spool_path(self) -> Path | None:
        return self._spool_path

    @property
    def replay_command(self) -> str:
        """Lệnh nạp bù, in nguyên văn vào log để người vận hành copy được."""
        if self._spool_path is None:
            # Không có gì để nạp bù vì không có gì được giữ lại — nói thẳng thế,
            # thay vì in một lệnh trỏ vào hư không.
            return "(spool đang TẮT — không có file nào để nạp bù, dữ liệu đã mất)"
        return f"python -m livelift.ingest.spool_replay {self._spool_path} --api-base {self._base}"

    async def post_comment(self, comment: RawComment) -> bool:
        # HARD RULE 1: scrub INSIDE the ingest process, before any transmit.
        result = scrub(comment.text)
        payload: dict[str, Any] = {
            "platform": comment.platform,
            "ext_id": comment.ext_id,
            "ts_utc": _to_utc_iso(comment.ts_utc),
            # API contract: CommentIn.text — already scrubbed at this point.
            "text": result.text,
            "pii_kinds": sorted(result.counts),
        }
        # NOTE: no author field, ever (description §11.2).
        ok = await self._post(f"/sessions/{self._session_id}/comments", payload, kind="comment")
        if ok and result.has_pii:
            # Log counts only — never the text or any substring of it.
            logger.info("comment posted: len=%d pii_counts=%s", len(result.text), result.counts)
        return ok

    async def post_tick(self, tick: RawTick) -> bool:
        payload = {
            "platform": tick.platform,
            "ts_utc": _to_utc_iso(tick.ts_utc),
            "viewers": tick.viewers,
        }
        return await self._post(f"/sessions/{self._session_id}/ticks", payload, kind="tick")

    async def _post(self, path: str, payload: dict[str, Any], kind: str = "event") -> bool:
        """POST with retry. On failure the payload goes to the spool file
        (scrubbed data only) and False is returned — never raises.

        Ngoại lệ duy nhất cho "luôn giữ bản ghi": payload sai (400/422), xem
        :data:`PERMANENT_STATUSES`.
        """
        url = self._base + path
        # Máy chủ/kho đang chết và chưa tới lượt dò lại: ghi thẳng vào spool.
        # KHÔNG chờ thêm một vòng timeout nào nữa — vòng đọc bình luận phải
        # giữ nguyên nhịp, nếu không sự cố kho sẽ kéo theo sự cố thu thập.
        if self.spool_mode and self._clock() < self._next_probe_at:
            self._spool(kind, path, payload, reason="máy chủ đang hỏng — ghi thẳng vào spool")
            return False
        # Lúc đang dò thì chỉ thử MỘT lần: dò mà cũng chờ 3 vòng backoff thì
        # mất đúng cái vừa cứu được.
        tries = 1 if self.spool_mode else self._max_tries

        last_status: int | None = None
        last_exc_name: str | None = None
        for attempt in range(1, tries + 1):
            try:
                resp = await self._client.post(url, json=payload, headers=self._headers)
                if resp.status_code < 400:
                    self._note_server_ok()
                    return True
                last_status, last_exc_name = resp.status_code, None
                if resp.status_code in PERMANENT_STATUSES:
                    # Sai hợp đồng payload: thử lại vô nghĩa, spool cũng vô
                    # nghĩa (mọi lần nạp bù sau sẽ báo thất bại vì bản ghi này).
                    self._drop(kind, path, resp.status_code)
                    return False
                logger.warning(
                    "sink POST %s -> HTTP %d (attempt %d/%d)",
                    path,
                    resp.status_code,
                    attempt,
                    tries,
                )
            except Exception as exc:  # noqa: BLE001 — sink must never raise out
                last_status, last_exc_name = None, type(exc).__name__
                logger.warning(
                    "sink POST %s failed: %s (attempt %d/%d)",
                    path,
                    type(exc).__name__,
                    attempt,
                    tries,
                )
            if attempt < tries:
                await asyncio.sleep(self._base_delay_s * 2 ** (attempt - 1))

        server_side = last_status is None or last_status >= SERVER_ERROR_MIN
        if server_side:
            self._note_server_failure(last_status, last_exc_name)
        reason = f"HTTP {last_status}" if last_status is not None else f"lỗi mạng {last_exc_name}"
        self._spool(kind, path, payload, reason=reason)
        return False

    # --- theo dõi sức khỏe máy chủ -------------------------------------------

    def _note_server_ok(self) -> None:
        """POST thành công: xóa trạng thái hỏng, và NÓI ra là đã sống lại."""
        self._server_failures = 0
        self.last_error = None
        if self._spool_mode_since is None:
            return
        down_s = self._clock() - self._spool_mode_since
        self._spool_mode_since = None
        self._next_probe_at = 0.0
        logger.warning(
            "Máy chủ nhận dữ liệu TRỞ LẠI sau %.0f giây. %d bản ghi đang nằm trong spool và "
            "CHƯA có trong cơ sở dữ liệu — nạp bù ngay bằng: %s",
            down_s,
            self.spooled,
            self.replay_command,
        )

    def _note_server_failure(self, status: int | None, exc_name: str | None) -> None:
        """Đếm lỗi phía máy chủ; đủ ngưỡng thì chuyển sang chế độ spool."""
        self._server_failures += 1
        self.last_error = (
            f"máy chủ trả HTTP {status}"
            if status is not None
            else f"không gọi được API ({exc_name})"
        )
        if self._server_failures < self._spool_mode_after:
            return
        now = self._clock()
        first_time = self._spool_mode_since is None
        if first_time:
            self._spool_mode_since = now
        self._next_probe_at = now + self._probe_every_s
        if first_time:
            logger.error(
                "BÁO ĐỘNG: máy chủ LiveLift không nhận dữ liệu (%s) sau %d lần POST liên tiếp — "
                "bộ thu chuyển sang CHẾ ĐỘ SPOOL: bình luận và lượt xem từ giờ ghi thẳng vào %s "
                "và KHÔNG có trong cơ sở dữ liệu. Số liệu trên bàn điều khiển đang THIẾU. "
                "Sửa xong kho thì nạp bù bằng: %s",
                self.last_error,
                self._server_failures,
                self._spool_path
                if self._spool_path is not None
                else "(spool TẮT — ĐANG MẤT DỮ LIỆU)",
                self.replay_command,
            )

    def _drop(self, kind: str, path: str, status: int) -> None:
        """Vứt một bản ghi không bao giờ gửi được — và kêu to."""
        self.dropped += 1
        self.last_error = f"payload bị API từ chối vĩnh viễn (HTTP {status})"
        logger.error(
            "MẤT bản ghi %s: API từ chối payload với HTTP %d ở %s — gửi lại cũng vẫn sai nên "
            "KHÔNG ghi vào spool. Đây là lỗi hợp đồng giữa bộ thu và API, phải sửa code. "
            "Tổng số bản ghi đã mất: %d",
            kind,
            status,
            path,
            self.dropped,
        )

    def _spool(self, kind: str, path: str, payload: dict[str, Any], reason: str = "") -> None:
        """Append one undeliverable record to the local JSONL spool.

        The payload is already scrubbed (hard rule 1 holds for files too).
        Never raises — a spool failure is logged and the record is lost, but
        the read loop must survive.
        """
        if self._spool_path is None:
            self.dropped += 1
            logger.error(
                "MẤT bản ghi %s (%s): spool đang TẮT nên không có chỗ giữ lại. Tổng đã mất: %d",
                kind,
                reason or "không gửi được",
                self.dropped,
            )
            return
        try:
            self._spool_path.parent.mkdir(parents=True, exist_ok=True)
            record = {"kind": kind, "path": path, "payload": payload}
            with self._spool_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            self.dropped += 1
            logger.error(
                "sink POST %s thất bại (%s) VÀ không ghi được spool (%s) — MẤT bản ghi. "
                "Tổng đã mất: %d",
                path,
                reason or "không gửi được",
                type(exc).__name__,
                self.dropped,
            )
            return
        self.spooled += 1
        if self.spool_mode:
            # Đang ở chế độ spool thì mỗi bản ghi một dòng ERROR là ngập log;
            # lời cảnh báo to đã in lúc chuyển chế độ, heartbeat nhắc lại đều.
            logger.debug(
                "đã spool %s (%s) — tổng %d bản ghi chờ nạp bù", kind, reason, self.spooled
            )
            return
        logger.error(
            "API không nhận %s (%s) — đã ghi vào spool %s (tổng %d bản ghi chờ); gửi lại bằng: %s",
            kind,
            reason or "không gửi được",
            self._spool_path,
            self.spooled,
            self.replay_command,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
