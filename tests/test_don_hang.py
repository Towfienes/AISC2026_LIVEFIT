"""Ghi đơn hàng — tay và nhập CSV (kiểm toán 17/09/2026).

Trước ngày này bảng ``order_event`` tồn tại nhưng không đường API nào ghi vào,
nên tín hiệu "đối soát doanh thu" vĩnh viễn THIẾU và biến phụ số đơn/GMV của
tiền đăng ký không kiểm chứng được.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.routes.orders import _so_tien, _thoi_diem
from livelift.api.store import InMemoryStore
from livelift.config import get_settings


@pytest.fixture
def client_store(monkeypatch):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    store = InMemoryStore()
    with TestClient(create_app(store=store)) as client:
        yield client, store
    get_settings.cache_clear()


def _phien_da_phat(client: TestClient) -> str:
    r = client.post("/sessions", json={"platform": "facebook", "planned_duration_min": 30})
    sid = r.json()["session_id"]
    assert client.post(f"/sessions/{sid}/schedule", json={"seed": 7}).status_code == 200
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    return sid


def test_ghi_mot_don_va_gan_khoi_theo_thoi_diem_dat(client_store):
    client, store = client_store
    client.post(
        "/products", json={"product_id": "p1", "name": "Son", "cost": 50, "price": 150, "stock": 5}
    )
    sid = _phien_da_phat(client)
    r = client.post(
        f"/sessions/{sid}/orders",
        json={"order_id": "DH-1", "product_id": "p1", "qty": 2, "gross": 300000},
    )
    assert r.status_code == 200, r.text
    assert r.json()["block_id"] is not None, "đơn đặt trong lúc live phải rơi vào một khối"

    tong = client.get(f"/sessions/{sid}/orders").json()
    assert tong["tong_don"] == 1
    assert tong["tong_doanh_thu"] == 300000

    signals = client.get(f"/sessions/{sid}/signals").json()
    assert "1 đơn" in str(signals)


def test_ghi_lai_cung_ma_don_khong_nhan_doi(client_store):
    client, _ = client_store
    sid = _phien_da_phat(client)
    for _ in range(3):
        client.post(f"/sessions/{sid}/orders", json={"order_id": "DH-7", "gross": 99000})
    assert client.get(f"/sessions/{sid}/orders").json()["tong_don"] == 1


def test_ma_san_pham_khong_co_trong_danh_muc_bi_tu_choi(client_store):
    client, _ = client_store
    sid = _phien_da_phat(client)
    r = client.post(f"/sessions/{sid}/orders", json={"product_id": "khong-co", "gross": 1})
    assert r.status_code == 422
    assert "danh mục" in r.json()["detail"]


def test_ma_don_cua_phien_khac_bi_tu_choi(client_store):
    client, _ = client_store
    a, b = _phien_da_phat(client), _phien_da_phat(client)
    dau = client.post(f"/sessions/{a}/orders", json={"order_id": "X", "gross": 1})
    assert dau.status_code == 200
    r = client.post(f"/sessions/{b}/orders", json={"order_id": "X", "gross": 1})
    assert r.status_code == 422


def test_nhap_csv_dinh_dang_viet_nam_va_nhap_lai_khong_trung(client_store):
    client, _ = client_store
    sid = _phien_da_phat(client)
    gio = (datetime.now(UTC) + timedelta(hours=7)).strftime("%d/%m/%Y %H:%M")
    csv_text = (
        "﻿Mã đơn hàng,Thời gian đặt hàng,Số lượng,Tổng tiền,Tên người mua,SĐT\n"
        f'DH-100,{gio},1,"1.250.000 ₫",Nguyễn Văn A,0912345678\n'
        f"DH-101,{gio},2,250000,Trần B,0987654321\n"
        "DH-102,khong-phai-ngay,1,1000,C,0900000000\n"
    )
    r = client.post(f"/sessions/{sid}/orders/import", json={"csv": csv_text})
    assert r.status_code == 200, r.text
    kq = r.json()
    assert kq["nhap_moi"] == 2
    assert kq["tong_doanh_thu"] == 1_500_000
    assert [loi["dong"] for loi in kq["loi"]] == [4]
    assert kq["tong_loi"] == 1
    # Không lặp lại nội dung dòng (có tên/SĐT người mua) trong thông báo lỗi.
    assert "0900000000" not in r.text

    lan_hai = client.post(f"/sessions/{sid}/orders/import", json={"csv": csv_text}).json()
    assert lan_hai["nhap_moi"] == 0
    assert lan_hai["trung_bo_qua"] == 2
    assert lan_hai["tong_don"] == 2


def test_csv_thieu_cot_bat_buoc(client_store):
    client, _ = client_store
    sid = _phien_da_phat(client)
    r = client.post(f"/sessions/{sid}/orders/import", json={"csv": "order_id,qty\nA,1\n"})
    assert r.status_code == 422
    assert "thiếu cột" in r.json()["detail"]


@pytest.mark.parametrize(
    ("raw", "so"),
    [
        ("1.250.000 ₫", 1_250_000),
        ("1,250,000", 1_250_000),
        ("125.000", 125_000),
        ("99000", 99_000),
        ("1.234,5", 1234.5),
        ("12.5", 12.5),
    ],
)
def test_doc_so_tien(raw, so):
    assert _so_tien(raw) == so


def test_doc_thoi_diem_gio_viet_nam():
    dt = _thoi_diem("17/09/2026 20:05")
    assert dt.utcoffset() == timedelta(hours=7)
    assert _thoi_diem("2026-09-17T13:05:00Z").utcoffset() == timedelta(0)


def test_don_trong_anh_chup_duoc_chong_trung_sau_khoi_dong_lai():
    kho = InMemoryStore()
    kho.add_order("s1", {"order_id": "A", "ts": datetime.now(UTC), "gross": 1})
    kho2 = InMemoryStore()
    kho2.import_json(kho.export_json())
    kho2.add_order("s1", {"order_id": "A", "ts": datetime.now(UTC), "gross": 1})
    assert len(kho2.list_orders("s1")) == 1


# ---------------------------------------------------------------------------
# Hồi quy kiểm toán 17/09/2026
# ---------------------------------------------------------------------------

GIO_VN_TEST = timezone(timedelta(hours=7))


def _phien_co_khung(store: InMemoryStore, start: datetime, end: datetime | None) -> str:
    sid = str(uuid.uuid4())
    store.create_session(
        {
            "session_id": sid,
            "platform": "facebook",
            "title": "t",
            "mode": "suggest",
            "status": "ended" if end is not None else "live",
            "planned_duration_min": 30,
            "host_id": None,
            "start_ts": start.astimezone(UTC),
            "end_ts": end.astimezone(UTC) if end is not None else None,
            "created_at": start,
            "dry_run": False,
            "is_demo": False,
        }
    )
    return sid


CSV_CA_NGAY = (
    "Mã đơn hàng,Thời gian đặt hàng,Số lượng,Tổng tiền\n"
    "DH-SANG,16/09/2026 10:10,1,100000\n"
    "DH-TOI,16/09/2026 20:10,1,900000\n"
    "DH-DEM,16/09/2026 23:50,1,500000\n"
)


def test_tep_ca_ngay_chi_gan_don_trong_khung_gio_cua_tung_phien(client_store):
    """Hai buổi live cùng ngày, nhập cùng một tệp xuất theo ngày vào cả hai.

    Trước khi sửa: A nhận cả 3 đơn (doanh thu 1.500.000), B bị từ chối cả 3 vì
    mã đơn đã thuộc A — B vĩnh viễn không có đơn của chính mình.
    """
    client, store = client_store
    ngay = datetime(2026, 9, 16, tzinfo=GIO_VN_TEST)
    a = _phien_co_khung(store, ngay.replace(hour=10), ngay.replace(hour=10, minute=30))
    b = _phien_co_khung(store, ngay.replace(hour=20), ngay.replace(hour=20, minute=30))

    ra = client.post(f"/sessions/{a}/orders/import", json={"csv": CSV_CA_NGAY})
    assert ra.status_code == 200, ra.text
    kq_a = ra.json()
    assert kq_a["nhap_moi"] == 1
    assert kq_a["tong_doanh_thu"] == 100_000
    assert kq_a["ngoai_khung"] == 2
    assert kq_a["tong_loi"] == 2
    assert all("ngoài khung giờ" in loi["ly_do"] for loi in kq_a["loi"])

    kq_b = client.post(f"/sessions/{b}/orders/import", json={"csv": CSV_CA_NGAY}).json()
    assert kq_b["nhap_moi"] == 1, kq_b
    assert kq_b["tong_doanh_thu"] == 900_000
    assert not any("phiên khác" in loi["ly_do"] for loi in kq_b["loi"])
    assert [o["order_id"] for o in client.get(f"/sessions/{b}/orders").json()["don"]] == ["DH-TOI"]
    # Đơn 23:50 không thuộc buổi nào: không được lưu ở đâu cả.
    assert all(o["order_id"] != "DH-DEM" for s in (a, b) for o in store.list_orders(s))


def test_don_tre_trong_khoang_dem_sau_khi_tat_live_van_duoc_nhan(client_store):
    client, store = client_store
    ngay = datetime(2026, 9, 16, tzinfo=GIO_VN_TEST)
    a = _phien_co_khung(store, ngay.replace(hour=10), ngay.replace(hour=10, minute=30))
    csv_text = "order_id,ts,gross\nDH-TRE,16/09/2026 10:45,1000\nDH-QUA,16/09/2026 11:15,1000\n"
    kq = client.post(f"/sessions/{a}/orders/import", json={"csv": csv_text}).json()
    assert kq["nhap_moi"] == 1
    assert kq["ngoai_khung"] == 1


def test_mot_don_nhap_tay_ngoai_khung_phien_bi_tu_choi(client_store):
    client, store = client_store
    ngay = datetime(2026, 9, 16, tzinfo=GIO_VN_TEST)
    a = _phien_co_khung(store, ngay.replace(hour=10), ngay.replace(hour=10, minute=30))
    r = client.post(
        f"/sessions/{a}/orders",
        json={"order_id": "DH-X", "gross": 1, "ts_utc": "2026-09-16T20:10:00+07:00"},
    )
    assert r.status_code == 422
    assert "ngoài khung giờ" in r.json()["detail"]
    assert store.list_orders(a) == []


@pytest.mark.parametrize("qty", ["inf", "1e999", "Infinity", "-inf", "nan"])
def test_so_luong_vo_han_la_loi_cua_dong_khong_phai_500(monkeypatch, qty):
    """``int(float("inf"))`` ném OverflowError — trước khi sửa lọt khỏi
    ``except (ValueError, TypeError)`` thành 500 sau khi đã ghi một phần."""
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    store = InMemoryStore()
    with TestClient(create_app(store=store), raise_server_exceptions=False) as client:
        sid = _phien_da_phat(client)
        gio = (datetime.now(UTC) + timedelta(hours=7)).strftime("%d/%m/%Y %H:%M")
        csv_text = f"order_id,ts,qty,gross\nDH-1,{gio},2,1000\nDH-2,{gio},{qty},2000\n"
        r = client.post(f"/sessions/{sid}/orders/import", json={"csv": csv_text})
        assert r.status_code == 200, r.text
        kq = r.json()
        assert kq["nhap_moi"] == 1
        assert [loi["dong"] for loi in kq["loi"]] == [3]
        assert kq["tong_don"] == 1
    get_settings.cache_clear()


# --- Khách không token trên bản trưng bày: không được làm ngập kho -----------


@pytest.fixture
def khach_demo(monkeypatch):
    monkeypatch.setenv("INGEST_TOKEN", "tok-bi-mat")
    monkeypatch.setenv("PUBLIC_DEMO_WRITES", "true")
    get_settings.cache_clear()
    store = InMemoryStore()
    with TestClient(create_app(store=store)) as client:
        r = client.post("/sessions", json={"platform": "facebook", "planned_duration_min": 30})
        assert r.status_code == 200, r.text
        yield client, store, r.json()["session_id"]
    get_settings.cache_clear()


def _csv_nhieu_dong(n: int) -> str:
    dong = [f"{uuid.uuid4().hex},2026-09-17T20:00:00+07:00,1000" for _ in range(n)]
    return "order_id,ts,gross\n" + "\n".join(dong)


def test_khach_khong_token_bi_tran_dong_moi_luot_nhap(khach_demo):
    from livelift.api.routes.orders import MAX_CSV_ROWS_KHACH

    client, store, sid = khach_demo
    r = client.post(
        f"/sessions/{sid}/orders/import", json={"csv": _csv_nhieu_dong(MAX_CSV_ROWS_KHACH + 50)}
    )
    assert r.status_code == 200, r.text
    assert r.json()["nhap_moi"] == MAX_CSV_ROWS_KHACH
    assert len(store.list_orders(sid)) == MAX_CSV_ROWS_KHACH


def test_nhap_don_cua_khach_co_tran_rieng_theo_gio(khach_demo):
    """Trước khi sửa: đường này chung trần 30 lượt/phút của nhóm "ghi", nên một
    địa chỉ ghi được 145.000 đơn trong vài giây."""
    client, store, sid = khach_demo
    tran = get_settings().order_import_rate_limit_per_hour
    ma = []
    for _ in range(tran + 3):
        r = client.post(f"/sessions/{sid}/orders/import", json={"csv": _csv_nhieu_dong(5)})
        ma.append(r.status_code)
    assert ma[:tran] == [200] * tran
    assert set(ma[tran:]) == {429}
    assert "giờ" in r.json()["detail"]
    assert len(store.list_orders(sid)) == 5 * tran
    # Trần theo giờ của nhập đơn là bộ đếm RIÊNG: một lượt ghi thường vẫn qua.
    assert client.post(f"/sessions/{sid}/orders", json={"gross": 1}).status_code == 200


def test_nguoi_van_hanh_co_token_khong_bi_tran_cua_khach(khach_demo):
    from livelift.api.routes.orders import MAX_CSV_ROWS_KHACH

    client, store, sid = khach_demo
    r = client.post(
        f"/sessions/{sid}/orders/import",
        json={"csv": _csv_nhieu_dong(MAX_CSV_ROWS_KHACH + 10)},
        headers={"Authorization": "Bearer tok-bi-mat"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["nhap_moi"] == MAX_CSV_ROWS_KHACH + 10


def test_khach_khong_vuot_tran_tong_don_moi_phien(khach_demo, monkeypatch):
    import livelift.api.routes.orders as orders

    monkeypatch.setattr(orders, "MAX_DON_PHIEN_KHACH", 8)
    client, store, sid = khach_demo
    kq = client.post(f"/sessions/{sid}/orders/import", json={"csv": _csv_nhieu_dong(12)}).json()
    assert kq["nhap_moi"] == 8
    assert "tối đa 8 đơn" in kq["loi"][-1]["ly_do"]
    r = client.post(f"/sessions/{sid}/orders", json={"gross": 1})
    assert r.status_code == 429
    assert len(store.list_orders(sid)) == 8
