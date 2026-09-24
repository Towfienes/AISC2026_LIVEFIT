"""Bộ thu bật TRƯỚC giờ phát: API phải nói thật chuyện gì đang xảy ra.

Kiểm toán 25/09/2026 (runtime.md 3.5, P2). Wizard bước 4 viết "Bật trước giờ
phát cũng được — bộ thu sẽ chờ buổi live bắt đầu". Thực tế:

* bộ thu YouTube/Facebook chờ NỀN TẢNG báo buổi live đang phát — nó không chờ
  nút "Bắt đầu phát sóng" của LiveLift, nên nếu kênh đã lên sóng mà phiên
  LiveLift còn ``scheduled`` thì bình luận vẫn được ghi;
* nguồn Mô phỏng không có "buổi live" nào để chờ: bật là phát kịch bản ngay
  (phiên 80da23ab: 78 bình luận ghi khi ``status=scheduled``, ``start_ts=null``).

Bình luận ghi trước giờ phát không thuộc khối nào (không vào ước lượng), nên
không có số liệu nào sai — nhưng lời hứa trên giao diện sai, và với ``x10`` kịch
bản bị "đốt" ngay lúc soát checklist. Cách an toàn nhất, không đổi hành vi thu
(test ``tests/test_ingest_mo_phong.py`` dựa vào việc thu ngay trên phiên chưa
phát): API THÊM trường ``ghi_chu_truoc_len_song`` vào trạng thái bộ thu, và câu
mô tả nguồn Mô phỏng trong ``/platforms`` nói rõ "phát NGAY khi bật".
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import get_settings


@pytest.fixture
def ung_dung(monkeypatch):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    store = InMemoryStore()
    with TestClient(create_app(store=store)) as client:
        yield client, store
    get_settings.cache_clear()


def _cho_dung(client, sid, timeout=20.0) -> dict:
    han = time.monotonic() + timeout
    while True:
        st = client.get(f"/sessions/{sid}/ingest").json()
        if not st["running"]:
            return st
        assert time.monotonic() < han, f"bộ thu không dừng: {st}"
        time.sleep(0.02)


def test_mo_phong_bat_truoc_gio_phat_co_ghi_chu_trung_thuc(ung_dung):
    client, store = ung_dung
    sid = client.post(
        "/sessions", json={"platform": "youtube", "planned_duration_min": 30, "dry_run": True}
    ).json()["session_id"]

    r = client.post(
        f"/sessions/{sid}/ingest", json={"platform": "mo_phong", "source": "ngan x1000"}
    )
    assert r.status_code == 202, r.text
    assert r.json()["ghi_chu_truoc_len_song"], "phiên chưa phát — phải nói ngay khi bật"

    st = _cho_dung(client, sid)
    assert st["comments_posted"] > 0, "hành vi thu giữ nguyên (test cũ dựa vào nó)"
    ghi_chu = st["ghi_chu_truoc_len_song"]
    assert ghi_chu, "đã ghi bình luận khi phiên chưa lên sóng mà API im lặng"
    assert "chưa lên sóng" in ghi_chu
    assert "không thuộc khối" in ghi_chu, "phải nói hệ quả: không vào ước lượng"
    assert "ngay" in ghi_chu.lower(), "nguồn Mô phỏng phát NGAY — không chờ nút phát sóng"
    assert all(c.get("block_id") is None for c in store.list_comments(sid))


def test_phien_dang_phat_khong_co_ghi_chu(ung_dung):
    client, _ = ung_dung
    sid = client.post(
        "/sessions", json={"platform": "youtube", "planned_duration_min": 30, "dry_run": True}
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 3})
    assert client.post(f"/sessions/{sid}/start").status_code == 200

    r = client.post(
        f"/sessions/{sid}/ingest", json={"platform": "mo_phong", "source": "ngan x1000"}
    )
    assert r.status_code == 202, r.text
    st = _cho_dung(client, sid)
    assert st["ghi_chu_truoc_len_song"] is None


def test_chua_bat_bo_thu_khong_co_ghi_chu(ung_dung):
    client, _ = ung_dung
    sid = client.post("/sessions", json={"platform": "youtube", "planned_duration_min": 30}).json()[
        "session_id"
    ]
    assert client.get(f"/sessions/{sid}/ingest").json()["ghi_chu_truoc_len_song"] is None


def test_platforms_noi_mo_phong_phat_ngay_khi_bat(ung_dung):
    client, _ = ung_dung
    muc = {p["platform"]: p for p in client.get("/platforms").json()}
    note = muc["mo_phong"]["note"]
    assert "ngay khi bật" in note.lower(), note
    for p in ("youtube", "facebook"):
        if p in muc:
            assert "nút" in muc[p]["note"] or "Bắt đầu phát sóng" in muc[p]["note"], (
                f"{p}: phải nói bộ thu chờ NỀN TẢNG lên sóng, không chờ nút của LiveLift"
            )
