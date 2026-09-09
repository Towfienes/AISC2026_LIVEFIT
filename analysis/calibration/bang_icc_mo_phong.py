"""Sinh bảng ánh xạ knob → ICC của bộ mô phỏng (gói P1-K2) → docs/benchmarks/sim-icc-map.md.

Chạy:  python analysis/calibration/bang_icc_mo_phong.py

Bảng này là SỐ ĐO, không phải giả định — và đó chính là lý do nó cần một lệnh
tái lập. Trước 09/09 các con số σ → ICC nằm trong docstring của
`livelift.sim.simulator` mà không có đường nào chạy lại được; người đọc chỉ có
thể tin. Script này đóng lỗ hổng đó: mọi con số trong file đầu ra đều do đúng
lệnh trên sinh ra, từ hàm gán và hàm mô phỏng production.

Phương pháp:

* mỗi hàng mô phỏng `--sessions` phiên × `--minutes` phút với `treatment_effect=0`
  (có tác động thì tương phản nhánh sẽ lẫn vào phần "giữa phiên" của ANOVA);
* `y` là biến kết quả chính đúng như phân tích thấy nó — khối đo được, sau
  burn-in (`livelift.core.features.block_frame`);
* ICC = ANOVA một chiều ICC(1) (Shrout & Fleiss 1979), KHÔNG chặn ở 0;
* sai số chuẩn = bootstrap theo CỤM PHIÊN (không phải theo khối: khối trong cùng
  phiên phụ thuộc nhau, đó đúng là đại lượng đang đo);
* mọi hàng dùng CÙNG `master_seed`, nên cùng chuỗi seed phiên ⇒ cùng lượt vào,
  cùng thời gian ở lại, cùng nhiễu AR(1). Hai hàng chỉ khác nhau ở knob.

CẢNH BÁO đọc bảng: hàng σ=0 KHÔNG cho ICC=0. ICC(1) theo ANOVA lệch LÊN khi
phương sai trong-cụm không đều, mà `session_shock_sd` (cú sốc lượt vào) làm đúng
thế — phiên đông đo tỷ lệ chính xác hơn phiên vắng. Giá trị σ=0 vì vậy là NỀN
của thước đo, không phải bằng chứng "thế giới không phân cụm".
"""

from __future__ import annotations

import argparse
from pathlib import Path

from livelift.console import configure as _configure_console
from livelift.core.assigner.outer import DesignParams
from livelift.sim.report import render_icc_map
from livelift.sim.validate import DEFAULT_FRAILTY_CVS, DEFAULT_ICC_SIGMAS, measure_icc_map

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "benchmarks" / "sim-icc-map.md"
COMMAND = "python analysis/calibration/bang_icc_mo_phong.py"

N_SESSIONS = 400
SESSION_MINUTES = 90
BLOCK_MIN = 5
BURN_IN_S = 60
MASTER_SEED = 909
N_BOOT = 400


def _repro_command(args: argparse.Namespace) -> str:
    """The command that regenerates THIS file — every overridden flag included.

    Built from the full argument list rather than a hand-picked subset: a
    "reproduction command" that silently drops, say, ``--boot`` is worse than no
    command at all, because it looks checkable and is not.
    """
    parts = [COMMAND]
    for flag, value, default in (
        ("--sessions", args.sessions, N_SESSIONS),
        ("--minutes", args.minutes, SESSION_MINUTES),
        ("--block", args.block, BLOCK_MIN),
        ("--burn-in", args.burn_in, BURN_IN_S),
        ("--seed", args.seed, MASTER_SEED),
        ("--boot", args.boot, N_BOOT),
    ):
        if value != default:
            parts.append(f"{flag} {value}")
    if Path(args.out) != OUT:
        parts.append(f'--out "{args.out}"')
    return " ".join(parts)


def _header(args: argparse.Namespace) -> str:
    cmd = _repro_command(args)
    return (
        "# Ánh xạ knob không đồng nhất → ICC cấp phiên (SỐ ĐO)\n"
        "\n"
        f"Lệnh tái lập (sinh chính file này):\n\n```\n{cmd}\n```\n"
        "\n"
        f"{args.sessions} phiên × {args.minutes} phút, khối {args.block} phút, burn-in "
        f"{args.burn_in} giây, `treatment_effect=0`, `master_seed={args.seed}`. `y` là biến "
        "kết quả chính (lượt nhấp hợp lệ / 1.000 giây·người xem) trên các khối ĐO ĐƯỢC sau "
        "burn-in. ICC = ANOVA một chiều ICC(1) (Shrout & Fleiss 1979), **không chặn ở 0**; "
        f"± là sai số chuẩn bootstrap theo CỤM PHIÊN ({args.boot} lần lặp, cùng seed).\n"
        "\n"
        "Hai bảng dùng CÙNG chuỗi seed phiên (cùng lượt vào, cùng thời gian ở lại, cùng "
        "nhiễu AR(1)), nên khác biệt giữa các hàng là do knob chứ không do may rủi của seed. "
        "Hàng đầu mỗi bảng (knob = 0) là cùng một thế giới, và đúng ra phải cho cùng một "
        "con số — đó là phép tự kiểm của chính file này.\n"
        "\n"
        "## 1. `session_click_sigma` — knob ICC chính thức\n"
    )


def _frailty_header() -> str:
    return (
        "\n"
        "## 2. `click_frailty_cv` — knob PHÂN TÁN, có tác dụng phụ ICC\n"
        "\n"
        "Frailty theo người xem `u_i ~ Gamma(1/cv², cv²)` được kỳ vọng KHÔNG đụng tới ICC. "
        "Đo ra thì có: khán giả hữu hạn (~500 lượt vào/phiên) nên trung bình frailty của "
        "phiên tự nó là một nhân tử cấp phiên với CV ≈ cv/√N. Bảng này là số đo của tác "
        "dụng phụ đó — công bố chứ không giấu.\n"
    )


def _footer() -> str:
    return (
        "\n"
        "**Đọc bảng.**\n"
        "\n"
        "- Hàng knob = 0 **không** cho ICC = 0. ICC(1) theo ANOVA lệch LÊN khi phương sai "
        "trong-cụm không đều, mà `session_shock_sd` (cú sốc lượt vào) làm đúng thế: phiên "
        'đông đo tỷ lệ chính xác hơn phiên vắng. Hàng này là NỀN của thước đo — đọc "σ=0" '
        'là "ICC ≈ 0,01", không phải "không phân cụm".\n'
        "- Cột **trung bình y** phải giữ nguyên trên mọi hàng của CẢ HAI bảng: hai knob đều "
        "là nhân tử mean-1 (`exp(N(0,σ²) − σ²/2)` và `Gamma` kỳ vọng 1). Một hàng lệch mức "
        "là dấu hiệu số hạng hiệu chỉnh trung bình bị mất.\n"
        "- Cột **phương sai TRONG-phiên** là thứ PHÂN BIỆT hai knob: bảng 1 giữ nguyên nó "
        "(knob phiên dịch cả phiên), bảng 2 làm nó tăng (frailty làm phân tán chính các "
        "khối). Muốn quay ICC thì dùng bảng 1; bảng 2 là khi câu hỏi là quá phân tán.\n"
        "- Ba mốc dùng cho cổng hiệu chuẩn: σ=0,03 → ICC≈0,02; **σ=0,06 → ICC≈0,05** (thế "
        "giới hai cổng `-m slow` chạy); σ=0,095 → ICC≈0,10.\n"
    )


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = argparse.ArgumentParser(prog=COMMAND, description=__doc__)
    parser.add_argument("--sessions", type=int, default=N_SESSIONS)
    parser.add_argument("--minutes", type=int, default=SESSION_MINUTES)
    parser.add_argument("--block", type=int, default=BLOCK_MIN)
    parser.add_argument("--burn-in", type=int, default=BURN_IN_S)
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--boot", type=int, default=N_BOOT)
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv)

    common = {
        "n_sessions": args.sessions,
        "session_minutes": args.minutes,
        "design": DesignParams(block_min=args.block),
        "burn_in_s": args.burn_in,
        "master_seed": args.seed,
        "n_boot": args.boot,
    }
    sigma_rows = measure_icc_map(DEFAULT_ICC_SIGMAS, knob="session_click_sigma", **common)
    frailty_rows = measure_icc_map(DEFAULT_FRAILTY_CVS, knob="click_frailty_cv", **common)

    text = (
        render_icc_map(sigma_rows, header=_header(args))
        + render_icc_map(frailty_rows, header=_frailty_header())
        + _footer()
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"→ đã ghi {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
