"""Estimator unit tests on synthetic data with known structure (E3-06/07).

Fast checks here; full Monte-Carlo calibration lives in test_sim_validation.py
(marked slow).
"""

import random

import numpy as np
import pytest

from livelift.analysis.estimators import (
    analyze_outer,
    cuped_adjust,
    diff_in_means,
    ht_effect,
    late_wald,
    ols_fe_lin,
    randomization_test,
    studentized_stat,
)
from livelift.core.assigner.outer import DesignParams, draw_assignments


def _make_data(n_sessions=8, blocks_per=12, tau=0.0, seed=0):
    """Blocks with session random effects; treatment adds tau."""
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    ys, zs, sids, phases = [], [], [], []
    for s in range(n_sessions):
        sess_effect = rng.normal(0, 0.5)
        ph = ["early", "mid", "late"][0:3] * (blocks_per // 3)
        ph = (ph + ["mid"] * blocks_per)[:blocks_per]
        arms, _ = draw_assignments(ph, py_rng)
        for i in range(blocks_per):
            z = 1 if arms[i] == "ON" else 0
            y = 5.0 + sess_effect + rng.normal(0, 1.0) + tau * z
            ys.append(y)
            zs.append(z)
            sids.append(f"s{s}")
            phases.append(ph[i])
    return np.array(ys), np.array(zs), np.array(sids), phases


def test_diff_and_ht_agree_at_half_propensity():
    y, z, _, _ = _make_data(tau=1.0, seed=1)
    d = diff_in_means(y, z)
    # HT with p=0.5 estimates the same contrast up to arm-imbalance weighting
    h = ht_effect(y, z, 0.5)
    assert d == pytest.approx(1.0, abs=0.5)
    assert h == pytest.approx(d, abs=0.6)


def test_ht_is_algebraically_identical_to_diff_in_means_at_constant_p():
    """Review 06/09: at CONSTANT p the Hájek weights collapse to the plain arm
    means, so ht_effect ≡ diff_in_means (any constant p, not just 0.5). It is
    therefore NOT a second independent estimator and the API report no longer
    publishes it next to the primary number (PREREGISTRATION §5b)."""
    y, z, _, _ = _make_data(tau=1.0, seed=9)
    d = diff_in_means(y, z)
    for p in (0.5, 0.3, 0.7):
        assert ht_effect(y, z, p) == pytest.approx(d, rel=1e-12, abs=1e-12)


def test_studentized_stat_sign_and_scale():
    y = np.array([1.0, 1.1, 0.9, 5.0, 5.2, 4.9])
    z = np.array([0, 0, 0, 1, 1, 1])
    t = studentized_stat(y, z)
    assert t > 5


def test_randomization_test_null_uniform_p():
    """Under the null, p-values should not concentrate near zero."""
    ps = []
    for seed in range(20):
        y, z, sids, phases = _make_data(tau=0.0, seed=seed)
        p, _ = randomization_test(y, z, sids, phases, n_draws=300, seed=seed)
        ps.append(p)
    assert min(ps) > 0.001
    assert sum(p < 0.05 for p in ps) <= 4  # ~1 expected, allow noise


def test_randomization_test_detects_large_effect():
    y, z, sids, phases = _make_data(tau=2.0, seed=3)
    p, _ = randomization_test(y, z, sids, phases, n_draws=500, seed=3)
    assert p < 0.01


def test_analyze_outer_ci_covers_truth():
    y, z, sids, phases = _make_data(tau=1.0, seed=4)
    res = analyze_outer(y, z, sids, phases, n_draws=400, seed=4)
    assert res.ci_low < 1.0 < res.ci_high
    assert res.ci_low < res.estimate < res.ci_high
    assert res.n_blocks == len(y)
    assert res.n_on + res.n_off == len(y)


def test_ols_fe_lin_removes_session_confounding():
    """Session effects correlated with nothing here, but FE must not bias tau."""
    y, z, sids, phases = _make_data(tau=1.5, seed=5)
    cov = np.random.default_rng(5).normal(size=(len(y), 1))
    res = ols_fe_lin(y, z, sids, covariates=cov)
    assert res.estimate == pytest.approx(1.5, abs=0.4)
    assert res.se_cluster > 0
    assert res.n_clusters == 8


def test_late_wald_recovers_effect_under_noncompliance():
    rng = np.random.default_rng(6)
    n = 4000
    z = rng.integers(0, 2, n)
    # 80% compliance in Z=1, 5% always-takers in Z=0
    d = np.where(z == 1, rng.random(n) < 0.8, rng.random(n) < 0.05).astype(int)
    y = 2.0 * d + rng.normal(0, 1, n)
    res = late_wald(y, z, d)
    assert res.first_stage == pytest.approx(0.75, abs=0.05)
    assert res.late == pytest.approx(2.0, abs=0.3)
    assert res.itt == pytest.approx(1.5, abs=0.3)


def test_late_wald_refuses_weak_first_stage():
    rng = np.random.default_rng(7)
    n = 500
    z = rng.integers(0, 2, n)
    d = rng.integers(0, 2, n)  # no relation to z
    y = rng.normal(size=n)
    res = late_wald(y, z, d)
    assert np.isnan(res.late)
    assert not np.isnan(res.itt)


def test_cuped_reduces_variance_with_correlated_covariate():
    rng = np.random.default_rng(8)
    x = rng.normal(size=2000)
    y = 3.0 + 0.8 * x + rng.normal(0, 0.5, 2000)
    y_adj, vr = cuped_adjust(y, x)
    assert vr > 0.5
    assert y_adj.mean() == pytest.approx(y.mean(), abs=1e-9)


def test_cuped_no_variance_no_crash():
    y = np.ones(10)
    x = np.ones(10)
    y_adj, vr = cuped_adjust(y, x)
    assert vr == 0.0
    assert np.allclose(y_adj, y)


# ---------------------------------------------------------------------------
# Audit 30/08 — degenerate designs must be REFUSED, never reported
# ---------------------------------------------------------------------------


def _degenerate(n_on=1, n_off=5, seed=0):
    """A session where one arm has too few blocks to studentize."""
    rng = np.random.default_rng(seed)
    z = np.array([1] * n_on + [0] * n_off)
    y = rng.normal(5.0, 1.0, size=len(z))
    sids = np.array(["s0"] * len(z))
    phases = ["early", "mid", "late"] * len(z)
    return y, z, sids, phases[: len(z)]


def test_single_block_arm_is_not_estimable():
    """FATAL (audit 30/08): with one arm below 2 blocks the studentized
    statistic is NaN. Every NaN comparison is False, so the p-value used to
    collapse to its floor and the Fisher CI to zero width — i.e. pure noise was
    reported as 'p < 0.001, significant'."""
    y, z, sids, phases = _degenerate(n_on=1, n_off=5)
    res = analyze_outer(y, z, sids, phases, n_draws=200, seed=1)
    assert not res.estimable
    assert np.isnan(res.p_value)
    assert np.isnan(res.ci_low)
    assert np.isnan(res.ci_high)
    assert not res.significant
    assert res.reason is not None
    assert "khối" in res.reason


def test_all_one_arm_is_not_estimable():
    y, z, sids, phases = _degenerate(n_on=0, n_off=6)
    res = analyze_outer(y, z, sids, phases, n_draws=200, seed=2)
    assert not res.estimable
    assert not res.significant


def test_significant_is_false_when_a_bound_is_unbounded():
    """An unidentified bound (-inf/+inf) must never read as significance."""
    from livelift.analysis.estimators import RandomizationResult

    res = RandomizationResult(
        estimate=0.5, estimate_ht=0.5, p_value=0.2,
        ci_low=0.1, ci_high=float("inf"),
        n_blocks=10, n_on=5, n_off=5, n_draws=100,
    )
    assert not res.significant


def test_identical_outcomes_do_not_produce_a_spurious_rejection():
    """SERIOUS (audit 30/08): an exact `se == 0` check missed floating-point
    dust, giving t ~ 1e16 and a false rejection. Constant outcomes carry no
    evidence of an effect."""
    y = np.full(12, 3.3)
    z = np.array([1, 0] * 6)
    sids = np.array(["s0"] * 12)
    phases = ["early", "mid", "late"] * 4
    res = analyze_outer(y, z, sids, phases, n_draws=300, seed=3)
    assert res.estimable
    assert not res.significant
    assert res.p_value > 0.05


def test_degenerate_redraws_are_dropped_not_counted_as_zero():
    """Degenerate reference draws (NaN) must leave the reference set, not be
    mapped to 0.0 — counting them as 'not extreme' biases p downward."""
    from livelift.analysis.estimators import _batch_studentized

    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    zmat = np.array(
        [
            [1, 1, 1, 0, 0, 0],  # fine
            [1, 0, 0, 0, 0, 0],  # one ON block -> undefined
            [0, 0, 0, 0, 0, 0],  # no ON blocks -> undefined
        ],
        dtype=np.int8,
    )
    t = _batch_studentized(y, zmat)
    assert np.isfinite(t[0])
    assert np.isnan(t[1])
    assert np.isnan(t[2])


# ---------------------------------------------------------------------------
# Review 06/09 — redraws must run the SAVED design, not the default one
# ---------------------------------------------------------------------------


def _phase_counts(zmat, phases, phase):
    idx = [i for i, ph in enumerate(phases) if ph == phase]
    n_on = zmat[:, idx].sum(axis=1)
    return n_on, len(idx) - n_on


def test_redraws_respect_saved_min_per_arm_per_phase():
    """A session persisted with min_per_arm_per_phase=3 must be re-drawn under
    that constraint — redrawing the default (2) builds the reference
    distribution of a design nobody ran."""
    from livelift.analysis.estimators import _redraw_matrix

    phases = ["early"] * 6 + ["mid"] * 6 + ["late"] * 6
    sids = np.array(["s0"] * len(phases))
    params = {"s0": DesignParams(min_per_arm_per_phase=3)}

    zmat = _redraw_matrix(sids, phases, n_draws=200, seed=11, design_params=params)
    for ph in ("early", "mid", "late"):
        n_on, n_off = _phase_counts(zmat, phases, ph)
        assert (n_on >= 3).all(), f"redraw vi phạm ràng buộc ≥3 BẬT ở {ph}"
        assert (n_off >= 3).all(), f"redraw vi phạm ràng buộc ≥3 TẮT ở {ph}"

    # Control: the DEFAULT design (min 2) does violate ≥3 in some redraws, so
    # the assertion above genuinely distinguishes the two designs.
    zmat_default = _redraw_matrix(sids, phases, n_draws=200, seed=11)
    violates = False
    for ph in ("early", "mid", "late"):
        n_on, n_off = _phase_counts(zmat_default, phases, ph)
        violates = violates or bool((n_on < 3).any() or (n_off < 3).any())
    assert violates, "thiết kế mặc định lẽ ra phải vi phạm ≥3 — test mất khả năng phân biệt"


def test_randomization_test_threads_design_params_over_full_schedule():
    """The reports path (full schedule + analyzed mask) must also redraw under
    the saved per-session design."""
    y, z, sids, phases = _make_data(n_sessions=1, blocks_per=18, tau=0.0, seed=12)
    params = {"s0": DesignParams(min_per_arm_per_phase=3)}
    _, zmat = randomization_test(
        y, z, sids, phases, n_draws=100, seed=12,
        all_phases=phases, all_session_ids=sids,
        analyzed_mask=np.ones(len(y), dtype=bool),
        design_params=params,
    )
    for ph in set(phases):
        n_on, n_off = _phase_counts(zmat, phases, ph)
        required = min(3, phases.count(ph) // 2)
        assert (n_on >= required).all()
        assert (n_off >= required).all()


@pytest.mark.slow
def test_null_false_positive_rate_is_nominal_on_short_sessions():
    """End-to-end guard on the exact scenario the audit used: 30-minute null
    sessions. Before the fix 52% of them were declared significant."""
    from livelift.core.assigner.outer import DesignParams, generate_schedule
    from livelift.core.features import block_frame
    from livelift.sim.simulator import SimParams, simulate_session

    sig = tested = 0
    for seed in range(120):
        sched = generate_schedule(30, DesignParams(), seed)
        out = simulate_session(sched, SimParams(treatment_effect=0.0), seed)
        frame = block_frame(sched, out.events, burn_in_s=60)
        y = np.array([r.y for r in frame])
        z = np.array([r.z for r in frame])
        res = analyze_outer(
            y, z, np.array(["s0"] * len(y)), [r.phase for r in frame],
            n_draws=299, seed=seed,
        )
        if not res.estimable:
            continue
        tested += 1
        sig += res.significant
    assert tested >= 30, f"quá ít phiên kiểm định được ({tested})"
    rate = sig / tested
    assert rate <= 0.20, f"tỷ lệ dương tính giả {rate:.1%} — kiểm định sai hiệu chỉnh"
