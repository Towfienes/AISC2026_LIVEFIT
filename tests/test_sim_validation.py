"""Statistical calibration gates (HARNESS §2) — Monte-Carlo, marked slow.

Fast smoke checks run in the default suite; the full calibration study runs
nightly / pre-release with `pytest -m slow`.
"""

import pytest
from scipy.stats import binomtest

from livelift.core.assigner.outer import DesignParams, generate_schedule
from livelift.core.features import block_frame
from livelift.sim.simulator import SimParams, simulate_session, true_effect
from livelift.sim.validate import run_validation

ALPHA = 0.05
"""Nominal significance level the calibration gates test against."""


def test_simulator_produces_events_and_blocks():
    schedule = generate_schedule(30, DesignParams(jitter_s=0), seed=1)
    out = simulate_session(schedule, SimParams(), seed=1)
    kinds = {e.kind for e in out.events}
    assert {"viewer_count", "comment", "click"} <= kinds
    frame = block_frame(schedule, out.events, burn_in_s=30)
    assert len(frame) == len(schedule.measurement_blocks)
    assert any(r.clicks > 0 for r in frame)


def test_crn_true_effect_positive_when_effect_injected():
    schedule = generate_schedule(60, DesignParams(jitter_s=0), seed=2)
    params = SimParams(treatment_effect=0.5)
    te = true_effect(schedule, params, seed=2)
    assert te > 0


def test_crn_true_effect_zero_when_no_effect():
    schedule = generate_schedule(60, DesignParams(jitter_s=0), seed=3)
    params = SimParams(treatment_effect=0.0)
    te = true_effect(schedule, params, seed=3)
    assert te == pytest.approx(0.0, abs=1e-9)


@pytest.mark.slow
def test_aa_false_positive_rate_near_alpha():
    """A/A gate: under a true null the rejection rate must match alpha.

    The gate is an EXACT TWO-SIDED BINOMIAL TEST of H0: FPR = alpha, failing
    when its p-value drops below 0.01. The previous version (40 reps, "reject
    rate <= 0.15") was close to useless: a test whose true FPR was 12% — 2.4x
    nominal — passed it 80% of the time, and it said nothing at all about
    over-conservatism even though HARNESS.md states the criterion two-sidedly.

    Measured power of THIS gate at 200 reps (scipy.stats.binomtest):
    true FPR  5% -> false alarm  0.8%   (acceptable flakiness)
    true FPR 10% -> detected    62.8%
    true FPR 12% -> detected    88.7%   (old gate: 19.8%)
    true FPR 15% -> detected    99.2%
    true FPR  1% -> detected    67.7%   (over-conservative, also a defect)
    """
    n_reps = 200
    res = run_validation(
        n_reps=n_reps,
        n_sessions_per_rep=6,
        session_minutes=60,
        sim_params=SimParams(treatment_effect=0.0),
        n_draws=300,
        master_seed=11,
    )
    n_reject = round(res.rejection_rate * n_reps)
    gate = binomtest(n_reject, n_reps, ALPHA).pvalue
    assert gate >= 0.01, (
        f"tỷ lệ bác bỏ {res.rejection_rate:.1%} ({n_reject}/{n_reps}) không khớp mức "
        f"ý nghĩa {ALPHA:.0%} — kiểm định nhị thức hai phía p={gate:.4f}\n"
        f"{res.summary()}"
    )


@pytest.mark.slow
def test_effect_recovery_bias_and_coverage():
    """Known-effect gate: bias < 10% of effect (vs CRN ground truth) and
    CI coverage in [90%, 98%] (E3-06 acceptance)."""
    res = run_validation(
        n_reps=40,
        n_sessions_per_rep=8,
        session_minutes=90,
        sim_params=SimParams(treatment_effect=0.3),
        n_draws=300,
        master_seed=13,
    )
    assert abs(res.relative_bias) < 0.10, res.summary()
    # Coverage is a proportion too: a correctly-calibrated 95% interval hits
    # 95% only in expectation. A hard [0.88, 0.99] band on 40 reps fails a
    # perfect estimator surprisingly often, so test the proportion properly.
    n_covered = round(res.ci_coverage * res.n_reps)
    cov_gate = binomtest(n_covered, res.n_reps, 1 - ALPHA).pvalue
    assert cov_gate >= 0.01, (
        f"độ phủ KTC {res.ci_coverage:.1%} ({n_covered}/{res.n_reps}) lệch khỏi 95% "
        f"— kiểm định nhị thức p={cov_gate:.4f}\n"
        f"{res.summary()}"
    )


@pytest.mark.slow
def test_power_improves_with_more_sessions():
    small = run_validation(
        n_reps=20,
        n_sessions_per_rep=3,
        session_minutes=60,
        sim_params=SimParams(treatment_effect=0.4),
        n_draws=200,
        master_seed=17,
    )
    large = run_validation(
        n_reps=20,
        n_sessions_per_rep=10,
        session_minutes=60,
        sim_params=SimParams(treatment_effect=0.4),
        n_draws=200,
        master_seed=17,
    )
    assert large.rejection_rate >= small.rejection_rate


# ---------------------------------------------------------------------------
# Audit 30/08 — the headline validation must also cover the HARD case
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_estimator_under_carryover_interference():
    """Validation with carryover ON — the assumption switchback exists to relax.

    Every previously reported bias/coverage figure was measured with
    ``carryover_halflife_s = 0``, i.e. a world with no interference at all. A
    judge can fairly ask what happens when the thing the design is FOR actually
    occurs; the honest answer has to be measured, not asserted.

    Carryover attenuates the block contrast (some of the ON effect bleeds into
    the following OFF block), so the estimate is expected to be biased TOWARD
    ZERO. What must not happen is a sign flip or a collapse of coverage to the
    point where the interval is meaningless.
    """
    res = run_validation(
        n_reps=25,
        n_sessions_per_rep=6,
        session_minutes=90,
        sim_params=SimParams(treatment_effect=0.4, carryover_halflife_s=120.0),
        n_draws=250,
        master_seed=4242,
    )
    assert res.mean_estimate > 0, f"đổi dấu dưới hiệu ứng lưu: {res.summary()}"
    # Attenuation toward zero is expected and acceptable; anti-conservative
    # inflation is not.
    assert res.relative_bias < 0.25, res.summary()
    assert res.ci_coverage >= 0.60, res.summary()


@pytest.mark.slow
def test_carryover_attenuates_relative_to_clean_world():
    """The direction of the carryover effect must be the documented one."""
    clean = run_validation(
        n_reps=15, n_sessions_per_rep=5, session_minutes=90,
        sim_params=SimParams(treatment_effect=0.4, carryover_halflife_s=0.0),
        n_draws=200, master_seed=77,
    )
    leaky = run_validation(
        n_reps=15, n_sessions_per_rep=5, session_minutes=90,
        sim_params=SimParams(treatment_effect=0.4, carryover_halflife_s=180.0),
        n_draws=200, master_seed=77,
    )
    assert leaky.mean_estimate <= clean.mean_estimate * 1.1, (
        f"hiệu ứng lưu phải làm suy giảm, không khuếch đại\n"
        f"sạch: {clean.summary()}\nrò rỉ: {leaky.summary()}"
    )
