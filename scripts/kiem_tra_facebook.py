#!/usr/bin/env python3
"""Kiểm tra token Facebook: đường ingest Facebook Live đã SẴN SÀNG chưa?

Chạy (từ thư mục gốc repo, sau khi đã dán token vào .env):

    .venv/Scripts/python scripts/kiem_tra_facebook.py          # Windows
    python scripts/kiem_tra_facebook.py                        # macOS/Linux

Script CHỈ ĐỌC — không đăng, không sửa, không xóa gì trên Facebook. Nó gọi
đúng những endpoint mà runner ingest sẽ gọi trong phiên thật, rồi in bảng
tiếng Việt: token còn hạn bao lâu, có đủ quyền gì, đọc được Page nào, có buổi
live nào đang phát không, và KẾT LUẬN "SẴN SÀNG / CHƯA SẴN SÀNG" kèm cách sửa.

Mã thoát: 0 = SẴN SÀNG, 1 = CHƯA SẴN SÀNG (dùng được trong CI/checklist).

Vì sao đọc bình luận là phép thử quyết định: quyền ``pages_read_engagement``
chỉ cho đọc nội dung do Page tự đăng; bình luận là nội dung của NGƯỜI XEM nên
cần ``pages_read_user_content``. Rất nhiều nhóm chỉ phát hiện ra điều này khi
phiên live đã bắt đầu — script gọi thẳng ``/{live-video-id}/comments`` với
đúng bộ tham số của runner để lỗi (nếu có) nổ ra từ hôm nay.

Hướng dẫn lấy token từng bước: docs/huong-dan-facebook-token.md
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from livelift.config import get_settings
from livelift.ingest.facebook import (
    GRAPH_BASE,
    TOKEN_SUBCODE_HINTS,
    comment_params,
    usage_percent,
)

# Quyền tối thiểu để đọc một phiên live của Page mình. Thiếu bất kỳ dòng nào ở
# đây là CHẶN — không phải cảnh báo.
QUYEN_BAT_BUOC: dict[str, str] = {
    "pages_read_engagement": "đọc video live + số người xem của Page",
    "pages_read_user_content": "đọc BÌNH LUẬN của người xem (biến kết quả chính)",
}
# Không bắt buộc lúc chạy, nhưng thiếu thì lần đổi token sau sẽ vướng.
QUYEN_NEN_CO: dict[str, str] = {
    "pages_show_list": "liệt kê Page mình quản trị (cần khi đổi/gia hạn token)",
}

NGAN = "-" * 66
DAM = "=" * 66


# --- phần thuần logic (test được, không cần mạng) ---------------------------


@dataclass(frozen=True)
class ThongTinToken:
    """Kết quả đọc ``/debug_token`` — chỉ dữ liệu, không in ấn."""

    hop_le: bool
    loai: str  # PAGE | USER | APP | "" (không đọc được)
    het_han_luc: datetime | None  # None = không có hạn
    het_quyen_luc: datetime | None  # data_access_expires_at
    scopes: tuple[str, ...]
    profile_id: str  # Page id (với token PAGE)
    app_id: str
    loi: str


def _thoi_diem(value: Any) -> datetime | None:
    """Unix seconds -> datetime UTC. 0 hoặc thiếu = không hết hạn."""
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return datetime.fromtimestamp(int(value), tz=UTC)


def doc_debug_token(payload: Mapping[str, Any]) -> ThongTinToken:
    """Bóc ``/debug_token``. ``granular_scopes`` (quyền cấp theo từng Page) được
    gộp vào ``scopes`` vì Facebook trả quyền ở một trong hai chỗ tùy loại app."""
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    scopes: list[str] = [str(s) for s in (data.get("scopes") or [])]
    for muc in data.get("granular_scopes") or []:
        if isinstance(muc, dict) and muc.get("scope") and str(muc["scope"]) not in scopes:
            scopes.append(str(muc["scope"]))
    loi = data.get("error") or {}
    return ThongTinToken(
        hop_le=bool(data.get("is_valid")),
        loai=str(data.get("type") or "").upper(),
        het_han_luc=_thoi_diem(data.get("expires_at")),
        het_quyen_luc=_thoi_diem(data.get("data_access_expires_at")),
        scopes=tuple(scopes),
        profile_id=str(data.get("profile_id") or ""),
        app_id=str(data.get("app_id") or ""),
        loi=str(loi.get("message") or "") if isinstance(loi, dict) else "",
    )


def mo_ta_han(luc: datetime | None, bay_gio: datetime) -> str:
    """Chuỗi tiếng Việt cho một mốc hết hạn (dùng cho cả token và data access)."""
    if luc is None:
        return "KHÔNG hết hạn (token dài hạn)"
    ngay = (luc - bay_gio).total_seconds() / 86400.0
    moc = f"{luc:%d/%m/%Y %H:%M} UTC"
    if ngay < 0:
        return f"ĐÃ HẾT HẠN {abs(ngay):.0f} ngày trước ({moc})"
    if ngay < 1:
        return f"CÒN DƯỚI 1 NGÀY ({moc}) — gia hạn ngay"
    if ngay < 7:
        return f"chỉ còn {ngay:.0f} ngày ({moc}) — nên gia hạn trước phiên"
    return f"còn {ngay:.0f} ngày ({moc})"


def thieu_quyen(scopes: tuple[str, ...] | list[str]) -> list[str]:
    """Các quyền BẮT BUỘC còn thiếu, theo thứ tự khai báo."""
    co = set(scopes)
    return [ten for ten in QUYEN_BAT_BUOC if ten not in co]


def mo_ta_loi_graph(status: int, err: Mapping[str, Any]) -> str:
    """Lỗi Graph -> một dòng tiếng Việt có mã lỗi và gợi ý nguyên nhân."""
    code = err.get("code")
    subcode = err.get("error_subcode")
    goi_y = TOKEN_SUBCODE_HINTS.get(subcode) if isinstance(subcode, int) else None
    phan = [f"HTTP {status}"]
    if code is not None:
        phan.append(f"code {code}")
    if goi_y:
        phan.append(goi_y)
    thong_diep = str(err.get("message") or "").strip().rstrip(".")
    dau = " · ".join(phan)
    return f"{dau} — {thong_diep}" if thong_diep else dau


@dataclass
class KetQua:
    """Báo cáo tích lũy: các dòng để in + lý do chặn + cảnh báo."""

    dong: list[str] = field(default_factory=list)
    ly_do_chan: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)

    @property
    def san_sang(self) -> bool:
        return not self.ly_do_chan

    def ghi(self, text: str = "") -> None:
        self.dong.append(text)

    def chan(self, ly_do: str) -> None:
        self.ly_do_chan.append(ly_do)

    def canh(self, text: str) -> None:
        self.canh_bao.append(text)

    def van_ban(self) -> str:
        khoi = list(self.dong)
        khoi.append(NGAN)
        khoi.append("KẾT LUẬN: " + ("SẴN SÀNG" if self.san_sang else "CHƯA SẴN SÀNG"))
        for ly_do in self.ly_do_chan:
            khoi.append(f"  [CHẶN]     {ly_do}")
        for canh in self.canh_bao:
            khoi.append(f"  [CẢNH BÁO] {canh}")
        if self.san_sang and not self.canh_bao:
            khoi.append("  Đường Facebook Live chạy được ngay: dùng live-video id ở mục 4")
            khoi.append("  cho `python -m livelift.ingest.runner --platform facebook`.")
        khoi.append(DAM)
        return "\n".join(khoi)


# --- phần gọi mạng ----------------------------------------------------------


class _Graph:
    """Bọc httpx.Client: token đi ở header, luôn trả (dữ liệu, lỗi)."""

    def __init__(self, client: httpx.Client, base: str, token: str) -> None:
        self._client = client
        self._base = base
        self._token = token
        #: % hạn mức cao nhất Facebook báo lại qua header X-App-Usage/X-Page-Usage.
        self.usage_pct: float | None = None

    def get(self, path: str, params: dict[str, str] | None = None) -> tuple[dict[str, Any], str]:
        try:
            resp = self._client.get(
                self._base + path,
                params=params or {},
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            return {}, f"không gọi được Facebook ({type(exc).__name__}) — kiểm tra mạng"
        pct = usage_percent(resp.headers)
        if pct is not None:
            self.usage_pct = pct if self.usage_pct is None else max(self.usage_pct, pct)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        if resp.status_code >= 400:
            err = body.get("error") or {}
            return {}, mo_ta_loi_graph(resp.status_code, err if isinstance(err, dict) else {})
        return body, ""


def _muc_1_token(
    graph: _Graph, kq: KetQua, token: str, app_token: str, bay_gio: datetime
) -> tuple[ThongTinToken | None, str]:
    """Mục 1: /debug_token. Trả (thông tin, lỗi) — thiếu app secret thì bỏ qua."""
    kq.ghi("1) TOKEN")
    kq.ghi(f"   Độ dài token   : {len(token)} ký tự (không in ra token)")
    payload, loi = graph.get("/debug_token", {"input_token": token, "access_token": app_token})
    if loi:
        kq.ghi(f"   /debug_token   : KHÔNG đọc được — {loi}")
        kq.canh(
            "Không đọc được hạn/quyền của token (thiếu FACEBOOK_APP_ID + FACEBOOK_APP_SECRET "
            "trong .env, hoặc token không thuộc app này). Các phép thử đọc thật bên dưới vẫn "
            "có giá trị, nhưng sẽ không biết trước ngày token hết hạn."
        )
        return None, loi
    info = doc_debug_token(payload)
    kq.ghi(f"   Trạng thái     : {'HỢP LỆ' if info.hop_le else 'KHÔNG HỢP LỆ'}")
    kq.ghi(f"   Loại token     : {info.loai or 'không rõ'}")
    kq.ghi(f"   App id         : {info.app_id or 'không rõ'}")
    kq.ghi(f"   Hạn token      : {mo_ta_han(info.het_han_luc, bay_gio)}")
    kq.ghi(f"   Hạn truy cập DL: {mo_ta_han(info.het_quyen_luc, bay_gio)}")
    if not info.hop_le:
        kq.chan(
            "Token KHÔNG hợp lệ"
            + (f" ({info.loi})" if info.loi else "")
            + " — lấy token mới theo docs/huong-dan-facebook-token.md mục 5."
        )
    if info.loai == "USER":
        kq.chan(
            "Đây là USER token, không phải PAGE token. Gọi /me/accounts bằng token này để "
            "lấy 'access_token' của Page rồi dán vào FACEBOOK_PAGE_ACCESS_TOKEN "
            "(docs/huong-dan-facebook-token.md mục 6)."
        )
    if info.het_han_luc is not None:
        kq.canh(
            "Token có ngày hết hạn — đổi sang Page token dài hạn (mục 5-6 trong hướng dẫn) "
            "để không chết giữa phiên."
        )
    if info.het_quyen_luc is not None:
        kq.canh(
            "Facebook khóa truy cập dữ liệu sau ~90 ngày không dùng (data access expiration): "
            f"{mo_ta_han(info.het_quyen_luc, bay_gio)} — cấp lại quyền trước ngày này."
        )
    return info, ""


def _muc_2_quyen(kq: KetQua, info: ThongTinToken | None) -> None:
    """Mục 2: quyền. Không có debug_token thì để phép thử đọc thật kết luận."""
    kq.ghi()
    kq.ghi("2) QUYỀN")
    if info is None or not info.scopes:
        kq.ghi("   (không đọc được danh sách quyền — xem kết quả đọc thử ở mục 4)")
        return
    co = set(info.scopes)
    for ten, y_nghia in {**QUYEN_BAT_BUOC, **QUYEN_NEN_CO}.items():
        dau = "x" if ten in co else " "
        bat_buoc = "BẮT BUỘC" if ten in QUYEN_BAT_BUOC else "nên có"
        kq.ghi(f"   [{dau}] {ten:<26} {bat_buoc} — {y_nghia}")
    for ten in thieu_quyen(info.scopes):
        kq.chan(
            f"Thiếu quyền {ten} ({QUYEN_BAT_BUOC[ten]}). Cấp lại token có quyền này "
            "(docs/huong-dan-facebook-token.md mục 4)."
        )
    for ten in QUYEN_NEN_CO:
        if ten not in co:
            kq.canh(f"Thiếu quyền {ten} — {QUYEN_NEN_CO[ten]}.")


def _muc_3_page(graph: _Graph, kq: KetQua, page_id_env: str) -> str:
    """Mục 3: /me -> Page nào đọc được. Trả page id dùng cho mục 4."""
    kq.ghi()
    kq.ghi("3) PAGE ĐỌC ĐƯỢC")
    data, loi = graph.get("/me", {"fields": "id,name,category"})
    if loi:
        kq.ghi(f"   /me            : KHÔNG đọc được — {loi}")
        kq.chan(
            f"Token không đọc nổi chính nó — /me lỗi: {loi}. Token sai hoặc đã bị thu hồi: "
            "lấy token mới theo docs/huong-dan-facebook-token.md (bước 4 → 6)."
        )
        return page_id_env
    ten = str(data.get("name") or "")
    page_id = str(data.get("id") or "")
    kq.ghi(f"   Tên            : {ten or 'không rõ'}")
    kq.ghi(f"   Id             : {page_id or 'không rõ'}")
    if data.get("category"):
        kq.ghi(f"   Hạng mục       : {data['category']}")
    if page_id_env and page_id and page_id_env != page_id:
        kq.canh(
            f"FACEBOOK_PAGE_ID trong .env ({page_id_env}) KHÁC Page của token ({page_id}). "
            "Sửa .env cho khớp, nếu không runner sẽ tìm live video ở Page khác."
        )
    if not page_id_env and page_id:
        kq.canh(f"FACEBOOK_PAGE_ID đang trống — điền {page_id} vào .env cho tiện.")
    return page_id or page_id_env


def _muc_4_live(graph: _Graph, kq: KetQua, page_id: str, live_video_id: str) -> None:
    """Mục 4: tìm buổi live + ĐỌC THỬ bình luận (phép thử quyết định)."""
    kq.ghi()
    kq.ghi("4) BUỔI LIVE & ĐỌC THỬ BÌNH LUẬN")
    if not page_id and not live_video_id:
        kq.ghi("   (chưa biết Page id — bỏ qua)")
        kq.chan("Không xác định được Page id để tìm buổi live (điền FACEBOOK_PAGE_ID vào .env).")
        return

    truc_tiep = ""
    if live_video_id:
        truc_tiep = live_video_id
        kq.ghi(f"   Live video id  : {truc_tiep} (do người dùng truyền vào)")
    else:
        fields = "id,status,live_views,broadcast_start_time,permalink_url"
        data, loi = graph.get(
            f"/{page_id}/live_videos",
            {"broadcast_status": '["LIVE"]', "fields": fields, "limit": "5"},
        )
        if loi:
            kq.ghi(f"   live_videos    : KHÔNG đọc được — {loi}")
            kq.chan(f"Không đọc được danh sách live video của Page ({loi}).")
            return
        muc = [m for m in (data.get("data") or []) if isinstance(m, dict)]
        if muc:
            dau = muc[0]
            truc_tiep = str(dau.get("id") or "")
            kq.ghi(f"   ĐANG PHÁT      : có ({len(muc)} buổi)")
            kq.ghi(f"   Live video id  : {truc_tiep}")
            kq.ghi(f"   Người xem hiện : {dau.get('live_views', 'không rõ')}")
            if dau.get("broadcast_start_time"):
                kq.ghi(f"   Bắt đầu lúc    : {dau['broadcast_start_time']}")
            if dau.get("permalink_url"):
                kq.ghi(f"   Link           : https://facebook.com{dau['permalink_url']}")
        else:
            kq.ghi("   ĐANG PHÁT      : KHÔNG có buổi live nào")
            truc_tiep = _live_gan_nhat(graph, kq, page_id)

    if not truc_tiep:
        kq.canh(
            "Page chưa từng có buổi live nào nên KHÔNG thể thử đọc bình luận hôm nay. "
            "Hãy phát live thử ~1 phút (có thể để chế độ 'Chỉ mình tôi'), tự bình luận một "
            "câu, rồi chạy lại script này — đó là phép thử duy nhất chứng minh đường dữ liệu."
        )
        return
    _doc_thu_binh_luan(graph, kq, truc_tiep)


def _live_gan_nhat(graph: _Graph, kq: KetQua, page_id: str) -> str:
    """Không có buổi live đang phát thì lấy buổi gần nhất để thử đọc bình luận."""
    data, loi = graph.get(
        f"/{page_id}/live_videos",
        {
            "broadcast_status": '["LIVE_STOPPED","PROCESSING","VOD"]',
            "fields": "id,status,broadcast_start_time",
            "limit": "1",
        },
    )
    if loi:
        kq.ghi(f"   live gần nhất  : KHÔNG đọc được — {loi}")
        kq.chan(f"Không đọc được lịch sử live video của Page ({loi}).")
        return ""
    muc = [m for m in (data.get("data") or []) if isinstance(m, dict)]
    if not muc:
        return ""
    vid = str(muc[0].get("id") or "")
    kq.ghi(f"   Live gần nhất  : {vid} (status={muc[0].get('status', '?')}) — dùng để đọc thử")
    return vid


def _doc_thu_binh_luan(graph: _Graph, kq: KetQua, live_video_id: str) -> None:
    """Gọi ĐÚNG request của runner. Chỉ đếm, KHÔNG in nội dung bình luận (PII)."""
    data, loi = graph.get(f"/{live_video_id}/comments", comment_params(limit=3))
    if loi:
        kq.ghi(f"   Đọc bình luận  : THẤT BẠI — {loi}")
        kq.chan(
            "Không đọc được bình luận của buổi live "
            f"({loi}). Nguyên nhân hay gặp nhất: token thiếu quyền pages_read_user_content."
        )
        return
    so = len([m for m in (data.get("data") or []) if isinstance(m, dict)])
    kq.ghi(f"   Đọc bình luận  : OK — lấy được {so} bình luận (không in nội dung: quy tắc PII)")
    if so == 0:
        kq.canh(
            "Đọc được nhưng buổi live này chưa có bình luận nào — quyền có vẻ đủ, vẫn nên "
            "thử lại trên một buổi live có bình luận thật."
        )


def _muc_5_han_muc(graph: _Graph, kq: KetQua) -> None:
    kq.ghi()
    kq.ghi("5) HẠN MỨC GỌI API")
    if graph.usage_pct is None:
        kq.ghi("   (Facebook không trả header X-App-Usage cho các lệnh vừa gọi)")
        return
    kq.ghi(f"   Đã dùng        : {graph.usage_pct:.0f}% (Facebook chặn khi chạm 100%)")
    kq.ghi("   Ghi chú        : hạn mức Page = 4800 × số người tương tác / 24 giờ trượt;")
    kq.ghi("                    poll 5 giây ≈ 17.000 lượt gọi/24 giờ.")
    if graph.usage_pct >= 75:
        kq.canh(
            f"Hạn mức đã dùng {graph.usage_pct:.0f}% — giãn nhịp poll hoặc tắt bớt tiến trình "
            "ingest trước khi vào phiên."
        )


def kiem_tra(
    client: httpx.Client,
    *,
    token: str,
    graph_version: str,
    page_id: str = "",
    live_video_id: str = "",
    app_id: str = "",
    app_secret: str = "",
    bay_gio: datetime | None = None,
) -> KetQua:
    """Chạy toàn bộ phép kiểm tra và trả về báo cáo (không in ra màn hình)."""
    bay_gio = bay_gio or datetime.now(UTC)
    kq = KetQua()
    kq.ghi(DAM)
    kq.ghi(" KIỂM TRA ĐƯỜNG FACEBOOK LIVE — LiveLift")
    kq.ghi(f" Thời điểm: {bay_gio:%d/%m/%Y %H:%M} UTC · Graph API {graph_version}")
    kq.ghi(DAM)
    kq.ghi()

    if not token.strip():
        kq.ghi("1) TOKEN")
        kq.ghi("   FACEBOOK_PAGE_ACCESS_TOKEN đang TRỐNG trong .env")
        kq.chan(
            "Chưa có token nào. Làm theo docs/huong-dan-facebook-token.md (khoảng 20 phút), "
            "dán token vào .env rồi chạy lại lệnh này."
        )
        return kq

    graph = _Graph(client, f"{GRAPH_BASE}/{graph_version}", token)
    app_token = f"{app_id}|{app_secret}" if app_id and app_secret else token
    info, _ = _muc_1_token(graph, kq, token, app_token, bay_gio)
    _muc_2_quyen(kq, info)
    page_id_thuc = _muc_3_page(graph, kq, page_id)
    _muc_4_live(graph, kq, page_id_thuc, live_video_id)
    _muc_5_han_muc(graph, kq)
    return kq


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/kiem_tra_facebook.py",
        description="Kiểm tra token/quyền Facebook trước khi chạy ingest phiên live thật.",
    )
    parser.add_argument("--token", default=None, help="ghi đè FACEBOOK_PAGE_ACCESS_TOKEN")
    parser.add_argument("--page-id", default=None, help="ghi đè FACEBOOK_PAGE_ID")
    parser.add_argument("--live-video-id", default="", help="thử đọc bình luận đúng video này")
    parser.add_argument("--graph-version", default=None, help="ví dụ v25.0")
    parser.add_argument("--timeout", type=float, default=20.0, help="giây cho mỗi lệnh gọi")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    token = args.token if args.token is not None else settings.facebook_page_access_token
    page_id = args.page_id if args.page_id is not None else settings.facebook_page_id
    version = args.graph_version or settings.facebook_graph_version
    with httpx.Client(timeout=args.timeout) as client:
        ket_qua = kiem_tra(
            client,
            token=token,
            graph_version=version,
            page_id=page_id,
            live_video_id=args.live_video_id,
            app_id=settings.facebook_app_id,
            app_secret=settings.facebook_app_secret,
        )
    print(ket_qua.van_ban())
    return 0 if ket_qua.san_sang else 1


if __name__ == "__main__":
    raise SystemExit(main())
