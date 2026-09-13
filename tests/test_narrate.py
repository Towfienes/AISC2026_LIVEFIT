"""Gói KẾT-QUẢ — tóm tắt 3 câu (AI-LAYER lớp 0, analysis/narrate.py).

Máy soạn câu TẤT ĐỊNH: template có kiểm soát, không LLM, mọi con số trong câu
chép từ đầu vào. Các bất biến bị khóa ở đây:

* luôn ĐÚNG 3 câu, cho CẢ BA trạng thái (DƯƠNG / NULL / CHƯA ĐỦ ĐIỀU KIỆN) —
  và trạng thái NULL được soạn như một KẾT QUẢ HỢP LỆ, không phải lời xin lỗi
  (phản biện khoa học ưu tiên #6);
* huy hiệu ``thi_nghiem`` KHÔNG BAO GIỜ xuất hiện khi thiết kế không ước
  lượng được (chốt chống vượt rào của spec AI-LAYER);
* khóa §7: khi ``khoa=True`` không câu nào chứa ước lượng/KTC/p;
* không bịa số: mọi token số trong câu truy được về đầu vào hoặc ngưỡng
  thiết kế đã khai báo (kiểm bằng bộ trích số đối kháng);
* API: ``/experiment/summary`` và ``/sessions/{id}/bao-cao`` mang
  ``tom_tat_3_cau`` khớp trạng thái — kiểm trên đúng BỘ PHIÊN DEMO VÀNG
  (docs/demo-vang.md) vốn phủ đủ ba trạng thái.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from livelift.analysis import narrate
from livelift.analysis.narrate import (
    BADGE_QUAN_SAT,
    BADGE_THI_NGHIEM,
    BADGE_THIEU_DU_LIEU,
    tom_tat_gop,
    tom_tat_phien,
    trang_thai_ket_luan,
)
from livelift.api.main import create_app
from livelift.api.routes.demo import seed_demo_vang
from livelift.api.store import InMemoryStore

# ---------------------------------------------------------------------------
# Bộ trích số đối kháng — "không bịa số" kiểm bằng máy, không bằng lời hứa
# ---------------------------------------------------------------------------

_SO_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _cac_so(text: str) -> set[str]:
    """Mọi token số trong câu, chuẩn hóa dấu phẩy thập phân về dấu chấm."""
    return {m.replace(",", ".") for m in _SO_RE.findall(text)}


def _so_cho_phep(*values: object) -> set[str]:
    """Tập token số hợp lệ sinh từ CHÍNH các đầu vào, qua đúng các phép định
    dạng mà narrate được phép dùng (làm tròn, %, phút, |x|, p-floor)."""
    ra: set[str] = set()
    for v in values:
        if v is None:
            continue
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            ra.add(str(v))
            ra.add(str(abs(v)))
        elif isinstance(v, float):
            ra.add(f"{abs(v):.3f}")
            ra.add(f"{abs(v):.2f}")
            ra.add(f"{abs(v):.4f}")
            ra.add(f"{abs(v) * 100:.0f}")
            ra.add(f"{v / 60:.0f}")  # giây -> phút
            ra.add(str(int(abs(v))))
    return ra


def _khong_bia_so(cau_list: list[narrate.Cau], *allowed_values: object) -> None:
    allowed = _so_cho_phep(*allowed_values)
    # hằng đơn vị của biến kết quả chính xuất hiện trong mọi câu kết luận
    allowed |= {"1000", "95", "0", "7"}  # 1000 giây·người xem, KTC 95%, chứa 0, §7
    for c in cau_list:
        for so in _cac_so(c.text):
            assert so in allowed, f"số {so!r} không truy được nguồn trong câu: {c.text!r}"


# ---------------------------------------------------------------------------
# Thuần: trạng thái kết luận
# ---------------------------------------------------------------------------


def test_trang_thai_ket_luan_phan_loai_du_bon_nhanh():
    assert trang_thai_ket_luan(False, None, None) == "thieu"
    assert trang_thai_ket_luan(True, 0.3, 1.2) == "duong"
    assert trang_thai_ket_luan(True, -1.2, -0.3) == "am"
    assert trang_thai_ket_luan(True, -0.2, 0.5) == "null"


# ---------------------------------------------------------------------------
# Thuần: bản gộp — ba trạng thái + khóa §7
# ---------------------------------------------------------------------------

GOP_DUONG = {
    "estimable": True,
    "estimate": 1.224,
    "ci_low": 0.932,
    "ci_high": 1.498,
    "p_value": 0.000999,
    "n_draws": 1000,
    "n_sessions": 3,
    "n_blocks": 48,
    "n_on": 24,
    "n_off": 24,
    "valid_clicks": 310,
    "measured_cv": 0.62,
    "measured_compliance": 0.94,
}


def test_gop_duong_ket_luan_bang_chung_viec_lam():
    cau = tom_tat_gop(**GOP_DUONG)
    assert len(cau) == 3, "tóm tắt PHẢI đúng 3 câu"
    assert "tạo thêm +1.224" in cau[0].text
    assert "không chứa 0" in cau[0].text
    assert cau[0].badge == BADGE_THI_NGHIEM
    assert "48 khối" in cau[1].text
    assert "24 BẬT / 24 TẮT" in cau[1].text
    assert "p < 0.0010" in cau[1].text, "p chạm sàn hoán vị phải in sàn, không in số giả"
    assert "tuân thủ đo được 94%" in cau[2].text
    assert "giữ nguyên" in cau[2].text.lower()
    _khong_bia_so(cau, *GOP_DUONG.values())
    # refs: mỗi câu phải khai nguồn số
    assert all(c.refs for c in cau)


def test_gop_null_la_ket_qua_hop_le_va_giai_k_tu_bang_luc():
    power = [
        {
            "scenario": "không đối tác (18 phiên)",
            "n_sessions": 18,
            "blocks_per_session": 16,
            "n_blocks_total": 288,
            "cv": 0.62,
            "mde_relative": 0.21,
        }
    ]
    cau = tom_tat_gop(
        estimable=True,
        estimate=0.206,
        ci_low=-0.031,
        ci_high=0.396,
        p_value=0.14,
        n_draws=1000,
        n_sessions=2,
        n_blocks=32,
        n_on=16,
        n_off=16,
        power_table=power,
    )
    assert len(cau) == 3
    assert "Chưa đủ bằng chứng" in cau[0].text
    assert "kết quả hợp lệ" in cau[0].text, "NULL phải được nói như kết quả, không như lỗi"
    assert "còn chứa 0" in cau[0].text
    # k = 18 - 2 = 16, giải từ bảng lực với CV đo được — không hardcode
    assert "thêm ~16 phiên" in cau[2].text
    assert "21%" in cau[2].text
    assert "0.62" in cau[2].text
    assert cau[2].badge == BADGE_THIEU_DU_LIEU
    _khong_bia_so(cau, 0.206, -0.031, 0.396, 0.14, 1000, 2, 32, 16, 16, 18, 16, 0.62, 0.21, 288)


def test_gop_am_noi_thang_tac_dung_nguoc():
    cau = tom_tat_gop(
        estimable=True,
        estimate=-0.8,
        ci_low=-1.2,
        ci_high=-0.4,
        p_value=0.002,
        n_draws=1000,
        n_sessions=2,
        n_blocks=32,
        n_on=16,
        n_off=16,
    )
    assert "GIẢM" in cau[0].text
    assert "phép đo thật" in cau[0].text


def test_gop_thieu_tuyen_bo_thieu_bang_so():
    cau = tom_tat_gop(
        estimable=False,
        message="Chưa đủ dữ liệu cho phân tích gộp (cần ≥ 2 phiên đã kết thúc và ≥ 8 khối).",
        n_sessions=1,
        n_blocks=3,
        n_on=2,
        n_off=1,
        valid_clicks=12,
    )
    assert len(cau) == 3
    assert cau[0].text.startswith("Thiết kế chưa đủ điều kiện")
    assert "thêm 1 phiên" in cau[2].text
    assert "thêm 5 khối" in cau[2].text
    # CHỐT CHỐNG VƯỢT RÀO: không ước lượng được thì không câu nào mang huy
    # hiệu thí nghiệm (spec AI-LAYER — badge thi_nghiem chỉ từ analyze_outer).
    assert all(c.badge != BADGE_THI_NGHIEM for c in cau)


def test_gop_khoa_7_khong_lo_uoc_luong_ke_ca_khi_duoc_truyen():
    """Khóa §7 đứng trên template: truyền cả bộ số suy diễn vào, không câu nào
    được nhắc tới ước lượng/KTC/p."""
    ly_do = (
        "Tiền đăng ký §7: ước lượng hiệu ứng bị khóa đến 2026-11-02 — chỉ hiển thị số liệu vận hành"
    )
    cau = tom_tat_gop(
        estimable=False,
        khoa=True,
        ly_do_khoa=ly_do,
        # cố tình truyền số suy diễn — phải bị lờ đi
        estimate=1.234,
        ci_low=0.9,
        ci_high=1.5,
        p_value=0.001,
        n_draws=1000,
        n_sessions=4,
        n_blocks=64,
        n_on=32,
        n_off=32,
        valid_clicks=200,
    )
    assert len(cau) == 3
    assert ly_do in cau[0].text, "lý do khóa phải được chép nguyên văn"
    ca_ba = " ".join(c.text for c in cau)
    for cam in ("1.234", "0.9", "1.5", "KTC", "p =", "p <"):
        assert cam not in ca_ba, f"khóa §7 mà vẫn lộ {cam!r}"
    assert all(c.badge != BADGE_THI_NGHIEM for c in cau)


# ---------------------------------------------------------------------------
# Thuần: bản từng phiên — quan sát + ba trạng thái
# ---------------------------------------------------------------------------


def test_phien_quan_sat_khong_cau_nao_nhan_qua():
    cau = tom_tat_phien(
        loai_phien="quan_sat",
        tong_binh_luan=1234,
        luot_nhap_hop_le=None,
        thoi_luong_s=5400.0,
    )
    assert len(cau) == 3
    assert "Phiên quan sát" in cau[0].text
    assert cau[0].badge == BADGE_QUAN_SAT
    assert "1234 bình luận" in cau[1].text
    assert "THIẾU nguồn" in cau[1].text, "lượt nhấp không có phải nói THIẾU, không phải 0"
    assert "90 phút" in cau[1].text
    assert all(c.badge != BADGE_THI_NGHIEM for c in cau)


def test_phien_thieu_dieu_kien_dung_ly_do_may_chu():
    msg = "Chưa đủ khối đo được để ước lượng (3 khối, cần ≥ 4) — tuyên bố thiếu, không trả số."
    cau = tom_tat_phien(
        loai_phien="thi_nghiem",
        tong_binh_luan=40,
        luot_nhap_hop_le=5,
        thoi_luong_s=900.0,
        estimable=False,
        n_blocks=3,
        n_on=2,
        n_off=1,
        message=msg,
    )
    assert msg in cau[0].text
    assert cau[0].badge == BADGE_THIEU_DU_LIEU
    assert "3 khối" in cau[1].text
    assert "4 khối đo được" in cau[2].text
    assert all(c.badge != BADGE_THI_NGHIEM for c in cau)


def test_phien_duong_va_null_du_ba_cau_co_so():
    chung = {
        "loai_phien": "thi_nghiem",
        "tong_binh_luan": 150,
        "luot_nhap_hop_le": 88,
        "thoi_luong_s": 5400.0,
        "estimable": True,
        "p_value": 0.01,
        "n_draws": 1000,
        "n_blocks": 16,
        "n_on": 8,
        "n_off": 8,
    }
    duong = tom_tat_phien(**chung, estimate=1.224, ci_low=0.932, ci_high=1.498)
    assert "tạo thêm +1.224" in duong[0].text
    assert duong[0].badge == BADGE_THI_NGHIEM
    assert "16 khối" in duong[1].text
    assert "một phiên chưa phải chuỗi" in duong[2].text.lower()

    null = tom_tat_phien(**chung, estimate=0.206, ci_low=-0.031, ci_high=0.396)
    assert "Chưa đủ bằng chứng" in null[0].text
    assert "kết quả hợp lệ" in null[0].text
    assert null[2].badge == BADGE_THIEU_DU_LIEU


# ---------------------------------------------------------------------------
# API trên BỘ PHIÊN DEMO VÀNG — ba trạng thái thật, đúng đường serialize
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vang():
    """Seed demo vàng MỘT lần cho cả module (6 phiên × analyze_outer là phần
    đắt nhất của bộ test này — trả giá một lần)."""
    store = InMemoryStore()
    ket_qua = seed_demo_vang(store)
    app = create_app(store=store)
    with TestClient(app) as client:
        yield client, ket_qua["nhom"]


def _bao_cao(client, sid: str) -> dict:
    r = client.get(f"/sessions/{sid}/bao-cao")
    assert r.status_code == 200, r.text
    return r.json()


def test_bao_cao_demo_vang_duong_narrate_khop_trang_thai(vang):
    client, nhom = vang
    bc = _bao_cao(client, nhom["duong"][0])
    cau = bc["tom_tat_3_cau"]
    assert len(cau) == 3
    assert "tạo thêm +" in cau[0]["text"]
    assert "không chứa 0" in cau[0]["text"]
    assert cau[0]["badge"] == "thi_nghiem"
    # con số trong câu phải là ĐÚNG con số của khối nhân quả cùng payload
    kq = bc["ket_qua_thi_nghiem"]
    assert f"{kq['estimate']:+.3f}" in cau[0]["text"]
    assert f"{kq['n_blocks']} khối" in cau[1]["text"]
    assert cau[0]["refs"], "mỗi câu phải khai nguồn số (refs)"


def test_bao_cao_demo_vang_null_narrate_la_ket_qua_hop_le(vang):
    client, nhom = vang
    bc = _bao_cao(client, nhom["null"][0])
    cau = bc["tom_tat_3_cau"]
    assert len(cau) == 3
    assert "Chưa đủ bằng chứng" in cau[0]["text"]
    assert "kết quả hợp lệ" in cau[0]["text"]
    assert "còn chứa 0" in cau[0]["text"]


def test_bao_cao_demo_vang_thieu_narrate_tu_choi_ket_luan(vang):
    client, nhom = vang
    bc = _bao_cao(client, nhom["thieu"][0])
    cau = bc["tom_tat_3_cau"]
    assert len(cau) == 3
    assert "chưa đủ điều kiện" in cau[0]["text"].lower()
    assert bc["ket_qua_thi_nghiem"]["message"] in cau[0]["text"], (
        "lý do từ chối phải chép nguyên văn từ ket_qua_thi_nghiem.message"
    )
    assert all(c["badge"] != "thi_nghiem" for c in cau)


def test_summary_demo_vang_mang_tom_tat_va_khong_tron_sang_that(vang):
    client, _ = vang
    demo = client.get("/experiment/summary?env=demo").json()
    assert len(demo["tom_tat_3_cau"]) == 3
    # bản gộp demo đủ khối/phiên nên phải ước lượng được và narrate nhân quả
    assert demo["estimable"] is True
    assert demo["tom_tat_3_cau"][0]["badge"] == "thi_nghiem"

    real = client.get("/experiment/summary").json()
    assert len(real["tom_tat_3_cau"]) == 3
    assert "chưa đủ điều kiện" in real["tom_tat_3_cau"][0]["text"].lower()
    assert all(c["badge"] != "thi_nghiem" for c in real["tom_tat_3_cau"]), (
        "kho chỉ có demo ⇒ bản THẬT phải từ chối kết luận, không mượn số demo"
    )


def test_summary_khoa_7_narrate_khong_lo_so(monkeypatch):
    """Trong cửa sổ khóa §7, tóm tắt 3 câu của bản THẬT chép nguyên văn lý do
    khóa và chỉ có số vận hành — kho riêng có phiên THẬT đủ khối để chắc chắn
    đường khóa (không phải đường thiếu-dữ-liệu) được đi qua."""
    from livelift.config import get_settings
    from tests.conftest import seed_phien_that_mo_phong

    store = InMemoryStore()
    seed_phien_that_mo_phong(store)
    app = create_app(store=store)
    monkeypatch.setenv("RESULTS_FREEZE_UNTIL", "2999-01-01")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            real = client.get("/experiment/summary").json()
    finally:
        monkeypatch.delenv("RESULTS_FREEZE_UNTIL", raising=False)
        get_settings.cache_clear()
    assert real["estimable"] is False
    cau = real["tom_tat_3_cau"]
    assert len(cau) == 3
    assert "khóa đến 2999-01-01" in cau[0]["text"], "lý do khóa phải nguyên văn"
    ca_ba = " ".join(c["text"] for c in cau)
    assert "KTC" not in ca_ba
    assert "p =" not in ca_ba
    assert "p <" not in ca_ba
    assert all(c["badge"] != "thi_nghiem" for c in cau)
