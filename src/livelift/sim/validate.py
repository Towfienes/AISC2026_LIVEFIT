"""Estimator validation harness: bias, CI coverage, A/A false-positive rate.

The acceptance criteria (E3-06/07, HARNESS.md gates):
- A/A (zero effect): rejection rate ≈ alpha (within Monte-Carlo error).
- Known effect: |mean(estimate) - mean(true effect)| < 10% of the true effect;
  95% CI coverage within [90%, 98%].

Run from the CLI (``livelift-simulate``) or the slow test suite.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from livelift.analysis.estimators import analyze_outer
from livelift.core.assigner.outer import DesignParams, generate_schedule
from livelift.core.features import block_frame, blocks_to_dicts
from livelift.sim.simulator import SimParams, simulate_session, true_effect


@dataclass(frozen=True)
class ValidationResult:
    n_reps: int
    n_sessions_per_rep: int
    mean_estimate: float
    mean_true_effect: float
    relative_bias: float
    ci_coverage: float
    rejection_rate: float  # share of reps with p < alpha

    def summary(self) -> str:
        return (
            f"reps={self.n_reps} sessions/rep={self.n_sessions_per_rep}\n"
            f"mean estimate      : {self.mean_estimate:+.4f}\n"
            f"mean true effect   : {self.mean_true_effect:+.4f}\n"
            f"relative bias      : {self.relative_bias:+.1%}\n"
            f"95% CI coverage    : {self.ci_coverage:.1%}\n"
            f"rejection rate     : {self.rejection_rate:.1%}"
        )


def run_validation(
    n_reps: int = 50,
    n_sessions_per_rep: int = 10,
    session_minutes: int = 90,
    design: DesignParams | None = None,
    sim_params: SimParams | None = None,
    burn_in_s: int = 60,
    alpha: float = 0.05,
    n_draws: int = 500,
    master_seed: int = 2026,
) -> ValidationResult:
    """Monte-Carlo study over replications of a multi-session experiment.

    MEASURED behaviour (25 reps x 6 sessions x 90 min, effect 0.4,
    re-measured 02/09 with KuaiLive-calibrated SimParams — engaged-viewer
    mean stay 10 min):

    ==========================  ==========  ==========  =========
    carryover half-life         estimate    rel. bias   coverage
    ==========================  ==========  ==========  =========
    0 s (no interference)          +0.395       -0.3%       100%
    120 s                          +0.316      -20.3%        84%
    180 s                          +0.278      -29.8%        60%
    ==========================  ==========  ==========  =========

    Carryover attenuates the block contrast toward zero — the conservative
    direction: the system under-states its own effect rather than inventing
    one. NOTE the calibrated world is HARDER than the pre-calibration one
    (longer stays carry more effect across block boundaries): coverage at a
    3-minute half-life dropped from 76% to 60%. This is precisely why the
    week-3 calibration measures the real decay time (t_mix) BEFORE the block
    length is fixed — if t_mix approaches minutes, blocks must lengthen.
    Quote these numbers rather than the no-carryover ones alone: the
    clean-world figure on its own is circular evidence.
    """
    design = design or DesignParams()
    sim_params = sim_params or SimParams()
    seed_rng = random.Random(master_seed)

    estimates: list[float] = []
    truths: list[float] = []
    covered = 0
    rejected = 0

    for _ in range(n_reps):
        ys, zs, sess_ids, phases = [], [], [], []
        rep_truths = []
        for s in range(n_sessions_per_rep):
            seed = seed_rng.randrange(2**60)
            schedule = generate_schedule(session_minutes, design, seed)
            out = simulate_session(schedule, sim_params, seed)
            frame = block_frame(schedule, out.events, burn_in_s=burn_in_s)
            # Same exclusion rule as production (reports.py): unmeasurable
            # blocks never enter estimation, so the harness must not feed them
            # either — otherwise it validates a pipeline nobody runs.
            for r in blocks_to_dicts(frame):
                if not r.get("measurable", True):
                    continue
                ys.append(r["y"])
                zs.append(r["z"])
                sess_ids.append(f"s{s}")
                phases.append(r["phase"])
            rep_truths.append(true_effect(schedule, sim_params, seed, burn_in_s))

        res = analyze_outer(
            np.array(ys),
            np.array(zs),
            np.array(sess_ids),
            phases,
            alpha=alpha,
            n_draws=n_draws,
            seed=seed_rng.randrange(2**31),
        )
        truth = float(np.mean(rep_truths))
        estimates.append(res.estimate)
        truths.append(truth)
        if res.ci_low <= truth <= res.ci_high:
            covered += 1
        if res.p_value < alpha:
            rejected += 1

    mean_est = float(np.mean(estimates))
    mean_truth = float(np.mean(truths))
    rel_bias = (mean_est - mean_truth) / abs(mean_truth) if abs(mean_truth) > 1e-12 else 0.0
    return ValidationResult(
        n_reps=n_reps,
        n_sessions_per_rep=n_sessions_per_rep,
        mean_estimate=mean_est,
        mean_true_effect=mean_truth,
        relative_bias=float(rel_bias),
        ci_coverage=covered / n_reps,
        rejection_rate=rejected / n_reps,
    )
