"""Platform-client error handling: startup retry, auth-vs-transient
classification, exponential backoff, and the runner heartbeat error surface.

No network, no real sleeping: transports are httpx.MockTransport and
``asyncio.sleep`` is monkeypatched to record requested delays.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from types import SimpleNamespace

import httpx
import pytest

from livelift.ingest.facebook import AUTH_BACKOFF_S as FB_AUTH_BACKOFF_S
from livelift.ingest.facebook import FacebookLiveClient
from livelift.ingest.runner import Counters, _heartbeat
from livelift.ingest.youtube import AUTH_BACKOFF_S as YT_AUTH_BACKOFF_S
from livelift.ingest.youtube import CHAT_ID_MAX_TRIES, YouTubeLiveChatClient

YT_MESSAGE = {
    "id": "m1",
    "snippet": {"publishedAt": "2026-08-24T13:05:42Z", "displayMessage": "chốt đơn"},
}
FB_MESSAGE = {
    "id": "1_2",
    "message": "còn màu đen không",
    "created_time": "2026-08-24T13:05:42+0000",
}
CHAT_ID_JSON = {"items": [{"liveStreamingDetails": {"activeLiveChatId": "chat-1"}}]}


@pytest.fixture
def sleeps(monkeypatch):
    """Recorded asyncio.sleep delays; nothing actually waits."""
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


def _yt_client(handler) -> tuple[YouTubeLiveChatClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return YouTubeLiveChatClient(api_key="k", client=http), http


def _fb_client(handler) -> tuple[FacebookLiveClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return FacebookLiveClient(page_access_token="t", graph_version="v23.0", client=http), http


# --- get_active_live_chat_id: retry at start (defect: one blip killed it) ---


def test_chat_id_lookup_retries_transient_errors(sleeps):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json=CHAT_ID_JSON)

    async def run() -> str:
        client, http = _yt_client(handler)
        try:
            return await client.get_active_live_chat_id("vid")
        finally:
            await http.aclose()

    assert asyncio.run(run()) == "chat-1"
    assert calls["n"] == 3
    assert sleeps == [1.0, 2.0]  # exponential between attempts


def test_chat_id_lookup_fails_fast_on_auth_error_in_vietnamese(sleeps):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(403, json={"error": {"message": "quotaExceeded"}})

    async def run() -> str:
        client, http = _yt_client(handler)
        try:
            return await client.get_active_live_chat_id("vid")
        finally:
            await http.aclose()

    with pytest.raises(RuntimeError, match="LỖI YouTube API"):
        asyncio.run(run())
    assert calls["n"] == 1  # a bad key cannot be fixed by retrying
    assert sleeps == []


def test_chat_id_lookup_gives_up_after_max_tries(sleeps):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("down", request=request)

    async def run() -> str:
        client, http = _yt_client(handler)
        try:
            return await client.get_active_live_chat_id("vid")
        finally:
            await http.aclose()

    with pytest.raises(RuntimeError, match="thử chạy lại"):
        asyncio.run(run())
    assert calls["n"] == CHAT_ID_MAX_TRIES


# --- YouTube comment loop: 401/403 vs 5xx classification --------------------


def test_yt_comment_loop_auth_error_pauses_long_and_logs_red(sleeps, caplog):
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/videos"):
            return httpx.Response(200, json=CHAT_ID_JSON)
        polls["n"] += 1
        if polls["n"] == 1:
            return httpx.Response(401, json={"error": {"message": "keyInvalid"}})
        return httpx.Response(
            200, json={"items": [YT_MESSAGE], "offlineAt": "2026-08-24T14:00:00Z"}
        )

    async def run():
        client, http = _yt_client(handler)
        try:
            return [c async for c in client.iter_comments("vid")], client
        finally:
            await http.aclose()

    with caplog.at_level(logging.ERROR, logger="livelift.ingest.youtube"):
        comments, client = asyncio.run(run())
    assert [c.text for c in comments] == ["chốt đơn"]
    assert YT_AUTH_BACKOFF_S in sleeps  # long pause, not the 2s poll floor
    assert "LỖI YouTube API (HTTP 401)" in caplog.text
    assert client.last_error is None  # cleared by the successful poll


def test_yt_comment_loop_5xx_backs_off_exponentially(sleeps):
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/videos"):
            return httpx.Response(200, json=CHAT_ID_JSON)
        polls["n"] += 1
        if polls["n"] <= 2:
            return httpx.Response(500, json={"error": "down"})
        return httpx.Response(
            200, json={"items": [YT_MESSAGE], "offlineAt": "2026-08-24T14:00:00Z"}
        )

    async def run() -> list:
        client, http = _yt_client(handler)
        try:
            return [c async for c in client.iter_comments("vid")]
        finally:
            await http.aclose()

    comments = asyncio.run(run())
    assert len(comments) == 1
    assert sleeps[0] == 2.0  # poll floor
    assert sleeps[1] == 4.0  # doubled — not a flat retry forever


# --- Facebook: OAuthException (even as HTTP 400) is an auth error -----------


def test_fb_comment_loop_expired_token_pauses_long_and_logs_red(sleeps, caplog):
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        polls["n"] += 1
        if polls["n"] == 1:
            # Graph answers an expired token with HTTP 400 + OAuthException.
            return httpx.Response(
                400,
                json={"error": {"type": "OAuthException", "code": 190, "message": "expired"}},
            )
        return httpx.Response(200, json={"data": [FB_MESSAGE]})

    async def run():
        client, http = _fb_client(handler)
        try:
            async for comment in client.iter_comments("live-1", poll_s=1.0):
                return comment, client
        finally:
            await http.aclose()
        return None, client

    with caplog.at_level(logging.ERROR, logger="livelift.ingest.facebook"):
        comment, client = asyncio.run(run())
    assert comment is not None
    assert comment.text == "còn màu đen không"
    assert FB_AUTH_BACKOFF_S in sleeps
    assert "LỖI Facebook Graph API" in caplog.text
    assert "FACEBOOK_PAGE_ACCESS_TOKEN" in caplog.text
    assert client.last_error is None


def test_fb_viewer_loop_5xx_backs_off_exponentially(sleeps):
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        polls["n"] += 1
        if polls["n"] <= 2:
            return httpx.Response(502, json={"error": "bad gateway"})
        return httpx.Response(200, json={"live_views": 42})

    async def run():
        client, http = _fb_client(handler)
        try:
            async for tick in client.iter_viewers("live-1", every_s=1.0):
                return tick
        finally:
            await http.aclose()
        return None

    tick = asyncio.run(run())
    assert tick is not None
    assert tick.viewers == 42.0
    assert sleeps[0] == 1.0
    assert sleeps[1] == 2.0


# --- runner heartbeat surfaces the latest platform error --------------------


def test_heartbeat_reports_last_platform_error(caplog):
    async def run() -> None:
        counters = Counters()
        client = SimpleNamespace(last_error="LỖI Facebook Graph API (HTTP 401): ...")
        task = asyncio.create_task(_heartbeat(counters, client, every_s=0.01))
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    with caplog.at_level(logging.INFO, logger="livelift.ingest.runner"):
        asyncio.run(run())
    assert "lỗi gần nhất: LỖI Facebook Graph API" in caplog.text


def test_heartbeat_healthy_says_no_error(caplog):
    async def run() -> None:
        counters = Counters()
        client = SimpleNamespace(last_error=None)
        task = asyncio.create_task(_heartbeat(counters, client, every_s=0.01))
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    with caplog.at_level(logging.INFO, logger="livelift.ingest.runner"):
        asyncio.run(run())
    assert "lỗi gần nhất: không có" in caplog.text
