"""Nhịp bình luận theo mốc 30 giây phải đếm từ bảng bình luận — hồi quy 17/09/2026.

Mọi client live (YouTube, Facebook, Shopee, mô phỏng) chỉ gửi số người xem trong
tick; ``StoreSink.post_tick`` và ``ApiSink.post_tick`` không có ``comment_rate``
nên ``TickIn`` điền mặc định 0.0. Trên Bàn trợ live, ô "Bình luận / phút" in số
0 ngay cạnh "110 bình luận", biểu đồ nhịp vẽ đường phẳng, và báo cáo kết luận
"nhịp chat tương đối đều" từ một chuỗi toàn 0 — số bịa.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from livelift.api.ingest_jobs import IngestManager
from livelift.api.main import create_app
from livelift.api.routes.events import gan_nhip_binh_luan, nhip_binh_luan_theo_moc
from livelift.api.store import InMemoryStore
from livelift.config import get_settings
from livelift.ingest.mo_phong import MoPhongLiveClient


@pytest.fixture
def client_store(monkeypatch):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    store = InMemoryStore()
    with TestClient(create_app(store=store)) as client:
        yield client, store
    get_settings.cache_clear()


def _phien(store: InMemoryStore, start: datetime, status: str = "live", **them) -> str:
    sid = str(uuid.uuid4())
    store.create_session(
        {
            "session_id": sid,
            "platform": "youtube",
            "title": "nhịp",
            "mode": "suggest",
            "status": status,
            "planned_duration_min": 90,
            "host_id": None,
            "start_ts": start,
            "end_ts": None if status == "live" else start + timedelta(minutes=30),
            "created_at": start,
            "dry_run": False,
            "is_demo": False,
            **them,
        }
    )
    return sid


def _binh_luan(store: InMemoryStore, sid: str, ts: datetime, i: int) -> None:
    store.add_comment(
        sid,
        {
            "comment_id": str(uuid.uuid4()),
            "session_id": sid,
            "block_id": None,
            "ts": ts,
            "platform": "youtube",
            "ext_id": f"c-{i}-{ts.timestamp()}",
            "text_scrubbed": "còn size M không",
            "pii_kinds": [],
            "intent_label": None,
            "intent_confidence": None,
            "sentiment": None,
        },
    )


def test_tick_live_mang_nhip_binh_luan_that_cua_moc(client_store):
    client, store = client_store
    start = datetime.now(UTC) - timedelta(minutes=5)
    sid = _phien(store, start)
    moc = start + timedelta(seconds=60)  # mốc [60s, 90s) đã trôi hết
    for i in range(7):
        _binh_luan(store, sid, moc + timedelta(seconds=2 + i), i)

    r = client.post(
        f"/sessions/{sid}/ticks",
        json={"viewers": 40, "ts_utc": (moc + timedelta(seconds=15)).isoformat()},
    )
    assert r.status_code == 200, r.text
    assert r.json()["comment_rate"] == 14.0, "7 bình luận trong 30 giây = 14 bình luận/phút"

    ticks = client.get(f"/sessions/{sid}/ticks").json()
    assert [t["comment_rate"] for t in ticks] == [14.0]


def test_binh_luan_den_sau_khi_tick_da_ghi_van_duoc_dem(client_store):
    client, store = client_store
    start = datetime.now(UTC) - timedelta(minutes=5)
    sid = _phien(store, start)
    moc = start + timedelta(seconds=120)
    client.post(
        f"/sessions/{sid}/ticks",
        json={"viewers": 40, "ts_utc": (moc + timedelta(seconds=1)).isoformat()},
    )
    for i in range(5):
        _binh_luan(store, sid, moc + timedelta(seconds=10 + i), i)
    ticks = client.get(f"/sessions/{sid}/ticks").json()
    assert ticks[0]["comment_rate"] == 10.0


def test_moc_dang_chay_do_bang_30_giay_gan_nhat_khong_phai_nua_moc():
    start = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    moc = start + timedelta(seconds=30)
    now = moc + timedelta(seconds=10)  # mốc mới trôi được 10 giây
    comments = [{"ts": start + timedelta(seconds=s)} for s in (21, 25, 29, 32, 35, 38)]
    nhip = nhip_binh_luan_theo_moc([start, moc], comments, now)
    assert nhip[start] == 3 * 2.0  # mốc đã xong: đúng [0s, 30s)
    assert nhip[moc] == 6 * 2.0  # mốc dở dang: [10s, 40s) — trọn 30 giây gần nhất


def test_gia_tri_da_luu_cua_demo_va_replay_duoc_giu_nguyen():
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    ticks = [
        {"ts_bucket": t0, "comment_rate": 18.0},
        {"ts_bucket": t0 + timedelta(seconds=30), "comment_rate": 0.0},
    ]
    comments = [{"ts": t0 + timedelta(seconds=40)}]
    out = gan_nhip_binh_luan(ticks, comments, now=t0 + timedelta(hours=1))
    assert [t["comment_rate"] for t in out] == [18.0, 2.0]
    assert ticks[1]["comment_rate"] == 0.0, "không sửa tại chỗ danh sách của kho"


def test_bao_cao_phien_live_thay_dinh_va_spike_binh_luan(client_store):
    """Tick live toàn 0: trước khi sửa báo cáo ghi THIẾU đỉnh và "nhịp chat tương
    đối đều" dù có một đợt 20 bình luận trong 30 giây."""
    client, store = client_store
    start = datetime.now(UTC) - timedelta(hours=2)
    sid = _phien(store, start, status="ended")
    i = 0
    for k in range(40):
        moc = start + timedelta(seconds=30 * k)
        store.add_tick(
            sid,
            {
                "ts_bucket": moc,
                "viewers": 50.0,
                "comment_rate": 0.0,
                "like_rate": 0.0,
                "click_count": 0,
                "pinned_product_id": None,
            },
        )
        so = 20 if k == 25 else 1
        for j in range(so):
            _binh_luan(store, sid, moc + timedelta(seconds=1 + j), i)
            i += 1

    r = client.get(f"/sessions/{sid}/bao-cao")
    assert r.status_code == 200, r.text
    bc = r.json()
    dinh = bc["tong_quan"]["dinh_binh_luan"]
    assert dinh is not None
    assert dinh["gia_tri_per_phut"] == 40.0
    assert dinh["offset_s"] == 25 * 30
    assert "tương đối đều" not in (bc["khoanh_khac_ghi_chu"] or "")
    assert len(bc["khoanh_khac"]) >= 1


def test_bo_thu_nen_mo_phong_ghi_tick_co_nhip_binh_luan(client_store):
    """Đúng kịch bản quan sát được trên trình duyệt: bật nguồn mô phỏng trên phiên
    chạy thử, feed có bình luận nhưng GET /ticks trả comment_rate toàn 0.0."""
    client, store = client_store
    sid = _phien(store, datetime.now(UTC), dry_run=True)

    async def chay():
        m = IngestManager(
            store,
            client_factory=lambda _p: MoPhongLiveClient(he_so=1e5),
            restart_base_s=0.01,
            restart_cap_s=0.02,
            wait_for_live_s=0.01,
            watch_every_s=0.02,
        )
        job = m.start(sid, "mo_phong", "ngan")
        for _ in range(500):
            if not job.dang_chay:
                break
            await asyncio.sleep(0.01)
        return job

    job = asyncio.run(chay())
    assert job.trang_thai()["comments_posted"] > 0
    rates = [t["comment_rate"] for t in client.get(f"/sessions/{sid}/ticks").json()]
    assert rates
    assert max(rates) > 0
