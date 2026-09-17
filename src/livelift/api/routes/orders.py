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
* Mức bảo vệ ``demo``: phiên THẬT cần token ghi, khách của bản trưng bày chỉ
  ghi được vào phiên mẫu.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from livelift.api import service
from livelift.api.auth import cho_phep_demo
from livelift.api.service import StoreDep

router = APIRouter()

GIO_VN = timezone(timedelta(hours=7))
MAX_CSV_BYTES = 2_000_000
MAX_CSV_ROWS = 5000


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


def _ghi_don(
    store: Any, session: dict[str, Any], body: OrderIn, da_co: set[str]
) -> tuple[dict[str, Any], bool]:
    """Ghi một đơn. Trả (bản ghi, là_đơn_mới). ``da_co`` = mã đơn đã có của
    phiên, được cập nhật tại chỗ (nhập 5.000 dòng không đọc lại kho 5.000 lần)."""
    session_id = session["session_id"]
    if body.product_id and store.get_product(body.product_id) is None:
        raise ValueError(f"Mã sản phẩm {body.product_id!r} không có trong danh mục")
    ts = (body.ts_utc or service.now_utc()).astimezone(UTC)
    block = _khoi_cua_thoi_diem(session, store.get_blocks(session_id), ts)
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


@cho_phep_demo
@router.post("/sessions/{session_id}/orders", response_model=OrderOut)
def create_order(session_id: str, body: OrderIn, store: StoreDep) -> OrderOut:
    session = service.require_session(store, session_id)
    da_co = {str(o["order_id"]) for o in store.list_orders(session_id)}
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
def import_orders(session_id: str, body: OrderImportIn, store: StoreDep) -> OrderImportOut:
    session = service.require_session(store, session_id)
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
    da_co = {str(o["order_id"]) for o in store.list_orders(session_id)}
    for so_dong, dong in enumerate(doc, start=2):
        if not any(c.strip() for c in dong):
            continue
        if so_dong - 1 > MAX_CSV_ROWS:
            loi.append(OrderImportLoi(dong=so_dong, ly_do=f"vượt trần {MAX_CSV_ROWS} dòng"))
            break

        def o(khoa: str, dong: list[str] = dong) -> str:
            i = vi_tri.get(khoa)
            return dong[i].strip() if i is not None and i < len(dong) else ""

        try:
            don = OrderIn(
                order_id=o("order_id") or None,
                ts_utc=_thoi_diem(o("ts")),
                product_id=o("product_id") or None,
                qty=int(float(o("qty"))) if o("qty") else 1,
                gross=_so_tien(o("gross")),
                fees=_so_tien(o("fees")) if o("fees") else 0.0,
            )
            _, moi = _ghi_don(store, session, don, da_co)
        except (ValueError, TypeError) as exc:
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
    return OrderImportOut(
        nhap_moi=nhap_moi,
        trung_bo_qua=trung,
        loi=loi[:50],
        tong_don=len(tat_ca),
        tong_doanh_thu=sum(_so(r.get("gross")) for r in tat_ca),
    )
