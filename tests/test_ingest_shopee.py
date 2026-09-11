"""Shopee Live ingest: ký, parse, khử trùng lặp, phân loại lỗi, rò rỉ token.

Không chạm mạng: mọi lời gọi đi qua ``httpx.MockTransport``. Không có
``pytest-asyncio`` trong repo nên coroutine chạy bằng ``asyncio.run`` trong
test đồng bộ, đúng như ``tests/test_ingest_errors.py``.

Ghi rõ giới hạn: nhóm CHƯA có danh tính Shopee thật, nên đây là test hành vi
của adapter trên phản hồi mô phỏng theo đúng lược đồ tài liệu — **không phải**
live-fire. Xem ``docs/nen-tang-ho-tro.md`` §4.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from datetime import UTC, datetime

import httpx
import pytest

from livelift.ingest.shopee import (
    AUTH_BACKOFF_S,
    COMMENT_WINDOW_S,
    MAX_SAFE_POLL_S,
    PATH_COMMENTS,
    RATE_LIMIT_BACKOFF_S,
    REGION_BASE_URLS,
    ShopeeApiError,
    ShopeeLiveClient,
    build_signed_params,
    classify_error,
    next_offset,
    parse_comment,
    sign_request,
)

PARTNER_ID = "2001234"
PARTNER_KEY = "khoa-bi-mat-cua-partner"
SHOP_ID = "77001"
TOKEN = "access-token-song-4-gio"

COMMENT_ITEM = {
    "comment_id": 918273645,
    "content": "chốt đơn 2 cái size L nhé shop",
    "timestamp": 1789105000,
    "user_id": 555666777,
    "username": "Nguyễn Thị Hoa",
}


@pytest.fixture
def sleeps(monkeypatch):
    """Thời gian ngủ được ghi lại; không có gì thật sự chờ."""
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


def _client(handler) -> ShopeeLiveClient:
    return ShopeeLiveClient(
        partner_id=PARTNER_ID,
        partner_key=PARTNER_KEY,
        shop_id=SHOP_ID,
        access_token=TOKEN,
        region="global",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _envelope(response: dict) -> httpx.Response:
    return httpx.Response(
        200, json={"error": "", "message": "", "request_id": "rq-1", "response": response}
    )


async def _take(agen, n: int) -> list:
    out = []
    async for item in agen:
        out.append(item)
        if len(out) >= n:
            break
    await agen.aclose()
    return out


# --- chữ ký ----------------------------------------------------------------


def test_sign_matches_shopee_scheme():
    """partner_id + path + timestamp + access_token + shop_id, HMAC-SHA256 hex."""
    ts = 1789105000
    expected = hmac.new(
        PARTNER_KEY.encode(),
        f"{PARTNER_ID}{PATH_COMMENTS}{ts}{TOKEN}{SHOP_ID}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert sign_request(PARTNER_ID, PARTNER_KEY, PATH_COMMENTS, ts, TOKEN, SHOP_ID) == expected


def test_sign_covers_the_full_api_path_not_just_the_tail():
    """Ký nhầm phần đuôi là lỗi tích hợp Shopee phổ biến nhất — khóa lại."""
    ts = 1789105000
    full = sign_request(PARTNER_ID, PARTNER_KEY, "/api/v2/livestream/x", ts, TOKEN, SHOP_ID)
    tail = sign_request(PARTNER_ID, PARTNER_KEY, "/livestream/x", ts, TOKEN, SHOP_ID)
    assert full != tail


def test_build_signed_params_carries_every_required_field():
    params = build_signed_params(
        PARTNER_ID,
        PARTNER_KEY,
        PATH_COMMENTS,
        TOKEN,
        SHOP_ID,
        extra={"session_id": 42, "offset": 0},
        timestamp=1789105000,
    )
    assert params["partner_id"] == PARTNER_ID
    assert params["shop_id"] == SHOP_ID
    assert params["access_token"] == TOKEN
    assert params["timestamp"] == "1789105000"
    assert params["session_id"] == "42"
    assert len(params["sign"]) == 64


def test_vietnam_uses_the_global_gateway():
    """Shopee KHÔNG có host .vn — VN đi qua partner.shopeemobile.com."""
    assert REGION_BASE_URLS["global"] == "https://partner.shopeemobile.com/api/v2"


def test_unknown_region_is_rejected_loudly():
    with pytest.raises(ValueError, match="SHOPEE_REGION"):
        ShopeeLiveClient(
            partner_id=PARTNER_ID,
            partner_key=PARTNER_KEY,
            shop_id=SHOP_ID,
            access_token=TOKEN,
            region="vietnam",
        )


# --- parse + quyền riêng tư -------------------------------------------------


def test_parse_comment_fields():
    c = parse_comment(COMMENT_ITEM)
    assert c is not None
    assert c.platform == "shopee"
    assert c.ext_id == "918273645"
    assert c.text == "chốt đơn 2 cái size L nhé shop"
    assert c.ts_utc == datetime.fromtimestamp(1789105000, tz=UTC)
    assert c.ts_utc.tzinfo is not None


def test_parse_comment_drops_user_id_and_username():
    """Phản hồi Shopee CÓ user_id + username; cả hai không được ra khỏi parser."""
    c = parse_comment(COMMENT_ITEM)
    assert c is not None
    assert c.author_ext_id is None
    assert "555666777" not in repr(c)
    assert "Hoa" not in repr(c)


@pytest.mark.parametrize(
    "item",
    [
        {"content": "x", "timestamp": 1789105000},  # thiếu comment_id
        {"comment_id": 1, "timestamp": 1789105000},  # thiếu content
        {"comment_id": 1, "content": "x"},  # thiếu timestamp
        {"comment_id": 1, "content": "x", "timestamp": "khong-phai-so"},
    ],
)
def test_parse_comment_returns_none_on_broken_payload(item):
    assert parse_comment(item) is None


def test_next_offset_normalizes():
    assert next_offset({"next_offset": "7"}) == 7
    assert next_offset({}) is None
    assert next_offset({"next_offset": "x"}) is None


# --- vòng poll bình luận ----------------------------------------------------


def test_iter_comments_deduplicates_the_overlapping_window(sleeps):
    """Cửa sổ 10s + poll 5s cố ý chồng lấn: mỗi bình luận về ~2 lần."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return _envelope(
            {"next_offset": 0, "list": [COMMENT_ITEM, dict(COMMENT_ITEM, comment_id=2)]}
        )

    client = _client(handler)
    got = asyncio.run(_take(client.iter_comments("42", poll_s=5.0), 2))
    # Hai bình luận khác nhau, không bao giờ lặp dù server trả lại y hệt.
    assert [c.ext_id for c in got] == ["918273645", "2"]
    assert len(calls) >= 1


def test_iter_comments_sorts_each_batch_by_time(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        return _envelope(
            {
                "next_offset": 0,
                "list": [
                    dict(COMMENT_ITEM, comment_id=9, timestamp=1789105090),
                    dict(COMMENT_ITEM, comment_id=8, timestamp=1789105010),
                ],
            }
        )

    client = _client(handler)
    got = asyncio.run(_take(client.iter_comments("42", poll_s=5.0), 2))
    assert [c.ext_id for c in got] == ["8", "9"]


def test_iter_comments_follows_next_offset_within_one_poll(sleeps):
    seen_offsets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = request.url.params["offset"]
        seen_offsets.append(offset)
        if offset == "0":
            return _envelope({"next_offset": 1, "list": [dict(COMMENT_ITEM, comment_id=1)]})
        return _envelope({"next_offset": 1, "list": [dict(COMMENT_ITEM, comment_id=2)]})

    client = _client(handler)
    got = asyncio.run(_take(client.iter_comments("42", poll_s=5.0), 2))
    assert [c.ext_id for c in got] == ["1", "2"]
    assert seen_offsets[:2] == ["0", "1"]


def test_slow_poll_is_refused_because_the_window_is_only_10_seconds():
    """Poll chậm hơn cửa sổ = mất bình luận vĩnh viễn. Phải NỔ, không âm thầm."""
    client = _client(lambda request: _envelope({"list": []}))

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=MAX_SAFE_POLL_S + 0.1)
        await agen.__anext__()

    with pytest.raises(ValueError, match="MẤT bình luận"):
        asyncio.run(run())
    assert MAX_SAFE_POLL_S < COMMENT_WINDOW_S


def test_missing_credentials_fail_with_a_vietnamese_message():
    client = ShopeeLiveClient(
        partner_id="",
        partner_key="",
        shop_id="",
        access_token="",
        region="global",
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: _envelope({}))),
    )

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=5.0)
        await agen.__anext__()

    with pytest.raises(RuntimeError, match="SHOPEE_PARTNER_ID"):
        asyncio.run(run())


# --- người xem --------------------------------------------------------------


def test_iter_viewers_yields_ccu(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        if "get_session_detail" in request.url.path:
            return _envelope({"status": 1, "title": "Live bán hàng"})
        return _envelope({"ccu": 1523, "peak_ccu": 2100, "gmv": 9_000_000, "orders": 37})

    client = _client(handler)
    ticks = asyncio.run(_take(client.iter_viewers("42", every_s=30.0), 1))
    assert ticks[0].platform == "shopee"
    assert ticks[0].viewers == 1523.0
    assert ticks[0].ts_utc.tzinfo is not None


def test_iter_viewers_stops_when_the_session_has_ended(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        if "get_session_detail" in request.url.path:
            return _envelope({"status": 2})
        raise AssertionError("không được hỏi metric sau khi phiên đã kết thúc")

    client = _client(handler)

    async def run() -> list:
        return [tick async for tick in client.iter_viewers("42", every_s=30.0)]

    assert asyncio.run(run()) == []


def test_session_metric_exposes_conversion_signals():
    """gmv/orders/atc là thứ YouTube và TikTok KHÔNG có — khóa hợp đồng lại."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _envelope(
            {"gmv": 12_500_000, "orders": 41, "atc": 190, "ctr": 0.07, "ccu": 830, "peak_ccu": 1400}
        )

    client = _client(handler)
    metric = asyncio.run(client.get_session_metric("42"))
    assert metric["gmv"] == 12_500_000
    assert metric["orders"] == 41
    assert metric["atc"] == 190


# --- lỗi: phân loại và KHÔNG rò token ---------------------------------------


def test_api_error_never_contains_the_access_token(sleeps):
    """Chữ ký Shopee ép access_token vào query string; lỗi phải giấu URL."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert TOKEN in str(request.url), "tiền đề: token nằm trong query"
        return httpx.Response(
            403,
            json={"error": "error_auth", "message": "Invalid access_token", "request_id": "rq-9"},
        )

    client = _client(handler)

    async def run() -> None:
        await client.get_session_metric("42")

    with pytest.raises(ShopeeApiError) as excinfo:
        asyncio.run(run())
    text = str(excinfo.value)
    assert TOKEN not in text
    assert PARTNER_KEY not in text
    assert "partner.shopeemobile.com" not in text
    assert "error_auth" in text
    assert "rq-9" in text


def test_transport_error_message_also_hides_the_url():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connect failed", request=request)

    client = _client(handler)

    async def run() -> None:
        await client.get_session_metric("42")

    with pytest.raises(ShopeeApiError) as excinfo:
        asyncio.run(run())
    assert TOKEN not in str(excinfo.value)
    assert excinfo.value.code == "network"


def test_classify_auth_vs_rate_limit_vs_transient():
    assert classify_error(ShopeeApiError("error_auth", status=403)) == "auth"
    assert classify_error(ShopeeApiError("error_sign", status=403)) == "auth"
    assert classify_error(ShopeeApiError("error_rate_limit", status=429)) == "rate_limit"
    # Rate limit trả 403 vẫn phải ra "rate_limit": bảo người ta xoay một token
    # đang tốt giữa phiên là kịch bản tệ nhất.
    assert (
        classify_error(ShopeeApiError("error_permission_rate_limited", status=403)) == "rate_limit"
    )
    assert classify_error(ShopeeApiError("error_server", status=500)) == "transient"
    assert classify_error(ShopeeApiError("network")) == "transient"


def _first_comment_after_one_failure(handler_first: httpx.Response, sleeps) -> ShopeeLiveClient:
    """Poll đầu hỏng, poll sau tốt — trả client để soi last_error/log."""
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        polls["n"] += 1
        if polls["n"] == 1:
            return handler_first
        return _envelope({"next_offset": 0, "list": [COMMENT_ITEM]})

    client = _client(handler)

    async def run():
        async for comment in client.iter_comments("42", poll_s=5.0):
            return comment
        return None

    comment = asyncio.run(run())
    assert comment is not None
    assert comment.ext_id == "918273645"
    return client


def test_auth_failure_pauses_long_and_says_what_to_do(sleeps, caplog):
    bad = httpx.Response(403, json={"error": "error_auth", "message": "bad token"})
    with caplog.at_level(logging.ERROR, logger="livelift.ingest.shopee"):
        client = _first_comment_after_one_failure(bad, sleeps)
    assert AUTH_BACKOFF_S in sleeps
    assert "XÁC THỰC Shopee THẤT BẠI" in caplog.text
    assert "kiem_tra_shopee" in caplog.text
    # Poll sau thành công đã xóa lỗi — heartbeat không được báo động giả.
    assert client.last_error is None


def test_rate_limit_says_the_token_is_fine(sleeps, caplog):
    """Bảo người vận hành xoay một token đang tốt giữa phiên là kịch bản tệ nhất."""
    throttled = httpx.Response(429, json={"error": "error_rate_limit", "message": "too many"})
    with caplog.at_level(logging.ERROR, logger="livelift.ingest.shopee"):
        _first_comment_after_one_failure(throttled, sleeps)
    assert RATE_LIMIT_BACKOFF_S in sleeps
    assert "KHÔNG cần đổi token" in caplog.text
    assert AUTH_BACKOFF_S not in sleeps


def test_runner_accepts_shopee_platform():
    from livelift.ingest.runner import build_parser

    args = build_parser().parse_args(
        ["--platform", "shopee", "--source-id", "42", "--session-id", "s-1"]
    )
    assert args.platform == "shopee"
