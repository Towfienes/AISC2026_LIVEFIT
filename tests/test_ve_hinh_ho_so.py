"""Cổng nhanh cho ``scripts/ve_hinh_ho_so.py``: hình hồ sơ không được trôi khỏi nguồn số.

Vì sao tệp này tồn tại. Hồ sơ Sáng tạo trẻ AI 2026 hứa rằng mọi con số trên hình đều
sinh lại được. Script vẽ tự kiểm một số điều lúc chạy, nhưng không ai chạy nó trong
CI, vì nó cần matplotlib, gói không thuộc phụ thuộc lõi. Tệp này giữ các bất biến
rẻ tiền trong bộ test nhanh:

1. ``so()``/``phan_tram()`` viết số kiểu Việt Nam: phẩy thập phân, chấm phân nghìn, dấu
   trừ thật, không in "−0,00".
2. Tham số cổng hiệu ứng lưu mà hình 5 bóc bằng ``ast`` TRÙNG với tham số cổng thật sự
   gọi. Phép kiểm đi đường khác hẳn ``ast``: CHẠY hàm cổng với ``run_validation`` giả
   rồi ghi lại lời gọi.
3. Số đếm trong ``hinh/du-lieu/hieu-chuan.json`` khớp ``docs/benchmarks/so-hieu-chuan.json``;
   cả hai tệp Monte-Carlo (hình 3, 5) được tính trên cây sạch, đúng một commit.
4. Số trên hình 6 lấy đúng từ ``docs/benchmarks/intent-eval/chi-tiet-hinh.json``, và
   bản PNG/NGUON.md đang nằm trong kho được vẽ từ đúng bản JSON hiện tại.

Không chạy Monte-Carlo, không mạng. Phần dựng hình cần matplotlib: thiếu thì SKIP có
lý do; phần còn lại chạy được trên ``.venv`` trần.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import re
import struct
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
SCRIPT = GOC / "scripts" / "ve_hinh_ho_so.py"
HINH = GOC / "docs" / "competition" / "sang-tao-tre-2026" / "hinh"
DU_LIEU = HINH / "du-lieu"
SO_HIEU_CHUAN = GOC / "docs" / "benchmarks" / "so-hieu-chuan.json"
CHI_TIET = GOC / "docs" / "benchmarks" / "intent-eval" / "chi-tiet-hinh.json"

LY_DO_THIEU_MPL = (
    "matplotlib chưa được cài (chỉ dùng để vẽ hình hồ sơ, không thuộc phụ thuộc lõi) — "
    "cài nó để chạy phần dựng hình 6; phần kiểm số liệu vẫn chạy"
)


def _doc(duong: Path) -> dict:
    return json.loads(duong.read_text(encoding="utf-8"))


def _tinh_tren_cay_sach(du_lieu: dict) -> None:
    """Chân hình 3/5 in ``ban_git`` của lần tính: phải là MỘT commit, không kèm thay đổi chưa
    commit (25/09/2026: hai tệp mang "390027b+ban-lam-viec-co-thay-doi" — không ai tái lập
    được từ một commit). Tính lại bằng ``--tinh-lai`` trên cây sạch rồi commit."""
    ban = du_lieu["ban_git"]
    assert re.fullmatch(r"[0-9a-f]{7,40}", ban), f"ban_git = {ban!r}: tính trên cây bẩn/không rõ"


@pytest.fixture(scope="module")
def vh():
    """Nạp script như một module (thư mục scripts/ không phải package)."""
    spec = importlib.util.spec_from_file_location("ve_hinh_ho_so", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def chi_tiet() -> dict:
    return _doc(CHI_TIET)


@pytest.fixture(scope="module")
def plt(vh):
    pytest.importorskip("matplotlib", reason=LY_DO_THIEU_MPL)
    return vh.nap_matplotlib()  # backend Agg + đúng rcParams (Arial, cỡ chữ) của bản vẽ thật


# =============================================================== 1. định dạng số
@pytest.mark.parametrize(
    ("x", "nd", "mong_doi"),
    [
        (1234.5, 1, "1.234,5"),
        (1234567.891, 2, "1.234.567,89"),
        (19126, 0, "19.126"),
        (-0.84, 2, "−0,84"),
        (-0.001, 2, "0,00"),  # làm tròn về 0 thì không in "−0,00"
        (0, 0, "0"),
        (0.5423, 3, "0,542"),
        # giá trị nhị phân của 0,6245 nhỉnh hơn 0,6245 nên lên 0,625 — trùng Bảng 8 hồ sơ
        (0.6245, 3, "0,625"),
        (0.2115, 3, "0,211"),
    ],
)
def test_so_viet_kieu_viet_nam(vh, x, nd, mong_doi):
    assert vh.so(x, nd) == mong_doi


@pytest.mark.parametrize(
    ("x", "nd", "mong_doi"),
    [
        (0.035, 2, "3,50%"),
        (0.965, 2, "96,50%"),
        (-0.215, 1, "−21,5%"),
        (1, 0, "100%"),
        (-0.00004, 2, "0,00%"),
    ],
)
def test_phan_tram_viet_kieu_viet_nam(vh, x, nd, mong_doi):
    assert vh.phan_tram(x, nd) == mong_doi


def test_dau_tru_la_ky_tu_tru_that(vh):
    assert vh.so(-5, 1) == "−5,0"
    assert "-" not in vh.so(-1234.5, 1)


def test_huong_dan_cai_goi_ve_theo_pyproject(vh, monkeypatch, tmp_path):
    """NGUON.md và thông báo thiếu gói không được nói "không có trong pyproject" khi đã có."""
    monkeypatch.setattr(vh, "GOC", tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n[project.optional-dependencies]\nhinh = ["matplotlib>=3.9"]\n',
        encoding="utf-8",
    )
    assert ".[hinh]" in vh.cach_cai_goi_ve()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    assert "không nằm trong pyproject" in vh.cach_cai_goi_ve()


# ======================================================= 2. cổng hiệu ứng lưu
def _chay_cong_luu(monkeypatch, do_phu: float) -> list[dict]:
    """Chạy ĐÚNG hàm cổng, thay ``run_validation`` bằng bản giả ghi lại lời gọi."""
    spec = importlib.util.spec_from_file_location(
        "cong_sim_validation", GOC / "tests" / "test_sim_validation.py"
    )
    cong = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(cong)
    goi: list[dict] = []

    class KetQuaGia:
        mean_estimate = 1.0
        relative_bias = 0.0
        ci_coverage = do_phu

        def summary(self) -> str:
            return "kết quả giả"

    def run_validation_gia(*args, **kw):
        assert not args, "cổng gọi run_validation bằng đối số vị trí — ast không bóc được"
        goi.append(kw)
        return KetQuaGia()

    monkeypatch.setattr(cong, "run_validation", run_validation_gia)
    cong.test_estimator_under_carryover_interference()
    return goi


def test_tham_so_cong_hieu_ung_luu_trung_loi_goi_that(vh, monkeypatch):
    from livelift.sim.simulator import SimParams

    goi = _chay_cong_luu(monkeypatch, do_phu=1.0)
    assert len(goi) == 1
    kw = dict(goi[0])
    sp = kw.pop("sim_params")
    boc = vh.tham_so_cong_hieu_ung_luu()
    # mọi đối số ngoài sim_params: trùng từng giá trị
    assert {k: boc.get(k) for k in kw} == kw
    # mọi trường SimParams mà cổng đặt khác mặc định đều được bóc, đúng giá trị
    mac_dinh = SimParams()
    doi = {
        f.name
        for f in dataclasses.fields(SimParams)
        if getattr(sp, f.name) != getattr(mac_dinh, f.name)
    }
    assert doi == set(boc) - set(kw)
    for k in doi:
        assert getattr(sp, k) == boc[k]


def test_nguong_phu_trung_assert_cua_cong(vh, monkeypatch):
    nguong = vh.nguong_phu_cong_hieu_ung_luu()
    _chay_cong_luu(monkeypatch, do_phu=nguong)  # đúng bằng ngưỡng: cổng đạt
    with pytest.raises(AssertionError):
        _chay_cong_luu(monkeypatch, do_phu=nguong - 1e-9)


def test_tham_so_cong_doc_tu_ma_nguon_khong_chep_tay(vh, monkeypatch, tmp_path):
    """Đổi cổng thì hàm bóc phải đổi theo; mất lời gọi thì DỪNG, không đoán."""
    nguon = (GOC / "tests" / "test_sim_validation.py").read_text(encoding="utf-8")
    (tmp_path / "tests").mkdir()
    doi = nguon.replace("carryover_halflife_s=120.0", "carryover_halflife_s=150.0")
    assert doi != nguon
    (tmp_path / "tests" / "test_sim_validation.py").write_text(doi, encoding="utf-8")
    monkeypatch.setattr(vh, "GOC", tmp_path)
    assert vh.tham_so_cong_hieu_ung_luu()["carryover_halflife_s"] == 150.0
    (tmp_path / "tests" / "test_sim_validation.py").write_text(
        nguon.replace("run_validation(", "khong_phai_run_validation("), encoding="utf-8"
    )
    with pytest.raises(SystemExit):
        vh.tham_so_cong_hieu_ung_luu()


def test_du_lieu_hinh5_tinh_voi_tham_so_cong_hien_hanh(vh):
    """hieu-ung-luu.json tính với tham số khác cổng hiện tại = hình 5 đã cũ."""
    du_lieu = _doc(DU_LIEU / "hieu-ung-luu.json")
    assert du_lieu["tham_so_mong_doi"] == {
        "cong": vh.tham_so_cong_hieu_ung_luu(),
        "ban_ra_s": list(vh.BAN_RA_S),
        "seed_them": list(vh.SEED_THEM),
    }
    _tinh_tren_cay_sach(du_lieu)


# ============================================================ 3. số hiệu chuẩn
def test_dem_trong_hieu_chuan_json_khop_so_hieu_chuan():
    """Đếm lại từ giá trị từng lần lặp, không qua hàm của script."""
    du_lieu = _doc(DU_LIEU / "hieu-chuan.json")
    chuan = _doc(SO_HIEU_CHUAN)
    alpha = chuan["alpha"]
    for ten in ("aa", "thu_hoi"):
        kq = du_lieu["ket_qua"][ten]
        c = chuan["nghien_cuu"][ten]
        n = len(kq["p_values"])
        assert n == len(kq["co_phu"]) == c["tham_so"]["n_reps"]
        assert du_lieu["tham_so_mong_doi"][ten] == c["tham_so"]
        assert f"{sum(p < alpha for p in kq['p_values'])}/{n}" == c["so_lan_bac_bo"]
        assert f"{sum(bool(x) for x in kq['co_phu'])}/{n}" == c["so_lan_phu"]
        assert round(kq["do_lech_tuong_doi"], 4) == c["do_lech_tuong_doi"]
    _tinh_tren_cay_sach(du_lieu)


def test_kiem_khop_so_hieu_chuan_dung_khi_lech(vh):
    du_lieu = _doc(DU_LIEU / "hieu-chuan.json")
    dem = vh.kiem_khop_so_hieu_chuan(du_lieu)
    chuan = _doc(SO_HIEU_CHUAN)["nghien_cuu"]
    assert f"{dem['aa']['bac_bo']}/{dem['aa']['n']}" == chuan["aa"]["so_lan_bac_bo"]
    hong = copy.deepcopy(du_lieu)
    p = hong["ket_qua"]["aa"]["p_values"]
    i = next(j for j, x in enumerate(p) if x >= 0.05)
    p[i] = 0.001  # thêm một lần bác bỏ: 7/200 → 8/200
    with pytest.raises(SystemExit):
        vh.kiem_khop_so_hieu_chuan(hong)


# ===================================================================== 4. hình 6
def _chuoi_ktc(vh, d: dict) -> str:
    return f"{vh.so(d['macro_f1'], 3)} [{vh.so(d['ktc'][0], 3)}; {vh.so(d['ktc'][1], 3)}]"


def test_h6_so_lay_dung_tu_json(vh, chi_tiet):
    s = vh.du_lieu_h6(copy.deepcopy(chi_tiet))
    theo_ma = {d["ma"]: d for d in chi_tiet["macro_f1"]}
    assert [d["ma"] for d in s["rung"]] == [ma for ma, _, _ in vh.H6_HE_THONG]
    for d in s["rung"]:
        assert d["macro_f1"] == theo_ma[d["ma"]]["macro_f1"]
        assert d["ktc"] == theo_ma[d["ma"]]["macro_f1_ktc95_bootstrap"]
    mt = chi_tiet["ma_tran_nham_lan"]
    assert mt["he_thong"] == theo_ma[s["he_thong_ma_tran"]]["ten"]
    assert s["ma_tran"] == mt["ma_tran"]
    assert s["tong_hang"] == mt["tong_hang"]
    for i, hang in enumerate(mt["ma_tran"]):
        if sum(hang) == 0:
            assert s["ty_le_hang"][i] is None
        else:
            assert s["ty_le_hang"][i] == [c / sum(hang) for c in hang]
    assert s["n"] == sum(mt["tong_hang"]) == theo_ma[s["he_thong_ma_tran"]]["n_test"]
    assert s["n_bootstrap"] == chi_tiet["n_bootstrap"]
    assert s["so_buoi"] == len(chi_tiet["precision_theo_buoi_va_ty_le_nen"])
    y, m, d = chi_tiet["generated_at"][:10].split("-")
    assert s["ngay_do"] == f"{d}/{m}/{y}"


def test_h6_ma_tran_tai_tao_dung_so_cua_he_thong(vh, chi_tiet):
    """Ma trận vẽ ở (a) và số macro-F1 ở (b) phải là CÙNG một hệ thống."""
    s = vh.du_lieu_h6(chi_tiet)
    he = next(d for d in chi_tiet["macro_f1"] if d["ma"] == s["he_thong_ma_tran"])
    assert round(s["accuracy_ma_tran"], 4) == he["accuracy"]
    assert round(s["macro_f1_ma_tran"], 4) == he["macro_f1"]


def test_h6_bo_nhan_du_11_lop(chi_tiet):
    from livelift.nlp.labels import INTENT_LABELS, LABEL_DISPLAY

    nhan = chi_tiet["ma_tran_nham_lan"]["nhan"]
    assert list(nhan) == list(INTENT_LABELS)
    assert all(x in LABEL_DISPLAY for x in nhan)


def _dat(duong: str, gia_tri):
    def lam(ct: dict) -> None:
        *truoc, cuoi = duong.split(".")
        o = ct
        for k in truoc:
            o = next(d for d in o if d["ma"] == k) if isinstance(o, list) else o[k]
        o[cuoi] = gia_tri(o[cuoi]) if callable(gia_tri) else gia_tri

    return lam


def _chuyen_mot_dem(ct: dict) -> None:
    """Dời 1 dòng từ đường chéo sang ô khác CÙNG hàng: tổng hàng giữ, tổng cột lệch."""
    m = ct["ma_tran_nham_lan"]["ma_tran"]
    m[0][0] -= 1
    m[0][1] += 1


@pytest.mark.parametrize(
    ("sua", "chu_trong_loi"),
    [
        pytest.param(
            _dat("nguon_nhan.test", "Nhãn do hai thành viên gán"), "tác tử AI", id="nhan-nguoi"
        ),
        pytest.param(
            _dat("nguon_nhan.data", "Bình luận lấy qua API chính thức"), "yt-dlp", id="nguon-api"
        ),
        pytest.param(
            _dat("ma_tran_nham_lan.he_thong", "C9 · không tồn tại"), "C9", id="ma-tran-la"
        ),
        pytest.param(
            _dat("ma_tran_nham_lan.quy_tac_chon", "Chọn dòng điểm cao nhất"),
            "intent_clf_v2",
            id="khong-phai-ban-dong-goi",
        ),
        pytest.param(_chuyen_mot_dem, "tổng hàng/cột", id="tong-cot-lech"),
        pytest.param(
            _dat("macro_f1.C2.macro_f1", 0.6), "macro-F1 từ ma trận", id="f1-khac-ma-tran"
        ),
        pytest.param(
            _dat("macro_f1.C2.accuracy", 0.9), "accuracy từ ma trận", id="acc-khac-ma-tran"
        ),
        pytest.param(_dat("macro_f1.C1.thang", "6_lop_gop"), "thang", id="thang-6-lop"),
        pytest.param(_dat("macro_f1.B2.ten", "B2 · một bộ khác"), "ĐANG CHẠY", id="b2-doi-nghia"),
        pytest.param(_dat("macro_f1.A0.macro_f1", 0.6), "A0", id="a0-khac-c2"),
        pytest.param(_dat("macro_f1.A4.n_test", 200), "200", id="n-test-khac"),
    ],
)
def test_h6_dung_khi_du_lieu_khong_noi_dung_dieu_hinh_khai(vh, chi_tiet, sua, chu_trong_loi):
    hong = copy.deepcopy(chi_tiet)
    sua(hong)
    with pytest.raises(SystemExit) as loi:
        vh.du_lieu_h6(hong)
    assert chu_trong_loi in str(loi.value.code)


def test_h6_cau_c1_c2_chi_in_khi_con_dung(vh):
    goc = {
        "he_thong_ma_tran": "C2",
        "rung": [
            {"ma": "C1", "macro_f1": 0.56, "ktc": [0.49, 0.62]},
            {"ma": "C2", "macro_f1": 0.54, "ktc": [0.48, 0.62]},
        ],
    }
    assert any("C1 (0,560) cao hơn C2" in x and "KTC chồng lấn" in x for x in vh._luu_y_h6(goc))
    c1_thap = copy.deepcopy(goc)
    c1_thap["rung"][0]["macro_f1"] = 0.50
    assert not any("cao hơn" in x for x in vh._luu_y_h6(c1_thap))
    tach = copy.deepcopy(goc)
    tach["rung"][0].update(macro_f1=0.8, ktc=[0.7, 0.9])
    cau = [x for x in vh._luu_y_h6(tach) if "cao hơn" in x]
    assert cau
    assert "chồng lấn" not in cau[0]


def test_h6_trong_kho_duoc_ve_tu_ban_json_hien_tai(vh, chi_tiet):
    """Chạy lại bộ đánh giá ý định mà quên `--chi h6` thì PNG/NGUON.md nói số cũ."""
    tom_tat = _doc(DU_LIEU / "tom-tat.json")
    assert "h6" in tom_tat, "chưa vẽ hình 6 — chạy: python scripts/ve_hinh_ho_so.py --chi h6"
    h = tom_tat["h6"]
    s = vh.du_lieu_h6(chi_tiet)
    ghi_lai = "đo lại ý định mà chưa vẽ lại — chạy: python scripts/ve_hinh_ho_so.py --chi h6"
    assert h["rung"] == [{k: d[k] for k in ("ma", "nhan", "macro_f1", "ktc")} for d in s["rung"]], (
        ghi_lai
    )
    assert h["ma_tran"] == s["ma_tran"], ghi_lai
    assert (h["n"], h["so_buoi"], h["ngay_do"]) == (s["n"], s["so_buoi"], s["ngay_do"]), ghi_lai
    nguon = (HINH / "NGUON.md").read_text(encoding="utf-8")
    for d in s["rung"]:
        assert f"{d['ma']} {_chuoi_ktc(vh, d)}" in nguon


def test_nguon_md_sinh_tu_tom_tat_khong_sua_tay(vh, monkeypatch, tmp_path):
    """NGUON.md phải đúng bằng cái ghi_nguon() viết ra từ tom-tat.json đang lưu."""
    ra = tmp_path / "hinh"
    ra.mkdir()
    # ghi_nguon đọc pyproject (câu hướng dẫn cài) và in đường dẫn tương đối theo GOC
    (tmp_path / "pyproject.toml").write_bytes((GOC / "pyproject.toml").read_bytes())
    monkeypatch.setattr(vh, "RA", ra)
    monkeypatch.setattr(vh, "GOC", tmp_path)
    vh.ghi_nguon(_doc(DU_LIEU / "tom-tat.json"))
    assert (ra / "NGUON.md").read_text(encoding="utf-8") == (HINH / "NGUON.md").read_text(
        encoding="utf-8"
    )
    # Hội đồng thử 25/09/2026: /host vẫn hiện sản phẩm đang ghim, và ở chế độ Tự ghim lệnh
    # ghim chỉ đến trong khối BẬT — hồ sơ mục 5.3 nói làm mù "một phần". Hình 2 (hồ sơ
    # gọi là Hình 6) và NGUON.md không được nói người dẫn "bị làm mù"; thứ bị che là lịch.
    for ten, chu in (
        ("html_h2()", vh.html_h2()),
        ("h2-kien-truc.html", (HINH / "h2-kien-truc.html").read_text(encoding="utf-8")),
        ("NGUON.md", (HINH / "NGUON.md").read_text(encoding="utf-8")),
    ):
        assert "làm mù" not in chu, f"{ten} còn nói người dẫn bị làm mù"
        assert "không thấy lịch" in chu, f"{ten} phải nói thứ bị che là lịch"


# ------------------------------------------------------------------ khổ in PNG
def _kho_png(duong: Path) -> tuple[float, float, float]:
    """(rộng cm, cao cm, dpi) đọc thẳng từ IHDR + pHYs — không cần Pillow."""
    b = duong.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n", f"{duong.name} không phải PNG"
    rong_px, cao_px = struct.unpack(">II", b[16:24])
    i = b.find(b"pHYs")
    assert i > 0, f"{duong.name} không ghi dpi — Word sẽ chèn sai khổ"
    px_x, _, don_vi = struct.unpack(">IIB", b[i + 4 : i + 13])
    assert don_vi == 1  # điểm ảnh / mét
    dpi = px_x * 0.0254
    return rong_px / dpi * 2.54, cao_px / dpi * 2.54, dpi


@pytest.mark.parametrize("ten", sorted(p.name for p in HINH.glob("h*.png")))
def test_hinh_ho_so_dung_kho_16_cm_300_dpi(ten):
    rong, _, dpi = _kho_png(HINH / ten)
    assert round(dpi) == 300
    assert rong <= 16.0 + 1e-9


def test_h6_ton_tai_va_khong_qua_cao(vh):
    rong, cao, _ = _kho_png(HINH / "h6-nlp.png")
    assert rong <= vh.H6_RONG_CM + 1e-9
    assert cao <= vh.H6_CAO_CM + 0.01 <= 8.5 + 0.01


# ------------------------------------------------------- dựng hình (cần matplotlib)
def _chu_tren_hinh(fig) -> list:
    from matplotlib.text import Text

    return [t for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()]


def test_h6_so_tren_hinh_dung_json_va_chu_du_lon(vh, plt, chi_tiet):
    s = vh.du_lieu_h6(chi_tiet)
    fig = vh.hinh_h6(plt, s)
    try:
        fig.canvas.draw()  # chốt nhãn trục như lúc lưu PNG
        chu = _chu_tren_hinh(fig)
        noi_dung = [t.get_text() for t in chu]
        for d in s["rung"]:
            assert _chuoi_ktc(vh, d) in noi_dung, d["ma"]
            assert f"{d['ma']} · {d['nhan']}" in noi_dung
        chan = next(x for x in noi_dung if x.startswith("Nhãn tham chiếu"))
        assert (
            f"Nhãn tham chiếu do tác tử AI gán, {vh.so(s['n'], 0)} bình luận thật, "
            "leave-one-session-out" in chan
        )
        assert "chi-tiet-hinh.json" in chan
        assert s["ngay_do"] in chan
        for ten in s["ten_lop"]:
            assert noi_dung.count(ten) == 2  # nhãn hàng + nhãn cột
        # từng ô khác 0 mang đúng % của hàng, ở đúng vị trí
        ax = fig.axes[0]
        o = {
            (round(t.get_position()[0] - 0.5), round(t.get_position()[1] - 0.54)): t.get_text()
            for t in ax.texts
            if t.get_position()[0] < len(s["nhan"])
        }
        for i, hang in enumerate(s["ty_le_hang"]):
            for j, v in enumerate(hang or []):
                if s["ma_tran"][i][j]:
                    assert o[(j, i)] == str(round(100 * v)), (i, j)
        nho = [(t.get_text(), t.get_fontsize()) for t in chu if t.get_fontsize() < 7.5]
        assert not nho
        rong_cm, cao_cm = (x * 2.54 for x in fig.get_size_inches())
        assert rong_cm <= 16.0 + 1e-9
        assert cao_cm <= 8.5
        vh._kiem_nhan_h6(fig, s)  # nhãn không đè KTC với số hiện tại
    finally:
        plt.close(fig)


def test_h6_so_tren_hinh_di_theo_json_khong_go_tay(vh, plt, chi_tiet):
    hong = copy.deepcopy(chi_tiet)
    b1 = next(d for d in hong["macro_f1"] if d["ma"] == "B1")
    b1["macro_f1"], b1["macro_f1_ktc95_bootstrap"] = 0.1234, [0.1, 0.15]
    fig = vh.hinh_h6(plt, vh.du_lieu_h6(hong))
    try:
        noi_dung = [t.get_text() for t in _chu_tren_hinh(fig)]
        assert "0,123 [0,100; 0,150]" in noi_dung
        assert not any(x.startswith("0,146 [") for x in noi_dung)
    finally:
        plt.close(fig)


def test_h6_dung_khi_nhan_se_de_len_ktc(vh, plt, chi_tiet):
    hong = copy.deepcopy(chi_tiet)
    b3 = next(d for d in hong["macro_f1"] if d["ma"] == "B3")
    b3["macro_f1"], b3["macro_f1_ktc95_bootstrap"] = 0.2, [0.01, 0.3]
    s = vh.du_lieu_h6(hong)
    fig = vh.hinh_h6(plt, s)
    try:
        with pytest.raises(SystemExit) as loi:
            vh._kiem_nhan_h6(fig, s)
        assert "B3" in str(loi.value.code)
    finally:
        plt.close(fig)
