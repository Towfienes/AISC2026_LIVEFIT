"""Facebook Live ingestion via the Graph API (own Page, Page access token).

Verified facts encoded here (docs/research/2026-08-24-apis-competition.md §b):

- The old SSE live-comments stream is gone; official best practice is to
  continually poll ``GET /{live-video-id}/comments`` with
  ``order=reverse_chronological``.
- ``live_filter`` MUST be ``no_filter``: the default filtering silently
  drops "low quality" comments, which for us is lost purchase-intent data.
- A ``since`` cursor (unix seconds) de-duplicates across polls; because the
  cursor has 1-second granularity a recent-id set guards the boundary.
- Viewer count comes from ``GET /{live-video-id}?fields=live_views``.
- An app in Development Mode reads its own Page with no App Review, using a
  Page access token (``pages_read_user_content`` for viewers' comments).

Raw comment text stays in memory only; scrubbing happens in the sink
(see :mod:`livelift.ingest.base`). The commenter's id (``from``) is dropped
at normalization (description §11.2).
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx

from livelift.config import get_settings
from livelift.ingest.base import AUTH_STATUSES, Backoff, RawComment, RawTick, http_status

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com"
DEFAULT_POLL_S = 5.0
_SEEN_IDS_MAX = 2048
# Error handling: an expired/invalid Page token cannot be fixed by retrying —
# pause long and tell the operator what to do; 429/5xx/transport errors get
# exponential backoff with a ceiling.
AUTH_BACKOFF_S = 60.0
RETRY_CAP_S = 60.0


def _is_auth_error(exc: httpx.HTTPError) -> bool:
    """True for credential/permission failures. The Graph API answers an
    expired token with 401/403 OR with HTTP 400 + an OAuthException body
    (error code 190), so the status code alone is not enough."""
    status = http_status(exc)
    if status in AUTH_STATUSES:
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            body = exc.response.json()
        except ValueError:
            return False
        err = body.get("error") if isinstance(body, dict) else None
        if not isinstance(err, dict):
            return False
        return err.get("type") == "OAuthException" or err.get("code") == 190
    return False


def _auth_error_message(exc: httpx.HTTPError) -> str:
    """Operator-facing (Vietnamese): what broke and what to do about it."""
    status = http_status(exc)
    return (
        f"LỖI Facebook Graph API (HTTP {status}): Page access token hết hạn hoặc thiếu quyền. "
        "Tạo token mới với quyền pages_read_user_content rồi cập nhật "
        "FACEBOOK_PAGE_ACCESS_TOKEN trong .env."
    )


def _parse_graph_time(value: str) -> datetime:
    """Parse a Graph API timestamp like ``2026-08-24T13:05:42+0000`` to UTC."""
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        ts = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def parse_comment(item: dict[str, Any]) -> RawComment | None:
    """Parse one Graph comment object into a :class:`RawComment`.

    Pure function. Returns ``None`` for comments without a message (e.g.
    sticker-only). The ``from`` field is present in the raw object but
    deliberately ignored — the author id is dropped here, at normalization,
    and never reaches storage or transmission.
    """
    text = item.get("message")
    created = item.get("created_time")
    ext_id = item.get("id")
    if not text or not created or not ext_id:
        return None
    return RawComment(
        platform="facebook",
        ext_id=str(ext_id),
        ts_utc=_parse_graph_time(str(created)),
        text=str(text),
        author_ext_id=None,  # dropped at normalization — never transmitted
    )


class FacebookLiveClient:
    """Async client for live-video comments and viewer snapshots.

    Uses a Page access token and Graph version from :func:`get_settings`
    unless passed explicitly. An injected ``httpx.AsyncClient`` makes the
    class testable without network access.
    """

    def __init__(
        self,
        page_access_token: str | None = None,
        graph_version: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if page_access_token is None or graph_version is None:
            settings = get_settings()
            if page_access_token is None:
                page_access_token = settings.facebook_page_access_token
            if graph_version is None:
                graph_version = settings.facebook_graph_version
        self._token = page_access_token
        version = graph_version
        self._base = f"{GRAPH_BASE}/{version}"
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None
        #: Most recent error description (None = healthy); shown by the
        #: runner heartbeat so an operator sees a stuck loop without grepping.
        self.last_error: str | None = None

    async def _handle_poll_error(self, what: str, exc: httpx.HTTPError, backoff: Backoff) -> None:
        """Classify a polling failure, record it for the heartbeat, and sleep.

        Auth failures (expired token, missing permission): red Vietnamese
        error + long fixed pause — an operator must rotate the token, no
        amount of fast retrying helps. 429/5xx/transport: exponential backoff
        with a ceiling.
        """
        if _is_auth_error(exc):
            self.last_error = _auth_error_message(exc)
            logger.error("%s — tạm dừng %.0fs rồi thử lại.", self.last_error, AUTH_BACKOFF_S)
            await asyncio.sleep(AUTH_BACKOFF_S)
            return
        status = http_status(exc)
        delay = backoff.next_delay()
        detail = f"HTTP {status}" if status is not None else type(exc).__name__
        self.last_error = f"{what}: {detail}"
        logger.warning("%s failed: %s; retrying in %.1fs", what, detail, delay)
        await asyncio.sleep(delay)

    async def iter_comments(
        self, live_video_id: str, poll_s: float = DEFAULT_POLL_S
    ) -> AsyncIterator[RawComment]:
        """Yield comments by polling with a ``since`` cursor.

        ``live_filter=no_filter`` is non-negotiable (see module docstring).
        Comments arrive reverse-chronological; each poll's batch is re-sorted
        ascending before yielding so downstream sees monotone-ish time order.
        """
        since: int | None = None
        seen: deque[str] = deque(maxlen=_SEEN_IDS_MAX)
        seen_set: set[str] = set()
        backoff = Backoff(base_s=poll_s, cap_s=max(poll_s, RETRY_CAP_S))
        while True:
            params: dict[str, str] = {
                "order": "reverse_chronological",
                "live_filter": "no_filter",
                "fields": "id,message,created_time",
                "limit": "100",
            }
            if since is not None:
                params["since"] = str(since)
            try:
                data = await self._get(f"/{live_video_id}/comments", params)
            except httpx.HTTPError as exc:
                await self._handle_poll_error("comment poll", exc, backoff)
                continue
            self.last_error = None
            backoff.reset()

            batch: list[RawComment] = []
            for item in data.get("data") or []:
                comment = parse_comment(item)
                if comment is None or comment.ext_id in seen_set:
                    continue
                if len(seen) == seen.maxlen:
                    seen_set.discard(seen[0])
                seen.append(comment.ext_id)
                seen_set.add(comment.ext_id)
                batch.append(comment)

            for comment in sorted(batch, key=lambda c: c.ts_utc):
                yield comment

            if batch:
                newest = max(c.ts_utc for c in batch)
                # 1s overlap on purpose: the seen-id set absorbs duplicates,
                # a forward-only cursor would drop same-second stragglers.
                since = int(newest.timestamp())
            await asyncio.sleep(poll_s)

    async def iter_viewers(
        self, live_video_id: str, every_s: float = 30.0
    ) -> AsyncIterator[RawTick]:
        """Yield ``live_views`` snapshots every ``every_s`` seconds."""
        backoff = Backoff(base_s=every_s, cap_s=max(every_s, RETRY_CAP_S))
        while True:
            try:
                data = await self._get(f"/{live_video_id}", {"fields": "live_views,status"})
                viewers = data.get("live_views")
                if viewers is not None:
                    yield RawTick(
                        platform="facebook",
                        ts_utc=datetime.now(UTC),
                        viewers=float(viewers),
                    )
                elif data.get("status") in {"VOD", "PROCESSING"}:
                    logger.info("live video ended (status=%s); stopping", data["status"])
                    return
                self.last_error = None
                backoff.reset()
            except httpx.HTTPError as exc:
                await self._handle_poll_error("viewer poll", exc, backoff)
                continue
            await asyncio.sleep(every_s)

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        resp = await self._client.get(
            self._base + path, params={**params, "access_token": self._token}
        )
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
