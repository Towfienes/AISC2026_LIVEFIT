"""scripts/kiem_tra_youtube.py: mọi nhánh, không mạng, không lộ khoá, không lộ bình luận.

Chưa có YOUTUBE_API_KEY thật để thử, nên mỗi nhánh được khoá bằng
``httpx.MockTransport`` trả đúng thân phản hồi trong ``tests/data/youtube/`` — hai thân
lỗi khoá (không key, key sai) là nguyên văn đo thật ngày 17/09/2026 bằng key GIẢ; các
thân còn lại dựng theo tài liệu chính thức (nguồn ghi trong trường ``_nguon`` của từng
tệp).

Ba điều không bao giờ được xảy ra, kiểm ở mọi nhánh:
1. khoá xuất hiện trong stdout hoặc log;
2. nội dung tin nhắn, tên hiển thị, mã kênh người xem xuất hiện trong stdout;
3. mã thoát sai (0 = SẴN SÀNG, 1 = CHƯA SẴN SÀNG).
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

_GOC = Path(__file__).resolve().parent.parent
_SCRIPT = _GOC / "scripts" / "kiem_tra_youtube.py"
_spec = importlib.util.spec_from_file_location("kiem_tra_youtube", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
kt = importlib.util.module_from_spec(_spec)
# @dataclass tra module trong sys.modules khi phân giải type hint -> đăng ký TRƯỚC.
sys.modules[_spec.name] = kt
_spec.loader.exec_module(kt)

DATA = _GOC / "tests" / "data" / "youtube"
KHOA = "AIzaSyKHOA_GIA_CHO_TEST_0123456789abcd"
VIDEO = "LiveLiftGia"

# Chuỗi riêng tư có trong fixture chat — không chuỗi nào được lên màn hình.
RIENG_TU = (
    "0901234567",
    "cho em xin link",
    "còn màu đen",
    "Nguyen Van Gia",
    "Tran Thi Gia",
    "chot 2 cai",
    "3 thang roi",
    "Le Van Bi Cam Gia",
    "Vu Thi Gia",
    "Pham Van Gia",
    "Do Thi Gia",
    "UC_GIA_",
    "anh-dai-dien-gia",
    "Ban thich mau nao",
    "cam on shop",
)


def doc_fixture(ten: str) -> tuple[int, Any]:
    """(mã HTTP, thân phản hồi) — bỏ các khoá ``_...`` chỉ dành cho người đọc."""
    raw = json.loads((DATA / ten).read_text(encoding="utf-8"))
    phan_tu = raw[0] if isinstance(raw, list) else raw
    status = int(phan_tu.get("_http_status", 200))
    if isinstance(raw, list):
        body: Any = [{k: v for k, v in p.items() if not k.startswith("_")} for p in raw]
    else:
        body = {k: v for k, v in raw.items() if not k.startswith("_")}
    return status, body


class MayChuGia:
    """Google giả: trả fixture theo đường dẫn, ghi lại mọi request."""

    def __init__(self, videos: str | None = None, chat: str | None = None) -> None:
        self.videos = videos
        self.chat = chat
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        ten = self.videos if request.url.path.endswith("/videos") else self.chat
        assert ten is not None, f"không được gọi {request.url.path} trong ca này"
        status, body = doc_fixture(ten)
        return httpx.Response(status, json=body)

    def duong_dan(self) -> list[str]:
        return [r.url.path for r in self.requests]


def chay(capsys, handler, argv: list[str] | None = None, khoa: str = KHOA) -> tuple[int, str]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    code = kt.main(argv or [], settings=SimpleNamespace(youtube_api_key=khoa), http=http)
    out = capsys.readouterr().out
    return code, out


def kiem_an_toan(out: str) -> None:
    assert KHOA not in out
    assert KHOA[:12] not in out
    assert KHOA[-8:] not in out
    for chuoi in RIENG_TU:
        assert chuoi not in out, f"lộ chuỗi riêng tư: {chuoi!r}"


# --- 1. khoá ---------------------------------------------------------------


def test_thieu_khoa_chan_va_khong_goi_google(capsys):
    may = MayChuGia()
    code, out = chay(capsys, may, ["--video", VIDEO], khoa="")
    assert code == 1
    assert "CHƯA SẴN SÀNG" in out
    assert "Chưa có YOUTUBE_API_KEY" in out
    assert "HUONG-DAN-LAY-KHOA-API.md" in out
    assert may.requests == []
    # Ước lượng quota vẫn in — không cần mạng.
    assert "ƯỚC LƯỢNG QUOTA" in out


def test_khoa_sai_do_that_doc_details_truoc(capsys):
    """Key sai hiện trả 400 + errors[].reason 'badRequest'; lý do thật ở details[]."""
    may = MayChuGia(videos="loi_key_sai.json")
    code, out = chay(capsys, may)
    assert code == 1
    assert "API key không hợp lệ (API_KEY_INVALID)" in out
    assert "Cách sửa:" in out
    assert len(may.requests) == 1
    kiem_an_toan(out)


def test_khoa_sai_kieu_cu_keyinvalid(capsys):
    code, out = chay(capsys, MayChuGia(videos="loi_key_sai_kieu_cu.json"))
    assert code == 1
    assert "(keyInvalid)" in out
    kiem_an_toan(out)


def test_api_chua_bat_in_link_bat_api(capsys):
    code, out = chay(capsys, MayChuGia(videos="loi_chua_bat_api.json"))
    assert code == 1
    assert "chưa bật YouTube Data API v3" in out
    assert "APIs & Services → Library" in out
    assert (
        "https://console.developers.google.com/apis/api/youtube.googleapis.com/overview"
        "?project=123456789012" in out
    )
    kiem_an_toan(out)


def test_het_quota(capsys):
    code, out = chay(capsys, MayChuGia(videos="loi_het_quota.json"))
    assert code == 1
    assert "hết hạn mức quota" in out
    assert "0h giờ Thái Bình Dương" in out
    kiem_an_toan(out)


def test_khoa_bi_gioi_han_api(capsys):
    code, out = chay(capsys, MayChuGia(videos="loi_key_bi_gioi_han.json"))
    assert code == 1
    assert "API_KEY_SERVICE_BLOCKED" in out
    assert "API restrictions" in out
    kiem_an_toan(out)


def test_khong_video_chi_kiem_khoa_ok(capsys):
    may = MayChuGia(videos="video_khong_thay.json")
    code, out = chay(capsys, may)
    assert code == 0
    assert "KẾT LUẬN: SẴN SÀNG" in out
    assert "Google nhận khoá" in out
    assert "Chưa thử đọc chat" in out
    assert may.duong_dan() == ["/youtube/v3/videos"]
    params = may.requests[0].url.params
    assert params["part"] == "id"
    assert params["id"] == kt.ID_KIEM_KHOA
    # Đi đúng đường gọi của bộ thu (YouTubeLiveChatClient._get đặt khoá ở key=).
    assert params["key"] == KHOA
    assert "Lần kiểm tra này: 1 videos.list + 0 liveChatMessages.list = 1 đơn vị" in out
    kiem_an_toan(out)


def test_khong_video_404_videonotfound_van_la_khoa_hop_le(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "error": {
                    "code": 404,
                    "message": "The video that you are trying to retrieve cannot be found.",
                    "errors": [{"domain": "youtube.video", "reason": "videoNotFound"}],
                }
            },
        )

    code, out = chay(capsys, handler)
    assert code == 0
    assert "OK (HTTP 404)" in out


def test_khoa_co_ngoac_kep_canh_bao(capsys):
    khoa = '"AIzaSyKHOA_GIA"'
    code, out = chay(capsys, MayChuGia(videos="video_khong_thay.json"), khoa=khoa)
    assert code == 0
    assert "ngoặc kép" in out
    assert khoa not in out


# --- 2. video ------------------------------------------------------------------


def test_video_sap_phat_canh_bao_khong_doc_chat(capsys):
    may = MayChuGia(videos="video_sap_phat.json")
    code, out = chay(capsys, may, ["--video", f"https://youtu.be/{VIDEO}"])
    assert code == 0
    assert "SẮP PHÁT" in out
    assert "activeLiveChatId: KHÔNG có" in out
    assert "chạy lại lệnh sau khi đã bấm phát" in out
    assert may.duong_dan() == ["/youtube/v3/videos"]  # không gọi chat
    kiem_an_toan(out)


def test_video_da_ket_thuc_chan(capsys):
    may = MayChuGia(videos="video_da_ket_thuc.json")
    code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 1
    assert "đã kết thúc" in out
    assert "Người xem đồng thời: không có trường" in out
    assert may.duong_dan() == ["/youtube/v3/videos"]
    kiem_an_toan(out)


def test_video_khong_phai_live_chan(capsys):
    code, out = chay(capsys, MayChuGia(videos="video_khong_phai_live.json"), ["--video", VIDEO])
    assert code == 1
    assert "không phải buổi phát trực tiếp" in out


def test_video_khong_thay_chan(capsys):
    code, out = chay(capsys, MayChuGia(videos="video_khong_thay.json"), ["--video", VIDEO])
    assert code == 1
    assert "Tìm thấy        : KHÔNG" in out


def test_video_link_sai_khong_goi_google(capsys):
    may = MayChuGia()
    code, out = chay(capsys, may, ["--video", "https://www.youtube.com/@kenh-nhom"])
    assert code == 1
    assert "Không nhận ra video YouTube" in out
    assert may.requests == []


def test_video_live_goi_dung_tham_so(capsys):
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_van_ban.json")
    code, _ = chay(capsys, may, ["--video", f"https://www.youtube.com/watch?v={VIDEO}&t=3"])
    assert code == 0
    assert may.duong_dan() == ["/youtube/v3/videos", "/youtube/v3/liveChat/messages"]
    v = may.requests[0].url.params
    assert v["id"] == VIDEO
    assert v["part"] == "snippet,liveStreamingDetails,status"
    c = may.requests[1].url.params
    assert c["liveChatId"] == "LIVECHAT_GIA_1"
    # Cùng tham số với iter_comments: không xin authorDetails (giảm PII).
    assert c["part"] == "id,snippet"
    assert "authorDetails" not in c["part"]
    assert c["maxResults"] == "500"


# --- 3. chat -------------------------------------------------------------------


def test_live_co_binh_luan_chi_dem_khong_in_noi_dung(capsys):
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_van_ban.json")
    code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 0
    assert "KẾT LUẬN: SẴN SÀNG" in out
    assert "ĐANG LIVE" in out
    assert "Người xem đồng thời: 3" in out
    assert "Số mục trả về   : 2" in out
    assert "textMessageEvent=2" in out
    assert "Bộ thu nhận là bình luận: 2" in out
    assert "pollingIntervalMillis: 5.123 ms" in out
    assert "Không công khai (unlisted)" in out
    assert "API key đọc được chat của video Không công khai" in out
    assert "Lần kiểm tra này: 1 videos.list + 1 liveChatMessages.list = 2–6 đơn vị" in out
    kiem_an_toan(out)


def test_live_su_kien_tra_phi_bi_bo_co_chu_dich(capsys):
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_su_kien_tra_phi.json")
    code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 0
    assert "superChatEvent=1" in out
    assert "superStickerEvent=2" in out
    assert "pollEvent=1" in out
    assert "Bộ thu nhận là bình luận: 0" in out
    assert "activePollItem  : có" in out
    assert "loại sự kiện chưa có trong tài liệu" not in out
    kiem_an_toan(out)


def test_live_qua_jewels_bao_dang_truong(capsys):
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_qua_jewels.json")
    code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 0
    assert "giftEvent=3" in out
    assert "snippet.giftDetails (khớp Discovery/proto)" in out
    assert "snippet.giftEventDetails.giftMetadata (khớp trang tài liệu HTML)" in out
    kiem_an_toan(out)


def test_live_loai_su_kien_la_duoc_canh_bao(capsys):
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_da_xoa_bi_chan.json")
    code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 0
    assert "tombstone=1" in out
    assert "userBannedEvent=1" in out
    assert "loại sự kiện chưa có trong tài liệu: suKienTuongLaiGia" in out
    kiem_an_toan(out)


def test_live_trang_rong_canh_bao(capsys):
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_rong.json")
    code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 0
    assert "chưa có tin nhắn nào" in out
    assert "pollingIntervalMillis: 10.000 ms" in out


def test_live_offline_chan(capsys):
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_offline.json")
    code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 1
    assert "CÓ — luồng đã offline" in out
    assert "bộ thu DỪNG đọc chat" in out
    kiem_an_toan(out)


@pytest.mark.parametrize(
    ("fixture", "cau"),
    [
        ("loi_chat_da_ket_thuc.json", "(liveChatEnded)"),
        ("loi_chat_bi_tat.json", "(liveChatDisabled)"),
        ("loi_khong_thay_chat.json", "(liveChatNotFound)"),
        ("loi_chat_khong_co_quyen.json", "Google từ chối quyền đọc (forbidden)"),
        ("loi_qua_nhanh.json", "(rateLimitExceeded)"),
        ("loi_het_quota.json", "(quotaExceeded)"),
    ],
)
def test_loi_doc_chat_phan_loai_rieng_tung_ca(capsys, fixture, cau):
    may = MayChuGia(videos="video_dang_live.json", chat=fixture)
    code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 1
    assert "Không đọc được chat: " in out
    assert cau in out
    kiem_an_toan(out)


# --- 4. mạng hỏng, phản hồi hỏng, log ---------------------------------------------


def test_loi_mang_khong_in_chuoi_ngoai_le_co_url(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        # Chuỗi ngoại lệ cố ý chứa URL đầy đủ có key= — script chỉ được in tên loại lỗi.
        raise httpx.ConnectError(f"không kết nối được {request.url}", request=request)

    code, out = chay(capsys, handler, ["--video", VIDEO])
    assert code == 1
    assert "Không gọi được Google (ConnectError)" in out
    assert "key=" not in out
    kiem_an_toan(out)


def test_phan_hoi_khong_phai_json(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>dang nhap wifi</html>")

    code, out = chay(capsys, handler)
    assert code == 1
    assert "không phải JSON" in out


def test_loi_4xx_khong_than_khong_in_url(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(418, text="")

    code, out = chay(capsys, handler)
    assert code == 1
    assert "HTTP 418" in out
    kiem_an_toan(out)


def test_khoa_khong_ra_log_httpx(capsys, caplog):
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_van_ban.json")
    with caplog.at_level(logging.DEBUG):
        code, out = chay(capsys, may, ["--video", VIDEO])
    assert code == 0
    dong_httpx = [r.getMessage() for r in caplog.records if r.name == "httpx"]
    assert dong_httpx, "httpx phải ghi 'HTTP Request' ở mức INFO (điều kiện của phép thử)"
    assert any("key=***" in d for d in dong_httpx)
    for r in caplog.records:
        assert KHOA not in r.getMessage()
        for chuoi in RIENG_TU:
            assert chuoi not in r.getMessage()
    kiem_an_toan(out)


def test_van_ban_che_khoa_lop_cuoi():
    kq = kt.KetQua()
    kq.ghi(f"dòng lỗi giả chứa {KHOA}")
    assert KHOA not in kq.van_ban(KHOA)
    assert "***" in kq.van_ban(KHOA)


# --- 5. phần thuần logic ------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture", "nhan"),
    [
        ("loi_khong_co_key.json", "THIEU_KEY"),
        ("loi_key_sai.json", "KEY_SAI"),
        ("loi_key_sai_kieu_cu.json", "KEY_SAI"),
        ("loi_bao_trong_mang.json", "KEY_SAI"),
        ("loi_chua_bat_api.json", "CHUA_BAT_API"),
        ("loi_key_bi_gioi_han.json", "KEY_BI_GIOI_HAN"),
        ("loi_het_quota.json", "HET_QUOTA"),
        ("loi_qua_nhanh.json", "QUA_NHANH"),
        ("loi_chat_da_ket_thuc.json", "CHAT_DA_KET_THUC"),
        ("loi_chat_bi_tat.json", "CHAT_BI_TAT"),
        ("loi_khong_thay_chat.json", "KHONG_THAY_CHAT"),
        ("loi_chat_khong_co_quyen.json", "KHONG_CO_QUYEN"),
    ],
)
def test_phan_loai_moi_fixture_loi(fixture, nhan):
    status, body = doc_fixture(fixture)
    assert kt.phan_loai_loi(status, body).nhan == nhan


def test_phan_loai_theo_ma_http_khi_khong_co_ly_do():
    assert kt.phan_loai_loi(503, None).nhan == "LOI_MAY_CHU"
    assert kt.phan_loai_loi(429, {}).nhan == "QUA_NHANH"
    assert kt.phan_loai_loi(403, {"error": {"code": 403}}).nhan == "KHONG_RO"


def test_details_duoc_doc_truoc_errors():
    """Cùng thân có errors[] 'forbidden' nhưng details[] nói rõ key bị chặn API."""
    body = {
        "error": {
            "errors": [{"reason": "forbidden"}],
            "details": [{"reason": "API_KEY_HTTP_REFERRER_BLOCKED"}],
        }
    }
    loi = kt.phan_loai_loi(403, body)
    assert loi.nhan == "KEY_BI_GIOI_HAN"
    assert "Application restrictions" in loi.cach_sua


def test_ly_do_la_khong_duoc_in_nguyen():
    loi = kt.phan_loai_loi(400, {"error": {"errors": [{"reason": "<script>0901234567"}]}})
    assert loi.nhan == "KHONG_RO"
    assert "0901234567" not in loi.mo_ta


@pytest.mark.parametrize(
    ("nhap", "ra"),
    [
        (VIDEO, VIDEO),
        (f"https://www.youtube.com/watch?v={VIDEO}", VIDEO),
        (f"https://youtu.be/{VIDEO}?si=abc", VIDEO),
        (f"https://www.youtube.com/live/{VIDEO}?feature=share", VIDEO),
        ("https://www.youtube.com/@kenh-nhom", None),
        ("", None),
    ],
)
def test_chuan_hoa_video(nhap, ra):
    assert kt.chuan_hoa_video(nhap) == ra


def test_uoc_luong_chua_do_dung_san_bo_thu():
    """Chỉ buổi 90 phút (bật bộ thu đúng lúc phát): số học cũ giữ nguyên."""
    u = kt.uoc_luong_quota(90, None, cho_truoc_phut=0)
    assert u.san_poll_ms == 2000
    assert u.luot_videos_cho == 0
    assert u.luot_list == 2700
    assert u.luot_videos == 181  # 1 lượt lấy chat id + 180 lượt người xem mỗi 30 s
    assert u.dv_theo_bang == 2881
    assert u.dv_than_trong == 13681
    assert u.dv_than_trong > kt.HAN_MUC_NGAY
    assert u.nhip_toi_thieu_than_trong_s == 10  # 5400*5/(3000-181) = 9,58 -> 10
    assert u.nhip_do_ms is None
    assert u.luot_list_do is None


def test_uoc_luong_mac_dinh_tinh_ca_cho_len_song_t_tru_2h():
    """Phản biện 17/09: bật bộ thu ở T−2h tốn 2 lượt videos.list mỗi vòng dò 20 s."""
    assert kt.CHO_TRUOC_PHUT_MAC_DINH == 120
    assert kt.WAIT_FOR_LIVE_S == 20.0
    u = kt.uoc_luong_quota(90, None)
    assert u.cho_truoc_phut == 120
    assert u.luot_videos_cho == 720  # 7200 s / 20 s = 360 vòng × 2 lượt
    assert u.dv_theo_bang == 720 + 2700 + 181 == 3601
    assert u.dv_than_trong == 720 + 2700 * 5 + 181 == 14401
    assert u.dv_theo_bang > u.ngan_sach_dv  # 36% > ngưỡng 30%
    assert u.nhip_toi_thieu_than_trong_s == 13  # 5400*5/(3000-181-720) = 12,86 -> 13


def test_uoc_luong_cho_len_song_so_hoc():
    assert kt.uoc_luong_quota(90, None, cho_truoc_phut=15).luot_videos_cho == 90
    assert kt.uoc_luong_quota(90, None, cho_truoc_phut=1).luot_videos_cho == 6  # 6 đv/phút
    # Số vòng làm tròn LÊN: cận trên, không bao giờ ước thấp.
    u = kt.uoc_luong_quota(90, None, cho_truoc_phut=1, nhip_cho_len_song_s=25)
    assert u.luot_videos_cho == 6  # ceil(60/25) = 3 vòng × 2


def test_uoc_luong_polling_nho_hon_san_van_dung_san():
    """PR #420 tính ngược ra ≈ 1,41 s/lượt; bộ thu không poll nhanh hơn 2 s."""
    u = kt.uoc_luong_quota(90, 1410, cho_truoc_phut=0)
    assert u.luot_list == 2700
    assert u.luot_list_do == 2700


def test_uoc_luong_khop_so_hoc_bao_cao_nghien_cuu():
    """Báo cáo L2: bám 1,41 s trong 90 phút ≈ 3.830 lượt, 19.150 đơn vị nếu giá 5."""
    u = kt.uoc_luong_quota(90, 1410, san_poll_ms=1000, cho_truoc_phut=0)
    assert u.luot_list_do == 3830
    assert u.luot_list_do * kt.GIA_LIST_THAN_TRONG == 19150


def test_uoc_luong_polling_do_duoc_chi_tham_khao():
    """Phản biện 17/09: nhịp đo lúc thử KHÔNG được hạ trường hợp tốn nhất."""
    u = kt.uoc_luong_quota(90, 5123, cho_truoc_phut=0)
    assert u.nhip_do_ms == 5123
    assert u.luot_list_do == 1055
    assert u.dv_theo_bang_do == 1055 + 181
    assert u.dv_than_trong_do == 1055 * 5 + 181 == 5456
    # Trường hợp tốn nhất vẫn tính theo sàn 2 s, y như khi chưa đo.
    chua_do = kt.uoc_luong_quota(90, None, cho_truoc_phut=0)
    assert (u.luot_list, u.dv_theo_bang, u.dv_than_trong) == (
        chua_do.luot_list,
        chua_do.dv_theo_bang,
        chua_do.dv_than_trong,
    )


@pytest.mark.parametrize("cho", ["120", "0"])
def test_trang_chat_5123_ms_van_canh_bao_b_vuot_han_muc(capsys, cho):
    """Phản biện 17/09 (P2): trang chat lúc thử trả 5.123 ms từng làm mất cảnh báo B."""
    may = MayChuGia(videos="video_dang_live.json", chat="chat_trang_van_ban.json")
    code, out = chay(capsys, may, ["--video", VIDEO, "--cho-truoc-phut", cho])
    assert code == 0  # cảnh báo, không chặn
    assert "KẾT LUẬN: SẴN SÀNG" in out
    assert "VƯỢT hạn mức ngày" in out
    assert "đọc chat mỗi 2,0 s" in out
    assert "pollingIntervalMillis 5.123 ms (mục 4) → đọc mỗi 5,1 s" in out
    assert "CHỈ tham khảo" in out
    assert "PR #420" in out
    if cho == "0":
        assert "Chờ lên sóng    : 0 lượt" in out
        assert "13.681 đơn vị — VƯỢT hạn mức ngày" in out
    else:
        assert "Chờ lên sóng    : 720 lượt videos.list" in out
        assert "14.401 đơn vị — VƯỢT hạn mức ngày" in out
        assert "36% hạn mức ngày — quá ngưỡng 30%" in out
        assert "bật bộ thu gần giờ phát hơn" in out
    kiem_an_toan(out)


def test_cho_truoc_phut_am_bi_tu_choi(capsys):
    may = MayChuGia()
    code, out = chay(capsys, may, ["--cho-truoc-phut", "-5"])
    assert code == 1
    assert "--cho-truoc-phut phải ≥ 0" in out
    assert may.requests == []


def test_video_sap_phat_co_chat_id_truoc_gio_canh_bao(capsys):
    """Tài liệu videos: activeLiveChatId "is filled only if the video is a currently live
    broadcast". Nếu Google trả sớm (trái tài liệu), bộ thu đọc chat suốt lúc chờ."""
    status, body = doc_fixture("video_sap_phat.json")
    body["items"][0]["liveStreamingDetails"]["activeLiveChatId"] = "LIVECHAT_GIA_SOM"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/videos"), "không được đọc chat khi chưa phát"
        return httpx.Response(status, json=body)

    code, out = chay(capsys, handler, ["--video", VIDEO])
    assert code == 0
    assert "activeLiveChatId: có" in out
    assert "video CHƯA phát nhưng Google đã trả activeLiveChatId" in out
    assert "thêm tới 3.600 lượt liveChatMessages.list (3.600–18.000 đơn vị)" in out
    assert "Chưa đo         :" not in out
    kiem_an_toan(out)


def test_video_sap_phat_khong_chat_id_ghi_da_do(capsys):
    code, out = chay(capsys, MayChuGia(videos="video_sap_phat.json"), ["--video", VIDEO])
    assert code == 0
    assert "Đã đo           : video Sắp phát này chưa có activeLiveChatId" in out
    assert "Chưa đo         :" not in out


def test_khong_video_ghi_rui_ro_chat_id_chua_do(capsys):
    code, out = chay(capsys, MayChuGia(videos="video_khong_thay.json"))
    assert code == 0
    assert "Chưa đo         : tài liệu videos nói activeLiveChatId chỉ có khi video" in out


def test_vong_cho_len_song_that_ton_dung_so_luot_videos_list():
    """Khoá LUOT_VIDEOS_MOI_VONG_CHO vào IngestManager thật: mỗi vòng chờ lên sóng của
    YouTube gọi đúng 2 lượt videos.list (bình luận + người xem) và không đọc chat."""
    import asyncio

    from livelift.api.ingest_jobs import IngestManager
    from livelift.ingest.youtube import YouTubeLiveChatClient

    status, body = doc_fixture("video_sap_phat.json")
    luot_theo_vong: list[list[str]] = []

    class KhoGia:
        def get_session(self, session_id: str) -> dict[str, Any]:
            return {"id": session_id, "status": "running"}

    def factory(platform: str) -> YouTubeLiveChatClient:
        assert platform == "youtube"
        cua_vong: list[str] = []
        luot_theo_vong.append(cua_vong)

        async def handler(request: httpx.Request) -> httpx.Response:
            cua_vong.append(request.url.path)
            await asyncio.sleep(0.01)  # độ trễ mạng: hai tác vụ gửi request chồng nhau
            return httpx.Response(status, json=body)

        return YouTubeLiveChatClient(
            api_key=KHOA, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )

    async def chay_vong() -> None:
        m = IngestManager(KhoGia(), client_factory=factory, wait_for_live_s=0.02, watch_every_s=60)
        job = m.start("phien-gia", "youtube", VIDEO)
        for _ in range(500):
            if len(luot_theo_vong) >= 5:
                break
            await asyncio.sleep(0.01)
        await m.stop("phien-gia")
        assert job.state == "da_dung"

    asyncio.run(chay_vong())
    xong = luot_theo_vong[:-1]  # vòng cuối có thể bị dừng giữa chừng
    assert len(xong) >= 4
    for cua_vong in xong:
        assert cua_vong == ["/youtube/v3/videos"] * kt.LUOT_VIDEOS_MOI_VONG_CHO


def test_buoi_qua_dai_vuot_han_muc_theo_bang_thi_chan(capsys):
    code, out = chay(
        capsys, MayChuGia(videos="video_khong_thay.json"), ["--thoi-luong-phut", "400"]
    )
    assert code == 1
    assert "Ngay cả theo bảng giá chính thức" in out


def test_nhip_nguoi_xem_lay_tu_bo_thu():
    assert kt.NHIP_NGUOI_XEM_S == 30.0


def test_dang_truong_qua():
    assert kt.dang_truong_qua({"giftDetails": {}}).startswith("snippet.giftDetails")
    assert "giftMetadata" in kt.dang_truong_qua({"giftEventDetails": {"giftMetadata": {}}})
    assert "không khớp" in kt.dang_truong_qua({"giftEventDetails": {"jewelsAmount": 1}})
    assert kt.dang_truong_qua({"textMessageDetails": {}}) is None
