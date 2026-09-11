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
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

from livelift.ingest.pii import scrub

logger = logging.getLogger(__name__)

# HTTP statuses that mean "fix your credentials/quota", where retrying fast
# only burns quota and floods logs (401 unauthorized, 403 forbidden/quota).
AUTH_STATUSES: frozenset[int] = frozenset({401, 403})

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
        """POST with retry. On final failure the payload goes to the spool
        file (scrubbed data only) and False is returned — never raises."""
        url = self._base + path
        for attempt in range(1, self._max_tries + 1):
            try:
                resp = await self._client.post(url, json=payload, headers=self._headers)
                if resp.status_code < 400:
                    return True
                logger.warning(
                    "sink POST %s -> HTTP %d (attempt %d/%d)",
                    path,
                    resp.status_code,
                    attempt,
                    self._max_tries,
                )
            except Exception as exc:  # noqa: BLE001 — sink must never raise out
                logger.warning(
                    "sink POST %s failed: %s (attempt %d/%d)",
                    path,
                    type(exc).__name__,
                    attempt,
                    self._max_tries,
                )
            if attempt < self._max_tries:
                await asyncio.sleep(self._base_delay_s * 2 ** (attempt - 1))
        self._spool(kind, path, payload)
        return False

    def _spool(self, kind: str, path: str, payload: dict[str, Any]) -> None:
        """Append one undeliverable record to the local JSONL spool.

        The payload is already scrubbed (hard rule 1 holds for files too).
        Never raises — a spool failure is logged and the record is lost, but
        the read loop must survive.
        """
        if self._spool_path is None:
            logger.error("sink POST %s dropped after %d tries (spool tắt)", path, self._max_tries)
            return
        try:
            self._spool_path.parent.mkdir(parents=True, exist_ok=True)
            record = {"kind": kind, "path": path, "payload": payload}
            with self._spool_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.error(
                "sink POST %s thất bại sau %d lần thử VÀ không ghi được spool (%s) — mất bản ghi",
                path,
                self._max_tries,
                type(exc).__name__,
            )
            return
        logger.error(
            "API không nhận %s sau %d lần thử — đã ghi vào spool %s; gửi lại bằng: "
            "python -m livelift.ingest.spool_replay %s --api-base %s",
            kind,
            self._max_tries,
            self._spool_path,
            self._spool_path,
            self._base,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
