"""Shopee Live ingest: ký, parse, khử trùng lặp, phân loại lỗi, rò rỉ token.

Không chạm mạng: mọi lời gọi đi qua ``httpx.MockTransport``. Không có
``pytest-asyncio`` trong repo nên coroutine chạy bằng ``asyncio.run`` trong
test đồng bộ, đúng như ``tests/test_ingest_errors.py``.

Ghi rõ giới hạn: nhóm CHƯA có danh tính Shopee thật, nên đây là test hành vi
của adapter trên phản hồi mô phỏng theo đúng lược đồ tài liệu — **không phải**
live-fire. Xem ``docs/nen-tang-ho-tro.md`` §4.

Nguồn của lược đồ ký (sửa 17/09/2026): JSON tài liệu gốc tải từ
open.shopee.com cho bảy endpoint ``v2.livestream.*`` (get_latest_comment_list,
get_session_detail, get_session_metric, get_session_item_metric,
update_show_item, create_session, post_comment). Cả bảy có
``"api_type": "User"``; ``common_params`` = ``partner_id, timestamp,
access_token, user_id, sign``; mô tả ``sign`` nguyên văn: "Signature generated
by(depends on different APIs) partner_id, api path, timestamp, access_token,
user_id and partner_key via HMAC-SHA256 hashing algorithm". Trường ``path`` của
tài liệu là đường dẫn đầy đủ, ví dụ ``/api/v2/livestream/get_latest_comment_list``.

Trước 17/09 các test ở đây khẳng định chữ ký bằng ``shop_id`` và ký trên phần
đuôi ``/livestream/...`` — tức là khóa chặt đúng hai lỗi sẽ làm mọi lời gọi
thật bị từ chối. Chúng đã được sửa theo tài liệu gốc.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import importlib.util
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from livelift.api.ingest_jobs import mo_ta_loi as giam_sat_mo_ta_loi
from livelift.api.ingest_jobs import phan_loai_loi
from livelift.config import Settings
from livelift.ingest.shopee import (
    AUTH_BACKOFF_S,
    COMMENT_WINDOW_S,
    MAX_SAFE_POLL_S,
    PATH_COMMENTS,
    RATE_LIMIT_BACKOFF_S,
    REGION_BASE_URLS,
    REQUIRED_ENV_LIVESTREAM,
    REQUIRED_ENV_SHOW_ITEM,
    ShopeeApiError,
    ShopeeLiveClient,
    ShopeeNotLiveError,
    ShopeeRegionError,
    ShopeeSessionError,
    build_signed_params,
    classify_error,
    credential_problem,
    next_offset,
    parse_comment,
    sign_request,
)

ROOT = Path(__file__).resolve().parent.parent

PARTNER_ID = "2001234"
PARTNER_KEY = "khoa-bi-mat-cua-partner"
USER_ID = "880011"
SHOP_ID = "77001"
TOKEN = "access-token-song-4-gio"
TS = 1789105000

FULL_PATH_COMMENTS = "/api/v2/livestream/get_latest_comment_list"
FULL_PATH_SHOW_ITEM = "/api/v2/livestream/update_show_item"

#: Vector ký TỰ TÍNH, độc lập với mã Python — sinh bằng OpenSSL (Git Bash):
#:   B='2001234''<PATH>''1789105000''access-token-song-4-gio''880011'
#:   printf '%s' "$B" | openssl dgst -sha256 -hmac 'khoa-bi-mat-cua-partner'
#: <PATH> = /api/v2/livestream/get_latest_comment_list
SIGN_VECTOR_COMMENTS = "8a5b2c2291fcd5afd58231b89c44c624d6abec9cc3e0bf213a14e0d5200381f4"
#: <PATH> = /api/v2/livestream/update_show_item
SIGN_VECTOR_SHOW_ITEM = "ae71db4096d4bd1840bd6eab44c2ec9b2ce9bbf5b0addd0f6b1753d757c03331"
#: <PATH> = /livestream/get_latest_comment_list — ký phần ĐUÔI, lỗi của adapter trước 17/09.
SIGN_VECTOR_TAIL_BUG = "39f5846f0795d876716a05cd31287b5563e861e7598c2fd580f7cc8084cb3f36"

COMMENT_ITEM = {
    "comment_id": 918273645,
    "content": "chốt đơn 2 cái size L nhé shop",
    "timestamp": 1789105000,
    "user_id": 555666777,
    "username": "Nguyễn Thị Hoa",
}

MSG_REGION = "The API is not supported for current region"
MSG_NOT_ONGOING = "The session(session_id:42) is not ongoing"


@pytest.fixture
def sleeps(monkeypatch):
    """Thời gian ngủ được ghi lại; không có gì thật sự chờ."""
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


def _client(handler, **overrides) -> ShopeeLiveClient:
    kwargs = {
        "partner_id": PARTNER_ID,
        "partner_key": PARTNER_KEY,
        "user_id": USER_ID,
        "shop_id": SHOP_ID,
        "access_token": TOKEN,
        "region": "global",
    }
    kwargs.update(overrides)
    return ShopeeLiveClient(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        **kwargs,
    )


def _envelope(response: dict) -> httpx.Response:
    return httpx.Response(
        200, json={"error": "", "message": "", "request_id": "rq-1", "response": response}
    )


def _loi(error: str, message: str, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status, json={"error": error, "message": message, "request_id": "rq-7", "response": {}}
    )


def _expected_sign(request: httpx.Request) -> str:
    """Tính lại chữ ký từ CHÍNH yêu cầu đã gửi đi: đường dẫn thật + query thật."""
    q = request.url.params
    base = f"{q['partner_id']}{request.url.path}{q['timestamp']}{q['access_token']}{q['user_id']}"
    return hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()


async def _take(agen, n: int) -> list:
    out = []
    async for item in agen:
        out.append(item)
        if len(out) >= n:
            break
    await agen.aclose()
    return out


# --- chữ ký (API loại "User") ---------------------------------------------


def test_sign_matches_documented_user_scheme():
    """partner_id + api path + timestamp + access_token + user_id, HMAC-SHA256 hex.

    Nguồn: mô tả ``sign`` trong ``common_params`` của tài liệu gốc
    ``v2.livestream.get_latest_comment_list`` (api_type "User").
    """
    expected = hmac.new(
        PARTNER_KEY.encode(),
        f"{PARTNER_ID}{FULL_PATH_COMMENTS}{TS}{TOKEN}{USER_ID}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert sign_request(PARTNER_ID, PARTNER_KEY, FULL_PATH_COMMENTS, TS, TOKEN, USER_ID) == expected


def test_sign_known_answer_vectors_computed_with_openssl():
    """Vector tự tính bằng OpenSSL — không dùng lại mã hmac của Python để so."""
    assert (
        sign_request(PARTNER_ID, PARTNER_KEY, FULL_PATH_COMMENTS, TS, TOKEN, USER_ID)
        == SIGN_VECTOR_COMMENTS
    )
    assert (
        sign_request(PARTNER_ID, PARTNER_KEY, FULL_PATH_SHOW_ITEM, TS, TOKEN, USER_ID)
        == SIGN_VECTOR_SHOW_ITEM
    )


def test_sign_covers_the_full_api_path_not_just_the_tail():
    """Ký nhầm phần đuôi là lỗi tích hợp Shopee phổ biến nhất — khóa lại."""
    tail = sign_request(PARTNER_ID, PARTNER_KEY, PATH_COMMENTS, TS, TOKEN, USER_ID)
    assert tail == SIGN_VECTOR_TAIL_BUG
    assert tail != SIGN_VECTOR_COMMENTS


def test_sign_with_shop_id_differs_from_documented_scheme():
    """Lược đồ loại "Shop" (ký bằng shop_id) cho chữ ký KHÁC — đó là lỗi cũ."""
    by_shop = sign_request(PARTNER_ID, PARTNER_KEY, FULL_PATH_COMMENTS, TS, TOKEN, SHOP_ID)
    assert by_shop != SIGN_VECTOR_COMMENTS


def test_build_signed_params_carries_exactly_the_documented_common_params():
    params = build_signed_params(
        PARTNER_ID,
        PARTNER_KEY,
        FULL_PATH_COMMENTS,
        TOKEN,
        USER_ID,
        extra={"session_id": 42, "offset": 0},
        timestamp=TS,
    )
    assert set(params) == {
        "partner_id",
        "timestamp",
        "access_token",
        "user_id",
        "sign",
        "session_id",
        "offset",
    }
    assert "shop_id" not in params
    assert params["partner_id"] == PARTNER_ID
    assert params["user_id"] == USER_ID
    assert params["access_token"] == TOKEN
    assert params["timestamp"] == str(TS)
    assert params["session_id"] == "42"
    assert params["sign"] == SIGN_VECTOR_COMMENTS


def test_build_signed_params_refuses_a_tail_path():
    with pytest.raises(ValueError, match="ĐẦY ĐỦ"):
        build_signed_params(PARTNER_ID, PARTNER_KEY, PATH_COMMENTS, TOKEN, USER_ID, timestamp=TS)


@pytest.mark.parametrize("region", sorted(REGION_BASE_URLS))
def test_client_signs_the_full_path_it_actually_requests(region):
    """Chữ ký phải khớp đường dẫn THẬT của yêu cầu, ở mọi cổng vùng."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _envelope({"status": 1})

    client = _client(handler, region=region)
    asyncio.run(client.get_session_detail("42"))
    request = seen[0]
    assert request.method == "GET"
    assert request.url.path == "/api/v2/livestream/get_session_detail"
    assert set(request.url.params) == {
        "partner_id",
        "timestamp",
        "access_token",
        "user_id",
        "sign",
        "session_id",
    }
    assert request.url.params["user_id"] == USER_ID
    assert request.url.params["sign"] == _expected_sign(request)


def test_client_request_matches_the_known_answer_vector(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: float(TS))
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _envelope({"list": []})

    asyncio.run(_client(handler).get_latest_comment_page("42"))
    assert seen[0].url.path == FULL_PATH_COMMENTS
    assert seen[0].url.params["sign"] == SIGN_VECTOR_COMMENTS
    assert "shop_id" not in seen[0].url.params


def test_vietnam_uses_the_global_gateway():
    """Shopee KHÔNG có host .vn — VN đi qua partner.shopeemobile.com."""
    assert REGION_BASE_URLS["global"] == "https://partner.shopeemobile.com/api/v2"


def test_unknown_region_is_rejected_loudly():
    with pytest.raises(ValueError, match="SHOPEE_REGION"):
        ShopeeLiveClient(
            partner_id=PARTNER_ID,
            partner_key=PARTNER_KEY,
            user_id=USER_ID,
            access_token=TOKEN,
            region="vietnam",
        )


# --- danh tính --------------------------------------------------------------


def test_settings_reads_shopee_user_id_from_env(monkeypatch):
    monkeypatch.setenv("SHOPEE_USER_ID", USER_ID)
    assert Settings(_env_file=None).shopee_user_id == USER_ID


def test_env_example_documents_shopee_user_id():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "\nSHOPEE_USER_ID=" in text


def test_required_env_lists():
    assert REQUIRED_ENV_LIVESTREAM == (
        "SHOPEE_PARTNER_ID",
        "SHOPEE_PARTNER_KEY",
        "SHOPEE_USER_ID",
        "SHOPEE_ACCESS_TOKEN",
    )
    assert "SHOPEE_SHOP_ID" not in REQUIRED_ENV_LIVESTREAM
    assert REQUIRED_ENV_SHOW_ITEM[-1] == "SHOPEE_SHOP_ID"


def test_missing_credentials_fail_with_a_vietnamese_message():
    client = _client(lambda r: _envelope({}), partner_id="", partner_key="", access_token="")

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=5.0)
        await agen.__anext__()

    with pytest.raises(RuntimeError, match="SHOPEE_PARTNER_ID"):
        asyncio.run(run())


def test_missing_user_id_is_a_config_error_for_the_supervisor():
    """Tiền tố "Thiếu danh tính Shopee" là thứ bộ giám sát dùng để dừng ngay."""

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi Shopee khi thiếu SHOPEE_USER_ID")

    client = _client(handler, user_id="")

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=5.0)
        await agen.__anext__()

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(run())
    text = str(excinfo.value)
    assert text.startswith("Thiếu danh tính Shopee")
    assert "SHOPEE_USER_ID" in text
    assert "user_id_list" in text
    assert phan_loai_loi(excinfo.value) == "cau_hinh"
    assert TOKEN not in text
    assert PARTNER_KEY not in text


def test_shop_id_is_not_needed_to_read_a_session():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "shop_id" not in request.url.params
        return _envelope({"ccu": 12})

    metric = asyncio.run(_client(handler, shop_id="").get_session_metric("42"))
    assert metric["ccu"] == 12


def test_non_numeric_user_id_is_rejected_before_any_call():
    problem = credential_problem(
        {
            "SHOPEE_PARTNER_ID": PARTNER_ID,
            "SHOPEE_PARTNER_KEY": PARTNER_KEY,
            "SHOPEE_USER_ID": "shop-cua-toi",
            "SHOPEE_ACCESS_TOKEN": TOKEN,
        },
        REQUIRED_ENV_LIVESTREAM,
    )
    assert problem is not None
    assert problem.startswith("Thiếu danh tính Shopee")
    assert "SHOPEE_USER_ID phải là dãy số" in problem
    assert "shop-cua-toi" not in problem  # không bao giờ in lại giá trị


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


def test_trang_sau_loi_tam_thoi_khong_lam_mat_trang_da_doc(sleeps):
    """Hồi quy kiểm toán 17/09/2026: trang 1 đọc được 2 bình luận, trang 2 trả
    HTTP 500 một lần. Trước khi sửa batch bị bỏ nhưng id đã vào seen-set, nên lần
    poll lại coi cả hai là "đã thấy" — mất vĩnh viễn, không một dòng báo lỗi."""
    goi = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        goi["n"] += 1
        offset = request.url.params["offset"]
        if offset == "0":
            return _envelope(
                {
                    "next_offset": 2,
                    "list": [dict(COMMENT_ITEM, comment_id=1), dict(COMMENT_ITEM, comment_id=2)],
                }
            )
        if goi["n"] == 2:
            return _loi("error_server", "internal", status=500)
        if goi["n"] > 40:
            return _envelope({"next_offset": 2, "list": [dict(COMMENT_ITEM, comment_id=3)]})
        return _envelope({"next_offset": 2, "list": []})

    client = _client(handler)
    got = asyncio.run(_take(client.iter_comments("42", poll_s=5.0), 3))
    assert [c.ext_id for c in got] == ["1", "2", "3"]


def test_phien_ket_thuc_o_trang_sau_van_tra_trang_da_doc(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("get_session_detail"):
            return _envelope({"status": 2})
        if request.url.params["offset"] == "0":
            return _envelope({"next_offset": 1, "list": [dict(COMMENT_ITEM, comment_id=5)]})
        return _loi("common.error_param", MSG_NOT_ONGOING)

    client = _client(handler)

    async def tat_ca() -> list:
        return [c async for c in client.iter_comments("42", poll_s=5.0)]

    got = asyncio.run(tat_ca())
    assert [c.ext_id for c in got] == ["5"]


def test_slow_poll_is_refused_because_the_window_is_only_10_seconds():
    """Poll chậm hơn cửa sổ = mất bình luận vĩnh viễn. Phải NỔ, không âm thầm."""
    client = _client(lambda request: _envelope({"list": []}))

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=MAX_SAFE_POLL_S + 0.1)
        await agen.__anext__()

    with pytest.raises(ValueError, match="MẤT bình luận"):
        asyncio.run(run())
    assert MAX_SAFE_POLL_S < COMMENT_WINDOW_S


# --- vùng / chưa phát / sai phiên -------------------------------------------


def test_region_not_supported_is_a_config_error_and_is_not_retried(sleeps):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return _loi("error_server", MSG_REGION)

    client = _client(handler)

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=5.0)
        await agen.__anext__()

    with pytest.raises(ShopeeRegionError) as excinfo:
        asyncio.run(run())
    exc = excinfo.value
    assert isinstance(exc, ValueError)
    assert isinstance(exc, ShopeeApiError)
    assert "CHƯA được cấp API livestream" in str(exc)
    assert phan_loai_loi(exc) == "cau_hinh"
    assert "CHƯA được cấp API livestream" in giam_sat_mo_ta_loi(exc)
    assert calls["n"] == 1
    assert sleeps == []
    assert TOKEN not in str(exc)


def test_not_ongoing_session_says_no_live_is_playing(sleeps):
    """Cụm "KHÔNG có buổi live nào đang phát" ⇒ bộ giám sát chờ lên sóng."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("get_session_detail"):
            return _envelope({"status": 0})
        return _loi("error_data", MSG_NOT_ONGOING)

    client = _client(handler)

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=5.0)
        await agen.__anext__()

    with pytest.raises(ShopeeNotLiveError) as excinfo:
        asyncio.run(run())
    exc = excinfo.value
    assert "KHÔNG có buổi live nào đang phát" in str(exc)
    assert phan_loai_loi(exc) == "chua_phat"
    assert "KHÔNG có buổi live nào đang phát" in giam_sat_mo_ta_loi(exc)
    assert TOKEN not in str(exc)
    assert sleeps == []
    # Không hứa "rồi chờ" vô điều kiện: runner CLI hiện KHÔNG chờ (xem test
    # runner bên dưới). Hướng dẫn cho cả hai đường phải còn nguyên sau khi bộ
    # giám sát cắt thông điệp ở 400 ký tự.
    hien_thi = giam_sat_mo_ta_loi(exc)
    assert "Bộ thu bình luận trên web tự dò lại" in hien_thi
    assert "chạy lại lệnh sau khi đã phát" in hien_thi
    assert "rồi chờ." not in str(exc)


def test_not_ongoing_after_the_session_ended_stops_the_source_cleanly(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("get_session_detail"):
            return _envelope({"status": 2})
        return _loi("error_data", MSG_NOT_ONGOING)

    client = _client(handler)

    async def run() -> list:
        return [c async for c in client.iter_comments("42", poll_s=5.0)]

    assert asyncio.run(run()) == []


def test_not_ongoing_with_unknown_status_still_waits_for_live(sleeps):
    """Không hỏi được trạng thái thì KHÔNG kết thúc bộ thu — coi là chưa phát."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("get_session_detail"):
            return _loi("error_server", "Something wrong. Please try later.", status=500)
        return _loi("error_data", MSG_NOT_ONGOING)

    client = _client(handler)

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=5.0)
        await agen.__anext__()

    with pytest.raises(ShopeeNotLiveError):
        asyncio.run(run())


def test_iter_viewers_propagates_not_live(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("get_session_detail"):
            return _envelope({"status": 0})
        return _loi("error_data", MSG_NOT_ONGOING)

    client = _client(handler)

    async def run() -> None:
        agen = client.iter_viewers("42", every_s=30.0)
        await agen.__anext__()

    with pytest.raises(ShopeeNotLiveError):
        asyncio.run(run())


@pytest.mark.parametrize(
    "message",
    [
        "The session(session_id:42) is not belong to you",
        "The session(session_id:42) is not exist",
        "Invalid session_id",
    ],
)
def test_wrong_session_is_a_config_error(sleeps, message):
    def handler(request: httpx.Request) -> httpx.Response:
        return _loi("error_data", message)

    client = _client(handler)

    async def run() -> None:
        agen = client.iter_comments("42", poll_s=5.0)
        await agen.__anext__()

    with pytest.raises(ShopeeSessionError) as excinfo:
        asyncio.run(run())
    assert phan_loai_loi(excinfo.value) == "cau_hinh"
    assert "SHOPEE_USER_ID" in str(excinfo.value)
    assert sleeps == []


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


# --- ghim sản phẩm: update_show_item ----------------------------------------


def test_update_show_item_posts_signed_query_and_shop_id_in_body(monkeypatch):
    """Tài liệu: POST, tham số chung ở query, thân JSON {session_id, item_id, shop_id}."""
    monkeypatch.setattr(time, "time", lambda: float(TS))
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _envelope({})

    result = asyncio.run(_client(handler).update_show_item("42", 123))
    assert result == {}
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == FULL_PATH_SHOW_ITEM
    assert set(request.url.params) == {"partner_id", "timestamp", "access_token", "user_id", "sign"}
    assert request.url.params["user_id"] == USER_ID
    assert request.url.params["sign"] == SIGN_VECTOR_SHOW_ITEM
    assert request.url.params["sign"] == _expected_sign(request)
    assert json.loads(request.content) == {"session_id": 42, "item_id": 123, "shop_id": 77001}
    assert request.headers["content-type"].startswith("application/json")


def test_update_show_item_requires_shop_id_before_any_call():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi Shopee khi thiếu SHOPEE_SHOP_ID")

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(_client(handler, shop_id="").update_show_item("42", "123"))
    assert str(excinfo.value).startswith("Thiếu danh tính Shopee")
    assert "SHOPEE_SHOP_ID" in str(excinfo.value)


def test_update_show_item_rejects_non_numeric_ids_before_any_call():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi Shopee với item_id sai")

    with pytest.raises(ValueError, match="item_id"):
        asyncio.run(_client(handler).update_show_item("42", "ao-thun-L"))


def test_update_show_item_is_not_retried(sleeps):
    """Ghim đến muộn = sản phẩm lên màn hình ở SAI khối. Lỗi phải nổi lên ngay."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return _loi("error_server", "Too many requests, please try again later")

    with pytest.raises(ShopeeApiError):
        asyncio.run(_client(handler).update_show_item("42", "123"))
    assert calls["n"] == 1
    assert sleeps == []


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


def test_classify_error_kinds():
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
    # Nguyên văn từ error_list của tài liệu v2.livestream.*:
    assert classify_error(ShopeeApiError("error_server", MSG_REGION)) == "region"
    assert classify_error(ShopeeApiError("error_data", MSG_NOT_ONGOING)) == "not_live"
    assert classify_error(ShopeeApiError("error_param", "Invalid session_id")) == "session"
    assert (
        classify_error(ShopeeApiError("error_server", "Too many requests, please try again later"))
        == "rate_limit"
    )


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
    assert "SHOPEE_USER_ID" in caplog.text
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


def test_runner_cli_started_before_go_live_does_not_crash(monkeypatch, caplog):
    """Người vận hành chạy lệnh ở docs §4.4 vài phút trước khi bấm phát.

    Phản biện 17/09 đo được: Shopee trả "is not ongoing", ``get_session_detail``
    trả ``status=0`` ⇒ client ném :class:`ShopeeNotLiveError` (đúng hợp đồng,
    bộ giám sát web cần lỗi này để chuyển sang chờ lên sóng) ⇒ ``runner.main``
    không bắt ⇒ traceback, không trả mã thoát.

    Test chấp nhận CẢ HAI cách sửa runner: (a) ghi câu tiếng Việt rồi trả mã 1,
    hoặc (b) chờ rồi dò lại — phiên được cho "kết thúc" (status=2) sau vài lần
    hỏi nên runner chờ vẫn dừng và trả 0. Cả hai đều phải để người vận hành
    thấy câu "KHÔNG có buổi live nào đang phát", và không lộ token.
    """
    from livelift.ingest import runner

    hoi_trang_thai = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("get_session_detail"):
            hoi_trang_thai["n"] += 1
            return _envelope({"status": 0 if hoi_trang_thai["n"] <= 3 else 2})
        return _loi("error_data", MSG_NOT_ONGOING)

    class _Sink:
        spooled = 0
        dropped = 0

        def __init__(self, **_kwargs) -> None:
            pass

        async def post_comment(self, _comment) -> bool:
            return True

        async def post_tick(self, _tick) -> bool:
            return True

        async def aclose(self) -> None:
            return None

    real_sleep = asyncio.sleep

    async def sleep_nhuong_luot(_delay: float, *args, **kwargs) -> None:
        # Nhường vòng sự kiện (sleep 0 thật) để asyncio.wait kịp thấy tác vụ xong.
        await real_sleep(0)

    async def khong_heartbeat(*_args, **_kwargs) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(asyncio, "sleep", sleep_nhuong_luot)
    monkeypatch.setattr(runner, "_heartbeat", khong_heartbeat, raising=False)
    monkeypatch.setattr(runner, "ApiSink", _Sink)
    monkeypatch.setattr(runner, "_build_client", lambda _platform: _client(handler))

    with caplog.at_level(logging.INFO):
        rc = runner.main(["--platform", "shopee", "--source-id", "42", "--session-id", "s-1"])

    assert rc in (0, 1)
    assert "KHÔNG có buổi live nào đang phát" in caplog.text
    assert TOKEN not in caplog.text


# --- scripts/kiem_tra_shopee.py ---------------------------------------------

# scripts/ không phải package -> nạp theo đường dẫn, đăng ký TRƯỚC exec_module
# vì @dataclass tra cứu module trong sys.modules.
_SCRIPT = ROOT / "scripts" / "kiem_tra_shopee.py"
_spec = importlib.util.spec_from_file_location("kiem_tra_shopee", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
kts = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = kts
_spec.loader.exec_module(kts)


def _settings(**overrides) -> SimpleNamespace:
    values = {
        "shopee_partner_id": PARTNER_ID,
        "shopee_partner_key": PARTNER_KEY,
        "shopee_user_id": USER_ID,
        "shopee_access_token": TOKEN,
        "shopee_shop_id": SHOP_ID,
        "shopee_refresh_token": "refresh-30-ngay",
        "shopee_region": "global",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _chay_script(handler, **overrides):
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return asyncio.run(kts.kiem_tra("42", settings=_settings(**overrides), http=http))


def test_script_thieu_user_id_thi_chan_va_khong_goi_mang():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi Shopee khi thiếu SHOPEE_USER_ID")

    kq = _chay_script(handler, shopee_user_id="")
    assert kq.san_sang is False
    assert any("SHOPEE_USER_ID" in dong for dong in kq.chan)


def test_script_duong_di_day_du_san_sang_ma_khong_can_shop_id(capsys):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("get_session_detail"):
            return _envelope({"status": 1, "title": "Live thử", "session_id": 42})
        if request.url.path.endswith("get_session_metric"):
            return _envelope({"ccu": 30, "orders": 2, "gmv": 350000})
        return _envelope({"next_offset": 0, "list": [COMMENT_ITEM]})

    kq = _chay_script(handler, shopee_shop_id="")
    out = capsys.readouterr().out
    assert kq.san_sang is True
    assert any("SHOPEE_SHOP_ID" in c for c in kq.canh_bao)
    assert len(requests) == 3
    for request in requests:
        assert request.url.params["user_id"] == USER_ID
        assert "shop_id" not in request.url.params
        assert request.url.params["sign"] == _expected_sign(request)
    # PII + bí mật: không in nội dung bình luận, tên người xem, token, khóa.
    assert COMMENT_ITEM["content"] not in out
    assert "Nguyễn Thị Hoa" not in out
    assert TOKEN not in out
    assert PARTNER_KEY not in out


def test_script_vung_chua_duoc_cap_api_thi_chan_ro_rang():
    def handler(request: httpx.Request) -> httpx.Response:
        return _loi("error_server", MSG_REGION)

    kq = _chay_script(handler)
    assert kq.san_sang is False
    assert any("CHƯA được cấp API livestream" in dong for dong in kq.chan)


def test_script_phien_chua_phat_chi_canh_bao_khong_chan():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("get_session_detail"):
            return _envelope({"status": 0, "title": "Sắp live"})
        return _loi("error_data", MSG_NOT_ONGOING)

    kq = _chay_script(handler)
    assert kq.san_sang is True  # danh tính + phiên đã qua ở mục 2
    assert any("KHÔNG có buổi live nào đang phát" in c for c in kq.canh_bao)
    # Runner CLI hiện KHÔNG tự chờ lên sóng (xem test runner ở trên): script
    # phải bảo người vận hành bật lệnh SAU khi phát, không để họ bật trước giờ G.
    assert any("SAU khi đã bấm phát" in c for c in kq.canh_bao)
