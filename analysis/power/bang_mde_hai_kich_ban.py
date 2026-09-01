"""Sinh bảng MDE hai kịch bản trung thực (sửa lỗi L2 trong báo cáo nghiên cứu).

Chạy:  python analysis/power/bang_mde_hai_kich_ban.py

QUAN TRỌNG — các con số CV ở đây là GIẢ ĐỊNH ban đầu để lập kế hoạch.
Quy tắc bất di bất dịch (kế hoạch §1.4): từ tuần 5 phải thay bằng CV
**trong-phiên** đo được từ phiên thăm dò (`within_session_cv`), lấy qua
`GET /experiment/summary` → `measured_cv`.

Không truyền `var_reduction_r2` ở đây: không đoạn code nào trong dự án ước
lượng R² của CUPED, và rà soát phương pháp 02/09 đo được phần phương sai
GIẢM ĐƯỢC gần bằng 0 (biến kết quả gần như thuần nhiễu đếm). Giả định một
mức R² sẽ cắt MDE dựa trên hư không — xem `poisson_floor()`.
"""

from livelift.analysis.power import Scenario, scenario_table
from livelift.console import configure as _configure_console

SCENARIOS = [
    # Chỉ chuỗi khẳng định tuần 6-11 (18 phiên) — KHÔNG tính phiên hiệu chỉnh
    Scenario("A: không đối tác (18 phiên tự vận hành)", 18, 90, 5, compliance=0.95),
    # Thêm 10 phiên đối tác 120' ở chế độ đề xuất (compliance đo được, giả định 0.85)
    Scenario("B: có đối tác (+10 phiên 120', chế độ đề xuất)", 28, 90, 5, compliance=0.85),
]

if __name__ == "__main__":
    _configure_console()
    rows = scenario_table(SCENARIOS, cv_grid=(0.5, 0.8, 1.2))
    header = f"{'Kịch bản':45} {'Phiên':>5} {'Khối':>5} {'CV':>4} {'MDE':>7}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['scenario']:45} {r['n_sessions']:>5} {r['n_blocks_total']:>5} "
            f"{r['cv']:>4.1f} {r['mde_relative']:>6.1%}"
        )
    print()
    print("MDE đã bao gồm biên độ đo được của kiểm định ngẫu nhiên hóa")
    print("(RANDOMIZATION_TEST_MARGIN — xem docstring của livelift.analysis.power).")
