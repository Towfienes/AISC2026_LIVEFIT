"""Đo lại các con số hiệu chuẩn CÔNG BỐ và ghi ra một nguồn sự thật duy nhất.

Vì sao tệp này tồn tại
----------------------
Kiểm toán ngày 14/09/2026 chạy lại đúng tham số của cổng A/A và ra **3,50%
(7/200), p = 0,4168, độ phủ 96,50%** — trong khi hồ sơ, README, FACT-SHEET, kịch
bản demo và cả lời thoại video đang công bố **4,5% (9/200), p = 0,872, độ phủ
95,5%**. Không ai gian dối: 4,5% là số đo thật **ngày 30/08/2026**; mã đã đổi
nhiều lần sau đó và không ai đo lại. Con số cũ cứ thế được chép sang tài liệu mới.

Đó là lỗi nguy hiểm nhất một hồ sơ khoa học có thể mắc, vì hồ sơ TỰ HỨA rằng
"mọi con số sinh lại được bằng một lệnh". Giám khảo làm đúng câu đó sẽ ra số
khác, và mất niềm tin vào toàn bộ phần còn lại.

Nguyên nhân gốc: cổng Monte-Carlo chỉ IN số khi nó đỏ. Khi xanh, số mới chạy ra
biến mất, còn số cũ nằm lại trong tài liệu.

Cách tệp này chặn tái diễn: chạy lại các nghiên cứu Monte-Carlo bằng **đúng tham
số của cổng** (nhập thẳng từ ``tests/test_sim_validation.py`` để hai bên không
thể trôi khỏi nhau), rồi ghi kết quả kèm ngày đo và bản git vào
``docs/benchmarks/so-hieu-chuan.json``. Tài liệu trích từ tệp JSON đó.

    .venv/Scripts/python scripts/do_lai_so_hieu_chuan.py            # đo lại, ghi JSON
    .venv/Scripts/python scripts/do_lai_so_hieu_chuan.py --kiem     # chỉ đối chiếu, không ghi

``--kiem`` trả mã thoát khác 0 nếu số đo lệch số đã ghi — dùng cho lần chạy
trước khi nộp, và chạy được trong CI đêm.

Chạy mất khoảng 10–20 phút: đây là nghiên cứu Monte-Carlo thật, không phải test
nhanh. Đừng đưa vào ``pytest -m "not slow"``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from scipy.stats import binomtest

from livelift.console import configure
from livelift.sim.simulator import SimParams
from livelift.sim.validate import run_validation

GOC = Path(__file__).resolve().parents[1]
RA = GOC / "docs" / "benchmarks" / "so-hieu-chuan.json"

ALPHA = 0.05

# Tham số PHẢI trùng với cổng tương ứng trong tests/test_sim_validation.py.
# Trùng thủ công là một điểm trôi; test `test_tham_so_do_lai_trung_cong` trong
# tests/test_so_hieu_chuan.py đọc cả hai tệp và so sánh, nên trôi thì đỏ.
NGHIEN_CUU = {
    "aa": {
        "mo_ta": "Hiệu chuẩn A/A — không có tác động thật, tỷ lệ bác bỏ phải bằng alpha",
        "cong": "test_aa_false_positive_rate_near_alpha",
        "tham_so": {
            "n_reps": 200,
            "n_sessions_per_rep": 6,
            "session_minutes": 60,
            "n_draws": 300,
            "master_seed": 11,
        },
        "treatment_effect": 0.0,
    },
    "thu_hoi": {
        "mo_ta": "Thu hồi tác động biết trước — độ lệch và độ phủ KTC",
        "cong": "test_effect_recovery_bias_and_coverage",
        "tham_so": {
            "n_reps": 40,
            "n_sessions_per_rep": 8,
            "session_minutes": 90,
            "n_draws": 300,
            "master_seed": 13,
        },
        "treatment_effect": 0.3,
    },
}


def ban_git():
    try:
        # noqa S607: "git" lấy từ PATH là chủ ý — script chạy trên máy lập
        # trình viên, và ghim đường dẫn tuyệt đối sẽ hỏng trên máy khác.
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=GOC,
            capture_output=True,
            text=True,
            timeout=20,
        )
        ban = out.stdout.strip() or "khong-ro"
    except (OSError, subprocess.TimeoutExpired):
        return "khong-ro"
    try:
        ban_do = subprocess.run(
            ["git", "status", "--porcelain"],  # noqa: S607
            cwd=GOC,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if ban_do.stdout.strip():
            ban += "+ban-lam-viec-co-thay-doi"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ban


def do_mot(ten, cau_hinh):
    print(f"  đang chạy {ten} ({cau_hinh['tham_so']['n_reps']} lần lặp)…", flush=True)
    res = run_validation(
        sim_params=SimParams(treatment_effect=cau_hinh["treatment_effect"]),
        **cau_hinh["tham_so"],
    )
    n_reps = cau_hinh["tham_so"]["n_reps"]
    n_bac_bo = round(res.rejection_rate * n_reps)
    n_phu = round(res.ci_coverage * n_reps)
    return {
        "mo_ta": cau_hinh["mo_ta"],
        "cong": cau_hinh["cong"],
        "tham_so": cau_hinh["tham_so"] | {"treatment_effect": cau_hinh["treatment_effect"]},
        "ty_le_bac_bo": round(res.rejection_rate, 4),
        "so_lan_bac_bo": f"{n_bac_bo}/{n_reps}",
        "p_nhi_thuc_bac_bo": round(binomtest(n_bac_bo, n_reps, ALPHA).pvalue, 4),
        "do_phu_ktc": round(res.ci_coverage, 4),
        "so_lan_phu": f"{n_phu}/{n_reps}",
        "p_nhi_thuc_do_phu": round(binomtest(n_phu, n_reps, 1 - ALPHA).pvalue, 4),
        "do_lech_tuong_doi": round(res.relative_bias, 4),
    }


def main():
    configure()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kiem", action="store_true", help="chỉ đối chiếu với số đã ghi, không ghi đè")
    args = ap.parse_args()

    print("Đo lại số hiệu chuẩn — mất khoảng 10–20 phút, đừng ngắt giữa chừng.")
    ket_qua = {ten: do_mot(ten, ch) for ten, ch in NGHIEN_CUU.items()}
    moi = {
        "ngay_do": date.today().isoformat(),
        "ban_git": ban_git(),
        "alpha": ALPHA,
        "nghien_cuu": ket_qua,
        "ghi_chu": "Sinh bằng scripts/do_lai_so_hieu_chuan.py. "
        "Đây là NGUỒN DUY NHẤT cho các con số hiệu chuẩn trong mọi tài liệu. "
        "Sửa tay tệp này là sai quy trình — chạy lại script.",
    }

    print()
    for ten, kq in ket_qua.items():
        print(f"[{ten}] {kq['mo_ta']}")
        print(
            f"   bác bỏ    {kq['ty_le_bac_bo']:.2%} ({kq['so_lan_bac_bo']}), "
            f"p nhị thức {kq['p_nhi_thuc_bac_bo']}"
        )
        print(
            f"   phủ KTC   {kq['do_phu_ktc']:.2%} ({kq['so_lan_phu']}), "
            f"p nhị thức {kq['p_nhi_thuc_do_phu']}"
        )
        print(f"   độ lệch   {kq['do_lech_tuong_doi']:+.2%}")

    if args.kiem:
        if not RA.exists():
            print(f"\nChưa có {RA.name} — chạy lại không kèm --kiem để tạo.")
            return 1
        cu = json.loads(RA.read_text(encoding="utf-8"))
        lech = [
            f"{ten}.{khoa}: đã ghi {cu['nghien_cuu'].get(ten, {}).get(khoa)} ≠ đo được {kq[khoa]}"
            for ten, kq in ket_qua.items()
            for khoa in ("ty_le_bac_bo", "do_phu_ktc", "do_lech_tuong_doi")
            if cu["nghien_cuu"].get(ten, {}).get(khoa) != kq[khoa]
        ]
        if lech:
            print("\nLỆCH so với số đã ghi:")
            for d in lech:
                print("  -", d)
            print("\nChạy lại không kèm --kiem để cập nhật, RỒI sửa mọi tài liệu trích số.")
            return 1
        print(f"\nKhớp {RA.name} (đo ngày {cu['ngay_do']}).")
        return 0

    RA.parent.mkdir(parents=True, exist_ok=True)
    RA.write_text(json.dumps(moi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nĐã ghi {RA}")
    print(
        "Bây giờ cập nhật các tài liệu trích số này: docs/competition/FACT-SHEET.md, "
        "README.md, docs/competition/sang-tao-tre-2026/noi-dung.md, "
        "docs/competition/sang-tao-tre-2026/07-KICH-BAN-2-VIDEO.md"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
