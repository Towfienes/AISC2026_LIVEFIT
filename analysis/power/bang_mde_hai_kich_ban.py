"""Sinh bảng MDE hai kịch bản trung thực (sửa lỗi L2 trong báo cáo nghiên cứu).

Chạy:  python analysis/power/bang_mde_hai_kich_ban.py

Số liệu CV/ICC/autocorr ở đây là GIẢ ĐỊNH ban đầu — quy tắc bất di bất dịch
(kế hoạch §1.4): từ tuần 5 phải thay bằng số đo được từ phiên thăm dò.
"""

from livelift.analysis.power import Scenario, scenario_table

SCENARIOS = [
    # Chỉ chuỗi khẳng định tuần 6-11 (18 phiên) — KHÔNG tính phiên hiệu chỉnh
    Scenario("A: không đối tác (18 phiên tự vận hành)", 18, 90, 5, compliance=0.95),
    # Thêm 10 phiên đối tác 120' ở chế độ đề xuất (compliance đo được, giả định 0.7)
    Scenario("B: có đối tác (+10 phiên 120', chế độ đề xuất)", 28, 90, 5, compliance=0.85),
]

if __name__ == "__main__":
    rows = scenario_table(
        SCENARIOS,
        cv_grid=(0.5, 0.8, 1.2),
        icc_session=0.05,      # đo lại ở tuần 3 (L8)
        resid_autocorr=0.2,    # đo lại ở tuần 3
        burn_in_share=0.2,     # b=1 phút / khối 5 phút
        var_reduction_r2=0.3,  # CUPED/CUPAC kỳ vọng thận trọng
    )
    header = f"{'Kịch bản':45} {'Phiên':>5} {'Khối':>5} {'CV':>4} {'MDE':>7}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['scenario']:45} {r['n_sessions']:>5} {r['n_blocks_total']:>5} "
            f"{r['cv']:>4.1f} {r['mde_relative']:>6.1%}"
        )
