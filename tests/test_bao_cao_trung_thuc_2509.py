"""Phần nhân quả của báo cáo phải TRUNG THỰC ở hai chỗ kiểm toán 25/09/2026 bắt được.

1. **Sập trang ``/ket-qua?phien=`` (runtime.md 3.0, P1).** Phiên chạy thử có ≥ 4
   khối đo được nhưng 0 lượt nhấp (không tạo link đo, hoặc có link mà chưa ai
   bấm). Máy chủ trả ``estimable=true, estimate=0.0, ci_low=null,
   ci_high=null, p_value=1.0`` — trình duyệt gọi ``ciLow.toFixed`` trên null và
   trang sập. Tệ hơn cả cú sập: chỉ số chính đang THIẾU nguồn (ma trận tín hiệu
   ghi ``clicks: missing``) mà báo cáo vẫn in "ước lượng 0.000", trái luật
   "THIẾU không phải 0". Luật từ nay, ở CẢ báo cáo một phiên lẫn bản gộp:
   ``estimable=true`` thì estimate, ci_low, ci_high, p_value đều phải là số.

2. **Nhìn trộm giữa phiên (runtime.md 3.9 / mục 5, P2).** Khi
   ``RESULTS_FREEZE_UNTIL`` để trống (mặc định), ``/bao-cao`` của một phiên
   KHÔNG phải demo đang ``live`` vẫn chạy estimator ngay khi đủ 4 khối — tức là
   ai mở trang giữa buổi là thấy ước lượng nhân quả trước khi thí nghiệm xong
   (trái PREREGISTRATION §7). Phiên chưa kết thúc nay bị khoá với lý do
   "Phiên đang chạy"; phiên demo vẫn được miễn như cũ (không có gì thật để
   nhìn trộm), và khoá §7 theo ngày vẫn giữ nguyên.
"""

from __future__ import annotations

import random
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from livelift.api import service
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.core.assigner import DesignParams

TRUONG_SO = ("estimate", "ci_low", "ci_high", "p_value")


@pytest.fixture
def ung_dung():
    store = InMemoryStore()
    with TestClient(create_app(store=store)) as c:
        yield c, store


def _phien(
    store,
    *,
    thoi_luong_min: int = 40,
    phat_duoc_min: int | None = None,
    ket_thuc: bool = True,
    dry_run: bool = False,
    tao_link: bool = False,
    luot_nhap_moi_phut: float = 0.0,
    luot_nhap_hop_le: bool = True,
    seed: int = 7,
    bat_dau_cach_day_min: int = 120,
) -> str:
    """Một phiên KHÔNG phải demo đi qua đúng đường lịch/bắt đầu của máy chủ.

    Người xem có mặt suốt thời gian phát (tick 30 giây, 40 người) nên mọi khối
    đã phát đều đo được; lượt nhấp chỉ có khi được yêu cầu — đúng cấu hình của
    buổi tập dượt làm sập trang (bộ thu Mô phỏng, không ai bấm link).
    """
    now = service.now_utc()
    start_ts = now - timedelta(minutes=bat_dau_cach_day_min)
    session = store.create_session(
        {
            "session_id": service.new_id(),
            "platform": "youtube",
            "title": "Phiên kiểm toán 25/09",
            "mode": "auto",
            "status": "planned",
            "planned_duration_min": thoi_luong_min,
            "host_id": None,
            "start_ts": None,
            "end_ts": None,
            "design": None,
            "created_at": now,
            "is_demo": False,
            "dry_run": dry_run,
        }
    )
    sid = session["session_id"]
    session, _ = service.schedule_session(store, session, DesignParams(jitter_s=0), seed)
    service.start_session(store, session, start_ts)

    phat_s = (thoi_luong_min if phat_duoc_min is None else phat_duoc_min) * 60
    for t in range(0, phat_s, 30):
        store.add_tick(
            sid,
            {
                "ts_bucket": start_ts + timedelta(seconds=t),
                "viewers": 40.0,
                "comment_rate": 0.0,
                "like_rate": 0.0,
                "click_count": 0,
                "pinned_product_id": None,
            },
        )
    if tao_link or luot_nhap_moi_phut > 0:
        store.create_product(
            {
                "product_id": f"SP-{sid[:8]}",
                "name": "Áo khoác dù",
                "category": "test",
                "cost": 50000,
                "price": 120000,
                "stock": 30,
                "created_at": now,
            }
        )
        store.create_shortlink(
            {
                "code": f"kt{sid[:8]}",
                "product_id": f"SP-{sid[:8]}",
                "session_id": sid,
                "target_url": "https://shop.example/ao-khoac",
                "created_at": now,
            }
        )
    if luot_nhap_moi_phut > 0:
        rng = random.Random(seed)
        n = int(luot_nhap_moi_phut * phat_s / 60)
        for _ in range(n):
            store.add_click(
                sid,
                {
                    "click_id": service.new_id(),
                    "block_id": None,
                    "ts": start_ts + timedelta(seconds=rng.uniform(0, phat_s - 1)),
                    "product_id": f"SP-{sid[:8]}",
                    "shortlink_code": f"kt{sid[:8]}",
                    "dedup_hash": None,
                    # False = bộ lọc GIVT-lite gắn cờ (bot/xem trước link/bấm dồn).
                    **({} if luot_nhap_hop_le else {"is_valid": False, "invalid_reason": "bot"}),
                },
            )
    if ket_thuc:
        store.update_session(
            sid, {"status": "ended", "end_ts": start_ts + timedelta(seconds=phat_s)}
        )
    return sid


def _ket_qua(client, sid) -> dict:
    r = client.get(f"/sessions/{sid}/bao-cao")
    assert r.status_code == 200, r.text
    return r.json()["ket_qua_thi_nghiem"]


def _khong_bao_gio_estimable_voi_so_rong(kq: dict) -> None:
    if kq["estimable"]:
        rong = [f for f in TRUONG_SO if kq[f] is None]
        assert not rong, (
            f"estimable=true mà {rong} là null — trang Kết quả gọi toFixed trên null và sập "
            f"(kiểm toán 25/09, runtime.md 3.0). Payload: {kq}"
        )


# ---------------------------------------------------------------------------
# 1. Không bao giờ estimable=true với KTC null
# ---------------------------------------------------------------------------


def test_bao_cao_khong_link_do_0_luot_nhap_tuyen_bo_thieu_khong_in_so_0(ung_dung):
    """Đúng kịch bản làm sập trang: ≥ 4 khối, bộ thu Mô phỏng, không link đo."""
    client, store = ung_dung
    sid = _phien(store, dry_run=True)

    kq = _ket_qua(client, sid)
    assert kq["n_blocks"] >= 4, "phải đủ khối để estimator được gọi — đúng điều kiện sập"
    _khong_bao_gio_estimable_voi_so_rong(kq)
    assert kq["estimable"] is False, "chỉ số chính THIẾU nguồn thì không có ước lượng"
    for f in (*TRUONG_SO, "n_draws"):
        assert kq[f] is None, f"{f} phải để trống khi chỉ số chính THIẾU — THIẾU không phải 0"
    assert "link đo" in kq["message"], f"lý do phải nói thiếu gì: {kq['message']!r}"

    # Ba câu tóm tắt cũng không được in một ước lượng 0 cho chỉ số đang THIẾU.
    tom_tat = client.get(f"/sessions/{sid}/bao-cao").json()["tom_tat_3_cau"]
    chu = " ".join(c["text"] for c in tom_tat)
    assert "0.000" not in chu, chu
    assert "link đo" in chu


def test_bao_cao_co_link_nhung_0_luot_nhap_ktc_khong_tinh_duoc_thi_khong_estimable(ung_dung):
    """Có link đo nhưng chưa ai bấm: tín hiệu 'degraded', estimator chạy nhưng
    thống kê kiểm định không xác định (mọi khối đều 0) nên KTC là NaN."""
    client, store = ung_dung
    sid = _phien(store, dry_run=True, tao_link=True)

    kq = _ket_qua(client, sid)
    assert kq["n_blocks"] >= 4
    _khong_bao_gio_estimable_voi_so_rong(kq)
    assert kq["estimable"] is False
    assert "khoảng tin cậy" in kq["message"].lower(), kq["message"]


def test_bao_cao_phien_du_luot_nhap_van_co_uoc_luong(ung_dung):
    """Đối chứng dương: sửa không được biến mọi phiên thành 'thiếu'."""
    client, store = ung_dung
    sid = _phien(store, luot_nhap_moi_phut=3.0)

    kq = _ket_qua(client, sid)
    assert kq["khoa"] is False
    assert kq["estimable"] is True, kq["message"]
    for f in TRUONG_SO:
        assert kq[f] is not None, f"{f} phải có số khi ước lượng được"


def test_bao_cao_moi_luot_nhap_bi_loc_givt_khong_khuyen_tao_link(ung_dung):
    """Phản biện 25/09/2026: 0 lượt HỢP LỆ trên N lượt thô (GIVT-lite gắn cờ hết)
    cũng là ``clicks=missing`` — nhưng link đo ĐÃ có và đang nhận traffic. Câu
    "Việc nên làm: tạo link đo…" ở đây là lời khuyên sai việc."""
    client, store = ung_dung
    sid = _phien(store, luot_nhap_moi_phut=3.0, luot_nhap_hop_le=False)

    body = client.get(f"/sessions/{sid}/bao-cao").json()
    kq = body["ket_qua_thi_nghiem"]
    _khong_bao_gio_estimable_voi_so_rong(kq)
    assert kq["estimable"] is False
    assert kq["message"].startswith("Chỉ số chính"), kq["message"]
    viec = body["tom_tat_3_cau"][2]["text"]
    assert viec.startswith("Việc nên làm"), viec
    assert "tạo link đo" not in viec, f"link đo đã có, đang nhận traffic bị lọc: {viec!r}"
    assert "gắn cờ" in viec, viec


def test_bao_cao_phien_da_huy_khong_khuyen_tiep_tuc_chay(ung_dung):
    """Phản biện 25/09/2026: phiên huỷ chỉ đến được từ planned/scheduled — chưa
    từng lên sóng và không bao giờ kết thúc. Câu khoá không được nói "phát sóng
    xong", và câu việc nên làm không được bảo "tiếp tục chạy phiên theo lịch"."""
    client, _ = ung_dung
    sid = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 40}
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 3})
    assert client.post(f"/sessions/{sid}/cancel").status_code == 200

    body = client.get(f"/sessions/{sid}/bao-cao").json()
    kq = body["ket_qua_thi_nghiem"]
    assert kq["khoa"] is True
    assert kq["ly_do_khoa"].startswith("Phiên đã huỷ"), kq["ly_do_khoa"]
    assert "phát sóng xong" not in kq["ly_do_khoa"], "phiên huỷ chưa từng lên sóng"
    viec = body["tom_tat_3_cau"][2]["text"]
    assert "tiếp tục chạy phiên" not in viec, viec


def test_ban_gop_hai_phien_0_luot_nhap_khong_estimable_voi_ktc_null(ung_dung):
    """Rủi ro runtime.md nêu mà chưa tái hiện: bản gộp dùng cùng component nên
    ≥ 2 phiên thật đã kết thúc đều 0 lượt nhấp cũng làm sập /ket-qua."""
    client, store = ung_dung
    for seed in (7, 8):
        _phien(store, tao_link=True, seed=seed)

    body = client.get("/experiment/summary").json()
    assert body["n_sessions"] == 2
    assert body["n_blocks"] >= 8
    _khong_bao_gio_estimable_voi_so_rong(body)
    assert body["estimable"] is False
    assert body["message"], "không ước lượng thì phải nói vì sao"


# ---------------------------------------------------------------------------
# 2. Không nhìn trộm giữa phiên (phiên KHÔNG phải demo)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dry_run", [False, True], ids=["phien-that", "chay-thu"])
def test_bao_cao_phien_dang_chay_bi_khoa_du_da_du_khoi(ung_dung, dry_run):
    client, store = ung_dung
    sid = _phien(
        store,
        thoi_luong_min=60,
        phat_duoc_min=45,
        ket_thuc=False,
        dry_run=dry_run,
        luot_nhap_moi_phut=3.0,
        bat_dau_cach_day_min=45,
    )
    assert store.get_session(sid)["status"] == "live"

    kq = _ket_qua(client, sid)
    assert kq["n_blocks"] >= 4, "đủ khối — trước bản vá estimator đã chạy ở đây"
    assert kq["khoa"] is True, "phiên đang chạy mà trả ước lượng là nhìn trộm (§7)"
    assert "Phiên đang chạy" in kq["ly_do_khoa"]
    assert kq["estimable"] is False
    for f in (*TRUONG_SO, "n_draws"):
        assert kq[f] is None, f"{f} lọt ra khi phiên còn đang chạy"
    # Số vận hành vẫn được phục vụ.
    assert kq["n_on"] + kq["n_off"] == kq["n_blocks"]

    # Kết thúc phiên thì khoá tự mở — cùng dữ liệu, cùng đường phân tích.
    client.post(f"/sessions/{sid}/end")
    kq = _ket_qua(client, sid)
    assert kq["khoa"] is False
    assert kq["estimable"] is True, kq["message"]


def test_bao_cao_phien_chua_len_song_bi_khoa(ung_dung):
    client, store = ung_dung
    sid = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 40}
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 3})

    kq = _ket_qua(client, sid)
    assert kq["khoa"] is True
    assert kq["estimable"] is False
    assert kq["ly_do_khoa"]


def test_bao_cao_phien_demo_dang_phat_van_duoc_mien_khoa(ung_dung):
    """Demo không có gì thật để nhìn trộm — giữ nguyên miễn trừ của gói DEMO-THẬT."""
    client, store = ung_dung
    client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 40})
    dang_phat = [s for s in store.list_sessions() if s.get("status") == "live"]
    assert dang_phat, "/demo/seed phải có một phiên đang phát"
    for s in dang_phat:
        assert s.get("is_demo") is True
        kq = client.get(f"/sessions/{s['session_id']}/bao-cao").json()["ket_qua_thi_nghiem"]
        assert kq is not None, "phiên demo đang phát là phiên thí nghiệm — phải có khối nhân quả"
        assert kq["khoa"] is False


def test_khoa_theo_ngay_7_van_uu_tien_tren_phien_dang_chay(ung_dung, monkeypatch):
    from livelift.config import get_settings

    client, store = ung_dung
    sid = _phien(
        store,
        thoi_luong_min=60,
        phat_duoc_min=45,
        ket_thuc=False,
        luot_nhap_moi_phut=3.0,
        bat_dau_cach_day_min=45,
    )
    monkeypatch.setenv("RESULTS_FREEZE_UNTIL", "2999-01-01")
    get_settings.cache_clear()
    try:
        kq = _ket_qua(client, sid)
    finally:
        monkeypatch.delenv("RESULTS_FREEZE_UNTIL", raising=False)
        get_settings.cache_clear()
    assert kq["khoa"] is True
    assert "§7" in kq["ly_do_khoa"]
    assert "2999-01-01" in kq["ly_do_khoa"], "khoá theo ngày giữ nguyên câu chữ cũ"
