"""Statistical power / MDE calculator for the WITHIN-SESSION switchback.

Base formula (J-PAL): relative MDE ≈ (z_{1-α/2} + z_{power}) · CV · √(2/n_arm)
(≈ 4·CV/√n_arm at 80% power, 5% two-sided — the plan's approximation).

**Which corrections apply depends on where randomization happens**, and getting
this wrong in either direction is a reportable error. LiveLift randomizes
BETWEEN blocks INSIDE a session, so:

- ÷ compliance — ITT dilution. Applies. Largest term outside Live Lab.
- × √(1 - burn_in_share)⁻¹ — effective-n loss from the analysis burn-in.
  Applies, but only if the CV was measured on windows that did NOT already
  drop the burn-in (double-charging it is a real mistake — see reports.py).
- × √(1 - R²) — CUPED/CUPAC variance reduction. Applies.
- × √(1 + (m-1)·ICC_session) — the Moulton cluster design effect. **DOES NOT
  APPLY** to this design and is off by default. It is derived for CLUSTER-level
  assignment, where every unit in a cluster shares one arm so the cluster
  random effect never cancels. Here the session random effect is common to
  that session's ON and OFF blocks and differences out of the ON−OFF contrast
  — which is exactly what the pre-registered analysis does (randomization
  redraws happen within session; ``ols_fe_lin`` demeans within session).
  ``session_level_assignment=True`` re-enables it for a hypothetical arm where
  a whole session is assigned one way.
- Serial correlation — the AR(1) mean-inflation factor (1+ρ)/(1-ρ) is the
  correction for the MEAN of a time series, NOT for a contrast between
  interleaved randomized blocks. Under i.i.d.-per-block assignment, positive
  residual autocorrelation makes the ON and OFF means move together, so it
  slightly SHRINKS Var(ȳ_ON − ȳ_OFF). Importing the mean-inflation factor
  applied an inflation of the wrong sign. This module therefore applies NO
  serial-correlation term by default; ``serial_factor`` lets the analyst pass
  a factor derived from the realized assignment autocorrelation if the design
  ever gains alternation constraints. Audit 30/08 — see docs/incident-log.md.

- × ``RANDOMIZATION_TEST_MARGIN`` — a MEASURED gap, not an assumption. The
  closed-form MDE assumes an asymptotic z-test; the pre-registered primary
  test is a finite-draw randomization test on a small block count, which is
  less powerful. Sweeping achieved power against effect size (8 sessions, 128
  blocks, 60 reps/point) gave 65% power at 1.00x the analytic MDE, 78% at
  1.15x and 85% at 1.30x — so the analytic figure must be scaled by ~1.2 to
  mean what it claims. Reporting the unscaled number would overstate what the
  design can detect. Re-measure with
  ``tests/test_power.py::test_predicted_mde_matches_achieved_power`` whenever
  the estimator or design changes.

HARD RULE (plan §1.4): from week 5 the CV fed into this module must be a
MEASURED within-session value from pilot sessions, not an assumption.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

RANDOMIZATION_TEST_MARGIN = 1.2
"""Measured shortfall of the randomization test vs the asymptotic formula.

See the module docstring for the sweep that produced it. Set to 1.0 only to
inspect the raw closed-form value — never for a reported number.
"""


@dataclass(frozen=True)
class PowerInputs:
    cv: float
    """Coefficient of variation of the block outcome, WITHIN session.

    Must be the within-session CV: the primary analysis differences out the
    session effect, so pooling raw blocks across sessions smuggles
    between-session variance the estimator never pays for. Use
    :func:`within_session_cv`.
    """

    n_blocks_total: int  # measurement blocks across all sessions
    n_sessions: int
    alpha: float = 0.05
    power: float = 0.80
    compliance: float = 0.95  # auto mode ≈ 0.95; suggest mode measured
    burn_in_share: float = 0.0  # share of block minutes dropped as burn-in
    var_reduction_r2: float = 0.0  # CUPED/CUPAC R² (measured)

    # --- corrections that DO NOT apply to a within-session switchback -------
    icc_session: float = 0.0
    """Session-level ICC. Ignored unless ``session_level_assignment`` is set —
    see the module docstring."""

    session_level_assignment: bool = False
    """True only for a design where an entire session gets one arm."""

    serial_factor: float = 1.0
    """Variance-inflation factor for residual serial correlation, if the
    analyst derives one for the realized assignment. 1.0 = neutral (the
    default and the right value for i.i.d.-per-block assignment)."""

    randomization_margin: float = RANDOMIZATION_TEST_MARGIN
    """Measured correction for the randomization test's finite-sample power."""


def within_session_cv(y: np.ndarray, session_ids: np.ndarray) -> float:
    """CV of the block outcome after removing session means.

    The primary analysis is within-session, so this — not the pooled CV — is
    what drives its power. Pooled CV = √(σ²_between + σ²_within)/mean, which
    charges the design for variance it already differences away.

    Uses the FE degrees-of-freedom correction (n - n_sessions).
    """
    y = np.asarray(y, float)
    sess = np.asarray(session_ids)
    n, k = len(y), len(np.unique(sess))
    if n <= k or y.mean() == 0:
        return float("nan")
    resid = y.astype(float).copy()
    for s in np.unique(sess):
        m = sess == s
        resid[m] -= resid[m].mean()
    sd_within = float(np.sqrt((resid**2).sum() / (n - k)))
    return sd_within / abs(float(y.mean()))


def poisson_floor(
    y: np.ndarray,
    clicks: np.ndarray,
    exposure_viewer_s: np.ndarray,
    session_ids: np.ndarray,
) -> tuple[float, float]:
    """How much of the block-outcome variance is IRREDUCIBLE counting noise.

    The outcome is a rate, ``y_k = 1000 * clicks_k / E_k``. If clicks are
    Poisson given the exposure, their variance contributes
    ``var_pois = mean_k(1000² · clicks_k / E_k²)`` — noise no covariate can
    explain, because there is nothing to explain: it is the arrival process.

    Returns ``(cv_poisson_floor, reducible_share)``:

    - ``cv_poisson_floor`` — the CV the design would still have if every
      systematic source of variation were perfectly predicted. The MDE cannot
      go below the value this implies without changing the DESIGN.
    - ``reducible_share`` — the fraction of within-session variance that is
      NOT counting noise, i.e. the hard ceiling on any covariate-adjustment
      R². Near zero means CUPED/CUPAC/prognostic scores cannot help at all.

    Why this matters more than any adjustment method: measured on the
    calibrated simulator (24 sessions, 384 blocks, ~9.5 clicks/block) the
    within-session CV is 0.352 and the Poisson floor is 0.356 — a reducible
    share of about zero. Spending three weeks on a prognostic model would have
    bought nothing. The lever that DOES work is design: longer blocks collect
    more clicks per block, and CV_poisson falls as 1/√clicks — 10-minute
    blocks (~19 clicks) put the floor near 0.23, roughly a 35% cut in MDE.

    Run this on pilot data BEFORE committing to any variance-reduction work.
    """
    y = np.asarray(y, float)
    clicks = np.asarray(clicks, float)
    exposure = np.asarray(exposure_viewer_s, float)
    ok = (exposure > 0) & np.isfinite(y)
    if ok.sum() < 2 or y[ok].mean() <= 0:
        return float("nan"), float("nan")

    var_pois = float(np.mean(1_000_000.0 * clicks[ok] / exposure[ok] ** 2))
    cv_floor = float(np.sqrt(var_pois) / y[ok].mean())

    sess = np.asarray(session_ids)[ok]
    resid = y[ok].copy()
    for sid in np.unique(sess):
        m = sess == sid
        resid[m] -= resid[m].mean()
    n, k = len(resid), len(np.unique(sess))
    if n <= k:
        return cv_floor, float("nan")
    var_within = float((resid**2).sum() / (n - k))
    if var_within <= 0:
        return cv_floor, float("nan")
    return cv_floor, float(1.0 - var_pois / var_within)


def mde_relative(inp: PowerInputs) -> float:
    """Minimum detectable RELATIVE effect on the block outcome (0.18 = 18%)."""
    if inp.n_blocks_total < 4 or inp.n_sessions < 1 or not np.isfinite(inp.cv):
        return float("inf")
    n_arm = inp.n_blocks_total / 2
    z = norm.ppf(1 - inp.alpha / 2) + norm.ppf(inp.power)
    mde = z * inp.cv * (2 / n_arm) ** 0.5

    if inp.session_level_assignment:
        m = inp.n_blocks_total / inp.n_sessions  # cluster size
        mde *= (1 + (m - 1) * max(inp.icc_session, 0.0)) ** 0.5

    mde *= max(inp.serial_factor, 0.0) ** 0.5
    mde *= (1.0 / max(1.0 - inp.burn_in_share, 1e-9)) ** 0.5
    mde *= (1 - max(0.0, min(inp.var_reduction_r2, 0.95))) ** 0.5
    mde /= max(inp.compliance, 1e-9)
    mde *= max(inp.randomization_margin, 1.0)
    return float(mde)


@dataclass(frozen=True)
class Scenario:
    name: str
    n_sessions: int
    session_minutes: int
    block_min: int
    endpoint_double: bool = True
    compliance: float = 0.95


def blocks_in_session(session_minutes: int, block_min: int, endpoint_double: bool) -> int:
    if endpoint_double and session_minutes >= 4 * block_min + 2 * block_min:
        return session_minutes // block_min - 2
    return session_minutes // block_min


def scenario_table(
    scenarios: list[Scenario],
    cv_grid: tuple[float, ...] = (0.5, 0.8, 1.2),
    burn_in_share: float = 0.0,
    var_reduction_r2: float = 0.0,
) -> list[dict]:
    """MDE table across scenarios × CV — the honest two-scenario power table
    (no-partner vs with-partner) required by the research synthesis (L2).

    ``burn_in_share`` defaults to 0 because the measured CV normally comes from
    outcomes that ALREADY exclude the burn-in window; passing a share here as
    well would charge for it twice.
    """
    rows = []
    for sc in scenarios:
        n_blocks = blocks_in_session(sc.session_minutes, sc.block_min, sc.endpoint_double)
        total = n_blocks * sc.n_sessions
        for cv in cv_grid:
            inp = PowerInputs(
                cv=cv,
                n_blocks_total=total,
                n_sessions=sc.n_sessions,
                compliance=sc.compliance,
                burn_in_share=burn_in_share,
                var_reduction_r2=var_reduction_r2,
            )
            rows.append(
                {
                    "scenario": sc.name,
                    "n_sessions": sc.n_sessions,
                    "blocks_per_session": n_blocks,
                    "n_blocks_total": total,
                    "cv": cv,
                    "mde_relative": round(mde_relative(inp), 4),
                }
            )
    return rows
