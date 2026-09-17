"""Nguồn bình luận MÔ PHỎNG — kiểm thử đầu-cuối không cần nền tảng (17/09/2026).

Ba client thật (YouTube/Facebook/Shopee) đều cần khoá mà máy nhóm chưa có, nên
trước tệp này không ai chạy được TRỌN đường ống. Các test ở đây khoá:

* lời khai nguồn gốc của kịch bản (dữ liệu tổng hợp, do AI soạn 17/09/2026) —
  tệp mất lời khai thì client TỪ CHỐI phát;
* thông tin cá nhân trong kịch bản chỉ là đồ GIẢ định dạng rõ ràng;
* nhịp phát theo hệ số tăng tốc, số người xem tất định;
* đường ống thật: ``IngestManager`` + ``StoreSink`` + ``InMemoryStore`` — bình
  luận vào kho đã lọc số điện thoại giả, có nhãn ý định, được phát lên kênh
  WebSocket, và hai lần chạy cho cùng kết quả;
* RÀNG BUỘC AN TOÀN: phiên thật bị từ chối (route 422 + manager tự chặn), phiên
  chạy thử/phiên mẫu được nhận.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.ingest_jobs import (
    LOI_MO_PHONG_PHIEN_THAT,
    NEN_TANG_THU,
    IngestManager,
    cho_phep_mo_phong,
    chuan_hoa_nguon,
    client_mac_dinh,
    muc_san_sang_nen_tang,
    phan_loai_loi,
)
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import get_settings
from livelift.ingest.mo_phong import (
    HE_SO_TOI_DA,
    NGAN_DEN_GIAY,
    TEP_KICH_BAN,
    KichBan,
    MoPhongLiveClient,
    chuan_hoa_nguon_mo_phong,
    chuoi_nguoi_xem,
    doc_kich_ban,
    doc_tep_kich_ban,
    phan_tich_nguon,
)
from livelift.ingest.pii import scrub

NHANH = {
    "restart_base_s": 0.01,
    "restart_cap_s": 0.02,
    "wait_for_live_s": 0.01,
    "watch_every_s": 0.02,
}

CHUOI_PII_GIA = ("0900", "900 000", "O9OO", "example.com", "Thử Nghiệm", "Giả Định", "Không Tên")


def _phien(store: InMemoryStore, *, dry_run: bool = False, is_demo: bool = False) -> str:
    sid = str(uuid.uuid4())
    now = datetime.now(UTC)
    store.create_session(
        {
            "session_id": sid,
            "platform": "sim",
            "title": "thử nguồn mô phỏng",
            "mode": "suggest",
            "status": "live",
            "planned_duration_min": 30,
            "host_id": None,
            "start_ts": now,
            "end_ts": None,
            "created_at": now,
            "dry_run": dry_run,
            "is_demo": is_demo,
        }
    )
    return sid


async def _cho(dieu_kien, timeout: float = 60.0) -> None:
    han = time.monotonic() + timeout
    while not dieu_kien():
        if time.monotonic() > han:
            raise AssertionError("hết giờ chờ điều kiện")
        await asyncio.sleep(0.01)


class DongHoGia:
    """Đồng hồ + hàm ngủ giả: ghi lại mọi lần ngủ, không chờ thật."""

    def __init__(self) -> None:
        self.bay_gio = 0.0
        self.lan_ngu: list[float] = []

    def dong_ho(self) -> float:
        return self.bay_gio

    async def ngu(self, giay: float) -> None:
        self.lan_ngu.append(giay)
        self.bay_gio += giay


# ---------------------------------------------------------------------------
# G2 — tệp kịch bản: nguồn gốc thật, PII chỉ là đồ giả, ý định đa dạng
# ---------------------------------------------------------------------------


def test_tep_kich_ban_khai_ro_du_lieu_tong_hop_va_nguon_goc():
    dau = json.loads(TEP_KICH_BAN.read_text(encoding="utf-8").splitlines()[0])
    assert dau["loai"] == "meta"
    assert dau["du_lieu_tong_hop"] is True
    assert "17/09/2026" in dau["nguon_goc"]
    assert "AI" in dau["nguon_goc"]
    assert dau["ngay_soan"] == "2026-09-17"
    assert "KHÔNG" in dau["cam_dung"], "phải cấm dùng làm dữ liệu huấn luyện/đánh giá"
    meta, dong = doc_tep_kich_ban()
    assert 150 <= len(dong) <= 250
    assert meta["so_dong"] == len(dong)


@pytest.mark.parametrize(
    ("meta", "loi"),
    [
        ({"loai": "meta", "nguon_goc": "x", "so_dong": 1}, "tổng hợp"),
        ({"loai": "meta", "du_lieu_tong_hop": "true", "nguon_goc": "x", "so_dong": 1}, "tổng hợp"),
        ({"loai": "meta", "du_lieu_tong_hop": True, "nguon_goc": "", "so_dong": 1}, "nguồn gốc"),
        ({"loai": "meta", "du_lieu_tong_hop": True, "nguon_goc": "x", "so_dong": 5}, "5 dòng"),
    ],
)
def test_tu_choi_tep_thieu_loi_khai_nguon_goc(tmp_path: Path, meta: dict, loi: str):
    tep = tmp_path / "kb.jsonl"
    dong = {"t": 1.0, "text": "chốt 1 áo", "nhom": "chot_don"}
    tep.write_text(
        json.dumps(meta, ensure_ascii=False) + "\n" + json.dumps(dong, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=loi):
        doc_tep_kich_ban(tep)


def test_tu_choi_tep_co_thoi_diem_lui(tmp_path: Path):
    tep = tmp_path / "kb.jsonl"
    meta = {"loai": "meta", "du_lieu_tong_hop": True, "nguon_goc": "x", "so_dong": 2}
    dong = [{"t": 5.0, "text": "a"}, {"t": 2.0, "text": "b"}]
    tep.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in [meta, *dong]), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="lùi"):
        doc_tep_kich_ban(tep)


def test_client_khong_phat_tep_mat_loi_khai(tmp_path: Path):
    tep = tmp_path / "kb.jsonl"
    tep.write_text(json.dumps({"t": 1, "text": "chốt"}) + "\n", encoding="utf-8")
    client = MoPhongLiveClient(he_so=1e6, tep=tep)

    async def chay():
        return [c async for c in client.iter_comments("")]

    with pytest.raises(ValueError) as exc:
        asyncio.run(chay())
    assert phan_loai_loi(exc.value) == "cau_hinh", "tệp sai là lỗi cấu hình: dừng, không thử lại"
    assert client.last_error is not None
    assert "tổng hợp" in client.last_error


def test_kich_ban_da_dang_y_dinh():
    _, dong = doc_tep_kich_ban()
    nhom = {d.nhom for d in dong}
    assert {
        "hoi_gia",
        "chot_don",
        "hoi_size",
        "van_chuyen",
        "che_dat",
        "cam_on_khen",
        "chao_hoi",
        "chi_so",
        "khac",
    } <= nhom
    chi_so = [d.text for d in dong if d.nhom == "chi_so"]
    assert len(chi_so) >= 10
    assert all(re.fullmatch(r"[A-Z]?\d{1,3}k?", t) for t in chi_so), chi_so


def test_thong_tin_ca_nhan_trong_kich_ban_chi_la_do_gia():
    """Mọi SĐT bộ lọc bắt được phải là số giả 0900 000 00x; email chỉ ở
    example.com. Ai lỡ dán một số thật vào kịch bản thì test này đỏ."""
    _, dong = doc_tep_kich_ban()
    co_pii = [d for d in dong if d.co_pii_gia]
    assert len(co_pii) >= 5
    for d in dong:
        ket = scrub(d.text)
        if d.co_pii_gia:
            assert ket.has_pii, f"dòng PII giả không bị lọc: stt={d.stt}"
        # Vị trí khớp tính trên bản đã chuẩn hoá (NFKC, bỏ dấu keycap) — cắt đúng bản đó.
        chuan = (
            unicodedata.normalize("NFKC", d.text).replace(chr(0xFE0F), "").replace(chr(0x20E3), "")
        )
        for m in ket.matches:
            doan = chuan[m.start : m.end]
            if m.kind == "phone":
                so = re.sub(r"\D", "", doan.replace("O", "0").replace("o", "0"))
                so = "0" + so[2:] if so.startswith("84") else so
                assert so.startswith("0900000"), f"SĐT không phải số giả: stt={d.stt}"
            if m.kind == "email":
                assert doan.endswith("@example.com")
    assert any(d.t <= NGAN_DEN_GIAY for d in co_pii), "bản 'ngan' cũng phải trình diễn bộ lọc"


# ---------------------------------------------------------------------------
# G1 — client: nguồn, nhịp phát, người xem tất định
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nguon", "mong_doi", "chuan"),
    [
        ("", ("mac_dinh", None), ""),
        ("  ", ("mac_dinh", None), ""),
        ("ngan", ("ngan", None), "ngan"),
        ("NGAN X10", ("ngan", 10.0), "ngan x10"),
        ("x2,5", ("mac_dinh", 2.5), "mac_dinh x2.5"),
        ("mac_dinh ×1000", ("mac_dinh", 1000.0), "mac_dinh x1000"),
        # Người bán gõ tiếng Việt có dấu — dạng lưu vẫn là tên không dấu.
        ("Ngắn x10", ("ngan", 10.0), "ngan x10"),
        ("mặc định", ("mac_dinh", None), "mac_dinh"),
        ("Mặc Định X2", ("mac_dinh", 2.0), "mac_dinh x2"),
    ],
)
def test_phan_tich_nguon(nguon, mong_doi, chuan):
    assert phan_tich_nguon(nguon) == mong_doi
    assert chuan_hoa_nguon_mo_phong(nguon) == chuan
    assert chuan_hoa_nguon("mo_phong", nguon) == chuan


@pytest.mark.parametrize(
    ("nguon", "loi"),
    [
        ("khong_co", "Không có kịch bản"),
        ("ngan mac_dinh", "tên kịch bản"),
        ("x0", "Hệ số tăng tốc"),
        (f"x{int(HE_SO_TOI_DA) + 1}", "Hệ số tăng tốc"),
        ("x2 x3", "một hệ số"),
    ],
)
def test_nguon_sai_bao_loi_tieng_viet(nguon, loi):
    with pytest.raises(ValueError, match=loi):
        chuan_hoa_nguon("mo_phong", nguon)


def test_client_phat_dung_nhip_voi_he_so_tang_toc():
    dh = DongHoGia()
    gio = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    client = MoPhongLiveClient(he_so=3.0, ngu=dh.ngu, dong_ho=dh.dong_ho, gio_utc=lambda: gio)
    kb = doc_kich_ban("ngan")

    async def chay():
        return [c async for c in client.iter_comments("ngan x10")]

    ra = asyncio.run(chay())
    assert [c.text for c in ra] == [d.text for d in kb.dong]
    # hệ số trong nguồn (x10) thắng hệ số của hàm dựng (3)
    assert sum(dh.lan_ngu) == pytest.approx(kb.dong[-1].t / 10)
    moc = [d.t / 10 for d in kb.dong]
    khoang = [b - a for a, b in zip([0.0, *moc], moc, strict=False) if b - a > 0]
    assert dh.lan_ngu == pytest.approx(khoang)
    assert {c.platform for c in ra} == {"sim"}
    assert len({c.ext_id for c in ra}) == len(ra)
    assert ra[0].ext_id == "sim-0000"
    assert all(c.ts_utc == gio and c.author_ext_id is None for c in ra)
    assert client.last_error is None


def test_ext_id_cua_ban_ngan_trung_voi_ban_day_du():
    """Chạy ``ngan`` rồi ``mac_dinh`` vào cùng phiên không nhân đôi bình luận."""
    ngan = [KichBan.ext_id(d) for d in doc_kich_ban("ngan").dong]
    day_du = [KichBan.ext_id(d) for d in doc_kich_ban("mac_dinh").dong]
    assert day_du[: len(ngan)] == ngan


def test_nguoi_xem_tat_dinh():
    def thu(client: MoPhongLiveClient, nguon: str) -> list[float]:
        async def chay():
            return [t.viewers async for t in client.iter_viewers(nguon)]

        return asyncio.run(chay())

    a = thu(MoPhongLiveClient(he_so=1e6), "")
    b = thu(MoPhongLiveClient(he_so=1e6), "")
    assert a == b
    assert len(a) >= 10
    assert all(v >= 1 for v in a)
    assert max(a) > a[0], "người xem phải tăng lên trong buổi, không phẳng"
    ngan = thu(MoPhongLiveClient(he_so=1e6), "ngan")
    assert ngan == a[: len(ngan)], "bản ngắn là phần đầu của cùng buổi"
    khac_seed = chuoi_nguoi_xem(doc_kich_ban(), seed=1)
    assert khac_seed != [int(v) for v in a]


def test_aclose_dung_phat():
    dh = DongHoGia()
    client = MoPhongLiveClient(he_so=1.0, ngu=dh.ngu, dong_ho=dh.dong_ho)

    async def chay():
        ra = []
        async for c in client.iter_comments(""):
            ra.append(c)
            if len(ra) == 3:
                await client.aclose()
        return ra

    assert len(asyncio.run(chay())) == 3


# ---------------------------------------------------------------------------
# G3 — đăng ký vào bộ thu nền
# ---------------------------------------------------------------------------


def test_dang_ky_vao_bo_thu_nen():
    assert "mo_phong" in NEN_TANG_THU
    assert isinstance(client_mac_dinh("mo_phong"), MoPhongLiveClient)
    muc = {m["platform"]: m for m in muc_san_sang_nen_tang(get_settings())}["mo_phong"]
    assert muc["ready"] is True
    assert muc["mode"] == "du_phong"
    assert muc["ten"] == "Mô phỏng (kiểm thử)"
    assert muc["missing"] == []
    assert "tổng hợp" in muc["note"]
    assert "chạy thử" in muc["note"]
    # Chữ cho người bán: thuật ngữ thống nhất, không lẫn từ kỹ thuật.
    assert "Bàn trợ live" in muc["note"]
    assert not any(t in muc["note"].lower() for t in ("đường ống", "pipeline", "demo"))
    assert "ngắn x10" in muc["source_hint"]


@pytest.mark.parametrize(
    ("phien", "duoc"),
    [
        (None, False),
        ({"dry_run": False, "is_demo": False}, False),
        ({}, False),
        ({"dry_run": True, "is_demo": False}, True),
        ({"dry_run": False, "is_demo": True}, True),
    ],
)
def test_cho_phep_mo_phong(phien, duoc):
    assert cho_phep_mo_phong(phien) is duoc


# ---------------------------------------------------------------------------
# G5 — đường ống thật: IngestManager + StoreSink + InMemoryStore
# ---------------------------------------------------------------------------


def _chay_ong_dan() -> tuple[list[tuple], dict, int]:
    store = InMemoryStore()
    sid = _phien(store, dry_run=True)

    async def chay():
        m = IngestManager(store, client_factory=lambda _p: MoPhongLiveClient(he_so=1e5), **NHANH)
        hang_doi = store.subscribe(sid)
        job = m.start(sid, "mo_phong", "")
        await _cho(lambda: not job.dang_chay)
        for _ in range(50):  # nhả các lần publish còn chờ trong vòng lặp
            await asyncio.sleep(0)
        so_tin_binh_luan = 0
        while not hang_doi.empty():
            if hang_doi.get_nowait()["type"] == "comment":
                so_tin_binh_luan += 1
        return job, so_tin_binh_luan

    job, so_tin = asyncio.run(chay())
    rows = sorted(store.list_comments(sid), key=lambda c: c["ext_id"])
    ket = [
        (c["platform"], c["ext_id"], c["text_scrubbed"], tuple(c["pii_kinds"]), c["intent_label"])
        for c in rows
    ]
    return ket, job.trang_thai(), so_tin


def test_ong_dan_that_loc_pii_phan_loai_phat_ws_va_tat_dinh():
    lan1, trang_thai, so_tin = _chay_ong_dan()
    _, dong = doc_tep_kich_ban()

    assert trang_thai["state"] == "nguon_ket_thuc"
    assert trang_thai["resolved_source"] == "mac_dinh"
    assert trang_thai["comments_posted"] == len(dong) == len(lan1)
    assert trang_thai["write_failures"] == 0
    assert trang_thai["ticks_posted"] >= 1
    assert so_tin == len(dong), "mọi bình luận phải được phát lên kênh WebSocket"
    assert {r[0] for r in lan1} == {"sim"}

    theo_ext = {KichBan.ext_id(d): d for d in dong}
    for _, ext_id, text, _pii, _y in lan1:
        assert not any(s in text for s in CHUOI_PII_GIA), f"PII giả lọt vào kho: {ext_id}"
        if theo_ext[ext_id].co_pii_gia:
            assert re.search(r"\[(SĐT|ĐỊA CHỈ|EMAIL)\]", text), f"thiếu dấu đã lọc: {ext_id}"
    assert sum("[SĐT]" in r[2] for r in lan1) >= 5
    assert len({r[4] for r in lan1}) >= 3, "bộ phân loại phải thấy nhiều ý định"

    lan2, _, _ = _chay_ong_dan()
    assert lan2 == lan1, "hai lần chạy phải cho cùng bình luận, cùng nhãn"


def test_pii_kinds_duoc_giu_qua_bo_thu_nen():
    """Hồi quy 17/09/2026: bộ thu lọc chữ tại nguồn nên máy chủ lọc lại không thấy
    gì; loại PII phải đi cùng bình luận qua ``CommentIn.pii_kinds``."""
    store = InMemoryStore()
    sid = _phien(store, dry_run=True)

    async def chay():
        m = IngestManager(store, client_factory=lambda _p: MoPhongLiveClient(he_so=1e5), **NHANH)
        job = m.start(sid, "mo_phong", "ngan")
        await _cho(lambda: not job.dang_chay)

    asyncio.run(chay())
    theo_ext = {KichBan.ext_id(d): d for d in doc_kich_ban("ngan").dong}
    co_pii = [c for c in store.list_comments(sid) if theo_ext[c["ext_id"]].co_pii_gia]
    assert co_pii
    assert all(c["pii_kinds"] for c in co_pii)


def test_manager_tu_chan_mo_phong_tren_phien_that():
    """Lớp chặn thứ hai: đường tự nối lại hay gọi thẳng manager không qua route."""
    store = InMemoryStore()
    sid_that = _phien(store)
    sid_mau = _phien(store, is_demo=True)

    async def chay():
        m = IngestManager(store, client_factory=lambda _p: MoPhongLiveClient(he_so=1e5), **NHANH)
        that = m.start(sid_that, "mo_phong", "ngan")
        mau = m.start(sid_mau, "mo_phong", "ngan")
        await _cho(lambda: not that.dang_chay and not mau.dang_chay)
        return that, mau

    that, mau = asyncio.run(chay())
    assert that.state == "loi"
    assert that.last_error == LOI_MO_PHONG_PHIEN_THAT
    assert store.list_comments(sid_that) == []
    assert mau.state == "nguon_ket_thuc"
    assert len(store.list_comments(sid_mau)) == len(doc_kich_ban("ngan").dong)


# ---------------------------------------------------------------------------
# G4 — endpoint: từ chối phiên thật, nhận phiên chạy thử
# ---------------------------------------------------------------------------


@pytest.fixture
def ung_dung(monkeypatch):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    store = InMemoryStore()
    # KHÔNG tiêm client giả: route phải dựng MoPhongLiveClient thật.
    app = create_app(store=store)
    with TestClient(app) as client:
        yield client, store
    get_settings.cache_clear()


def _tao_phien(client: TestClient, **kw) -> str:
    body = {"platform": "youtube", "planned_duration_min": 30, **kw}
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def _cho_http(client: TestClient, sid: str, dieu_kien, timeout: float = 20.0) -> dict:
    han = time.monotonic() + timeout
    while True:
        st = client.get(f"/sessions/{sid}/ingest").json()
        if dieu_kien(st):
            return st
        assert time.monotonic() < han, f"bộ thu không tới trạng thái mong đợi: {st}"
        time.sleep(0.02)


def test_route_tu_choi_phien_that(ung_dung):
    client, store = ung_dung
    sid = _tao_phien(client)
    r = client.post(
        f"/sessions/{sid}/ingest", json={"platform": "mo_phong", "source": "ngan x1000"}
    )
    assert r.status_code == 422
    assert r.json()["detail"].startswith(
        "Nguồn mô phỏng chỉ dùng cho phiên chạy thử hoặc phiên mẫu — không trộn vào dữ liệu thật"
    )
    assert client.get(f"/sessions/{sid}/ingest").json()["state"] == "chua_bat"
    assert store.list_comments(sid) == []


def test_route_nhan_phien_chay_thu_va_thu_tron_kich_ban(ung_dung):
    client, store = ung_dung
    sid = _tao_phien(client, dry_run=True)
    r = client.post(
        f"/sessions/{sid}/ingest", json={"platform": "mo_phong", "source": "NGAN x1000"}
    )
    assert r.status_code == 202, r.text
    assert r.json()["platform"] == "mo_phong"
    assert r.json()["source_id"] == "ngan x1000"

    st = _cho_http(client, sid, lambda s: not s["running"])
    assert st["state"] == "nguon_ket_thuc"
    so_dong = len(doc_kich_ban("ngan").dong)
    assert st["comments_posted"] == so_dong
    rows = store.list_comments(sid)
    assert len(rows) == so_dong
    assert {c["platform"] for c in rows} == {"sim"}
    assert not any("0900" in c["text_scrubbed"] for c in rows)


def test_route_phien_sim_mac_dinh_dung_mo_phong_va_phien_mau_duoc_nhan(ung_dung):
    client, store = ung_dung
    sid = _tao_phien(client, platform="sim", dry_run=True)
    r = client.post(f"/sessions/{sid}/ingest", json={"source": "ngan x1000"})
    assert r.status_code == 202, r.text
    assert r.json()["platform"] == "mo_phong"
    _cho_http(client, sid, lambda s: not s["running"])

    sid_mau = _phien(store, is_demo=True)
    r = client.post(
        f"/sessions/{sid_mau}/ingest", json={"platform": "mo_phong", "source": "Ngắn x1000"}
    )
    assert r.status_code == 202, r.text
    assert r.json()["source_id"] == "ngan x1000", "gõ có dấu vẫn được nhận"
    st = _cho_http(client, sid_mau, lambda s: not s["running"])
    assert st["state"] == "nguon_ket_thuc"


def test_route_nguon_mo_phong_sai_bao_422(ung_dung):
    client, _ = ung_dung
    sid = _tao_phien(client, dry_run=True)
    r = client.post(f"/sessions/{sid}/ingest", json={"platform": "mo_phong", "source": "khong_co"})
    assert r.status_code == 422
    assert "Không có kịch bản" in r.json()["detail"]
    r = client.post(f"/sessions/{sid}/ingest", json={"platform": "mo_phong", "source": "x5000"})
    assert r.status_code == 422
    assert "Hệ số tăng tốc" in r.json()["detail"]


def test_route_platforms_co_mo_phong_luon_san_sang(ung_dung):
    client, _ = ung_dung
    muc = {p["platform"]: p for p in client.get("/platforms").json()}
    assert muc["mo_phong"]["ready"] is True
    assert muc["mo_phong"]["mode"] == "du_phong"
    assert list(muc)[-1] == "mo_phong", "công cụ kiểm thử đứng cuối, sau các nền tảng thật"
