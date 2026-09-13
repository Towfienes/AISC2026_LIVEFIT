"""Gate (sự cố 13/09/2026, gói D-ĐỘ-BỀN): kho chết giữa phiên live.

Bối cảnh thật: Docker tắt, PostgreSQL biến mất, API vẫn sống. Ba câu hỏi sống
còn cho một phiên 90 phút đang phát — và ba câu trả lời cũ đều sai:

1. **Bình luận đang thu có mất không?** Sink vẫn spool, nhưng nó thử đủ ba
   vòng timeout cho MỖI bản ghi, nên vòng đọc bình luận đứng lại hàng chục
   giây một lần ngay lúc đông nhất; và 4xx-payload cũng bị spool, gieo bản ghi
   "độc" làm mọi lần nạp bù sau này báo thất bại.
2. **Người vận hành có biết không?** Đường ghi sự kiện trả ``500 Internal
   Server Error`` trống rỗng — không ai biết bình luận vừa rồi đã lưu hay chưa.
3. **Bộ thực thi tự động làm gì?** Nuốt lỗi trong ``except Exception``, quét
   tiếp mỗi 5 giây, im lặng, trong khi từng khối BẬT trôi qua không ai ghim →
   báo cáo sẽ nói "đội vận hành không tuân thủ" thay vì "cơ sở dữ liệu đã chết".

Không cần PostgreSQL để chạy gate này: :class:`KhoCoTheChet` bọc
``InMemoryStore`` và ném đúng lớp lỗi mà psycopg/sqlite3 ném khi mất kết nối.
Kịch bản đo thật nằm ở ``docs/benchmarks/kho-chet-giua-phien.md``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from livelift.api import autopilot, service
from livelift.api.main import create_app
from livelift.api.routes.events import is_storage_outage
from livelift.api.store import InMemoryStore
from livelift.ingest.base import ApiSink, RawComment, RawTick
from livelift.ingest.spool_replay import replay_file

API_BASE = "http://api.test"


class OperationalError(Exception):
    """Tên lớp cố ý trùng ``psycopg.OperationalError`` / ``sqlite3.OperationalError``.

    Bộ phân loại nhận diện kho chết theo TÊN lớp trên cây kế thừa (psycopg là
    phụ thuộc tùy chọn), nên đây chính là thứ nó phải bắt được.
    """


class KhoCoTheChet:
    """Bọc một store thật và cho phép "rút dây" giữa phiên.

    Mọi lời gọi phương thức đều đi qua đây; khi ``chet`` bật, lời gọi ném lỗi
    kết nối y như psycopg khi PostgreSQL biến mất dưới chân.
    """

    def __init__(self, inner: InMemoryStore) -> None:
        self._inner = inner
        self.chet = False
        self.so_lan_goi_khi_chet = 0

    def __getattr__(self, name: str):
        attr = getattr(self._inner, name)
        if not callable(attr):
            return attr

        def goi(*args, **kwargs):
            if self.chet:
                self.so_lan_goi_khi_chet += 1
                raise OperationalError(
                    "consuming input failed: server closed the connection unexpectedly"
                )
            return attr(*args, **kwargs)

        return goi


@pytest.fixture(autouse=True)
def _sach_trang_thai_toan_cuc():
    """Cửa sổ kho chết sống ở phạm vi tiến trình — dọn trước và sau mỗi test."""
    autopilot.reset_heartbeats()
    yield
    autopilot.reset_heartbeats()


@pytest.fixture
def kho():
    return KhoCoTheChet(InMemoryStore())


@pytest.fixture
def app_client(kho, monkeypatch):
    # Tắt tác vụ nền: các test dưới đây gọi step_all() bằng tay để kiểm soát
    # từng vòng quét, một vòng quét lén lút sẽ làm khẳng định thành ngẫu nhiên.
    monkeypatch.setenv("LIVELIFT_AUTOPILOT", "0")
    app = create_app(store=kho)
    with TestClient(app) as tc:
        try:
            yield app, tc
        finally:
            # Nối lại dây trước khi lifespan gọi store.close(): tắt máy là việc
            # của test kế tiếp, không phải một sự cố nữa.
            kho.chet = False


def _live_session(tc: TestClient, mode: str = "auto") -> tuple[str, list[dict]]:
    sid = tc.post(
        "/sessions",
        json={"platform": "youtube", "mode": mode, "planned_duration_min": 60},
    ).json()["session_id"]
    sched = tc.post(
        f"/sessions/{sid}/schedule",
        json={"block_min": 5, "washout_min": 0, "jitter_s": 0, "seed": 2026},
    )
    assert sched.status_code == 200, sched.text
    started = tc.post(f"/sessions/{sid}/start")
    assert started.status_code == 200, started.text
    return sid, sched.json()["blocks"]


def _seed_products(tc: TestClient, n: int = 3) -> None:
    for i in range(n):
        r = tc.post(
            "/products",
            json={
                "product_id": f"SP{i}",
                "name": f"Sản phẩm số {i}",
                "category": "test",
                "cost": 10_000,
                "price": 40_000,
                "stock": 25,
            },
        )
        assert r.status_code == 200, r.text


def _dat_phien_tai(kho: KhoCoTheChet, session_id: str, offset_s: float) -> None:
    now = service.now_utc()
    kho.update_session(session_id, {"start_ts": now - timedelta(seconds=offset_s)})


def _make_sink(handler, **kwargs) -> tuple[ApiSink, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    kwargs.setdefault("token", "")
    kwargs.setdefault("base_delay_s", 0.0)
    sink = ApiSink(api_url=API_BASE, session_id="sess-1", client=client, **kwargs)
    return sink, client


# ---------------------------------------------------------------------------
# 1. Bộ phân loại: kho chết là lỗi tạm thời, bug là bug
# ---------------------------------------------------------------------------


def test_nhan_dien_loi_kho_theo_ten_lop_cua_db_api():
    assert is_storage_outage(OperationalError("server closed the connection"))
    assert is_storage_outage(ConnectionResetError("đứt socket"))
    assert is_storage_outage(TimeoutError("hết giờ chờ kết nối"))
    # Bug thật KHÔNG được ngụy trang thành "kho chết" — nếu không, bộ thu sẽ
    # gửi lại mãi mãi một bản ghi không bao giờ vào được.
    assert not is_storage_outage(ValueError("lỗi lập trình"))
    assert not is_storage_outage(KeyError("thiếu khóa"))


def test_nhan_dien_lop_that_cua_psycopg_va_pool():
    psycopg = pytest.importorskip("psycopg")
    psycopg_pool = pytest.importorskip("psycopg_pool")
    assert is_storage_outage(psycopg.OperationalError("connection failed"))
    assert is_storage_outage(psycopg.errors.AdminShutdown("shutting down"))
    assert is_storage_outage(psycopg_pool.PoolTimeout("hết chỗ trong pool"))


# ---------------------------------------------------------------------------
# 2. Đường ghi sự kiện: 503 + tiếng Việt nói rõ "CHƯA ĐƯỢC LƯU"
# ---------------------------------------------------------------------------


def test_ghi_binh_luan_khi_kho_chet_tra_503_va_noi_ro_chua_luu(app_client, kho):
    app, tc = app_client
    sid, _ = _live_session(tc)
    kho.chet = True

    r = tc.post(
        f"/sessions/{sid}/comments",
        json={"platform": "youtube", "ext_id": "LCC.1", "text": "chốt đơn"},
    )
    assert r.status_code == 503, r.text
    detail = r.json()["detail"]
    assert "KHO DỮ LIỆU KHÔNG PHẢN HỒI" in detail
    assert "CHƯA ĐƯỢC LƯU" in detail
    # Phải nói LÀM GÌ TIẾP, không chỉ nói hỏng.
    assert "spool_replay" in detail
    assert sid in detail
    assert r.headers["X-LiveLift-Storage"] == "down"
    assert r.headers["Retry-After"] == "5"


def test_ghi_tick_va_doc_danh_sach_khi_kho_chet_cung_tra_503(app_client, kho):
    app, tc = app_client
    sid, _ = _live_session(tc)
    kho.chet = True

    tick = tc.post(f"/sessions/{sid}/ticks", json={"platform": "youtube", "viewers": 120})
    assert tick.status_code == 503
    assert "CHƯA ĐƯỢC LƯU" in tick.json()["detail"]

    # Đọc cũng phải trả lời tử tế thay vì treo rồi "Internal Server Error":
    # người vận hành mở bảng bình luận lúc kho chết phải biết vì sao nó rỗng.
    doc = tc.get(f"/sessions/{sid}/comments")
    assert doc.status_code == 503
    assert "KHO DỮ LIỆU KHÔNG PHẢN HỒI" in doc.json()["detail"]


def test_loi_lap_trinh_that_khong_bi_nguy_trang_thanh_503(app_client, kho, monkeypatch):
    """503 nghĩa là "thử lại sau". Một bug mà trả 503 thì bộ thu sẽ giữ bản ghi
    và gửi lại vô hạn, còn lập trình viên thì không bao giờ nhìn thấy lỗi."""
    app, tc = app_client
    sid, _ = _live_session(tc)

    def no_tung(*_args, **_kwargs):
        raise ValueError("bug thật trong code")

    monkeypatch.setattr(kho._inner, "add_comment", no_tung)
    with pytest.raises(ValueError, match="bug thật"):
        tc.post(
            f"/sessions/{sid}/comments",
            json={"platform": "youtube", "ext_id": "LCC.bug", "text": "chốt đơn"},
        )


# ---------------------------------------------------------------------------
# 3. ApiSink: 5xx luôn vào spool, và không được làm nghẽn vòng đọc
# ---------------------------------------------------------------------------


def test_moi_loi_5xx_deu_vao_spool_khong_bi_vut(tmp_path):
    """Kho chết thì API trả 5xx — mọi mã 5xx phải giữ được bản ghi."""
    for status in (500, 502, 503, 504):
        thu_muc = tmp_path / str(status)

        def handler(request: httpx.Request, status: int = status) -> httpx.Response:
            return httpx.Response(status, json={"detail": "kho chết"})

        comment = RawComment(
            platform="youtube",
            ext_id=f"LCC.{status}",
            ts_utc=datetime(2026, 9, 13, 13, 5, 42, tzinfo=UTC),
            text="giữ giúp em, sđt 0901234567",
        )

        async def run(handler=handler, thu_muc=thu_muc, comment=comment) -> bool:
            sink, client = _make_sink(handler, spool_dir=thu_muc)
            try:
                return await sink.post_comment(comment)
            finally:
                await client.aclose()

        assert asyncio.run(run()) is False
        spool = thu_muc / "sess-1.jsonl"
        assert spool.is_file(), f"HTTP {status} làm mất bản ghi"
        raw = spool.read_text(encoding="utf-8")
        assert "0901234567" not in raw  # hard rule 1 vẫn đúng với file spool
        assert json.loads(raw.splitlines()[0])["payload"]["ext_id"] == f"LCC.{status}"


def test_payload_sai_bi_vut_chu_khong_gieo_ban_ghi_doc_vao_spool(tmp_path, caplog):
    """422 = bộ thu và API lệch hợp đồng. Gửi lại y hệt thì vẫn 422, nên giữ nó
    trong spool chỉ làm mọi lần nạp bù sau này báo thất bại vĩnh viễn."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "thiếu trường"})

    tick = RawTick("youtube", datetime(2026, 9, 13, 13, 0, 0, tzinfo=UTC), 5.0)

    async def run() -> tuple[bool, ApiSink]:
        sink, client = _make_sink(handler, spool_dir=tmp_path)
        try:
            return await sink.post_tick(tick), sink
        finally:
            await client.aclose()

    with caplog.at_level(logging.ERROR, logger="livelift.ingest.base"):
        ok, sink = asyncio.run(run())
    assert ok is False
    assert list(tmp_path.iterdir()) == []
    assert sink.dropped == 1
    assert "MẤT bản ghi" in caplog.text  # mất thì phải kêu to, không im lặng


def test_khi_may_chu_hong_lien_tuc_sink_ghi_thang_vao_spool_va_bao_dong(tmp_path, caplog):
    """Điểm sống còn của nhịp thu: khi kho đã chết, KHÔNG được bắt mỗi bình
    luận chờ hết ba vòng timeout nữa — livestream không dừng lại chờ ta."""
    calls = {"n": 0}
    dong_ho = {"t": 0.0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, json={"detail": "kho chết"})

    async def run() -> ApiSink:
        sink, client = _make_sink(
            handler, spool_dir=tmp_path, clock=lambda: dong_ho["t"], probe_every_s=30.0
        )
        try:
            for i in range(4):
                ts = datetime(2026, 9, 13, 13, 0, i, tzinfo=UTC)
                assert await sink.post_comment(RawComment("youtube", f"c{i}", ts, "chốt")) is False
            return sink
        finally:
            await client.aclose()

    with caplog.at_level(logging.ERROR, logger="livelift.ingest.base"):
        sink = asyncio.run(run())

    # Hai POST đầu thử đủ 3 lần (3+3), hai POST sau đi thẳng vào spool: 6 lần
    # gọi HTTP cho 4 bản ghi thay vì 12.
    assert calls["n"] == 6
    assert sink.spool_mode is True
    assert sink.spooled == 4
    assert sink.dropped == 0
    assert len((tmp_path / "sess-1.jsonl").read_text(encoding="utf-8").splitlines()) == 4
    assert "CHẾ ĐỘ SPOOL" in caplog.text
    assert "spool_replay" in caplog.text  # lệnh nạp bù in sẵn để copy


def test_sink_do_lai_va_bao_song_lai_khi_kho_hoi_phuc(tmp_path, caplog):
    calls = {"n": 0}
    dong_ho = {"t": 0.0}
    song = {"ok": False}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if song["ok"]:
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(500, json={"detail": "kho chết"})

    async def run() -> ApiSink:
        sink, client = _make_sink(
            handler, spool_dir=tmp_path, clock=lambda: dong_ho["t"], probe_every_s=30.0
        )
        try:
            for i in range(3):  # vào chế độ spool
                ts = datetime(2026, 9, 13, 13, 0, i, tzinfo=UTC)
                await sink.post_comment(RawComment("youtube", f"c{i}", ts, "chốt"))
            assert sink.spool_mode is True
            truoc_khi_do = calls["n"]

            # Chưa tới lượt dò: không một lời gọi HTTP nào.
            dong_ho["t"] = 10.0
            ts = datetime(2026, 9, 13, 13, 1, 0, tzinfo=UTC)
            await sink.post_comment(RawComment("youtube", "c-cho", ts, "chốt"))
            assert calls["n"] == truoc_khi_do

            # Tới lượt dò mà máy chủ vẫn hỏng: đúng MỘT lần gọi, không ba.
            dong_ho["t"] = 31.0
            await sink.post_comment(RawComment("youtube", "c-do-1", ts, "chốt"))
            assert calls["n"] == truoc_khi_do + 1
            assert sink.spool_mode is True

            # Kho sống lại -> lần dò kế tiếp thành công.
            song["ok"] = True
            dong_ho["t"] = 62.0
            assert await sink.post_comment(RawComment("youtube", "c-song", ts, "chốt")) is True
            return sink
        finally:
            await client.aclose()

    with caplog.at_level(logging.WARNING, logger="livelift.ingest.base"):
        sink = asyncio.run(run())

    assert sink.spool_mode is False
    assert sink.spooled == 5  # 3 + 1 (chờ) + 1 (dò hỏng); bản thứ 6 vào thẳng API
    assert "nhận dữ liệu TRỞ LẠI" in caplog.text
    # Sống lại KHÔNG có nghĩa là xong: 5 bản ghi vẫn chưa có trong cơ sở dữ liệu.
    assert "CHƯA có trong cơ sở dữ liệu" in caplog.text
    assert "spool_replay" in caplog.text


def test_heartbeat_cua_runner_het_len_khi_dang_o_che_do_spool(caplog):
    """Vòng đọc vẫn chạy êm khi kho chết — đúng cái làm sự cố trở nên VÔ HÌNH.
    Heartbeat là dòng log duy nhất người vận hành còn nhìn thấy."""
    from types import SimpleNamespace

    from livelift.ingest.runner import Counters, _heartbeat

    async def run() -> None:
        sink = SimpleNamespace(
            spool_mode=True,
            spooled=137,
            dropped=0,
            last_error="máy chủ trả HTTP 500",
            spool_path="data/spool/abc.jsonl",
            replay_command="python -m livelift.ingest.spool_replay data/spool/abc.jsonl",
        )
        task = asyncio.create_task(_heartbeat(Counters(), None, every_s=0.01, sink=sink))
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    with caplog.at_level(logging.INFO, logger="livelift.ingest.runner"):
        asyncio.run(run())
    assert "BÁO ĐỘNG" in caplog.text
    assert "137 bản ghi" in caplog.text
    assert "spool_replay" in caplog.text


# ---------------------------------------------------------------------------
# 4. Bộ thực thi tự động: DỪNG + BÁO ĐỘNG, không im lặng bỏ khối BẬT
# ---------------------------------------------------------------------------


def test_kho_chet_lam_bo_thuc_thi_dung_han_va_khong_ghim_nua(app_client, kho, caplog):
    app, tc = app_client
    _seed_products(tc)
    sid, blocks = _live_session(tc)
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _dat_phien_tai(kho, sid, (on_block["start_offset_s"] + on_block["end_offset_s"]) / 2)

    kho.chet = True
    with caplog.at_level(logging.ERROR, logger="livelift.autopilot"):
        assert autopilot.step_all(kho) == []

    su_co = autopilot.storage_outage()
    assert su_co is not None
    assert su_co.active is True
    assert "ĐÃ DỪNG" in caplog.text
    assert "KHÔNG ghim bù được" in caplog.text

    kho.chet = False
    assert kho.list_exposure_events(sid) == [], "không được ghim gì khi chưa đọc nổi kho"


def test_bao_dong_kho_chet_hien_len_ban_dieu_khien(app_client, kho):
    """Người vận hành nhìn /state phải thấy LÝ DO, không chỉ thấy con số 0."""
    app, tc = app_client
    _seed_products(tc)
    sid, blocks = _live_session(tc)
    _dat_phien_tai(kho, sid, 12 * 60)

    kho.chet = True
    autopilot.step_all(kho)
    kho.chet = False

    state = tc.get(f"/sessions/{sid}/state", params={"role": "operator"})
    assert state.status_code == 200, state.text
    auto = state.json()["autopilot"]
    assert auto["alarm"] is not None
    assert "kho dữ liệu" in auto["alarm"]
    assert "OperationalError" in auto["alarm"]
    # Hai báo động cùng lúc: nguyên nhân (kho chết) đứng trước hậu quả (chưa
    # ghim gì), để người đọc không kết luận nhầm là đội vận hành lười.
    assert auto["alarm"].index("kho dữ liệu") < auto["alarm"].index("CHƯA CÓ hành động ghim")


def test_sau_khi_kho_song_lai_bo_thuc_thi_chay_tiep_nhung_van_khai_bao_su_co(app_client, kho):
    app, tc = app_client
    _seed_products(tc)
    sid, blocks = _live_session(tc)
    measurement = [b for b in blocks if not b["is_washout"]]
    on_blocks = [b for b in measurement if b["assignment"] == "ON"]
    assert len(on_blocks) >= 2, "kịch bản cần ít nhất 2 khối BẬT"

    # Khối BẬT thứ nhất trôi qua trong lúc kho chết: không ghim bù được.
    _dat_phien_tai(kho, sid, (on_blocks[0]["start_offset_s"] + on_blocks[0]["end_offset_s"]) / 2)
    kho.chet = True
    autopilot.step_all(kho)
    assert autopilot.storage_outage().active is True

    # Kho sống lại đúng lúc khối BẬT thứ hai đang phát.
    kho.chet = False
    _dat_phien_tai(kho, sid, (on_blocks[1]["start_offset_s"] + on_blocks[1]["end_offset_s"]) / 2)
    lines = autopilot.step_all(kho)
    assert len(lines) == 1
    assert "Tự động ghim" in lines[0]

    su_co = autopilot.storage_outage()
    assert su_co is not None
    assert su_co.active is False  # cửa sổ đã đóng…
    canh_bao = autopilot.storage_alarm()
    assert canh_bao is not None  # …nhưng KHÔNG bị xóa
    assert "kho dữ liệu đã chết" in canh_bao
    assert "KHÔNG ghim bù được" in canh_bao

    pins = [e for e in kho.list_exposure_events(sid) if e["source"] == "model"]
    assert [e["block_idx"] for e in pins] == [on_blocks[1]["block_index"]]


def test_loi_thuong_cua_mot_phien_khong_lam_dung_ca_vong_quet(app_client, kho, monkeypatch):
    """Chỉ lỗi KHO mới được dừng vòng quét. Một phiên hỏng vì lý do khác không
    được kéo theo các phiên khác — và cũng không được bịa ra một sự cố kho."""
    app, tc = app_client
    _seed_products(tc)
    sid, blocks = _live_session(tc)
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _dat_phien_tai(kho, sid, (on_block["start_offset_s"] + on_block["end_offset_s"]) / 2)

    def no_tung(*_args, **_kwargs):
        raise ValueError("bug thật trong bộ chọn sản phẩm")

    monkeypatch.setattr("livelift.api.routes.actions.execute_action", no_tung)
    assert autopilot.step_all(kho) == []
    assert autopilot.storage_outage() is None  # KHÔNG đổ cho kho
    assert "ValueError" in (autopilot.heartbeat(sid).last_error or "")


# ---------------------------------------------------------------------------
# 5. Toàn tuyến: kho chết giữa phiên -> spool -> kho sống -> nạp bù, không trùng
# ---------------------------------------------------------------------------


def test_toan_tuyen_kho_chet_giua_phien_roi_nap_bu_khong_trung_lap(app_client, kho, tmp_path):
    app, tc = app_client
    sid, blocks = _live_session(tc)

    async def gui(sink_kwargs: dict, comments: list[RawComment]) -> ApiSink:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=API_BASE)
        sink = ApiSink(
            api_url=API_BASE,
            session_id=sid,
            client=client,
            base_delay_s=0.0,
            token="",
            **sink_kwargs,
        )
        try:
            for c in comments:
                await sink.post_comment(c)
            return sink
        finally:
            await client.aclose()

    t0 = datetime.now(UTC)
    truoc = [RawComment("youtube", "LCC.truoc", t0, "áo này còn size M không")]
    trong = [
        RawComment("youtube", f"LCC.chet-{i}", t0 + timedelta(seconds=i), f"chốt đơn {i}")
        for i in range(5)
    ]

    # (a) Kho sống: bình luận vào thẳng cơ sở dữ liệu.
    asyncio.run(gui({"spool_dir": tmp_path}, truoc))
    assert len(kho.list_comments(sid)) == 1

    # (b) Rút dây giữa phiên.
    kho.chet = True
    sink = asyncio.run(gui({"spool_dir": tmp_path}, trong))
    assert sink.spool_mode is True
    assert sink.spooled == 5
    assert sink.dropped == 0

    spool_file = tmp_path / f"{sid}.jsonl"
    ext_ids_spool = [
        json.loads(line)["payload"]["ext_id"]
        for line in spool_file.read_text(encoding="utf-8").splitlines()
    ]
    assert ext_ids_spool == [c.ext_id for c in trong], "không bình luận nào được phép rơi"

    # (c) Kho sống lại — nhưng dữ liệu vẫn CHƯA có trong kho cho tới khi nạp bù.
    kho.chet = False
    assert len(kho.list_comments(sid)) == 1

    async def nap_bu() -> tuple[int, int]:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app))
        try:
            return await replay_file(spool_file, API_BASE, client=client)
        finally:
            await client.aclose()

    assert asyncio.run(nap_bu()) == (5, 0)
    assert {c["ext_id"] for c in kho.list_comments(sid)} == {"LCC.truoc"} | set(ext_ids_spool)

    # (d) Nạp bù hai lần (chuyện thường: chạy lại cho chắc) không nhân đôi gì.
    assert asyncio.run(nap_bu()) == (5, 0)
    assert len(kho.list_comments(sid)) == 6
