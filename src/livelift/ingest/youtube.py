"""YouTube Live ingestion via the official Live Streaming API.

Verified facts encoded here (docs/research/2026-08-24-apis-competition.md §a):

- ``liveChatMessages.streamList`` is the recommended path since July 2025
  (server push, one connection per session). This client is structured so
  that :meth:`YouTubeLiveChatClient.stream_comments` can be filled in later;
  until then :meth:`iter_comments` uses ``liveChatMessages.list`` polling.
- The ``list`` fallback MUST honor ``pollingIntervalMillis`` from each
  response. A fixed 5s poll over a 90-minute session costs > 5,000 of the
  10,000 daily quota units — never hardcode the interval.
- ``activeLiveChatId`` is fetched via ``videos.list part=liveStreamingDetails``
  (1 unit), NEVER via ``search.list`` (capped at 100 calls/day).
- Concurrent viewers come from the same ``videos.list`` call's
  ``concurrentViewers`` field, polled every 30 s.

Raw comment text stays in memory only; scrubbing happens in the sink
(see :mod:`livelift.ingest.base`). Author channel ids are dropped at
normalization (description §11.2).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx

from livelift.config import get_settings
from livelift.ingest.base import RawComment, RawTick

logger = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/youtube/v3"
# Community-measured cost of one liveChatMessages.list call (Google no longer
# publishes it); used for quota-awareness logging only.
EST_UNITS_PER_LIST_CALL = 5
DEFAULT_POLL_FLOOR_MS = 2000  # safety floor if the API omits pollingIntervalMillis


def parse_live_chat_message(item: dict[str, Any]) -> RawComment | None:
    """Parse one ``liveChatMessage`` resource into a :class:`RawComment`.

    Pure function. Returns ``None`` for items without display content
    (deleted messages, non-text events). ``authorDetails`` is present in the
    resource but deliberately ignored — the author id is dropped here, at
    normalization, and never reaches storage or transmission.
    """
    snippet = item.get("snippet") or {}
    text = snippet.get("displayMessage")
    published = snippet.get("publishedAt")
    ext_id = item.get("id")
    if not text or not published or not ext_id:
        return None
    ts = datetime.fromisoformat(published).astimezone(UTC)
    return RawComment(
        platform="youtube",
        ext_id=str(ext_id),
        ts_utc=ts,
        text=str(text),
        author_ext_id=None,  # dropped at normalization — never transmitted
    )


class YouTubeLiveChatClient:
    """Async client for live chat messages and concurrent-viewer snapshots.

    Auth is an API key (read-only public data) from :func:`get_settings`
    unless passed explicitly. An injected ``httpx.AsyncClient`` makes the
    class testable without network access.
    """

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else get_settings().youtube_api_key
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None
        self._list_calls = 0

    async def get_active_live_chat_id(self, video_id: str) -> str:
        """Resolve ``activeLiveChatId`` via ``videos.list`` (NOT search.list)."""
        data = await self._get("/videos", {"part": "liveStreamingDetails", "id": video_id})
        items = data.get("items") or []
        if not items:
            raise RuntimeError(f"video {video_id} not found or not accessible")
        details = items[0].get("liveStreamingDetails") or {}
        chat_id = details.get("activeLiveChatId")
        if not chat_id:
            raise RuntimeError(f"video {video_id} has no active live chat (not live?)")
        return str(chat_id)

    async def iter_comments(self, video_id: str) -> AsyncIterator[RawComment]:
        """Yield chat messages by polling ``liveChatMessages.list``.

        Honors ``pollingIntervalMillis`` from every response and continues
        with ``nextPageToken``. Logs estimated quota consumption every 50
        calls so a quota-hungry session is visible before it exhausts the
        10,000-unit daily budget.
        """
        chat_id = await self.get_active_live_chat_id(video_id)
        page_token: str | None = None
        while True:
            params: dict[str, str] = {
                "liveChatId": chat_id,
                "part": "id,snippet",
                "maxResults": "500",
            }
            if page_token:
                params["pageToken"] = page_token
            try:
                data = await self._get("/liveChat/messages", params)
            except httpx.HTTPError as exc:
                logger.warning("liveChatMessages.list failed: %s; retrying", type(exc).__name__)
                await asyncio.sleep(DEFAULT_POLL_FLOOR_MS / 1000)
                continue

            self._list_calls += 1
            if self._list_calls % 50 == 0:
                logger.info(
                    "quota: %d list calls (~%d units est.) this run",
                    self._list_calls,
                    self._list_calls * EST_UNITS_PER_LIST_CALL,
                )

            for item in data.get("items") or []:
                comment = parse_live_chat_message(item)
                if comment is not None:
                    yield comment

            if data.get("offlineAt"):
                logger.info("live chat ended (offlineAt set); stopping comment loop")
                return

            page_token = data.get("nextPageToken") or page_token
            interval_ms = int(data.get("pollingIntervalMillis") or DEFAULT_POLL_FLOOR_MS)
            await asyncio.sleep(max(interval_ms, DEFAULT_POLL_FLOOR_MS) / 1000)

    async def stream_comments(self, video_id: str) -> AsyncIterator[RawComment]:
        """Preferred path: ``liveChatMessages.streamList`` (server push).

        NOT YET IMPLEMENTED. Recommended by Google since 2025-07-14: one
        long-lived server-streaming HTTP connection per session instead of
        ~1,000 polled calls, resumable after disconnect by passing the last
        ``nextPageToken`` as ``pageToken``. Implementation sketch: open
        ``GET {API_BASE}/liveChat/messages/stream`` with the same params as
        ``iter_comments``, read the chunked JSON stream via
        ``client.stream(...)``, yield parsed messages, reconnect with the
        resume token on drop. Until implemented, callers use
        :meth:`iter_comments` (quota-honoring polling fallback).
        """
        raise NotImplementedError("streamList transport not implemented yet")
        yield  # pragma: no cover — makes this an async generator for typing

    async def iter_viewers(self, video_id: str, every_s: float = 30.0) -> AsyncIterator[RawTick]:
        """Yield ``concurrentViewers`` snapshots every ``every_s`` seconds
        via ``videos.list part=liveStreamingDetails`` (1 unit per call)."""
        while True:
            try:
                data = await self._get("/videos", {"part": "liveStreamingDetails", "id": video_id})
                items = data.get("items") or []
                details = (items[0].get("liveStreamingDetails") or {}) if items else {}
                viewers = details.get("concurrentViewers")
                if viewers is not None:
                    yield RawTick(
                        platform="youtube",
                        ts_utc=datetime.now(UTC),
                        viewers=float(viewers),
                    )
                elif details.get("actualEndTime"):
                    logger.info("broadcast ended (actualEndTime set); stopping viewer loop")
                    return
            except httpx.HTTPError as exc:
                logger.warning("viewer poll failed: %s; retrying", type(exc).__name__)
            await asyncio.sleep(every_s)

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        resp = await self._client.get(API_BASE + path, params={**params, "key": self._api_key})
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
