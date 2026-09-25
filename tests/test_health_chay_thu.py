"""``/health`` đếm phiên CHẠY THỬ riêng — để web không gộp chạy thử vào "thật".

Kiểm toán 25/09/2026 (runtime.md 3.2, P1). Sau một lần tập dượt bằng wizard
("Chạy thử"), ``/health`` trả ``mode_counts.real=3`` — một phiên đã huỷ và hai
phiên chạy thử, KHÔNG có phiên thí nghiệm thật nào — và chip trên web đổi thành
"KHO: THẬT + MẪU". Hồ sơ nói "0 phiên thí nghiệm thật"; chỉ cần tập dượt một lần
trước mặt giám khảo là màn hình nói ngược lại.

Hợp đồng C-4 (``/health``: chỉ THÊM khoá, không đổi tên hay xoá): ``demo`` và
``real`` giữ nguyên tên và nghĩa; thêm khoá con ``mode_counts.dry_run`` = số
phiên chạy thử (không phải demo), NẰM TRONG ``real``. Phiên thật không chạy thử
là ``real - dry_run``. Người đọc cũ dùng ``.get("demo")``/``.get("real")``
(``scripts/kiem_tra_truoc_demo.py``, ``scripts/chay_local.py``, ``ModeChip``)
không bị ảnh hưởng.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore


@pytest.fixture
def client():
    with TestClient(create_app(store=InMemoryStore())) as c:
        yield c


def _tao(client, **kw) -> str:
    body = {"platform": "youtube", "mode": "auto", "planned_duration_min": 30, **kw}
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def test_kho_trong_dem_chay_thu_bang_0(client):
    body = client.get("/health").json()
    assert body["mode_counts"] == {"demo": 0, "real": 0, "dry_run": 0, "da_huy": 0}


def test_chay_thu_duoc_dem_rieng_ben_trong_real(client):
    """Đúng tình huống runtime.md 3.2: tập dượt hai lần, huỷ một nháp."""
    _tao(client, dry_run=True)
    _tao(client, dry_run=True)
    nhap = _tao(client)
    assert client.post(f"/sessions/{nhap}/cancel").status_code == 200

    body = client.get("/health").json()
    mc = body["mode_counts"]
    assert mc["real"] == 3, "nghĩa cũ giữ nguyên: dry_run vẫn nằm trong real (C-4)"
    assert mc["dry_run"] == 2, "web phải trừ được phiên chạy thử ra khỏi 'thật'"
    assert mc["real"] - mc["dry_run"] == 1
    assert "chạy thử" in body["mode_note"], "câu giải thích phải nói có phiên chạy thử"


def test_phien_demo_khong_bao_gio_dem_la_chay_thu(client):
    client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 40})
    _tao(client, dry_run=True)
    _tao(client)

    mc = client.get("/health").json()["mode_counts"]
    assert mc == {"demo": 2, "real": 2, "dry_run": 1, "da_huy": 0}
    assert 0 <= mc["dry_run"] <= mc["real"]


def test_kho_chet_thi_khong_dem_duoc_gi(monkeypatch):
    """Không đếm được thì mode_counts là None — không bịa số 0 cho khoá mới."""
    from livelift.api import service
    from livelift.api.store import StoreUnavailableError

    def _chet(_store):
        raise StoreUnavailableError("kho chết (test)")

    monkeypatch.setattr(service, "data_mode", _chet)
    with TestClient(create_app(store=InMemoryStore())) as c:
        body = c.get("/health").json()
    assert body["mode"] == "unknown"
    assert body["mode_counts"] is None
