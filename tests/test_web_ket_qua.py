"""Gói KẾT-QUẢ v2 — gate cho màn /ket-qua verdict-first + tóm tắt 3 câu.

Điều kiện bắt buộc từ phản biện khoa học (ưu tiên #6): CẢ BA trạng thái kết
quả — DƯƠNG/ÂM, NULL, CHƯA ĐỦ ĐIỀU KIỆN — được thiết kế RIÊNG với mức công
phu NGANG NHAU; và từ phản biện #1: con dấu "TÁC ĐỘNG THẬT" chỉ tồn tại khi
KTC 95% loại 0, KHÔNG count-up cho ước lượng nhân quả. Các gate ở đây đọc
thẳng mã render để giữ những lời hứa đó không bị "tiện tay" gỡ mất:

1. ba (bốn, tính quan sát) khối verdict tồn tại và đều là Card padding="lg";
2. con dấu TÁC ĐỘNG THẬT bị nhốt trong đúng nhánh KTC-loại-0;
3. không cơ chế count-up/tween nào trên trang kết quả;
4. trạng thái NULL mang huy hiệu "KẾT QUẢ TRUNG THỰC" + bảng "cần thêm bao
   nhiêu phiên"; trạng thái CHƯA ĐỦ in nguyên văn lý do máy chủ + checklist
   ngưỡng thiết kế; khóa §7 có mặt chữ;
5. tóm tắt 3 câu render nguyên văn từ server (không .toFixed nào trong
   component — client không được chế lại số) trên CẢ /ket-qua và /bao-cao;
6. chip DEMO đi theo cờ is_demo ở mọi chỗ số liệu demo xuất hiện.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
SRC = WEB / "src"
KET_QUA = SRC / "app" / "ket-qua" / "page.tsx"
BAO_CAO = SRC / "app" / "bao-cao" / "[id]" / "page.tsx"
TOM_TAT = SRC / "components" / "TomTat3Cau.tsx"
TYPES = SRC / "lib" / "types.ts"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Ba trạng thái — ba thiết kế riêng, cùng mức công phu
# ---------------------------------------------------------------------------


def test_ca_ba_trang_thai_verdict_deu_ton_tai():
    src = _read(KET_QUA)
    for comp in ("VerdictCoTacDong", "VerdictNull", "VerdictChuaDu", "VerdictQuanSat"):
        assert f"function {comp}" in src, f"thiếu khối verdict {comp}"
        assert re.search(rf"<{comp}\b", src), f"{comp} được định nghĩa nhưng không render"


def test_ba_trang_thai_cung_muc_cong_phu_card_lg():
    """Mỗi trạng thái là một Card padding='lg' có huy hiệu nhận diện — NULL và
    CHƯA ĐỦ không được là một dòng chữ xám lép vế cạnh trạng thái dương."""
    src = _read(KET_QUA)
    for comp, badge in [
        ("VerdictCoTacDong", "TÁC ĐỘNG THẬT"),
        ("VerdictNull", "KẾT QUẢ TRUNG THỰC"),
        ("VerdictChuaDu", "CHƯA ĐỦ ĐIỀU KIỆN"),
    ]:
        body = src.split(f"function {comp}")[1].split("\nfunction ")[0]
        assert 'padding="lg"' in body, f"{comp} phải là Card padding='lg'"
        assert badge in body, f"{comp} thiếu huy hiệu nhận diện {badge!r}"
        assert "<Badge" in body


def test_verdict_state_theo_dung_luat_ktc_loai_0():
    """Cùng luật phân loại với analysis/narrate.trang_thai_ket_luan."""
    src = _read(KET_QUA)
    assert "ciLow != null && ciLow > 0" in src
    assert "ciHigh != null && ciHigh < 0" in src


# ---------------------------------------------------------------------------
# 2. Con dấu TÁC ĐỘNG THẬT bị nhốt trong nhánh KTC-loại-0
# ---------------------------------------------------------------------------


def test_con_dau_tac_dong_that_chi_o_nhanh_co_tac_dong():
    src = _read(KET_QUA)
    # chuỗi RENDER của con dấu (không tính chú thích mã) phải xuất hiện đúng
    # MỘT chỗ — trong VerdictCoTacDong
    con_dau = "TÁC ĐỘNG THẬT · KTC 95% không chứa 0"
    assert src.count(con_dau) == 1, "con dấu render phải xuất hiện đúng MỘT chỗ"
    body = src.split("function VerdictCoTacDong")[1].split("\nfunction ")[0]
    assert con_dau in body, "con dấu phải nằm trong VerdictCoTacDong"
    # ... và VerdictCoTacDong chỉ được render khi state là duong/am
    m = re.search(r'verdict\.state === "duong" \|\| verdict\.state === "am"', src)
    assert m, "VerdictCoTacDong phải được gate bằng state duong/am"
    # con dấu luôn kèm KTC ngay trong chính nó (phản biện #1)
    assert "TÁC ĐỘNG THẬT · KTC 95% không chứa 0" in body


# ---------------------------------------------------------------------------
# 3. Không count-up cho ước lượng nhân quả
# ---------------------------------------------------------------------------


def test_khong_count_up_tren_man_ket_qua():
    src = _read(KET_QUA)
    for cam in ("countUp", "CountUp", "requestAnimationFrame", "dur-countup", "medium3"):
        assert cam not in src, f"cấm count-up/tween trên ước lượng nhân quả: tìm thấy {cam!r}"


# ---------------------------------------------------------------------------
# 4. NULL và CHƯA ĐỦ được dàn dựng thật, khóa §7 có mặt chữ
# ---------------------------------------------------------------------------


def test_null_state_noi_dung_bat_buoc():
    src = _read(KET_QUA)
    body = src.split("function VerdictNull")[1].split("\nfunction ")[0]
    assert "kết quả hợp lệ" in body, "NULL phải được tuyên bố là kết quả hợp lệ"
    assert "Cần thêm bao nhiêu phiên" in body, "NULL phải trả lời bằng bảng lực, không an ủi"
    assert "còn chứa 0" in body
    assert "CIBar" in body, "NULL vẽ thanh KTC như trạng thái dương — không lép"


def test_chua_du_in_ly_do_may_chu_va_nguong_thiet_ke():
    src = _read(KET_QUA)
    body = src.split("function VerdictChuaDu")[1].split("\nfunction ")[0]
    assert "v.lyDo" in body, "lý do từ chối phải in nguyên văn từ máy chủ"
    assert "từ chối kết luận" in body
    for nguong in ("nguong: 2", "nguong: 8", "nguong: 4"):
        assert nguong in body, f"checklist thiếu ngưỡng thiết kế {nguong!r}"
    assert "/chay-phien" in body, "CHƯA ĐỦ phải dẫn người dùng đi sửa thiết kế"
    assert "KHÓA THEO TIỀN ĐĂNG KÝ" in body, "khóa §7 là một biến thể có mặt chữ riêng"


# ---------------------------------------------------------------------------
# 5. Tóm tắt 3 câu — render nguyên văn, không chế lại số ở client
# ---------------------------------------------------------------------------


def test_tom_tat_3_cau_render_o_ca_hai_man():
    assert "tom_tat_3_cau" in _read(KET_QUA)
    assert "tom_tat_3_cau" in _read(BAO_CAO)
    for page in (KET_QUA, BAO_CAO):
        assert "TomTat3Cau" in _read(page), f"{page.name} phải dùng component chung"


def _render(src: str) -> str:
    """Nguồn đã bỏ chú thích (chú thích giải thích chính câu bị cấm)."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<![:\w])//.*$", " ", src)


def test_chua_du_khong_lap_thong_diep_ba_lan():
    """Đánh giá UI 17/09/2026: khi CHƯA ĐỦ ĐIỀU KIỆN, trang in cùng một thông
    điệp ba lần liền — tiêu đề khối verdict → lý do máy chủ → câu 1 của tóm tắt
    ("Thiết kế chưa đủ điều kiện…: <cùng lý do>"), rồi câu 2/3 lặp checklist và
    nút. Khối verdict đã chứa đủ ba ý, nên tóm tắt 3 câu không hiện ở trạng thái
    này; ở DƯƠNG/ÂM/NULL nó vẫn hiện vì nói thêm điều khối verdict không nói."""
    src = _render(_read(KET_QUA))
    m = re.search(r"\{([^{}]*?)\?\s*\(\s*<TomTat3Cau\b", src)
    assert m, "không đọc được điều kiện render TomTat3Cau"
    assert 'verdict?.state !== "chuadu"' in m.group(1), (
        "tóm tắt 3 câu phải bị bỏ ở trạng thái chuadu — nếu không câu 1 lặp lại lý do "
        "khối verdict vừa in nguyên văn"
    )
    assert src.count("<TomTat3Cau") == 1


def test_chua_du_an_tom_tat_nhung_khong_mat_so_luot_nhap_hop_le():
    """Phản biện gói E: ẩn tóm tắt 3 câu ở trạng thái chuadu từng làm mất số
    lượt nhấp hợp lệ — CHỈ SỐ CHÍNH — vì câu 2 của máy chủ là chỗ duy nhất in
    nó (và, khi xem ?phien=, cả tổng bình luận và thời lượng). Bỏ lặp chỉ được
    bỏ chữ trùng, không được bỏ số: khối VerdictChuaDu phải tự in các số đó,
    thiếu thì nói THIẾU chứ không in 0."""
    src = _render(_read(KET_QUA))
    body = src.split("function VerdictChuaDu")[1].split("\nfunction ")[0]
    assert "fmtNumber(v.luotNhapHopLe)" in body, "khối chưa đủ phải in số lượt nhấp hợp lệ"
    assert "Lượt nhấp hợp lệ qua link đo" in body
    assert "v.luotNhapHopLe != null" in body, "thiếu nguồn lượt nhấp phải rẽ nhánh THIẾU"
    assert "không phải bằng 0" in body, "lượt nhấp THIẾU không được đọc thành 0"
    assert "THIẾU" in body
    # Dòng lượt nhấp không bị giấu sau nhánh khóa §7: số vận hành luôn công khai.
    i = body.index("fmtNumber(v.luotNhapHopLe)")
    assert "v.khoa ?" not in body[body.rindex("<li", 0, i) : i]
    # Bản một phiên: tổng bình luận và thời lượng cũng từng chỉ nằm trong câu 2.
    for so in ("fmtNumber(v.motPhien.tongBinhLuan)", "v.motPhien.thoiLuongS"):
        assert so in body, f"khối chưa đủ (?phien=) phải in {so}"

    # Nguồn số: bản gộp đọc valid_clicks, bản một phiên đọc tong_quan.
    gop = src.split("function verdictFromSummary")[1].split("\nfunction ")[0]
    assert ".valid_clicks" in gop
    mot = src.split("function verdictFromKetQua")[1].split("\nfunction ")[0]
    for f in ("luot_nhap_hop_le", "thieu?.luot_nhap", "tong_binh_luan", "thoi_luong_s"):
        assert f in mot, f"bản một phiên phải đọc tong_quan.{f}"
    assert "baoCao.tong_quan" in src, "verdictFromKetQua phải nhận tong_quan của báo cáo"


def test_hop_dong_may_chu_tra_so_luot_nhap_o_nhanh_chua_du(monkeypatch):
    """Hai đầu không lệch: ở nhánh CHƯA ĐỦ, máy chủ vẫn trả valid_clicks (bản
    gộp) và tong_quan.luot_nhap_hop_le + lý do thiếu (báo cáo phiên) — đúng
    các trường VerdictChuaDu đọc."""
    from fastapi.testclient import TestClient

    from livelift.api.main import create_app
    from livelift.api.store import InMemoryStore
    from livelift.config import get_settings

    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(create_app(store=InMemoryStore())) as c:
            gop = c.get("/experiment/summary").json()
            assert gop["estimable"] is False
            assert "valid_clicks" in gop
            assert gop["valid_clicks"] is not None
            cau2 = gop["tom_tat_3_cau"][1]["text"]
            assert f"{gop['valid_clicks']} lượt nhấp hợp lệ" in cau2, (
                "câu 2 bị ẩn mang số lượt nhấp — khối verdict phải in lại đúng số này"
            )

            sid = c.post(
                "/sessions", json={"platform": "facebook", "planned_duration_min": 30}
            ).json()["session_id"]
            tq = c.get(f"/sessions/{sid}/bao-cao").json()["tong_quan"]
            for f in ("luot_nhap_hop_le", "tong_binh_luan", "thoi_luong_s", "thieu"):
                assert f in tq, f"báo cáo phiên thiếu tong_quan.{f}"
            thieu_kem_ly_do = (
                "khi chưa có link đo, máy chủ trả null + lý do — web in THIẾU kèm lý do"
            )
            assert tq["luot_nhap_hop_le"] is None, thieu_kem_ly_do
            assert tq["thieu"].get("luot_nhap"), thieu_kem_ly_do
    finally:
        get_settings.cache_clear()


def test_chua_du_khong_them_cau_ket_noi_lai_lan_thu_tu():
    body = _render(_read(KET_QUA)).split("function VerdictChuaDu")[1].split("\nfunction ")[0]
    assert "Không hạ ngưỡng, không nội suy" not in body, (
        "câu kết cũ nói lại điều checklist + nút đã nói"
    )
    # Nhánh khóa §7 vẫn giải thích VÌ SAO khóa — đó là thông tin mới, không phải lặp.
    assert "nhìn trộm hiệu ứng" in body


def test_component_tom_tat_khong_che_so_va_khai_nguon():
    src = _read(TOM_TAT)
    assert ".toFixed" not in src, "client không được định dạng lại số của narrate"
    assert "Nguồn số" in src, "mỗi câu phải khai nguồn (refs) qua tooltip"
    for badge in ("THÍ NGHIỆM", "QUAN SÁT", "THIẾU DỮ LIỆU"):
        assert badge in src, f"thiếu huy hiệu bằng chứng {badge}"
    assert "{c.text}" in src, "câu phải render nguyên văn từ server"


def test_types_khai_bao_cau_tom_tat():
    src = _read(TYPES)
    assert "CauTomTat" in src
    assert '"thi_nghiem" | "quan_sat" | "thieu_du_lieu"' in src


# ---------------------------------------------------------------------------
# 6. Chip DEMO theo cờ is_demo
# ---------------------------------------------------------------------------


def test_chip_demo_theo_co_is_demo():
    kq = _read(KET_QUA)
    # verdict + tóm tắt + danh sách phiên đều đeo chip theo cờ
    assert "isDemo" in kq
    assert kq.count("DEMO — dữ liệu mẫu") >= 4, "mọi khối số liệu demo phải đeo chip DEMO"
    assert "s.is_demo ? <Badge" in kq, "từng dòng phiên demo trong danh sách phải có chip"
    bc = _read(BAO_CAO)
    assert "data?.is_demo" in bc or "data.is_demo" in bc, "/bao-cao phải vẽ chip DEMO theo cờ"


def test_danh_sach_phien_tach_nhom_that_demo():
    src = _read(KET_QUA)
    assert "realSessions" in src
    assert "demoSessions" in src
    assert "filter((s) => !s.is_demo)" in src
    assert "filter((s) => s.is_demo)" in src


# ---------------------------------------------------------------------------
# 7. Chi tiết thống kê giữ nguyên (MDE/CV/tuân thủ) + p-floor trung thực
# ---------------------------------------------------------------------------


def test_chi_tiet_thong_ke_van_con_va_p_floor_trung_thuc():
    src = _read(KET_QUA)
    assert "Chi tiết thống kê cho giám khảo" in src
    for can in ("power_table", "measured_cv", "measured_compliance", "MDE"):
        assert can in src, f"chi tiết thống kê thiếu {can}"
    # sàn p của kiểm định hoán vị — không in số chính-xác-giả
    assert "p <" in src
    assert "1 / (draws + 1)" in src


def test_xem_mot_phien_qua_query_phien():
    """docs/demo-vang.md: 'trang kết quả của web với phiên tương ứng' — ba
    trạng thái demo vàng phải mở được qua /ket-qua?phien=<id>."""
    src = _read(KET_QUA)
    assert 'get("phien")' in src
    assert "getBaoCao(phien)" in src
    assert "verdictFromKetQua" in src
