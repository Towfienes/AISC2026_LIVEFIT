#!/usr/bin/env python3
"""Kiểm tra TikTok Shop: đường hậu kiểm LIVE theo phút đã DÙNG ĐƯỢC chưa?

Chạy (từ thư mục gốc repo, sau khi đã điền bốn biến TIKTOK_SHOP_* vào .env):

    .venv/Scripts/python scripts/kiem_tra_tiktok_shop.py
    python scripts/kiem_tra_tiktok_shop.py --so-ngay 7        # macOS/Linux

Script **CHỈ ĐỌC** qua API chính thức TikTok Shop Open Platform:

1. kiểm đủ bốn biến (chỉ in độ dài, KHÔNG in giá trị);
2. gọi ``GET /analytics/202509/shop_lives/performance`` cho N ngày gần nhất,
   với tài khoản CHÍNH THỨC và tài khoản MARKETING (hai loại duy nhất có số liệu
   theo phút), in số phiên;
3. nếu có phiên: gọi ``performance_per_minutes`` cho phiên mới nhất, in số phút
   dữ liệu.

KHÔNG in thông tin khách hàng, tiêu đề phiên hay tên tài khoản — chỉ mã phiên,
giờ và số đếm. KHÔNG in token/App Secret.

Ngày trong tham số được tính theo **giờ Việt Nam (UTC+7)** vì tài liệu ghi
``start_date_ge``/``end_date_lt`` theo *"shop registered timezone"* — đúng cho
shop đăng ký ở Việt Nam. Tài liệu không nêu giới hạn độ dài khoảng ngày.

Mã thoát:

- 0 = DÙNG ĐƯỢC: đã đọc được ÍT NHẤT MỘT phút dữ liệu từ ``performance_per_minutes``;
- 1 = CHƯA DÙNG ĐƯỢC: có mục CHẶN (thiếu biến, sai danh tính, thiếu quyền…);
- 2 = CHƯA KIỂM ĐƯỢC THEO PHÚT: danh tính và danh sách phiên đã qua, nhưng không
  có phiên nào để gọi, hoặc phiên mới nhất chưa có phút dữ liệu nào. Kết quả này
  KHÔNG chứng minh đường theo phút chạy được — đừng ghi nó vào hồ sơ như vậy.

Hướng dẫn lấy khoá: docs/HUONG-DAN-LAY-KHOA-API.md mục 5.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import httpx

from livelift.config import get_settings
from livelift.console import configure
from livelift.ingest.tiktok_shop import (
    ACCOUNT_TYPES_CO_THEO_PHUT,
    DEFAULT_MIN_INTERVAL_S,
    REQUIRED_ENV,
    TikTokShopApiError,
    TikTokShopLiveAnalyticsClient,
    credential_problem,
    phien_moi_nhat,
)

NGAN = "-" * 66
DAM = "=" * 66

#: Việt Nam không có giờ mùa hè — độ lệch cố định, không cần cơ sở dữ liệu múi giờ.
GIO_VIET_NAM = timezone(timedelta(hours=7))

TEN_LOAI_TAI_KHOAN = {
    "OFFICIAL_ACCOUNTS": "tài khoản chính thức",
    "MARKETING_ACCOUNTS": "tài khoản marketing",
}

#: Cách sửa theo loại lỗi (câu chi tiết đã nằm trong chính thông điệp lỗi).
CACH_SUA = {
    "auth": "sửa danh tính theo câu trên rồi chạy lại script",
    "permission": "bật gói 'TikTok Shop Analytics' cho app và cho shop ủy quyền lại",
    "rate_limit": "đợi vài phút rồi chạy lại; không chạy song song nhiều tiến trình",
    "config": "đối chiếu biến TIKTOK_SHOP_SHOP_CIPHER và tài liệu endpoint",
    "transient": "chạy lại sau ít phút",
    "other": "tra mã lỗi ở https://partner.tiktokshop.com/docv2/page/common-errors",
}


MA_THOAT_DUNG_DUOC = 0
MA_THOAT_CHUA_DUNG_DUOC = 1
MA_THOAT_CHUA_KIEM_THEO_PHUT = 2


@dataclass
class KetQua:
    """Tích lũy kết luận theo ba trạng thái (xem mã thoát trong docstring mô-đun)."""

    chan: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    so_phien: int | None = None
    so_phut_phien_moi_nhat: int | None = None

    @property
    def bi_chan(self) -> bool:
        return bool(self.chan)

    @property
    def da_kiem_theo_phut(self) -> bool:
        """True chỉ khi ``performance_per_minutes`` trả về ít nhất một phút."""
        return (self.so_phut_phien_moi_nhat or 0) > 0

    @property
    def dung_duoc(self) -> bool:
        return not self.bi_chan and self.da_kiem_theo_phut

    @property
    def ket_luan(self) -> str:
        if self.bi_chan:
            return "CHƯA DÙNG ĐƯỢC"
        if self.da_kiem_theo_phut:
            return "DÙNG ĐƯỢC"
        return "CHƯA KIỂM ĐƯỢC THEO PHÚT"

    @property
    def ma_thoat(self) -> int:
        if self.bi_chan:
            return MA_THOAT_CHUA_DUNG_DUOC
        if self.da_kiem_theo_phut:
            return MA_THOAT_DUNG_DUOC
        return MA_THOAT_CHUA_KIEM_THEO_PHUT

    def giai_thich_ket_luan(self) -> str:
        """Một câu tiếng Việt nói rõ kết luận chứng minh được gì, không được gì."""
        if self.bi_chan:
            return "Sửa các mục CHẶN dưới đây rồi chạy lại."
        if self.da_kiem_theo_phut:
            return (
                f"Đã đọc được {self.so_phut_phien_moi_nhat} phút dữ liệu của phiên mới nhất "
                "qua API chính thức."
            )
        viec = (
            "không có phiên LIVE nào để gọi performance_per_minutes"
            if self.so_phut_phien_moi_nhat is None
            else "performance_per_minutes trả về 0 phút cho phiên mới nhất"
        )
        return (
            f"Danh tính và danh sách phiên đã qua, nhưng {viec}. Đường hậu kiểm theo phút "
            "CHƯA được chứng minh — không ghi vào hồ sơ là đã chạy được. Phát một phiên bằng "
            "tài khoản chính thức của shop, kết thúc phiên, rồi chạy lại script."
        )

    def bao_chan(self, ly_do: str, cach_sua: str) -> None:
        self.chan.append(f"{ly_do} → {cach_sua}")
        print(f"   [CHẶN] {ly_do}")
        print(f"          Cách sửa: {cach_sua}")

    def bao_canh(self, noi_dung: str) -> None:
        self.canh_bao.append(noi_dung)
        print(f"   [CẢNH BÁO] {noi_dung}")


def _gio_vn(ts: Any) -> str:
    try:
        moc = datetime.fromtimestamp(int(str(ts)), tz=UTC).astimezone(GIO_VIET_NAM)
    except (TypeError, ValueError, OSError, OverflowError):
        return "(không rõ)"
    return moc.strftime("%d/%m/%Y %H:%M:%S") + " (giờ VN)"


def _chan_theo_loi(kq: KetQua, viec: str, exc: TikTokShopApiError) -> None:
    kq.bao_chan(f"{viec} thất bại: {exc}", CACH_SUA.get(exc.loai, CACH_SUA["other"]))


def _muc_1_danh_tinh(
    kq: KetQua,
    s: Any,
    http: httpx.AsyncClient | None,
    nhip_s: float,
) -> TikTokShopLiveAnalyticsClient | None:
    print("1) DANH TÍNH")
    cap = {
        "TIKTOK_SHOP_APP_KEY": s.tiktok_shop_app_key,
        "TIKTOK_SHOP_APP_SECRET": s.tiktok_shop_app_secret,
        "TIKTOK_SHOP_ACCESS_TOKEN": s.tiktok_shop_access_token,
        "TIKTOK_SHOP_SHOP_CIPHER": s.tiktok_shop_shop_cipher,
    }
    for ten in REQUIRED_ENV:
        gia_tri = (cap[ten] or "").strip()
        mo_ta = f"{len(gia_tri)} ký tự (không in ra)" if gia_tri else "TRỐNG"
        print(f"   {ten:26s}: {mo_ta}")
    van_de = credential_problem(cap)
    if van_de:
        kq.bao_chan(
            van_de,
            "tạo app trong Partner Center, bật gói 'TikTok Shop Analytics', cho shop ủy "
            "quyền, rồi điền đủ bốn biến vào .env",
        )
        return None
    return TikTokShopLiveAnalyticsClient(
        app_key=cap["TIKTOK_SHOP_APP_KEY"],
        app_secret=cap["TIKTOK_SHOP_APP_SECRET"],
        access_token=cap["TIKTOK_SHOP_ACCESS_TOKEN"],
        shop_cipher=cap["TIKTOK_SHOP_SHOP_CIPHER"],
        client=http,
        min_interval_s=nhip_s,
    )


async def _muc_2_danh_sach(
    client: TikTokShopLiveAnalyticsClient, kq: KetQua, hom_nay: date, so_ngay: int
) -> list[dict[str, Any]] | None:
    print()
    tu_ngay = hom_nay - timedelta(days=so_ngay - 1)
    den_truoc = hom_nay + timedelta(days=1)
    print(f"2) DANH SÁCH PHIÊN LIVE {so_ngay} NGÀY GẦN NHẤT")
    print(f"   Khoảng ngày (giờ VN) : {tu_ngay.isoformat()} → {hom_nay.isoformat()} (gồm cả hai)")
    tat_ca: list[dict[str, Any]] = []
    for loai in ACCOUNT_TYPES_CO_THEO_PHUT:
        try:
            ds = await client.list_live_sessions(tu_ngay, den_truoc, account_type=loai)
        except TikTokShopApiError as exc:
            _chan_theo_loi(kq, f"shop_lives/performance ({TEN_LOAI_TAI_KHOAN[loai]})", exc)
            return None
        print(f"   {TEN_LOAI_TAI_KHOAN[loai]:21s}: {len(ds.phien)} phiên")
        if ds.latest_available_date:
            print(f"   {'':21s}  dữ liệu ngày mới nhất: {ds.latest_available_date}")
        tat_ca.extend(ds.phien)
    kq.so_phien = len(tat_ca)
    print(f"   Tổng số phiên        : {kq.so_phien}")
    return tat_ca


async def _muc_3_theo_phut(
    client: TikTokShopLiveAnalyticsClient, kq: KetQua, phien: list[dict[str, Any]]
) -> None:
    print()
    print("3) SỐ LIỆU THEO PHÚT CỦA PHIÊN MỚI NHẤT")
    moi_nhat = phien_moi_nhat(phien)
    if moi_nhat is None:
        kq.bao_canh(
            "Không có phiên LIVE nào của tài khoản chính thức/marketing trong khoảng ngày "
            "này — danh tính đã qua, nhưng chưa thử được số liệu theo phút. Phát một phiên "
            "bằng tài khoản chính thức của shop, KẾT THÚC phiên, rồi chạy lại script."
        )
        return
    live_id = str(moi_nhat.get("id") or "")
    print(f"   Mã phiên (live_id)   : {live_id or '(không có)'}")
    print(f"   Bắt đầu              : {_gio_vn(moi_nhat.get('start_time'))}")
    print(f"   Kết thúc             : {_gio_vn(moi_nhat.get('end_time'))}")
    print("   Tiêu đề/tài khoản    : KHÔNG in")
    if not live_id:
        kq.bao_chan(
            "Phiên mới nhất không có trường id",
            "lược đồ phản hồi đã đổi — đối chiếu tài liệu shop_lives/performance",
        )
        return
    try:
        hs = await client.performance_per_minutes(live_id)
    except TikTokShopApiError as exc:
        _chan_theo_loi(kq, "performance_per_minutes", exc)
        return
    except ValueError as exc:
        kq.bao_chan(f"live_id không dùng được: {exc}", "đối chiếu trường id trong phản hồi")
        return
    kq.so_phut_phien_moi_nhat = len(hs.intervals)
    tong = "không có" if hs.total_count is None else str(hs.total_count)
    print(f"   Số phút dữ liệu      : {len(hs.intervals)} (total_count TikTok báo: {tong})")
    print(f"   Số trang đã đọc      : {hs.so_trang}")
    for dong in hs.canh_bao:
        kq.bao_canh(dong)
    if not hs.intervals:
        kq.bao_canh(
            "Phiên mới nhất chưa có dữ liệu theo phút. TikTok chỉ trả sau khi phiên KẾT THÚC "
            "và tài liệu không công bố độ trễ — chạy lại sau (ví dụ mỗi 15 phút) và ghi lại "
            "độ trễ đo được."
        )


def _muc_4_gioi_han() -> None:
    print()
    print("4) GIỚI HẠN CỦA ĐƯỜNG NÀY")
    print("   - Chỉ HẬU KIỂM: số theo phút có SAU khi phiên kết thúc, không có trong lúc phát.")
    print("   - KHÔNG có nội dung bình luận (chỉ SỐ bình luận), KHÔNG ghim sản phẩm qua API.")
    print("   - Chỉ phiên của tài khoản chính thức / marketing của shop.")
    print("   - access_token sống 7 ngày; LiveLift chưa tự làm mới.")


async def kiem_tra(
    *,
    so_ngay: int = 7,
    settings: Any = None,
    http: httpx.AsyncClient | None = None,
    hom_nay: date | None = None,
    nhip_s: float = DEFAULT_MIN_INTERVAL_S,
) -> KetQua:
    """Chạy các mục kiểm tra. ``settings``/``http``/``hom_nay``/``nhip_s`` để test tiêm vào."""
    kq = KetQua()
    print(DAM)
    print(" KIỂM TRA TIKTOK SHOP — LiveLift")
    print(" API chính thức: TikTok Shop Open Platform (hậu kiểm LIVE theo phút)")
    print(DAM)
    ngay = hom_nay or datetime.now(GIO_VIET_NAM).date()
    client = _muc_1_danh_tinh(
        kq, settings if settings is not None else get_settings(), http, nhip_s
    )
    if client is not None:
        try:
            phien = await _muc_2_danh_sach(client, kq, ngay, so_ngay)
            if phien is not None:
                await _muc_3_theo_phut(client, kq, phien)
        finally:
            await client.aclose()
    _muc_4_gioi_han()
    return kq


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/kiem_tra_tiktok_shop.py",
        description="Kiểm tra đường hậu kiểm LIVE TikTok Shop (API chính thức, chỉ đọc).",
    )
    parser.add_argument(
        "--so-ngay",
        type=int,
        default=7,
        help="số ngày gần nhất (tính cả hôm nay, giờ VN) để tìm phiên LIVE; mặc định 7",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # Console Windows mặc định cp1252 — gọi TRƯỚC parse_args (sự cố 27/08).
    configure()
    args = build_parser().parse_args(argv)
    if args.so_ngay < 1:
        print("--so-ngay phải ≥ 1.")
        return 1
    kq = asyncio.run(kiem_tra(so_ngay=args.so_ngay))
    print()
    print(NGAN)
    print(f"KẾT LUẬN: {kq.ket_luan} (mã thoát {kq.ma_thoat})")
    print(kq.giai_thich_ket_luan())
    if kq.chan:
        print("Phải sửa:")
        for dong in kq.chan:
            print(f"  - {dong}")
    if kq.canh_bao:
        print("Lưu ý:")
        for dong in kq.canh_bao:
            print(f"  - {dong}")
    print(DAM)
    return kq.ma_thoat


if __name__ == "__main__":
    raise SystemExit(main())
