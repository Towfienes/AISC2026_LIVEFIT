"""Gate cho ``scripts/dong_bo_so_test.py`` — công cụ "một nguồn số test".

Kiểm toán 25/09/2026 (so-chuan.md §3.1, §3.3; aisc-r2.md T1) tìm ra ba lỗ:

1. Nhãn "17 cổng Monte-Carlo" SAI: 17 test ``slow and not browser`` gồm 13 test
   mô phỏng/thống kê, 1 test đánh giá NLP trên chat thật và 3 cổng dựng bản
   build CSS. Giám khảo mở test ra là thấy lệch.
2. Script chỉ quét README và trang chủ rồi báo "Mọi nơi đã ghi đúng" — trong khi
   ``docs/competition/FACT-SHEET.md`` (tệp mà hồ sơ gọi là nguồn số duy nhất)
   vẫn ghi 1.555 + 17 + 10 = 1.582 của ngày 17/09.
3. Một nhánh đổi chữ badge/PROOF làm regex im lặng không khớp nữa, và script
   vẫn báo "đúng" — an toàn giả. Mẫu không tìm thấy phải là LỖI.

Gate ở đây nạp chính script (không chạy pytest con) và thử các hàm thuần của nó
trên TỆP THẬT của kho: mẫu nào không khớp tệp thật là đỏ ngay.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
SCRIPT = GOC / "scripts" / "dong_bo_so_test.py"
README = GOC / "README.md"
TRANG_CHU = GOC / "web" / "src" / "app" / "page.tsx"
FACT_SHEET = GOC / "docs" / "competition" / "FACT-SHEET.md"
HO_SO_DIR = GOC / "docs" / "competition" / "sang-tao-tre-2026"
#: Ba tệp nộp chép lại dòng "Bộ kiểm thử" của FACT-SHEET (phần việc 3, tối 25/09/2026): hồ sơ
#: (Tóm tắt, Bảng 5), bản kê khai mục VIII, lời dẫn và bảng "Số được phép nói" của kịch bản video.
#: Trước đó script không quét chúng — đổi số test thì ba tệp nộp giữ số cũ mà vẫn báo "đúng".
#: 27/09/2026: ba tệp viết lại theo văn phong tự nhiên, mẫu của script đổi theo.
HO_SO = (
    HO_SO_DIR / "noi-dung.md",
    HO_SO_DIR / "05-BAN-KE-KHAI.md",
    HO_SO_DIR / "07-KICH-BAN-2-VIDEO.md",
)
#: Nhóm theo nguồn mà tệp chép số: ba tệp nộp đi cùng FACT-SHEET, tệp chúng trích.
NHOM = {
    "README.md": (README,),
    "page.tsx": (TRANG_CHU,),
    "FACT-SHEET+ho-so": (FACT_SHEET, *HO_SO),
}


@pytest.fixture(scope="module")
def db():
    spec = importlib.util.spec_from_file_location("dong_bo_so_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # dataclass tra module qua sys.modules lúc tạo lớp — phải đăng ký trước.
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.modules.pop(spec.name, None)


def _doc(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_phan_loai_17_cong_cham_theo_tep(db):
    """Con số tách ra phải SINH từ danh sách test thu thập được, không chép tay."""
    theo_tep = {
        "tests/test_sim_validation.py": 7,
        "tests/test_sim_report.py": 2,
        "tests/test_estimators.py": 1,
        "tests/test_power.py": 1,
        "tests/test_sim_heterogeneity.py": 1,
        "tests/test_click_validity.py": 1,
        "tests/test_nlp_eval_harness.py": 1,
        "tests/test_web_css_gate.py": 3,
    }
    assert db.phan_loai_cham(theo_tep) == (13, 1, 3)


def test_khong_noi_dau_con_goi_17_cong_cham_la_monte_carlo(db):
    so = db.SoTest(nhanh=1803, thong_ke=13, nlp=1, css=3, trinh_duyet=10)
    dong = db.mo_ta(so)
    assert "Monte-Carlo" not in dong.split("(")[0], dong
    assert "17 cổng chậm (13 mô phỏng/thống kê · 1 đánh giá NLP · 3 cổng build CSS)" in dong
    for tep in (README, TRANG_CHU, FACT_SHEET):
        noi_dung = _doc(tep)
        assert "cổng Monte-Carlo" not in noi_dung, (
            f"{tep.name} còn gọi nhóm chậm là cổng Monte-Carlo"
        )
        assert "Monte--Carlo-" not in noi_dung, f"{tep.name}: badge còn chữ Monte-Carlo"


@pytest.mark.parametrize("nhom", list(NHOM))
def test_moi_mau_bat_buoc_khop_tep_that(db, nhom):
    """Mẫu bắt buộc không khớp = script im lặng ngừng đồng bộ (sự cố T1)."""
    so = db.SoTest(nhanh=4242, thong_ke=31, nlp=2, css=5, trinh_duyet=11)
    for tep in NHOM[nhom]:
        luat = db.LUAT[tep.relative_to(GOC).as_posix()]
        _, thieu = db.ap_dung(_doc(tep), luat, so, "01/01/2099")
        assert not thieu, f"{tep.name}: mẫu bắt buộc không tìm thấy trong tệp thật: {thieu}"


@pytest.mark.parametrize("nhom", list(NHOM))
def test_doi_so_thi_tep_that_doi_theo(db, nhom):
    so = db.SoTest(nhanh=4242, thong_ke=31, nlp=2, css=5, trinh_duyet=11)
    for tep in NHOM[nhom]:
        luat = db.LUAT[tep.relative_to(GOC).as_posix()]
        cu = _doc(tep)
        moi, _ = db.ap_dung(cu, luat, so, "01/01/2099")
        assert moi != cu, tep.name
        assert "4242" in moi or "4.242" in moi, tep.name
        if tep in (README, FACT_SHEET):
            assert "38 cổng chậm (31 mô phỏng/thống kê · 2 đánh giá NLP · 5 cổng build CSS)" in moi
        if tep is FACT_SHEET:
            assert "01/01/2099" in moi, "FACT-SHEET đổi số thì phải đổi luôn ngày đếm"
            assert "4.242 test nhanh" in moi, "FACT-SHEET dùng số vi-VN"
            assert "4.291" in moi, "FACT-SHEET dùng số vi-VN"
        if tep in HO_SO:
            assert "4.291" in moi, f"{tep.name}: tổng số test phải đổi theo, số vi-VN"
            # Số test THU THẬP đổi thì câu kết quả chạy cũ ("2.091 đạt, 2 bỏ qua") không còn
            # cộng ra tổng: script không được tự sửa số đạt, phải báo để người chạy lại.
            assert db.lech_ket_qua_chay(moi, so), f"{tep.name}: kết quả chạy cũ không bị báo"
            assert not db.lech_ket_qua_chay("chạy: 4.289 đạt, 2 bỏ qua", so)
        if tep is README:
            # README viết lại 27/09/2026: bảng "Bộ số chuẩn" nêu tổng số test (được đồng bộ)
            # và kết quả một lần chạy (không tự sửa được, nên phải bị báo khi tổng đổi).
            assert "4.291 test thu thập được, gồm 4.242 nhanh, 38 chậm" in moi
            assert "README.md" in db.TEP_KET_QUA_CHAY
            assert db.lech_ket_qua_chay(moi, so), "README: kết quả chạy cũ không bị báo"
        # Áp lại cùng bộ số lần hai: không đổi gì nữa (idempotent).
        lai, _ = db.ap_dung(moi, luat, so, "02/02/2099")
        assert lai == moi, f"{tep.name}: ngày đếm chỉ đổi khi con số đổi"


def test_badge_giu_mau_va_khong_bi_khoa_vao_brightgreen(db):
    luat = db.LUAT["README.md"]
    so = db.SoTest(nhanh=7, thong_ke=1, nlp=1, css=1, trinh_duyet=1)
    for mau in ("brightgreen", "blue"):
        t = f"[![Tests](https://img.shields.io/badge/tests-1%20nhanh-{mau})](tests/)"
        moi, _ = db.ap_dung(t, luat, so, "01/01/2099")
        assert re.search(
            rf"badge/tests-7%20nhanh%20%2B%203%20c%E1%BB%95ng%20ch%E1%BA%ADm-{mau}\)", moi
        ), moi


def test_loi_thu_thap_la_loi_khong_dem_thieu(db, monkeypatch):
    """Phản biện 25/09/2026: một tệp test lỗi import thì ``--collect-only`` vẫn in
    số của các tệp còn lại và thoát mã 2. Cộng số đó là ghi con số THIẾU vào
    README/trang chủ/FACT-SHEET mà vẫn báo "đúng" — phải dừng, không đếm."""

    class _KetQua:
        returncode = 2
        stdout = "tests/test_a.py: 3\n\n==== 1 error in 0.5s ====\n"
        stderr = "ERROR collecting tests/test_b.py"

    monkeypatch.setattr(db.subprocess, "run", lambda *a, **k: _KetQua())
    with pytest.raises(SystemExit):
        db.dem_theo_tep("not slow")


def test_fact_sheet_so_y_dinh_khop_results_json():
    """Phản biện 25/09/2026: FACT-SHEET/README ghi v2 "0,565 [0,491; 0,649]" và trỏ
    về ``results.json``, trong khi chính tệp đó (đo lại sau khi lọc lại PII) ghi
    0,542 [0,478; 0,625]. Số chép tay cũ đi mà không gate nào đỏ. Dòng C2 (cấu
    hình v2) và B2 (artifact đang chạy) của results.json phải có nguyên văn trong
    FACT-SHEET — nguồn số duy nhất của hồ sơ."""
    import json

    kq = json.loads((GOC / "docs/benchmarks/intent-eval/results.json").read_text(encoding="utf-8"))
    dong = {r["name"][:2]: r for bang in kq["tables"] for r in bang["rows"]}
    fs = _doc(FACT_SHEET)

    def vi3(x: float) -> str:
        return f"{x:.3f}".replace(".", ",")

    for ma in ("B2", "C2"):
        r = dong[ma]
        lo, hi = r["macro_f1_ci95"]
        cum = f"macro-F1 {vi3(r['macro_f1'])} · KTC95 [{vi3(lo)}; {vi3(hi)}]"
        assert cum in fs, f"FACT-SHEET thiếu số {ma} của results.json: {cum!r}"
