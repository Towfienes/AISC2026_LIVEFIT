"""Pure parsing tests for ingest clients + ApiSink privacy behavior.

No network: platform payloads are fixture dicts, and the sink is exercised
through an httpx.MockTransport that captures outgoing requests. Async code
runs via asyncio.run inside plain sync tests (no pytest-asyncio needed).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import httpx
import pytest

from livelift.ingest.base import ApiSink, RawComment, RawTick
from livelift.ingest.facebook import parse_comment
from livelift.ingest.youtube import parse_live_chat_message

# --- fixtures: realistic platform payloads ---------------------------------

YT_ITEM = {
    "kind": "youtube#liveChatMessage",
    "etag": "abc",
    "id": "LCC.CjgKDQoLYWJjZGVmZ2hpamsq",
    "snippet": {
        "type": "textMessageEvent",
        "liveChatId": "Cg0KC2FiY2RlZmdoaWpr",
        "authorChannelId": "UC_author_channel_id",
        "publishedAt": "2026-08-24T13:05:42.123456Z",
        "hasDisplayContent": True,
        "displayMessage": "chốt đơn size M nhé shop",
        "textMessageDetails": {"messageText": "chốt đơn size M nhé shop"},
    },
    "authorDetails": {
        "channelId": "UC_author_channel_id",
        "displayName": "Nguyễn Văn A",
        "isChatOwner": False,
    },
}

FB_ITEM = {
    "id": "1234567890_9876543210",
    "message": "còn màu đen không shop ơi",
    "created_time": "2026-08-24T13:05:42+0000",
    "from": {"id": "111222333", "name": "Trần Thị B"},
}


# --- YouTube parsing --------------------------------------------------------


def test_parse_youtube_message_fields():
    c = parse_live_chat_message(YT_ITEM)
    assert c is not None
    assert c.platform == "youtube"
    assert c.ext_id == "LCC.CjgKDQoLYWJjZGVmZ2hpamsq"
    assert c.text == "chốt đơn size M nhé shop"
    assert c.ts_utc == datetime(2026, 8, 24, 13, 5, 42, 123456, tzinfo=UTC)
    assert c.ts_utc.tzinfo is not None


def test_parse_youtube_drops_author_id():
    # authorDetails and snippet.authorChannelId are present in the raw
    # resource but MUST be dropped at normalization (description §11.2).
    c = parse_live_chat_message(YT_ITEM)
    assert c is not None
    assert c.author_ext_id is None


def test_parse_youtube_no_display_content_returns_none():
    item = {
        "id": "LCC.deleted",
        "snippet": {"publishedAt": "2026-08-24T13:05:42Z", "hasDisplayContent": False},
    }
    assert parse_live_chat_message(item) is None


# --- Facebook parsing -------------------------------------------------------


def test_parse_facebook_comment_fields():
    c = parse_comment(FB_ITEM)
    assert c is not None
    assert c.platform == "facebook"
    assert c.ext_id == "1234567890_9876543210"
    assert c.text == "còn màu đen không shop ơi"
    # "+0000" offset must parse to aware UTC
    assert c.ts_utc == datetime(2026, 8, 24, 13, 5, 42, tzinfo=UTC)


def test_parse_facebook_drops_author_id():
    c = parse_comment(FB_ITEM)
    assert c is not None
    assert c.author_ext_id is None


def test_parse_facebook_empty_message_returns_none():
    assert parse_comment({"id": "1_2", "created_time": "2026-08-24T13:05:42+0000"}) is None


# --- RawComment invariants --------------------------------------------------


def test_raw_comment_rejects_naive_timestamp():
    with pytest.raises(ValueError):
        RawComment("youtube", "x", datetime(2026, 8, 24, 13, 0, 0), "hi")


# --- ApiSink: scrub before transmit, author never transmitted ---------------


def _make_sink(handler) -> tuple[ApiSink, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sink = ApiSink(api_url="http://api.test", session_id="sess-1", client=client, base_delay_s=0.0)
    return sink, client


def test_sink_scrubs_phone_before_post():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    comment = RawComment(
        platform="youtube",
        ext_id="LCC.x",
        ts_utc=datetime(2026, 8, 24, 13, 5, 42, tzinfo=UTC),
        text="ib em nhé, sđt 0901234567 gửi hàng giúp em",
    )

    async def run() -> bool:
        sink, client = _make_sink(handler)
        try:
            return await sink.post_comment(comment)
        finally:
            await client.aclose()

    assert asyncio.run(run()) is True
    assert len(captured) == 1
    req = captured[0]
    assert str(req.url) == "http://api.test/sessions/sess-1/comments"
    body = json.loads(req.content.decode("utf-8"))
    # The phone number never leaves the ingest process in the clear.
    assert "0901234567" not in req.content.decode("utf-8")
    assert "[SĐT]" in body["text_scrubbed"]
    assert body["platform"] == "youtube"
    assert body["ext_id"] == "LCC.x"
    assert "phone" in body["pii_kinds"]
    # No author field of any spelling, ever.
    assert not any("author" in k.lower() for k in body)
    # Raw text is not in the payload under any key.
    assert comment.text not in json.dumps(body, ensure_ascii=False)


def test_sink_posts_tick_payload():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    tick = RawTick(
        platform="facebook",
        ts_utc=datetime(2026, 8, 24, 13, 6, 0, tzinfo=UTC),
        viewers=137.0,
    )

    async def run() -> bool:
        sink, client = _make_sink(handler)
        try:
            return await sink.post_tick(tick)
        finally:
            await client.aclose()

    assert asyncio.run(run()) is True
    req = captured[0]
    assert str(req.url) == "http://api.test/sessions/sess-1/ticks"
    body = json.loads(req.content.decode("utf-8"))
    assert body == {
        "platform": "facebook",
        "ts_utc": "2026-08-24T13:06:00+00:00",
        "viewers": 137.0,
    }


def test_sink_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json={"ok": True})

    tick = RawTick("youtube", datetime(2026, 8, 24, 13, 0, 0, tzinfo=UTC), 5.0)

    async def run() -> bool:
        sink, client = _make_sink(handler)
        try:
            return await sink.post_tick(tick)
        finally:
            await client.aclose()

    assert asyncio.run(run()) is True
    assert calls["n"] == 3


def test_sink_never_raises_after_exhausted_retries():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, json={"error": "down"})

    tick = RawTick("youtube", datetime(2026, 8, 24, 13, 0, 0, tzinfo=UTC), 5.0)

    async def run() -> bool:
        sink, client = _make_sink(handler)
        try:
            return await sink.post_tick(tick)
        finally:
            await client.aclose()

    assert asyncio.run(run()) is False  # returns False, never raises
    assert calls["n"] == 3
