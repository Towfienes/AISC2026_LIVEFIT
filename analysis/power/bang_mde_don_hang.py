"""Sinh bảng MDE cho biến kết quả ĐƠN HÀNG (gói Q4) → docs/benchmarks/order-mde.md.

Chạy:  python analysis/power/bang_mde_don_hang.py

TOÀN BỘ bảng này là KỊCH BẢN, không phải số đo. Ba đầu vào là prior/giả định và
mỗi dòng của báo cáo nói rõ điều đó:

* tỷ lệ nhấp (click/1000 giây·người xem) — dự án CHƯA đo được; đây là đại lượng
  chỉ có từ phiên thăm dò của chính nhóm.
* phễu click→đơn — prior Taobao UserBehavior (Tianchi #649): pv→giỏ 9,33% ×
  giỏ→mua 24,33% ≈ 2,27%. Bước giỏ→mua (q2) được QUÉT vì đây là bước một phiên
  livestream lệch khỏi prior nhiều nhất.
* nhân khán giả nhánh đối tác ×4,9 (arXiv:2106.03415) — chỉ nhân KHÁN GIẢ.

CẤM map KuaiLive vào phễu: 'click' của KuaiLive là VÀO PHÒNG, không phải nhấp
sản phẩm ghim (docs/benchmarks/kuailive-calibration.md nói đúng giới hạn này cho
`base_click_prob_per_min`). Dùng nó ở đây sẽ ra một tỷ lệ chuyển đổi của một
hành vi khác hẳn.

Số MDE in ra là SÀN POISSON — cận DƯỚI. Phiên thật còn phương sai hệ thống chồng
lên nhiễu đếm, nên MDE thật chỉ có thể LỚN HƠN.
"""

from __future__ import annotations

from pathlib import Path

from livelift.analysis.power import (
    FUNNEL_CART_TO_BUY,
    FUNNEL_PV_TO_CART,
    PARTNER_AUDIENCE_MULTIPLIER,
    Q2_GRID,
    RANDOMIZATION_TEST_MARGIN,
    analysis_window_seconds,
    expected_orders,
    order_mde_table,
)
from livelift.console import configure as _configure_console

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "benchmarks" / "order-mde.md"
COMMAND = "python analysis/power/bang_mde_don_hang.py"

# --- lưới kịch bản ---------------------------------------------------------

SESSION_MIN = 90
BLOCK_MIN = 5
BURN_IN_S = 60
COMPLIANCE = 0.95

SESSIONS_GRID = (18, 28)  # A/B của PREREGISTRATION §6
AUDIENCE_GRID = (15.0, 50.0, 150.0, 500.0)  # người xem đồng thời trung bình

# Tỷ lệ nhấp trung tâm của bảng chính. Chọn 0,30 vì đó là mức tái tạo đúng mốc
# tỉnh táo trong agenda Q4 (15 người xem × 90 phút → 0,3–0,6 đơn/phiên); mức
# 1,00 là giá trị suy ra từ tham số mô phỏng hiện tại
# (`SimParams.base_click_prob_per_min = 0,06`/người xem·phút) và được in kèm để
# thấy khoảng cách. Cả hai đều là GIẢ ĐỊNH cho tới khi có phiên thăm dò.
CLICK_RATE_ANCHOR = 0.30
CLICK_RATE_SENSITIVITY = (0.20, 0.30, 0.40, 1.00)


def _fmt(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ")


def _table(rows: list[dict]) -> list[str]:
    lines = [
        "| Nhánh | Phiên | Khán giả | q2 | Đơn/khối | Đơn/phiên | CV Poisson | "
        "MDE tương đối | MDE tuyệt đối (đơn/phiên) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['branch']} | {r['n_sessions']} | {r['audience']:.0f} "
            f"({r['audience_effective']:.0f}) | {r['q2']:.2f} | "
            f"{r['orders_per_block']:.3f} | {_fmt(r['orders_per_session'])} | "
            f"{r['cv_poisson']:.2f} | {r['mde_relative']:.0%} | "
            f"{_fmt(r['mde_orders_per_session'])} |"
        )
    return lines


def build_report() -> str:
    window_s = sum(analysis_window_seconds(SESSION_MIN, BLOCK_MIN, True, BURN_IN_S))
    rows = order_mde_table(
        CLICK_RATE_ANCHOR,
        SESSIONS_GRID,
        AUDIENCE_GRID,
        Q2_GRID,
        session_minutes=SESSION_MIN,
        block_min=BLOCK_MIN,
        burn_in_s=BURN_IN_S,
        compliance=COMPLIANCE,
    )
    blocks_per_session = rows[0]["blocks_per_session"]

    lines = [
        "# MDE đơn hàng theo số phiên × cỡ khán giả × q2",
        "",
        f"*Sinh lại bằng đúng một lệnh:* `{COMMAND}`",
        "",
        "> **KỊCH BẢN — KHÔNG PHẢI SỐ ĐO.** Không dòng nào trong bảng này là kết quả",
        "> quan sát của LiveLift. Ba đầu vào là prior/giả định, liệt kê ngay dưới đây.",
        "",
        "## Nguồn prior và điều KHÔNG được dùng",
        "",
        f"- **Phễu click→đơn**: pv→giỏ **{FUNNEL_PV_TO_CART:.2%}** × giỏ→mua "
        f"**{FUNNEL_CART_TO_BUY:.2%}** ≈ **{FUNNEL_PV_TO_CART * FUNNEL_CART_TO_BUY:.2%}** "
        "— Taobao UserBehavior, Alibaba Tianchi bộ #649 (100 triệu tương tác, 11–12/2017). "
        "Khác nền tảng, khác năm, khác quốc gia: dùng làm prior, không làm số công bố.",
        f"- **Quét q2 (giỏ→mua)**: {', '.join(f'{q:.2f}' for q in Q2_GRID)} — prior "
        f"{FUNNEL_CART_TO_BUY:.4f} nằm giữa hai mốc 0.15 và 0.25. q1 (pv→giỏ) giữ nguyên.",
        f"- **Nhánh đối tác**: nhân **khán giả** ×**{PARTNER_AUDIENCE_MULTIPLIER:g}** "
        "(arXiv:2106.03415). Chỉ nhân khán giả — nguồn đó không nói gì về phễu hay tỷ lệ "
        "nhấp nên hai đại lượng này giữ nguyên.",
        f"- **Tỷ lệ nhấp**: bảng chính dùng **{CLICK_RATE_ANCHOR:.2f}** click hợp lệ / 1000 "
        "giây·người xem — một GIẢ ĐỊNH. Dự án chưa có số đo; xem bảng độ nhạy bên dưới.",
        "",
        "**CẤM map KuaiLive vào phễu này.** 'Click' của KuaiLive là *vào phòng live*, "
        "không phải nhấp sản phẩm ghim — hai hành vi khác nhau về ngữ nghĩa. "
        "`docs/benchmarks/kuailive-calibration.md` đã nêu đúng giới hạn đó cho "
        "`base_click_prob_per_min`; ràng buộc ở đây mạnh hơn, vì một tỷ lệ chuyển đổi sai "
        "ngữ nghĩa sẽ đi thẳng vào con số đơn hàng.",
        "",
        "## Cách tính (dùng lại đúng machinery MDE hiện có)",
        "",
        f"- Bố cục phiên: **{SESSION_MIN} phút**, khối **{BLOCK_MIN} phút**, khối biên nhân "
        f"đôi → **{blocks_per_session} khối đo/phiên**; burn-in **{BURN_IN_S}s** cắt khỏi "
        "cửa sổ kết quả của từng khối (đúng quy tắc `core.features.block_frame`).",
        "- Đơn kỳ vọng mỗi khối: `λ_k = tỷ_lệ_nhấp/1000 × khán_giả × cửa_sổ_k × q1 × q2`.",
        "- Đơn là biến ĐẾM HIẾM nên phương sai bị nhiễu đếm chi phối: CV nạp vào "
        "`mde_relative` là **CV Poisson** `√(trung bình_k 1/λ_k)` — cùng đại lượng mà "
        "`poisson_floor()` đo trên dữ liệu thật.",
        f"- MDE đã chia cho tuân thủ {COMPLIANCE:.2f} và nhân biên độ kiểm định ngẫu nhiên "
        f"hóa đo được ×{RANDOMIZATION_TEST_MARGIN:g} (xem docstring "
        "`livelift.analysis.power`).",
        "",
        "> **Đây là SÀN.** Con số MDE dưới đây là cận DƯỚI: nó giả định biến kết quả không "
        "có phương sai nào ngoài nhiễu đếm. Phiên thật có sốc cấp phiên, biến động khán "
        "giả, thay đổi sản phẩm — MDE thật chỉ có thể LỚN HƠN.",
        "",
        f"## Bảng chính — tỷ lệ nhấp {CLICK_RATE_ANCHOR:.2f}/1000 giây·người xem",
        "",
        "Cột *Khán giả* ghi `danh nghĩa (hiệu dụng sau nhân đối tác)`.",
        "",
    ]
    lines += _table(rows)

    lines += [
        "",
        "## Độ nhạy theo tỷ lệ nhấp (ô neo: 18 phiên, 15 người xem, q2 = 0.25)",
        "",
        "| Tỷ lệ nhấp /1000 gs·nx | Đơn/phiên | CV Poisson | MDE tương đối |",
        "|---:|---:|---:|---:|",
    ]
    for cr in CLICK_RATE_SENSITIVITY:
        row = order_mde_table(
            cr,
            (18,),
            (15.0,),
            (0.25,),
            session_minutes=SESSION_MIN,
            block_min=BLOCK_MIN,
            burn_in_s=BURN_IN_S,
            compliance=COMPLIANCE,
            include_partner=False,
        )[0]
        lines.append(
            f"| {cr:.2f} | {row['orders_per_session']:.2f} | "
            f"{row['cv_poisson']:.2f} | {row['mde_relative']:.0%} |"
        )

    sim_orders = order_mde_table(
        1.0,
        (18,),
        (15.0,),
        (FUNNEL_CART_TO_BUY,),
        session_minutes=SESSION_MIN,
        block_min=BLOCK_MIN,
        burn_in_s=BURN_IN_S,
        include_partner=False,
    )[0]["orders_per_session"]

    lines += [
        "",
        "## Mốc tỉnh táo (assert trong `tests/test_power.py`)",
        "",
        f"- 15 người xem × {SESSION_MIN} phút, tỷ lệ nhấp {CLICK_RATE_ANCHOR:.2f}/1000 "
        "giây·người xem, prior phễu đầy đủ → "
        f"**{expected_orders(CLICK_RATE_ANCHOR, 15.0 * window_s):.2f} đơn/phiên** trong cửa "
        f"sổ phân tích ({window_s:.0f} giây/phiên sau burn-in). Khớp bậc với mốc kỳ vọng "
        "0.3–0.6 đơn/phiên của agenda.",
        f"- Cùng ô đó nhưng lấy tỷ lệ nhấp suy ra từ machinery mô phỏng hiện có "
        f"(`SimParams.base_click_prob_per_min = 0.06`/người xem·phút ⇒ 1.00/1000 "
        f"giây·người xem) → **{sim_orders:.2f} đơn/phiên**, tức cao hơn mốc agenda khoảng "
        f"{sim_orders / 0.6:.1f}–{sim_orders / 0.3:.1f} lần. Cùng bậc độ lớn, nhưng KHÔNG "
        "trùng: ghi ra ở đây thay vì làm tròn cho khớp. Tham số mô phỏng đó vốn được đánh "
        "dấu là GIẢ ĐỊNH và chỉ phiên thăm dò mới chốt được.",
        "",
        "## Kết luận đọc được ngay",
        "",
    ]
    lines += _conclusions(rows)
    lines.append("")
    return "\n".join(lines)


SELF_RUN_AUDIENCE_CEILING = 50.0
"""Cỡ khán giả mà một Page tự vận hành có thể trông đợi ở giai đoạn thí nghiệm."""


def _conclusions(rows: list[dict]) -> list[str]:
    """Kết luận SUY TỪ BẢNG, không viết tay — sửa lưới là kết luận tự đổi theo."""
    small_self_run = [
        r
        for r in rows
        if r["audience_effective"] <= SELF_RUN_AUDIENCE_CEILING and r["branch"].startswith("không")
    ]
    best_small = min(r["mde_relative"] for r in small_self_run)
    usable = [r for r in rows if r["mde_relative"] <= 0.30]
    min_audience_usable = min((r["audience_effective"] for r in usable), default=None)

    out = [
        f"- Ở quy mô một Page tự vận hành (≤ {SELF_RUN_AUDIENCE_CEILING:.0f} người xem đồng "
        f"thời), MDE tốt nhất trong bảng vẫn là **{best_small:.0%}** — nghĩa là **không có "
        "ô nào biến đơn hàng thành biến kết quả khẳng định được**. Đơn hàng ở lại đúng chỗ "
        "của nó: thứ cấp/mô tả (PREREGISTRATION §4.2), báo cáo kèm bất định, không dùng để "
        "kết luận.",
    ]
    if min_audience_usable is None:
        out.append(
            "- Không ô nào trong lưới đạt MDE ≤ 30%. Với lưới hiện tại, endpoint đơn hàng "
            "không có kịch bản nào dùng được để kết luận."
        )
    else:
        out.append(
            f"- Ô đầu tiên đạt MDE ≤ 30% cần khoảng **{min_audience_usable:.0f} người xem "
            "đồng thời hiệu dụng** — chỉ với tay tới được qua nhánh đối tác."
        )
    out += [
        "- Đòn bẩy duy nhất có thật là **khán giả**: MDE tỉ lệ với CV Poisson ∝ "
        f"`1/√khán_giả`. Nhân ×{PARTNER_AUDIENCE_MULTIPLIER:g} khán giả của nhánh đối tác "
        f"chia MDE cho ≈ **{PARTNER_AUDIENCE_MULTIPLIER**0.5:.2f}** — đúng bậc, không hơn.",
        f"- Thêm phiên ({SESSIONS_GRID[0]} → {SESSIONS_GRID[-1]}) chỉ chia MDE cho "
        f"√({SESSIONS_GRID[-1]}/{SESSIONS_GRID[0]}) ≈ "
        f"{(SESSIONS_GRID[-1] / SESSIONS_GRID[0]) ** 0.5:.2f}. Không đủ để cứu endpoint này.",
    ]
    return out


def main() -> int:
    _configure_console()
    report = build_report()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report, encoding="utf-8")
    print(f"Đã ghi {OUT.relative_to(ROOT)}")
    print(
        f"  lưới: {len(SESSIONS_GRID)} × {len(AUDIENCE_GRID)} khán giả × {len(Q2_GRID)} q2 "
        "× 2 nhánh"
    )
    print(f"  tỷ lệ nhấp bảng chính: {CLICK_RATE_ANCHOR:.2f}/1000 giây·người xem (GIẢ ĐỊNH)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
