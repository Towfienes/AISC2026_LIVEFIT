"""Estimator validation harness: bias, CI coverage, A/A false-positive rate.

The acceptance criteria (E3-06/07, HARNESS.md gates):
- A/A (zero effect): rejection rate ≈ alpha (within Monte-Carlo error).
- Known effect: |mean(estimate) - mean(true effect)| < 10% of the true effect;
  95% CI coverage within [90%, 98%].

Run from the CLI (``livelift-simulate``) or the slow test suite.

Gói P2 (2026-09-09) added the SBC-style grid on top of the same machinery:
:func:`run_validation` now also returns the PER-REPLICATION p-value, coverage
flag and signed error, and :func:`run_grid` turns a list of
:class:`GridSpec` worlds into :class:`livelift.sim.report.SbcCell` verdicts.
Aggregates alone cannot answer "are the p-values uniform"; the per-rep vectors
can.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np

from livelift.analysis.estimators import analyze_outer
from livelift.core.assigner.outer import DesignParams, generate_schedule
from livelift.core.features import block_frame, blocks_to_dicts
from livelift.sim.report import IccRow, SbcCell, sbc_cell, session_icc, session_icc_bootstrap_se
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
    # Per-replication detail (gói P2). Aggregates cannot be tested for
    # uniformity, so the raw vectors travel with the summary. Defaulted to
    # empty tuples so every pre-existing construction site stays valid.
    p_values: tuple[float, ...] = ()
    coverage_flags: tuple[int, ...] = ()
    errors: tuple[float, ...] = ()  # estimate - true effect, per replication
    truths: tuple[float, ...] = ()
    estimates: tuple[float, ...] = ()

    def summary(self) -> str:
        return (
            f"reps={self.n_reps} sessions/rep={self.n_sessions_per_rep}\n"
            f"mean estimate      : {self.mean_estimate:+.4f}\n"
            f"mean true effect   : {self.mean_true_effect:+.4f}\n"
            f"relative bias      : {self.relative_bias:+.1%}\n"
            f"95% CI coverage    : {self.ci_coverage:.1%}\n"
            f"rejection rate     : {self.rejection_rate:.1%}"
        )

    def to_cell(
        self,
        label: str,
        *,
        check_uniformity: bool,
        alpha: float = 0.05,
        max_relative_bias: float = 0.10,
    ) -> SbcCell:
        """Reduce this study to one grid cell verdict.

        ``truth_scale`` is the mean ABSOLUTE true effect over replications, so a
        null cell (truth ≈ 0) falls back to the "no systematic offset" bias
        criterion instead of dividing by numerical zero — see
        :func:`livelift.sim.report.sbc_cell`.

        A replication whose design could not be tested at all (``estimable=False``
        → NaN p-value, NaN interval) is carried through honestly rather than
        dropped: its p-value is excluded from the uniformity check and the
        rejection count, and its coverage flag is 0 — no interval is a miss, not
        a free pass. If such replications are common the cell should go red on
        coverage, which is the correct signal.
        """
        truth_scale = float(np.mean(np.abs(self.truths))) if self.truths else 0.0
        return sbc_cell(
            self.p_values,
            self.coverage_flags,
            self.errors,
            label=label,
            truth_scale=truth_scale,
            alpha=alpha,
            check_uniformity=check_uniformity,
            max_relative_bias=max_relative_bias,
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
    p_values: list[float] = []
    coverage_flags: list[int] = []
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
        p_values.append(float(res.p_value))
        is_covered = int(res.ci_low <= truth <= res.ci_high)
        coverage_flags.append(is_covered)
        covered += is_covered
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
        p_values=tuple(p_values),
        coverage_flags=tuple(coverage_flags),
        errors=tuple(e - t for e, t in zip(estimates, truths, strict=True)),
        truths=tuple(truths),
        estimates=tuple(estimates),
    )


# ---------------------------------------------------------------------------
# SBC-style grid (gói P2 — SKELETON)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GridSpec:
    """One world on the calibration grid.

    ``check_uniformity`` defaults to "only where a sharp null actually holds"
    (zero treatment effect). Forcing it on for an effect cell would flag a
    perfectly calibrated pipeline: under a real effect the p-values are
    SUPPOSED to concentrate near zero.
    """

    label: str
    sim_params: SimParams
    n_reps: int = 100
    n_sessions_per_rep: int = 3
    session_minutes: int = 60
    n_draws: int = 200
    burn_in_s: int = 60
    master_seed: int = 2026
    design: DesignParams | None = None
    check_uniformity: bool | None = None

    @property
    def uniformity_expected(self) -> bool:
        if self.check_uniformity is not None:
            return self.check_uniformity
        return self.sim_params.treatment_effect == 0.0


def run_grid_cell(spec: GridSpec, alpha: float = 0.05) -> SbcCell:
    """Run one grid cell end-to-end and reduce it to a green/red verdict."""
    res = run_validation(
        n_reps=spec.n_reps,
        n_sessions_per_rep=spec.n_sessions_per_rep,
        session_minutes=spec.session_minutes,
        design=spec.design,
        sim_params=spec.sim_params,
        burn_in_s=spec.burn_in_s,
        alpha=alpha,
        n_draws=spec.n_draws,
        master_seed=spec.master_seed,
    )
    return res.to_cell(spec.label, check_uniformity=spec.uniformity_expected, alpha=alpha)


def run_grid(specs: Sequence[GridSpec], alpha: float = 0.05) -> list[SbcCell]:
    """Run every cell of the grid, in order."""
    return [run_grid_cell(spec, alpha=alpha) for spec in specs]


DEFAULT_ICC_SIGMAS: tuple[float, ...] = (0.0, 0.03, 0.06, 0.095, 0.1, 0.2, 0.3)
"""The ``session_click_sigma`` grid of the published map.

0.1/0.2/0.3 are the coarse grid the P1-K2 brief asked for; 0.03/0.06/0.095 are
the three points that were then tuned to land on the ICC targets 0.02/0.05/0.10
that the calibration gates actually run at.
"""

DEFAULT_FRAILTY_CVS: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0)
"""The ``click_frailty_cv`` grid of the published map.

Swept and published because per-viewer frailty turned out to raise session ICC
as well — a finite audience makes the session's MEAN frailty a session-level
factor — and a side effect nobody measured would be a side effect nobody could
argue with.
"""

ICC_KNOBS: tuple[str, ...] = ("session_click_sigma", "click_frailty_cv")
"""The ``SimParams`` fields a map may sweep: the two heterogeneity knobs.

Restricted on purpose. Sweeping, say, ``treatment_effect`` through this function
would produce a table labelled "ICC" that is really measuring the arm contrast.
"""


def measure_icc_row(
    knob_value: float,
    *,
    knob: str = "session_click_sigma",
    n_sessions: int = 400,
    session_minutes: int = 90,
    design: DesignParams | None = None,
    burn_in_s: int = 60,
    base_params: SimParams | None = None,
    master_seed: int = 909,
    n_boot: int = 400,
) -> IccRow:
    """Measure the session ICC of block ``y`` at one setting of one knob.

    ``base_params`` defaults to a ZERO-effect world on purpose: with a treatment
    effect switched on, blocks of the same session differ by arm as well as by
    session and the one-way ANOVA would be attributing part of the treatment
    contrast to clustering.

    ``master_seed`` is deliberately re-used for every row of a map, so all rows
    share the same session seeds — hence the same arrivals, stays and AR(1)
    noise. Rows therefore differ ONLY in the knob, which is what makes the map a
    measurement of the knob rather than of seed-to-seed luck.
    """
    if knob not in ICC_KNOBS:
        raise ValueError(f"knob phải thuộc {ICC_KNOBS} (nhận {knob!r})")
    base = base_params or SimParams(treatment_effect=0.0)
    params = replace(base, **{knob: knob_value})
    seed_rng = random.Random(master_seed)

    ys: list[float] = []
    session_ids: list[str] = []
    within: list[float] = []
    for s in range(n_sessions):
        seed = seed_rng.randrange(2**60)
        schedule = generate_schedule(session_minutes, design or DesignParams(), seed)
        out = simulate_session(schedule, params, seed)
        vals = [r.y for r in block_frame(schedule, out.events, burn_in_s=burn_in_s) if r.measurable]
        # A session with a single measurable block carries no within-session
        # information and no within-variance; it is skipped rather than entered
        # with a fabricated 0 variance.
        if len(vals) < 2:
            continue
        ys.extend(vals)
        session_ids.extend([f"s{s}"] * len(vals))
        within.append(float(np.var(vals, ddof=1)))

    icc = session_icc(ys, session_ids)
    se = session_icc_bootstrap_se(ys, session_ids, n_boot=n_boot, seed=master_seed)
    return IccRow(
        knob=knob,
        knob_value=knob_value,
        icc=icc,
        icc_se=se,
        mean_y=float(np.mean(ys)) if ys else float("nan"),
        mean_within_var=float(np.mean(within)) if within else float("nan"),
        n_sessions=len(within),
        n_blocks=len(ys),
    )


def measure_icc_map(
    values: Sequence[float] = DEFAULT_ICC_SIGMAS,
    **row_kwargs: object,
) -> list[IccRow]:
    """One knob → ICC map: :func:`measure_icc_row` per value, in the given order."""
    return [measure_icc_row(v, **row_kwargs) for v in values]  # type: ignore[arg-type]


def default_grid(
    sigmas: Sequence[float] = (0.0, 0.055),
    effects: Sequence[float] = (0.0, 0.30),
    icc_labels: dict[float, str] | None = None,
    **spec_kwargs: object,
) -> list[GridSpec]:
    """The shipped SKELETON grid: {no clustering, ICC≈0.05} x {A/A, MDE}.

    ``sigmas`` are ``SimParams.session_click_sigma`` values, NOT ICCs — the map
    between them is empirical and lives in the simulator's module docstring.
    ``icc_labels`` lets the caller print the measured ICC instead of sigma;
    without it the label quotes sigma, which is the only number this function
    actually knows.

    Four cells at 100 reps is what fits in a coffee break. The ~20-cell grid
    (carryover x ICC x effect, 1000 reps) is pre-registration-week work and is
    deliberately NOT approximated here.
    """
    specs: list[GridSpec] = []
    for sigma in sigmas:
        icc_txt = (icc_labels or {}).get(sigma, f"σ={sigma:g}")
        for effect in effects:
            eff_txt = "A/A (tác động 0)" if effect == 0.0 else f"tác động {effect:g}"
            specs.append(
                GridSpec(
                    label=f"{icc_txt} × {eff_txt}",
                    sim_params=SimParams(treatment_effect=effect, session_click_sigma=sigma),
                    **spec_kwargs,  # type: ignore[arg-type]
                )
            )
    return specs
