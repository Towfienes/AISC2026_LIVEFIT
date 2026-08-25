"""Statistical calibration gates (HARNESS §2) — Monte-Carlo, marked slow.

Fast smoke checks run in the default suite; the full calibration study runs
nightly / pre-release with `pytest -m slow`.
"""

import pytest

from livelift.core.assigner.outer import DesignParams, generate_schedule
from livelift.core.features import block_frame
from livelift.sim.simulator import SimParams, simulate_session, true_effect
from livelift.sim.validate import run_validation


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
    """A/A gate: with zero effect, rejection rate ≈ 5% (Monte-Carlo error band)."""
    res = run_validation(
        n_reps=40,
        n_sessions_per_rep=6,
        session_minutes=60,
        sim_params=SimParams(treatment_effect=0.0),
        n_draws=300,
        master_seed=11,
    )
    assert res.rejection_rate <= 0.15, res.summary()


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
    assert 0.88 <= res.ci_coverage <= 0.99, res.summary()


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
