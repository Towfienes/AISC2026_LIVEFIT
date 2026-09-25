"""Vẽ sáu hình minh hoạ cho hồ sơ thuyết minh Sáng tạo trẻ AI 2026 (Bảng C).

Vì sao tệp này tồn tại
----------------------
Hồ sơ hứa "mọi con số sinh lại được bằng một lệnh". Hình vẽ cũng là con số:
một biểu đồ vẽ tay từ số chép lại sẽ lặp đúng lớp lỗi của sự cố A/A 14/09
(số cũ nằm lại trong tài liệu sau khi mã đã đổi). Vì vậy KHÔNG có con số nào
trên hình được gõ tay: lịch khối sinh bằng chính hàm gán production, số hiệu
chuẩn chạy lại bằng đúng tham số của cổng và đối chiếu với
``docs/benchmarks/so-hieu-chuan.json``, MDE tính bằng ``livelift.analysis.power``,
số phân loại ý định (hình 6) đọc từ ``docs/benchmarks/intent-eval/chi-tiet-hinh.json``
do ``python -m livelift.nlp.eval_intent --ablation --coverage`` ghi.
Chân mỗi hình ghi nguồn.

Chạy (từ gốc kho)::

    .venv/Scripts/python scripts/ve_hinh_ho_so.py               # vẽ cả 6 hình
    .venv/Scripts/python scripts/ve_hinh_ho_so.py --chi h1,h4   # chỉ vẽ vài hình
    .venv/Scripts/python scripts/ve_hinh_ho_so.py --kiem        # chạy lại, đối chiếu du-lieu/
    .venv/Scripts/python scripts/ve_hinh_ho_so.py --tinh-lai    # chạy lại Monte-Carlo, ghi đè

Hình 3 và 5 cần giá trị TỪNG lần lặp Monte-Carlo (vài phút CPU). Lần chạy đầu
tự tính và lưu vào ``docs/competition/sang-tao-tre-2026/hinh/du-lieu/*.json``
(kèm tham số, ngày đo, bản git); các lần sau đọc lại tệp đó, trừ khi tham số của
cổng đã đổi (khi đó báo lỗi và đòi ``--tinh-lai``) hoặc có ``--tinh-lai``.
``--kiem`` KHÔNG ghi đè ``du-lieu/``, nhưng vẫn vẽ lại các hình, ``tom-tat.json``
và ``NGUON.md`` từ số vừa chạy (trùng từng lần lặp với tệp đã lưu nếu khớp).
Số tổng của A/A PHẢI khớp ``so-hieu-chuan.json`` — lệch thì script DỪNG, không vẽ.

Phụ thuộc ngoài pyproject: ``matplotlib`` (hình 1, 3, 4, 5, 6) và Playwright +
Chromium (hình 2, sơ đồ kiến trúc viết bằng HTML rồi chụp ở 300 dpi).

Kích thước: mọi hình rộng đúng 16 cm (bề rộng vùng chữ của hồ sơ: A4, lề trái
3 cm, lề phải 2 cm), 300 dpi, chữ nhỏ nhất 8 pt (hình 6: 7,5 pt cho số trong ô ma
trận, cao 8,2 cm). Chèn vào hồ sơ bằng
``![Hình N. ...](hinh/<tệp>.png){width=16cm}`` (cú pháp của ``dung_ho_so.py``;
chú thích phải bắt đầu bằng "Hình N.") để chữ in ra vẫn ≥ 8 pt.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

# Giới hạn luồng BLAS TRƯỚC khi numpy nạp: lần đo hiệu ứng lưu ngày 25/09 chết
# vì OpenBLAS xin bộ nhớ cho nhiều luồng trên máy đang thiếu RAM.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402
from scipy.stats import binom, binomtest  # noqa: E402

from livelift.analysis.power import (  # noqa: E402
    PowerInputs,
    analysis_window_seconds,
    mde_relative,
    poisson_cv,
    within_session_cv,
)
from livelift.console import configure  # noqa: E402
from livelift.core.assigner.outer import (  # noqa: E402
    ON,
    DesignParams,
    design_hash,
    generate_schedule,
)
from livelift.core.features import block_frame, blocks_to_dicts  # noqa: E402
from livelift.sim.simulator import SimParams, simulate_session  # noqa: E402
from livelift.sim.validate import run_validation  # noqa: E402

GOC = Path(__file__).resolve().parents[1]
RA = GOC / "docs" / "competition" / "sang-tao-tre-2026" / "hinh"
DU_LIEU = RA / "du-lieu"
SO_HIEU_CHUAN = GOC / "docs" / "benchmarks" / "so-hieu-chuan.json"
LENH = "python scripts/ve_hinh_ho_so.py"

RONG_CM = 16.0
DPI = 300
CM = 1 / 2.54

# ------------------------------------------------------------------ bảng màu
# Màu dịu, in đen trắng vẫn phân biệt được bằng ĐỘ SÁNG (không chỉ bằng sắc);
# mọi cặp cần phân biệt còn có thêm kênh thứ hai (gạch chéo, kiểu nét, nhãn).
MUC = "#0b0b0b"  # chữ chính
MUC_PHU = "#52514e"  # chữ phụ
MUC_MO = "#898781"  # trục, chú thích nhỏ
LUOI = "#e1e0d9"
XANH_DAM = "#256abf"
XANH = "#2a78d6"
XANH_NHAT = "#86b6ef"
XANH_RAT_NHAT = "#cde2fb"
XANH_TOI = "#0d366b"
XANH_VUA = "#5598e7"
CAM = "#eb6834"
XAM_NEN = "#f0efec"
XAM_TAT = "#e3e1da"
DO_CONG = "#b3261e"


# ------------------------------------------------------------ định dạng số VN
def so(x: float, nd: int = 2) -> str:
    """Số kiểu Việt Nam: dấu chấm phân nghìn, dấu phẩy thập phân, dấu trừ thật."""
    r = round(float(x), nd)
    s = f"{abs(r):,.{nd}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return ("−" if r < 0 else "") + s


def phan_tram(x: float, nd: int = 2) -> str:
    return f"{so(100 * x, nd)}%"


# ----------------------------------------------------------- nạp phụ thuộc
def cach_cai_goi_ve() -> str:
    """Câu hướng dẫn cài gói vẽ, đọc từ pyproject: đúng cả khi có lẫn chưa có extra ``hinh``."""
    import tomllib

    du_an = tomllib.loads((GOC / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    if "hinh" in du_an.get("optional-dependencies", {}):
        return 'cài bằng `pip install -e ".[hinh]"` rồi `playwright install chromium`'
    return (
        "matplotlib không nằm trong pyproject — cài riêng bằng `pip install matplotlib`; "
        "hình 2 cần thêm Playwright + Chromium"
    )


def nap_matplotlib():
    try:
        import matplotlib
    except ModuleNotFoundError:
        sys.exit(f"Thiếu matplotlib (chỉ dùng để vẽ hình hồ sơ): {cach_cai_goi_ve()}.")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8.5,
            "axes.titlesize": 9,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.labelsize": 8.5,
            "axes.labelcolor": MUC_PHU,
            "axes.edgecolor": "#c3c2b7",
            "axes.linewidth": 0.6,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "xtick.color": MUC_PHU,
            "ytick.color": MUC_PHU,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "legend.fontsize": 8,
            "legend.frameon": False,
            "axes.unicode_minus": True,
            "svg.fonttype": "none",
            "hatch.linewidth": 0.6,
        }
    )
    return plt


def chan_nguon(fig, dong: str, y: float = 0.012) -> None:
    """Dòng nguồn ở chân hình — 8 pt, màu phụ, xuống dòng theo bề rộng hình."""
    fig.text(
        0.012,
        y,
        dong,
        fontsize=8,
        color=MUC_PHU,
        ha="left",
        va="bottom",
        wrap=True,
        linespacing=1.25,
    )


def luu(fig, ten: str) -> Path:
    RA.mkdir(parents=True, exist_ok=True)
    duong = RA / ten
    # KHÔNG dùng bbox_inches="tight": nó cắt lề và làm bề rộng lệch khỏi 16 cm.
    fig.savefig(duong, dpi=DPI, facecolor="white")
    rong, cao = _kiem_kho(duong)
    print(f"  đã ghi {duong.relative_to(GOC)} ({so(rong, 2)} × {so(cao, 1)} cm)")
    return duong


def truc_toi_gian(ax) -> None:
    for canh in ("top", "right"):
        ax.spines[canh].set_visible(False)
    ax.tick_params(length=2.5)


# ------------------------------------------------------------ nguồn tham số
def nap_do_lai_so_hieu_chuan():
    """Nạp scripts/do_lai_so_hieu_chuan.py để dùng ĐÚNG ``NGHIEN_CUU`` của nó."""
    duong = GOC / "scripts" / "do_lai_so_hieu_chuan.py"
    spec = importlib.util.spec_from_file_location("do_lai_so_hieu_chuan", duong)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def tham_so_cong_hieu_ung_luu() -> dict:
    """Đọc tham số của cổng hiệu ứng lưu thẳng từ mã nguồn test (không chép tay).

    ``tests/test_sim_validation.py::test_estimator_under_carryover_interference``
    gọi ``run_validation(...)`` bằng hằng số viết trực tiếp; hàm này bóc chúng ra
    bằng ``ast`` để hình và cổng không thể trôi khỏi nhau.
    """
    nguon = (GOC / "tests" / "test_sim_validation.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    for nut in ast.walk(cay):
        if (
            isinstance(nut, ast.FunctionDef)
            and nut.name == "test_estimator_under_carryover_interference"
        ):
            for goi in ast.walk(nut):
                if isinstance(goi, ast.Call) and getattr(goi.func, "id", None) == "run_validation":
                    ts: dict = {}
                    for kw in goi.keywords:
                        if kw.arg == "sim_params":
                            for k2 in kw.value.keywords:
                                ts[k2.arg] = ast.literal_eval(k2.value)
                        else:
                            ts[kw.arg] = ast.literal_eval(kw.value)
                    return ts
    raise SystemExit("Không tìm thấy lời gọi run_validation trong cổng hiệu ứng lưu — test đã đổi?")


def nguong_phu_cong_hieu_ung_luu() -> float:
    """Ngưỡng độ phủ mà cổng đòi (``assert res.ci_coverage >= X``), bóc bằng ``ast``.

    Tách khỏi :func:`tham_so_cong_hieu_ung_luu` vì tham số đó là khoá đối chiếu
    của ``du-lieu/hieu-ung-luu.json``; ngưỡng chỉ dùng để vẽ, không đổi dữ liệu.
    """
    cay = ast.parse((GOC / "tests" / "test_sim_validation.py").read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if (
            isinstance(nut, ast.FunctionDef)
            and nut.name == "test_estimator_under_carryover_interference"
        ):
            for a in ast.walk(nut):
                if (
                    isinstance(a, ast.Assert)
                    and isinstance(a.test, ast.Compare)
                    and isinstance(a.test.left, ast.Attribute)
                    and a.test.left.attr == "ci_coverage"
                    and isinstance(a.test.ops[0], ast.GtE)
                ):
                    return float(ast.literal_eval(a.test.comparators[0]))
    raise SystemExit("Không tìm thấy 'assert res.ci_coverage >= …' trong cổng hiệu ứng lưu.")


# Bán rã cần vẽ (giây). 120 s là mức của cổng; 0 s và 180 s là hai mức của
# test_carryover_attenuates_relative_to_clean_world — cùng bộ ba mà docstring
# run_validation (livelift/sim/validate.py) công bố.
BAN_RA_S = (0.0, 120.0, 180.0)
# Seed của cổng + hai seed thêm mà kiểm toán 25/09 dùng để đo lại (dossier-audit-B §1.1):
# với 25 lần lặp, sai số chuẩn của độ phủ ~8–9 điểm %, một seed là không đủ.
SEED_THEM = (2026, 11)

# Phiên mô phỏng để đo CV trong phiên cho điểm "mô phỏng" của hình 4 — đúng bước 1
# của tests/test_power.py::test_predicted_mde_matches_achieved_power.
MDE_SO_PHIEN_MO_PHONG = 8
MDE_SEED_GOC = 900
PHIEN_PHUT = 90
KHOI_PHUT = DesignParams().block_min

# Seed của lịch minh hoạ hình 1 — seed mà buổi chạy thử đầu-cuối 11/09 đã bốc
# (docs/benchmarks/nhat-ky-test.md), để hình khớp ảnh chụp giao diện.
SEED_LICH = 42


# ---------------------------------------------------------------- tiện ích git
def ban_git_hien_tai(mod_do_lai) -> str:
    """Bản git của mã, đọc MỘT lần ở đầu ``main`` trước khi script ghi bất cứ tệp nào.

    Đọc lại sau mỗi lần ghi thì chính đầu ra của hình trước (h1, h2, ``hieu-chuan.json``,
    ``h3-hieu-chuan-aa.png``) làm ``git status`` thấy cây bẩn, và hình 5 bị đóng dấu
    "+ban-lam-viec-co-thay-doi" dù chạy ``--tinh-lai`` trên cây sạch (25/09/2026).
    """
    return mod_do_lai.ban_git()


# ======================================================== DỮ LIỆU MONTE-CARLO
def _ket_qua_sang_dict(res) -> dict:
    return {
        "ty_le_bac_bo": res.rejection_rate,
        "do_phu_ktc": res.ci_coverage,
        "do_lech_tuong_doi": res.relative_bias,
        "p_values": list(res.p_values),
        "co_phu": list(res.coverage_flags),
        "uoc_luong": list(res.estimates),
        "gia_tri_that": list(res.truths),
    }


def tinh_hieu_chuan(mod_do_lai) -> dict:
    """A/A + thu hồi tác động, bằng đúng NGHIEN_CUU của do_lai_so_hieu_chuan.py."""
    ket_qua: dict = {}
    for ten, ch in mod_do_lai.NGHIEN_CUU.items():
        t0 = time.time()
        print(f"  Monte-Carlo {ten}: {ch['tham_so']['n_reps']} lần lặp…", flush=True)
        res = run_validation(
            sim_params=SimParams(treatment_effect=ch["treatment_effect"]),
            **ch["tham_so"],
        )
        ket_qua[ten] = {
            "tham_so": ch["tham_so"] | {"treatment_effect": ch["treatment_effect"]},
            **_ket_qua_sang_dict(res),
            "giay": round(time.time() - t0, 1),
        }
    return ket_qua


def tinh_hieu_ung_luu() -> dict:
    cong = tham_so_cong_hieu_ung_luu()
    seeds = (cong["master_seed"], *SEED_THEM)
    ket_qua: dict = {"tham_so_cong": cong, "seeds": list(seeds), "ban_ra": {}}
    for hl in BAN_RA_S:
        theo_seed = {}
        for seed in seeds:
            t0 = time.time()
            print(f"  Monte-Carlo hiệu ứng lưu: bán rã {hl:.0f} s, seed {seed}…", flush=True)
            res = run_validation(
                n_reps=cong["n_reps"],
                n_sessions_per_rep=cong["n_sessions_per_rep"],
                session_minutes=cong["session_minutes"],
                sim_params=SimParams(
                    treatment_effect=cong["treatment_effect"], carryover_halflife_s=hl
                ),
                n_draws=cong["n_draws"],
                master_seed=seed,
            )
            theo_seed[str(seed)] = _ket_qua_sang_dict(res) | {"giay": round(time.time() - t0, 1)}
        ket_qua["ban_ra"][f"{hl:.0f}"] = theo_seed
    return ket_qua


def _tep_du_lieu(ten: str) -> Path:
    return DU_LIEU / f"{ten}.json"


def _bo_thoi_gian(x):
    """Bỏ các khoá thời gian chạy ("giay") để so hai lần đo theo NỘI DUNG."""
    if isinstance(x, dict):
        return {k: _bo_thoi_gian(v) for k, v in x.items() if k != "giay"}
    if isinstance(x, list):
        return [_bo_thoi_gian(v) for v in x]
    return x


def doc_hoac_tinh(ten: str, ham_tinh, tham_so_mong_doi: dict, che_do: str, ban_git: str) -> dict:
    """``che_do``: "doc" (đọc tệp đã lưu, tính nếu chưa có) · "tinh_lai" · "kiem".

    "kiem" chạy lại Monte-Carlo và đối chiếu TỪNG lần lặp với tệp đã lưu, không
    ghi đè tệp đó; lệch là DỪNG với mã thoát 1 — đúng vai trò của ``--kiem`` trong
    scripts/do_lai_so_hieu_chuan.py. (``main`` vẫn vẽ lại hình từ số vừa chạy.)
    """
    tep = _tep_du_lieu(ten)
    if che_do == "kiem":
        if not tep.exists():
            sys.exit(f"DỪNG: chưa có {tep.relative_to(GOC)} — chạy kèm --tinh-lai trước.")
        da_luu = json.loads(tep.read_text(encoding="utf-8"))
        if da_luu.get("tham_so_mong_doi") != tham_so_mong_doi:
            sys.exit(f"DỪNG: {tep.relative_to(GOC)} được tính với tham số khác tham số của cổng.")
        moi = json.loads(json.dumps(ham_tinh()))
        if _bo_thoi_gian(moi) != _bo_thoi_gian(da_luu["ket_qua"]):
            sys.exit(
                f"DỪNG: chạy lại KHÔNG khớp {tep.relative_to(GOC)} (đo {da_luu['ngay_do']}) — "
                "mã hoặc môi trường đã đổi; chạy kèm --tinh-lai rồi cập nhật mọi tài liệu trích số."
            )
        print(f"  khớp từng lần lặp với {tep.relative_to(GOC)} (đo {da_luu['ngay_do']})")
        return da_luu
    if tep.exists() and che_do == "doc":
        du_lieu = json.loads(tep.read_text(encoding="utf-8"))
        if du_lieu.get("tham_so_mong_doi") != tham_so_mong_doi:
            sys.exit(
                f"DỪNG: {tep.relative_to(GOC)} được tính với tham số khác tham số hiện tại "
                f"của cổng.\n  đã lưu : {du_lieu.get('tham_so_mong_doi')}\n"
                f"  hiện tại: {tham_so_mong_doi}\nChạy lại kèm --tinh-lai."
            )
        print(
            f"  đọc {tep.relative_to(GOC)} (đo ngày {du_lieu['ngay_do']}, bản {du_lieu['ban_git']})"
        )
        return du_lieu
    t0 = time.time()
    ket_qua = ham_tinh()
    du_lieu = {
        "ngay_do": date.today().isoformat(),
        "ban_git": ban_git,
        "lenh": f"{LENH} --tinh-lai",
        "tham_so_mong_doi": tham_so_mong_doi,
        "ghi_chu": "Sinh bằng scripts/ve_hinh_ho_so.py. Dữ liệu MÔ PHỎNG Monte-Carlo, "
        "không phải phiên thí nghiệm thật. Sửa tay tệp này là sai quy trình — chạy lại script.",
        "tong_giay": round(time.time() - t0, 1),
        "moi_truong": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": importlib.import_module("scipy").__version__,
        },
        "ket_qua": ket_qua,
    }
    DU_LIEU.mkdir(parents=True, exist_ok=True)
    tep.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  đã ghi {tep.relative_to(GOC)} ({du_lieu['tong_giay']:.0f} s)")
    return du_lieu


def kiem_khop_so_hieu_chuan(du_lieu: dict) -> dict:
    """Số tổng của lần chạy này PHẢI trùng so-hieu-chuan.json. Lệch → DỪNG."""
    chuan = json.loads(SO_HIEU_CHUAN.read_text(encoding="utf-8"))["nghien_cuu"]
    kq = du_lieu["ket_qua"]
    dem = {}
    lech = []
    for ten in ("aa", "thu_hoi"):
        n = len(kq[ten]["p_values"])
        n_bac_bo = sum(1 for p in kq[ten]["p_values"] if p < 0.05)
        n_phu = sum(kq[ten]["co_phu"])
        dem[ten] = {"n": n, "bac_bo": n_bac_bo, "phu": n_phu}
        for khoa, gia_tri in (("so_lan_bac_bo", n_bac_bo), ("so_lan_phu", n_phu)):
            if chuan[ten][khoa] != f"{gia_tri}/{n}":
                lech.append(
                    f"{ten}.{khoa}: so-hieu-chuan.json ghi {chuan[ten][khoa]} ≠ đo {gia_tri}/{n}"
                )
        if round(kq[ten]["do_lech_tuong_doi"], 4) != chuan[ten]["do_lech_tuong_doi"]:
            lech.append(
                f"{ten}.do_lech_tuong_doi: ghi {chuan[ten]['do_lech_tuong_doi']} ≠ đo "
                f"{round(kq[ten]['do_lech_tuong_doi'], 4)}"
            )
    if lech:
        sys.exit(
            "DỪNG — số A/A không khớp docs/benchmarks/so-hieu-chuan.json:\n  - "
            + "\n  - ".join(lech)
        )
    print(
        f"  khớp so-hieu-chuan.json: A/A bác bỏ {dem['aa']['bac_bo']}/{dem['aa']['n']}, "
        f"phủ {dem['aa']['phu']}/{dem['aa']['n']}; thu hồi phủ "
        f"{dem['thu_hoi']['phu']}/{dem['thu_hoi']['n']}"
    )
    return dem


def ktc_nhi_thuc(k: int, n: int) -> tuple[float, float]:
    ci = binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
    return float(ci.low), float(ci.high)


# ================================================================== HÌNH 1
def ve_h1(plt) -> dict:
    from matplotlib.patches import Patch, Rectangle

    from livelift.api.routes.reports import BURN_IN_S

    tham_so = DesignParams()
    lich = generate_schedule(PHIEN_PHUT, tham_so, seed=SEED_LICH)
    ma_bam = design_hash(tham_so, SEED_LICH)
    khoi = lich.measurement_blocks

    fig = plt.figure(figsize=(RONG_CM * CM, 7.7 * CM))
    ax = fig.add_axes((0.02, 0.335, 0.965, 0.655))
    x_min, x_max = -10.0, PHIEN_PHUT + 0.8
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-0.08, 3.75)
    for canh in ("top", "right", "left"):
        ax.spines[canh].set_visible(False)
    ax.spines["bottom"].set_bounds(0, PHIEN_PHUT)
    ax.set_yticks([])
    ax.set_xticks(range(0, PHIEN_PHUT + 1, 10))
    ax.tick_params(axis="x", length=2.5, pad=2)
    fig.text(
        0.02 + 0.965 * (0 - x_min + PHIEN_PHUT / 2) / (x_max - x_min),
        0.245,
        "Thời gian kể từ lúc lên sóng (phút)",
        ha="center",
        va="center",
        fontsize=8.5,
        color=MUC_PHU,
    )

    y0, cao = 1.05, 0.9
    # vùng trước giờ phát (không theo tỉ lệ thời gian)
    ax.add_patch(
        Rectangle((x_min, 0.3), -x_min - 1.2, 2.25, facecolor=XAM_NEN, edgecolor="none", zorder=0)
    )
    ax.text(
        (x_min - 1.2) / 2,
        0.42,
        "trước\ngiờ phát",
        fontsize=8,
        color=MUC_PHU,
        ha="center",
        va="bottom",
        linespacing=1.1,
    )

    for b in khoi:
        x = b.start_offset_s / 60
        w = b.duration_s / 60
        bat = b.assignment == ON
        ax.add_patch(
            Rectangle(
                (x, y0),
                w,
                cao,
                facecolor=XANH_DAM if bat else XAM_TAT,
                edgecolor="none",
                hatch="////" if bat else None,
                hatchcolor="#5b8fd6" if bat else None,
                zorder=2,
            )
        )
        # burn-in: đúng quy tắc block_frame — min(burn_in, max(dài − 30, 0)) giây đầu khối
        bi = min(BURN_IN_S, max(b.duration_s - 30, 0)) / 60
        ax.add_patch(
            Rectangle((x, y0), bi, cao, facecolor=MUC, alpha=0.6, edgecolor="none", zorder=3)
        )
        ax.text(
            x + bi + (w - bi) / 2,
            y0 + cao / 2,
            "BẬT" if bat else "TẮT",
            ha="center",
            va="center",
            rotation=90,
            fontsize=8,
            color="white" if bat else MUC,
            zorder=4,
            fontweight="bold" if bat else "normal",
        )
        ax.plot([x, x], [y0, y0 + cao], color="white", lw=1.4, zorder=5, solid_capstyle="butt")
    ax.add_patch(
        Rectangle((0, y0), PHIEN_PHUT, cao, facecolor="none", edgecolor=MUC_MO, lw=0.6, zorder=6)
    )

    # giai đoạn (tầng của ràng buộc cân bằng khi bốc lại)
    ten_gd = {"early": "Giai đoạn đầu", "mid": "Giai đoạn giữa", "late": "Giai đoạn cuối"}
    yb = y0 + cao + 0.14
    for gd in ("early", "mid", "late"):
        kgd = [b for b in khoi if b.phase == gd]
        a, c = kgd[0].start_offset_s / 60, kgd[-1].end_offset_s / 60
        ax.plot(
            [a + 0.3, a + 0.3, c - 0.3, c - 0.3],
            [yb - 0.07, yb, yb, yb - 0.07],
            color=MUC_MO,
            lw=0.7,
        )
        n_bat = sum(1 for b in kgd if b.assignment == ON)
        ax.text(
            (a + c) / 2,
            yb + 0.06,
            f"{ten_gd[gd]}: {len(kgd)} khối\n{n_bat} BẬT · {len(kgd) - n_bat} TẮT",
            ha="center",
            va="bottom",
            fontsize=8,
            color=MUC_PHU,
            linespacing=1.15,
        )

    # mốc lên sóng + kết thúc (hàng T2) và mốc khoá lịch (hàng T1)
    y_t2, y_t1 = 3.0, 3.52
    for xm in (0, PHIEN_PHUT):
        ax.plot([xm, xm], [y0 - 0.03, y_t2 - 0.02], color=MUC, lw=1.1, zorder=7)
    ax.text(
        0.5,
        y_t2,
        "Lên sóng — POST /start; chưa có lịch gán → HTTP 409, không phát được",
        fontsize=8,
        ha="left",
        va="center",
        color=MUC,
    )
    ax.text(
        PHIEN_PHUT - 0.5,
        y_t2,
        f"Kết thúc — POST /end, phút {PHIEN_PHUT}",
        fontsize=8,
        ha="right",
        va="center",
        color=MUC,
    )
    xk = (x_min - 1.2) / 2
    ax.plot([xk, xk], [y0 + cao / 2, y_t1 - 0.02], color=MUC, lw=0.9, ls=(0, (1.5, 1.5)), zorder=6)
    ax.plot([xk], [y0 + cao / 2], marker="D", ms=5.5, color=DO_CONG, mec="white", mew=0.8, zorder=7)
    ax.text(
        xk + 0.8,
        y_t1,
        f"Khoá lịch TRƯỚC giờ phát — POST /schedule lưu lịch + design_hash {ma_bam[:16]}…",
        fontsize=8,
        ha="left",
        va="center",
        color=MUC,
    )

    # khối đầu / cuối nhân đôi (hàng dưới dải)
    dau, cuoi = khoi[0], khoi[-1]
    yc = y0 - 0.1
    for b in (dau, cuoi):
        a, c = b.start_offset_s / 60, b.end_offset_s / 60
        ax.plot(
            [a + 0.2, a + 0.2, c - 0.2, c - 0.2],
            [yc + 0.07, yc, yc, yc + 0.07],
            color=MUC_PHU,
            lw=0.7,
        )
    ax.text(
        dau.start_offset_s / 60 + 0.2,
        yc - 0.08,
        f"Khối đầu {so(dau.duration_s / 60, 1)} phút\n(2 × {tham_so.block_min} phút ± lệch biên)",
        ha="left",
        va="top",
        fontsize=8,
        color=MUC,
        linespacing=1.15,
    )
    ax.text(
        cuoi.end_offset_s / 60 - 0.2,
        yc - 0.08,
        f"Khối cuối {so(cuoi.duration_s / 60, 1)} phút\n(2 × {tham_so.block_min} phút ± lệch biên)",
        ha="right",
        va="top",
        fontsize=8,
        color=MUC,
        linespacing=1.15,
    )
    b3 = khoi[3]
    ax.annotate(
        f"burn-in {BURN_IN_S} giây đầu mỗi khối: vẫn ghi dữ liệu,\nchỉ bỏ khỏi cửa sổ phân tích",
        xy=(b3.start_offset_s / 60 + 0.45, y0 + 0.05),
        xytext=(30, 0.5),
        fontsize=8,
        color=MUC,
        ha="left",
        va="center",
        linespacing=1.15,
        arrowprops={
            "arrowstyle": "-|>",
            "color": MUC_PHU,
            "lw": 0.7,
            "shrinkA": 2,
            "shrinkB": 1,
            "connectionstyle": "angle3,angleA=180,angleB=-90",
            "mutation_scale": 6,
        },
    )

    chu_giai = [
        Patch(
            facecolor=XANH_DAM,
            hatch="////",
            edgecolor="#5b8fd6",
            lw=0,
            label="BẬT — khối can thiệp (ghim sản phẩm)",
        ),
        Patch(facecolor=XAM_TAT, edgecolor="none", label="TẮT — khối đối chứng"),
        Patch(facecolor=MUC, alpha=0.6, edgecolor="none", label=f"burn-in {BURN_IN_S} s"),
        plt.Line2D(
            [], [], ls="none", marker="D", ms=5, color=DO_CONG, mec="white", label="khoá lịch"
        ),
    ]
    fig.legend(
        handles=chu_giai,
        loc="center left",
        bbox_to_anchor=(0.012, 0.18),
        ncol=4,
        handlelength=1.5,
        handleheight=0.9,
        columnspacing=1.2,
        handletextpad=0.5,
        fontsize=8,
    )

    n_bat, n_tat = lich.n_on, lich.n_off
    chan_nguon(
        fig,
        f"Nguồn: livelift.core.assigner.outer.generate_schedule({PHIEN_PHUT}, DesignParams(), "
        f"seed={SEED_LICH}) — "
        f"chính hàm gán production: {len(khoi)} khối đo, {n_bat} BẬT/{n_tat} TẮT, bốc lại "
        f"{lich.n_redraws} lần; "
        f"khối {tham_so.block_min} phút, lệch biên ±{tham_so.jitter_s} s, p = {so(tham_so.p, 1)}. "
        "burn-in = BURN_IN_S (api/routes/reports.py); design_hash = SHA-256(tham số, seed). "
        f"{LENH}",
    )
    luu(fig, "h1-switchback.png")
    plt.close(fig)
    return {
        "seed": SEED_LICH,
        "design_hash": ma_bam,
        "so_khoi": len(khoi),
        "n_bat": n_bat,
        "n_tat": n_tat,
        "n_boc_lai": lich.n_redraws,
        "khoi_dau_phut": dau.duration_s / 60,
        "khoi_cuoi_phut": cuoi.duration_s / 60,
        "burn_in_s": BURN_IN_S,
        "ranh_gioi_s": [(b.start_offset_s, b.end_offset_s, b.assignment, b.phase) for b in khoi],
    }


# ================================================================== HÌNH 2
TEN_PII = {
    "email": "email",
    "social": "tài khoản mạng xã hội",
    "bank": "số tài khoản ngân hàng",
    "order": "mã đơn",
    "phone": "số điện thoại",
    "address": "địa chỉ",
    "name": "tên người",
}


def html_h2() -> str:
    from livelift.api.routes.reports import BURN_IN_S
    from livelift.ingest.pii.filter import KIND_PRIORITY
    from livelift.nlp.intent import INTENT_MODEL_ENV

    ten_pii = [TEN_PII.get(k, k) for k in sorted(KIND_PRIORITY, key=KIND_PRIORITY.get)]
    tp = DesignParams()
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Kiến trúc LiveLift</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #fff; }}
  #hinh {{ position: relative; width: 15.98cm; font-family: Arial, sans-serif; font-size: 8pt;
          line-height: 1.16; color: {MUC}; background: #fff; padding: 0 0 0.1cm 0; }}
  .lan {{ border-radius: 3px; padding: 0.1cm 0.15cm 0.18cm 0.15cm; }}
  .lan + .lan {{ margin-top: 0.4cm; }}
  .lan-nhan {{ font-size: 8pt; font-weight: bold; color: {MUC_PHU}; height: 0.42cm; }}
  .hang {{ display: flex; gap: 0.35cm; align-items: stretch; }}
  .luoi {{ display: grid; grid-template-columns: 3.2cm 3.35cm 2.4cm 2.6cm 2.73cm;
           column-gap: 0.35cm; }}
  .cot {{ display: flex; flex-direction: column; gap: 0.28cm; }}
  .hop {{ background: #fff; border: 0.9px solid {MUC_MO}; border-radius: 3px;
          padding: 0.08cm 0.12cm 0.1cm; }}
  .hop b {{ display: block; font-size: 8.5pt; margin-bottom: 0.02cm; }}
  .phu {{ color: {MUC_PHU}; }}
  .quan-sat {{ border-style: dashed; border-width: 1.2px; }}
  .mo-phong {{ border-style: dotted; border-width: 1.5px; }}
  .cong {{ border: 1.8px solid {DO_CONG}; background: #fbeeec; }}
  .the {{ display: inline-block; background: {DO_CONG}; color: #fff; font-weight: bold;
          font-size: 8pt; padding: 0.01cm 0.1cm; border-radius: 2px; margin-bottom: 0.04cm;
          white-space: nowrap; }}
  .kho {{ background: #eef3fa; border-color: {XANH_DAM}; flex: 1; }}
  .ghi-chu {{ color: {MUC_PHU}; padding: 0 0.05cm; }}
  svg {{ position: absolute; left: 0; top: 0; overflow: visible; pointer-events: none; }}
  .nhan-mui {{ position: absolute; font-size: 8pt; color: {MUC_PHU}; padding: 0 0.04cm; }}
  .nguon {{ margin-top: 0.12cm; padding: 0 0.1cm; font-size: 8pt; color: {MUC_PHU}; }}
</style></head><body>
<div id="hinh">
 <div class="lan" style="background:#f0f4fa">
  <div class="lan-nhan">THIẾT KẾ (TRƯỚC GIỜ PHÁT) → PHÁT SÓNG</div>
  <div class="hang">
   <div class="hop" id="thamso" style="flex:0 0 3.2cm"><b>Tham số + seed</b>
     <span class="phu">khối {tp.block_min} phút, khối đầu/cuối ×2,
     lệch biên ±{tp.jitter_s} s, p = {so(tp.p, 1)}</span></div>
   <div class="hop" id="gan" style="flex:0 0 3.35cm"><b>Bộ gán ngẫu nhiên</b>
     lịch khối + <i>design_hash</i> (SHA-256 của tham số, seed)</div>
   <div class="hop cong" id="cong2" style="flex:0 0 4.05cm">
     <span class="the">CỔNG 2 · HTTP 409</span><br>
     Chưa có lịch gán → không cho lên sóng. Đã lên sóng → không bốc lại lịch.</div>
   <div class="hop" id="phat" style="flex:1"><b>Phát sóng</b>
     /desk: vận hành thấy khối, nhánh<br>
     /host: người dẫn bị <b style="display:inline">làm mù</b></div>
  </div>
 </div>
 <div class="lan" style="background:#f6f6f3">
  <div class="lan-nhan">DỮ LIỆU (TRONG VÀ SAU PHIÊN)</div>
  <div class="luoi">
   <div class="cot">
    <div class="hop" id="api"><b>API chính thức</b>YouTube, Facebook, Shopee
      <div class="phu">bộ nối đã viết, chưa chạy với khoá thật</div></div>
    <div class="hop quan-sat" id="vod"><b>VOD đã kết thúc</b>
      yt-dlp; dữ liệu QUAN SÁT, không qua API chính thức</div>
    <div class="hop mo-phong" id="sim"><b>Mô phỏng</b>kịch bản AI soạn; chỉ phiên chạy thử</div>
    <div class="hop" id="link" style="margin-top:auto"><b>Link đo /r/&#123;code&#125;</b>
      lượt nhấp; băm có muối</div>
   </div>
   <div class="cot">
    <div class="hop" id="thu"><b>Bộ thu</b>chạy nền trong API hoặc CLI; nạp lại VOD</div>
    <div class="hop cong" id="cong1"><span class="the">CỔNG 1 · LỌC PII</span><br>
      che {len(ten_pii)} loại PII ({", ".join(ten_pii[:3])}…) TRƯỚC khi ghi đĩa/log;
      API lọc lại lần 2</div>
    <div class="hop" id="nlp"><b>Phân loại ý định</b>sau lọc PII; v1 mặc định, v2 chỉ bật bằng
      {INTENT_MODEL_ENV.replace("_", "_<wbr>")}=v2</div>
   </div>
   <div class="cot">
    <div class="hop kho" id="kho"><b>Kho dữ liệu</b>PostgreSQL (chạy thử: bộ nhớ)
      <div style="margin-top:0.1cm">• bình luận đã lọc + nhãn ý định</div>
      <div style="margin-top:0.06cm">• lượt nhấp: gắn cờ, không xoá</div>
      <div style="margin-top:0.06cm">• bảng gán chỉ ghi thêm, kèm <i>design_hash</i></div></div>
   </div>
   <div class="cot">
    <div class="hop" id="khung"><b>Gắn khối + burn-in</b>
      theo lịch đã khoá; bỏ {BURN_IN_S} s đầu mỗi khối</div>
    <div class="hop" id="ri"><b>Suy luận nhân quả</b>
      kiểm định ngẫu nhiên hoá, bốc lại bằng CHÍNH hàm gán; KTC Fisher</div>
    <div class="ghi-chu">Nhãn ý định chỉ để mô tả (bàn điều khiển, phân bố trong
      /bao-cao), không vào phân tích nhân quả.</div>
   </div>
   <div class="cot">
    <div class="hop cong" id="cong3"><span class="the">CỔNG 3 · KHOÁ</span><br>
      RESULTS_<wbr>FREEZE_<wbr>UNTIL: trước ngày mở khoá, /ket-qua và /bao-cao không trả
      ước lượng, p, KTC phiên thật; sai định dạng vẫn khoá.
      <div class="phu">Để trống = tắt (mặc định). Còn lọt: GET
      /sessions/&#123;id&#125;/<wbr>report vẫn trả chênh lệch trung bình.</div></div>
    <div class="hop" id="kq"><b>Kết quả</b>/ket-qua, /bao-cao</div>
   </div>
  </div>
 </div>
 <div class="nguon">Nguồn: đọc từ mã src/livelift — api/routes/sessions.py (409) ·
  ingest/base.py, api/ingest_jobs.py, api/routes/events.py (lọc PII) · api/routes/reports.py
  (khoá kết quả, burn-in) · core/assigner/outer.py · api/routes/redirect.py. Vẽ bằng {LENH}</div>
 <div class="nhan-mui" id="nhan-lich">lưu lịch + <i>design_hash</i></div>
 <svg id="mui"></svg>
</div>
<script>
const MUC = "{MUC_PHU}";
const khung = document.getElementById("hinh");
const svg = document.getElementById("mui");
const goc = khung.getBoundingClientRect();
svg.setAttribute("width", goc.width); svg.setAttribute("height", goc.height);
svg.innerHTML = `<defs><marker id="dau" viewBox="0 0 10 10" refX="9" refY="5"
  markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse">
  <path d="M0,0 L10,5 L0,10 z" fill="${{MUC}}"/></marker></defs>`;
const loi = [];
function hop(id) {{
  const r = document.getElementById(id).getBoundingClientRect();
  return {{l: r.left - goc.left, r: r.right - goc.left, t: r.top - goc.top,
          b: r.bottom - goc.top, cx: (r.left + r.right) / 2 - goc.left,
          cy: (r.top + r.bottom) / 2 - goc.top}};
}}
function net(d) {{
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", d); p.setAttribute("fill", "none"); p.setAttribute("stroke", MUC);
  p.setAttribute("stroke-width", "1"); p.setAttribute("marker-end", "url(#dau)");
  svg.appendChild(p);
}}
// ngang: cạnh phải A → cạnh trái B; gấp khúc giữa khe nếu lệch độ cao.
// Điểm đầu/cuối nằm ngoài cạnh hộp thì ghi lỗi — Python sẽ DỪNG, không chụp hình sai.
function ngang(a, b, ya, yb) {{
  const A = hop(a), B = hop(b);
  const y1 = ya ?? A.cy, y2 = yb ?? B.cy; const xm = (A.r + B.l) / 2;
  if (y1 < A.t || y1 > A.b || y2 < B.t || y2 > B.b) loi.push(a + "->" + b);
  if (Math.abs(y1 - y2) < 0.5) net(`M${{A.r}},${{y1}} L${{B.l - 1}},${{y2}}`);
  else net(`M${{A.r}},${{y1}} L${{xm}},${{y1}} L${{xm}},${{y2}} L${{B.l - 1}},${{y2}}`);
}}
function doc(a, b) {{
  const A = hop(a), B = hop(b);
  net(`M${{A.cx}},${{A.b}} L${{A.cx}},${{B.t - 1}}`);
}}
ngang("thamso", "gan"); ngang("gan", "cong2"); ngang("cong2", "phat");
const T = hop("thu");
ngang("api", "thu", null, T.t + 10);
ngang("vod", "thu", null, T.cy);
ngang("sim", "thu", null, T.b - 8);
doc("thu", "cong1"); doc("cong1", "nlp");
const K = hop("kho"), N = hop("nlp"), L = hop("link");
if (L.cy < N.b + 3) loi.push("link-duoi-nlp");
ngang("nlp", "kho", N.cy, N.cy);
ngang("link", "kho", L.cy, L.cy);
// lịch + design_hash: từ đáy bộ gán, qua khe giữa hai làn, xuống đỉnh kho
(() => {{
  const G = hop("gan"); const yk = G.b + 0.26 * 37.8; const x0 = G.r - 10;
  net(`M${{x0}},${{G.b}} L${{x0}},${{yk}} L${{K.cx}},${{yk}} L${{K.cx}},${{K.t - 1}}`);
  const nh = document.getElementById("nhan-lich"); nh.style.left = (K.cx + 4) + "px";
  nh.style.top = (K.t - nh.getBoundingClientRect().height - 2) + "px";
}})();
const KH = hop("khung"), R = hop("ri"), C3 = hop("cong3");
ngang("kho", "khung", KH.cy, KH.cy); doc("khung", "ri");
ngang("ri", "cong3", Math.min(R.cy, C3.b - 8), Math.min(R.cy, C3.b - 8));
doc("cong3", "kq");
document.body.dataset.loi = loi.join(",");
</script>
</body></html>
"""


def ve_h2() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        sys.exit(
            "Thiếu Playwright — hình 2 cần `pip install playwright` và `playwright install "
            "chromium`."
        )
    # Kiểm Pillow TRƯỚC khi chụp: `--chi h2` không nạp matplotlib, mà .venv không có
    # Pillow — thiếu thì _dat_dpi chết SAU khi PNG đã bị ghi đè, để lại hình không
    # mang 300 dpi (Word sẽ chèn sai khổ khi không ép bề rộng).
    try:
        import PIL  # noqa: F401
    except ModuleNotFoundError:
        sys.exit(
            "Thiếu Pillow — hình 2 cần nó để ghi 300 dpi và kiểm khổ; cài matplotlib (kéo "
            "theo Pillow) hoặc `pip install pillow`."
        )
    RA.mkdir(parents=True, exist_ok=True)
    tep_html = RA / "h2-kien-truc.html"
    tep_html.write_text(html_h2(), encoding="utf-8")
    tep_png = RA / "h2-kien-truc.png"
    with sync_playwright() as pw:
        trinh_duyet = pw.chromium.launch()
        # 1 inch CSS = 96 px; 300 dpi ⇒ hệ số 300/96.
        trang = trinh_duyet.new_context(
            viewport={"width": 620, "height": 640}, device_scale_factor=DPI / 96
        ).new_page()
        trang.goto(tep_html.as_uri())
        trang.wait_for_timeout(300)
        loi = trang.evaluate("document.body.dataset.loi || ''")
        if loi:
            sys.exit(f"DỪNG: mũi tên hình 2 không nối đúng cạnh hộp ({loi}) — sửa bố cục HTML.")
        trang.locator("#hinh").screenshot(path=str(tep_png))
        trinh_duyet.close()
    _dat_dpi(tep_png)
    rong, cao = _kiem_kho(tep_png)
    print(
        f"  đã ghi {tep_png.relative_to(GOC)} ({so(rong, 2)} × {so(cao, 1)} cm; nguồn HTML: "
        f"{tep_html.relative_to(GOC)})"
    )


def _dat_dpi(duong: Path) -> None:
    """Ghi 300 dpi vào PNG để Word chèn đúng 16 cm khi không ép bề rộng."""
    from PIL import Image

    with Image.open(duong) as anh:
        anh.load()
        anh.save(duong, dpi=(DPI, DPI))


def _kiem_kho(duong: Path) -> tuple[float, float]:
    """Khổ in (cm) ở 300 dpi; rộng quá 16 cm là DỪNG — hình sẽ tràn lề hồ sơ."""
    from PIL import Image

    with Image.open(duong) as anh:
        rong_px, cao_px = anh.size
    rong, cao = rong_px / DPI * 2.54, cao_px / DPI * 2.54
    if rong > RONG_CM + 1e-9:
        sys.exit(f"DỪNG: {duong.name} rộng {rong:.3f} cm > {RONG_CM} cm ở {DPI} dpi.")
    return rong, cao


# ================================================================== HÌNH 3
def ve_h3(plt, du_lieu: dict, dem: dict) -> dict:
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    kq = du_lieu["ket_qua"]
    p = np.array(kq["aa"]["p_values"])
    n = len(p)
    tham_aa = kq["aa"]["tham_so"]
    tham_th = kq["thu_hoi"]["tham_so"]
    tac_dong = so(tham_th["treatment_effect"], 1)

    fig = plt.figure(figsize=(RONG_CM * CM, 8.6 * CM))

    # (a) histogram p-value
    ax = fig.add_axes((0.075, 0.34, 0.41, 0.57))
    so_ngan = 20
    canh = np.linspace(0, 1, so_ngan + 1)
    dem_ngan, _ = np.histogram(p, bins=canh)
    ky_vong = n / so_ngan
    lo = binom.ppf(0.025, n, 1 / so_ngan)
    hi = binom.ppf(0.975, n, 1 / so_ngan)
    ax.axhspan(lo, hi, color=XAM_NEN, zorder=0, lw=0)
    ax.axhline(ky_vong, color=MUC_PHU, lw=0.8, ls=(0, (3, 2)), zorder=1)
    rong = 1 / so_ngan
    for i, c in enumerate(dem_ngan):
        dau = i == 0
        ax.bar(
            canh[i] + rong / 2,
            c,
            width=rong * 0.86,
            color=CAM if dau else XANH_NHAT,
            edgecolor="none",
            hatch="////" if dau else None,
            hatchcolor="white" if dau else None,
            zorder=2,
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 25)
    ax.set_yticks([0, 5, 10, 15, 20])
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels([so(v, 2) for v in (0, 0.25, 0.5, 0.75, 1)])
    ax.set_xlabel("p-value của từng lần lặp", labelpad=2)
    ax.set_ylabel("Số lần lặp trong ngăn rộng 0,05", labelpad=2)
    ax.set_title(f"(a) Phân phối p-value, {n} lần lặp A/A", pad=4)
    truc_toi_gian(ax)
    ax.legend(
        handles=[
            Patch(
                facecolor=CAM,
                hatch="////",
                edgecolor="white",
                lw=0,
                label=f"p < 0,05: {dem['aa']['bac_bo']} lần (bác bỏ)",
            ),
            Line2D(
                [],
                [],
                color=MUC_PHU,
                lw=0.8,
                ls=(0, (3, 2)),
                label=f"kỳ vọng nếu p đều: {so(ky_vong, 0)}/ngăn",
            ),
            Patch(facecolor=XAM_NEN, edgecolor="none", label="dải dao động ngẫu nhiên 95%"),
        ],
        loc="upper left",
        bbox_to_anchor=(0.0, 1.0),
        ncol=1,
        fontsize=8,
        handlelength=1.6,
        borderaxespad=0.2,
        labelspacing=0.3,
    )

    # (b) tỷ lệ bác bỏ
    k_bb, n_bb = dem["aa"]["bac_bo"], dem["aa"]["n"]
    lo_bb, hi_bb = ktc_nhi_thuc(k_bb, n_bb)
    p_bb = binomtest(k_bb, n_bb, 0.05).pvalue
    x0 = 0.585
    fig.text(
        x0, 0.955, "(b) Tỷ lệ bác bỏ khi KHÔNG có tác động", fontsize=9, fontweight="bold", va="top"
    )
    fig.text(
        x0,
        0.895,
        f"{phan_tram(k_bb / n_bb)} ({k_bb}/{n_bb}), KTC 95% [{phan_tram(lo_bb)}; "
        f"{phan_tram(hi_bb)}]\np nhị thức so với 5% = {so(p_bb, 4)}",
        fontsize=8,
        color=MUC,
        va="top",
        linespacing=1.2,
    )
    axb = fig.add_axes((x0, 0.665, 0.39, 0.1))
    axb.axvline(5, color=MUC_PHU, lw=0.8, ls=(0, (3, 2)))
    axb.errorbar(
        [100 * k_bb / n_bb],
        [0],
        xerr=[[100 * (k_bb / n_bb - lo_bb)], [100 * (hi_bb - k_bb / n_bb)]],
        fmt="o",
        color=XANH_DAM,
        ms=5,
        capsize=2.5,
        lw=1.2,
        mec="white",
        mew=0.8,
    )
    axb.text(5.25, 0.45, "α = 5%", fontsize=8, color=MUC_PHU, va="bottom", ha="left")
    axb.set_xlim(0, 12)
    axb.set_ylim(-0.5, 1.1)
    axb.set_yticks([])
    axb.set_xticks([0, 2, 4, 6, 8, 10, 12])
    axb.set_xticklabels([f"{v}%" for v in (0, 2, 4, 6, 8, 10, 12)])
    for c in ("top", "right", "left"):
        axb.spines[c].set_visible(False)
    axb.tick_params(length=2.5)

    # (c) độ phủ
    k_aa, k_th, n_th = dem["aa"]["phu"], dem["thu_hoi"]["phu"], dem["thu_hoi"]["n"]
    lo_a, hi_a = ktc_nhi_thuc(k_aa, n_bb)
    lo_t, hi_t = ktc_nhi_thuc(k_th, n_th)
    hang = [
        (f"A/A, n = {n_bb}: {phan_tram(k_aa / n_bb)} ({k_aa}/{n_bb})", k_aa, n_bb, lo_a, hi_a),
        (
            f"Tác động {tac_dong}, n = {n_th}: {phan_tram(k_th / n_th)} ({k_th}/{n_th})",
            k_th,
            n_th,
            lo_t,
            hi_t,
        ),
    ]
    fig.text(
        x0, 0.535, "(c) Độ phủ của KTC 95% (phải ≈ 95%)", fontsize=9, fontweight="bold", va="top"
    )
    axc = fig.add_axes((x0, 0.34, 0.39, 0.145))
    axc.axvline(95, color=MUC_PHU, lw=0.8, ls=(0, (3, 2)))
    for i, (nhan, k, nn, lo_, hi_) in enumerate(hang):
        y = 1 - i
        axc.errorbar(
            [100 * k / nn],
            [y],
            xerr=[[100 * (k / nn - lo_)], [100 * (hi_ - k / nn)]],
            fmt="o",
            color=XANH_DAM,
            ms=5,
            capsize=2.5,
            lw=1.2,
            mec="white",
            mew=0.8,
        )
        axc.text(75.2, y + 0.22, nhan, fontsize=8, color=MUC, va="bottom", ha="left")
    axc.text(95.3, 1.75, "95%", fontsize=8, color=MUC_PHU, va="top", ha="left")
    axc.set_ylim(-0.6, 1.75)
    axc.set_xlim(75, 100)
    axc.set_yticks([])
    axc.set_xticks([75, 80, 85, 90, 95, 100])
    axc.set_xticklabels([f"{v}%" for v in (75, 80, 85, 90, 95, 100)])
    for c in ("top", "right", "left"):
        axc.spines[c].set_visible(False)
    axc.tick_params(axis="x", length=2.5)

    chan_nguon(
        fig,
        "Nguồn: mô phỏng Monte-Carlo (KHÔNG phải phiên thật), livelift.sim.validate.run_validation "
        "với đúng NGHIEN_CUU của scripts/do_lai_so_hieu_chuan.py — A/A: "
        f"{tham_aa['n_reps']} lần × {tham_aa['n_sessions_per_rep']} phiên × "
        f"{tham_aa['session_minutes']} phút, seed {tham_aa['master_seed']}; tác động {tac_dong}: "
        f"{tham_th['n_reps']} × {tham_th['n_sessions_per_rep']} × {tham_th['session_minutes']} "
        "phút, "
        f"seed {tham_th['master_seed']}, độ lệch ước lượng "
        f"{phan_tram(kq['thu_hoi']['do_lech_tuong_doi'])}. Số tổng khớp "
        "docs/benchmarks/so-hieu-chuan.json. KTC Clopper–Pearson. "
        f"Đo {du_lieu['ngay_do']} ({du_lieu['ban_git']}).",
    )
    luu(fig, "h3-hieu-chuan-aa.png")
    plt.close(fig)
    return {
        "ty_le_bac_bo": k_bb / n_bb,
        "ktc_bac_bo": (lo_bb, hi_bb),
        "p_nhi_thuc_bac_bo": p_bb,
        "phu_aa": (k_aa, n_bb, lo_a, hi_a),
        "phu_thu_hoi": (k_th, n_th, lo_t, hi_t),
        "do_lech_thu_hoi": kq["thu_hoi"]["do_lech_tuong_doi"],
        "dem_ngan": dem_ngan.tolist(),
        "dai_ngau_nhien": (float(lo), float(hi)),
    }


# ================================================================== HÌNH 4
def diem_mo_phong_mde() -> dict:
    """CV trong phiên + khán giả trung bình trên phiên mô phỏng hiệu chuẩn (tác động 0).

    Đúng bước 1 của tests/test_power.py::test_predicted_mde_matches_achieved_power.
    """
    ys, sids, khan_gia = [], [], []
    for s in range(MDE_SO_PHIEN_MO_PHONG):
        lich = generate_schedule(PHIEN_PHUT, DesignParams(), MDE_SEED_GOC + s)
        out = simulate_session(lich, SimParams(treatment_effect=0.0), MDE_SEED_GOC + s)
        khan_gia.append(float(np.mean(out.viewers_trace)))
        for r in blocks_to_dicts(block_frame(lich, out.events, burn_in_s=60)):
            if r["measurable"]:
                ys.append(r["y"])
                sids.append(f"s{s}")
    cv = within_session_cv(np.array(ys), np.array(sids))
    n_khoi = len(ys)
    mde = mde_relative(PowerInputs(cv=cv, n_blocks_total=n_khoi, n_sessions=MDE_SO_PHIEN_MO_PHONG))
    return {
        "cv_trong_phien": cv,
        "n_khoi": n_khoi,
        "mde": mde,
        "khan_gia_tb": float(np.mean(khan_gia)),
        "khan_gia_min": float(np.min(khan_gia)),
        "khan_gia_max": float(np.max(khan_gia)),
    }


def mde_san_poisson(ty_le_nhap: float, khan_gia: float, n_phien: int, burn_in_s: int) -> float:
    """MDE tương đối (sàn Poisson) của biến kết quả CHÍNH — lượt nhấp / 1000 giây·người xem.

    Cùng cơ chế với ``order_mde_table`` nhưng không nhân phễu đơn hàng:
    λ_k = tỷ lệ nhấp/1000 × khán giả × cửa sổ phân tích của khối k.
    ``burn_in_s`` là ``BURN_IN_S`` của đường phân tích production.
    """
    cua_so = analysis_window_seconds(PHIEN_PHUT, KHOI_PHUT, True, burn_in_s)
    lams = [ty_le_nhap / 1000.0 * khan_gia * w for w in cua_so]
    return mde_relative(
        PowerInputs(cv=poisson_cv(lams), n_blocks_total=len(cua_so) * n_phien, n_sessions=n_phien)
    )


def ve_h4(plt) -> dict:
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter

    ty_le_mo_phong = (
        SimParams().base_click_prob_per_min / 60.0 * 1000.0
    )  # = 1,00 / 1000 giây·người xem
    # Mốc kịch bản của bảng MDE đơn hàng (analysis/power/bang_mde_don_hang.py).
    spec = importlib.util.spec_from_file_location(
        "bang_mde_don_hang", GOC / "analysis" / "power" / "bang_mde_don_hang.py"
    )
    bang = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(bang)
    ty_le_moc = bang.CLICK_RATE_ANCHOR
    luoi_phien = (MDE_SO_PHIEN_MO_PHONG, *bang.SESSIONS_GRID)

    from livelift.api.routes.reports import BURN_IN_S

    # α, lực, tuân thủ, biên kiểm định ngẫu nhiên hoá: giá trị mặc định mà
    # mde_relative thực sự dùng — chân hình đọc từ đây, không gõ tay.
    mac_dinh = PowerInputs(cv=1.0, n_blocks_total=4, n_sessions=1)
    mp = diem_mo_phong_mde()
    khan_gia = np.geomspace(3, 600, 200)
    n_khoi_phien = len(analysis_window_seconds(PHIEN_PHUT, KHOI_PHUT, True, BURN_IN_S))

    fig = plt.figure(figsize=(RONG_CM * CM, 8.4 * CM))
    truc = [fig.add_axes((0.085, 0.335, 0.40, 0.475)), fig.add_axes((0.585, 0.335, 0.40, 0.475))]
    kieu = {
        luoi_phien[0]: (XANH_VUA, (0, (1.2, 1.2))),
        luoi_phien[1]: (XANH_DAM, (0, (4, 1.5))),
        luoi_phien[2]: (XANH_TOI, "-"),
    }
    ket_qua: dict = {
        "mo_phong": mp,
        "ty_le_mo_phong": ty_le_mo_phong,
        "ty_le_moc": ty_le_moc,
        "luoi": {},
    }
    for i, (ax, r, tieu_de) in enumerate(
        (
            (
                truc[0],
                ty_le_mo_phong,
                f"(a) Tỷ lệ nhấp {so(ty_le_mo_phong)}/1.000 giây·người xem\n"
                "      (giả định: tham số của bộ mô phỏng)",
            ),
            (
                truc[1],
                ty_le_moc,
                f"(b) Tỷ lệ nhấp {so(ty_le_moc)}/1.000 giây·người xem\n"
                "      (giả định: mốc bảng MDE đơn hàng)",
            ),
        )
    ):
        ax.axvspan(5, 15, color=CAM, alpha=0.14, lw=0, zorder=0)
        ax.axvspan(
            5, 15, facecolor="none", edgecolor=CAM, alpha=0.4, hatch="\\\\\\\\", lw=0, zorder=0
        )
        for n_phien in luoi_phien:
            mau, net = kieu[n_phien]
            y = [100 * mde_san_poisson(r, a, n_phien, BURN_IN_S) for a in khan_gia]
            ax.plot(khan_gia, y, color=mau, ls=net, lw=1.5, zorder=3)
            ket_qua["luoi"][f"{so(r)}|{n_phien}"] = {
                "5": mde_san_poisson(r, 5, n_phien, BURN_IN_S),
                "10": mde_san_poisson(r, 10, n_phien, BURN_IN_S),
                "15": mde_san_poisson(r, 15, n_phien, BURN_IN_S),
                "50": mde_san_poisson(r, 50, n_phien, BURN_IN_S),
                "khan_gia_mo_phong": mde_san_poisson(r, mp["khan_gia_tb"], n_phien, BURN_IN_S),
            }
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(3, 600)
        ax.set_ylim(4, 400)
        ax.xaxis.set_major_locator(FixedLocator([3, 5, 10, 15, 30, 50, 100, 200, 500]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: so(v, 0)))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(FixedLocator([5, 10, 20, 50, 100, 200]))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{so(v, 0)}%"))
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.grid(True, which="major", color=LUOI, lw=0.5, zorder=0)
        ax.set_axisbelow(True)
        truc_toi_gian(ax)
        ax.set_xlabel("Người xem đồng thời (thang log)", labelpad=2)
        if i == 0:
            ax.set_ylabel(
                f"MDE tương đối, lực {phan_tram(mac_dinh.power, 0)} (thang log)", labelpad=2
            )
        ax.set_title(tieu_de, fontsize=8.5, pad=4, linespacing=1.2)
        ax.text(
            5.4,
            340,
            "5–15 người xem:\nƯỚC TÍNH từ CPM,\nchưa đo",
            fontsize=8,
            color="#8a3a12",
            va="top",
            ha="left",
            linespacing=1.12,
            zorder=6,
            bbox={
                "boxstyle": "square,pad=0.15",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.9,
            },
        )
    # điểm mô phỏng chỉ thuộc panel (a): cùng tỷ lệ nhấp với bộ mô phỏng
    ax = truc[0]
    ax.errorbar(
        [mp["khan_gia_tb"]],
        [100 * mp["mde"]],
        xerr=[[mp["khan_gia_tb"] - mp["khan_gia_min"]], [mp["khan_gia_max"] - mp["khan_gia_tb"]]],
        fmt="D",
        color=MUC,
        ms=4.5,
        mec="white",
        mew=0.7,
        lw=1,
        capsize=2,
        zorder=5,
    )
    ax.annotate(
        f"mô phỏng {MDE_SO_PHIEN_MO_PHONG} phiên: {phan_tram(mp['mde'], 1)}\nở "
        f"~{so(mp['khan_gia_tb'], 0)} người xem",
        xy=(mp["khan_gia_tb"], 100 * mp["mde"]),
        xytext=(46, 62),
        fontsize=8,
        color=MUC,
        ha="left",
        va="bottom",
        linespacing=1.15,
        arrowprops={
            "arrowstyle": "-|>",
            "color": MUC_PHU,
            "lw": 0.7,
            "mutation_scale": 6,
            "shrinkB": 3,
        },
    )
    fig.legend(
        handles=[
            Line2D(
                [],
                [],
                color=kieu[n][0],
                ls=kieu[n][1],
                lw=1.5,
                label=f"{n} phiên × {PHIEN_PHUT} phút",
            )
            for n in luoi_phien
        ]
        + [
            Line2D(
                [],
                [],
                ls="none",
                marker="D",
                ms=4.5,
                color=MUC,
                mec="white",
                label="CV đo trên mô phỏng",
            )
        ],
        loc="upper left",
        bbox_to_anchor=(0.075, 1.0),
        ncol=4,
        fontsize=8,
        handlelength=2.4,
        columnspacing=1.5,
        handletextpad=0.5,
    )

    chan_nguon(
        fig,
        "Nguồn: livelift.analysis.power — sàn Poisson (CẬN DƯỚI) cho lượt nhấp hợp lệ/1.000 "
        "giây·người xem: "
        f"λ_k = tỷ lệ nhấp × khán giả × cửa sổ khối (analysis_window_seconds, {n_khoi_phien} "
        f"khối/phiên, burn-in {BURN_IN_S} s) "
        f"→ poisson_cv → mde_relative (α {phan_tram(mac_dinh.alpha, 0)}, lực "
        f"{phan_tram(mac_dinh.power, 0)}, tuân thủ {so(mac_dinh.compliance)}, "
        f"×{so(mac_dinh.randomization_margin, 1)} cho kiểm định "
        f"ngẫu nhiên hoá). Hình thoi: CV trong phiên đo trên {MDE_SO_PHIEN_MO_PHONG} phiên mô "
        "phỏng (seed "
        f"{MDE_SEED_GOC}–{MDE_SEED_GOC + MDE_SO_PHIEN_MO_PHONG - 1}), thanh ngang = khán giả "
        "min–max. "
        "5–15 người: docs/research/2026-08-24-phan-bien-tai-lieu.md (R1).",
    )
    luu(fig, "h4-mde.png")
    plt.close(fig)
    return ket_qua


# ================================================================== HÌNH 5
def ve_h5(plt, du_lieu: dict) -> dict:
    kq = du_lieu["ket_qua"]
    cong = kq["tham_so_cong"]
    seeds = kq["seeds"]
    muc = list(kq["ban_ra"].keys())
    fig = plt.figure(figsize=(RONG_CM * CM, 8.4 * CM))
    ax_phu = fig.add_axes((0.085, 0.355, 0.40, 0.49))
    ax_lech = fig.add_axes((0.585, 0.355, 0.39, 0.49))
    nen_trang = {"boxstyle": "square,pad=0.08", "facecolor": "white", "edgecolor": "none"}
    x = np.arange(len(muc))
    tong: dict = {}
    for j, m in enumerate(muc):
        theo_seed = kq["ban_ra"][m]
        co_phu = [c for s in seeds for c in theo_seed[str(s)]["co_phu"]]
        uoc = [e for s in seeds for e in theo_seed[str(s)]["uoc_luong"]]
        that = [t for s in seeds for t in theo_seed[str(s)]["gia_tri_that"]]
        k, n = int(sum(co_phu)), len(co_phu)
        lo, hi = ktc_nhi_thuc(k, n)
        lech = (np.mean(uoc) - np.mean(that)) / abs(np.mean(that))
        tong[m] = {
            "phu": (k, n, lo, hi),
            "lech_tuong_doi": float(lech),
            "theo_seed": {
                str(s): (theo_seed[str(s)]["do_phu_ktc"], theo_seed[str(s)]["do_lech_tuong_doi"])
                for s in seeds
            },
        }
        # điểm từng seed (rỗng), lệch ngang nhẹ để không đè nhau
        for d, s in zip((-0.16, 0.0, 0.16), seeds, strict=True):
            ax_phu.plot(
                j + d - 0.0,
                100 * theo_seed[str(s)]["do_phu_ktc"],
                "o",
                ms=4,
                mfc="white",
                mec=MUC_MO,
                mew=0.9,
                zorder=3,
            )
            ax_lech.plot(
                j + d,
                100 * theo_seed[str(s)]["do_lech_tuong_doi"],
                "o",
                ms=4,
                mfc="white",
                mec=MUC_MO,
                mew=0.9,
                zorder=3,
            )
        ax_phu.errorbar(
            [j + 0.34],
            [100 * k / n],
            yerr=[[100 * (k / n - lo)], [100 * (hi - k / n)]],
            fmt="o",
            color=XANH_DAM,
            ms=5.5,
            capsize=2.5,
            lw=1.3,
            mec="white",
            mew=0.8,
            zorder=4,
        )
        ax_phu.text(
            j + 0.44,
            100 * k / n,
            f"{phan_tram(k / n, 0)}\n({k}/{n})",
            fontsize=8,
            va="center",
            ha="left",
            color=MUC,
            linespacing=1.1,
            bbox=nen_trang,
            zorder=5,
        )
        ax_lech.plot(
            [j + 0.34], [100 * lech], "o", color=XANH_DAM, ms=5.5, mec="white", mew=0.8, zorder=4
        )
        ax_lech.text(
            j + 0.44,
            100 * lech,
            phan_tram(lech, 1),
            fontsize=8,
            va="center",
            ha="left",
            color=MUC,
            bbox=nen_trang,
            zorder=5,
        )

    nhan_x = [("0 s\n(không lưu)" if m == "0" else f"{m} s") for m in muc]
    ax_phu.axhline(95, color=MUC_PHU, lw=0.8, ls=(0, (3, 2)))
    ax_phu.text(
        len(muc) - 0.15, 95.8, "95% danh nghĩa", fontsize=8, color=MUC_PHU, va="bottom", ha="right"
    )
    # Cổng chỉ đòi ngưỡng này ở MỘT điểm: bán rã của cổng, seed của cổng. Vẽ ngang
    # cả trục mà không nói vậy thì 180 s (không có cổng) trông như "trượt cổng".
    nguong = 100 * nguong_phu_cong_hieu_ung_luu()
    ax_phu.axhline(nguong, color=DO_CONG, lw=0.8, ls=(0, (1, 1.5)))
    ax_phu.text(
        -0.45,
        nguong - 1.0,
        f"ngưỡng cổng test: ≥ {so(nguong, 0)}%\n(chỉ đòi ở "
        f"{cong['carryover_halflife_s']:.0f} s, seed {cong['master_seed']})",
        fontsize=8,
        color=DO_CONG,
        va="top",
        linespacing=1.1,
    )
    ax_phu.set_ylim(30, 105)
    ax_phu.set_yticks([30, 40, 50, 60, 70, 80, 90, 100])
    ax_phu.set_yticklabels([f"{v}%" for v in (30, 40, 50, 60, 70, 80, 90, 100)])
    ax_phu.set_title("(a) Độ phủ của KTC 95%", pad=4)
    ax_lech.axhline(0, color=MUC_PHU, lw=0.8, ls=(0, (3, 2)))
    ax_lech.text(
        len(muc) - 0.15, 1.0, "không lệch", fontsize=8, color=MUC_PHU, va="bottom", ha="right"
    )
    ax_lech.set_ylim(-45, 8)
    ax_lech.set_yticks([-40, -30, -20, -10, 0])
    ax_lech.set_yticklabels([f"{so(v, 0)}%" for v in (-40, -30, -20, -10, 0)])
    ax_lech.set_title("(b) Độ lệch tương đối của ước lượng", pad=4)
    for ax in (ax_phu, ax_lech):
        ax.set_xticks(x)
        ax.set_xticklabels(nhan_x)
        ax.set_xlim(-0.5, len(muc) - 0.1)
        ax.set_xlabel("Bán rã hiệu ứng lưu sang khối sau", labelpad=2)
        ax.grid(True, axis="y", color=LUOI, lw=0.5)
        ax.set_axisbelow(True)
        truc_toi_gian(ax)

    from matplotlib.lines import Line2D

    fig.legend(
        handles=[
            Line2D(
                [],
                [],
                ls="none",
                marker="o",
                ms=4,
                mfc="white",
                mec=MUC_MO,
                mew=0.9,
                label=f"từng seed ({', '.join(str(s) for s in seeds)}), {cong['n_reps']} lần lặp",
            ),
            Line2D(
                [],
                [],
                ls="-",
                marker="o",
                ms=5.5,
                color=XANH_DAM,
                mec="white",
                label=f"gộp {len(seeds) * cong['n_reps']} lần lặp, KTC 95% Clopper–Pearson",
            ),
        ],
        loc="upper left",
        bbox_to_anchor=(0.075, 1.0),
        ncol=2,
        fontsize=8,
        handletextpad=0.4,
        columnspacing=1.6,
    )
    chan_nguon(
        fig,
        "Nguồn: mô phỏng Monte-Carlo (KHÔNG phải phiên thật), "
        "livelift.sim.validate.run_validation với tham số đọc "
        "thẳng từ tests/test_sim_validation.py::test_estimator_under_carryover_interference — "
        f"{cong['n_reps']} lần lặp × {cong['n_sessions_per_rep']} phiên × "
        f"{cong['session_minutes']} phút, "
        f"tác động {so(cong['treatment_effect'], 1)}, {cong['n_draws']} lần bốc lại; seed "
        f"{seeds[0]} (của cổng) "
        f"và {', '.join(str(s) for s in seeds[1:])}. Đo {du_lieu['ngay_do']} "
        f"({du_lieu['ban_git']}).",
    )
    luu(fig, "h5-luu-hieu-ung.png")
    plt.close(fig)
    return tong


# ================================================================== HÌNH 6
# Hình 6 KHÔNG chạy mô hình: nó đọc số do bộ đánh giá ý định đã ghi. Chạy lại
# bộ đánh giá (LENH_NLP) → chi-tiet-hinh.json đổi → chạy lại `--chi h6`.
CHI_TIET_NLP = GOC / "docs" / "benchmarks" / "intent-eval" / "chi-tiet-hinh.json"
LENH_NLP = "python -m livelift.nlp.eval_intent --ablation --coverage"

# Panel (b): (mã, nhãn ngắn trên hình, chuỗi PHẢI có trong trường "ten" của mã đó).
# Chuỗi kiểm giữ nhãn ngắn khỏi trôi nghĩa: nếu eval_intent đổi định nghĩa một mã
# (ví dụ B2 không còn là artifact đang chạy) thì script DỪNG, không vẽ nhãn sai.
H6_HE_THONG = (
    ("B0", "đoán lớp đa số", "lớp đa số"),
    ("B1", "từ khóa", "từ khoá"),  # hình theo chính tả hồ sơ; JSON viết "khoá"
    ("B2", "v1 đang chạy", "ĐANG CHẠY"),
    ("B3", "học lại trên câu mẫu", "câu biên soạn"),
    ("C1", "11 lớp + nhãn 2 buổi", "gold 2 buổi"),
    ("C2", "v2: C1 + nhãn LLM", "nhãn LLM"),
    ("C3", "C2 + từ chối trả lời", "từ chối trả lời"),
    ("A4", "C2 bỏ bộ câu mẫu", "bộ biên soạn"),
)
# Hai cấu hình được đóng gói (v1 mặc định, v2 bật bằng cờ) — in đậm.
H6_DONG_GOI = ("B2", "C2")
# Dòng "đầy đủ" của bảng ablation; nó PHẢI trùng C2 thì mới được ghi "C2 bỏ …".
H6_BAN_DAY_DU = "A0"
H6_THANG = "11_lop"
H6_RONG_CM = RONG_CM
H6_CAO_CM = 8.2
H6_CHU_O = 7.5  # cỡ số trong ô ma trận — nhỏ nhất của hình 6
H6_CHU_TOI_THIEU = 7.5
_H6_SAI_SO_LAM_TRON = 5e-5 + 1e-12  # JSON làm tròn 4 chữ số


def _loi_h6(loi: list[str]) -> None:
    if loi:
        sys.exit(
            f"DỪNG — {CHI_TIET_NLP.relative_to(GOC)} không nói đúng điều hình 6 sẽ nói:\n  - "
            + "\n  - ".join(loi)
        )


def du_lieu_h6(chi_tiet: dict) -> dict:
    """Mọi con số và nhãn của hình 6, lấy từ ``chi-tiet-hinh.json`` — hàm thuần, không vẽ.

    DỪNG (``SystemExit``) thay vì vẽ khi dữ liệu không khớp điều hình sẽ khai: nguồn
    nhãn không còn là tác tử AI, ma trận không thuộc hệ thống được chọn, ma trận
    không cộng ra đúng n hay không tái tạo được accuracy/macro-F1 của chính hệ thống
    đó, một dòng khác thang 11 lớp, hoặc dòng "đầy đủ" của ablation khác C2.
    """
    from livelift.nlp.labels import LABEL_DISPLAY

    loi: list[str] = []
    nguon = chi_tiet["nguon_nhan"]
    if "tác tử AI" not in nguon["test"]:
        loi.append("nguon_nhan.test không còn ghi 'tác tử AI' — chân hình sẽ khai sai nguồn nhãn")
    if "yt-dlp" not in nguon["data"]:
        loi.append("nguon_nhan.data không còn ghi 'yt-dlp' — chân hình sẽ khai sai nguồn dữ liệu")
    _loi_h6(loi)

    theo_ma = {d["ma"]: d for d in chi_tiet["macro_f1"]}
    mt = chi_tiet["ma_tran_nham_lan"]
    ma_mt = mt["he_thong"].split(" · ")[0]
    if ma_mt not in theo_ma or theo_ma[ma_mt]["ten"] != mt["he_thong"]:
        _loi_h6([f"ma trận ghi hệ thống '{mt['he_thong']}' — không có dòng macro_f1 nào trùng tên"])
    # Hình gắn nhãn "v2" cho hệ thống của ma trận: chỉ đúng khi bộ đánh giá ghi rằng
    # đó là cấu hình được đóng gói thành intent_clf_v2.joblib.
    if ma_mt != "C2" or "intent_clf_v2" not in mt.get("quy_tac_chon", ""):
        loi.append(
            f"ma trận là của {ma_mt}, không được ghi là cấu hình đóng gói intent_clf_v2 — "
            "hình sẽ gắn nhãn 'v2' sai"
        )
    he = theo_ma[ma_mt]
    nhan = list(mt["nhan"])
    dem = [list(map(int, hang)) for hang in mt["ma_tran"]]
    k = len(nhan)
    n = he["n_test"]
    if len(dem) != k or any(len(h) != k for h in dem):
        loi.append(f"ma trận không phải {k}×{k}")
    thieu = [x for x in nhan if x not in LABEL_DISPLAY]
    if thieu:
        loi.append(f"nhãn chưa có tên tiếng Việt trong LABEL_DISPLAY: {thieu}")
    _loi_h6(loi)
    tong_hang = [sum(h) for h in dem]
    tong_cot = [sum(dem[r][c] for r in range(k)) for c in range(k)]
    if tong_hang != list(mt["tong_hang"]) or tong_cot != list(mt["tong_cot"]):
        loi.append("tổng hàng/cột tính lại khác tong_hang/tong_cot đã ghi")
    if sum(tong_hang) != n:
        loi.append(f"ma trận cộng ra {sum(tong_hang)} dòng, còn {ma_mt} chấm trên {n}")
    dung = sum(dem[i][i] for i in range(k))
    acc = dung / sum(tong_hang) if sum(tong_hang) else float("nan")
    f1_lop = []
    for i in range(k):
        p = dem[i][i] / tong_cot[i] if tong_cot[i] else 0.0
        r = dem[i][i] / tong_hang[i] if tong_hang[i] else 0.0
        f1_lop.append(2 * p * r / (p + r) if p + r else 0.0)
    macro = sum(f1_lop) / k
    if abs(acc - he["accuracy"]) > _H6_SAI_SO_LAM_TRON:
        loi.append(f"accuracy từ ma trận {acc:.4f} ≠ {he['accuracy']} của {ma_mt}")
    if abs(macro - he["macro_f1"]) > _H6_SAI_SO_LAM_TRON:
        loi.append(f"macro-F1 từ ma trận {macro:.4f} ≠ {he['macro_f1']} của {ma_mt}")
    _loi_h6(loi)

    rung = []
    for ma, nhan_ngan, chu_kiem in H6_HE_THONG:
        d = theo_ma.get(ma)
        if d is None:
            loi.append(f"thiếu dòng {ma}")
            continue
        if chu_kiem not in d["ten"]:
            loi.append(f"{ma} là '{d['ten']}', không còn chứa '{chu_kiem}' — nhãn ngắn sẽ sai")
        if d["thang"] != H6_THANG:
            loi.append(f"{ma} chấm trên thang {d['thang']}, không so được với {H6_THANG}")
        if d["n_test"] != n:
            loi.append(f"{ma} chấm trên {d['n_test']} dòng, không phải {n}")
        lo, hi = d["macro_f1_ktc95_bootstrap"]
        rung.append(
            {
                "ma": ma,
                "nhan": nhan_ngan,
                "nhom": d["bang"].split(" (")[0].split(". ", 1)[-1],
                "macro_f1": d["macro_f1"],
                "ktc": [lo, hi],
            }
        )
    day_du = theo_ma.get(H6_BAN_DAY_DU)
    if day_du is None or (
        day_du["macro_f1"],
        day_du["macro_f1_ktc95_bootstrap"],
    ) != (theo_ma["C2"]["macro_f1"], theo_ma["C2"]["macro_f1_ktc95_bootstrap"]):
        loi.append(
            f"dòng đầy đủ {H6_BAN_DAY_DU} của ablation không trùng C2 — không được ghi 'C2 bỏ …'"
        )
    _loi_h6(loi)

    buoi = chi_tiet["precision_theo_buoi_va_ty_le_nen"]
    if sum(b["n_dong"] for b in buoi) != n:
        _loi_h6([f"số dòng theo buổi cộng ra {sum(b['n_dong'] for b in buoi)} ≠ {n}"])
    y, m, dd = chi_tiet["generated_at"][:10].split("-")
    hanh_dong = list(chi_tiet["nhan_hanh_dong"])
    return {
        "he_thong_ma_tran": ma_mt,
        "nhan": nhan,
        "ten_lop": [LABEL_DISPLAY[x].replace(" / ", "/") for x in nhan],
        "so_lop_hanh_dong_dau": len(hanh_dong) if nhan[: len(hanh_dong)] == hanh_dong else 0,
        "ma_tran": dem,
        "tong_hang": tong_hang,
        "ty_le_hang": [
            [c / tong_hang[i] for c in dem[i]] if tong_hang[i] else None for i in range(k)
        ],
        "accuracy_ma_tran": acc,
        "macro_f1_ma_tran": macro,
        "n": n,
        "so_buoi": len(buoi),
        "n_bootstrap": chi_tiet["n_bootstrap"],
        "ngay_do": f"{dd}/{m}/{y}",
        "rung": rung,
        "ablation": {"tu": "C2", "den": "A4"},
    }


def _o_cm(fig, trai: float, duoi: float, rong: float, cao: float):
    """Trục đặt bằng cm từ góc dưới-trái của hình."""
    w, h = (v / CM for v in fig.get_size_inches())
    return fig.add_axes((trai / w, duoi / h, rong / w, cao / h))


def hinh_h6(plt, s: dict):
    """Dựng hình 6 từ ``du_lieu_h6`` (không lưu). Trả ``fig`` để test đọc chữ trên hình.

    Toạ độ tính bằng cm (khổ in). Bề rộng cột chữ đo bằng renderer ở 8 pt Arial ngày
    25/09: tên lớp dài nhất 1,96 cm, nhãn hệ thống ≤ 2,6 cm, cột số 2,5 cm (chữ đậm).
    """
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import Rectangle

    fig = plt.figure(figsize=(H6_RONG_CM * CM, H6_CAO_CM * CM))
    k = len(s["nhan"])

    def chu_hinh(x_cm: float, y_tu_tren_cm: float, chu: str, **kw) -> None:
        fig.text(x_cm / H6_RONG_CM, 1 - y_tu_tren_cm / H6_CAO_CM, chu, va="top", **kw)

    # ---------------------------------------------------------------- (a) ma trận
    canh_o, trai_mt, day_mt = 4.3, 2.18, 2.75
    ax = _o_cm(fig, trai_mt, day_mt, canh_o, canh_o)
    thang_mau = LinearSegmentedColormap.from_list(
        "h6",
        [(0.0, "#eef4fc"), (0.15, XANH_RAT_NHAT), (0.45, XANH_NHAT), (0.75, XANH), (1.0, XANH_TOI)],
    ).with_extremes(bad="#f3f2ee")  # ô 0 (bị che): xám rất nhạt, khác ô có số
    gia_tri = np.ma.masked_equal(
        np.array([h if h is not None else [0.0] * k for h in s["ty_le_hang"]], dtype=float), 0.0
    )
    ax.pcolormesh(
        np.arange(k + 1),
        np.arange(k + 1),
        gia_tri,
        cmap=thang_mau,
        vmin=0,
        vmax=1,
        edgecolors="white",
        linewidth=0.9,
    )
    ax.set_xlim(0, k)
    ax.set_ylim(k, 0)
    for i, hang in enumerate(s["ty_le_hang"]):
        if hang is None:  # lớp không có dòng tham chiếu nào: tỷ lệ theo hàng không xác định
            ax.add_patch(
                Rectangle(
                    (0.04, i + 0.06),
                    k - 0.08,
                    0.88,
                    facecolor="white",
                    edgecolor=MUC_MO,
                    hatch="////",
                    lw=0,
                    zorder=3,
                )
            )
            ax.text(
                k / 2,
                i + 0.52,
                "không có dòng nào (n = 0)",
                ha="center",
                va="center",
                fontsize=H6_CHU_O,
                color=MUC,
                zorder=6,
                bbox={"boxstyle": "square,pad=0.15", "facecolor": "white", "edgecolor": "none"},
            )
            continue
        for j, v in enumerate(hang):
            if s["ma_tran"][i][j] == 0:
                continue
            phan = round(100 * v)
            ax.text(
                j + 0.5,
                i + 0.54,
                "<1" if phan == 0 else str(phan),
                ha="center",
                va="center",
                fontsize=H6_CHU_O,
                color="white" if v >= 0.6 else MUC,
                fontweight="bold" if i == j else "normal",
            )
    h = s["so_lop_hanh_dong_dau"]
    if 0 < h < k:  # kẻ tách nhóm ý định hành động khỏi các lớp còn lại
        ax.plot([h, h], [0, k], color=MUC, lw=0.9, zorder=5)
        ax.plot([0, k], [h, h], color=MUC, lw=0.9, zorder=5)
        x_ngoac = (0.45 - trai_mt) / canh_o * k  # cm → toạ độ dữ liệu
        ax.plot(
            [x_ngoac + 0.25, x_ngoac, x_ngoac, x_ngoac + 0.25],
            [0.12, 0.12, h - 0.12, h - 0.12],
            color=MUC_PHU,
            lw=0.7,
            clip_on=False,
        )
        ax.text(
            x_ngoac - 0.15,
            h / 2,
            "hành động",
            rotation=90,
            ha="right",
            va="center",
            fontsize=8,
            color=MUC_PHU,
            clip_on=False,
        )
    ax.set_xticks(np.arange(k) + 0.5)
    ax.set_yticks(np.arange(k) + 0.5)
    ax.set_xticklabels(s["ten_lop"], rotation=45, ha="right", rotation_mode="anchor")
    ax.set_yticklabels(s["ten_lop"])
    ax.tick_params(length=0, pad=2.5)
    for canh in ax.spines.values():
        canh.set_visible(False)
    # cột n: tỷ lệ theo hàng mà không kèm n thì 1/3 trông như 33/100
    for i, c in enumerate(s["tong_hang"]):
        ax.text(k + 0.2, i + 0.54, str(c), ha="left", va="center", fontsize=8, color=MUC_PHU)
    ax.text(k + 0.2, -0.2, "n", ha="left", va="bottom", fontsize=8, color=MUC_PHU)
    chu_hinh(
        0.12,
        0.1,
        f"(a) Ma trận nhầm lẫn của {s['he_thong_ma_tran']} (v2)",
        fontsize=9,
        fontweight="bold",
    )
    chu_hinh(
        0.12,
        0.52,
        "ô = % của hàng; hàng: tham chiếu, cột: mô hình đoán",
        fontsize=8,
        color=MUC_PHU,
    )

    # ------------------------------------------------------------ (b) biểu đồ rừng
    trai_nhan, trai_b, phai_b = 7.35, 10.05, 13.2
    rong_b = phai_b - trai_b
    rung = s["rung"]
    vi_tri, tieu_de_nhom, nhom_truoc, yv = [], [], None, 0.0
    for d in rung:
        if d["nhom"] != nhom_truoc:
            yv -= 0.0 if nhom_truoc is None else 0.5
            tieu_de_nhom.append((yv, d["nhom"]))
            yv -= 0.9
            nhom_truoc = d["nhom"]
        vi_tri.append(yv)
        yv -= 1.0
    day_b, dinh_b = 1.85, 7.3
    axb = _o_cm(fig, trai_b, day_b, rong_b, dinh_b - day_b)
    axb.set_gid("h6-rung")
    axb.set_ylim(yv + 0.5, 0.3)
    moc = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    axb.set_xlim(moc[0], moc[-1])
    axb.set_xticks(moc)
    axb.set_xticklabels(
        ["0" if v == 0 else so(v, 1) if i % 2 == 0 else "" for i, v in enumerate(moc)]
    )
    axb.set_yticks([])
    axb.grid(True, axis="x", color=LUOI, lw=0.5)
    axb.set_axisbelow(True)
    for canh in ("top", "right", "left"):
        axb.spines[canh].set_visible(False)
    axb.tick_params(axis="x", length=2.5, pad=2)
    axb.set_xlabel(
        f"macro-F1 {k} lớp · KTC 95% bootstrap {so(s['n_bootstrap'], 0)} lần", labelpad=3
    )
    tf = axb.get_yaxis_transform()  # x theo trục (0–1), y theo dữ liệu
    x_nhan = (trai_nhan - trai_b) / rong_b
    x_so = 1 + 0.12 / rong_b
    nghieng = {"fontsize": 8, "color": MUC_PHU, "fontstyle": "italic"}
    for y0, ten in tieu_de_nhom:
        axb.text(x_nhan, y0, ten, transform=tf, ha="left", va="center", **nghieng)
    axb.text(
        x_so,
        tieu_de_nhom[0][0],
        "macro-F1 [KTC 95%]",
        transform=tf,
        ha="left",
        va="center",
        **nghieng,
    )
    nhom_goc = rung[0]["nhom"]
    toa_do = {}
    for d, y in zip(rung, vi_tri, strict=True):
        toa_do[d["ma"]] = (d, y)
        dam = d["ma"] in H6_DONG_GOI
        mau = XANH_TOI if dam else (MUC_MO if d["nhom"] == nhom_goc else XANH_DAM)
        rong_ruot = d["ma"] == s["ablation"]["den"]
        axb.plot(d["ktc"], [y, y], color=mau, lw=1.4, solid_capstyle="butt", zorder=3)
        axb.plot(
            d["macro_f1"],
            y,
            ls="none",
            marker="D" if dam else "o",
            ms=5.5 if dam else 4.8,
            mfc="white" if rong_ruot else mau,
            mec=mau,
            mew=1.1 if rong_ruot else 0.8,
            zorder=4,
        )
        kieu = {"fontsize": 8, "color": MUC, "fontweight": "bold" if dam else "normal"}
        # nhãn dài được lấn vào đầu trục (điểm của các dòng đó nằm xa bên phải);
        # nền trắng che lưới dưới chữ. _kiem_nhan_h6 bảo đảm nhãn không đè KTC.
        axb.text(
            x_nhan,
            y,
            f"{d['ma']} · {d['nhan']}",
            transform=tf,
            ha="left",
            va="center",
            bbox={"boxstyle": "square,pad=0.05", "facecolor": "white", "edgecolor": "none"},
            gid=f"nhan-{d['ma']}",
            **kieu,
        )
        axb.text(
            x_so,
            y,
            f"{so(d['macro_f1'], 3)} [{so(d['ktc'][0], 3)}; {so(d['ktc'][1], 3)}]",
            transform=tf,
            ha="left",
            va="center",
            **kieu,
        )
    # ablation: bóng của C2 trên hàng A4, mũi tên tới cận trên KTC của A4 (không đè KTC)
    tu, _ = toa_do[s["ablation"]["tu"]]
    den, y_den = toa_do[s["ablation"]["den"]]
    axb.plot(
        tu["macro_f1"],
        y_den,
        ls="none",
        marker="D",
        ms=5.5,
        mfc="white",
        mec=MUC_MO,
        mew=0.9,
        zorder=4,
    )
    axb.annotate(
        "",
        xy=(den["ktc"][1] + 0.006, y_den),
        xytext=(tu["macro_f1"] - 0.014, y_den),
        arrowprops={
            "arrowstyle": "-|>",
            "color": MUC_PHU,
            "lw": 0.8,
            "mutation_scale": 7,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=2,
    )
    chu_hinh(trai_nhan, 0.1, "(b) macro-F1 trên chat thật", fontsize=9, fontweight="bold")
    chu_hinh(
        trai_nhan,
        0.52,
        "đậm: hai bản đóng gói (v1 mặc định, v2 bật bằng cờ)",
        fontsize=8,
        color=MUC_PHU,
    )
    chan_nguon(
        fig,
        f"Nhãn tham chiếu do tác tử AI gán, {so(s['n'], 0)} bình luận thật, leave-one-session-out "
        f"theo buổi ({s['so_buoi']} buổi live, VOD YouTube qua yt-dlp); số đo mức đồng thuận "
        "với nhãn AI, chưa phải so với người. Nguồn: "
        f"docs/benchmarks/intent-eval/chi-tiet-hinh.json, đo {s['ngay_do']}.",
    )
    return fig


def _kiem_chu_h6(fig) -> None:
    from matplotlib.text import Text

    nho = sorted(
        {
            (round(t.get_fontsize(), 2), t.get_text())
            for t in fig.findobj(Text)
            if t.get_visible() and t.get_text().strip() and t.get_fontsize() < H6_CHU_TOI_THIEU
        }
    )
    if nho:
        sys.exit(f"DỪNG: hình 6 có chữ nhỏ hơn {so(H6_CHU_TOI_THIEU, 1)} pt: {nho[:5]}")


def _kiem_nhan_h6(fig, s: dict) -> None:
    """Nhãn hệ thống lấn vào đầu trục (b) phải dừng TRƯỚC điểm và KTC của chính dòng đó.

    Bố cục cố định, số thì đổi theo lần đo: một hệ thống mới có macro-F1 gần 0 sẽ
    đẩy KTC xuống dưới chữ. Khi đó DỪNG, không vẽ hình chữ đè số.
    """
    axb = next(a for a in fig.axes if a.get_gid() == "h6-rung")
    ve = fig.canvas.get_renderer()
    nghich = axb.transData.inverted()
    loi = []
    for d in s["rung"]:
        chu = next(t for t in axb.texts if t.get_gid() == f"nhan-{d['ma']}")
        mep_phai = nghich.transform((chu.get_window_extent(ve).x1, 0))[0]
        if mep_phai > min(d["ktc"][0], d["macro_f1"]) - 0.005:
            loi.append(f"{d['ma']}: chữ tới x = {mep_phai:.3f}, KTC bắt đầu ở {d['ktc'][0]}")
    if loi:
        sys.exit(
            "DỪNG: nhãn hình 6 đè lên KTC — rút ngắn nhãn trong H6_HE_THONG:\n  - "
            + "\n  - ".join(loi)
        )


def ve_h6(plt) -> dict:
    s = du_lieu_h6(json.loads(CHI_TIET_NLP.read_text(encoding="utf-8")))
    fig = hinh_h6(plt, s)
    _kiem_chu_h6(fig)
    _kiem_nhan_h6(fig, s)
    duong = luu(fig, "h6-nlp.png")
    plt.close(fig)
    _, cao = _kiem_kho(duong)
    if cao > H6_CAO_CM + 0.01:
        sys.exit(f"DỪNG: h6-nlp.png cao {so(cao, 2)} cm > {so(H6_CAO_CM, 1)} cm.")
    return {
        "he_thong_ma_tran": s["he_thong_ma_tran"],
        "n": s["n"],
        "so_buoi": s["so_buoi"],
        "ngay_do": s["ngay_do"],
        "accuracy_ma_tran": s["accuracy_ma_tran"],
        "macro_f1_ma_tran": s["macro_f1_ma_tran"],
        "hang_trong": [x for x, c in zip(s["nhan"], s["tong_hang"], strict=True) if c == 0],
        "ten_hang_trong": [t for t, c in zip(s["ten_lop"], s["tong_hang"], strict=True) if c == 0],
        "rung": [{k: d[k] for k in ("ma", "nhan", "macro_f1", "ktc")} for d in s["rung"]],
        # ma trận đã vẽ — test so với chi-tiet-hinh.json để biết PNG còn khớp bản JSON
        "ma_tran": s["ma_tran"],
        "ablation": s["ablation"],
        "cao_cm": cao,
    }


# ================================================================== NGUON.md
def _luu_y_h6(h: dict | None) -> list[str]:
    """Lưu ý trung thực cho hình 6 — câu so sánh C1/C2 chỉ in khi số còn đúng như vậy."""
    if not h:
        return []
    rung = {d["ma"]: d for d in h["rung"]}
    v2 = H6_DONG_GOI[1]
    ra = [
        "- `h6-nlp.png` đo **mức đồng thuận với nhãn tham chiếu do tác tử AI gán**, chưa "
        "phải độ chính xác so với người: chưa có nhãn người (bảng gán mù cho hai thành viên "
        "đã chuẩn bị nhưng chưa gán — `docs/benchmarks/intent-eval/gan-mu/README.md`). "
        "Dữ liệu là bình luận công khai của VOD lấy qua yt-dlp (quan sát, không qua API "
        "chính thức). Ma trận là của "
        f"{h['he_thong_ma_tran']} vì đó là cấu hình đóng gói `intent_clf_v2.joblib`, chọn "
        "trước chứ không chọn theo điểm trên tập test."
    ]
    c1 = rung.get("C1")
    if c1 and c1["macro_f1"] > rung[v2]["macro_f1"]:
        chong = c1["ktc"][0] <= rung[v2]["ktc"][1] and rung[v2]["ktc"][0] <= c1["ktc"][1]
        ra.append(
            f"- Trên `h6-nlp.png`, C1 ({so(c1['macro_f1'], 3)}) cao hơn {v2} "
            f"({so(rung[v2]['macro_f1'], 3)}) về macro-F1"
            + (", KTC chồng lấn" if chong else "")
            + " — trích đủ cả hai, không gọi C2 là “tốt nhất”."
        )
    return ra


CHUP_H7 = Path(__file__).resolve().parents[1] / "docs" / "img" / "v2" / "chup.json"


def doc_h7() -> dict:
    """Hình 7 không vẽ ở đây: chỉ đọc nguồn (bản build, ngày chụp) cho NGUON.md."""
    if not (RA / "h7-giao-dien.png").is_file() or not CHUP_H7.is_file():
        sys.exit(
            "DỪNG: thiếu hinh/h7-giao-dien.png hoặc docs/img/v2/chup.json — chạy "
            "python scripts/chup_giao_dien.py chup rồi ghep."
        )
    c = json.loads(CHUP_H7.read_text(encoding="utf-8"))
    return {"ban_git": c["git"]["head"], "ngay_chup": c["bat_dau"][:10]}


def ghi_nguon(tom_tat: dict) -> None:
    """Viết NGUON.md từ chính các số vừa vẽ — không gõ tay số nào."""
    dong = [
        "# Nguồn các hình minh hoạ hồ sơ",
        "",
        f"*Sinh bằng* `{LENH}` *— không sửa tay tệp này; chạy lại script.*",
        "",
        "Mọi hình rộng đúng **16 cm** (bề rộng vùng chữ của hồ sơ: A4, lề 3 cm/2 cm), **300 dpi**,",
        "chữ nhỏ nhất 8 pt. Chèn vào `noi-dung.md` bằng `![Hình N. "
        "...](hinh/<tệp>.png){width=16cm}`",
        '(chú thích phải bắt đầu bằng "Hình N." — quy ước của `dung_ho_so.py`); chèn hẹp '
        "hơn 16 cm thì chữ",
        "in ra nhỏ hơn 8 pt. Mỗi hình có dòng nguồn ở chân hình.",
        *(
            [
                f"Riêng `h6-nlp.png`: số trong ô ma trận {so(H6_CHU_O, 1)} pt, hình cao "
                f"{so(tom_tat['h6']['cao_cm'], 1)} cm.",
            ]
            if "h6" in tom_tat
            else []
        ),
        "",
        "| Tệp | Mô tả một dòng | Nguồn chạy lại được |",
        "|---|---|---|",
    ]
    if "h1" in tom_tat:
        h = tom_tat["h1"]
        dong.append(
            f"| `h1-switchback.png` | Lịch khối của một phiên {PHIEN_PHUT} phút sinh bằng chính "
            "hàm gán "
            f"production (seed {h['seed']}): {h['so_khoi']} khối đo, {h['n_bat']} "
            f"BẬT/{h['n_tat']} TẮT, khối đầu "
            f"{so(h['khoi_dau_phut'], 1)} phút và khối cuối {so(h['khoi_cuoi_phut'], 1)} phút "
            "(nhân đôi), "
            f"burn-in {h['burn_in_s']} s đầu mỗi khối, mốc khoá lịch + `design_hash` "
            f"`{h['design_hash'][:12]}…` trước giờ phát, mốc lên sóng (409 nếu chưa có lịch) và "
            "kết thúc | "
            f"`generate_schedule({PHIEN_PHUT}, DesignParams(), seed={h['seed']})`, `design_hash`, "
            "`BURN_IN_S` (`api/routes/reports.py`) |"
        )
    if "h2" in tom_tat:
        dong.append(
            "| `h2-kien-truc.png` | Sơ đồ kiến trúc: nguồn (API chính thức · VOD quan sát qua "
            "yt-dlp · mô "
            "phỏng · link đo) → bộ thu → cổng lọc PII trước khi ghi → kho → lõi thống kê → /desk, "
            "/host làm mù, "
            "kết quả; tô 3 cổng chặn: PII, HTTP 409, `RESULTS_FREEZE_UNTIL` | Đọc từ mã (đường "
            "dẫn ở chân hình); "
            "nguồn HTML chỉnh được: `h2-kien-truc.html`, chụp bằng Playwright Chromium ở 300 dpi |"
        )
    if "h3" in tom_tat:
        h = tom_tat["h3"]
        k_aa, n_aa, lo_a, hi_a = h["phu_aa"]
        k_th, n_th, lo_t, hi_t = h["phu_thu_hoi"]
        dong.append(
            f"| `h3-hieu-chuan-aa.png` | Hiệu chuẩn A/A (mô phỏng): phân phối p-value {n_aa} lần "
            "lặp; tỷ lệ "
            f"bác bỏ {phan_tram(h['ty_le_bac_bo'])} (KTC 95% [{phan_tram(h['ktc_bac_bo'][0])}; "
            f"{phan_tram(h['ktc_bac_bo'][1])}], p nhị thức {so(h['p_nhi_thuc_bac_bo'], 4)}) so "
            "với 5%; độ phủ "
            f"{phan_tram(k_aa / n_aa)} ({k_aa}/{n_aa}) và {phan_tram(k_th / n_th)} "
            f"({k_th}/{n_th}) so với 95% | "
            "`run_validation` với `NGHIEN_CUU` của `scripts/do_lai_so_hieu_chuan.py`; dữ liệu "
            "từng lần lặp: "
            "`du-lieu/hieu-chuan.json`; số tổng đối chiếu `docs/benchmarks/so-hieu-chuan.json` |"
        )
    if "h4" in tom_tat:
        h = tom_tat["h4"]
        mp = h["mo_phong"]
        r1 = h["luoi"][f"{so(h['ty_le_mo_phong'])}|18"]
        r2 = h["luoi"][f"{so(h['ty_le_moc'])}|18"]
        san_tai_mp = h["luoi"][f"{so(h['ty_le_mo_phong'])}|{MDE_SO_PHIEN_MO_PHONG}"]
        dong.append(
            "| `h4-mde.png` | MDE (sàn Poisson, cận dưới) của biến kết quả chính theo số người "
            "xem đồng thời × "
            "số phiên, trục log, hai giả định tỷ lệ nhấp; vùng 5–15 người xem là ƯỚC TÍNH từ "
            "CPM, chưa đo. Ở 18 "
            f"phiên: 5–15 người xem cho MDE {phan_tram(r1['15'], 0)}–{phan_tram(r1['5'], 0)} (tỷ "
            "lệ nhấp "
            f"{so(h['ty_le_mo_phong'])}) hoặc {phan_tram(r2['15'], 0)}–{phan_tram(r2['5'], 0)} "
            "(tỷ lệ nhấp "
            f"{so(h['ty_le_moc'])}). Điểm mô phỏng {MDE_SO_PHIEN_MO_PHONG} phiên: CV trong phiên "
            f"{so(mp['cv_trong_phien'], 3)}, MDE {phan_tram(mp['mde'], 1)} ở "
            f"~{so(mp['khan_gia_tb'], 0)} người "
            f"xem ({so(mp['khan_gia_min'], 0)}–{so(mp['khan_gia_max'], 0)}); sàn Poisson cùng "
            f"chỗ đó là {phan_tram(san_tai_mp['khan_gia_mo_phong'], 1)}, tức bộ mô phỏng gần như "
            "chỉ có nhiễu đếm | "
            "`livelift.analysis.power` "
            "(`analysis_window_seconds`, `poisson_cv`, `mde_relative`), `SimParams`, "
            "`analysis/power/bang_mde_don_hang.py` (`CLICK_RATE_ANCHOR`, `SESSIONS_GRID`) |"
        )
    if "h5" in tom_tat:
        h = tom_tat["h5"]
        phan = []
        for m, v in h.items():
            k, n, lo, hi = v["phu"]
            phan.append(
                f"{m} s: {phan_tram(k / n, 0)} ({k}/{n}), lệch {phan_tram(v['lech_tuong_doi'], 1)}"
            )
        so_seed = len(next(iter(h.values()))["theo_seed"])
        dong.append(
            "| `h5-luu-hieu-ung.png` | Độ phủ KTC 95% và độ lệch khi tác động kéo sang khối sau "
            "(mô phỏng), bán "
            f"rã {'/'.join(h)} s, {so_seed} seed gộp — {'; '.join(phan)} | `run_validation` với "
            "tham số đọc "
            "bằng `ast` từ "
            "`tests/test_sim_validation.py::test_estimator_under_carryover_interference`; dữ liệu "
            "từng lần lặp: "
            "`du-lieu/hieu-ung-luu.json` |"
        )
    if "h6" in tom_tat:
        h = tom_tat["h6"]
        rung = {d["ma"]: d for d in h["rung"]}

        def f1_ktc(ma: str) -> str:
            d = rung[ma]
            return f"{so(d['macro_f1'], 3)} [{so(d['ktc'][0], 3)}; {so(d['ktc'][1], 3)}]"

        v1, v2 = H6_DONG_GOI
        den = h["ablation"]["den"]
        trong = (
            f"; lớp {', '.join(h['ten_hang_trong'])} không có dòng tham chiếu nào (n = 0)"
            if h["ten_hang_trong"]
            else ""
        )
        dong.append(
            f"| `h6-nlp.png` | Phân loại ý định trên {so(h['n'], 0)} bình luận thật "
            f"({h['so_buoi']} buổi live, leave-one-session-out), nhãn tham chiếu do tác tử AI "
            f"gán: (a) ma trận nhầm lẫn {len(h['ma_tran'])} lớp của {h['he_thong_ma_tran']} "
            "(v2) chuẩn hóa "
            f"theo hàng, accuracy {so(h['accuracy_ma_tran'], 3)}{trong}; (b) macro-F1 kèm "
            "KTC 95% bootstrap — "
            + "; ".join(f"{d['ma']} {f1_ktc(d['ma'])}" for d in h["rung"])
            + f". {v1} (v1 đang chạy) {so(rung[v1]['macro_f1'], 3)} → {v2} (v2) "
            f"{so(rung[v2]['macro_f1'], 3)}; bỏ bộ câu mẫu: {so(rung[v2]['macro_f1'], 3)} → "
            f"{so(rung[den]['macro_f1'], 3)} | `docs/benchmarks/intent-eval/chi-tiet-hinh.json` "
            f"(sinh bằng `{LENH_NLP}`, đo {h['ngay_do']}); tên lớp: "
            "`livelift.nlp.labels.LABEL_DISPLAY` |"
        )
    h7 = tom_tat.get("h7")
    if h7:
        n = h7["ngay_chup"]
        dong.append(
            "| `h7-giao-dien.png` | Giao diện thật — ảnh chụp tự động (Playwright, Chromium) bản "
            f"build `{h7['ban_git']}` ngày {n[8:10]}/{n[5:7]}/{n[:4]}, lưới 2×2: (a) wizard "
            "bước 3, lịch 16 khối BẬT/TẮT bốc trước giờ phát của một phiên CHẠY THỬ; (b) feed "
            "bình luận trên bàn trợ live, câu có số điện thoại giả đã thành [SĐT]; (c) màn "
            "người dẫn cùng phiên — không có khối, không có nhánh; (d) kết quả một phiên Demo "
            "Vàng, nhãn DEMO | "
            "`python scripts/chup_giao_dien.py chup` (API + web production đang chạy) rồi "
            "`python scripts/chup_giao_dien.py ghep`; ảnh cắt và số đo: `docs/img/v2/` |"
        )
    # Cỡ mẫu mỗi mức bán rã đọc từ chính số đã vẽ, không gõ tay.
    co_mau = sorted({v["phu"][1] for v in tom_tat.get("h5", {}).values()})
    kem_co_mau = f" (n = {'/'.join(str(n) for n in co_mau)} mỗi mức)" if co_mau else ""
    dong += [
        "",
        "## Lưu ý trung thực khi trích hình",
        "",
        "- Hình 3 và 5 là **mô phỏng Monte-Carlo**; dự án có **0 phiên thí nghiệm ngẫu nhiên "
        "thật**.",
        "- Hình 5 **thay** bảng hiệu ứng lưu cũ (100% / 84% / 60%, docstring `sim/validate.py`, "
        "đo 02/09): bảng "
        f"đó không tái lập được ở mã hiện tại. Trích số từ hình này kèm cỡ mẫu{kem_co_mau}.",
        "- Hình 4 là **sàn Poisson** — với CÙNG tỷ lệ nhấp và số người xem, MDE thật chỉ có "
        "thể lớn hơn. Tỷ lệ nhấp chưa đo được (cả hai panel là giả "
        "định); vùng 5–15 người xem là ước tính từ chi phí quảng cáo (CPM), **chưa đo**.",
        "- Hình 2: nguồn VOD là dữ liệu quan sát lấy bằng yt-dlp, **không** qua API chính thức; "
        "các bộ nối API "
        "chính thức đã viết nhưng chưa chạy với khoá thật. `RESULTS_FREEZE_UNTIL` hiện để trống "
        "(tắt) trong "
        "`.env.example`; khi đặt, `/ket-qua` và `/bao-cao` bị khoá nhưng "
        "`GET /sessions/{id}/report` vẫn trả chênh lệch trung bình (đường lọt đã biết, kiểm "
        "toán 25/09) — hộp CỔNG 3 ghi rõ; vá xong thì sửa `html_h2()` và chạy lại `--chi h2`.",
        *_luu_y_h6(tom_tat.get("h6")),
        *(
            [
                "- `h7-giao-dien.png` là ảnh chụp giao diện: bình luận là dữ liệu mô phỏng tổng "
                "hợp của một phiên chạy thử (không phải khách thật); ô (d) là dữ liệu MẪU — không "
                "phải kết quả thí nghiệm (dự án có 0 phiên thí nghiệm ngẫu nhiên thật)."
            ]
            if tom_tat.get("h7")
            else []
        ),
        "",
        "## Chạy lại",
        "",
        "```",
        f"{LENH}               # vẽ lại từ du-lieu/*.json (~1 phút)",
        f"{LENH} --kiem        # chạy lại Monte-Carlo, đối chiếu TỪNG lần lặp với du-lieu/ (~9 "
        "phút)",
        f"{LENH} --tinh-lai    # chạy lại Monte-Carlo và ghi đè du-lieu/ (khi mã đã đổi có chủ ý)",
        f"{LENH_NLP}   # đo lại bộ phân loại ý định → chi-tiet-hinh.json",
        f"{LENH} --chi h6      # rồi vẽ lại hình 6 từ chi-tiet-hinh.json (vài giây)",
        "```",
        "",
        f"Cần `matplotlib`, Pillow, và Playwright + Chromium cho hình 2: {cach_cai_goi_ve()}.",
        "",
    ]
    (RA / "NGUON.md").write_text("\n".join(dong), encoding="utf-8")
    print(f"  đã ghi {(RA / 'NGUON.md').relative_to(GOC)}")


# ==================================================================== main
def main() -> int:
    configure()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--chi", default="h1,h2,h3,h4,h5,h6,h7", help="danh sách hình cần vẽ, ví dụ h1,h4"
    )
    nhom = ap.add_mutually_exclusive_group()
    nhom.add_argument(
        "--tinh-lai",
        action="store_true",
        help="chạy lại Monte-Carlo của hình 3 và 5, ghi đè du-lieu/",
    )
    nhom.add_argument(
        "--kiem",
        action="store_true",
        help="chạy lại Monte-Carlo, đối chiếu từng lần lặp với du-lieu/ (không ghi đè "
        "du-lieu/, vẫn vẽ lại hình); lệch → mã 1",
    )
    args = ap.parse_args()
    che_do = "tinh_lai" if args.tinh_lai else "kiem" if args.kiem else "doc"
    chon = {h.strip() for h in args.chi.split(",") if h.strip()}
    la = chon - {"h1", "h2", "h3", "h4", "h5", "h6", "h7"}
    if la:
        ap.error(f"không có hình {sorted(la)}")

    tom_tat_cu = RA / "du-lieu" / "tom-tat.json"
    tom_tat: dict = {}
    if tom_tat_cu.exists():
        tom_tat = json.loads(tom_tat_cu.read_text(encoding="utf-8"))

    plt = nap_matplotlib() if chon & {"h1", "h3", "h4", "h5", "h6"} else None
    mod_do_lai = nap_do_lai_so_hieu_chuan()
    ban_git = ban_git_hien_tai(mod_do_lai)  # TRƯỚC mọi lần ghi — xem docstring của hàm

    if "h1" in chon:
        print("Hình 1 — lịch switchback")
        tom_tat["h1"] = ve_h1(plt)
    if "h2" in chon:
        print("Hình 2 — kiến trúc")
        ve_h2()
        tom_tat["h2"] = {"ok": True}
    if "h3" in chon:
        print("Hình 3 — hiệu chuẩn A/A")
        mong_doi = {
            ten: ch["tham_so"] | {"treatment_effect": ch["treatment_effect"]}
            for ten, ch in mod_do_lai.NGHIEN_CUU.items()
        }
        du_lieu = doc_hoac_tinh(
            "hieu-chuan", lambda: tinh_hieu_chuan(mod_do_lai), mong_doi, che_do, ban_git
        )
        dem = kiem_khop_so_hieu_chuan(du_lieu)
        tom_tat["h3"] = ve_h3(plt, du_lieu, dem)
    if "h4" in chon:
        print("Hình 4 — MDE")
        tom_tat["h4"] = ve_h4(plt)
    if "h5" in chon:
        print("Hình 5 — hiệu ứng lưu")
        mong_doi = {
            "cong": tham_so_cong_hieu_ung_luu(),
            "ban_ra_s": list(BAN_RA_S),
            "seed_them": list(SEED_THEM),
        }
        du_lieu = doc_hoac_tinh("hieu-ung-luu", tinh_hieu_ung_luu, mong_doi, che_do, ban_git)
        tom_tat["h5"] = ve_h5(plt, du_lieu)
    if "h6" in chon:
        print("Hình 6 — phân loại ý định trên chat thật")
        tom_tat["h6"] = ve_h6(plt)
    if "h7" in chon:
        print("Hình 7 — giao diện (ảnh chụp; dựng bằng scripts/chup_giao_dien.py ghep)")
        tom_tat["h7"] = doc_h7()

    DU_LIEU.mkdir(parents=True, exist_ok=True)
    tom_tat_cu.write_text(
        json.dumps(tom_tat, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8"
    )
    ghi_nguon(tom_tat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
