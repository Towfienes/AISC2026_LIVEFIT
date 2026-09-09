"""SRM đợt 1 (gói Q5): kiểm định hai check mới bằng TIÊM LỖI, không bằng ví dụ tay.

Một kiểm tra chất lượng chỉ đáng tin khi ta đo được hai điều: nó IM trên dữ liệu
sạch (A/A) và nó KÊU khi có đúng loại lỗi nó sinh ra để bắt. Harness dưới đây
sinh phiên sạch từ chính simulator + hàm gán production, rồi tiêm:

* mất 10% nhịp telemetry trong khối TẮT  -> `telemetry_delivery` phải bắt được
* dịch chuỗi gán đi một khối             -> `assignment_integrity` phải bắt được

và đo FPR trên 30 phiên A/A sạch.
"""

import random

from livelift.core.assigner.outer import DesignParams, generate_schedule
from livelift.core.features import block_frame, blocks_to_dicts, build_ticks
from livelift.core.quality import (
    SRM_ALPHA,
    TelemetryCounts,
    check_assignment_integrity,
    check_telemetry_counts,
    check_telemetry_delivery,
    run_all,
    telemetry_counts,
)
from livelift.sim.simulator import SimParams, simulate_session

TICK_S = 30
SESSION_MIN = 90
DESIGN = DesignParams()


# --- harness ---------------------------------------------------------------


def clean_session(seed: int, session_min: int = SESSION_MIN):
    """Một phiên sạch: lịch từ hàm gán production + sự kiện từ simulator.

    Trả về (schedule_rows, tick_offsets_s, analysis_rows) — đúng ba thứ mà bộ
    QC sau phiên đọc: `design['blocks']`, mốc `session_tick`, và khung phân
    tích `block_frame`.
    """
    sched = generate_schedule(session_min, DESIGN, seed)
    out = simulate_session(sched, SimParams(), seed)
    ticks = [float(t.bucket_start_s) for t in build_ticks(out.events, session_min * 60, TICK_S)]
    analysis = blocks_to_dicts(block_frame(sched, out.events, burn_in_s=60))
    return sched.to_rows(), ticks, analysis


def heartbeat_ticks(session_min: int = SESSION_MIN) -> list[float]:
    """Nhịp telemetry lý tưởng: một mốc mỗi 30 giây suốt phiên.

    `session_tick` là nhịp ĐỒNG HỒ, nên trên phiên đầy đủ nó đúng bằng lưới
    này — `test_heartbeat_matches_simulator_ticks` khẳng định điều đó thay vì
    để nó thành giả định ngầm. Các vòng quét công suất dùng lưới này để không
    phải chạy simulator hàng nghìn lần cho một đại lượng mà simulator không
    tham gia quyết định.
    """
    return [float(t) for t in range(0, session_min * 60, TICK_S)]


def drop_off_ticks(
    schedule_rows: list[dict], ticks: list[float], share: float, rng: random.Random
) -> list[float]:
    """Tiêm lỗi: bỏ ngẫu nhiên `share` số nhịp rơi vào khối TẮT."""
    off_spans = [
        (r["start_offset_s"], r["end_offset_s"])
        for r in schedule_rows
        if not r["is_washout"] and r["assignment"] == "OFF"
    ]

    def in_off(t: float) -> bool:
        return any(lo <= t < hi for lo, hi in off_spans)

    return [t for t in ticks if not (in_off(t) and rng.random() < share)]


def shift_assignments(rows: list[dict], by: int = 1) -> list[dict]:
    """Tiêm lỗi: xoay chuỗi gán đi `by` khối, giữ nguyên chỉ số khối.

    Đây là hình dạng của một lỗi off-by-one thật (lệch khi ghép lịch với khung
    phân tích), chứ không phải một giá trị bị bôi bẩn ngẫu nhiên."""
    meas = [r for r in rows if not r.get("is_washout") and r.get("assignment") is not None]
    arms = [r["assignment"] for r in meas]
    rotated = arms[by:] + arms[:by]
    replaced = {id(r): a for r, a in zip(meas, rotated, strict=True)}
    return [{**r, "assignment": replaced.get(id(r), r.get("assignment"))} for r in rows]


# --- phiên sạch: cả hai check phải PASS -------------------------------------


def test_clean_session_passes_both_checks():
    rows, ticks, analysis = clean_session(seed=11)
    assert check_assignment_integrity(rows, analysis).passed
    res = check_telemetry_delivery(rows, ticks)
    assert res.passed, res.detail
    assert "kỳ vọng theo thời gian lịch" in res.detail


def test_heartbeat_matches_simulator_ticks():
    """Lối tắt của các vòng quét công suất phải bằng đúng cái simulator sinh ra."""
    _, ticks, _ = clean_session(seed=12)
    assert ticks == heartbeat_ticks()


def test_expected_share_is_not_one_half_because_endpoints_are_doubled():
    """Kỳ vọng phải là TỶ LỆ THỜI GIAN của lịch, không phải 0.5.

    Khối biên dài gấp đôi (quy tắc 2m), nên tùy chuỗi gán mà thời gian BẬT lệch
    khỏi một nửa rõ rệt. Lấy 0.5 làm kỳ vọng sẽ biến lịch hợp lệ thành báo động.
    """
    shares = []
    for seed in range(40):
        rows, ticks, _ = clean_session(seed=seed)
        counts = telemetry_counts(rows, ticks)
        shares.append(counts.expected_on_share)
    assert all(s is not None for s in shares)
    assert any(abs(s - 0.5) > 0.03 for s in shares), (
        "không lịch nào lệch khỏi 0.5 — mốc kiểm tra này mất ý nghĩa"
    )
    # ...và với lịch lệch nhất, dùng 0.5 làm kỳ vọng sẽ cho p-value nhỏ hơn hẳn
    worst_seed = max(range(40), key=lambda s: abs(shares[s] - 0.5))
    rows, ticks, _ = clean_session(seed=worst_seed)
    counts = telemetry_counts(rows, ticks)
    honest = check_telemetry_counts(counts)
    naive = check_telemetry_counts(
        TelemetryCounts(
            n_on=counts.n_on,
            n_off=counts.n_off,
            on_seconds=1.0,
            off_seconds=1.0,
            n_outside=counts.n_outside,
        )
    )
    assert honest.passed
    assert float(honest.detail.split("p = ")[1].split(" ")[0]) > float(
        naive.detail.split("p = ")[1].split(" ")[0]
    )


def test_ticks_outside_measurement_blocks_are_reported_not_dropped():
    """Nhịp ngoài mọi khối đo được ĐẾM RIÊNG (flag-don't-drop), không nhập vào
    kiểm định và cũng không biến mất."""
    rows, ticks, _ = clean_session(seed=13)
    counts = telemetry_counts(rows, [*ticks, -30.0, 999_999.0])
    assert counts.n_outside == 2
    assert counts.n == telemetry_counts(rows, ticks).n


# --- tiêm lỗi 1: mất nhịp telemetry trong khối TẮT --------------------------


def test_gross_tick_outage_is_caught_within_one_session():
    """Ở mức MỘT phiên, kiểm định chỉ đủ nhạy cho sự cố thô — và với sự cố thô
    thì nó phải kêu chắc chắn."""
    rows, ticks, _ = clean_session(seed=21)
    rng = random.Random(0)
    damaged = drop_off_ticks(rows, ticks, share=0.7, rng=rng)
    res = check_telemetry_delivery(rows, damaged)
    assert not res.passed
    assert "bug pipeline HOẶC sự cố telemetry" in res.detail


def test_ten_percent_off_drop_is_invisible_in_a_single_session():
    """Ghi lại giới hạn đã đo: ~180 nhịp/phiên không đủ để thấy mất 10%.

    Đây là lý do `check_telemetry_counts` có đường gộp chuỗi phiên. Test này ở
    lại để nếu ai đó nới α hay đổi mẫu số, sự thay đổi phải là CÓ CHỦ ĐÍCH."""
    rng = random.Random(1)
    caught = 0
    for seed in range(20):
        rows, ticks, _ = clean_session(seed=100 + seed)
        damaged = drop_off_ticks(rows, ticks, share=0.10, rng=rng)
        caught += not check_telemetry_delivery(rows, damaged).passed
    assert caught <= 1, f"{caught}/20 — độ nhạy mỗi-phiên cao hơn dự kiến, xem lại ghi chú"


def test_pooled_series_detects_ten_percent_off_tick_drop_with_power_over_80pct():
    """Công suất ≥ 0.8 khi mất 10% nhịp khối TẮT, gộp trên chuỗi 30 phiên.

    Tốc độ: 50 lần lặp × 30 phiên chạy dưới 1 giây, nên gate này thuộc bộ
    NHANH, không phải bộ `slow`. Nó rẻ được vì nhịp telemetry là lưới đồng hồ
    tất định (`test_heartbeat_matches_simulator_ticks`) — vòng lặp không cần
    simulator, chỉ cần hai nguồn ngẫu nhiên thật sự quan trọng: chuỗi gán và
    việc nhịp nào bị mất. Cả hai đều nhận seed cố định, nên kết quả tất định:
    không có nguy cơ flake khi để ở bộ nhanh.
    """
    reps, n_sessions, drop = 50, 30, 0.10
    rng = random.Random(20260908)
    grid = heartbeat_ticks()
    detected = 0
    for rep in range(reps):
        pooled = TelemetryCounts()
        for s in range(n_sessions):
            sched = generate_schedule(SESSION_MIN, DESIGN, 7000 + rep * 100 + s)
            rows = sched.to_rows()
            pooled = pooled + telemetry_counts(rows, drop_off_ticks(rows, grid, drop, rng))
        detected += not check_telemetry_counts(pooled, scope="chuỗi phiên").passed
    power = detected / reps
    assert power >= 0.80, f"công suất {power:.0%} < 80% khi mất {drop:.0%} nhịp khối TẮT"


def test_pooled_series_is_quiet_on_clean_data():
    """Đối trọng của test trên: cùng quy mô gộp, không tiêm lỗi -> FPR ≈ α."""
    reps, n_sessions = 50, 30
    grid = heartbeat_ticks()
    false_alarms = 0
    for rep in range(reps):
        pooled = TelemetryCounts()
        for s in range(n_sessions):
            sched = generate_schedule(SESSION_MIN, DESIGN, 9000 + rep * 100 + s)
            pooled = pooled + telemetry_counts(sched.to_rows(), grid)
        false_alarms += not check_telemetry_counts(pooled, scope="chuỗi phiên").passed
    assert false_alarms / reps <= 0.05, f"{false_alarms}/{reps} báo động giả trên dữ liệu sạch"


# --- tiêm lỗi 2: dịch lịch một khối ----------------------------------------


def test_shifted_schedule_fails_assignment_integrity():
    rows, _, analysis = clean_session(seed=31)
    res = check_assignment_integrity(shift_assignments(rows, 1), analysis)
    assert not res.passed
    assert "lệch giữa" in res.detail
    assert "bug pipeline HOẶC sự cố telemetry" in res.detail


def test_shifted_analysis_frame_fails_too():
    """Lệch ở phía nào cũng phải bắt được — lỗi off-by-one không có chiều ưu tiên."""
    rows, _, analysis = clean_session(seed=32)
    assert not check_assignment_integrity(rows, shift_assignments(analysis, 1)).passed


def test_missing_block_in_analysis_frame_is_caught():
    rows, _, analysis = clean_session(seed=33)
    res = check_assignment_integrity(rows, analysis[:-1])
    assert not res.passed
    assert "số khối đo lệch" in res.detail


def test_assignment_event_is_preferred_and_cross_checked():
    """Nguồn ưu tiên là bảng chỉ-ghi-thêm; hai nguồn persist mâu thuẫn = lỗi riêng."""
    rows, _, analysis = clean_session(seed=34)
    events = [
        {
            "block_idx": r["block_index"],
            "assignment": r["assignment"],
            "block_start_s": r["start_offset_s"],
            "block_end_s": r["end_offset_s"],
            "design_hash": "h",
        }
        for r in rows
    ]
    ok = check_assignment_integrity(rows, analysis, events)
    assert ok.passed
    assert "assignment_event" in ok.detail

    tampered_design = shift_assignments(rows, 1)
    clash = check_assignment_integrity(tampered_design, analysis, events)
    assert not clash.passed
    assert "hai nguồn lịch đã lưu mâu thuẫn" in clash.detail


def test_no_persisted_schedule_and_no_frame_are_distinct_failures():
    rows, _, analysis = clean_session(seed=35)
    no_sched = check_assignment_integrity([], analysis)
    no_frame = check_assignment_integrity(rows, None)
    assert not no_sched.passed
    assert not no_frame.passed
    assert no_sched.detail != no_frame.detail
    assert "KHÔNG có lịch gán" in no_sched.detail
    assert "chưa truyền khung phân tích" in no_frame.detail


# --- A/A: 30 phiên sạch, FPR mỗi check <= 5% -------------------------------


def test_aa_thirty_clean_sessions_false_positive_rate_under_5pct():
    """A/A trên 30 phiên sạch: mỗi check được phép sai tối đa 5% số phiên.

    `assignment_integrity` là kiểm tra tất định nên FPR phải bằng 0 tuyệt đối;
    `telemetry_delivery` là kiểm định thống kê ở α = 0.005 nên kỳ vọng ~0.15
    báo động giả trên 30 phiên."""
    n_sessions = 30
    fails = {"assignment_integrity": 0, "telemetry_delivery": 0}
    for seed in range(n_sessions):
        rows, ticks, analysis = clean_session(seed=500 + seed)
        for res in (
            check_assignment_integrity(rows, analysis),
            check_telemetry_delivery(rows, ticks),
        ):
            fails[res.name] += not res.passed
    assert fails["assignment_integrity"] == 0
    for name, n in fails.items():
        assert n / n_sessions <= 0.05, f"{name}: FPR {n}/{n_sessions} > 5%"


def test_alpha_is_the_family_budget():
    assert SRM_ALPHA == 0.005
    assert 10 * SRM_ALPHA <= 0.05


# --- bộ QC sau phiên giờ có 8 mục ------------------------------------------


def test_run_all_includes_the_two_srm_checks():
    rows, ticks, analysis = clean_session(seed=41)
    results = run_all(
        scheduled_blocks=rows,
        recorded_blocks=[
            {
                "block_index": r["block_index"],
                "assignment": r["assignment"],
                "is_washout": r["is_washout"],
            }
            for r in rows
        ],
        tick_timestamps_s=ticks,
        session_duration_s=SESSION_MIN * 60,
        interventions=[],
        scrubbed_texts=["giá bao nhiêu"],
        db_order_total=0,
        platform_report_total=0,
        analysis_blocks=analysis,
    )
    assert len(results) == 8
    names = [r.name for r in results]
    assert "assignment_integrity" in names
    assert "telemetry_delivery" in names
    assert all(r.passed for r in results), [r for r in results if not r.passed]


def test_run_all_without_the_analysis_frame_flags_instead_of_passing_silently():
    """Không truyền khung phân tích thì kiểm tra phải ĐỎ, không được im lặng."""
    rows, ticks, _ = clean_session(seed=42)
    results = run_all(
        scheduled_blocks=rows,
        recorded_blocks=[
            {
                "block_index": r["block_index"],
                "assignment": r["assignment"],
                "is_washout": r["is_washout"],
            }
            for r in rows
        ],
        tick_timestamps_s=ticks,
        session_duration_s=SESSION_MIN * 60,
        interventions=[],
        scrubbed_texts=["giá bao nhiêu"],
        db_order_total=0,
        platform_report_total=0,
    )
    integrity = next(r for r in results if r.name == "assignment_integrity")
    assert not integrity.passed


# --- nguyên tắc: KHÔNG SRM trên đại lượng hậu can thiệp ---------------------


def test_srm_module_exposes_no_post_treatment_check():
    """Chốt bằng test: không có hàm SRM nào trên viewers/comments/clicks.

    Ba đại lượng đó là HẬU CAN THIỆP — nếu can thiệp có tác dụng thì chúng PHẢI
    lệch giữa hai nhánh. Một 'SRM' trên chúng sẽ gắn cờ đỏ đúng lúc thí nghiệm
    thành công. Test này là hàng rào để lần sau không ai thêm vào cho 'đủ bộ'."""
    import inspect

    import livelift.core.quality as q

    forbidden = ("viewer", "comment", "click", "like")
    offenders = [
        n for n in dir(q) if n.startswith("check_") and any(w in n.lower() for w in forbidden)
    ]
    assert not offenders, f"SRM trên đại lượng hậu can thiệp: {offenders}"
    # quy tắc phải nằm trong mã nguồn, không chỉ trong đầu người viết
    assert "TUYỆT ĐỐI KHÔNG chạy SRM" in inspect.getsource(q)
