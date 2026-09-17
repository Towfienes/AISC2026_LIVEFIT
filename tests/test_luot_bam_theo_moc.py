"""Lượt bấm theo mốc 30 giây phải đến từ bảng click — hồi quy kiểm toán 17/09/2026.

Trước khi sửa, ``POST /sessions/{id}/ticks`` luôn ghi ``click_count = 0`` và
``GET /sessions/{id}/ticks`` trả nguyên số đó. Link đo ``/r/{code}`` ghi vào bảng
click, không vào tick, nên ô "Lượt bấm / phút" và biểu đồ nhịp trên Bàn trợ live
luôn bằng 0 trong mọi buổi live thật dù click vẫn được đo đúng. Chỉ phiên demo có
số, vì máy sinh demo tự điền ``click_count``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import get_settings

UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Mobile Safari/537.36"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    with TestClient(create_app(store=InMemoryStore()), follow_redirects=False) as c:
        yield c
    get_settings.cache_clear()


def _phien_dang_phat_co_link(client: TestClient) -> tuple[str, str]:
    client.post(
        "/products",
        json={"product_id": "p-bam", "name": "Son", "cost": 50, "price": 120, "stock": 9},
    )
    sid = client.post("/sessions", json={"platform": "youtube", "planned_duration_min": 90}).json()[
        "session_id"
    ]
    assert client.post(f"/sessions/{sid}/schedule", json={"seed": 3}).status_code == 200
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    code = client.post(
        "/shortlinks",
        json={"product_id": "p-bam", "session_id": sid, "target_url": "https://shop.vn/son"},
    ).json()["code"]
    return sid, code


def _bam(client: TestClient, code: str, nguoi: int) -> None:
    # Mỗi "người xem" một User-Agent riêng ⇒ vân tay riêng ⇒ không dính luật
    # refractory của click_validity.
    r = client.get(f"/r/{code}", headers={"User-Agent": f"{UA} nguoi-{nguoi}"})
    assert r.status_code == 302


def test_tick_ghi_so_lan_bam_that_cua_moc(client):
    sid, code = _phien_dang_phat_co_link(client)
    _bam(client, code, 1)
    _bam(client, code, 2)
    tick = client.post(f"/sessions/{sid}/ticks", json={"viewers": 12})
    assert tick.status_code == 200
    assert tick.json()["click_count"] == 2


def test_doc_lai_tick_cong_ca_click_den_sau_khi_tick_da_ghi(client):
    sid, code = _phien_dang_phat_co_link(client)
    client.post(f"/sessions/{sid}/ticks", json={"viewers": 12})
    _bam(client, code, 1)
    _bam(client, code, 2)
    _bam(client, code, 3)
    ticks = client.get(f"/sessions/{sid}/ticks").json()
    assert sum(t["click_count"] for t in ticks) == 3


def test_click_vo_hieu_khong_duoc_dem(client):
    sid, code = _phien_dang_phat_co_link(client)
    _bam(client, code, 1)
    # Cùng người bấm lại ngay ⇒ click_validity gắn cờ vô hiệu (refractory).
    _bam(client, code, 1)
    ticks = client.get(f"/sessions/{sid}/ticks")
    if not ticks.json():
        client.post(f"/sessions/{sid}/ticks", json={"viewers": 5})
        ticks = client.get(f"/sessions/{sid}/ticks")
    assert sum(t["click_count"] for t in ticks.json()) == 1
