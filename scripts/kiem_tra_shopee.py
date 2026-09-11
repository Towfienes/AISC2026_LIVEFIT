#!/usr/bin/env python3
"""Kiểm tra Shopee Live: đường ingest Shopee đã SẴN SÀNG chưa?

Chạy (từ thư mục gốc repo, sau khi đã điền danh tính vào .env):

    .venv/Scripts/python scripts/kiem_tra_shopee.py --session-id <SESSION_ID>
    python scripts/kiem_tra_shopee.py --session-id <SESSION_ID>     # macOS/Linux

Script **CHỈ ĐỌC** — không đăng bình luận, không bắt đầu/kết thúc phiên nào.
Nó gọi đúng ba endpoint mà runner sẽ gọi trong phiên thật
(``get_session_detail``, ``get_session_metric``, ``get_latest_comment_list``),
rồi in bảng tiếng Việt và KẾT LUẬN "SẴN SÀNG / CHƯA SẴN SÀNG" kèm cách sửa.

Mã thoát: 0 = SẴN SÀNG, 1 = CHƯA SẴN SÀNG (dùng được trong checklist trước phiên).

**KHÔNG in nội dung bình luận** (quy tắc PII của dự án) — chỉ in số lượng.
**KHÔNG in token/partner_key** — chỉ in độ dài.

Bối cảnh và cách xin danh tính: docs/nen-tang-ho-tro.md §4.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field

from livelift.config import get_settings
from livelift.ingest.shopee import (
    COMMENT_WINDOW_S,
    MAX_SAFE_POLL_S,
    REGION_BASE_URLS,
    STATUS_ENDED,
    STATUS_INIT,
    STATUS_ONGOING,
    ShopeeApiError,
    ShopeeLiveClient,
    classify_error,
    parse_comment,
)

NGAN = "-" * 66
DAM = "=" * 66

TEN_TRANG_THAI = {
    STATUS_INIT: "chưa bắt đầu",
    STATUS_ONGOING: "ĐANG PHÁT",
    STATUS_ENDED: "đã kết thúc",
}


@dataclass
class KetQua:
    """Tích lũy kết luận; ``san_sang`` False ngay khi có một mục CHẶN."""

    san_sang: bool = True
    chan: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)

    def bao_chan(self, ly_do: str, cach_sua: str) -> None:
        self.san_sang = False
        self.chan.append(f"{ly_do} → {cach_sua}")
        print(f"   [CHẶN] {ly_do}")
        print(f"          Cách sửa: {cach_sua}")

    def bao_canh(self, noi_dung: str) -> None:
        self.canh_bao.append(noi_dung)
        print(f"   [CẢNH BÁO] {noi_dung}")


def mo_ta_loi(exc: ShopeeApiError) -> str:
    """Thông điệp tiếng Việt cho một lỗi Shopee, kèm việc phải làm."""
    kind = classify_error(exc)
    if kind == "auth":
        return (
            f"{exc.code} — danh tính sai hoặc token hết hạn. access_token của "
            "Shopee chỉ sống 4 giờ: làm mới bằng refresh_token, rồi dán lại "
            "SHOPEE_ACCESS_TOKEN vào .env."
        )
    if kind == "rate_limit":
        return f"{exc.code} — đang bị bóp nhịp gọi. Token VẪN TỐT; chờ rồi thử lại."
    return f"{exc.code} — lỗi tạm thời/máy chủ. Thử lại sau ít phút."


def _muc_1_danh_tinh(kq: KetQua) -> ShopeeLiveClient | None:
    print("1) DANH TÍNH")
    s = get_settings()
    cap = {
        "SHOPEE_PARTNER_ID": s.shopee_partner_id,
        "SHOPEE_PARTNER_KEY": s.shopee_partner_key,
        "SHOPEE_SHOP_ID": s.shopee_shop_id,
        "SHOPEE_ACCESS_TOKEN": s.shopee_access_token,
    }
    for ten, gia_tri in cap.items():
        if ten.endswith(("KEY", "TOKEN")):
            mo_ta = f"{len(gia_tri)} ký tự (không in ra)" if gia_tri else "TRỐNG"
        else:
            mo_ta = gia_tri or "TRỐNG"
        print(f"   {ten:22s}: {mo_ta}")
    thieu = [ten for ten, gia_tri in cap.items() if not gia_tri]
    if thieu:
        kq.bao_chan(
            "Thiếu " + ", ".join(thieu) + " trong .env",
            "xin partner_id/partner_key ở open.shopee.com rồi chạy luồng ủy quyền "
            "shop — xem docs/nen-tang-ho-tro.md §4",
        )
        return None
    vung = (s.shopee_region or "global").strip().lower()
    if vung not in REGION_BASE_URLS:
        kq.bao_chan(
            f"SHOPEE_REGION không hợp lệ: {vung!r}",
            "đặt SHOPEE_REGION=global (Việt Nam dùng cổng global)",
        )
        return None
    print(f"   {'SHOPEE_REGION':22s}: {vung} → {REGION_BASE_URLS[vung]}")
    if not s.shopee_refresh_token:
        kq.bao_canh(
            "Chưa có SHOPEE_REFRESH_TOKEN — access_token hết hạn sau 4 giờ và "
            "sẽ không tự làm mới được giữa phiên."
        )
    return ShopeeLiveClient()


async def _muc_2_phien(client: ShopeeLiveClient, kq: KetQua, session_id: str) -> int | None:
    print()
    print("2) PHIÊN LIVE")
    try:
        detail = await client.get_session_detail(session_id)
    except ShopeeApiError as exc:
        kq.bao_chan(f"get_session_detail thất bại: {mo_ta_loi(exc)}", "sửa theo dòng trên")
        return None
    status = detail.get("status")
    status_int = int(status) if status is not None else None
    print(f"   Tiêu đề          : {detail.get('title') or '(không có)'}")
    print(f"   session_id       : {detail.get('session_id') or session_id}")
    print(f"   Trạng thái       : {TEN_TRANG_THAI.get(status_int, f'không rõ ({status})')}")
    if status_int == STATUS_ENDED:
        kq.bao_canh(
            "Phiên ĐÃ KẾT THÚC — get_latest_comment_list chỉ có dữ liệu khi đang "
            "phát, nên phép thử đọc bình luận bên dưới sẽ rỗng dù đường đi vẫn tốt."
        )
    return status_int


async def _muc_3_chi_so(client: ShopeeLiveClient, kq: KetQua, session_id: str) -> None:
    print()
    print("3) CHỈ SỐ THỜI GIAN THỰC (nguồn biến kết quả)")
    try:
        metric = await client.get_session_metric(session_id)
    except ShopeeApiError as exc:
        kq.bao_chan(f"get_session_metric thất bại: {mo_ta_loi(exc)}", "sửa theo dòng trên")
        return
    for khoa, nhan in (
        ("ccu", "Người xem hiện tại"),
        ("peak_ccu", "Đỉnh người xem"),
        ("views", "Lượt xem"),
        ("comments", "Số bình luận"),
        ("atc", "Lượt thêm giỏ (ATC)"),
        ("orders", "Số đơn"),
        ("gmv", "GMV"),
    ):
        gia_tri = metric.get(khoa)
        print(f"   {nhan:22s}: {'(không có)' if gia_tri is None else gia_tri}")
    if metric.get("orders") is None and metric.get("gmv") is None:
        kq.bao_canh(
            "Không thấy orders/gmv — thiếu tín hiệu chuyển đổi thì phiên này chỉ "
            "quan sát được, KHÔNG sinh được số nhân quả."
        )


async def _muc_4_binh_luan(client: ShopeeLiveClient, kq: KetQua, session_id: str) -> None:
    print()
    print("4) ĐỌC THỬ BÌNH LUẬN (phép thử quyết định)")
    try:
        data = await client._get(  # noqa: SLF001 — cố ý gọi đúng đường của runner
            "/livestream/get_latest_comment_list", {"session_id": session_id, "offset": 0}
        )
    except ShopeeApiError as exc:
        kq.bao_chan(
            f"get_latest_comment_list thất bại: {mo_ta_loi(exc)}",
            "nếu là lỗi quyền: kiểm tra app đã xin scope livestream khi ủy quyền shop chưa",
        )
        return
    items = data.get("list") or []
    doc_duoc = sum(1 for item in items if parse_comment(item) is not None)
    print("   Gọi API          : OK")
    print(f"   Bình luận trả về : {len(items)} (parse được {doc_duoc})")
    print("   Nội dung         : KHÔNG in (quy tắc PII của dự án)")
    if items and doc_duoc == 0:
        kq.bao_chan(
            "Shopee trả bình luận nhưng parser đọc được 0",
            "lược đồ phản hồi đã đổi — sửa parse_comment trong src/livelift/ingest/shopee.py",
        )
    elif not items:
        kq.bao_canh(
            f"0 bình luận trong cửa sổ {COMMENT_WINDOW_S:.0f}s vừa rồi — bình thường "
            "nếu phòng đang vắng hoặc phiên đã kết thúc; chạy lại lúc có người chat "
            "mới chứng minh được đường dữ liệu."
        )


def _muc_5_nhac_nhip(kq: KetQua) -> None:
    print()
    print("5) NHỊP POLL")
    print(f"   Cửa sổ dữ liệu   : {COMMENT_WINDOW_S:.0f}s (get_latest_comment_list)")
    print(f"   Nhịp tối đa      : {MAX_SAFE_POLL_S:.0f}s — runner từ chối chạy nếu vượt")
    print("   Lý do            : không có con trỏ 'since'; poll chậm là MẤT bình luận")


async def kiem_tra(session_id: str) -> KetQua:
    kq = KetQua()
    print(DAM)
    print(" KIỂM TRA ĐƯỜNG SHOPEE LIVE — LiveLift")
    print(" API chính thức: Shopee Open Platform v2 (hợp Điều khoản dịch vụ)")
    print(DAM)
    client = _muc_1_danh_tinh(kq)
    if client is None:
        _muc_5_nhac_nhip(kq)
        return kq
    try:
        status = await _muc_2_phien(client, kq, session_id)
        if status is not None:
            await _muc_3_chi_so(client, kq, session_id)
            await _muc_4_binh_luan(client, kq, session_id)
    finally:
        await client.aclose()
    _muc_5_nhac_nhip(kq)
    return kq


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/kiem_tra_shopee.py",
        description="Kiểm tra đường ingest Shopee Live đã sẵn sàng chưa (chỉ đọc).",
    )
    parser.add_argument(
        "--session-id",
        required=True,
        help="session_id của phiên Shopee Live cần kiểm tra (id đổi theo từng buổi)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kq = asyncio.run(kiem_tra(args.session_id))
    print()
    print(NGAN)
    print(f"KẾT LUẬN: {'SẴN SÀNG' if kq.san_sang else 'CHƯA SẴN SÀNG'}")
    if kq.chan:
        print("Phải sửa:")
        for dong in kq.chan:
            print(f"  - {dong}")
    if kq.canh_bao:
        print("Lưu ý:")
        for dong in kq.canh_bao:
            print(f"  - {dong}")
    print(DAM)
    return 0 if kq.san_sang else 1


if __name__ == "__main__":
    raise SystemExit(main())
