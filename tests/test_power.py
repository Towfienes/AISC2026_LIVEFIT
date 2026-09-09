"""MDE calculator: base formula, the corrections that apply, and — most
importantly — a check that the predicted MDE matches the power the estimator
actually achieves on simulated data.

Audit 30/08 removed two corrections that did not belong to a within-session
switchback (Moulton cluster design effect; AR(1) mean-inflation factor) and
switched the CV to a within-session one. Those removals make the MDE SMALLER,
which is exactly the direction where a mistake would flatter the project — so
the calibration test below is the one that matters.
"""

import numpy as np
import pytest

from livelift.analysis.power import (
    PowerInputs,
    Scenario,
    blocks_in_session,
    mde_relative,
    scenario_table,
    within_session_cv,
)


def base(cv, n, **kw):
    defaults = {
        "cv": cv,
        "n_blocks_total": n,
        "n_sessions": 30,
        "compliance": 1.0,
        "burn_in_share": 0.0,
        "var_reduction_r2": 0.0,
        # The plan's published rows are the RAW closed-form values; the
        # measured randomization-test margin is checked separately.
        "randomization_margin": 1.0,
    }
    defaults.update(kw)
    return PowerInputs(**defaults)


# --- base formula ----------------------------------------------------------


def test_reproduces_plan_base_case():
    """Plan doc §7.2: 650 blocks total (325/arm), CV=0.5 -> MDE ≈ 11%."""
    assert mde_relative(base(cv=0.5, n=650)) == pytest.approx(0.11, abs=0.01)


def test_reproduces_plan_cv08_row():
    assert mde_relative(base(cv=0.8, n=650)) == pytest.approx(0.176, abs=0.015)


def test_mde_scales_as_inverse_sqrt_n():
    a = mde_relative(base(0.6, 200))
    b = mde_relative(base(0.6, 800))
    assert a / b == pytest.approx(2.0, rel=0.01)


def test_degenerate_inputs():
    assert mde_relative(base(0.5, 2)) == float("inf")
    assert mde_relative(base(float("nan"), 650)) == float("inf")


# --- corrections that DO apply --------------------------------------------


def test_compliance_dilution_inflates_mde():
    full = mde_relative(base(0.5, 650))
    diluted = mde_relative(base(0.5, 650, compliance=0.5))
    assert diluted == pytest.approx(full * 2, rel=0.01)


def test_variance_reduction_shrinks_mde():
    plain = mde_relative(base(0.5, 650))
    cupac = mde_relative(base(0.5, 650, var_reduction_r2=0.36))
    assert cupac == pytest.approx(plain * 0.8, rel=0.01)


def test_burn_in_share_inflates_mde():
    plain = mde_relative(base(0.5, 650))
    burned = mde_relative(base(0.5, 650, burn_in_share=0.2))
    assert burned > plain


# --- corrections that DO NOT apply to a within-session switchback ----------


def test_session_icc_is_ignored_by_default():
    """The Moulton cluster design effect is for CLUSTER-level assignment. Here
    treatment alternates INSIDE the session, so the session effect differences
    out of the ON-OFF contrast (audit 30/08)."""
    without = mde_relative(base(0.5, 650))
    with_icc = mde_relative(base(0.5, 650, icc_session=0.2))
    assert with_icc == pytest.approx(without, rel=1e-12)


def test_session_icc_applies_when_the_session_itself_is_randomized():
    """Kept available for a hypothetical session-level-assignment arm."""
    plain = mde_relative(base(0.5, 650, n_sessions=30))
    clustered = mde_relative(
        base(0.5, 650, n_sessions=30, icc_session=0.1, session_level_assignment=True)
    )
    m = 650 / 30
    assert clustered / plain == pytest.approx((1 + (m - 1) * 0.1) ** 0.5, rel=0.02)


def test_no_serial_correlation_penalty_by_default():
    """The AR(1) mean-inflation factor is the wrong correction for a contrast
    between interleaved randomized blocks — and has the wrong SIGN, since
    positive autocorrelation makes the two arm means move together."""
    assert mde_relative(base(0.5, 650)) == pytest.approx(
        mde_relative(base(0.5, 650, serial_factor=1.0)), rel=1e-12
    )


def test_serial_factor_is_still_available_when_derived():
    inflated = mde_relative(base(0.5, 650, serial_factor=1.44))
    assert inflated == pytest.approx(mde_relative(base(0.5, 650)) * 1.2, rel=0.01)


# --- within-session CV -----------------------------------------------------


def test_within_session_cv_excludes_between_session_variance():
    """Pooled CV would charge the design for session-level variance that the
    within-session analysis differences away."""
    rng = np.random.default_rng(0)
    ys, sids = [], []
    for s in range(10):
        level = 10.0 + 5.0 * s  # huge between-session spread
        for _ in range(20):
            ys.append(level + rng.normal(0, 1.0))
            sids.append(f"s{s}")
    y, sess = np.array(ys), np.array(sids)

    pooled = y.std(ddof=1) / y.mean()
    within = within_session_cv(y, sess)
    assert within < pooled / 3
    # within-session sd is ~1.0 against a grand mean of ~32.5
    assert within == pytest.approx(1.0 / y.mean(), rel=0.15)


def test_within_session_cv_degenerate():
    y = np.array([1.0, 2.0])
    sess = np.array(["a", "b"])
    assert not np.isfinite(within_session_cv(y, sess))


# --- table -----------------------------------------------------------------


def test_blocks_in_session_endpoint_double():
    assert blocks_in_session(90, 5, True) == 16
    assert blocks_in_session(90, 5, False) == 18


def test_scenario_table_two_honest_scenarios():
    rows = scenario_table(
        [
            Scenario("không đối tác (tuần 6-11)", n_sessions=18, session_minutes=90, block_min=5),
            Scenario("có đối tác", n_sessions=28, session_minutes=90, block_min=5),
        ]
    )
    assert len(rows) == 6  # 2 scenarios × 3 CVs
    no_partner = [r for r in rows if r["scenario"].startswith("không")]
    partner = [r for r in rows if r["scenario"].startswith("có")]
    for a, b in zip(no_partner, partner, strict=True):
        assert a["mde_relative"] > b["mde_relative"]  # more data -> smaller MDE
    assert all(r["n_blocks_total"] == r["blocks_per_session"] * r["n_sessions"] for r in rows)


# --- the test that actually matters ---------------------------------------


def test_randomization_margin_is_applied_by_default():
    """The reported MDE must carry the measured randomization-test margin —
    publishing the raw closed-form number would overstate what the design can
    detect (audit 30/08)."""
    from livelift.analysis.power import RANDOMIZATION_TEST_MARGIN

    raw = mde_relative(base(0.5, 650))  # helper pins margin to 1.0
    reported = mde_relative(PowerInputs(cv=0.5, n_blocks_total=650, n_sessions=30, compliance=1.0))
    assert RANDOMIZATION_TEST_MARGIN > 1.0
    assert reported == pytest.approx(raw * RANDOMIZATION_TEST_MARGIN, rel=1e-9)


@pytest.mark.slow
def test_predicted_mde_matches_achieved_power():
    """Calibration: an effect at the predicted MDE should be detected close to
    the nominal 80% of the time.

    This is the guard against a self-flattering formula. Removing corrections
    makes the MDE smaller; if the removal were wrong, the achieved power at
    that effect size would fall well below 80% and this test would fail.
    """
    from livelift.analysis.estimators import analyze_outer
    from livelift.core.assigner.outer import DesignParams, generate_schedule
    from livelift.core.features import block_frame, blocks_to_dicts
    from livelift.sim.simulator import SimParams, simulate_session

    n_sessions, reps = 8, 40
    design = DesignParams()

    # 1) measure the within-session CV under the null
    ys, sids = [], []
    for s in range(n_sessions):
        sched = generate_schedule(90, design, 900 + s)
        out = simulate_session(sched, SimParams(treatment_effect=0.0), 900 + s)
        for r in blocks_to_dicts(block_frame(sched, out.events, burn_in_s=60)):
            if r["measurable"]:
                ys.append(r["y"])
                sids.append(f"s{s}")
    cv = within_session_cv(np.array(ys), np.array(sids))
    n_blocks = len(ys)
    assert np.isfinite(cv)

    predicted = mde_relative(
        PowerInputs(cv=cv, n_blocks_total=n_blocks, n_sessions=n_sessions, compliance=1.0)
    )
    assert 0.0 < predicted < 2.0, f"MDE dự đoán bất thường: {predicted}"

    # 2) run the estimator at exactly that effect size
    detected = tested = 0
    for rep in range(reps):
        ys, zs, sids, phases = [], [], [], []
        for s in range(n_sessions):
            seed = 5000 + rep * 50 + s
            sched = generate_schedule(90, design, seed)
            out = simulate_session(sched, SimParams(treatment_effect=predicted), seed)
            for r in blocks_to_dicts(block_frame(sched, out.events, burn_in_s=60)):
                if not r["measurable"]:
                    continue
                ys.append(r["y"])
                zs.append(r["z"])
                sids.append(f"s{s}")
                phases.append(r["phase"])
        res = analyze_outer(
            np.array(ys), np.array(zs), np.array(sids), phases, n_draws=299, seed=rep
        )
        if not res.estimable:
            continue
        tested += 1
        detected += res.significant

    power = detected / max(tested, 1)
    assert tested >= reps * 0.8, f"quá nhiều lần không ước lượng được ({tested}/{reps})"
    # Wide band: 40 reps give a ±13pp Monte-Carlo margin at p=0.8. The point is
    # to catch a formula that is wrong by a FACTOR, not to pin 80% exactly.
    assert 0.65 <= power <= 0.99, (
        f"lực thống kê thực tế {power:.0%} tại MDE dự đoán {predicted:.1%} — "
        "công thức MDE lệch khỏi lực thống kê thật"
    )


# --- irreducible noise (method review 02/09) -------------------------------


def test_poisson_floor_detects_pure_counting_noise():
    """When clicks ARE Poisson, the reducible share must be ~0 — the signal
    that covariate adjustment cannot help and the fix has to be the design."""
    from livelift.analysis.power import poisson_floor

    rng = np.random.default_rng(0)
    n = 400
    exposure = np.full(n, 5000.0)  # identical exposure -> no systematic spread
    clicks = rng.poisson(10.0, n).astype(float)
    y = 1000.0 * clicks / exposure
    sids = np.array([f"s{i // 20}" for i in range(n)])

    cv_floor, reducible = poisson_floor(y, clicks, exposure, sids)
    assert 0.2 < cv_floor < 0.5
    assert abs(reducible) < 0.25, f"reducible share {reducible:.2f} — kỳ vọng ~0"


def test_poisson_floor_detects_reducible_structure():
    """With a strong systematic component on top of counting noise, the
    reducible share must be clearly positive."""
    from livelift.analysis.power import poisson_floor

    rng = np.random.default_rng(1)
    n = 400
    exposure = np.full(n, 5000.0)
    base = np.where(np.arange(n) % 2 == 0, 4.0, 30.0)  # big systematic swing
    clicks = rng.poisson(base).astype(float)
    y = 1000.0 * clicks / exposure
    sids = np.array([f"s{i // 20}" for i in range(n)])

    _, reducible = poisson_floor(y, clicks, exposure, sids)
    assert reducible > 0.5, f"reducible share {reducible:.2f} — kỳ vọng lớn"


def test_poisson_floor_degenerate():
    from livelift.analysis.power import poisson_floor

    z = np.array([0.0])
    assert not np.isfinite(poisson_floor(z, z, z, np.array(["a"]))[0])


# --- MDE trên số ĐƠN HÀNG (gói Q4) -----------------------------------------


ANCHOR_AUDIENCE = 15.0
ANCHOR_SESSION_MIN = 90
ANCHOR_ORDERS_LO, ANCHOR_ORDERS_HI = 0.3, 0.6
"""Mốc tỉnh táo của agenda Q4: 15 người xem × 90 phút → 0,3–0,6 đơn/phiên."""


def _anchor_exposure(burn_in: bool = True) -> float:
    from livelift.analysis.power import analysis_window_seconds

    if burn_in:
        return ANCHOR_AUDIENCE * sum(analysis_window_seconds(ANCHOR_SESSION_MIN, 5, True, 60))
    return ANCHOR_AUDIENCE * ANCHOR_SESSION_MIN * 60


def test_funnel_prior_multiplies_to_the_documented_overall_rate():
    """9,33% × 24,33% ≈ 2,3% — cùng con số đã dán nhãn trong báo cáo."""
    from livelift.analysis.power import FUNNEL_CART_TO_BUY, FUNNEL_PV_TO_CART

    assert pytest.approx(0.0227, abs=0.0005) == FUNNEL_PV_TO_CART * FUNNEL_CART_TO_BUY


def test_poisson_cv_agrees_with_poisson_floor_measured_on_data():
    """`poisson_cv` (từ λ giả định) và `poisson_floor` (từ click quan sát) phải
    là CÙNG một đại lượng — nếu không, bảng đơn hàng và bảng click sẽ nói hai
    thứ khác nhau về cùng một thiết kế."""
    from livelift.analysis.power import poisson_cv, poisson_floor

    rng = np.random.default_rng(3)
    n, lam, exposure = 600, 9.0, 5000.0
    clicks = rng.poisson(lam, n).astype(float)
    y = 1000.0 * clicks / exposure
    sids = np.array([f"s{i // 20}" for i in range(n)])

    measured, _ = poisson_floor(y, clicks, np.full(n, exposure), sids)
    assumed = poisson_cv([lam] * n)
    assert measured == pytest.approx(assumed, rel=0.05)


def test_analysis_window_matches_block_frame_burn_in_rule():
    """Cửa sổ dùng để tính λ phải đúng bằng cửa sổ `block_frame` thật sự đo."""
    from livelift.analysis.power import analysis_window_seconds
    from livelift.core.assigner.outer import DesignParams, generate_schedule

    sched = generate_schedule(90, DesignParams(), 4)
    burn_in = 60
    real = sorted(
        b.duration_s - min(burn_in, max(b.duration_s - 30, 0)) for b in sched.measurement_blocks
    )
    # jitter xê dịch ranh giới ±30s nên chỉ so TỔNG và số khối, không so từng khối
    modelled = sorted(analysis_window_seconds(90, 5, True, burn_in))
    assert len(modelled) == len(real)
    assert sum(modelled) == pytest.approx(sum(real), rel=0.02)


def test_order_sanity_anchor_matches_the_existing_click_machinery():
    """Mốc tỉnh táo: 15 người xem × 90 phút phải cho 0,3–0,6 đơn/phiên ở một
    tỷ lệ nhấp CÙNG BẬC với machinery click hiện có.

    `SimParams.base_click_prob_per_min = 0,06`/người xem·phút ⇔ 1,00 click /
    1000 giây·người xem. Mốc 0,3–0,6 đơn/phiên ứng với tỷ lệ nhấp 0,2–0,4 —
    thấp hơn tham số mô phỏng 2,5–5 lần, tức CÙNG BẬC nhưng KHÔNG trùng. Test
    này khẳng định cả hai vế thay vì làm tròn cho khớp: tham số mô phỏng đó
    được đánh dấu là GIẢ ĐỊNH và chỉ phiên thăm dò mới chốt được.
    """
    from livelift.analysis.power import expected_orders
    from livelift.sim.simulator import SimParams

    sim_rate_per_1000vs = SimParams().base_click_prob_per_min / 60.0 * 1000.0
    assert sim_rate_per_1000vs == pytest.approx(1.0, rel=1e-9)

    exposure = _anchor_exposure()
    lo_rate = ANCHOR_ORDERS_LO / expected_orders(1.0, exposure)
    hi_rate = ANCHOR_ORDERS_HI / expected_orders(1.0, exposure)
    assert 0.15 < lo_rate < hi_rate < 0.5, (lo_rate, hi_rate)

    # cùng bậc độ lớn với machinery hiện có (trong vòng một bậc 10)
    assert lo_rate / sim_rate_per_1000vs > 0.1
    assert hi_rate / sim_rate_per_1000vs < 10.0

    # và ở tỷ lệ nhấp neo của báo cáo, số đơn rơi đúng vào dải mốc
    orders = expected_orders(0.30, exposure)
    assert ANCHOR_ORDERS_LO <= orders <= ANCHOR_ORDERS_HI, orders


def test_order_mde_table_shape_and_monotonicity():
    from livelift.analysis.power import PARTNER_AUDIENCE_MULTIPLIER, Q2_GRID, order_mde_table

    rows = order_mde_table(0.30, (18, 28), (15.0, 150.0), Q2_GRID)
    assert len(rows) == 2 * 2 * len(Q2_GRID) * 2  # phiên × khán giả × q2 × nhánh

    by_key = {(r["branch"], r["n_sessions"], r["audience"], r["q2"]): r for r in rows}
    partner = next(b for b in {r["branch"] for r in rows} if b.startswith("có"))
    solo = next(b for b in {r["branch"] for r in rows} if b.startswith("không"))

    # nhiều phiên hơn -> MDE nhỏ hơn
    assert (
        by_key[(solo, 28, 15.0, 0.25)]["mde_relative"]
        < by_key[(solo, 18, 15.0, 0.25)]["mde_relative"]
    )
    # khán giả lớn hơn -> MDE nhỏ hơn
    assert (
        by_key[(solo, 18, 150.0, 0.25)]["mde_relative"]
        < by_key[(solo, 18, 15.0, 0.25)]["mde_relative"]
    )
    # q2 cao hơn -> nhiều đơn hơn -> MDE nhỏ hơn
    assert (
        by_key[(solo, 18, 15.0, 0.50)]["mde_relative"]
        < by_key[(solo, 18, 15.0, 0.15)]["mde_relative"]
    )
    # nhánh đối tác: khán giả ×4.9 -> MDE chia cho ≈ √4.9
    solo_row = by_key[(solo, 18, 15.0, 0.25)]
    partner_row = by_key[(partner, 18, 15.0, 0.25)]
    assert partner_row["audience_effective"] == pytest.approx(
        solo_row["audience_effective"] * PARTNER_AUDIENCE_MULTIPLIER
    )
    assert solo_row["mde_relative"] / partner_row["mde_relative"] == pytest.approx(
        PARTNER_AUDIENCE_MULTIPLIER**0.5, rel=0.02
    )


def test_order_mde_is_a_floor_never_smaller_than_the_click_mde_at_equal_n():
    """Đơn hiếm hơn click đúng bằng hệ số phễu, nên MDE đơn PHẢI lớn hơn MDE
    click trên cùng số khối — một bảng cho ra ngược lại là bảng sai."""
    from livelift.analysis.power import (
        FUNNEL_CART_TO_BUY,
        FUNNEL_PV_TO_CART,
        order_mde_table,
        poisson_cv,
    )

    exposure_per_block = 15.0 * 240.0
    click_lam = 0.30 * exposure_per_block / 1000.0
    order_row = order_mde_table(0.30, (18,), (15.0,), (FUNNEL_CART_TO_BUY,), include_partner=False)[
        0
    ]
    click_mde = mde_relative(
        PowerInputs(
            cv=poisson_cv([click_lam] * order_row["n_blocks_total"]),
            n_blocks_total=order_row["n_blocks_total"],
            n_sessions=18,
            compliance=0.95,
        )
    )
    assert order_row["mde_relative"] > click_mde
    ratio = order_row["mde_relative"] / click_mde
    assert ratio == pytest.approx((FUNNEL_PV_TO_CART * FUNNEL_CART_TO_BUY) ** -0.5, rel=0.15)


def test_order_mde_table_reports_a_zero_lambda_cell_as_infinite():
    """Khán giả 0 → không đơn nào → MDE vô hạn, không phải một con số đẹp."""
    from livelift.analysis.power import order_mde_table

    row = order_mde_table(0.30, (18,), (0.0,), (0.25,), include_partner=False)[0]
    assert not np.isfinite(row["cv_poisson"])
    assert not np.isfinite(row["mde_relative"])
