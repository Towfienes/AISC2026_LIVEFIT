"""Gói P3+P4 — mẫu số nội sinh (tuyến tính hóa tỷ lệ, cổng ICS) và CUPED đa biến.

Hai đường ĐỘ NHẠY, cả hai TẮT mặc định. Vì vậy bộ test này phải trả lời ba câu:

1. Đường mới có ĐÚNG không (công thức khớp một mốc độc lập, không phải khớp
   chính nó)?
2. Bật lên có làm HỎNG tính chính xác của kiểm định ngẫu nhiên hóa không —
   tỷ lệ dương tính giả có còn đúng mức?
3. Không bật thì con số chính có y hệt như trước không?

Câu (2) là câu đắt nhất và là lý do có mấy vòng lặp Monte-Carlo nhanh ở đây:
một hiệp biến hậu-can-thiệp hay một r0 tính lại theo từng redraw sẽ không làm
test nào khác đỏ — nó chỉ lặng lẽ đẩy FPR lên.

Hiệu chỉnh Monte-Carlo đầy đủ (nhiều lần lặp hơn) thuộc test_sim_validation.py.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from fastapi.testclient import TestClient

from livelift.analysis.adjust import (
    COVARIATE_NAMES,
    LOCAL_TZ,
    SPLINE_KNOT_MIN,
    build_deterministic_covariates,
    cuped_adjust_mv,
    delta_var_ratio,
    linearize_ratio,
    observed_ratio,
)
from livelift.analysis.estimators import (
    _redraw_matrix,
    analyze_outer,
    randomization_test,
)
from livelift.analysis.robust import (
    ICS_ALPHA,
    ICS_CLEAR_MESSAGE,
    ICS_FLAGGED_MESSAGE,
    ICS_UNTESTABLE_MESSAGE,
    ics_gate,
)
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.core.assigner.outer import draw_assignments

ALPHA = 0.05
"""Mức ý nghĩa danh nghĩa của kiểm định chính."""

FPR_TOLERANCE = 0.20
"""Trần cho các vòng A/A nhanh ở đây (cùng ngưỡng với
``test_estimators.py::test_null_false_positive_rate_is_nominal_on_short_sessions``).

Vài chục lần lặp không phân biệt được 5% với 8%; chúng chỉ bắt được hỏng THÔ —
đúng thứ một hiệp biến hậu-can-thiệp hay một r0 trôi theo redraw gây ra. Cổng
hiệu chỉnh chính xác là kiểm định nhị thức trong test_sim_validation.py.
"""

BLOCK_S = 300


# ---------------------------------------------------------------------------
# Thế giới tổng hợp
# ---------------------------------------------------------------------------


def _ratio_world(
    n_sessions: int = 6,
    blocks_per: int = 12,
    exposure_lift: float = 0.0,
    click_lift: float = 0.0,
    r_base: float = 0.004,
    seed: int = 0,
):
    """Khối với TỬ SỐ và MẪU SỐ tách rời nhau.

    ``exposure_lift`` chỉ tác động lên viewer-giây (mẫu số); ``click_lift`` chỉ
    tác động lên tỷ lệ nhấp. Số click sinh từ Poisson(rate × exposure), nên khi
    ``click_lift=0`` thì tỷ lệ THẬT bằng nhau ở hai nhánh dù mẫu số lệch —
    đúng cấu hình mà tuyến tính hóa phải chịu được.
    """
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    clicks, exposures, zs, sids, phases = [], [], [], [], []
    for s in range(n_sessions):
        viewers = rng.uniform(30.0, 50.0)
        ph = (["early", "mid", "late"] * blocks_per)[:blocks_per]
        arms, _ = draw_assignments(ph, py_rng)
        for i in range(blocks_per):
            z = 1 if arms[i] == "ON" else 0
            exposure = viewers * 240.0 * (1 + exposure_lift * z) * rng.uniform(0.85, 1.15)
            lam = r_base * (1 + click_lift * z) * exposure
            clicks.append(float(rng.poisson(lam)))
            exposures.append(exposure)
            zs.append(z)
            sids.append(f"s{s}")
            phases.append(ph[i])
    return (
        np.array(clicks),
        np.array(exposures),
        np.array(zs),
        np.array(sids),
        phases,
    )


def _local_hour(ts: datetime) -> float:
    local = ts.astimezone(LOCAL_TZ)
    return local.hour + local.minute / 60.0 + local.second / 3600.0


def _diurnal_world(
    n_sessions: int = 8,
    blocks_per: int = 16,
    amp: float = 0.0,
    tau: float = 0.0,
    noise: float = 1.0,
    seed: int = 0,
):
    """Phiên bắt đầu ở nhiều giờ khác nhau; ``amp`` bơm hiệu ứng GIỜ-TRONG-NGÀY.

    Hiệu ứng này KHÔNG có trong `sim/simulator.py` và cố ý không được thêm vào
    đó: bộ mô phỏng đã hiệu chỉnh theo dữ liệu thật (KuaiLive) và PREREGISTRATION
    §5c ghi rằng ở đó phương sai gần như thuần nhiễu đếm — không hiệp biến nào
    giúp được. Muốn kiểm tra CUPED-mv CÓ hoạt động khi có tín hiệu hệ thống thì
    phải dựng một thế giới có tín hiệu đó, chứ không phải nắn bộ mô phỏng cho
    ra kết quả mình muốn.
    """
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    blocks, ys, zs, sids, phases = [], [], [], [], []
    for s in range(n_sessions):
        hour = 7 + (s * 5) % 15
        start = datetime(2026, 9, 1, tzinfo=UTC) + timedelta(days=s, hours=hour)
        ph = (["early", "mid", "late"] * blocks_per)[:blocks_per]
        arms, _ = draw_assignments(ph, py_rng)
        for i in range(blocks_per):
            z = 1 if arms[i] == "ON" else 0
            s0, s1 = i * BLOCK_S, (i + 1) * BLOCK_S
            block_start = start + timedelta(seconds=s0)
            h = _local_hour(block_start)
            t_min = (s0 + s1) / 2 / 60.0
            signal = amp * (
                np.sin(2 * np.pi * h / 24) + 0.6 * np.cos(2 * np.pi * h / 24) + 0.02 * t_min
            )
            ys.append(5.0 + signal + rng.normal(0, noise) + tau * z)
            zs.append(z)
            sids.append(f"s{s}")
            phases.append(ph[i])
            blocks.append({"start_ts": block_start, "start_offset_s": s0, "end_offset_s": s1})
    return np.array(ys), np.array(zs), np.array(sids), phases, blocks


# ---------------------------------------------------------------------------
# P3.1 — tuyến tính hóa tỷ lệ, r0 CỐ ĐỊNH
# ---------------------------------------------------------------------------


def test_observed_ratio_is_the_pooled_ratio_not_the_mean_of_ratios():
    """r0 = Σclick / Σexposure, KHÔNG phải trung bình của các tỷ lệ khối.

    Hai đại lượng này khác nhau bất cứ khi nào exposure không đều — và exposure
    ở đây rất không đều. Lấy nhầm sẽ làm mean(L) khác 0 và toàn bộ phần sau
    lệch theo.
    """
    clicks = np.array([10.0, 1.0])
    exposures = np.array([1000.0, 10.0])
    assert observed_ratio(clicks, exposures) == pytest.approx(11.0 / 1010.0)
    mean_of_ratios = float(np.mean(clicks / exposures))
    assert observed_ratio(clicks, exposures) != pytest.approx(mean_of_ratios)


def test_observed_ratio_refuses_zero_exposure():
    assert np.isnan(observed_ratio(np.array([1.0, 2.0]), np.zeros(2)))


def test_linearized_outcome_is_centred_at_the_observed_ratio():
    clicks, exposures, _, _, _ = _ratio_world(seed=3)
    lin = linearize_ratio(clicks, exposures, observed_ratio(clicks, exposures))
    assert lin.sum() == pytest.approx(0.0, abs=1e-8 * exposures.sum())
    assert lin.shape == clicks.shape


def test_linearize_ratio_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="cùng độ dài"):
        linearize_ratio(np.ones(3), np.ones(4), 0.5)


def test_r0_and_the_linearized_outcome_are_invariant_across_redraws():
    """QUY ƯỚC TIỀN ĐĂNG KÝ: r0 thuộc về MẪU QUAN SÁT, không thuộc về vector gán.

    Đây là bất biến giữ cho kiểm định ngẫu nhiên hóa còn CHÍNH XÁC: giữa hai
    draw chỉ z được phép động, outcome phải đứng yên. Nếu ai đó "cải tiến" bằng
    cách tính lại r0 trong mỗi redraw thì mọi test khác vẫn xanh còn p-value thì
    sai — nên bất biến này được khẳng định trực tiếp trên chính ma trận redraw
    của production.
    """
    clicks, exposures, _, sids, phases = _ratio_world(seed=5)
    r0 = observed_ratio(clicks, exposures)
    baseline = linearize_ratio(clicks, exposures, r0)

    zmat = _redraw_matrix(sids, phases, n_draws=40, seed=5)
    assert zmat.shape == (40, len(clicks))
    for row in zmat:
        # r0 không nhận z làm tham số; khẳng định lại điều đó ở mức hành vi
        assert observed_ratio(clicks, exposures) == r0
        again = linearize_ratio(clicks, exposures, r0)
        assert np.array_equal(again, baseline), "L đổi theo redraw — r0 đã bị trôi"
        assert row.sum() > 0  # ma trận redraw thật sự thay đổi giữa các draw
    assert len({tuple(row.tolist()) for row in zmat}) > 1


def test_ri_on_the_linearized_outcome_keeps_the_false_positive_rate():
    """SHARP NULL TỔNG HỢP: hiệu ứng click = 0 nhưng hiệu ứng MẪU SỐ = +20%.

    Đây là cấu hình mà biến kết quả tỷ lệ trở nên khó chịu: mẫu số lệch theo
    nhánh nên phương sai của L lệch theo nhánh (heteroskedastic). Thống kê
    studentized sinh ra để chịu đúng chuyện đó; test này khẳng định nó chịu được
    thật, chứ không phải chỉ trên giấy.
    """
    rejects = tested = 0
    for rep in range(40):
        clicks, exposures, z, sids, phases = _ratio_world(
            exposure_lift=0.20, click_lift=0.0, seed=100 + rep
        )
        lin = linearize_ratio(clicks, exposures, observed_ratio(clicks, exposures))
        p, _ = randomization_test(lin, z, sids, phases, n_draws=149, seed=100 + rep)
        if not np.isfinite(p):
            continue
        tested += 1
        rejects += p < ALPHA
    assert tested >= 35, f"quá ít lần lặp kiểm định được ({tested})"
    rate = rejects / tested
    assert rate <= FPR_TOLERANCE, (
        f"tỷ lệ dương tính giả {rate:.1%} trên L khi chỉ mẫu số chịu tác động — "
        f"tuyến tính hóa không giữ được mức ý nghĩa"
    )


# ---------------------------------------------------------------------------
# P3.1 — phương sai delta-method theo cụm (CHỈ MÔ TẢ)
# ---------------------------------------------------------------------------


def test_delta_var_ratio_matches_a_cluster_bootstrap():
    """Mốc độc lập: bootstrap theo CỤM (lấy lại nguyên phiên, có hoàn lại).

    Bootstrap không dùng công thức delta chút nào, nên nó là phép đối chứng
    thật sự chứ không phải viết lại cùng một biểu thức hai lần. Dùng 40 cụm để
    xấp xỉ chuẩn còn hợp lệ — đúng chỗ công thức được kỳ vọng đúng, và cũng là
    lý do docstring nói nó KHÔNG đáng tin ở 18–31 cụm của thí nghiệm này.
    """
    clicks, exposures, _, sids, _ = _ratio_world(n_sessions=40, blocks_per=12, seed=11)
    analytic = delta_var_ratio(clicks, exposures, sids)

    rng = np.random.default_rng(7)
    keys = np.unique(sids)
    rows_of = {k: np.where(sids == k)[0] for k in keys}
    draws = []
    for _ in range(2000):
        picked = rng.choice(keys, size=len(keys), replace=True)
        rows = np.concatenate([rows_of[k] for k in picked])
        draws.append(clicks[rows].sum() / exposures[rows].sum())
    empirical = float(np.var(draws, ddof=1))

    rel = abs(analytic - empirical) / empirical
    assert rel < 0.10, (
        f"phương sai delta {analytic:.4g} lệch {rel:.1%} so với bootstrap cụm "
        f"{empirical:.4g} — công thức (6) cài sai"
    )


def test_delta_var_ratio_refuses_a_single_cluster():
    """Một cụm thì không có phương sai giữa cụm để ước lượng — trả NaN, không 0."""
    clicks, exposures, _, _, _ = _ratio_world(n_sessions=1, seed=13)
    sids = np.array(["s0"] * len(clicks))
    assert np.isnan(delta_var_ratio(clicks, exposures, sids))


def test_delta_var_ratio_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="cùng độ dài"):
        delta_var_ratio(np.ones(3), np.ones(3), np.array(["a", "b"]))


# ---------------------------------------------------------------------------
# P3.2 — đường độ nhạy outcome_mode='linearized' trong analyze_outer
# ---------------------------------------------------------------------------


def test_analyze_outer_linearized_runs_the_whole_pipeline_on_the_linearized_outcome():
    """Đường 'linearized' phải là ĐÚNG pipeline cũ chạy trên L — không phải một
    nhánh code song song. So khớp với việc tự tuyến tính hóa rồi gọi hàm cũ."""
    clicks, exposures, z, sids, phases = _ratio_world(seed=17)
    lin = linearize_ratio(clicks, exposures, observed_ratio(clicks, exposures))

    manual = analyze_outer(lin, z, sids, phases, n_draws=120, seed=17)
    wired = analyze_outer(
        np.zeros_like(lin),  # y bị bỏ qua hoàn toàn ở chế độ này
        z,
        sids,
        phases,
        n_draws=120,
        seed=17,
        outcome_mode="linearized",
        clicks=clicks,
        exposures=exposures,
    )
    assert wired.estimate == pytest.approx(manual.estimate)
    assert wired.p_value == pytest.approx(manual.p_value)
    assert wired.ci_low == pytest.approx(manual.ci_low)
    assert wired.ci_high == pytest.approx(manual.ci_high)
    assert wired.outcome_mode == "linearized"
    assert manual.outcome_mode == "ratio"


def test_analyze_outer_linearized_needs_clicks_and_exposures():
    _, _, z, sids, phases = _ratio_world(seed=19)
    with pytest.raises(ValueError, match="clicks và exposures"):
        analyze_outer(np.zeros(len(z)), z, sids, phases, n_draws=20, outcome_mode="linearized")


def test_analyze_outer_rejects_unknown_sensitivity_modes():
    _, _, z, sids, phases = _ratio_world(seed=21)
    y = np.zeros(len(z))
    with pytest.raises(ValueError, match="outcome_mode"):
        analyze_outer(y, z, sids, phases, n_draws=20, outcome_mode="ratio_v2")
    with pytest.raises(ValueError, match="adjust"):
        analyze_outer(y, z, sids, phases, n_draws=20, adjust="cuped")


def test_analyze_outer_default_path_is_untouched():
    """Con số CHÍNH phải y hệt trước gói P3+P4 — mặc định không được đổi hành vi."""
    y, z, sids, phases, _ = _diurnal_world(amp=1.0, tau=0.6, seed=23)
    base = analyze_outer(y, z, sids, phases, n_draws=120, seed=23)
    explicit = analyze_outer(
        y, z, sids, phases, n_draws=120, seed=23, outcome_mode="ratio", adjust="none"
    )
    assert base == explicit
    assert base.outcome_mode == "ratio"
    assert base.adjust == "none"


# ---------------------------------------------------------------------------
# P3.3 — cổng ICS (mẫu số nội sinh)
# ---------------------------------------------------------------------------


def _gate(exposures, z, sids, phases, seed, n_draws=149):
    def redraw_fn(outcome, arms):
        return randomization_test(outcome, arms, sids, phases, n_draws=n_draws, seed=seed)

    return ics_gate(exposures, z, redraw_fn)


def test_ics_gate_tests_the_denominator_not_the_outcome():
    """Bất biến quan trọng nhất của cổng: nó phải đưa EXPOSURE vào kiểm định.

    Nếu một lần sửa vô tình truyền y (biến kết quả chính) thì cổng vẫn chạy,
    vẫn ra p-value trông hợp lý, và sẽ lặng lẽ trở thành một lần nhìn trộm tác
    động — nên vector truyền vào redraw_fn được chặn và so khớp trực tiếp.
    """
    clicks, exposures, z, sids, phases = _ratio_world(seed=27)
    seen: dict[str, np.ndarray] = {}

    def redraw_fn(outcome, arms):
        seen["outcome"] = np.asarray(outcome).copy()
        seen["z"] = np.asarray(arms).copy()
        return randomization_test(outcome, arms, sids, phases, n_draws=99, seed=27)

    gate = ics_gate(exposures, z, redraw_fn)
    assert np.array_equal(seen["outcome"], exposures)
    assert np.array_equal(seen["z"], z)
    assert gate.n_draws == 99
    assert gate.alpha == ICS_ALPHA
    assert gate.estimate == pytest.approx(exposures[z == 1].mean() - exposures[z == 0].mean())


def test_ics_gate_detects_a_twenty_percent_denominator_effect():
    flagged = 0
    reps = 15
    for rep in range(reps):
        _, exposures, z, sids, phases = _ratio_world(exposure_lift=0.20, seed=500 + rep)
        gate = _gate(exposures, z, sids, phases, 500 + rep)
        flagged += gate.flagged
        if gate.flagged:
            assert gate.message == ICS_FLAGGED_MESSAGE
    assert flagged >= 12, (
        f"cổng chỉ bắt được {flagged}/{reps} lần khi mẫu số lệch 20% — công suất "
        f"quá thấp để đáng tin"
    )


def test_ics_gate_false_positive_rate_stays_at_the_nominal_level():
    flagged = 0
    reps = 30
    for rep in range(reps):
        _, exposures, z, sids, phases = _ratio_world(exposure_lift=0.0, seed=700 + rep)
        gate = _gate(exposures, z, sids, phases, 700 + rep)
        flagged += gate.flagged
        if not gate.flagged:
            assert gate.message == ICS_CLEAR_MESSAGE
            assert "KHÔNG phải bằng chứng" in gate.message
    rate = flagged / reps
    assert rate <= FPR_TOLERANCE, (
        f"cổng gắn cờ {rate:.1%} khi mẫu số KHÔNG chịu tác động — mức danh nghĩa là {ICS_ALPHA:.0%}"
    )


def test_ics_gate_reports_an_untestable_design_instead_of_a_number():
    """Thiết kế một nhánh chỉ có một khối: p là NaN. Cổng phải nói 'không kiểm
    định được', tuyệt đối không gắn cờ dựa trên NaN."""
    exposures = np.array([1000.0, 1100.0, 900.0, 1200.0, 1050.0, 980.0])
    z = np.array([1, 0, 0, 0, 0, 0])
    sids = np.array(["s0"] * 6)
    phases = ["early", "mid", "late"] * 2
    gate = _gate(exposures, z, sids, phases, seed=31, n_draws=60)
    assert np.isnan(gate.p_value)
    assert gate.flagged is False
    assert gate.message == ICS_UNTESTABLE_MESSAGE


def test_ics_gate_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="cùng độ dài"):
        ics_gate(np.ones(4), np.ones(3, dtype=int), lambda y, z: (0.5, np.zeros((1, 3))))


# ---------------------------------------------------------------------------
# P4.5 — hiệp biến TẤT ĐỊNH
# ---------------------------------------------------------------------------


def test_deterministic_covariates_shape_and_basis_values():
    start = datetime(2026, 9, 1, 11, 30, tzinfo=UTC)  # 18:30 giờ Việt Nam
    blocks = [
        {"start_ts": start, "start_offset_s": 0, "end_offset_s": 600},
        {"start_ts": start + timedelta(seconds=6000), "start_offset_s": 6000, "end_offset_s": 6600},
    ]
    x = build_deterministic_covariates(blocks)
    assert x.shape == (2, len(COVARIATE_NAMES)) == (2, 5)

    hour = 18.5
    assert x[0, 0] == pytest.approx(np.sin(2 * np.pi * hour / 24))
    assert x[0, 1] == pytest.approx(np.cos(2 * np.pi * hour / 24))
    # t = phút GIỮA khối
    assert x[0, 2] == pytest.approx(5.0)
    assert x[0, 3] == pytest.approx(25.0)
    assert x[0, 4] == 0.0, "hinge phải tắt trước nút 45 phút"
    assert x[1, 2] == pytest.approx(105.0)
    assert x[1, 4] == pytest.approx((105.0 - SPLINE_KNOT_MIN) ** 2)


def test_deterministic_covariates_use_local_time_not_utc():
    """Giờ-trong-ngày là biến HÀNH VI — nhịp mua sắm theo đồng hồ địa phương.

    UTC+0 lúc 23:00 là 06:00 hôm sau ở Việt Nam; hai giá trị sin/cos phải khác
    nhau rõ rệt, nếu không thì hàm đang đọc UTC.
    """
    ts = datetime(2026, 9, 1, 23, 0, tzinfo=UTC)
    x = build_deterministic_covariates([{"start_ts": ts, "start_offset_s": 0, "end_offset_s": 0}])
    local_hour = ts.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).hour
    assert local_hour == 6
    assert x[0, 0] == pytest.approx(np.sin(2 * np.pi * 6 / 24))
    assert x[0, 0] != pytest.approx(np.sin(2 * np.pi * 23 / 24))


def test_hour_basis_is_continuous_across_midnight():
    """Một cột 'giờ' thô sẽ coi 23:59 và 00:01 cách nhau 24 đơn vị; cặp sin/cos
    thì không. Đây là lý do tồn tại của cặp cơ sở này."""
    late = datetime(2026, 9, 1, 16, 59, tzinfo=UTC)  # 23:59 giờ VN
    early = datetime(2026, 9, 1, 17, 1, tzinfo=UTC)  # 00:01 giờ VN
    x = build_deterministic_covariates(
        [
            {"start_ts": late, "start_offset_s": 0, "end_offset_s": 0},
            {"start_ts": early, "start_offset_s": 0, "end_offset_s": 0},
        ]
    )
    assert np.linalg.norm(x[0, :2] - x[1, :2]) < 0.02


def test_deterministic_covariates_are_invariant_to_the_assignment():
    """§5c: hiệp biến phải cố định tại thời điểm sinh lịch gán.

    Ma trận X không nhận z làm đầu vào, nên bất biến này đúng theo cấu trúc —
    nhưng đó chính là tính chất mà đường CUPED-mv dựa vào để kiểm định ngẫu
    nhiên hóa còn CHÍNH XÁC, nên nó được khẳng định bằng test thay vì bằng lời
    hứa trong docstring. Vẽ lại vector gán bằng đúng cơ chế production và so
    khớp từng bit.
    """
    _, _, sids, phases, blocks = _diurnal_world(amp=1.0, seed=33)
    baseline = build_deterministic_covariates(blocks)
    zmat = _redraw_matrix(sids, phases, n_draws=25, seed=33)
    assert len({tuple(row.tolist()) for row in zmat}) > 1, "redraw không hề đổi"
    for _row in zmat:
        assert np.array_equal(build_deterministic_covariates(blocks), baseline)


def test_deterministic_covariates_refuse_a_naive_start_ts():
    naive = datetime(2026, 9, 1, 11, 30)
    with pytest.raises(ValueError, match="múi giờ"):
        build_deterministic_covariates(
            [{"start_ts": naive, "start_offset_s": 0, "end_offset_s": 300}]
        )


def test_deterministic_covariates_refuse_a_missing_start_ts():
    with pytest.raises(ValueError, match="start_ts"):
        build_deterministic_covariates([{"start_offset_s": 0, "end_offset_s": 300}])


def test_deterministic_covariates_handle_an_empty_schedule():
    x = build_deterministic_covariates([])
    assert x.shape == (0, len(COVARIATE_NAMES))


# ---------------------------------------------------------------------------
# P4.5 — CUPED đa biến
# ---------------------------------------------------------------------------


def test_cuped_mv_cuts_the_standard_error_in_a_diurnal_world():
    y, _, sids, _, blocks = _diurnal_world(amp=2.0, seed=41)
    x = build_deterministic_covariates(blocks)
    res = cuped_adjust_mv(y, x, sids)
    assert res.se_ratio <= 0.90, (
        f"SE chỉ giảm {(1 - res.se_ratio):.1%} dù thế giới có hiệu ứng giờ-trong-ngày rõ"
    )
    assert res.r2_cv > 0.2, "R² ngoài-phiên quá thấp — θ̂ đang khớp nhiễu của phiên"
    assert res.cv_available is True
    assert res.n_sessions == 8
    assert res.lambda_chosen in (0.1, 1.0, 10.0)


def test_cuped_mv_does_nothing_when_there_is_nothing_to_find():
    """PREREGISTRATION §5c: khi phương sai thuần nhiễu đếm thì KHÔNG hiệp biến
    nào giúp được. Hành vi đúng lúc đó là gần như không hiệu chỉnh gì và nói
    thật bằng R² ngoài-phiên ≈ 0, chứ không phải khoe một mức giảm SE trong-mẫu.
    """
    y, _, sids, _, blocks = _diurnal_world(amp=0.0, seed=43)
    x = build_deterministic_covariates(blocks)
    res = cuped_adjust_mv(y, x, sids)
    assert res.se_ratio > 0.95, "hiệu chỉnh 'giảm' phương sai trên thế giới không có tín hiệu"
    assert res.r2_cv < 0.10
    assert res.lambda_chosen == 10.0, "không có tín hiệu thì CV phải chọn co nhiều nhất"
    assert res.r2_in_sample > res.r2_cv, "R² trong-mẫu luôn lạc quan hơn — phải báo cả hai"


def test_cuped_mv_theta_is_stable_across_folds():
    """θ̂ chỉ có nghĩa nếu nó không nhảy khi bỏ đi một phiên.

    So sánh trên PHẦN DỰ ĐOÁN chứ không trên từng thành phần θ: các cột có thang
    đo lệch nhau hàng nghìn lần (phút vs phút²), nên độ lệch tương đối theo từng
    thành phần đo chủ yếu là thang đo, không phải độ ổn định.
    """
    for seed in (45, 46):
        y, _, sids, _, blocks = _diurnal_world(amp=2.0, seed=seed)
        x = build_deterministic_covariates(blocks)
        res = cuped_adjust_mv(y, x, sids)
        assert len(res.fold_thetas) == res.n_sessions
        xc = x - x.mean(axis=0)
        full = xc @ res.theta
        for theta_fold in res.fold_thetas:
            fold = xc @ theta_fold
            dev = np.linalg.norm(fold - full) / np.linalg.norm(full)
            assert dev < 0.25, f"θ̂ lệch {dev:.1%} khi bỏ một phiên (seed={seed})"
            assert np.corrcoef(fold, full)[0, 1] > 0.98


def test_cuped_mv_preserves_the_sample_mean():
    y, _, sids, _, blocks = _diurnal_world(amp=2.0, seed=47)
    x = build_deterministic_covariates(blocks)
    res = cuped_adjust_mv(y, x, sids)
    assert res.y_adj.mean() == pytest.approx(y.mean())


def test_cuped_mv_without_two_sessions_falls_back_to_most_shrinkage():
    """Một phiên thì không có fold nào để giữ lại; chọn λ theo khớp trong-mẫu sẽ
    luôn ra λ nhỏ nhất, tức hiệu chỉnh nhiều nhất, đúng lúc ít bằng chứng nhất."""
    y, _, _, _, blocks = _diurnal_world(n_sessions=1, amp=2.0, seed=49)
    x = build_deterministic_covariates(blocks)
    res = cuped_adjust_mv(y, x, np.array(["s0"] * len(y)))
    assert res.cv_available is False
    assert res.lambda_chosen == 10.0
    assert np.isnan(res.r2_cv)
    assert res.fold_thetas == ()


def test_cuped_mv_rejects_ragged_inputs():
    y, _, sids, _, blocks = _diurnal_world(amp=1.0, seed=51)
    x = build_deterministic_covariates(blocks)
    with pytest.raises(ValueError, match="cùng số hàng"):
        cuped_adjust_mv(y[:-1], x, sids)
    with pytest.raises(ValueError, match="λ"):
        cuped_adjust_mv(y, x, sids, ridge_lambdas=())


def test_aa_false_positive_rate_holds_under_cuped_mv():
    """A/A: bật CUPED-mv KHÔNG được làm hỏng mức ý nghĩa.

    Đây là test đắt nhất trong file và là lý do cả gói P4 dừng ở hiệp biến TẤT
    ĐỊNH. Một hiệp biến hậu-can-thiệp (lag trong-phiên) sẽ giảm SE đẹp hơn hẳn
    và không làm test nào khác đỏ — nó chỉ hiện ra ở đây, dưới dạng FPR trôi lên.
    """
    rejects = tested = 0
    for rep in range(50):
        y, z, sids, phases, blocks = _diurnal_world(amp=2.0, tau=0.0, seed=900 + rep)
        x = build_deterministic_covariates(blocks)
        adjusted = cuped_adjust_mv(y, x, sids).y_adj
        p, _ = randomization_test(adjusted, z, sids, phases, n_draws=149, seed=900 + rep)
        if not np.isfinite(p):
            continue
        tested += 1
        rejects += p < ALPHA
    assert tested >= 45, f"quá ít lần lặp kiểm định được ({tested})"
    rate = rejects / tested
    assert rate <= FPR_TOLERANCE, (
        f"tỷ lệ dương tính giả {rate:.1%} sau hiệu chỉnh CUPED đa biến — "
        f"hiệu chỉnh đã phá tính chính xác của kiểm định"
    )


# ---------------------------------------------------------------------------
# P4.6 — đường độ nhạy adjust='cuped_mv' trong analyze_outer
# ---------------------------------------------------------------------------


def test_analyze_outer_cuped_mv_matches_manual_adjustment():
    y, z, sids, phases, blocks = _diurnal_world(amp=2.0, tau=0.0, seed=53)
    x = build_deterministic_covariates(blocks)
    adjusted = cuped_adjust_mv(y, x, sids).y_adj

    manual = analyze_outer(adjusted, z, sids, phases, n_draws=120, seed=53)
    wired = analyze_outer(y, z, sids, phases, n_draws=120, seed=53, adjust="cuped_mv", covariates=x)
    assert wired.estimate == pytest.approx(manual.estimate)
    assert wired.p_value == pytest.approx(manual.p_value)
    assert wired.adjust == "cuped_mv"
    assert manual.adjust == "none"


def test_analyze_outer_cuped_mv_needs_covariates():
    y, z, sids, phases, _ = _diurnal_world(amp=1.0, seed=55)
    with pytest.raises(ValueError, match="covariates"):
        analyze_outer(y, z, sids, phases, n_draws=20, adjust="cuped_mv")


def test_analyze_outer_can_combine_linearization_and_adjustment():
    """Hai đường độ nhạy phải xếp chồng được: tuyến tính hóa TRƯỚC, hiệu chỉnh
    SAU — hiệu chỉnh tác động lên biến kết quả đang thực sự được kiểm định."""
    clicks, exposures, z, sids, phases = _ratio_world(seed=57)
    x = np.column_stack([np.arange(len(z), dtype=float), np.ones(len(z))])
    lin = linearize_ratio(clicks, exposures, observed_ratio(clicks, exposures))
    adjusted = cuped_adjust_mv(lin, x, sids).y_adj

    manual = analyze_outer(adjusted, z, sids, phases, n_draws=100, seed=57)
    wired = analyze_outer(
        np.zeros(len(z)),
        z,
        sids,
        phases,
        n_draws=100,
        seed=57,
        outcome_mode="linearized",
        clicks=clicks,
        exposures=exposures,
        adjust="cuped_mv",
        covariates=x,
    )
    assert wired.estimate == pytest.approx(manual.estimate)
    assert wired.outcome_mode == "linearized"
    assert wired.adjust == "cuped_mv"


# ---------------------------------------------------------------------------
# P3.3 — cờ mẫu số trong /experiment/summary
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


def _freeze(client, monkeypatch, value: str):
    from livelift.config import get_settings

    monkeypatch.setenv("RESULTS_FREEZE_UNTIL", value)
    get_settings.cache_clear()
    try:
        return client.get("/experiment/summary").json()
    finally:
        monkeypatch.delenv("RESULTS_FREEZE_UNTIL", raising=False)
        get_settings.cache_clear()


def test_summary_carries_the_denominator_flag(client):
    from livelift.api.routes.reports import ICS_DRAWS

    client.post("/demo/seed", json={"n_sessions": 3, "effect": 0.5, "duration_min": 40})
    summary = client.get("/experiment/summary").json()

    check = summary["denominator_check"]
    assert check is not None, "gói P3: /experiment/summary phải mang cờ mẫu số"
    assert check["n_draws"] == ICS_DRAWS
    assert 0.0 < check["p_value"] <= 1.0
    # Cờ phải khớp p-value của chính nó — một cờ trôi khỏi p là cờ vô nghĩa
    assert check["flagged"] == (check["p_value"] < ICS_ALPHA)
    assert check["note"]
    # Nó là ghi chú PHƯƠNG PHÁP, không phải suy diễn chính: không có KTC, và
    # con số chính vẫn được phục vụ bình thường bên cạnh.
    assert set(check) == {"p_value", "flagged", "n_draws", "estimate", "note"}
    assert summary["estimate"] is not None


def test_summary_withholds_the_denominator_flag_before_the_freeze_date(client, monkeypatch):
    """§7: viewer-giây là đại lượng HẬU CAN THIỆP.

    Biết được can thiệp có làm đổi mẫu số hay không đã là biết một phần tác
    động của can thiệp, nên cổng này bị khóa cùng với ước lượng hiệu ứng thay vì
    được phục vụ như số vận hành thuần túy.
    """
    client.post("/demo/seed", json={"n_sessions": 3, "effect": 0.5, "duration_min": 40})
    summary = _freeze(client, monkeypatch, "2999-01-01")

    assert summary["estimable"] is False
    check = summary["denominator_check"]
    assert check["p_value"] is None
    assert check["flagged"] is False
    assert check["n_draws"] == 0
    assert "§7" in check["note"]
