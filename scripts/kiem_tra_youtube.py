#!/usr/bin/env python3
"""Kiểm tra YouTube Live (API chính thức): đường ingest YouTube đã SẴN SÀNG chưa?

Chạy (từ thư mục gốc repo, sau khi đã điền YOUTUBE_API_KEY vào .env):

    .venv/Scripts/python scripts/kiem_tra_youtube.py                     # chỉ kiểm khoá + API
    .venv/Scripts/python scripts/kiem_tra_youtube.py --video <link|id>   # + live, người xem, chat
    python scripts/kiem_tra_youtube.py --video <link|id>                 # macOS/Linux

Script **CHỈ ĐỌC** — không đăng tin, không ghim, không sửa gì trên YouTube. Nó gọi
đúng các lệnh mà bộ thu sẽ gọi trong phiên thật, qua chính
:class:`livelift.ingest.youtube.YouTubeLiveChatClient` (không tự dựng lệnh gọi):

1. có ``YOUTUBE_API_KEY`` không — KHÔNG in khoá, chỉ in độ dài;
2. một lệnh ``videos.list`` (1 đơn vị quota theo bảng chính thức) để xác nhận Google
   nhận khoá và dự án đã bật YouTube Data API v3; lỗi được phân loại theo
   ``error.details[].reason`` trước rồi mới tới ``error.errors[].reason`` — vì đo thật
   ngày 17/09/2026 key sai trả ``badRequest`` + ``API_KEY_INVALID`` chứ không phải
   ``keyInvalid`` như bảng core_errors;
3. với ``--video``: trạng thái live, ``activeLiveChatId``, ``concurrentViewers``;
4. đọc thử MỘT trang ``liveChatMessages.list`` — chỉ in SỐ LƯỢNG và LOẠI sự kiện,
   KHÔNG in nội dung tin nhắn, tên hay mã kênh của người xem (quy tắc PII);
5. ước lượng quota cho thời gian CHỜ LÊN SÓNG (bật bộ thu trước giờ phát, mặc định
   120 phút theo mốc T−2h) cộng buổi N phút, in RIÊNG hai giả định giá
   ``liveChatMessages.list``: 1 đơn vị (bảng Quota Calculator, cập nhật 2026-09-15) và
   5 đơn vị (quan sát cộng đồng 09/2026). Mọi cảnh báo dựa trên TRƯỜNG HỢP TỐN NHẤT —
   bộ thu đọc chat đúng sàn :data:`DEFAULT_POLL_FLOOR_MS`. ``pollingIntervalMillis`` đo
   ở mục 4 là nhịp của MỘT trang lúc thử (chat thường vắng); Google trả trường này ở mỗi
   trang và tài liệu không nói nó cố định, nên con số đó chỉ in để tham khảo;
6. KẾT LUẬN "SẴN SÀNG / CHƯA SẴN SÀNG" kèm cách sửa.

Mã thoát: 0 = SẴN SÀNG, 1 = CHƯA SẴN SÀNG.

An toàn khoá: bộ thu đặt khoá ở tham số ``key=`` của URL; bộ lọc log ``httpx`` trong
``livelift.ingest.base`` che giá trị đó. Script này không bao giờ in chuỗi ngoại lệ của
httpx (chuỗi đó chứa URL đầy đủ) — chỉ in tên loại lỗi — và che khoá lần cuối trước khi in.

Nguồn (truy cập 17/09/2026):
- https://developers.google.com/youtube/v3/docs/videos (cập nhật 2026-09-14)
- https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list (cập nhật 2026-09-14)
- https://developers.google.com/youtube/v3/determine_quota_cost (cập nhật 2026-09-15)
- https://developers.google.com/youtube/v3/docs/core_errors (cập nhật 2025-08-20)
- https://github.com/googleapis/googleapis/blob/master/google/api/error_reason.proto
- https://github.com/clear-bg/NSS-Result-Tracker/pull/420 (giá 5 đơn vị — cộng đồng, 09/09/2026)

Hướng dẫn lấy khoá: docs/HUONG-DAN-LAY-KHOA-API.md mục 2.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import math
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from livelift.api.ingest_jobs import WAIT_FOR_LIVE_S
from livelift.config import get_settings
from livelift.console import configure
from livelift.ingest.youtube import (
    DEFAULT_POLL_FLOOR_MS,
    YouTubeLiveChatClient,
    parse_live_chat_message,
)
from livelift.ingest.youtube_replay import _VIDEO_ID_RE, extract_video_id

NGAN = "-" * 66
DAM = "=" * 66

HAN_MUC_NGAY = 10_000
"""'10,000 units per day combined for all other endpoints' — Quota Calculator 2026-09-15."""
GIA_VIDEOS_LIST = 1
"""videos.list = 1 đơn vị — Quota Calculator 2026-09-15 và trang videos/list."""
GIA_LIST_THEO_BANG = 1
"""liveChatMessages.list = 1 đơn vị — Quota Calculator (cập nhật 2026-09-15)."""
GIA_LIST_THAN_TRONG = 5
"""5 đơn vị/lượt — tài liệu cũ và PR #420 (09/09/2026); CHƯA có trong tài liệu hiện hành."""

NHIP_NGUOI_XEM_S = float(
    inspect.signature(YouTubeLiveChatClient.iter_viewers).parameters["every_s"].default
)
"""Nhịp đọc người xem mặc định của bộ thu (runner và web đều không truyền every_s)."""

CHO_TRUOC_PHUT_MAC_DINH = 120
"""Quy trình bật bộ thu ở mốc T−2h (docs/mo-hinh-van-hanh-kol.md mục 5.2)."""
LUOT_VIDEOS_MOI_VONG_CHO = 2
"""Mỗi vòng ``cho_len_song`` của ``IngestManager`` chạy song song hai tác vụ: bình luận
(``get_active_live_chat_id``) và người xem (``iter_viewers``), mỗi tác vụ một lượt
``videos.list`` — khoá bằng test mô phỏng vòng chờ thật. Vòng lặp lại sau
:data:`livelift.api.ingest_jobs.WAIT_FOR_LIVE_S` giây."""
PR_420 = "https://github.com/clear-bg/NSS-Result-Tracker/pull/420"

ID_KIEM_KHOA = "LiveLiftChk"
"""Id 11 ký tự dùng khi không có ``--video``: chỉ để xem Google có nhận khoá không.
Video không tồn tại vẫn chứng minh được khoá hợp lệ (trả 200 rỗng hoặc 404 videoNotFound)."""

LOAI_DA_BIET: frozenset[str] = frozenset(
    {
        # enum snippet.type trong Discovery Document rev 20260914
        "textMessageEvent",
        "tombstone",
        "fanFundingEvent",
        "chatEndedEvent",
        "sponsorOnlyModeStartedEvent",
        "sponsorOnlyModeEndedEvent",
        "newSponsorEvent",
        "memberMilestoneChatEvent",
        "membershipGiftingEvent",
        "giftMembershipReceivedEvent",
        "messageDeletedEvent",
        "messageRetractedEvent",
        "userBannedEvent",
        "superChatEvent",
        "superStickerEvent",
        "pollEvent",
        "giftEvent",
        # trang HTML liệt kê poll dưới tên này
        "pollDetails",
    }
)

_TEN_AN_TOAN = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_LINK_BAT_API = re.compile(r"https://console\.(?:developers|cloud)\.google\.com/[^\s\"'<>]+")

TEN_TRANG_THAI = {
    "live": "ĐANG LIVE",
    "upcoming": "SẮP PHÁT (đã lên lịch, chưa bắt đầu)",
    "none": "KHÔNG live",
    "completed": "ĐÃ KẾT THÚC",
}
TEN_CHE_DO = {
    "public": "Công khai (public)",
    "unlisted": "Không công khai (unlisted)",
    "private": "Riêng tư (private)",
}


def _so(n: int) -> str:
    """1234567 -> '1.234.567' (dấu chấm ngăn nghìn kiểu Việt Nam)."""
    return f"{n:,}".replace(",", ".")


def _giay(ms: int) -> str:
    """2000 -> '2,0'."""
    return f"{ms / 1000:.1f}".replace(".", ",")


def _ten_an_toan(value: Any) -> str:
    """Tên enum do API trả (reason, type) — chỉ in nếu đúng dạng định danh."""
    s = str(value or "")
    return s if _TEN_AN_TOAN.match(s) else "(tên lạ)"


# --- phần thuần logic (test được, không cần mạng) ---------------------------


@dataclass(frozen=True)
class LoiYouTube:
    """Một lỗi đã phân loại: nhãn nội bộ + câu tiếng Việt + cách sửa."""

    nhan: str
    mo_ta: str
    cach_sua: str


def _than_loi(body: Any) -> dict[str, Any]:
    """Lấy ``error`` từ thân lỗi. Endpoint streaming bọc thân trong mảng JSON."""
    if isinstance(body, list) and body:
        body = body[0]
    if not isinstance(body, dict):
        return {}
    err = body.get("error")
    return err if isinstance(err, dict) else {}


def ly_do_loi(body: Any) -> tuple[list[str], list[str], str]:
    """(``details[].reason``, ``errors[].reason``, thông điệp) của một thân lỗi Google."""
    err = _than_loi(body)
    chi_tiet = [
        str(d["reason"])
        for d in err.get("details") or []
        if isinstance(d, dict) and d.get("reason")
    ]
    loi_con = [
        str(e["reason"]) for e in err.get("errors") or [] if isinstance(e, dict) and e.get("reason")
    ]
    return chi_tiet, loi_con, str(err.get("message") or "")


def _link_bat_api(body: Any) -> str:
    """Link bật API mà Google gửi kèm (metadata.activationUrl hoặc trong message)."""
    err = _than_loi(body)
    for d in err.get("details") or []:
        meta = d.get("metadata") if isinstance(d, dict) else None
        url = meta.get("activationUrl") if isinstance(meta, dict) else None
        if isinstance(url, str) and _LINK_BAT_API.fullmatch(url):
            return url
    m = _LINK_BAT_API.search(str(err.get("message") or ""))
    return m.group(0).rstrip(".,)") if m else ""


_KEY_BI_GIOI_HAN = {
    "API_KEY_SERVICE_BLOCKED": (
        "Google Cloud → APIs & Services → Credentials → bấm tên key → API restrictions: tick "
        "YouTube Data API v3 → Save, rồi chạy lại."
    ),
    "API_KEY_HTTP_REFERRER_BLOCKED": (
        "Credentials → bấm tên key → Application restrictions: chọn None khi chạy trên "
        "laptop (bộ thu chạy ở máy chủ, không gửi Referer của trình duyệt) → Save."
    ),
    "API_KEY_IP_ADDRESS_BLOCKED": (
        "Credentials → bấm tên key → Application restrictions → IP addresses: thêm đúng IP "
        "công khai của máy đang chạy lệnh, hoặc chọn None khi chạy trên laptop → Save."
    ),
    "API_KEY_ANDROID_APP_BLOCKED": (
        "Credentials → bấm tên key → Application restrictions: bỏ giới hạn ứng dụng Android "
        "(chọn None hoặc IP addresses) → Save."
    ),
    "API_KEY_IOS_APP_BLOCKED": (
        "Credentials → bấm tên key → Application restrictions: bỏ giới hạn ứng dụng iOS "
        "(chọn None hoặc IP addresses) → Save."
    ),
}

_SUA_KEY = (
    "Mở .env, chép lại YOUTUBE_API_KEY từ Google Cloud → APIs & Services → Credentials "
    "(đủ cả chuỗi, không dấu cách, không ngoặc kép), rồi chạy lại lệnh này. "
    "Xem docs/HUONG-DAN-LAY-KHOA-API.md mục 2.2."
)
_SUA_QUOTA = (
    "Chờ hạn mức đặt lại lúc 0h giờ Thái Bình Dương (14h giờ Việt Nam khi bên đó đang giờ mùa "
    "hè, 15h khi giờ mùa đông) hoặc dùng key của một dự án Google Cloud khác; xem mức đã dùng "
    "ở APIs & Services → YouTube Data API v3 → Quotas."
)


def phan_loai_loi(status: int | None, body: Any) -> LoiYouTube:
    """Phân loại một phản hồi lỗi của Google thành câu tiếng Việt có cách sửa.

    Thứ tự đọc: ``details[].reason`` (google.rpc.ErrorInfo) → ``errors[].reason`` →
    mã HTTP. Cùng là 403 nhưng ``quotaExceeded`` (chờ reset), ``liveChatEnded`` (dừng
    hẳn), ``accessNotConfigured`` (bật API) cần cách xử lý trái ngược nhau.
    """
    chi_tiet, loi_con, thong_diep = ly_do_loi(body)

    for r in chi_tiet:
        if r in ("API_KEY_INVALID", "CONSUMER_INVALID"):
            return LoiYouTube("KEY_SAI", f"Google báo API key không hợp lệ ({r}).", _SUA_KEY)
        if r == "SERVICE_DISABLED":
            return _chua_bat_api(r, body)
        if r in _KEY_BI_GIOI_HAN:
            return LoiYouTube(
                "KEY_BI_GIOI_HAN",
                f"Key đang bị giới hạn nên Google từ chối lệnh gọi ({r}).",
                _KEY_BI_GIOI_HAN[r],
            )
        if r == "RESOURCE_QUOTA_EXCEEDED":
            return LoiYouTube("HET_QUOTA", f"Dự án đã hết hạn mức quota ({r}).", _SUA_QUOTA)
        if r == "RATE_LIMIT_EXCEEDED":
            return _qua_nhanh(r)

    for r in loi_con:
        if r == "keyInvalid":
            return LoiYouTube("KEY_SAI", "Google báo API key không hợp lệ (keyInvalid).", _SUA_KEY)
        if r == "keyExpired":
            return LoiYouTube(
                "KEY_HET_HAN",
                "API key đã hết hạn (keyExpired).",
                "Google Cloud → APIs & Services → Credentials → Create credentials → API key; "
                "dán key mới vào YOUTUBE_API_KEY trong .env rồi chạy lại.",
            )
        if r == "accessNotConfigured":
            return _chua_bat_api(r, body)
        if r in ("quotaExceeded", "dailyLimitExceeded"):
            return LoiYouTube(
                "HET_QUOTA", f"Dự án đã hết hạn mức quota trong ngày ({r}).", _SUA_QUOTA
            )
        if r in ("rateLimitExceeded", "userRateLimitExceeded"):
            return _qua_nhanh(r)
        if r == "liveChatEnded":
            return LoiYouTube(
                "CHAT_DA_KET_THUC",
                "Chat của buổi live này đã đóng (liveChatEnded). Tài liệu: sau khi buổi live "
                "kết thúc, live chat không còn đọc được qua API.",
                "Dùng link của buổi ĐANG phát; muốn thử thì phát một buổi mới rồi chạy lại.",
            )
        if r == "liveChatDisabled":
            return LoiYouTube(
                "CHAT_BI_TAT",
                "Buổi live đang tắt trò chuyện trực tiếp (liveChatDisabled).",
                "YouTube Studio → mở buổi live → bật Trò chuyện trực tiếp (Live chat), "
                "rồi chạy lại.",
            )
        if r == "liveChatNotFound":
            return LoiYouTube(
                "KHONG_THAY_CHAT",
                "Google không tìm thấy phòng chat này (liveChatNotFound).",
                "Chạy lại lệnh khi video ĐANG live để lấy activeLiveChatId mới.",
            )
        if r == "videoNotFound":
            return LoiYouTube(
                "KHONG_THAY_VIDEO",
                "Google không tìm thấy video (videoNotFound).",
                "Kiểm tra lại link/id video (dạng youtube.com/watch?v=… hoặc youtube.com/live/…).",
            )
        if r == "backendError":
            return _loi_may_chu(status)
        if r == "forbidden":
            if "unregistered callers" in thong_diep:
                return LoiYouTube(
                    "THIEU_KEY",
                    "Lệnh gọi tới Google không mang API key (unregistered callers).",
                    "Điền YOUTUBE_API_KEY vào .env (docs/HUONG-DAN-LAY-KHOA-API.md mục 2).",
                )
            return LoiYouTube(
                "KHONG_CO_QUYEN",
                "Google từ chối quyền đọc (forbidden).",
                "Với chat: video có thể đang Riêng tư hoặc giới hạn cho hội viên — thử lại với "
                "một buổi live Công khai của kênh nhóm để đối chứng.",
            )

    if status == 429:
        return _qua_nhanh("HTTP 429")
    if status is not None and status >= 500:
        return _loi_may_chu(status)
    ly_do = next(iter(chi_tiet or loi_con), "")
    kem = f", {_ten_an_toan(ly_do)}" if ly_do else ""
    return LoiYouTube(
        "KHONG_RO",
        f"Google trả lỗi chưa phân loại (HTTP {status}{kem}).",
        "Chạy lại; nếu vẫn lỗi, tra lý do tại https://developers.google.com/youtube/v3/docs/"
        "core_errors và báo nhóm kỹ thuật.",
    )


def _chua_bat_api(ly_do: str, body: Any) -> LoiYouTube:
    link = _link_bat_api(body)
    them = f" Link Google gửi kèm: {link}" if link else ""
    return LoiYouTube(
        "CHUA_BAT_API",
        f"Dự án Google Cloud của key chưa bật YouTube Data API v3 ({ly_do}).",
        "Google Cloud → APIs & Services → Library → tìm YouTube Data API v3 → Enable, rồi chạy "
        f"lại lệnh này.{them}",
    )


def _qua_nhanh(ly_do: str) -> LoiYouTube:
    return LoiYouTube(
        "QUA_NHANH",
        f"Google báo gọi quá dày ({ly_do}). Khoá vẫn dùng được.",
        "Không chạy nhiều bộ thu hay nhiều lệnh kiểm tra cùng lúc trên một key; chờ 1 phút rồi "
        "chạy lại.",
    )


def _loi_may_chu(status: int | None) -> LoiYouTube:
    return LoiYouTube(
        "LOI_MAY_CHU",
        f"Google trả lỗi phía máy chủ (HTTP {status}).",
        "Lỗi tạm thời phía Google — chạy lại sau ít phút.",
    )


def dang_truong_qua(snippet: Mapping[str, Any]) -> str | None:
    """Dạng trường quà Jewels thật sự gặp — ba nguồn chính thức của Google mâu thuẫn."""
    if isinstance(snippet.get("giftDetails"), dict):
        return "snippet.giftDetails (khớp Discovery/proto)"
    ged = snippet.get("giftEventDetails")
    if isinstance(ged, dict):
        if isinstance(ged.get("giftMetadata"), dict):
            return "snippet.giftEventDetails.giftMetadata (khớp trang tài liệu HTML)"
        return "snippet.giftEventDetails không có giftMetadata (không khớp nguồn nào)"
    return None


@dataclass(frozen=True)
class UocLuongQuota:
    """Quota ước lượng. Các trường không hậu tố ``_do`` là TRƯỜNG HỢP TỐN NHẤT (chờ lên
    sóng + buổi, đọc chat đúng sàn của bộ thu) — mọi cảnh báo dựa trên chúng."""

    thoi_luong_phut: int
    cho_truoc_phut: int
    """Số phút bộ thu chạy ở trạng thái ``cho_len_song`` trước giờ phát."""
    polling_ms: int | None
    """``pollingIntervalMillis`` của MỘT trang đo ở mục 4; None = chưa đo."""
    san_poll_ms: int
    """Nhịp nhanh nhất bộ thu có thể đọc chat = sàn cố định của bộ thu."""
    luot_videos_cho: int
    """``videos.list`` lúc chờ lên sóng (tối đa LUOT_VIDEOS_MOI_VONG_CHO lượt mỗi vòng)."""
    luot_list: int
    """``liveChatMessages.list`` trong buổi, đọc đúng sàn."""
    luot_videos: int
    """``videos.list`` trong buổi: 1 lượt lấy chat id + người xem mỗi NHIP_NGUOI_XEM_S."""
    dv_theo_bang: int
    dv_than_trong: int
    ngan_sach_phan_tram: int
    ngan_sach_dv: int
    nhip_toi_thieu_than_trong_s: int | None
    """Nhịp poll tối thiểu để giả định 5 đơn vị/lượt vẫn vừa ngân sách (đã trừ lượt chờ)."""
    nhip_do_ms: int | None = None
    """max(pollingIntervalMillis đo được, sàn) — CHỈ tham khảo; None = chưa đo."""
    luot_list_do: int | None = None
    dv_theo_bang_do: int | None = None
    dv_than_trong_do: int | None = None

    @property
    def phan_tram_theo_bang(self) -> float:
        return 100.0 * self.dv_theo_bang / HAN_MUC_NGAY

    @property
    def phan_tram_than_trong(self) -> float:
        return 100.0 * self.dv_than_trong / HAN_MUC_NGAY


def uoc_luong_quota(
    thoi_luong_phut: int,
    polling_ms: int | None,
    ngan_sach_phan_tram: int = 30,
    *,
    cho_truoc_phut: int = CHO_TRUOC_PHUT_MAC_DINH,
    san_poll_ms: int = DEFAULT_POLL_FLOOR_MS,
    nhip_nguoi_xem_s: float = NHIP_NGUOI_XEM_S,
    nhip_cho_len_song_s: float = WAIT_FOR_LIVE_S,
) -> UocLuongQuota:
    """Quota của chờ lên sóng ``cho_truoc_phut`` + buổi ``thoi_luong_phut`` phút.

    Trường hợp tốn nhất (dùng để cảnh báo):

    - chờ lên sóng: ``IngestManager`` dò lại mỗi ``WAIT_FOR_LIVE_S`` giây, mỗi vòng tối đa
      :data:`LUOT_VIDEOS_MOI_VONG_CHO` lượt ``videos.list`` (bỏ qua độ trễ mạng nên là
      cận trên);
    - trong buổi: ``iter_comments`` ngủ ``max(pollingIntervalMillis, sàn)`` giữa hai lượt
      ``liveChatMessages.list`` — nhanh nhất là đúng sàn, dù Google trả nhịp nhỏ hơn;
      ``iter_viewers`` gọi ``videos.list`` mỗi :data:`NHIP_NGUOI_XEM_S` giây; cộng 1 lượt
      ``videos.list`` lúc lấy chat id.

    ``polling_ms`` đo được chỉ sinh thêm các trường ``*_do`` để tham khảo: nhịp của một
    trang lúc thử không đại diện cho buổi đông người.
    """
    giay = thoi_luong_phut * 60
    san = int(san_poll_ms)
    luot_videos_cho = (
        math.ceil(cho_truoc_phut * 60 / nhip_cho_len_song_s) * LUOT_VIDEOS_MOI_VONG_CHO
        if cho_truoc_phut > 0
        else 0
    )
    luot_list = math.ceil(giay * 1000 / san)
    luot_videos = 1 + math.ceil(giay / nhip_nguoi_xem_s)
    dv_videos = (luot_videos_cho + luot_videos) * GIA_VIDEOS_LIST
    ngan_sach = HAN_MUC_NGAY * ngan_sach_phan_tram // 100
    con_lai = ngan_sach - dv_videos
    toi_thieu = math.ceil(giay * GIA_LIST_THAN_TRONG / con_lai) if con_lai > 0 else None

    nhip_do = luot_list_do = dv_bang_do = dv_than_trong_do = None
    if polling_ms is not None:
        nhip_do = max(int(polling_ms), san)
        luot_list_do = math.ceil(giay * 1000 / nhip_do)
        dv_bang_do = luot_list_do * GIA_LIST_THEO_BANG + dv_videos
        dv_than_trong_do = luot_list_do * GIA_LIST_THAN_TRONG + dv_videos
    return UocLuongQuota(
        thoi_luong_phut=thoi_luong_phut,
        cho_truoc_phut=cho_truoc_phut,
        polling_ms=polling_ms,
        san_poll_ms=san,
        luot_videos_cho=luot_videos_cho,
        luot_list=luot_list,
        luot_videos=luot_videos,
        dv_theo_bang=luot_list * GIA_LIST_THEO_BANG + dv_videos,
        dv_than_trong=luot_list * GIA_LIST_THAN_TRONG + dv_videos,
        ngan_sach_phan_tram=ngan_sach_phan_tram,
        ngan_sach_dv=ngan_sach,
        nhip_toi_thieu_than_trong_s=toi_thieu,
        nhip_do_ms=nhip_do,
        luot_list_do=luot_list_do,
        dv_theo_bang_do=dv_bang_do,
        dv_than_trong_do=dv_than_trong_do,
    )


def chuan_hoa_video(value: str) -> str | None:
    """Id 11 ký tự từ id hoặc link (watch?v=, youtu.be/, /live/, /shorts/, /embed/)."""
    s = (value or "").strip()
    if _VIDEO_ID_RE.match(s):
        return s
    return extract_video_id(s)


def _gio(value: Any) -> str:
    try:
        ts = datetime.fromisoformat(str(value)).astimezone(UTC)
    except ValueError:
        return "không đọc được"
    return f"{ts:%d/%m/%Y %H:%M} UTC"


@dataclass
class KetQua:
    """Báo cáo tích lũy: các dòng để in + lý do chặn (kèm cách sửa) + cảnh báo."""

    dong: list[str] = field(default_factory=list)
    ly_do_chan: list[tuple[str, str]] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    so_luot_videos: int = 0
    """Số lượt videos.list chính lần kiểm tra này đã gọi (1 đơn vị/lượt, kể cả lượt lỗi)."""
    so_luot_chat: int = 0
    """Số lượt liveChatMessages.list đã gọi (1 hay 5 đơn vị/lượt — chưa chốt)."""
    chat_id_truoc_gio: bool | None = None
    """Video Sắp phát có activeLiveChatId không: True = có (trái tài liệu videos), False =
    không (khớp tài liệu), None = chưa đo (không có ``--video`` của buổi Sắp phát)."""

    @property
    def san_sang(self) -> bool:
        return not self.ly_do_chan

    def ghi(self, text: str = "") -> None:
        self.dong.append(text)

    def chan(self, ly_do: str, cach_sua: str) -> None:
        self.ly_do_chan.append((ly_do, cach_sua))

    def canh(self, text: str) -> None:
        self.canh_bao.append(text)

    def chan_loi(self, loi: LoiYouTube, truoc: str = "") -> None:
        self.chan(f"{truoc}{loi.mo_ta}", loi.cach_sua)

    def van_ban(self, api_key: str = "") -> str:
        khoi = list(self.dong)
        khoi.append(NGAN)
        khoi.append("KẾT LUẬN: " + ("SẴN SÀNG" if self.san_sang else "CHƯA SẴN SÀNG"))
        for ly_do, cach_sua in self.ly_do_chan:
            khoi.append(f"  [CHẶN]     {ly_do}")
            khoi.append(f"             Cách sửa: {cach_sua}")
        for canh in self.canh_bao:
            khoi.append(f"  [CẢNH BÁO] {canh}")
        khoi.append(f"  Mã thoát: {0 if self.san_sang else 1}")
        khoi.append(DAM)
        text = "\n".join(khoi)
        # Lớp phòng thủ cuối: không dòng nào được mang khoá, dù lỗi ở đâu phía trên.
        if len(api_key) >= 8:
            text = text.replace(api_key, "***")
        return text


# --- phần gọi mạng (qua client của bộ thu) ----------------------------------


async def _goi(
    client: YouTubeLiveChatClient, kq: KetQua, path: str, params: dict[str, str]
) -> tuple[dict[str, Any] | None, LoiYouTube | None, int | None]:
    """Gọi đúng hàm ``_get`` của bộ thu. Trả (dữ liệu, lỗi đã phân loại, mã HTTP).

    Không bao giờ để chuỗi ngoại lệ httpx lọt ra: nó chứa URL đầy đủ có ``key=``.
    """
    if path == "/videos":
        kq.so_luot_videos += 1
    else:
        kq.so_luot_chat += 1
    try:
        data = await client._get(path, params)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        try:
            body: Any = exc.response.json()
        except ValueError:
            body = None
        return None, phan_loai_loi(status, body), status
    except httpx.HTTPError as exc:
        return (
            None,
            LoiYouTube(
                "LOI_MANG",
                f"Không gọi được Google ({type(exc).__name__}).",
                "Kiểm tra kết nối Internet, proxy hoặc tường lửa rồi chạy lại.",
            ),
            None,
        )
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return (
            None,
            LoiYouTube(
                "PHAN_HOI_HONG",
                "Google trả phản hồi không đọc được (không phải JSON).",
                "Chạy lại; nếu mạng có trang đăng nhập Wi-Fi hoặc proxy chặn, xử lý trước.",
            ),
            200,
        )
    return data, None, 200


def _muc_1_khoa(kq: KetQua, api_key: str) -> bool:
    kq.ghi("1) API KEY")
    if not api_key.strip():
        kq.ghi("   YOUTUBE_API_KEY : TRỐNG trong .env")
        kq.chan(
            "Chưa có YOUTUBE_API_KEY.",
            "Làm theo docs/HUONG-DAN-LAY-KHOA-API.md mục 2.2–2.3 (khoảng 10 phút), điền khoá "
            "vào .env rồi chạy lại lệnh này.",
        )
        return False
    kq.ghi(f"   YOUTUBE_API_KEY : {len(api_key)} ký tự (không in ra khoá)")
    if api_key != api_key.strip() or any(c.isspace() or c in "\"'" for c in api_key.strip()):
        kq.canh(
            "YOUTUBE_API_KEY có dấu cách, xuống dòng hoặc ngoặc kép — xoá chúng trong .env "
            "(Google sẽ báo key không hợp lệ)."
        )
    elif not api_key.startswith("AIza"):
        kq.canh(
            "YOUTUBE_API_KEY không bắt đầu bằng 'AIza' như chuỗi API key ở hướng dẫn mục 2.2 "
            "bước 4 — kiểm tra đã chép đúng API key (không phải Client ID hay mã khác)."
        )
    return True


async def _muc_2_3_video(
    client: YouTubeLiveChatClient, kq: KetQua, video_id: str
) -> tuple[str, str]:
    """Mục 2 (khoá + API) và mục 3 (video) dùng CHUNG một lệnh videos.list (1 đơn vị).

    Trả (activeLiveChatId hoặc "", privacyStatus hoặc "").
    """
    kq.ghi()
    kq.ghi("2) KHOÁ HỢP LỆ VÀ API ĐÃ BẬT")
    co_video = bool(video_id)
    params = (
        {"part": "snippet,liveStreamingDetails,status", "id": video_id}
        if co_video
        else {"part": "id", "id": ID_KIEM_KHOA}
    )
    data, loi, status = await _goi(client, kq, "/videos", params)
    kq.ghi("   Lệnh gọi        : videos.list (1 đơn vị quota theo bảng chính thức)")
    if loi is not None and loi.nhan == "KHONG_THAY_VIDEO" and not co_video:
        # Id kiểm khoá không tồn tại là đúng dự kiến: lệnh đã qua bước xác thực khoá.
        loi = None
    if loi is not None:
        kq.ghi(f"   Kết quả         : THẤT BẠI — {loi.mo_ta}")
        kq.chan_loi(loi)
        if co_video:
            kq.ghi()
            kq.ghi("3) VIDEO VÀ TRẠNG THÁI LIVE")
            kq.ghi("   (bỏ qua — khoá/API chưa qua mục 2)")
        return "", ""
    kq.ghi(
        f"   Kết quả         : OK (HTTP {status}) — Google nhận khoá, YouTube Data API v3 đã bật"
    )

    kq.ghi()
    kq.ghi("3) VIDEO VÀ TRẠNG THÁI LIVE")
    if not co_video:
        kq.ghi("   (không truyền --video — bỏ qua mục 3 và 4)")
        kq.canh(
            "Chưa thử đọc chat. Khi phát thử, chạy lại với --video <link buổi đang live> để "
            "chứng minh đường dữ liệu (mục 3–4)."
        )
        return "", ""
    kq.ghi(f"   Video id        : {video_id}")
    items = [m for m in ((data or {}).get("items") or []) if isinstance(m, dict)]
    if not items:
        kq.ghi("   Tìm thấy        : KHÔNG (items rỗng)")
        kq.chan(
            f"videos.list không trả video {video_id}: id sai, video đã xoá, hoặc video không "
            "đọc được bằng API key (ví dụ đang để Riêng tư).",
            "Kiểm tra lại link; để buổi phát ở chế độ Công khai hoặc Không công khai rồi chạy lại.",
        )
        return "", ""
    item = items[0]
    raw_snippet, raw_status = item.get("snippet"), item.get("status")
    snippet: dict[str, Any] = raw_snippet if isinstance(raw_snippet, dict) else {}
    status_obj: dict[str, Any] = raw_status if isinstance(raw_status, dict) else {}
    chi_tiet = item.get("liveStreamingDetails")
    chi_tiet = chi_tiet if isinstance(chi_tiet, dict) else None
    trang_thai = str(snippet.get("liveBroadcastContent") or "")
    che_do = str(status_obj.get("privacyStatus") or "")

    kq.ghi(
        f"   Trạng thái      : {TEN_TRANG_THAI.get(trang_thai, _ten_an_toan(trang_thai))}"
        f" (liveBroadcastContent={_ten_an_toan(trang_thai) if trang_thai else 'không có'})"
    )
    kq.ghi(
        "   Chế độ hiển thị : "
        + (TEN_CHE_DO.get(che_do, _ten_an_toan(che_do)) if che_do else "Google không trả")
    )
    chat_id = ""
    if chi_tiet is not None:
        for khoa, nhan in (
            ("scheduledStartTime", "Lịch bắt đầu    "),
            ("actualStartTime", "Bắt đầu thật    "),
            ("actualEndTime", "Kết thúc lúc    "),
        ):
            if chi_tiet.get(khoa):
                kq.ghi(f"   {nhan}: {_gio(chi_tiet[khoa])}")
        chat_id = str(chi_tiet.get("activeLiveChatId") or "")
        kq.ghi(f"   activeLiveChatId: {'có' if chat_id else 'KHÔNG có'}")
        nguoi_xem = chi_tiet.get("concurrentViewers")
        if nguoi_xem is None:
            kq.ghi(
                "   Người xem đồng thời: không có trường (0 người xem, chủ kênh ẩn số, hoặc "
                "không đang live)"
            )
        else:
            try:
                kq.ghi(f"   Người xem đồng thời: {_so(int(str(nguoi_xem)))}")
            except ValueError:
                kq.ghi("   Người xem đồng thời: giá trị không đọc được")

    if chi_tiet is None:
        kq.chan(
            "Video này không phải buổi phát trực tiếp (không có liveStreamingDetails).",
            "Dán link của buổi live (YouTube Studio → Tạo → Phát trực tiếp), không phải video "
            "tải lên thường.",
        )
        return "", che_do
    if trang_thai == "live" and chat_id:
        return chat_id, che_do
    if trang_thai == "live":
        kq.chan(
            "Video đang live nhưng không có activeLiveChatId — trò chuyện trực tiếp đang tắt.",
            "YouTube Studio → mở buổi live → bật Trò chuyện trực tiếp (Live chat), rồi chạy lại.",
        )
        return "", che_do
    if trang_thai == "upcoming":
        kq.canh(
            "Video chưa bắt đầu phát. Tài liệu videos ghi activeLiveChatId 'is filled only if "
            "the video is a currently live broadcast' — chạy lại lệnh sau khi đã bấm phát để "
            "thử đọc chat."
        )
        kq.chat_id_truoc_gio = bool(chat_id)
        if chat_id:
            kq.ghi(
                "   ĐÃ ĐO           : video CHƯA phát nhưng Google đã trả activeLiveChatId "
                "(trái tài liệu videos) — ghi kết quả này vào nhật ký buổi thử."
            )
        return "", che_do
    if chi_tiet.get("actualEndTime") or trang_thai == "completed":
        kq.chan(
            "Buổi live này đã kết thúc. Tài liệu liveChatMessage: 'After the event ends, live "
            "chat is no longer available for that event.'",
            "Dán link của buổi ĐANG phát; muốn thử thì phát một buổi mới rồi chạy lại.",
        )
        return "", che_do
    kq.chan(
        "Video không ở trạng thái đang live.",
        "Bấm phát trên YouTube rồi chạy lại lệnh này.",
    )
    return "", che_do


async def _muc_4_chat(
    client: YouTubeLiveChatClient, kq: KetQua, chat_id: str, che_do: str
) -> int | None:
    """Đọc thử MỘT trang, đúng tham số của bộ thu. Chỉ đếm — KHÔNG in nội dung/tên."""
    kq.ghi()
    kq.ghi("4) ĐỌC THỬ MỘT TRANG CHAT (liveChatMessages.list)")
    if not chat_id:
        kq.ghi("   (bỏ qua — chưa có activeLiveChatId ở mục 3)")
        return None
    data, loi, _ = await _goi(
        client,
        kq,
        "/liveChat/messages",
        # Cùng tham số với YouTubeLiveChatClient.iter_comments: không xin authorDetails.
        {"liveChatId": chat_id, "part": "id,snippet", "maxResults": "500"},
    )
    if loi is not None or data is None:
        loi = loi or phan_loai_loi(None, None)
        kq.ghi(f"   Kết quả         : THẤT BẠI — {loi.mo_ta}")
        kq.chan_loi(loi, "Không đọc được chat: ")
        return None

    items = [m for m in (data.get("items") or []) if isinstance(m, dict)]
    theo_loai: Counter[str] = Counter()
    dang_qua: set[str] = set()
    la_binh_luan = 0
    parser_loi = 0
    for m in items:
        raw_snippet = m.get("snippet")
        snippet_m: dict[str, Any] = raw_snippet if isinstance(raw_snippet, dict) else {}
        theo_loai[_ten_an_toan(snippet_m.get("type"))] += 1
        dang = dang_truong_qua(snippet_m)
        if dang:
            dang_qua.add(dang)
        try:
            if parse_live_chat_message(m) is not None:
                la_binh_luan += 1
        except (TypeError, ValueError):
            parser_loi += 1

    kq.ghi("   Kết quả         : OK")
    kq.ghi(f"   Số mục trả về   : {len(items)} (không in nội dung, tên hay mã kênh — quy tắc PII)")
    if theo_loai:
        kq.ghi(
            "   Theo loại       : "
            + ", ".join(f"{ten}={so}" for ten, so in sorted(theo_loai.items()))
        )
    kq.ghi(
        f"   Bộ thu nhận là bình luận: {la_binh_luan} (chỉ textMessageEvent; sự kiện trả phí, "
        "hội viên, hệ thống bị bỏ có chủ đích)"
    )
    polling = data.get("pollingIntervalMillis")
    polling_ms: int | None
    try:
        polling_ms = int(polling) if polling is not None else None
    except (TypeError, ValueError):
        polling_ms = None
    kq.ghi(
        "   pollingIntervalMillis: "
        + (f"{_so(polling_ms)} ms" if polling_ms is not None else "Google không trả")
    )
    kq.ghi(f"   nextPageToken   : {'có' if data.get('nextPageToken') else 'KHÔNG có'}")
    kq.ghi(f"   offlineAt       : {'CÓ — luồng đã offline' if data.get('offlineAt') else 'không'}")
    kq.ghi(f"   activePollItem  : {'có' if data.get('activePollItem') else 'không'}")
    for dang in sorted(dang_qua):
        kq.ghi(f"   Dạng trường quà : {dang}")

    la = sorted(ten for ten in theo_loai if ten not in LOAI_DA_BIET)
    if la:
        kq.canh(
            "Gặp loại sự kiện chưa có trong tài liệu: "
            + ", ".join(la)
            + " — bộ thu bỏ qua; báo nhóm kỹ thuật để cập nhật."
        )
    if parser_loi:
        kq.chan(
            f"Parser của bộ thu ném lỗi ở {parser_loi} mục (dạng dữ liệu đã đổi).",
            "Sửa parse_live_chat_message trong src/livelift/ingest/youtube.py, thêm fixture vào "
            "tests/data/youtube/.",
        )
    elif theo_loai.get("textMessageEvent", 0) and la_binh_luan == 0:
        kq.chan(
            "Google trả tin nhắn văn bản nhưng parser của bộ thu đọc được 0.",
            "Lược đồ phản hồi đã đổi — sửa parse_live_chat_message trong "
            "src/livelift/ingest/youtube.py.",
        )
    if data.get("offlineAt"):
        kq.chan(
            "Luồng phát đã offline (offlineAt có mặt) — bộ thu DỪNG đọc chat khi thấy trường này.",
            "Kiểm tra phần mềm phát/webcam, phát lại rồi chạy lại lệnh này.",
        )
    if not items:
        kq.canh(
            "Đọc được nhưng trang này chưa có tin nhắn nào — gửi một bình luận thử vào buổi "
            "live rồi chạy lại để chứng minh đường dữ liệu."
        )
    if che_do == "unlisted" and not data.get("offlineAt"):
        kq.ghi(
            "   ĐÃ ĐO           : API key đọc được chat của video Không công khai — ghi kết quả "
            "này vào nhật ký buổi thử."
        )
    return polling_ms


def _pham_vi(uoc: UocLuongQuota) -> str:
    """'chờ lên sóng 120 phút + buổi 90 phút' hoặc 'buổi 90 phút'."""
    buoi = f"buổi {uoc.thoi_luong_phut} phút"
    return f"chờ lên sóng {uoc.cho_truoc_phut} phút + {buoi}" if uoc.cho_truoc_phut else buoi


def _muc_5_quota(kq: KetQua, uoc: UocLuongQuota) -> None:
    kq.ghi()
    kq.ghi(f"5) ƯỚC LƯỢNG QUOTA: {_pham_vi(uoc).upper()}")
    kq.ghi("   Trường hợp tốn nhất của bộ thu — mọi cảnh báo dưới đây dựa trên số này:")
    if uoc.cho_truoc_phut > 0:
        kq.ghi(
            f"   Chờ lên sóng    : {_so(uoc.luot_videos_cho)} lượt videos.list — bật bộ thu trước "
            f"giờ phát {uoc.cho_truoc_phut} phút (--cho-truoc-phut), dò lại mỗi "
            f"{WAIT_FOR_LIVE_S:.0f} s, tối đa {LUOT_VIDEOS_MOI_VONG_CHO} lượt mỗi vòng"
        )
    else:
        kq.ghi("   Chờ lên sóng    : 0 lượt (--cho-truoc-phut 0 — bật bộ thu đúng lúc phát)")
    kq.ghi(
        f"   Nhịp đọc chat   : {_giay(uoc.san_poll_ms)} s = sàn cố định của bộ thu (không đọc "
        "nhanh hơn, kể cả khi Google trả pollingIntervalMillis nhỏ hơn)"
    )
    kq.ghi(f"   liveChatMessages.list: {_so(uoc.luot_list)} lượt")
    kq.ghi(
        f"   videos.list trong buổi: {_so(uoc.luot_videos)} lượt (1 lượt lấy chat id + người xem "
        f"mỗi {NHIP_NGUOI_XEM_S:.0f} s), 1 đơn vị/lượt"
    )
    kq.ghi(
        f"   Giả định A — {GIA_LIST_THEO_BANG} đơn vị/lượt list (bảng Quota Calculator, cập nhật "
        f"15/09/2026): {_so(uoc.dv_theo_bang)} đơn vị = {uoc.phan_tram_theo_bang:.0f}% hạn mức "
        f"{_so(HAN_MUC_NGAY)}/ngày"
    )
    kq.ghi(
        f"   Giả định B — {GIA_LIST_THAN_TRONG} đơn vị/lượt list (tài liệu cũ và quan sát cộng "
        f"đồng 09/2026, chưa có trong tài liệu hiện hành): {_so(uoc.dv_than_trong)} đơn vị = "
        f"{uoc.phan_tram_than_trong:.0f}%"
    )
    if uoc.nhip_toi_thieu_than_trong_s is not None:
        kq.ghi(
            f"   Để giả định B vừa {uoc.ngan_sach_phan_tram}% hạn mức ({_so(uoc.ngan_sach_dv)} "
            f"đơn vị), nhịp poll cần ≥ {uoc.nhip_toi_thieu_than_trong_s} s (bộ thu hiện chưa có "
            "tuỳ chọn đổi sàn poll)"
        )
    if (
        uoc.polling_ms is None
        or uoc.nhip_do_ms is None
        or uoc.luot_list_do is None
        or uoc.dv_theo_bang_do is None
        or uoc.dv_than_trong_do is None
    ):
        kq.ghi("   Nhịp lúc thử    : CHƯA đo (cần --video buổi đang live)")
    else:
        kq.ghi(
            f"   Nhịp lúc thử    : pollingIntervalMillis {_so(uoc.polling_ms)} ms (mục 4) → đọc "
            f"mỗi {_giay(uoc.nhip_do_ms)} s: {_so(uoc.luot_list_do)} lượt list, A = "
            f"{_so(uoc.dv_theo_bang_do)} đơn vị, B = {_so(uoc.dv_than_trong_do)} đơn vị"
        )
        kq.ghi(
            "                     CHỈ tham khảo, KHÔNG dùng để yên tâm: đây là nhịp của một trang "
            "lúc thử, khi chat thường vắng. Google trả trường này ở mỗi trang và tài liệu không "
            "nói nó cố định; PR #420 tính ngược ra ≈1,41 s/lượt ở buổi thật của họ, nhanh hơn "
            f"sàn 2 s ({PR_420})."
        )
    if uoc.cho_truoc_phut > 0 and kq.chat_id_truoc_gio is False:
        kq.ghi(
            "   Đã đo           : video Sắp phát này chưa có activeLiveChatId (khớp tài liệu "
            "videos) — lúc chờ bộ thu chỉ dò videos.list như dòng Chờ lên sóng."
        )
    elif uoc.cho_truoc_phut > 0 and kq.chat_id_truoc_gio is None:
        kq.ghi(
            "   Chưa đo         : tài liệu videos nói activeLiveChatId chỉ có khi video đang live. "
            "Nếu YouTube cấp sớm cho buổi đã lên lịch, bộ thu đọc chat suốt lúc chờ, thêm tới "
            f"{_so(math.ceil(uoc.cho_truoc_phut * 60_000 / uoc.san_poll_ms))} lượt list — chạy "
            "lệnh này với --video khi buổi còn Sắp phát để kiểm."
        )
    kq.ghi(
        "   Ghi chú         : API không trả số quota còn lại — xem Google Cloud → APIs & "
        "Services → YouTube Data API v3 → Quotas; đặt lại lúc 0h giờ Thái Bình Dương. Chưa tính "
        "lượt gọi lại khi lỗi mạng hay khi bộ thu tự khởi động lại."
    )
    if kq.so_luot_videos or kq.so_luot_chat:
        thap = kq.so_luot_videos * GIA_VIDEOS_LIST + kq.so_luot_chat * GIA_LIST_THEO_BANG
        cao = kq.so_luot_videos * GIA_VIDEOS_LIST + kq.so_luot_chat * GIA_LIST_THAN_TRONG
        kq.ghi(
            f"   Lần kiểm tra này: {kq.so_luot_videos} videos.list + {kq.so_luot_chat} "
            f"liveChatMessages.list = {thap if thap == cao else f'{thap}–{cao}'} đơn vị"
        )
    else:
        kq.ghi("   Lần kiểm tra này: không gọi Google (0 đơn vị)")

    pham_vi = _pham_vi(uoc)
    cach_sua = (
        (
            "bật bộ thu gần giờ phát hơn (lệnh kiểm tra này đủ để kiểm khoá sớm), "
            if uoc.cho_truoc_phut
            else ""
        )
        + "rút ngắn buổi, dùng một dự án Google Cloud riêng cho buổi live, hoặc xin tăng hạn mức "
        "ở trang Quotas; sau buổi thử, đọc số thật ở Metrics để chốt giá 1 hay 5 đơn vị"
    )
    if kq.chat_id_truoc_gio is True and uoc.cho_truoc_phut > 0:
        them = math.ceil(uoc.cho_truoc_phut * 60_000 / uoc.san_poll_ms)
        kq.canh(
            "Video chưa phát đã có activeLiveChatId: bật bộ thu trước giờ phát "
            f"{uoc.cho_truoc_phut} phút thì bộ thu đọc chat suốt lúc chờ, thêm tới {_so(them)} "
            f"lượt liveChatMessages.list ({_so(them * GIA_LIST_THEO_BANG)}–"
            f"{_so(them * GIA_LIST_THAN_TRONG)} đơn vị) ngoài số ở mục 5. Cách sửa: bật bộ thu "
            "đúng lúc bắt đầu phát, hoặc chạy lại ước lượng với --cho-truoc-phut nhỏ hơn."
        )
    if uoc.dv_theo_bang > HAN_MUC_NGAY:
        kq.chan(
            f"Ngay cả theo bảng giá chính thức, trường hợp tốn nhất ({pham_vi}) cần "
            f"{_so(uoc.dv_theo_bang)} đơn vị — vượt hạn mức {_so(HAN_MUC_NGAY)}/ngày.",
            cach_sua[0].upper() + cach_sua[1:] + ".",
        )
        return
    if uoc.dv_theo_bang > uoc.ngan_sach_dv:
        kq.canh(
            f"Theo bảng giá chính thức, trường hợp tốn nhất ({pham_vi}) dùng "
            f"{uoc.phan_tram_theo_bang:.0f}% hạn mức ngày — quá ngưỡng "
            f"{uoc.ngan_sach_phan_tram}% của buổi thử. Cách sửa: {cach_sua}."
        )
    if uoc.dv_than_trong > HAN_MUC_NGAY:
        kq.canh(
            f"Nếu giá thật là {GIA_LIST_THAN_TRONG} đơn vị/lượt list, trường hợp tốn nhất "
            f"({pham_vi}, đọc chat mỗi {_giay(uoc.san_poll_ms)} s) cần "
            f"{_so(uoc.dv_than_trong)} đơn vị — VƯỢT hạn mức ngày, bộ thu sẽ gặp quotaExceeded "
            f"giữa buổi. Cách sửa: {cach_sua}."
        )


async def kiem_tra(
    *,
    api_key: str,
    video: str = "",
    thoi_luong_phut: int = 90,
    ngan_sach_phan_tram: int = 30,
    cho_truoc_phut: int = CHO_TRUOC_PHUT_MAC_DINH,
    http: httpx.AsyncClient | None = None,
    timeout_s: float = 20.0,
    bay_gio: datetime | None = None,
) -> KetQua:
    """Chạy toàn bộ phép kiểm tra và trả về báo cáo (không in ra màn hình)."""
    bay_gio = bay_gio or datetime.now(UTC)
    kq = KetQua()
    kq.ghi(DAM)
    kq.ghi(" KIỂM TRA ĐƯỜNG YOUTUBE LIVE (API chính thức) — LiveLift")
    kq.ghi(f" Thời điểm: {bay_gio:%d/%m/%Y %H:%M} UTC · YouTube Data API v3 · chỉ đọc")
    kq.ghi(DAM)
    kq.ghi()

    video_id = ""
    video_sai = False
    if video.strip():
        video_id = chuan_hoa_video(video) or ""
        video_sai = not video_id
        if video_sai:
            kq.ghi("0) THAM SỐ --video")
            kq.ghi("   Không nhận ra video YouTube từ giá trị đã truyền — không gọi Google.")
            kq.chan(
                "Không nhận ra video YouTube trong --video.",
                "Dán link dạng youtube.com/watch?v=…, youtu.be/… hoặc youtube.com/live/…, hoặc "
                "id 11 ký tự (link kênh không dùng được).",
            )
            kq.ghi()

    polling_ms: int | None = None
    if _muc_1_khoa(kq, api_key) and not video_sai:
        owns = http is None
        http_client = http or httpx.AsyncClient(timeout=timeout_s)
        client = YouTubeLiveChatClient(api_key=api_key, client=http_client)
        try:
            chat_id, che_do = await _muc_2_3_video(client, kq, video_id)
            if video_id:
                polling_ms = await _muc_4_chat(client, kq, chat_id, che_do)
        finally:
            if owns:
                await http_client.aclose()
    _muc_5_quota(
        kq,
        uoc_luong_quota(
            thoi_luong_phut, polling_ms, ngan_sach_phan_tram, cho_truoc_phut=cho_truoc_phut
        ),
    )
    return kq


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/kiem_tra_youtube.py",
        description=(
            "Kiểm tra API key YouTube và đường đọc chat live trước phiên thật (chỉ đọc, "
            "không in khoá, không in nội dung bình luận)."
        ),
    )
    parser.add_argument(
        "--video",
        default="",
        help="link hoặc id 11 ký tự của buổi ĐANG live để thử đọc chat (tùy chọn)",
    )
    parser.add_argument(
        "--thoi-luong-phut",
        type=int,
        default=90,
        help="thời lượng buổi live dùng để ước lượng quota (mặc định 90)",
    )
    parser.add_argument(
        "--cho-truoc-phut",
        type=int,
        default=CHO_TRUOC_PHUT_MAC_DINH,
        help=(
            "số phút bật bộ thu TRƯỚC giờ phát (trạng thái Chờ buổi live bắt đầu) — vẫn tốn "
            f"quota; mặc định {CHO_TRUOC_PHUT_MAC_DINH} theo mốc T−2h, 0 = bật đúng lúc phát"
        ),
    )
    parser.add_argument(
        "--ngan-sach-phan-tram",
        type=int,
        default=30,
        help="ngưỡng %% hạn mức ngày cho một buổi (mặc định 30)",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="giây cho mỗi lệnh gọi")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    settings: Any = None,
    http: httpx.AsyncClient | None = None,
) -> int:
    """``settings``/``http`` chỉ để test tiêm vào (không mạng, không đọc .env thật)."""
    # Sự cố 27/08 (sổ sự cố): console Windows mặc định cp1252 làm chết báo cáo tiếng
    # Việt. Gọi TRƯỚC parse_args, đúng quy ước của scripts/chay_local.py.
    configure()
    args = build_parser().parse_args(argv)
    if (
        args.thoi_luong_phut <= 0
        or args.cho_truoc_phut < 0
        or not 0 < args.ngan_sach_phan_tram <= 100
    ):
        print(
            "--thoi-luong-phut phải > 0, --cho-truoc-phut phải ≥ 0 và --ngan-sach-phan-tram "
            "trong khoảng 1–100."
        )
        return 1
    s = settings if settings is not None else get_settings()
    api_key = str(getattr(s, "youtube_api_key", "") or "")
    kq = asyncio.run(
        kiem_tra(
            api_key=api_key,
            video=args.video,
            thoi_luong_phut=args.thoi_luong_phut,
            ngan_sach_phan_tram=args.ngan_sach_phan_tram,
            cho_truoc_phut=args.cho_truoc_phut,
            http=http,
            timeout_s=args.timeout,
        )
    )
    print(kq.van_ban(api_key))
    return 0 if kq.san_sang else 1


if __name__ == "__main__":
    raise SystemExit(main())
