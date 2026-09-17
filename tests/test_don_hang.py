"""Ghi đơn hàng — tay và nhập CSV (kiểm toán 17/09/2026).

Trước ngày này bảng ``order_event`` tồn tại nhưng không đường API nào ghi vào,
nên tín hiệu "đối soát doanh thu" vĩnh viễn THIẾU và biến phụ số đơn/GMV của
tiền đăng ký không kiểm chứng được.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
