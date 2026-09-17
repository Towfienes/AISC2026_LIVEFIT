"""Địa chỉ thật của người gọi sau Caddy — hồi quy kiểm toán 17/09/2026.

Hai lỗi trước khi sửa:

* ``/r/{code}`` băm ``request.client.host`` — sau Caddy đó là địa chỉ của
  CADDY, nên mọi người xem chung một vân tay và luật refractory/volume-cap
  đánh dấu click hợp lệ của người thứ hai trở đi là vô hiệu. Biến kết quả
  chính của thí nghiệm bị đếm thiếu một cách có hệ thống.
* ``X-Forwarded-For`` được tin vô điều kiện: ai gọi thẳng vào cổng API cũng
  tự chọn được địa chỉ của mình và phá trần tần suất.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from livelift.api.auth import dia_chi_goi, mang_proxy_tin_cay
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import get_settings


def _conn(host: str | None, xff: str | None = None) -> SimpleNamespace:
    headers = {"x-forwarded-for": xff} if xff is not None else {}
    client = SimpleNamespace(host=host) if host is not None else None
    return SimpleNamespace(client=client, headers=headers)


@pytest.fixture(autouse=True)
def _cau_hinh_sach():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_goi_truc_tiep_khong_tin_header_tu_bia():
    assert dia_chi_goi(_conn("203.0.113.7", "1.2.3.4")) == "203.0.113.7"


def test_sau_caddy_lay_dia_chi_nguoi_xem():
    # Caddy (172.18.0.3, mạng Docker) nối địa chỉ nó nhận gói tin vào cuối.
    assert dia_chi_goi(_conn("172.18.0.3", "198.51.100.20")) == "198.51.100.20"


def test_sau_caddy_bo_qua_phan_tu_dau_do_khach_bia():
    assert dia_chi_goi(_conn("172.18.0.3", "6.6.6.6, 198.51.100.20")) == "198.51.100.20"


def test_nhieu_chang_proxy_tin_cay_duoc_bo_qua():
    assert dia_chi_goi(_conn("172.18.0.3", "198.51.100.20, 10.0.0.9")) == "198.51.100.20"


def test_proxy_khong_gui_header_thi_dung_dia_chi_proxy():
    assert dia_chi_goi(_conn("127.0.0.1")) == "127.0.0.1"


def test_khong_co_client():
    assert dia_chi_goi(_conn(None)) == "khong-ro"


def test_cidr_sai_bi_bo_qua_khong_lam_sap():
    mang = mang_proxy_tin_cay("khong-phai-cidr, 10.0.0.0/8")
    assert len(mang) == 1


def test_danh_sach_rong_thi_khong_tin_ai(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "")
    get_settings.cache_clear()
    assert dia_chi_goi(_conn("172.18.0.3", "198.51.100.20")) == "172.18.0.3"


def _tao_link(client: TestClient) -> tuple[str, str]:
    client.post(
        "/products",
        json={"product_id": "p-proxy", "name": "Áo", "cost": 50, "price": 120, "stock": 9},
    )
    phien = client.post("/sessions", json={"platform": "youtube", "planned_duration_min": 90})
    sid = phien.json()["session_id"]
    link = client.post(
        "/shortlinks",
        json={"product_id": "p-proxy", "session_id": sid, "target_url": "https://shop.vn/ao"},
    )
    return link.json()["code"], sid


def test_hai_nguoi_xem_sau_caddy_la_hai_van_tay_khac_nhau():
    """Trước khi sửa: hai người xem khác nhau sau cùng một Caddy băm ra CÙNG
    một vân tay."""
    store = InMemoryStore()
    app = create_app(store=store)
    with TestClient(app, client=("172.18.0.3", 50000), follow_redirects=False) as client:
        code, sid = _tao_link(client)
        ua = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) Mobile"}
        for nguoi in ("198.51.100.20", "198.51.100.21"):
            r = client.get(f"/r/{code}", headers={**ua, "X-Forwarded-For": nguoi})
            assert r.status_code == 302
    clicks = store.list_clicks(sid)
    assert len(clicks) == 2
    assert clicks[0]["dedup_hash"] != clicks[1]["dedup_hash"]
