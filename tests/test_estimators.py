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
from livelift.core.assigner.outer import draw_assignments


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
