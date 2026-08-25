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
   never logged — log lines carry lengths and counts only.
2. The author's external id is never transmitted (description §11.2: no
   per-person behavior chains). Platform parsers set ``author_ext_id`` to
   ``None`` at normalization time, and the sink payload has no author field
   at all, so even a mis-parsed comment cannot leak an author id.

Timestamps: ``ts_utc`` is the *platform* timestamp, parsed to an aware UTC
datetime. The server stamps its own authoritative arrival time on insert
(project rule 7) — the platform timestamp is diagnostic metadata.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

from livelift.ingest.pii import scrub

logger = logging.getLogger(__name__)


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
    NEVER raises: on final failure it logs (counts/lengths only) and returns
    ``False`` so the caller's read loop keeps running.
    """

    def __init__(
        self,
        api_url: str,
        session_id: str,
        client: httpx.AsyncClient | None = None,
        max_tries: int = 3,
        base_delay_s: float = 0.5,
        timeout_s: float = 10.0,
    ) -> None:
        self._base = api_url.rstrip("/")
        self._session_id = session_id
        self._client = client or httpx.AsyncClient(timeout=timeout_s)
        self._owns_client = client is None
        self._max_tries = max_tries
        self._base_delay_s = base_delay_s

    async def post_comment(self, comment: RawComment) -> bool:
        # HARD RULE 1: scrub INSIDE the ingest process, before any transmit.
        result = scrub(comment.text)
        payload: dict[str, Any] = {
            "platform": comment.platform,
            "ext_id": comment.ext_id,
            "ts_utc": _to_utc_iso(comment.ts_utc),
            "text_scrubbed": result.text,
            "pii_kinds": sorted(result.counts),
        }
        # NOTE: no author field, ever (description §11.2).
        ok = await self._post(f"/sessions/{self._session_id}/comments", payload)
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
        return await self._post(f"/sessions/{self._session_id}/ticks", payload)

    async def _post(self, path: str, payload: dict[str, Any]) -> bool:
        """POST with retry. Returns False instead of raising on final failure."""
        url = self._base + path
        for attempt in range(1, self._max_tries + 1):
            try:
                resp = await self._client.post(url, json=payload)
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
        logger.error("sink POST %s dropped after %d tries", path, self._max_tries)
        return False

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
