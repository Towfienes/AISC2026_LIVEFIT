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
from livelift.ingest.base import RawComment, RawTick

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com"
DEFAULT_POLL_S = 5.0
_SEEN_IDS_MAX = 2048


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
                logger.warning("comment poll failed: %s; retrying", type(exc).__name__)
                await asyncio.sleep(poll_s)
                continue

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
            except httpx.HTTPError as exc:
                logger.warning("viewer poll failed: %s; retrying", type(exc).__name__)
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
