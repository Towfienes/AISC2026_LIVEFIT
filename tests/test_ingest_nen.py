"""Bộ thu bình luận chạy nền trong API — kiểm toán 17/09/2026.

Trước ngày này bộ thu chỉ chạy được bằng lệnh terminal, nên mọi phiên tạo trên
web hiện "THIẾU nguồn". Các test ở đây khoá hành vi của vòng đời mới bằng client
nền tảng GIẢ (không mạng): thu và lọc PII, chờ lên sóng, thử lại lỗi tạm thời,
dừng ngay khi lỗi cấu hình, tự dừng khi phiên đóng, tự nối lại sau khởi động lại,
và các endpoint điều khiển từ trình duyệt.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from livelift.api.ingest_jobs import (
    IngestConflictError,
    IngestManager,
    chuan_hoa_nguon,
    muc_san_sang_nen_tang,
    phan_loai_loi,
)
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import get_settings
from livelift.ingest.base import RawComment, RawTick

NHANH = {
    "restart_base_s": 0.01,
    "restart_cap_s": 0.02,
    "wait_for_live_s": 0.01,
    "watch_every_s": 0.02,
}


def _phien(store: InMemoryStore, status: str = "live") -> str:
    sid = str(uuid.uuid4())
    now = datetime.now(UTC)
    store.create_session(
        {
            "session_id": sid,
            "platform": "youtube",
            "title": "test",
            "mode": "suggest",
            "status": status,
            "planned_duration_min": 90,
            "host_id": None,
            "start_ts": now if status == "live" else None,
            "end_ts": None,
            "created_at": now,
            "dry_run": False,
            "is_demo": False,
        }
    )
    return sid


class KichBan:
    """Trạng thái dùng chung giữa các lần tạo client (supervisor tạo client mới
    sau mỗi lần thử lại)."""

    def __init__(
        self,
        texts: list[str],
        *,
        chua_phat: int = 0,
        loi_tam_thoi: int = 0,
        loi_cau_hinh: bool = False,
        het_luong: bool = True,
    ) -> None:
        self.texts = texts
        self.chua_phat = chua_phat
        self.loi_tam_thoi = loi_tam_thoi
        self.loi_cau_hinh = loi_cau_hinh
        self.het_luong = het_luong
        self.so_client = 0
        self.dong = 0

    def factory(self, platform: str) -> ClientGia:
        self.so_client += 1
        return ClientGia(self)


class ClientGia:
    def __init__(self, kb: KichBan) -> None:
        self.kb = kb
        self.last_error: str | None = None

    async def iter_comments(self, source_id: str):
        kb = self.kb
        if kb.loi_cau_hinh:
            raise RuntimeError(
                "LỖI YouTube API (HTTP 403): API key không hợp lệ hoặc quota trong ngày đã cạn."
            )
        if kb.chua_phat > 0:
            kb.chua_phat -= 1
            raise RuntimeError(f"video {source_id} has no active live chat (not live?)")
        if kb.loi_tam_thoi > 0:
            kb.loi_tam_thoi -= 1
            raise ConnectionError("mất mạng")
        for i, text in enumerate(kb.texts):
            await asyncio.sleep(0)
            yield RawComment(
                platform="youtube", ext_id=f"c-{i}", ts_utc=datetime.now(UTC), text=text
            )
        if not kb.het_luong:
            await asyncio.sleep(3600)

    async def iter_viewers(self, source_id: str):
        yield RawTick(platform="youtube", ts_utc=datetime.now(UTC), viewers=42)
        await asyncio.sleep(3600)

    async def aclose(self) -> None:
        self.kb.dong += 1


async def _cho(dieu_kien, timeout: float = 3.0) -> None:
    han = time.monotonic() + timeout
    while not dieu_kien():
        if time.monotonic() > han:
            raise AssertionError("hết giờ chờ điều kiện")
        await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# Vòng đời
# ---------------------------------------------------------------------------


def test_thu_binh_luan_loc_pii_va_dung_khi_nguon_ket_thuc():
    store = InMemoryStore()
    sid = _phien(store)
    kb = KichBan(["chốt 2 cái", "gọi em 0912 345 678 nha"])

    async def chay():
        m = IngestManager(store, client_factory=kb.factory, **NHANH)
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        await _cho(lambda: not job.dang_chay)
        return job

    job = asyncio.run(chay())
    assert job.state == "nguon_ket_thuc"
    texts = [c["text_scrubbed"] for c in store.list_comments(sid)]
    assert len(texts) == 2
    assert all("0912" not in t for t in texts), "số điện thoại phải bị lọc trước khi lưu"
    assert job.trang_thai()["comments_posted"] == 2
    assert kb.dong >= 1, "client phải được đóng"


def test_cho_len_song_khong_tinh_la_lan_thu_lai():
    store = InMemoryStore()
    sid = _phien(store, status="planned")
    kb = KichBan(["xin giá"], chua_phat=3)

    async def chay():
        m = IngestManager(store, client_factory=kb.factory, **NHANH)
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        await _cho(lambda: not job.dang_chay)
        return job

    job = asyncio.run(chay())
    assert job.state == "nguon_ket_thuc"
    assert job.restarts == 0
    assert len(store.list_comments(sid)) == 1


def test_loi_tam_thoi_duoc_thu_lai():
    store = InMemoryStore()
    sid = _phien(store)
    kb = KichBan(["còn size M không"], loi_tam_thoi=2)

    async def chay():
        m = IngestManager(store, client_factory=kb.factory, **NHANH)
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        await _cho(lambda: not job.dang_chay)
        return job

    job = asyncio.run(chay())
    assert job.restarts == 2
    assert job.state == "nguon_ket_thuc"
    assert len(store.list_comments(sid)) == 1


def test_loi_cau_hinh_dung_ngay_khong_dot_quota():
    store = InMemoryStore()
    sid = _phien(store)
    kb = KichBan([], loi_cau_hinh=True)

    async def chay():
        m = IngestManager(store, client_factory=kb.factory, **NHANH)
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        await _cho(lambda: not job.dang_chay)
        return job

    job = asyncio.run(chay())
    assert job.state == "loi"
    assert kb.so_client == 1, "lỗi cấu hình không được thử lại"
    assert "API key" in (job.last_error or "")


def test_vuot_so_lan_thu_lai_thi_bao_loi():
    store = InMemoryStore()
    sid = _phien(store)
    kb = KichBan([], loi_tam_thoi=99)

    async def chay():
        m = IngestManager(store, client_factory=kb.factory, max_restarts=3, **NHANH)
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        await _cho(lambda: not job.dang_chay)
        return job

    job = asyncio.run(chay())
    assert job.state == "loi"
    assert "thử lại 3 lần" in (job.last_error or "")


def test_tu_dung_khi_phien_ket_thuc():
    store = InMemoryStore()
    sid = _phien(store)
    kb = KichBan(["hello"], het_luong=False)

    async def chay():
        m = IngestManager(store, client_factory=kb.factory, **NHANH)
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        await _cho(lambda: job.trang_thai()["comments_posted"] == 1)
        store.update_session(sid, {"status": "ended", "end_ts": datetime.now(UTC)})
        await _cho(lambda: not job.dang_chay)
        return job

    job = asyncio.run(chay())
    assert job.state == "phien_ket_thuc"
    assert job.trang_thai()["ticks_posted"] == 1
    assert kb.dong == 1


def test_tat_bang_tay_va_khong_bat_trung():
    store = InMemoryStore()
    sid = _phien(store)
    kb = KichBan(["a"], het_luong=False)

    async def chay():
        m = IngestManager(store, client_factory=kb.factory, **NHANH)
        m.start(sid, "youtube", "dQw4w9WgXcQ")
        with pytest.raises(IngestConflictError):
            m.start(sid, "youtube", "dQw4w9WgXcQ")
        return await m.stop(sid)

    job = asyncio.run(chay())
    assert job is not None
    assert job.state == "da_dung"


def test_tu_noi_lai_sau_khi_api_khoi_dong_lai(tmp_path):
    store = InMemoryStore()
    sid_live = _phien(store)
    sid_dong = _phien(store)
    tep = tmp_path / "ingest.json"
    kb = KichBan(["a"], het_luong=False)

    async def lan_dau():
        m = IngestManager(store, client_factory=kb.factory, state_path=tep, **NHANH)
        m.start(sid_live, "youtube", "dQw4w9WgXcQ")
        m.start(sid_dong, "youtube", "dQw4w9WgXcQ")
        await asyncio.sleep(0.05)
        await m.shutdown()  # tắt API: KHÔNG xoá khỏi tệp trạng thái

    asyncio.run(lan_dau())
    assert {m["session_id"] for m in json.loads(tep.read_text(encoding="utf-8"))} == {
        sid_live,
        sid_dong,
    }
    store.update_session(sid_dong, {"status": "ended", "end_ts": datetime.now(UTC)})

    async def lan_hai():
        m = IngestManager(store, client_factory=kb.factory, state_path=tep, **NHANH)
        so = await m.resume()
        dang_chay = [j.session_id for j in m.all() if j.dang_chay]
        await m.shutdown()
        return so, dang_chay

    so, dang_chay = asyncio.run(lan_hai())
    assert so == 1
    assert dang_chay == [sid_live]


# ---------------------------------------------------------------------------
# Hàm thuần
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nguon", "id_mong_doi"),
    [
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"),
    ],
)
def test_chuan_hoa_link_youtube(nguon, id_mong_doi):
    assert chuan_hoa_nguon("youtube", nguon) == id_mong_doi


def test_chuan_hoa_nguon_bao_loi_tieng_viet():
    with pytest.raises(ValueError, match="Không nhận ra video YouTube"):
        chuan_hoa_nguon("youtube", "https://www.youtube.com/@kenhcuatoi")
    assert chuan_hoa_nguon("facebook", "") == ""
    assert chuan_hoa_nguon("facebook", "https://www.facebook.com/page/videos/123456/") == "123456"
    with pytest.raises(ValueError):
        chuan_hoa_nguon("shopee", "abc")


def test_phan_loai_loi():
    assert phan_loai_loi(RuntimeError("video x has no active live chat (not live?)")) == "chua_phat"
    assert phan_loai_loi(RuntimeError("Thiếu danh tính Shopee trong .env: X")) == "cau_hinh"
    assert phan_loai_loi(ConnectionError("x")) == "tam_thoi"


def test_muc_san_sang_khong_bao_gio_tra_gia_tri_khoa(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "BI-MAT-YT-123")
    monkeypatch.setenv("FACEBOOK_PAGE_ACCESS_TOKEN", "BI-MAT-FB-456")
    get_settings.cache_clear()
    try:
        ds = muc_san_sang_nen_tang(get_settings())
    finally:
        get_settings.cache_clear()
    text = json.dumps(ds, ensure_ascii=False)
    assert "BI-MAT" not in text
    theo_ten = {d["platform"]: d for d in ds}
    assert theo_ten["youtube"]["ready"] is True
    assert theo_ten["facebook"]["missing"] == ["FACEBOOK_PAGE_ID"]
    assert theo_ten["tiktok"]["mode"] == "khong_ho_tro"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def ung_dung(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "khoa-thu")
    monkeypatch.setenv("INGEST_YOUTUBE_BACKEND", "api")
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    kb = KichBan(["chốt đơn", "ship HN bao lâu"], het_luong=False)
    store = InMemoryStore()
    app = create_app(store=store, ingest_client_factory=kb.factory)
    with TestClient(app) as client:
        yield client, store, kb
    get_settings.cache_clear()


def _tao_phien(client: TestClient, platform: str = "youtube") -> str:
    r = client.post("/sessions", json={"platform": platform, "planned_duration_min": 90})
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def test_endpoint_bat_xem_tat_bo_thu(ung_dung):
    client, store, _ = ung_dung
    sid = _tao_phien(client)
    assert client.get(f"/sessions/{sid}/ingest").json()["state"] == "chua_bat"

    r = client.post(f"/sessions/{sid}/ingest", json={"source": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 202, r.text
    assert r.json()["source_id"] == "dQw4w9WgXcQ"

    han = time.monotonic() + 3
    while client.get(f"/sessions/{sid}/ingest").json()["comments_posted"] < 2:
        assert time.monotonic() < han, "bộ thu không ghi được bình luận"
        time.sleep(0.02)
    assert len(store.list_comments(sid)) == 2

    trung = client.post(f"/sessions/{sid}/ingest", json={"source": "dQw4w9WgXcQ"})
    assert trung.status_code == 409

    tat = client.post(f"/sessions/{sid}/ingest/stop")
    assert tat.status_code == 200
    assert tat.json()["state"] == "da_dung"


def test_endpoint_tu_choi_nen_tang_khong_ho_tro_va_link_sai(ung_dung):
    client, _, _ = ung_dung
    sid = _tao_phien(client, platform="tiktok")
    r = client.post(f"/sessions/{sid}/ingest", json={"source": "x"})
    assert r.status_code == 422
    assert "TikTok" in r.json()["detail"]

    sid2 = _tao_phien(client)
    r = client.post(f"/sessions/{sid2}/ingest", json={"source": "https://example.com"})
    assert r.status_code == 422
    assert "YouTube" in r.json()["detail"]


def test_endpoint_bao_thieu_khoa_bang_ten_bien(ung_dung, monkeypatch):
    client, _, _ = ung_dung
    sid = _tao_phien(client, platform="facebook")
    monkeypatch.setenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    monkeypatch.setenv("FACEBOOK_PAGE_ID", "")
    get_settings.cache_clear()
    r = client.post(f"/sessions/{sid}/ingest", json={})
    assert r.status_code == 422
    assert "FACEBOOK_PAGE_ACCESS_TOKEN" in r.json()["detail"]


def test_endpoint_khong_bat_cho_phien_da_dong(ung_dung):
    client, _, _ = ung_dung
    sid = _tao_phien(client)
    client.post(f"/sessions/{sid}/cancel")
    r = client.post(f"/sessions/{sid}/ingest", json={"source": "dQw4w9WgXcQ"})
    assert r.status_code == 409


def test_endpoint_platforms_la_duong_doc_mo(ung_dung):
    client, _, _ = ung_dung
    r = client.get("/platforms")
    assert r.status_code == 200
    # "mo_phong" (17/09/2026): nguồn bình luận tổng hợp để kiểm thử đường ống,
    # luôn sẵn sàng nhưng chỉ bật được trên phiên chạy thử — xem test_ingest_mo_phong.py.
    assert {p["platform"] for p in r.json()} == {
        "youtube",
        "facebook",
        "shopee",
        "tiktok",
        "mo_phong",
    }


def test_bat_bo_thu_doi_token_khi_da_dat_token(monkeypatch):
    monkeypatch.setenv("INGEST_TOKEN", "bi-mat")
    monkeypatch.setenv("YOUTUBE_API_KEY", "khoa-thu")
    get_settings.cache_clear()
    try:
        store = InMemoryStore()
        sid = _phien(store, status="planned")
        with TestClient(create_app(store=store)) as client:
            r = client.post(f"/sessions/{sid}/ingest", json={"source": "dQw4w9WgXcQ"})
            assert r.status_code == 401
    finally:
        get_settings.cache_clear()


def test_api_nhan_binh_luan_gan_nhan_shopee():
    """Trước 17/09: 422 ⇒ ApiSink vứt bản ghi ⇒ đường Shopee lưu được 0 bình luận."""
    store = InMemoryStore()
    with TestClient(create_app(store=store)) as client:
        sid = _tao_phien(client, platform="facebook")
        r = client.post(
            f"/sessions/{sid}/comments",
            json={"platform": "shopee", "ext_id": "sp-1", "text": "chốt 2 hộp"},
        )
        assert r.status_code == 200, r.text
        r = client.post(
            f"/sessions/{sid}/reactions",
            json={"platform": "shopee", "ext_id": "sp-2", "kind": "like"},
        )
        assert r.status_code == 200, r.text
