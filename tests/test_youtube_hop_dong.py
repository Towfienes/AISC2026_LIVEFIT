"""Hợp đồng dữ liệu YouTube Live Streaming API ↔ ``livelift.ingest.youtube``.

Fixture ở ``tests/data/youtube/`` dựng ĐÚNG cấu trúc trường của tài liệu chính thức
(nguồn + ngày truy cập ghi trong trường ``_nguon`` của từng tệp), toàn dữ liệu GIẢ:

- https://developers.google.com/youtube/v3/live/docs/liveChatMessages (cập nhật 2026-09-14)
- https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list (cập nhật 2026-09-14)
- https://youtube.googleapis.com/$discovery/rest?version=v3 (revision 20260914)
- https://developers.google.com/youtube/v3/docs/videos (cập nhật 2026-09-14)

Điều khoá ở đây:
1. chỉ ``textMessageEvent`` thành :class:`RawComment`; Super Chat, Super Sticker, quà
   Jewels (cả hai dạng trường mâu thuẫn của Google), hội viên, poll, cấm người dùng,
   tin đã xoá, kết thúc chat và loại lạ đều bị bỏ CÓ CHỦ ĐÍCH (hồi quy kiểm 17/09/2026:
   parser cũ lấy ``displayMessage`` của MỌI loại nên sự kiện trả phí lẫn thành bình luận);
2. ``author_ext_id`` luôn ``None`` và không trường nào của RawComment mang tên/mã kênh;
3. kiểu dữ liệu thật trong JSON (chuỗi số ``concurrentViewers``, ``publishedAt`` 1 hoặc 6
   chữ số lẻ) được client xử lý đúng; vòng poll dừng ở ``offlineAt``.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from livelift.ingest.base import ApiSink, RawComment
from livelift.ingest.youtube import (
    COMMENT_TYPES,
    DEFAULT_POLL_FLOOR_MS,
    YouTubeLiveChatClient,
    parse_live_chat_message,
)

DATA = Path(__file__).resolve().parent / "data" / "youtube"
TEP_CHAT = sorted(p.name for p in DATA.glob("chat_*.json"))
TEP_TAT_CA = sorted(p.name for p in DATA.glob("*.json"))


def doc_tho(ten: str) -> Any:
    return json.loads((DATA / ten).read_text(encoding="utf-8"))


def doc(ten: str) -> dict[str, Any]:
    """Thân phản hồi như Google trả — bỏ khoá ``_...`` dành cho người đọc."""
    raw = doc_tho(ten)
    assert isinstance(raw, dict)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def muc(ten: str) -> dict[str, dict[str, Any]]:
    """Các item của một trang chat theo id (id trùng: bản sau đè bản trước)."""
    return {m["id"]: m for m in doc(ten)["items"]}


@pytest.fixture
def sleeps(monkeypatch):
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


# --- 0. chính các fixture ------------------------------------------------------


def test_co_du_bo_fixture():
    assert len(TEP_CHAT) >= 6
    assert {"video_dang_live.json", "loi_key_sai.json", "loi_khong_co_key.json"} <= set(TEP_TAT_CA)


@pytest.mark.parametrize("ten", TEP_TAT_CA)
def test_moi_fixture_ghi_nguon_va_la_du_lieu_gia(ten):
    raw = doc_tho(ten)
    phan_tu = raw[0] if isinstance(raw, list) else raw
    nguon = phan_tu["_nguon"]
    assert nguon["tai_lieu"], "phải có ít nhất một nguồn"
    assert all("17/09/2026" in n for n in nguon["tai_lieu"]), "mỗi nguồn ghi ngày truy cập"
    assert any("https://" in n for n in nguon["tai_lieu"]) or "Đo trực tiếp" in str(
        nguon["tai_lieu"]
    )
    assert "GIẢ" in nguon["ghi_chu"]


@pytest.mark.parametrize("ten", sorted(p.name for p in DATA.glob("loi_*.json")))
def test_fixture_loi_dung_khuon_core_errors(ten):
    raw = doc_tho(ten)
    phan_tu = raw[0] if isinstance(raw, list) else raw
    err = phan_tu["error"]
    assert err["code"] == phan_tu["_http_status"]
    assert err["message"]
    assert all(e["reason"] for e in err["errors"])


@pytest.mark.parametrize("ten", TEP_CHAT)
def test_trang_chat_dung_khung_list_response(ten):
    body = doc(ten)
    assert body["kind"] == "youtube#liveChatMessageListResponse"
    assert isinstance(body["pollingIntervalMillis"], int)
    assert body["pageInfo"]["resultsPerPage"] == len(body["items"])
    for m in body["items"]:
        assert m["kind"] == "youtube#liveChatMessage"
        # 'This property is always present' (snippet.type).
        assert m["snippet"]["type"]
        assert m["snippet"]["publishedAt"].endswith("Z")


def test_tombstone_chi_co_ba_truong_theo_tai_lieu():
    tomb = muc("chat_trang_da_xoa_bi_chan.json")["MSG_GIA_DA_XOA"]["snippet"]
    assert set(tomb) == {"type", "liveChatId", "publishedAt"}


def test_hai_dang_truong_qua_dung_nguon():
    items = doc("chat_trang_qua_jewels.json")["items"]
    discovery, html, combo = items
    assert isinstance(discovery["snippet"]["giftDetails"]["giftDuration"], str)  # google-duration
    meta = html["snippet"]["giftEventDetails"]["giftMetadata"]
    assert set(meta["giftDuration"]) == {"seconds", "nanos"}
    assert combo["id"] == discovery["id"]  # 'the same ID may be reused to update the combo count'
    assert (
        combo["snippet"]["giftDetails"]["comboCount"]
        > discovery["snippet"]["giftDetails"]["comboCount"]
    )


def test_so_tien_la_chuoi_uint64_ep_kieu_duoc():
    sc = muc("chat_trang_su_kien_tra_phi.json")["MSG_GIA_SUPER_CHAT"]["snippet"]
    amount = sc["superChatDetails"]["amountMicros"]
    assert isinstance(amount, str)
    # '...if the purchase amount is one dollar, the snippet.amountMicros property value is 1000000'
    assert int(amount) / 1_000_000 == 20_000


# --- 1. parser: chỉ tin nhắn văn bản là bình luận ----------------------------------


@pytest.mark.parametrize("ten", TEP_CHAT)
def test_moi_item_parse_khong_nem_loi(ten):
    body = doc(ten)
    for m in [*body["items"], *([body["activePollItem"]] if "activePollItem" in body else [])]:
        parse_live_chat_message(m)


def test_chi_text_message_event_la_binh_luan():
    assert frozenset({"textMessageEvent"}) == COMMENT_TYPES
    for ten in TEP_CHAT:
        for m in doc(ten)["items"]:
            ket_qua = parse_live_chat_message(m)
            if m["snippet"]["type"] == "textMessageEvent":
                assert isinstance(ket_qua, RawComment), (ten, m["id"])
            else:
                assert ket_qua is None, (ten, m["id"], m["snippet"]["type"])


def test_van_ban_vao_raw_comment_dung_truong():
    items = muc("chat_trang_van_ban.json")
    c1 = parse_live_chat_message(items["MSG_GIA_VAN_BAN_1"])
    assert c1 is not None
    assert c1.platform == "youtube"
    assert c1.ext_id == "MSG_GIA_VAN_BAN_1"
    assert c1.text == items["MSG_GIA_VAN_BAN_1"]["snippet"]["textMessageDetails"]["messageText"]
    # 'YYYY-MM-DDThh:mm:ss.sZ' — 6 chữ số lẻ và 1 chữ số lẻ đều ra UTC có múi giờ.
    assert c1.ts_utc == datetime(2026, 9, 20, 13, 0, 1, 123456, tzinfo=UTC)
    c2 = parse_live_chat_message(items["MSG_GIA_VAN_BAN_2"])
    assert c2 is not None
    assert c2.ts_utc == datetime(2026, 9, 20, 13, 0, 2, 500000, tzinfo=UTC)


def test_author_ext_id_none_va_khong_mang_dinh_danh():
    items = muc("chat_trang_van_ban.json")
    for mid, m in items.items():
        c = parse_live_chat_message(m)
        assert c is not None
        assert c.author_ext_id is None
        dump = repr(c)
        assert "UC_GIA_" not in dump, mid
        assert "Nguyen Van Gia" not in dump, mid
        assert "anh-dai-dien-gia" not in dump, mid


@pytest.mark.parametrize(
    "mid",
    [
        "MSG_GIA_SUPER_CHAT",
        "MSG_GIA_STICKER_DISCOVERY",
        "MSG_GIA_STICKER_HTML",
        "MSG_GIA_HOI_VIEN_MOI",
        "MSG_GIA_COT_MOC",
        "MSG_GIA_TANG_HOI_VIEN",
        "MSG_GIA_NHAN_HOI_VIEN",
        "MSG_GIA_POLL",
    ],
)
def test_su_kien_tra_phi_hoi_vien_poll_bi_bo_co_chu_dich(mid):
    """Hồi quy: parser cũ biến displayMessage của các sự kiện này thành bình luận."""
    m = muc("chat_trang_su_kien_tra_phi.json")[mid]
    assert m["snippet"]["hasDisplayContent"] is True
    assert m["snippet"]["displayMessage"]
    assert parse_live_chat_message(m) is None


def test_active_poll_item_khong_phai_binh_luan():
    body = doc("chat_trang_su_kien_tra_phi.json")
    poll = body["activePollItem"]
    # Gọi bằng API key: 'The tally is only present if the API request is authorized by
    # the channel owner.'
    assert all("tally" not in o for o in poll["snippet"]["pollDetails"]["metadata"]["options"])
    assert parse_live_chat_message(poll) is None


@pytest.mark.parametrize("mid", ["MSG_GIA_QUA_1", "MSG_GIA_QUA_2"])
def test_qua_jewels_ca_hai_dang_bi_bo(mid):
    for m in doc("chat_trang_qua_jewels.json")["items"]:
        if m["id"] == mid:
            assert parse_live_chat_message(m) is None


@pytest.mark.parametrize(
    "mid",
    [
        "MSG_GIA_DA_XOA",
        "MSG_GIA_CAM",
        "MSG_GIA_CHE_DO_HOI_VIEN",
        "MSG_GIA_LOAI_MOI",
        "MSG_GIA_HET_CHAT",
    ],
)
def test_tin_da_xoa_bi_cam_he_thong_loai_la_bi_bo(mid):
    assert parse_live_chat_message(muc("chat_trang_da_xoa_bi_chan.json")[mid]) is None


def test_item_khong_co_type_giu_hanh_vi_cu():
    """Tài liệu nói type luôn có; payload tự dựng thiếu type vẫn đọc displayMessage."""
    item = {
        "id": "m-cu",
        "snippet": {"publishedAt": "2026-09-20T13:00:00Z", "displayMessage": "chốt đơn"},
    }
    c = parse_live_chat_message(item)
    assert c is not None
    assert c.text == "chốt đơn"


# --- 2. client trên fixture: vòng poll, người xem, chat id ----------------------------


def _client(handler) -> tuple[YouTubeLiveChatClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return YouTubeLiveChatClient(api_key="k", client=http), http


def test_vong_poll_chi_ra_binh_luan_van_ban_va_dung_o_offline(sleeps):
    trang = iter(
        [
            "chat_trang_su_kien_tra_phi.json",
            "chat_trang_qua_jewels.json",
            "chat_trang_da_xoa_bi_chan.json",
            "chat_trang_van_ban.json",
            "chat_trang_offline.json",
        ]
    )
    chat_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/videos"):
            return httpx.Response(200, json=doc("video_dang_live.json"))
        chat_requests.append(request)
        return httpx.Response(200, json=doc(next(trang)))

    async def run() -> list[RawComment]:
        client, http = _client(handler)
        try:
            return [c async for c in client.iter_comments("LiveLiftGia")]
        finally:
            await http.aclose()

    comments = asyncio.run(run())
    assert [c.ext_id for c in comments] == [
        "MSG_GIA_VAN_BAN_1",
        "MSG_GIA_VAN_BAN_2",
        "MSG_GIA_CUOI",
    ]
    assert all(c.author_ext_id is None for c in comments)
    assert len(chat_requests) == 5  # dừng ngay trang có offlineAt, không poll thêm
    assert chat_requests[0].url.params["liveChatId"] == "LIVECHAT_GIA_1"
    assert "pageToken" not in chat_requests[0].url.params
    assert chat_requests[1].url.params["pageToken"] == "TOKEN_GIA_TRANG_TIEP"
    # Tôn trọng pollingIntervalMillis (5123 ms > sàn 2000 ms) giữa các trang.
    assert sleeps == [max(5123, DEFAULT_POLL_FLOOR_MS) / 1000] * 4


def test_nguoi_xem_chuoi_so_va_dung_khi_ket_thuc(sleeps):
    trang = iter(["video_dang_live.json", "video_da_ket_thuc.json"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=doc(next(trang)))

    async def run() -> list[float]:
        client, http = _client(handler)
        try:
            return [t.viewers async for t in client.iter_viewers("LiveLiftGia")]
        finally:
            await http.aclose()

    # concurrentViewers là CHUỖI "3" trong JSON (Discovery: string uint64).
    assert asyncio.run(run()) == [3.0]


def test_chat_id_chi_co_khi_dang_live():
    def goi(ten: str) -> str:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=doc(ten))

        async def run() -> str:
            client, http = _client(handler)
            try:
                return await client.get_active_live_chat_id("LiveLiftGia")
            finally:
                await http.aclose()

        return asyncio.run(run())

    assert goi("video_dang_live.json") == "LIVECHAT_GIA_1"
    for ten in ("video_sap_phat.json", "video_da_ket_thuc.json", "video_khong_phai_live.json"):
        with pytest.raises(RuntimeError, match="no active live chat"):
            goi(ten)
    with pytest.raises(RuntimeError, match="not found"):
        goi("video_khong_thay.json")


def test_binh_luan_tu_fixture_qua_sink_da_loc_pii_va_khong_co_tac_gia():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    comment = parse_live_chat_message(muc("chat_trang_van_ban.json")["MSG_GIA_VAN_BAN_1"])
    assert comment is not None

    async def run() -> bool:
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        sink = ApiSink("http://api.test", "phien-1", client=http, spool_dir=None, token="")
        try:
            return await sink.post_comment(comment)
        finally:
            await http.aclose()

    assert asyncio.run(run()) is True
    raw = captured[0].content.decode("utf-8")
    body = json.loads(raw)
    assert "0901234567" not in raw
    assert "[SĐT]" in body["text"]
    assert not any("author" in k.lower() for k in body)
    assert "UC_GIA_" not in raw
