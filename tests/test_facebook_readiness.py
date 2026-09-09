"""Facebook Live: đường dẫn dữ liệu phải đúng NGAY LẦN ĐẦU có token thật.

Không có credential nào để thử hôm nay, nên mọi hành vi mới được khóa bằng
mock mô phỏng đúng dạng phản hồi Graph API (kể cả phân trang, token hết hạn
kiểu HTTP 400 + OAuthException, và giới hạn nhịp gọi code 4 — thứ Facebook
cũng trả về dưới dạng OAuthException).

No network: httpx.MockTransport everywhere, asyncio.sleep monkeypatched.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from livelift.ingest.facebook import (
    ENDED_STATUSES,
    LIVE_VIDEO_MAX_TRIES,
    FacebookLiveClient,
    classify_error,
    comment_params,
    next_page_cursor,
    usage_percent,
)

# scripts/ không phải package -> nạp module kiểm tra token theo đường dẫn.
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "kiem_tra_facebook.py"
_spec = importlib.util.spec_from_file_location("kiem_tra_facebook", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
kt = importlib.util.module_from_spec(_spec)
# @dataclass tra cứu module trong sys.modules khi phân giải type hint -> phải
# đăng ký TRƯỚC exec_module, nếu không nạp module theo đường dẫn sẽ nổ.
sys.modules[_spec.name] = kt
_spec.loader.exec_module(kt)


@pytest.fixture
def sleeps(monkeypatch):
    """Recorded asyncio.sleep delays; nothing actually waits."""
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


def _fb_client(handler) -> tuple[FacebookLiveClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return FacebookLiveClient(page_access_token="t0k", graph_version="v25.0", client=http), http


def _comment(cid: str, second: int, text: str = "chốt đơn") -> dict[str, Any]:
    return {
        "id": cid,
        "message": text,
        "created_time": f"2026-08-24T13:05:{second:02d}+0000",
    }


def _thu_binh_luan(handler, n: int, poll_s: float = 1.0) -> list:
    """Chạy iter_comments tới khi lấy đủ n bình luận rồi dừng."""

    async def run() -> list:
        client, http = _fb_client(handler)
        got: list = []
        try:
            async for comment in client.iter_comments("live-1", poll_s=poll_s):
                got.append(comment)
                if len(got) >= n:
                    break
        finally:
            await http.aclose()
        return got

    return asyncio.run(run())


# --- tham số bắt buộc: mất bình luận là mất biến kết quả --------------------


def test_comment_params_never_filter_and_include_replies():
    params = comment_params()
    # live_filter mặc định của Facebook là filter_low_quality -> mất intent.
    assert params["live_filter"] == "no_filter"
    # filter mặc định là toplevel -> mất mọi bình luận trả lời.
    assert params["filter"] == "stream"
    assert params["order"] == "reverse_chronological"
    assert "since" not in params
    assert "after" not in params


def test_comment_params_carries_cursors():
    params = comment_params(since=1756040742, after="CUR1")
    assert params["since"] == "1756040742"
    assert params["after"] == "CUR1"


# --- phân trang: 'paging.cursors.after' có ở CẢ trang cuối ------------------


def test_next_page_cursor_requires_paging_next():
    # Trang cuối vẫn kèm cursors.after -> nếu tin vào nó thì mỗi lần poll đều
    # đi hết trần số trang một cách vô ích.
    assert next_page_cursor({"paging": {"cursors": {"after": "A1"}}}) is None
    assert next_page_cursor({"paging": {"next": "https://...", "cursors": {"after": "A1"}}}) == "A1"
    assert next_page_cursor({}) is None


def test_comment_poll_follows_next_page_and_dedupes(sleeps):
    """Một đợt bình luận dài hơn một trang phải được lấy hết trong CÙNG lần
    poll: nếu bỏ trang sau, con trỏ ``since`` nhảy qua và mất vĩnh viễn."""
    requests: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url)
        after = request.url.params.get("after")
        n = len(requests)
        if n == 1:  # lần poll đầu — CÓ next nhưng phải bỏ qua (backfill bị chặn)
            return httpx.Response(
                200,
                json={
                    "data": [_comment("c1", 1)],
                    "paging": {"next": "https://graph/next", "cursors": {"after": "A1"}},
                },
            )
        if after is None:  # lần poll thứ hai, trang 1
            return httpx.Response(
                200,
                json={
                    "data": [_comment("c2", 2), _comment("c3", 3)],
                    "paging": {"next": "https://graph/next", "cursors": {"after": "A2"}},
                },
            )
        # trang 2 của lần poll thứ hai: có 1 bản trùng + 1 bản mới, hết trang
        return httpx.Response(
            200,
            json={
                "data": [_comment("c3", 3), _comment("c4", 4)],
                "paging": {"cursors": {"after": "A3"}},
            },
        )

    got = _thu_binh_luan(handler, 4)

    assert [c.ext_id for c in got] == ["c1", "c2", "c3", "c4"]  # không trùng, đúng thứ tự thời gian
    # Lần poll đầu chỉ 1 trang: request thứ 2 mở lần poll mới (có since, không after).
    assert requests[1].params.get("after") is None
    assert requests[1].params.get("since") is not None
    # Lần poll thứ hai đi tiếp trang bằng cursor Facebook trả về.
    assert requests[2].params.get("after") == "A2"


def test_comment_poll_stops_paging_when_page_is_all_seen(sleeps):
    """Trang tiếp theo toàn bản đã thấy = đã bắt kịp lần poll trước -> dừng."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200,
            json={
                "data": [_comment("c1", 1)],
                "paging": {"next": "https://graph/next", "cursors": {"after": "A1"}},
            },
        )

    got = _thu_binh_luan(handler, 1)
    assert [c.ext_id for c in got] == ["c1"]
    # 1 lần đầu + tối đa vài lần poll sau, KHÔNG phải 10 trang mỗi lần.
    assert calls["n"] <= 2


# --- vòng đếm người xem: status quyết định, không phải live_views ----------


def test_viewer_loop_stops_when_broadcast_stopped_even_if_live_views_present(sleeps):
    """Facebook còn trả live_views một lúc sau khi tắt sóng; kiểm tra
    live_views trước status làm vòng lặp bơm tick mãi cho buổi đã kết thúc."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"live_views": 12, "status": "LIVE_STOPPED"})

    async def run() -> list:
        client, http = _fb_client(handler)
        try:
            return [t async for t in client.iter_viewers("live-1", every_s=1.0)]
        finally:
            await http.aclose()

    assert asyncio.run(run()) == []
    assert calls["n"] == 1  # dừng ngay, không poll tiếp


def test_viewer_loop_yields_while_live_then_stops_on_vod(sleeps):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json={"live_views": 137, "status": "LIVE"})
        return httpx.Response(200, json={"live_views": 137, "status": "VOD"})

    async def run() -> list:
        client, http = _fb_client(handler)
        try:
            return [t async for t in client.iter_viewers("live-1", every_s=1.0)]
        finally:
            await http.aclose()

    ticks = asyncio.run(run())
    assert [t.viewers for t in ticks] == [137.0]
    assert "LIVE_STOPPED" in ENDED_STATUSES
    assert "LIVE" not in ENDED_STATUSES


# --- tìm live video id đang phát -------------------------------------------


def test_get_active_live_video_id_uses_broadcast_status_filter(sleeps):
    seen: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "10001", "status": "LIVE", "permalink_url": "/video/1"},
                ]
            },
        )

    async def run() -> str:
        client, http = _fb_client(handler)
        try:
            return await client.get_active_live_video_id("PAGE1")
        finally:
            await http.aclose()

    assert asyncio.run(run()) == "10001"
    assert seen[0].path.endswith("/PAGE1/live_videos")
    assert seen[0].params.get("broadcast_status") == '["LIVE"]'


def test_get_active_live_video_id_says_no_live_in_vietnamese(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    async def run() -> str:
        client, http = _fb_client(handler)
        try:
            return await client.get_active_live_video_id("PAGE1")
        finally:
            await http.aclose()

    with pytest.raises(RuntimeError, match="KHÔNG có buổi live nào đang phát"):
        asyncio.run(run())


def test_get_active_live_video_id_fails_fast_on_expired_token(sleeps):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Error validating access token",
                    "type": "OAuthException",
                    "code": 190,
                    "error_subcode": 463,
                }
            },
        )

    async def run() -> str:
        client, http = _fb_client(handler)
        try:
            return await client.get_active_live_video_id("PAGE1")
        finally:
            await http.aclose()

    with pytest.raises(RuntimeError, match="LỖI Facebook Graph API"):
        asyncio.run(run())
    assert calls["n"] == 1  # token hỏng thì thử lại vô nghĩa
    assert LIVE_VIDEO_MAX_TRIES > 1  # nhưng lỗi mạng thì vẫn có thử lại


# --- phân loại lỗi: rate limit KHÔNG phải lỗi token -------------------------


def _http_error(status: int, body: dict[str, Any]) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://graph.facebook.com/v25.0/x")
    response = httpx.Response(status, json=body, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


def test_classify_rate_limit_code_is_not_auth():
    # Facebook trả code 4 dưới dạng OAuthException/HTTP 400 — hệt token hỏng.
    exc = _http_error(
        400,
        {
            "error": {
                "message": "(#4) Application request limit reached",
                "type": "OAuthException",
                "is_transient": True,
                "code": 4,
            }
        },
    )
    assert classify_error(exc) == "rate_limit"


def test_classify_page_rate_limit_403_is_not_auth():
    exc = _http_error(403, {"error": {"message": "(#32) Page limit", "code": 32}})
    assert classify_error(exc) == "rate_limit"


def test_classify_expired_token_and_permission_are_auth():
    het_han = _http_error(400, {"error": {"type": "OAuthException", "code": 190}})
    thieu_quyen = _http_error(403, {"error": {"message": "(#200) Permissions", "code": 200}})
    assert classify_error(het_han) == "auth"
    assert classify_error(thieu_quyen) == "auth"


def test_classify_transient_flag_and_5xx():
    body = {"error": {"message": "unexpected", "code": 2, "is_transient": True}}
    assert classify_error(_http_error(500, body)) == "transient"
    assert classify_error(_http_error(502, {})) == "transient"


# --- cảnh báo hạn mức trước khi bị chặn ------------------------------------


def test_usage_percent_reads_all_documented_headers():
    flat = {"x-app-usage": json.dumps({"call_count": 12, "total_cputime": 88, "total_time": 4})}
    assert usage_percent(flat) == 88.0
    nested = {
        "x-business-use-case-usage": json.dumps(
            {"123": [{"type": "pages", "call_count": 61, "estimated_time_to_regain_access": 90}]}
        )
    }
    # 90 là SỐ PHÚT chờ, không phải phần trăm — không được lấy làm mức dùng.
    assert usage_percent(nested) == 61.0
    assert usage_percent({}) is None
    assert usage_percent({"x-app-usage": "không-phải-json"}) is None


def test_high_usage_logs_vietnamese_warning_once(sleeps, caplog):
    calls = {"n": 0}
    header = {"X-App-Usage": json.dumps({"call_count": 91, "total_cputime": 5, "total_time": 3})}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        status = "LIVE" if calls["n"] == 1 else "VOD"
        return httpx.Response(200, json={"live_views": 5, "status": status}, headers=header)

    async def run():
        client, http = _fb_client(handler)
        try:
            ticks = [t async for t in client.iter_viewers("live-1", every_s=1.0)]
        finally:
            await http.aclose()
        return ticks, client

    with caplog.at_level(logging.WARNING, logger="livelift.ingest.facebook"):
        _, client = asyncio.run(run())
    assert client.last_usage_pct == 91.0
    assert caplog.text.count("CẢNH BÁO hạn mức Facebook") == 1  # không spam mỗi lần poll


# --- vệ sinh bí mật: token không được nằm trong URL -------------------------


def test_token_travels_in_header_not_in_query_string(sleeps):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"live_views": 1, "status": "VOD"})

    async def run() -> None:
        client, http = _fb_client(handler)
        try:
            async for _ in client.iter_viewers("live-1", every_s=1.0):
                break
        finally:
            await http.aclose()

    asyncio.run(run())
    # httpx nhét nguyên URL vào mọi thông báo lỗi -> token trong query sẽ rò ra log.
    assert "t0k" not in str(seen[0].url)
    assert seen[0].headers["Authorization"] == "Bearer t0k"


# --- script kiểm tra token: phần thuần logic -------------------------------


def test_doc_debug_token_gop_granular_scopes():
    info = kt.doc_debug_token(
        {
            "data": {
                "is_valid": True,
                "type": "PAGE",
                "app_id": "111",
                "profile_id": "222",
                "expires_at": 0,
                "scopes": ["pages_show_list"],
                "granular_scopes": [{"scope": "pages_read_user_content", "target_ids": ["222"]}],
            }
        }
    )
    assert info.hop_le
    assert info.loai == "PAGE"
    assert info.het_han_luc is None  # expires_at = 0 -> token dài hạn
    assert set(info.scopes) == {"pages_show_list", "pages_read_user_content"}


def test_mo_ta_han_bang_tieng_viet():
    bay_gio = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
    assert "KHÔNG hết hạn" in kt.mo_ta_han(None, bay_gio)
    assert "ĐÃ HẾT HẠN" in kt.mo_ta_han(bay_gio - timedelta(days=3), bay_gio)
    assert "còn 58 ngày" in kt.mo_ta_han(bay_gio + timedelta(days=58), bay_gio)
    assert "gia hạn" in kt.mo_ta_han(bay_gio + timedelta(days=3), bay_gio)


def test_thieu_quyen_liet_ke_dung_thu_tu():
    assert kt.thieu_quyen(["pages_read_engagement"]) == ["pages_read_user_content"]
    assert kt.thieu_quyen(["pages_read_engagement", "pages_read_user_content"]) == []


# --- script kiểm tra token: chạy end-to-end trên mock ----------------------


def _script_handler(
    *,
    debug: dict[str, Any] | None = None,
    debug_status: int = 200,
    me: dict[str, Any] | None = None,
    live: list[dict[str, Any]] | None = None,
    comments: dict[str, Any] | None = None,
    comments_status: int = 200,
):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/debug_token"):
            return httpx.Response(debug_status, json=debug or {})
        if path.endswith("/me"):
            return httpx.Response(200, json=me or {"id": "222", "name": "Chợ Live Lab"})
        if path.endswith("/live_videos"):
            return httpx.Response(200, json={"data": live if live is not None else []})
        if path.endswith("/comments"):
            return httpx.Response(comments_status, json=comments or {"data": []})
        return httpx.Response(404, json={"error": {"message": "không khớp route"}})

    return handler


def _chay_script(handler, **kwargs) -> Any:
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return kt.kiem_tra(
            client,
            token=kwargs.pop("token", "PAGE-TOKEN"),
            graph_version="v25.0",
            page_id=kwargs.pop("page_id", "222"),
            bay_gio=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
            **kwargs,
        )


_DEBUG_OK = {
    "data": {
        "is_valid": True,
        "type": "PAGE",
        "app_id": "111",
        "profile_id": "222",
        "expires_at": 0,
        "data_access_expires_at": 0,
        "scopes": ["pages_show_list", "pages_read_engagement", "pages_read_user_content"],
    }
}


def test_script_token_trong_khong_goi_mang():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi Facebook khi chưa có token")

    ket_qua = _chay_script(handler, token="   ")
    assert ket_qua.san_sang is False
    assert "CHƯA SẴN SÀNG" in ket_qua.van_ban()
    assert "docs/huong-dan-facebook-token.md" in ket_qua.van_ban()


def test_script_duong_di_day_du_bao_san_sang():
    handler = _script_handler(
        debug=_DEBUG_OK,
        live=[
            {
                "id": "10001",
                "status": "LIVE",
                "live_views": 42,
                "broadcast_start_time": "2026-09-09T11:30:00+0000",
                "permalink_url": "/livelab/videos/10001",
            }
        ],
        comments={"data": [{"id": "1_2", "message": "chốt đơn", "created_time": "x"}]},
    )
    ket_qua = _chay_script(handler)
    text = ket_qua.van_ban()
    assert ket_qua.san_sang is True
    assert "KẾT LUẬN: SẴN SÀNG" in text
    assert "10001" in text  # live-video id để dán thẳng vào runner
    assert "Đọc bình luận  : OK" in text


def test_script_khong_bao_gio_in_noi_dung_binh_luan():
    """Quy tắc PII: script chỉ đếm bình luận, không in nội dung/tên người xem."""
    handler = _script_handler(
        debug=_DEBUG_OK,
        live=[{"id": "10001", "status": "LIVE", "live_views": 3}],
        comments={
            "data": [
                {
                    "id": "1_2",
                    "message": "ib em nhé sđt 0901234567",
                    "created_time": "2026-09-09T11:31:00+0000",
                    "from": {"id": "999", "name": "Trần Thị B"},
                }
            ]
        },
    )
    text = _chay_script(handler).van_ban()
    assert "0901234567" not in text
    assert "Trần Thị B" not in text
    assert "lấy được 1 bình luận" in text


def test_script_phat_hien_user_token_thay_vi_page_token():
    debug = {"data": dict(_DEBUG_OK["data"], type="USER")}
    handler = _script_handler(debug=debug, live=[{"id": "10001", "status": "LIVE"}])
    ket_qua = _chay_script(handler)
    assert ket_qua.san_sang is False
    assert any("USER token" in ly_do for ly_do in ket_qua.ly_do_chan)
    assert any("/me/accounts" in ly_do for ly_do in ket_qua.ly_do_chan)


def test_script_bao_thieu_quyen_doc_binh_luan():
    debug = {"data": dict(_DEBUG_OK["data"], scopes=["pages_show_list", "pages_read_engagement"])}
    handler = _script_handler(debug=debug, live=[{"id": "10001", "status": "LIVE"}])
    ket_qua = _chay_script(handler)
    assert ket_qua.san_sang is False
    assert any("pages_read_user_content" in ly_do for ly_do in ket_qua.ly_do_chan)


def test_script_bao_token_het_han():
    het_han = int(datetime(2026, 9, 1, tzinfo=UTC).timestamp())
    debug = {"data": dict(_DEBUG_OK["data"], is_valid=False, expires_at=het_han)}
    handler = _script_handler(debug=debug)
    ket_qua = _chay_script(handler)
    text = ket_qua.van_ban()
    assert ket_qua.san_sang is False
    assert "ĐÃ HẾT HẠN" in text
    assert any("KHÔNG hợp lệ" in ly_do for ly_do in ket_qua.ly_do_chan)


def test_script_loi_quyen_khi_doc_binh_luan_bi_chan():
    handler = _script_handler(
        debug=_DEBUG_OK,
        live=[{"id": "10001", "status": "LIVE"}],
        comments_status=403,
        comments={
            "error": {
                "message": "(#200) Missing pages_read_user_content",
                "type": "OAuthException",
                "code": 200,
            }
        },
    )
    ket_qua = _chay_script(handler)
    assert ket_qua.san_sang is False
    assert any("pages_read_user_content" in ly_do for ly_do in ket_qua.ly_do_chan)


def test_script_khong_co_live_thi_canh_bao_chu_khong_chan():
    """Chưa từng live thì không thể xác minh đọc bình luận — nói thẳng ra."""
    handler = _script_handler(debug=_DEBUG_OK, live=[])
    ket_qua = _chay_script(handler)
    assert ket_qua.san_sang is True  # token/quyền vẫn đạt
    assert any("phát live thử" in c for c in ket_qua.canh_bao)


def test_script_canh_bao_khi_page_id_env_lech():
    handler = _script_handler(
        debug=_DEBUG_OK,
        me={"id": "999", "name": "Page Khác"},
        live=[{"id": "10001", "status": "LIVE"}],
        comments={"data": []},
    )
    ket_qua = _chay_script(handler, page_id="222")
    assert any("KHÁC Page của token" in c for c in ket_qua.canh_bao)


def test_script_thieu_app_secret_chi_canh_bao():
    """Không có app id/secret thì /debug_token hỏng — vẫn phải kiểm tra tiếp."""
    handler = _script_handler(
        debug_status=400,
        debug={"error": {"message": "app token required", "code": 190}},
        live=[{"id": "10001", "status": "LIVE"}],
        comments={"data": [{"id": "1_2", "message": "ok", "created_time": "x"}]},
    )
    ket_qua = _chay_script(handler)
    assert ket_qua.san_sang is True
    assert any("FACEBOOK_APP_ID" in c for c in ket_qua.canh_bao)
    assert "Đọc bình luận  : OK" in ket_qua.van_ban()
