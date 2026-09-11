"""Báo cáo sau phiên GET /sessions/{id}/bao-cao.

Bốn quy tắc cứng được kiểm ở tầng HTTP:
- không-bịa-số: ô thiếu là None + lý do trong ``thieu``, không bao giờ 0 giả;
- phiên quan sát KHÔNG mang số nhân quả — mọi gợi ý là câu quan sát dán nhãn;
- phần nhân quả của phiên thí nghiệm đi đúng đường analyze_outer và bị khóa
  bởi RESULTS_FREEZE_UNTIL (tiền đăng ký §7, fail-closed với ngày hỏng);
- phân bố ý định luôn kèm caveat bắt buộc dẫn benchmark live-fire.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


def _seed(client, n_sessions=1, duration_min=60):
    r = client.post(
        "/demo/seed", json={"n_sessions": n_sessions, "effect": 0.5, "duration_min": duration_min}
    )
    assert r.status_code == 200, r.text
    return r.json()


def _bao_cao(client, sid):
    r = client.get(f"/sessions/{sid}/bao-cao")
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Phiên demo seed (thí nghiệm, đã kết thúc, đủ dữ liệu)
# ---------------------------------------------------------------------------


def test_bao_cao_on_seeded_experiment_session(client):
    seed = _seed(client)
    sid = seed["session_ids"][0]
    body = _bao_cao(client, sid)

    assert body["loai_phien"] == "thi_nghiem"
    assert "thí nghiệm" in body["nhan"]

    tq = body["tong_quan"]
    assert tq["thoi_luong_s"] == pytest.approx(3600.0)
    assert tq["tong_binh_luan"] > 0
    assert tq["dinh_binh_luan"] is not None
    assert tq["dinh_binh_luan"]["gia_tri_per_phut"] > 0
    assert tq["dinh_binh_luan"]["ts"] is not None
    # sim ticks mang viewers thật -> có tóm tắt người xem
    assert tq["nguoi_xem"] is not None
    assert tq["nguoi_xem"]["dinh"] >= tq["nguoi_xem"]["trung_binh"] > 0
    # demo seed ghi click -> lượt nhấp hợp lệ có giá trị
    assert tq["luot_nhap_hop_le"] is not None
    assert tq["luot_nhap_hop_le"] > 0
    # sim không có nguồn tim/quà -> ô reactions THIẾU kèm lý do, không 0 giả
    assert tq["reactions"] is None
    assert "reactions" in tq["thieu"]

    # ma trận tín hiệu nhúng thẳng trong báo cáo
    names = {s["name"] for s in body["tin_hieu"]}
    assert names == {"schedule", "ticks", "comments", "clicks", "orders", "reactions"}
    assert body["nang_luc"], "báo cáo phải nói phiên này hỗ trợ kết luận gì"

    # ý định: có phân bố + caveat bắt buộc dẫn benchmark
    yd = body["phan_bo_y_dinh"]
    assert yd["tong"] == tq["tong_binh_luan"]
    assert sum(yd["dem_theo_nhan"].values()) == yd["tong"]
    assert "live-fire-da-nguon.md" in yd["caveat"]
    assert "nhân quả" in yd["caveat"]

    # PII đã che theo loại (demo cố tình có SĐT + địa chỉ)
    assert body["pii_da_che"].get("phone", 0) >= 1

    # phần nhân quả tồn tại và không bị khóa (không đặt RESULTS_FREEZE_UNTIL)
    kq = body["ket_qua_thi_nghiem"]
    assert kq is not None
    assert kq["khoa"] is False
    assert kq["source"] == "experiment"
    assert kq["n_blocks"] >= 4
    assert kq["n_on"] + kq["n_off"] == kq["n_blocks"]

    # gợi ý chiến thuật: chỉ câu quan sát dán nhãn
    for cau in body["goi_y_chien_thuat"]:
        assert "quan sát" in cau
        assert "chưa kiểm chứng nhân quả" in cau


def test_bao_cao_khoanh_khac_from_controlled_spike(client):
    """Spike dựng tay: 14 tick nền 4 tin/phút rồi 1 tick 30 tin/phút — báo cáo
    phải khoanh đúng khoảnh khắc đó và mô tả bằng câu quan sát."""
    sid = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60}
    ).json()["session_id"]
    base = datetime(2026, 9, 11, 13, 0, 0, tzinfo=UTC)
    for i in range(15):
        rate = 30.0 if i == 14 else 4.0
        r = client.post(
            f"/sessions/{sid}/ticks",
            json={
                "viewers": 0.0,
                "comment_rate": rate,
                "ts_utc": (base + timedelta(seconds=30 * i)).isoformat(),
            },
        )
        assert r.status_code == 200, r.text

    body = _bao_cao(client, sid)
    assert body["loai_phien"] == "quan_sat"  # không lịch gán -> quan sát
    assert body["khoanh_khac_ghi_chu"] is None
    kks = body["khoanh_khac"]
    assert len(kks) == 1
    kk = kks[0]
    assert kk["binh_luan_per_phut"] == 30.0
    assert kk["offset_s"] == pytest.approx(14 * 30.0)
    assert kk["nen_per_phut"] == pytest.approx(4.0)
    assert "quan sát, chưa kiểm chứng nhân quả" in kk["mo_ta"]
    # đỉnh bình luận trong tổng quan trỏ cùng thời điểm
    assert body["tong_quan"]["dinh_binh_luan"]["gia_tri_per_phut"] == 30.0
    # gợi ý nhắc lại khoảnh khắc, vẫn dán nhãn quan sát
    assert any("phút 7" in c for c in body["goi_y_chien_thuat"])


# ---------------------------------------------------------------------------
# Phiên rỗng: mọi ô thiếu đều được TUYÊN BỐ
# ---------------------------------------------------------------------------


def test_bao_cao_on_empty_session_declares_every_gap(client):
    sid = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60}
    ).json()["session_id"]
    body = _bao_cao(client, sid)

    assert body["loai_phien"] == "quan_sat"
    assert "QUAN SÁT" in body["nhan"]
    assert body["ket_qua_thi_nghiem"] is None, "phiên quan sát không mang số nhân quả"

    tq = body["tong_quan"]
    assert tq["tong_binh_luan"] == 0
    for field in ("dinh_binh_luan", "nguoi_xem", "luot_nhap_hop_le", "reactions"):
        assert tq[field] is None, f"{field} phải là None, không phải 0 giả"
    for key in ("thoi_luong", "dinh_binh_luan", "nguoi_xem", "luot_nhap", "reactions"):
        assert tq["thieu"].get(key), f"thiếu lý do tiếng Việt cho ô {key}"

    assert body["khoanh_khac"] == []
    assert "quá ngắn" in body["khoanh_khac_ghi_chu"]
    assert body["phan_bo_y_dinh"]["tong"] == 0
    assert "live-fire-da-nguon.md" in body["phan_bo_y_dinh"]["caveat"]
    assert body["pii_da_che"] == {}


def test_bao_cao_unknown_session_is_404(client):
    assert client.get("/sessions/nope/bao-cao").status_code == 404


def test_bao_cao_includes_posted_reactions_with_public_amounts(client):
    sid = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60}
    ).json()["session_id"]
    for i, (kind, amount, currency) in enumerate(
        [("superchat", 50000, "₫"), ("superchat", 20000, "₫"), ("membership", None, None)]
    ):
        client.post(
            f"/sessions/{sid}/reactions",
            json={
                "kind": kind,
                "amount": amount,
                "currency": currency,
                "platform": "youtube",
                "ext_id": f"rx-{i}",
            },
        )
    tq = _bao_cao(client, sid)["tong_quan"]
    assert tq["reactions"] is not None
    assert tq["reactions"]["tong"] == 3
    assert tq["reactions"]["theo_loai"] == {"superchat": 2, "membership": 1}
    # tổng tiền CÔNG KHAI theo đơn vị; membership không tiền không đóng góp
    assert tq["reactions"]["tong_tien"] == {"₫": 70000.0}
    assert "reactions" not in tq["thieu"]


# ---------------------------------------------------------------------------
# Khóa §7 (RESULTS_FREEZE_UNTIL) trên phần nhân quả của báo cáo
# ---------------------------------------------------------------------------


def _bao_cao_with_freeze(client, monkeypatch, sid: str, value: str):
    from livelift.config import get_settings

    monkeypatch.setenv("RESULTS_FREEZE_UNTIL", value)
    get_settings.cache_clear()
    try:
        return _bao_cao(client, sid)
    finally:
        monkeypatch.delenv("RESULTS_FREEZE_UNTIL", raising=False)
        get_settings.cache_clear()


def test_bao_cao_causal_part_locked_before_freeze_date(client, monkeypatch):
    sid = _seed(client)["session_ids"][0]
    body = _bao_cao_with_freeze(client, monkeypatch, sid, "2999-01-01")

    kq = body["ket_qua_thi_nghiem"]
    assert kq["khoa"] is True
    assert "§7" in kq["ly_do_khoa"]
    assert kq["estimable"] is False
    for field in ("estimate", "ci_low", "ci_high", "p_value", "n_draws"):
        assert kq[field] is None, f"{field} lọt qua khóa §7 trong bao-cao"
    # số vận hành §7 cho phép vẫn được phục vụ
    assert kq["n_blocks"] > 0
    assert body["tong_quan"]["tong_binh_luan"] > 0
    assert body["khoanh_khac"] is not None


def test_bao_cao_causal_part_unlocked_after_freeze_date(client, monkeypatch):
    sid = _seed(client)["session_ids"][0]
    body = _bao_cao_with_freeze(client, monkeypatch, sid, "2000-01-01")
    kq = body["ket_qua_thi_nghiem"]
    assert kq["khoa"] is False
    assert kq["ly_do_khoa"] is None


def test_bao_cao_malformed_freeze_date_fails_closed(client, monkeypatch):
    sid = _seed(client)["session_ids"][0]
    kq = _bao_cao_with_freeze(client, monkeypatch, sid, "11/09/2026")["ket_qua_thi_nghiem"]
    assert kq["khoa"] is True
    assert "không hợp lệ" in kq["ly_do_khoa"]
    assert kq["estimate"] is None


def test_bao_cao_observational_session_with_comments_stays_causal_free(client):
    """Phiên có bình luận nhưng không lịch gán: báo cáo mô tả được nhịp chat
    nhưng tuyệt đối không sinh câu/số nhân quả."""
    sid = client.post(
        "/sessions", json={"platform": "replay", "mode": "auto", "planned_duration_min": 30}
    ).json()["session_id"]
    for text in ("giá bao nhiêu shop", "chốt 1 đơn nha", "ship về Hà Nội không"):
        client.post(f"/sessions/{sid}/comments", json={"text": text})

    body = _bao_cao(client, sid)
    assert body["loai_phien"] == "quan_sat"
    assert body["ket_qua_thi_nghiem"] is None
    assert body["tong_quan"]["tong_binh_luan"] == 3
    assert sum(body["phan_bo_y_dinh"]["dem_theo_nhan"].values()) == 3
    for cau in body["goi_y_chien_thuat"]:
        assert "quan sát" in cau


def test_goi_y_shows_vietnamese_label_not_snake_case_key():
    """Câu 'ý định xuất hiện nhiều nhất' phải in tên tiếng Việt có dấu
    ('Chốt đơn'), không lộ khóa nội bộ snake_case ('chot_don') — bắt gặp trên
    báo cáo buổi Achan 11/09 (quy tắc chuỗi hiển thị tiếng Việt)."""
    from livelift.api.routes.reports import _bao_cao_goi_y

    goi_y = _bao_cao_goi_y([], {"chot_don": 5, "khac": 10}, 15)
    dominant = [c for c in goi_y if "xuất hiện nhiều nhất" in c]
    assert dominant, "phải có câu về ý định trội khi có nhãn đáng chú ý"
    assert "'Chốt đơn'" in dominant[0]
    assert "chot_don" not in dominant[0]
    # nhãn lạ (chưa có tên hiển thị) không được làm vỡ câu — in nguyên khóa
    goi_y2 = _bao_cao_goi_y([], {"nhan_moi_chua_dat_ten": 2}, 2)
    assert any("nhan_moi_chua_dat_ten" in c for c in goi_y2)
