"""Bộ thu nền: độ bền khi nền tảng đổi buổi live và khi kho chập chờn.

Hồi quy kiểm toán 17/09/2026, ba lỗi của ``livelift.api.ingest_jobs``:

1. Facebook tự tìm buổi live chỉ dò MỘT lần. Host rớt sóng rồi phát lại (Page có
   live-video id mới) thì bộ thu vẫn poll video cũ mãi, mất toàn bộ bình luận
   của buổi mới trong khi trạng thái vẫn là "đang thu".
2. Mã xoá ``last_error`` khi thu lại được là mã chết: lỗi của lượt trước còn mãi,
   hiện sau khi tắt bộ thu và che lỗi hiện tại của client/sink.
3. ``StoreSink`` vứt vĩnh viễn bình luận gặp ``StoreUnavailableError`` (kho
   chập chờn vài giây) — client nền tảng đã đi qua chúng nên không gửi lại.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

import livelift.api.ingest_jobs as ingest_jobs
from livelift.api.ingest_jobs import IngestManager, StoreSink
from livelift.api.store import InMemoryStore, StoreUnavailableError
from livelift.ingest.base import RawComment, RawTick

NHANH = {
    "restart_base_s": 0.01,
    "restart_cap_s": 0.02,
    "wait_for_live_s": 0.01,
    "watch_every_s": 0.02,
}


@pytest.fixture(autouse=True, scope="module")
def _nap_san_bo_phan_loai():
    """Nạp mô hình ý định TRƯỚC khi đo thời gian.

    Bình luận đầu tiên của một tiến trình nguội tốn ~4 giây để nạp mô hình
    (kiểm toán 18/09/2026) — đủ để các phép chờ 3 giây trong tệp này hết giờ
    một cách ngẫu nhiên. Máy chủ thật nạp sẵn trong lifespan; test nạp ở đây."""
    from livelift.nlp.intent import classify_with_confidence

    classify_with_confidence("khởi động bộ phân loại")


def _phien(store: InMemoryStore, platform: str = "youtube") -> str:
    sid = str(uuid.uuid4())
    now = datetime.now(UTC)
    store.create_session(
        {
            "session_id": sid,
            "platform": platform,
            "title": "test",
            "mode": "suggest",
            "status": "live",
            "planned_duration_min": 90,
            "host_id": None,
            "start_ts": now,
            "end_ts": None,
            "created_at": now,
            "dry_run": False,
            "is_demo": False,
        }
    )
    return sid


async def _cho(dieu_kien, timeout: float = 3.0) -> None:
    han = time.monotonic() + timeout
    while not dieu_kien():
        if time.monotonic() > han:
            raise AssertionError("hết giờ chờ điều kiện")
        await asyncio.sleep(0.01)


def _binh_luan(ext_id: str, text: str = "còn size M không") -> RawComment:
    return RawComment(platform="youtube", ext_id=ext_id, ts_utc=datetime.now(UTC), text=text)


# ---------------------------------------------------------------------------
# 1. Facebook tự tìm buổi live: host phát lại thì bắt được buổi mới
# ---------------------------------------------------------------------------


class PagePhatLai:
    """Page phát buổi 111; host rớt sóng rồi bấm phát lại thành buổi 222."""

    def __init__(self) -> None:
        self.lan_tim = 0
        self.video_da_doc: list[str] = []

    def factory(self, platform: str) -> ClientFacebookGia:
        return ClientFacebookGia(self)


class ClientFacebookGia:
    def __init__(self, page: PagePhatLai) -> None:
        self.page = page
        self.last_error: str | None = None

    async def get_active_live_video_id(self) -> str:
        self.page.lan_tim += 1
        return "111" if self.page.lan_tim == 1 else "222"

    async def iter_comments(self, video_id: str):
        self.page.video_da_doc.append(video_id)
        yield RawComment(
            platform="facebook",
            ext_id=f"{video_id}-c1",
            ts_utc=datetime.now(UTC),
            text=f"chốt đơn buổi {video_id}",
        )
        if video_id == "111":
            # Bình luận cuối của buổi, tới SAU khi vòng người xem đã thấy
            # LIVE_STOPPED (poll bình luận chậm hơn một nhịp).
            await asyncio.sleep(0.1)
            yield RawComment(
                platform="facebook",
                ext_id="111-cuoi",
                ts_utc=datetime.now(UTC),
                text="chốt 3 cái nha shop",
            )
        # Graph không bao giờ báo "hết bình luận" cho một video đã dừng: vòng
        # poll bình luận của FacebookLiveClient không có điều kiện dừng.
        await asyncio.sleep(3600)

    async def iter_viewers(self, video_id: str):
        yield RawTick(platform="facebook", ts_utc=datetime.now(UTC), viewers=12)
        if video_id == "111":
            await asyncio.sleep(0.05)
            return  # status=LIVE_STOPPED: FacebookLiveClient.iter_viewers kết thúc êm
        await asyncio.sleep(3600)

    async def aclose(self) -> None:
        return None


def test_facebook_tu_tim_bat_lai_buoi_moi_khi_host_phat_lai():
    store = InMemoryStore()
    sid = _phien(store, platform="facebook")
    page = PagePhatLai()

    async def chay():
        m = IngestManager(store, client_factory=page.factory, doc_not_khi_het_buoi_s=0.5, **NHANH)
        job = m.start(sid, "facebook", "")
        try:
            await _cho(
                lambda: any(c["ext_id"] == "222-c1" for c in store.list_comments(sid)),
            )
            await _cho(lambda: job.state == "dang_thu")
            return job, job.trang_thai()
        finally:
            await m.stop(sid)

    job, st = asyncio.run(chay())
    assert page.video_da_doc[:2] == ["111", "222"], "phải dò lại buổi đang phát sau khi 111 dừng"
    assert st["resolved_source"] == "222"
    assert job.restarts == 0, "buổi live dừng không phải lỗi — không tính là lần thử lại"
    assert {c["ext_id"] for c in store.list_comments(sid)} == {"111-c1", "111-cuoi", "222-c1"}, (
        "bình luận cuối của buổi vừa dừng phải được đọc nốt trước khi chuyển buổi"
    )


def test_facebook_nguon_chi_dinh_san_khong_tu_doi_video():
    """Người vận hành dán sẵn live-video id thì bộ thu không được tự nhảy sang
    buổi khác của Page — chỉ chế độ để trống mới tự tìm."""
    store = InMemoryStore()
    sid = _phien(store, platform="facebook")
    page = PagePhatLai()

    async def chay():
        m = IngestManager(store, client_factory=page.factory, **NHANH)
        job = m.start(sid, "facebook", "111")
        try:
            await _cho(lambda: len(store.list_comments(sid)) == 1)
            await asyncio.sleep(0.2)
            return job
        finally:
            await m.stop(sid)

    asyncio.run(chay())
    assert page.lan_tim == 0
    assert page.video_da_doc == ["111"]


# ---------------------------------------------------------------------------
# 2. Lỗi của lượt trước không được sống mãi
# ---------------------------------------------------------------------------


class NguonLoiMotLan:
    """Lượt đầu mất mạng, lượt sau thu bình thường và không tự kết thúc."""

    def __init__(self) -> None:
        self.lan = 0

    def factory(self, platform: str) -> ClientLoiMotLan:
        return ClientLoiMotLan(self)


class ClientLoiMotLan:
    def __init__(self, nguon: NguonLoiMotLan) -> None:
        self.nguon = nguon
        self.last_error: str | None = None

    async def iter_comments(self, source_id: str):
        self.nguon.lan += 1
        if self.nguon.lan == 1:
            raise ConnectionError("mất mạng")
        for i in range(2):
            await asyncio.sleep(0)
            yield _binh_luan(f"c-{i}")
        await asyncio.sleep(3600)

    async def iter_viewers(self, source_id: str):
        await asyncio.sleep(3600)
        yield  # pragma: no cover

    async def aclose(self) -> None:
        return None


def test_loi_luot_truoc_duoc_xoa_khi_thu_lai_duoc_va_khong_che_loi_hien_tai():
    store = InMemoryStore()
    sid = _phien(store)
    nguon = NguonLoiMotLan()

    async def chay():
        m = IngestManager(store, client_factory=nguon.factory, **NHANH)
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        await _cho(lambda: job.trang_thai()["comments_posted"] == 2)
        khi_dang_thu = job.trang_thai()
        # Client báo một lỗi HIỆN TẠI (vd hạn mức): nó phải hiện ra, không bị
        # lỗi mạng cũ của lượt trước che mất.
        job.client.last_error = "LỖI YouTube API (HTTP 403): quota trong ngày đã cạn"
        loi_hien_tai = job.trang_thai()["last_error"]
        job.client.last_error = None
        await m.stop(sid)
        return job, khi_dang_thu, loi_hien_tai

    job, khi_dang_thu, loi_hien_tai = asyncio.run(chay())
    assert job.restarts == 1
    assert khi_dang_thu["last_error"] is None, "lỗi của lượt trước phải được xoá khi thu lại được"
    assert loi_hien_tai == "LỖI YouTube API (HTTP 403): quota trong ngày đã cạn"
    assert job.state == "da_dung"
    assert job.trang_thai()["last_error"] is None, "tắt bộ thu khoẻ không được hiện lỗi cũ"


# ---------------------------------------------------------------------------
# 3. StoreSink: kho chập chờn không làm mất bình luận
# ---------------------------------------------------------------------------


class KhoChapChon(InMemoryStore):
    """Kho bộ nhớ ném ``StoreUnavailableError`` khi ``chet`` hoặc trong
    ``chet_so_lan`` lần ghi đầu — đúng loại lỗi PostgresStore dịch ra."""

    def __init__(self, chet_so_lan: int = 0) -> None:
        super().__init__()
        self.chet = False
        self.chet_so_lan = chet_so_lan
        self.so_lan_ghi = 0

    def _co_the_chet(self) -> None:
        self.so_lan_ghi += 1
        if self.chet or self.chet_so_lan > 0:
            self.chet_so_lan = max(0, self.chet_so_lan - 1)
            raise StoreUnavailableError(
                "Kho dữ liệu không trả lời", cause_text="couldn't get a connection"
            )

    def add_comment(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        self._co_the_chet()
        return super().add_comment(session_id, row)

    def add_tick(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        self._co_the_chet()
        return super().add_tick(session_id, row)


class DongHo:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_store_sink_giu_ban_ghi_khi_kho_chet_va_ghi_lai_dung_thu_tu():
    store = KhoChapChon()
    sid = _phien(store)
    dong_ho = DongHo()
    sink = StoreSink(store, sid, thu_lai_dau_s=1.0, thu_lai_tran_s=8.0, clock=dong_ho)

    async def chay():
        store.chet = True
        assert await sink.post_comment(_binh_luan("c-1")) is False
        assert sink.pending == 1
        assert "không trả lời" in (sink.last_error or "")
        so_lan_truoc = store.so_lan_ghi
        # Chưa tới lượt dò: xếp thẳng vào hàng đợi, KHÔNG gõ kho thêm lần nào
        # (với Postgres mỗi lần gõ là một vòng hết giờ của pool).
        assert await sink.post_comment(_binh_luan("c-2")) is False
        assert await sink.post_tick(RawTick("youtube", datetime.now(UTC), 30)) is False
        assert store.so_lan_ghi == so_lan_truoc
        assert sink.pending == 3

        store.chet = False
        dong_ho.t += 2.0
        assert await sink.post_comment(_binh_luan("c-3")) is True

    asyncio.run(chay())
    assert [c["ext_id"] for c in store.list_comments(sid)] == ["c-1", "c-2", "c-3"]
    assert len(store.list_ticks(sid)) == 1
    assert sink.pending == 0
    assert sink.comments_posted == 3
    assert sink.ticks_posted == 1
    assert sink.failures == 0
    assert sink.dropped == 0
    assert sink.last_error is None, "kho sống lại và không mất gì thì không còn báo lỗi"


def test_store_sink_xa_hang_doi_khi_buoi_live_im_lang():
    store = KhoChapChon()
    sid = _phien(store)
    dong_ho = DongHo()
    sink = StoreSink(store, sid, thu_lai_dau_s=1.0, clock=dong_ho)

    async def chay():
        store.chet = True
        await sink.post_comment(_binh_luan("c-1"))
        store.chet = False
        await sink.xa_hang_doi()  # chưa tới lượt dò
        assert sink.pending == 1
        dong_ho.t += 1.5
        await sink.xa_hang_doi()

    asyncio.run(chay())
    assert sink.pending == 0
    assert [c["ext_id"] for c in store.list_comments(sid)] == ["c-1"]


def test_store_sink_hang_doi_day_thi_dem_ban_ghi_mat_khong_im_lang():
    store = KhoChapChon()
    sid = _phien(store)
    dong_ho = DongHo()
    sink = StoreSink(store, sid, hang_doi_toi_da=2, clock=dong_ho)

    async def chay():
        store.chet = True
        for i in range(3):
            await sink.post_comment(_binh_luan(f"c-{i}"))
        assert sink.pending == 2
        assert sink.dropped == 1
        store.chet = False
        dong_ho.t += 60.0
        await sink.xa_hang_doi()

    asyncio.run(chay())
    assert [c["ext_id"] for c in store.list_comments(sid)] == ["c-0", "c-1"]
    assert sink.dropped == 1
    assert "ĐÃ MẤT 1" in (sink.last_error or ""), "mất dữ liệu phải còn hiện sau khi kho sống lại"
    assert "c-" not in (sink.last_error or "")


def test_store_sink_loi_khong_phai_kho_chet_khong_bi_xep_hang():
    store = KhoChapChon()
    sink = StoreSink(store, "phien-khong-ton-tai")

    async def chay():
        return await sink.post_comment(_binh_luan("c-1"))

    assert asyncio.run(chay()) is False
    assert sink.pending == 0
    assert sink.failures == 1


def test_bo_thu_nen_khong_mat_binh_luan_khi_kho_chap_chon(monkeypatch):
    """Kịch bản của kiểm toán: kho chập chờn đúng lúc có bình luận. Trước bản sửa
    3 bình luận đầu mất hẳn (chỉ tăng ``write_failures``)."""
    monkeypatch.setattr(ingest_jobs, "THU_LAI_KHO_DAU_S", 0.01)
    monkeypatch.setattr(ingest_jobs, "THU_LAI_KHO_TRAN_S", 0.02)
    store = KhoChapChon(chet_so_lan=3)
    sid = _phien(store)

    class Client:
        last_error = None

        async def iter_comments(self, source_id: str):
            for i in range(5):
                yield _binh_luan(f"c-{i}")
            await asyncio.sleep(3600)  # rồi buổi live im lặng

        async def iter_viewers(self, source_id: str):
            await asyncio.sleep(3600)
            yield  # pragma: no cover

        async def aclose(self) -> None:
            return None

    async def chay():
        m = IngestManager(store, client_factory=lambda _p: Client(), **NHANH)
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        try:
            await _cho(lambda: len(store.list_comments(sid)) == 5)
            await _cho(lambda: job.trang_thai()["pending_writes"] == 0)
            return job.trang_thai()
        finally:
            await m.stop(sid)

    st = asyncio.run(chay())
    assert st["comments_posted"] == 5
    assert st["write_failures"] == 0
    assert st["dropped_writes"] == 0
    assert st["last_error"] is None


@pytest.mark.parametrize("truong", ["pending_writes", "dropped_writes"])
def test_trang_thai_endpoint_co_truong_hang_doi(truong):
    from livelift.api.routes.ingest import IngestStatus

    assert truong in IngestStatus.model_fields


# ---------------------------------------------------------------------------
# 4. Chờ buổi live: nhịp dò giãn dần để không đốt quota nền tảng
# ---------------------------------------------------------------------------


class ClientChuaPhat:
    """Nền tảng báo chưa phát ``chua_phat`` lần rồi mới có bình luận."""

    dem = {"chua_phat": 0}

    def __init__(self, chua_phat: int) -> None:
        self.con_lai = chua_phat
        self.last_error: str | None = None

    async def iter_comments(self, source_id: str):
        if ClientChuaPhat.dem["chua_phat"] > 0:
            ClientChuaPhat.dem["chua_phat"] -= 1
            raise RuntimeError(f"video {source_id} has no active live chat (not live?)")
        yield _binh_luan("sau-khi-len-song")

    async def iter_viewers(self, source_id: str):
        await asyncio.sleep(3600)
        yield RawTick(platform="youtube", ts_utc=datetime.now(UTC), viewers=1)

    async def aclose(self) -> None:
        return None


def test_nhip_do_khi_cho_len_song_gian_dan_de_do_quota(monkeypatch):
    """Kiểm toán 18/09/2026: chờ ở nhịp cố định tốn quota thật.

    Mỗi vòng chờ của YouTube gọi ``videos.list`` 2 lượt (360 đơn vị/giờ); quy
    trình vận hành bật bộ thu trước 2 giờ ⇒ 720 trong 10.000 đơn vị/ngày tiêu
    hết trước khi buổi live bắt đầu. Nhịp dò phải giãn gấp đôi tới trần.
    """
    ngu: list[float] = []
    that = asyncio.sleep

    async def ghi_lai(delay, *a, **kw):
        ngu.append(float(delay))
        return await that(0)

    ClientChuaPhat.dem["chua_phat"] = 5
    store = InMemoryStore()
    sid = _phien(store)

    async def chay():
        monkeypatch.setattr(ingest_jobs.asyncio, "sleep", ghi_lai)
        m = IngestManager(
            store,
            client_factory=lambda _p: ClientChuaPhat(5),
            wait_for_live_s=1.0,
            wait_for_live_cap_s=8.0,
            restart_base_s=0.01,
            restart_cap_s=0.02,
            watch_every_s=0.02,
        )
        job = m.start(sid, "youtube", "dQw4w9WgXcQ")
        han = time.monotonic() + 5
        while job.dang_chay and time.monotonic() < han:
            await that(0.01)
        return job

    job = asyncio.run(chay())
    assert job.state == "nguon_ket_thuc", job.last_error
    # Bỏ giấc 3600 giây của vòng người xem giả trong client thử.
    cho = [d for d in ngu if 1.0 <= d <= 8.0]
    assert cho[:5] == [1.0, 2.0, 4.0, 8.0, 8.0], f"nhịp chờ phải giãn tới trần: {cho[:6]}"
    assert sum(cho[:5]) < 5 * 8.0, "giãn dần phải rẻ hơn dò ở nhịp trần ngay từ đầu"
    assert len(store.list_comments(sid)) == 1, "lên sóng rồi thì phải thu được"
