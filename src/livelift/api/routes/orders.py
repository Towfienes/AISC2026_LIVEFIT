"""Ghi đơn hàng — tay từng đơn hoặc nhập tệp CSV (kiểm toán 17/09/2026).

Bảng ``order_event`` và ``Store.add_order`` có từ migration 0001, nhưng KHÔNG
một đường API nào gọi tới: báo cáo luôn ghi "chưa ghi nhận đơn", tín hiệu
"đối soát doanh thu" của ma trận năng lực vĩnh viễn THIẾU, và biến phụ số đơn
/GMV của tiền đăng ký (§4.2) không kiểm chứng được.

Đường thực tế cho người bán Việt Nam: hầu hết nền tảng KHÔNG cho đọc đơn theo
phiên live qua API (TikTok, Facebook, YouTube), nhưng Seller Center nào cũng
xuất được danh sách đơn ra tệp. Vì vậy có hai cửa:

* ``POST /sessions/{id}/orders``         — một đơn (nhập tay ngay trong buổi);
* ``POST /sessions/{id}/orders/import``  — dán nội dung CSV đã xuất.

Quy tắc chung:

* **Idempotent theo mã đơn.** Nhập lại cùng một tệp không nhân đôi doanh thu —
  người vận hành sẽ nhập lại, chắc chắn.
* **Gán khối theo THỜI ĐIỂM ĐẶT ĐƠN**, không theo lúc nhập: tệp thường được nhập
  sau khi buổi live đã kết thúc.
* **Không nhận dữ liệu người mua.** Không có cột tên/SĐT/địa chỉ nào được đọc;
  cột thừa trong tệp xuất bị bỏ qua, không lưu (quy tắc cứng 1).
* **Chỉ nhận đơn trong KHUNG GIỜ của phiên** (từ bắt đầu trừ
  :data:`DEM_TRUOC_BAT_DAU_S` tới kết thúc cộng :data:`DEM_SAU_KET_THUC_S`).
  Seller Center xuất theo NGÀY, nên một tệp thường chứa đơn của nhiều buổi live.
  Trước khi có luật này, đơn của buổi tối bị ghi vào buổi sáng (doanh thu phình,
  tín hiệu đơn hàng báo "ok"), và vì mã đơn là khoá toàn kho nên buổi tối không
  bao giờ nhập lại được đơn của chính mình (kiểm toán 17/09/2026). Dòng ngoài
  khung KHÔNG được lưu: nó được đếm ở ``ngoai_khung`` và liệt kê kèm lý do.
* Mức bảo vệ ``demo``: phiên THẬT cần token ghi, khách của bản trưng bày chỉ
  ghi được vào phiên mẫu. Khách không token còn bị trần riêng: tối đa
  :data:`MAX_CSV_ROWS_KHACH` dòng mỗi lượt nhập và :data:`MAX_DON_PHIEN_KHACH`
  đơn mỗi phiên, cộng trần lượt nhập theo giờ ở tầng xác thực.
"""

from __future__ import annotations

import csv
import io
import math
import re
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from livelift.api import service
from livelift.api.auth import cho_phep_demo, ghi_khong_token
from livelift.api.service import StoreDep

router = APIRouter()

GIO_VN = timezone(timedelta(hours=7))
MAX_CSV_BYTES = 2_000_000
MAX_CSV_ROWS = 5000
MAX_CSV_ROWS_KHACH = 500
"""Trần dòng mỗi lượt nhập của khách KHÔNG token trên bản trưng bày công khai.
5.000 dòng x trần 30 lượt/phút từng cho một địa chỉ ghi ~150.000 đơn/phút."""
MAX_DON_PHIEN_KHACH = 2000
"""Trần tổng số đơn của MỘT phiên mà khách không token được ghi tới."""

DEM_TRUOC_BAT_DAU_S = 60
"""Tệp xuất của Seller Center thường chỉ có giờ:phút, nên một đơn đặt ở giây
thứ 30 sau giờ bắt đầu hiện thành phút TRƯỚC giờ bắt đầu."""
DEM_SAU_KET_THUC_S = 30 * 60
"""Khách "chốt" trong bình luận rồi lên đơn trễ vài phút sau khi tắt live. Độ trễ
đặt đơn thật CHƯA đo (mo-hinh-van-hanh-kol.md, Rào cản 3): 30 phút là khoảng đệm
đặt trước, đơn trễ hơn không được gán cho phiên."""


class OrderIn(BaseModel):
    order_id: str | None = Field(default=None, min_length=1, max_length=128)
    """Mã đơn của nền tảng — khoá chống trùng. Bỏ trống = máy chủ tự sinh."""
    ts_utc: datetime | None = None
    """Thời điểm ĐẶT đơn (có múi giờ). Bỏ trống = bây giờ."""
    product_id: str | None = Field(default=None, max_length=64)
    qty: int = Field(default=1, ge=1, le=10_000)
    gross: float = Field(ge=0, le=10_000_000_000)
    """Tổng tiền đơn (VND)."""
    fees: float = Field(default=0, ge=0, le=10_000_000_000)
    net_margin: float | None = None

    @field_validator("ts_utc")
    @classmethod
    def _co_mui_gio(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("ts_utc phải có múi giờ, ví dụ 2026-09-17T20:05:00+07:00")
        return v


class OrderOut(BaseModel):
    order_id: str
    session_id: str
    block_id: str | None = None
    ts: datetime
    product_id: str | None = None
    qty: int
    gross: float
    fees: float
    net_margin: float | None = None


class OrderImportIn(BaseModel):
    csv: str = Field(min_length=1, max_length=MAX_CSV_BYTES)


class OrderImportLoi(BaseModel):
    dong: int
    ly_do: str


class OrderImportOut(BaseModel):
    nhap_moi: int
    trung_bo_qua: int
    loi: list[OrderImportLoi]
    """Tối đa 50 dòng lỗi đầu tiên — tổng thật ở ``tong_loi``. Lỗi dữ liệu đứng
    trước, dòng ngoài khung giờ phiên đứng sau."""
    tong_loi: int = 0
    ngoai_khung: int = 0
    """Số dòng KHÔNG lưu vì thời điểm đặt đơn nằm ngoài khung giờ của phiên (đã
    tính trong ``tong_loi``) — thường là đơn của buổi live khác cùng ngày."""
    tong_don: int
    tong_doanh_thu: float


class OrderSummary(BaseModel):
    session_id: str
    tong_don: int
    tong_san_pham: int
    tong_doanh_thu: float
    don: list[OrderOut]


def _so(v: Any) -> float:
    return float(v) if isinstance(v, (int, float, Decimal)) else 0.0


def _ra_out(session_id: str, row: dict[str, Any]) -> OrderOut:
    return OrderOut(
        order_id=str(row["order_id"]),
        session_id=session_id,
        block_id=str(row["block_id"]) if row.get("block_id") else None,
        ts=row["ts"],
        product_id=row.get("product_id"),
        qty=int(row.get("qty") or 1),
        gross=_so(row.get("gross")),
        fees=_so(row.get("fees")),
        net_margin=None if row.get("net_margin") is None else _so(row.get("net_margin")),
    )


def _khoi_cua_thoi_diem(session: dict[str, Any], blocks: list[dict[str, Any]], ts: datetime):
    """Khối chứa THỜI ĐIỂM ĐẶT ĐƠN — kể cả khi phiên đã kết thúc."""
    start = session.get("start_ts")
    if start is None or ts < start:
        return None
    end = session.get("end_ts")
    if end is not None and ts > end:
        return None
    return service.block_at_offset(blocks, (ts - start).total_seconds())


class NgoaiKhungPhienError(ValueError):
    """Thời điểm đặt đơn nằm ngoài khung giờ của phiên — đơn KHÔNG được lưu."""


def _gio_vn(ts: datetime) -> str:
    return ts.astimezone(GIO_VN).strftime("%d/%m/%Y %H:%M")


def _kiem_tra_khung_phien(session: dict[str, Any], ts: datetime) -> None:
    """Từ chối đơn ngoài [bắt đầu - đệm, kết thúc + đệm].

    Phiên chưa phát (chưa có ``start_ts``) thì chưa có khung để đối chiếu: nhận
    như trước. Phiên đang phát chỉ có cận dưới.
    """
    start = session.get("start_ts")
    if start is None:
        return
    tu = start - timedelta(seconds=DEM_TRUOC_BAT_DAU_S)
    end = session.get("end_ts")
    den = end + timedelta(seconds=DEM_SAU_KET_THUC_S) if end is not None else None
    if ts >= tu and (den is None or ts <= den):
        return
    khung = f"từ {_gio_vn(tu)}" + (f" đến {_gio_vn(den)}" if den is not None else "")
    raise NgoaiKhungPhienError(
        f"đơn đặt lúc {_gio_vn(ts)} (giờ VN) nằm ngoài khung giờ của phiên ({khung}) "
        "— không lưu; nếu là đơn của buổi live khác, hãy nhập vào đúng phiên đó"
    )


def _ghi_don(
    store: Any,
    session: dict[str, Any],
    body: OrderIn,
    da_co: set[str],
    blocks: list[dict[str, Any]] | None = None,
    san_pham_co: dict[str, bool] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Ghi một đơn. Trả (bản ghi, là_đơn_mới). ``da_co`` = mã đơn đã có của
    phiên, được cập nhật tại chỗ (nhập 5.000 dòng không đọc lại kho 5.000 lần).

    ``blocks`` và ``san_pham_co`` là bộ đệm của một lượt nhập: lịch khối đọc MỘT
    lần, mỗi mã sản phẩm tra danh mục MỘT lần — không phải một truy vấn mỗi dòng.
    """
    session_id = session["session_id"]
    if body.product_id:
        if san_pham_co is None:
            san_pham_co = {}
        if body.product_id not in san_pham_co:
            san_pham_co[body.product_id] = store.get_product(body.product_id) is not None
        if not san_pham_co[body.product_id]:
            raise ValueError(f"Mã sản phẩm {body.product_id!r} không có trong danh mục")
    ts = (body.ts_utc or service.now_utc()).astimezone(UTC)
    _kiem_tra_khung_phien(session, ts)
    if blocks is None:
        blocks = store.get_blocks(session_id)
    block = _khoi_cua_thoi_diem(session, blocks, ts)
    order_id = body.order_id or service.new_id()
    row = {
        "order_id": order_id,
        "block_id": block["block_id"] if block else None,
        "ts": ts,
        "product_id": body.product_id or None,
        "qty": body.qty,
        "gross": body.gross,
        "fees": body.fees,
        "net_margin": body.net_margin,
    }
    moi = order_id not in da_co
    stored = store.add_order(session_id, row)
    if str(stored.get("session_id") or session_id) != session_id:
        raise ValueError(f"Mã đơn {order_id!r} đã được ghi cho một phiên khác")
    da_co.add(order_id)
    return stored, moi


@router.get("/sessions/{session_id}/orders", response_model=OrderSummary)
def list_orders(session_id: str, store: StoreDep) -> OrderSummary:
    service.require_session(store, session_id)
    don = [_ra_out(session_id, o) for o in store.list_orders(session_id)]
    return OrderSummary(
        session_id=session_id,
        tong_don=len(don),
        tong_san_pham=sum(d.qty for d in don),
        tong_doanh_thu=sum(d.gross for d in don),
        don=don,
    )


def _loi_tran_khach(so_don: int) -> str:
    return (
        f"phiên mẫu đã có {so_don} đơn — bản trưng bày công khai nhận tối đa "
        f"{MAX_DON_PHIEN_KHACH} đơn mỗi phiên cho khách không có token"
    )


@cho_phep_demo
@router.post("/sessions/{session_id}/orders", response_model=OrderOut)
def create_order(session_id: str, body: OrderIn, store: StoreDep, request: Request) -> OrderOut:
    session = service.require_session(store, session_id)
    da_co = {str(o["order_id"]) for o in store.list_orders(session_id)}
    ghi_lai_don_cu = body.order_id is not None and body.order_id in da_co
    if ghi_khong_token(request) and len(da_co) >= MAX_DON_PHIEN_KHACH and not ghi_lai_don_cu:
        raise HTTPException(status_code=429, detail=_loi_tran_khach(len(da_co)))
    try:
        stored, moi = _ghi_don(store, session, body, da_co)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    out = _ra_out(session_id, stored)
    if moi:
        store.publish(session_id, {"type": "order", "data": out.model_dump(mode="json")})
    return out


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

_COT: dict[str, tuple[str, ...]] = {
    "order_id": ("order_id", "ma_don", "mã đơn", "ma don hang", "mã đơn hàng", "order id"),
    "ts": (
        "ts",
        "ts_utc",
        "thoi_gian",
        "thời gian",
        "thời gian đặt hàng",
        "ngay_dat",
        "ngày đặt hàng",
        "created_time",
        "order creation time",
    ),
    "product_id": ("product_id", "ma_sp", "mã sp", "mã sản phẩm", "sku", "seller sku"),
    "qty": ("qty", "so_luong", "số lượng", "quantity"),
    "gross": (
        "gross",
        "doanh_thu",
        "doanh thu",
        "tong_tien",
        "tổng tiền",
        "tổng giá trị đơn hàng",
        "order amount",
        "total",
    ),
    "fees": ("fees", "phi", "phí", "phí sàn", "platform fee"),
}


def _chuan_hoa_ten_cot(ten: str) -> str:
    return re.sub(r"\s+", " ", ten.replace("﻿", "").strip().lower())


def _so_tien(raw: str) -> float:
    """``"1.250.000 ₫"`` / ``"1,250,000"`` / ``"125000.5"`` → số."""
    s = re.sub(r"[^\d,.\-]", "", raw or "")
    if not s:
        raise ValueError("thiếu số tiền")
    if "," in s and "." in s:
        # Dấu xuất hiện sau cùng là dấu thập phân.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        s = s.replace(".", "")  # 1.250.000 hoặc 125.000 kiểu Việt Nam
    elif s.count(",") > 1 or (s.count(",") == 1 and len(s.split(",")[1]) == 3):
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    return float(s)


_DINH_DANG_GIO = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
)


def _so_luong(raw: str) -> int:
    """``"2"`` / ``"2.0"`` → 2. ``inf``/``1e999``/``nan`` là lỗi của DÒNG, không
    phải lỗi 500 của cả lượt nhập (``int(float("inf"))`` ném OverflowError)."""
    so = float(raw)
    if not math.isfinite(so):
        raise ValueError(f"số lượng {raw[:20]!r} không phải một số hữu hạn")
    return int(so)


def _thoi_diem(raw: str) -> datetime:
    """ISO có múi giờ, hoặc giờ Việt Nam không múi giờ (kiểu tệp xuất Seller Center)."""
    s = (raw or "").strip()
    if not s:
        raise ValueError("thiếu thời gian đặt đơn")
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=GIO_VN)
    except ValueError:
        pass
    for fmt in _DINH_DANG_GIO:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=GIO_VN)
        except ValueError:
            continue
    raise ValueError(f"không đọc được thời gian {s!r} (dùng dd/mm/yyyy HH:MM hoặc ISO 8601)")


@cho_phep_demo
@router.post("/sessions/{session_id}/orders/import", response_model=OrderImportOut)
def import_orders(
    session_id: str, body: OrderImportIn, store: StoreDep, request: Request
) -> OrderImportOut:
    session = service.require_session(store, session_id)
    khach = ghi_khong_token(request)
    tran_dong = MAX_CSV_ROWS_KHACH if khach else MAX_CSV_ROWS
    doc = csv.reader(io.StringIO(body.csv))
    try:
        tieu_de = next(doc)
    except StopIteration as exc:
        raise HTTPException(status_code=422, detail="Tệp CSV rỗng") from exc
    ten_cot = [_chuan_hoa_ten_cot(t) for t in tieu_de]
    vi_tri: dict[str, int] = {}
    for khoa, bi_danh in _COT.items():
        for i, ten in enumerate(ten_cot):
            if ten in bi_danh:
                vi_tri[khoa] = i
                break
    thieu = [k for k in ("ts", "gross") if k not in vi_tri]
    if thieu:
        raise HTTPException(
            status_code=422,
            detail=(
                "Tệp CSV thiếu cột bắt buộc: "
                + ", ".join(thieu)
                + ". Cần ít nhất cột thời gian đặt đơn (ts / thời gian) và tổng tiền "
                "(gross / tổng tiền). Nên có thêm order_id để nhập lại không bị trùng."
            ),
        )

    nhap_moi = trung = 0
    loi: list[OrderImportLoi] = []
    ngoai_khung: list[OrderImportLoi] = []
    da_co = {str(o["order_id"]) for o in store.list_orders(session_id)}
    blocks = store.get_blocks(session_id)
    san_pham_co: dict[str, bool] = {}
    for so_dong, dong in enumerate(doc, start=2):
        if not any(c.strip() for c in dong):
            continue
        if so_dong - 1 > tran_dong:
            loi.append(OrderImportLoi(dong=so_dong, ly_do=f"vượt trần {tran_dong} dòng"))
            break
        if khach and len(da_co) >= MAX_DON_PHIEN_KHACH:
            loi.append(OrderImportLoi(dong=so_dong, ly_do=_loi_tran_khach(len(da_co))))
            break

        def o(khoa: str, dong: list[str] = dong) -> str:
            i = vi_tri.get(khoa)
            return dong[i].strip() if i is not None and i < len(dong) else ""

        try:
            don = OrderIn(
                order_id=o("order_id") or None,
                ts_utc=_thoi_diem(o("ts")),
                product_id=o("product_id") or None,
                qty=_so_luong(o("qty")) if o("qty") else 1,
                gross=_so_tien(o("gross")),
                fees=_so_tien(o("fees")) if o("fees") else 0.0,
            )
            _, moi = _ghi_don(store, session, don, da_co, blocks, san_pham_co)
        except NgoaiKhungPhienError as exc:
            ngoai_khung.append(OrderImportLoi(dong=so_dong, ly_do=str(exc)[:200]))
            continue
        except (ValueError, TypeError, OverflowError) as exc:
            # Chỉ ghi lý do ngắn — không lặp lại nội dung dòng (có thể lẫn dữ liệu
            # người mua ở cột thừa).
            ly_do = str(exc).splitlines()[0][:160]
            loi.append(OrderImportLoi(dong=so_dong, ly_do=ly_do))
            continue
        if moi:
            nhap_moi += 1
        else:
            trung += 1

    tat_ca = store.list_orders(session_id)
    if nhap_moi:
        store.publish(session_id, {"type": "orders_imported", "data": {"count": nhap_moi}})
    tat_ca_loi = loi + ngoai_khung
    return OrderImportOut(
        nhap_moi=nhap_moi,
        trung_bo_qua=trung,
        loi=tat_ca_loi[:50],
        tong_loi=len(tat_ca_loi),
        ngoai_khung=len(ngoai_khung),
        tong_don=len(tat_ca),
        tong_doanh_thu=sum(_so(r.get("gross")) for r in tat_ca),
    )
