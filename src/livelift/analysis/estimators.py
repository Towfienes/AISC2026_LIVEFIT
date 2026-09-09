"""Design-based estimation and randomization inference for the outer tier.

Pre-registered analysis pipeline (docs/research/2026-08-24-estimators.md):

- Unit of analysis: the BLOCK. Cluster: the SESSION. Never click-level rows.
- Primary test: randomization inference with a STUDENTIZED difference
  statistic, re-drawing assignments with the production assignment mechanism
  (:func:`livelift.core.assigner.outer.draw_assignments`) independently per
  session — the reference distribution therefore matches the actual design
  exactly (Bojinov & Shephard, JASA 2019).
- Point estimate: the difference in means. The Hájek/IPW form
  (:func:`ht_effect`) is algebraically IDENTICAL to it at constant propensity —
  the outer tier's p=0.5 included — so it is not an independent second
  estimator and is never reported next to the primary number
  (PREREGISTRATION.md §5b); it exists for the inner tier's per-block
  propensities. OLS with session fixed effects + Lin (2013) interacted
  covariates is the variance-reduced secondary.
- Confidence interval: inversion of the randomization test over a grid of
  constant additive effects (Fisher CI).
- LATE under partial compliance: Wald / IV estimator with assignment as the
  instrument, delta-method SE, first-stage compliance reported.
- CUPED-style covariate adjustment. The covariates must be fixed at
  schedule-draw time (PREREGISTRATION.md §5c); the previous-block ``pre_*``
  metrics are explicitly NOT admissible, whatever the wording of an older
  revision of this line suggested.
- Two OPT-IN sensitivity switches on :func:`analyze_outer` (gói P3+P4, 09/09):
  ``outcome_mode='linearized'`` for a ratio metric whose denominator may itself
  be treated, and ``adjust='cuped_mv'`` for multivariate CUPED over the
  deterministic schedule/clock covariates. Both default to OFF; the primary
  path is unchanged and a test asserts it bit-for-bit.

All functions are pure NumPy — no I/O, explicit seeds everywhere.

MODULE SPLIT (2026-09-08, gói P5a — mechanical, no behavior change): the
covariate-adjustment and robust-variance blocks moved out to
:mod:`livelift.analysis.adjust` and :mod:`livelift.analysis.robust`, and the
empty :mod:`livelift.analysis.carryover` was created, so the queued work of the
2026-09-07 programme (CUPED-mv / linearization, wild cluster bootstrap / ICS,
lag-1 carryover) stops converging on this one file — three proposals editing
the same module days before the week-6 pre-registration freeze is how a
mechanical merge turns into a silent change to the primary test. The primary
test itself (:func:`randomization_test`, :func:`randomization_ci`,
:func:`analyze_outer`) deliberately did NOT move. Every public name is
re-exported below, so no import site changed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from livelift.core.assigner.outer import ON, DesignParams, draw_assignments

from .adjust import cuped_adjust, cuped_adjust_mv, linearize_ratio, observed_ratio
from .robust import OLSResult, ols_fe_lin

__all__ = [
    "MIN_BLOCKS_PER_ARM",
    "LATEResult",
    "OLSResult",
    "RandomizationResult",
    "analyze_outer",
    "cuped_adjust",
    "diff_in_means",
    "ht_effect",
    "late_wald",
    "ols_fe_lin",
    "randomization_ci",
    "randomization_test",
    "studentized_stat",
]

# ---------------------------------------------------------------------------
# Point estimators
# ---------------------------------------------------------------------------


def diff_in_means(y: np.ndarray, z: np.ndarray) -> float:
    y, z = np.asarray(y, float), np.asarray(z, int)
    if z.sum() == 0 or z.sum() == len(z):
        return float("nan")
    return float(y[z == 1].mean() - y[z == 0].mean())


def ht_effect(y: np.ndarray, z: np.ndarray, p: np.ndarray | float = 0.5) -> float:
    """Hájek (self-normalized) inverse-propensity estimate of the block effect.

    Each arm's weighted sum is divided by its REALIZED weight total, not by n.
    The un-normalized Horvitz–Thompson form is unbiased at p=0.5, but its error
    picks up a term proportional to (n_on - n_off) times the LEVEL of y — which
    carries no information about the treatment effect. Under a Bernoulli
    switchback the arm counts are random, so that term is pure noise: the
    estimate could differ from the difference in means by more than the whole
    effect under study, and even flip sign (audit 30/08). Normalizing removes
    it and makes this agree with the difference in means at constant p, while
    staying valid for the per-block propensities of the inner tier.

    ALGEBRAIC IDENTITY (review 06/09): at CONSTANT p — the outer tier's p=0.5
    included — every treated block gets weight 1/p and every control block
    1/(1-p), so each self-normalized arm mean reduces to the plain arm mean and
    this function equals :func:`diff_in_means` exactly (bit-for-bit up to
    float rounding). It is therefore NOT an independent second estimator there
    and must never be published next to the difference in means as if it were
    (PREREGISTRATION.md §5b). It earns its keep only where propensities vary
    per block (inner tier).
    """
    y, z = np.asarray(y, float), np.asarray(z, int)
    p_arr = np.full_like(y, float(p)) if np.isscalar(p) else np.asarray(p, float)
    w1 = z / p_arr
    w0 = (1 - z) / (1 - p_arr)
    if w1.sum() == 0 or w0.sum() == 0:
        return float("nan")
    return float((y * w1).sum() / w1.sum() - (y * w0).sum() / w0.sum())


MIN_BLOCKS_PER_ARM = 2
"""Below this the studentized statistic is undefined (no within-arm variance).

Reporting anything for such a configuration is worse than reporting nothing:
see :func:`analyze_outer` and the audit note in ``docs/incident-log.md``.
"""


def _se_is_degenerate(se: float, m1: float, m0: float) -> bool:
    """Scale-aware zero test for the studentized denominator.

    An exact ``se == 0`` check misses floating-point dust: identical block
    outcomes can leave an SE of ~1e-17 instead of 0, which turns a zero
    numerator difference into t ~ 1e16 and a spurious rejection. Compare
    against the scale of the means instead.
    """
    if not np.isfinite(se):
        return True
    return se <= 1e-12 * max(1.0, abs(m1) + abs(m0))


def studentized_stat(y: np.ndarray, z: np.ndarray) -> float:
    """Two-sample t-type statistic — studentization gives the randomization
    test better behavior under heteroskedasticity (Chung & Romano, 2013).

    Returns NaN when either arm holds fewer than ``MIN_BLOCKS_PER_ARM`` blocks.
    Callers MUST treat that NaN as "cannot test", never as a value: comparing
    NaN with the reference draws is False everywhere, which would silently
    collapse the p-value to its floor.
    """
    y, z = np.asarray(y, float), np.asarray(z, int)
    y1, y0 = y[z == 1], y[z == 0]
    if len(y1) < MIN_BLOCKS_PER_ARM or len(y0) < MIN_BLOCKS_PER_ARM:
        return float("nan")
    m1, m0 = y1.mean(), y0.mean()
    se = float(np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0)))
    if _se_is_degenerate(se, m1, m0):
        return 0.0
    return float((m1 - m0) / se)


# ---------------------------------------------------------------------------
# Randomization inference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RandomizationResult:
    estimate: float  # difference in means (per-1000-viewer-second click rate)
    # Hájek/IPW at the logged constant p=0.5 — algebraically EQUAL to
    # ``estimate`` (see ht_effect). Kept for auditing the identity; never
    # published as a second estimator (PREREGISTRATION.md §5b).
    estimate_ht: float
    p_value: float  # NaN when the design cannot be tested (see `estimable`)
    ci_low: float  # NaN if not estimable; -inf if the lower side is unbounded
    ci_high: float  # NaN if not estimable; +inf if the upper side is unbounded
    n_blocks: int
    n_on: int
    n_off: int
    n_draws: int
    estimable: bool = True
    reason: str | None = None  # Vietnamese, user-facing, set when not estimable
    # Which SENSITIVITY path produced these numbers (gói P3+P4, 09/09). Both
    # default to the pre-registered primary path, so an untouched call site
    # keeps describing itself correctly. A result carrying anything else is a
    # sensitivity run and must be LABELLED as one wherever it is printed — in
    # particular `estimate` is in linearized-click units, not clicks per 1000
    # viewer-seconds, when outcome_mode == "linearized".
    outcome_mode: str = "ratio"
    adjust: str = "none"

    @property
    def significant(self) -> bool:
        """Whether the interval excludes zero — False whenever not estimable.

        Callers must use THIS rather than comparing ci_low/ci_high themselves:
        a NaN or unbounded side must never read as significance.
        """
        if not self.estimable or not np.isfinite(self.ci_low) or not np.isfinite(self.ci_high):
            return False
        return self.ci_low > 0 or self.ci_high < 0


def _redraw_matrix(
    session_ids: np.ndarray,
    phases: list[str],
    n_draws: int,
    seed: int,
    analyzed_mask: np.ndarray | None = None,
    design_params: dict[str, DesignParams] | None = None,
) -> np.ndarray:
    """(n_draws, n_analyzed) matrix of assignment redraws.

    The reference distribution must come from the design that WAS ACTUALLY RUN.
    Assignment was drawn over every SCHEDULED block of each session, so the
    redraw has to be too — including blocks later dropped from the analysis
    (never aired, too little exposure). Redrawing over only the surviving
    blocks would rerandomize a design nobody ran: different stratum sizes, a
    different rerandomization constraint, hence a wrong p-value.

    ``design_params`` maps session_id → the session's persisted
    :class:`DesignParams`; each redraw then uses that session's own p /
    rerandomization constraint instead of the defaults. A session missing from
    the map falls back to ``DesignParams()`` — only correct for sessions that
    really ran the default design.

    ``analyzed_mask`` marks which of those scheduled blocks entered the
    analysis. Each redraw is generated over the full schedule and then
    subset by the SAME fixed mask, which keeps the test exact under the sharp
    null provided the exclusions do not depend on the assignment. Exclusions
    for "block never aired" cannot; the minimum-exposure rule could in
    principle, and that is recorded as a limitation in PREREGISTRATION.md.
    """
    rng = random.Random(seed)
    n = len(phases)
    sessions: dict = {}
    for i, s in enumerate(session_ids):
        sessions.setdefault(s, []).append(i)
    default_params = DesignParams()
    params_of = design_params or {}
    out = np.empty((n_draws, n), dtype=np.int8)
    for d in range(n_draws):
        for sid, idx in sessions.items():
            params = params_of.get(sid, default_params)
            arms, _ = draw_assignments(
                [phases[i] for i in idx],
                rng,
                p=params.p,
                min_per_arm_per_phase=params.min_per_arm_per_phase,
                max_redraws=params.max_redraws,
                min_transition_pairs=params.min_transition_pairs,
            )
            for i, arm in zip(idx, arms, strict=True):
                out[d, i] = 1 if arm == ON else 0
    if analyzed_mask is None:
        return out
    return out[:, np.asarray(analyzed_mask, bool)]


def _batch_studentized(y: np.ndarray, zmat: np.ndarray) -> np.ndarray:
    """Vectorized studentized statistic for every row of the redraw matrix.

    Rows whose arms are too small for a within-arm variance return NaN — the
    same convention as :func:`studentized_stat`. They must be EXCLUDED from the
    reference distribution, not mapped to 0.0: a degenerate draw is not
    evidence of "no effect", and counting it as a non-extreme statistic biases
    every p-value downward.
    """
    y = np.asarray(y, float)
    n1 = zmat.sum(axis=1)
    n0 = zmat.shape[1] - n1
    ok = (n1 >= MIN_BLOCKS_PER_ARM) & (n0 >= MIN_BLOCKS_PER_ARM)
    with np.errstate(divide="ignore", invalid="ignore"):
        s1 = zmat @ y
        s0 = y.sum() - s1
        m1 = np.where(n1 > 0, s1 / np.maximum(n1, 1), np.nan)
        m0 = np.where(n0 > 0, s0 / np.maximum(n0, 1), np.nan)
        q1 = zmat @ (y**2)
        q0 = (y**2).sum() - q1
        # unbiased variances
        v1 = (q1 - n1 * m1**2) / np.maximum(n1 - 1, 1)
        v0 = (q0 - n0 * m0**2) / np.maximum(n0 - 1, 1)
        se = np.sqrt(np.maximum(v1, 0) / np.maximum(n1, 1) + np.maximum(v0, 0) / np.maximum(n0, 1))
        scale = 1e-12 * np.maximum(1.0, np.abs(m1) + np.abs(m0))
        t = np.where(se > scale, (m1 - m0) / se, 0.0)
    return np.where(ok, t, np.nan)


def _p_from_stats(t_obs: float, t_draws: np.ndarray) -> float:
    """Two-sided randomization p-value from an observed statistic and its
    reference draws.

    Returns NaN when the observed statistic is undefined (an arm too small to
    studentize). Letting a NaN flow into the comparison would make every
    ``>=`` False and collapse p to its floor 1/(draws+1) — i.e. report maximal
    confidence on a configuration that carries no information at all. That is
    the single most dangerous failure mode this module can have, so it is
    refused explicitly (audit 30/08, docs/incident-log.md).

    Degenerate draws (NaN) are dropped from the reference set and the p-value
    is computed over the valid ones only.
    """
    if not np.isfinite(t_obs):
        return float("nan")
    valid = t_draws[np.isfinite(t_draws)]
    if valid.size == 0:
        return float("nan")
    # add-one correction keeps the p-value valid (never exactly 0)
    return float((1 + np.sum(np.abs(valid) >= abs(t_obs))) / (1 + valid.size))


def _build_zmat(
    session_ids,
    phases,
    n_draws: int,
    seed: int,
    all_phases: list[str] | None,
    all_session_ids=None,
    analyzed_mask: np.ndarray | None = None,
    design_params: dict[str, DesignParams] | None = None,
) -> np.ndarray:
    """Redraw matrix over the design that was actually run.

    When the caller knows the FULL schedule (including blocks dropped from the
    analysis) it must pass it: the assignment mechanism operated over those
    blocks, so the reference distribution has to as well. ``design_params``
    (session_id → persisted params) makes each redraw honor the session's own
    design — see :func:`_redraw_matrix`.
    """
    if all_phases is not None and analyzed_mask is not None:
        sids = np.asarray(all_session_ids if all_session_ids is not None else session_ids)
        return _redraw_matrix(sids, list(all_phases), n_draws, seed, analyzed_mask, design_params)
    return _redraw_matrix(
        np.asarray(session_ids), list(phases), n_draws, seed, design_params=design_params
    )


def randomization_test(
    y: np.ndarray,
    z: np.ndarray,
    session_ids: np.ndarray,
    phases: list[str],
    n_draws: int = 2000,
    seed: int = 12345,
    zmat: np.ndarray | None = None,
    all_phases: list[str] | None = None,
    all_session_ids: np.ndarray | None = None,
    analyzed_mask: np.ndarray | None = None,
    design_params: dict[str, DesignParams] | None = None,
) -> tuple[float, np.ndarray]:
    """Two-sided randomization p-value for the sharp null of no effect.

    Returns (p_value, redraw_matrix) — the matrix can be reused for CI
    inversion so the expensive redraws happen once.
    """
    y = np.asarray(y, float)
    z = np.asarray(z, int)
    if zmat is None:
        zmat = _build_zmat(
            session_ids,
            phases,
            n_draws,
            seed,
            all_phases,
            all_session_ids,
            analyzed_mask,
            design_params,
        )
    p = _p_from_stats(studentized_stat(y, z), _batch_studentized(y, zmat))
    return p, zmat


def randomization_ci(
    y: np.ndarray,
    z: np.ndarray,
    session_ids: np.ndarray,
    phases: list[str],
    alpha: float = 0.05,
    n_draws: int = 2000,
    seed: int = 12345,
    zmat: np.ndarray | None = None,
    all_phases: list[str] | None = None,
    all_session_ids: np.ndarray | None = None,
    analyzed_mask: np.ndarray | None = None,
    design_params: dict[str, DesignParams] | None = None,
) -> tuple[float, float]:
    """Fisher CI: invert the randomization test over constant additive effects.

    Under H0: effect = tau0 (sharp, additive), y - tau0*z restores the null;
    the CI is the set of tau0 not rejected at level alpha. Bounds located by
    bisection from the point estimate outward.
    """
    y = np.asarray(y, float)
    z = np.asarray(z, int)
    if zmat is None:
        zmat = _build_zmat(
            session_ids,
            phases,
            n_draws,
            seed,
            all_phases,
            all_session_ids,
            analyzed_mask,
            design_params,
        )

    # Undefined statistic -> no interval. Returning [tau_hat, tau_hat] here
    # would advertise a zero-width 95% CI on a configuration that cannot be
    # tested at all (audit 30/08).
    if not np.isfinite(studentized_stat(y, z)):
        return float("nan"), float("nan")

    def pval(tau0: float) -> float:
        y_adj = y - tau0 * z
        return _p_from_stats(studentized_stat(y_adj, z), _batch_studentized(y_adj, zmat))

    tau_hat = diff_in_means(y, z)
    spread = max(float(np.std(y)) * 4, 1e-6)

    def rejects(tau0: float) -> bool:
        """Reject only on a DEFINED p-value below alpha.

        A NaN p (undefined statistic at this tau0) is not a rejection —
        treating it as one used to let an isolated numerical dip terminate the
        expansion and collapse the interval.
        """
        p_val = pval(tau0)
        return bool(np.isfinite(p_val)) and p_val < alpha

    def search(direction: int) -> float:
        lo, hi = tau_hat, tau_hat + direction * spread
        # Expand until rejected. Require TWO consecutive rejecting points
        # before accepting the bracket: the Monte-Carlo p-surface is noisy and
        # a single dip below alpha is not evidence the true bound is here.
        bracketed = False
        for _ in range(30):
            if rejects(hi) and rejects(hi + direction * spread * 0.25):
                bracketed = True
                break
            hi += direction * spread
        if not bracketed:
            # Never rejected within a wide range: the bound is not identified
            # by this data. Report an open side rather than a fabricated one.
            return float("-inf") if direction < 0 else float("inf")
        for _ in range(40):
            mid = (lo + hi) / 2
            if rejects(mid):
                hi = mid
            else:
                lo = mid
        return lo

    return search(-1), search(+1)


_OUTCOME_MODES = ("ratio", "linearized")
_ADJUST_MODES = ("none", "cuped_mv")


def _analysis_outcome(
    y: np.ndarray,
    session_ids: np.ndarray,
    outcome_mode: str,
    clicks: np.ndarray | None,
    exposures: np.ndarray | None,
    adjust: str,
    covariates: np.ndarray | None,
) -> np.ndarray:
    """Build the vector the randomization test actually runs on.

    Two OPTIONAL, off-by-default transforms, applied in this order:

    1. ``outcome_mode="linearized"`` replaces the per-block rate with Deng's
       linearized ratio L_b = clicks_b − r0·exposures_b, r0 being the pooled
       ratio of the OBSERVED sample (pinned once — see
       :func:`livelift.analysis.adjust.linearize_ratio`).
    2. ``adjust="cuped_mv"`` subtracts the fit of the deterministic covariate
       matrix (multivariate CUPED).

    Both produce a vector that is FIXED before any assignment is redrawn — r0
    comes from the recorded sample, the covariates are functions of the schedule
    and the clock, and theta is fitted on the recorded outcome. That is the
    whole reason they are admissible: randomization inference stays exact
    because only z moves between draws.
    """
    if outcome_mode not in _OUTCOME_MODES:
        raise ValueError(f"outcome_mode phải thuộc {_OUTCOME_MODES} (nhận {outcome_mode!r})")
    if adjust not in _ADJUST_MODES:
        raise ValueError(f"adjust phải thuộc {_ADJUST_MODES} (nhận {adjust!r})")

    out = y
    if outcome_mode == "linearized":
        if clicks is None or exposures is None:
            raise ValueError(
                "outcome_mode='linearized' cần cả clicks và exposures theo khối — "
                "tuyến tính hóa tỷ lệ không suy ra được từ y đã chia sẵn"
            )
        clicks_arr = np.asarray(clicks, float)
        exposures_arr = np.asarray(exposures, float)
        r0 = observed_ratio(clicks_arr, exposures_arr)
        if not np.isfinite(r0):
            raise ValueError("tổng exposure bằng 0 — không có tỷ lệ quan sát r0 để tuyến tính hóa")
        out = linearize_ratio(clicks_arr, exposures_arr, r0)

    if adjust == "cuped_mv":
        if covariates is None:
            raise ValueError(
                "adjust='cuped_mv' cần covariates — ma trận hiệp biến TẤT ĐỊNH "
                "(build_deterministic_covariates); lag trong-phiên bị cấm (§5c)"
            )
        out = cuped_adjust_mv(out, np.asarray(covariates, float), session_ids).y_adj
    return np.asarray(out, float)


def analyze_outer(
    y: np.ndarray,
    z: np.ndarray,
    session_ids: np.ndarray,
    phases: list[str],
    alpha: float = 0.05,
    n_draws: int = 2000,
    seed: int = 12345,
    all_phases: list[str] | None = None,
    all_session_ids: np.ndarray | None = None,
    analyzed_mask: np.ndarray | None = None,
    design_params: dict[str, DesignParams] | None = None,
    outcome_mode: str = "ratio",
    clicks: np.ndarray | None = None,
    exposures: np.ndarray | None = None,
    adjust: str = "none",
    covariates: np.ndarray | None = None,
) -> RandomizationResult:
    """Full primary analysis: point estimates, p-value, Fisher CI.

    ``all_phases`` / ``all_session_ids`` / ``analyzed_mask`` describe the FULL
    schedule when some blocks were dropped from the analysis (never aired, too
    little exposure). Pass them whenever blocks were excluded: the reference
    distribution must be redrawn over the design that actually ran, not over
    the surviving subset.

    ``design_params`` maps session_id → the session's PERSISTED
    :class:`DesignParams` (``livelift.api.service.rebuild_design_params``).
    Pass it whenever any session ran a non-default design: the redraws then
    honor that session's own p / ``min_per_arm_per_phase`` /
    ``min_transition_pairs`` / ``max_redraws`` instead of silently
    rerandomizing the default design.

    When either arm holds fewer than ``MIN_BLOCKS_PER_ARM`` blocks the design
    cannot be tested at all; the result is returned with ``estimable=False``,
    NaN inference fields and a Vietnamese ``reason``. Publishing anything else
    in that case would present pure noise as a significant finding.

    SENSITIVITY PATHS (gói P3+P4, 09/09 — added before the week-6 freeze, both
    OFF by default so the pre-registered primary analysis is bit-for-bit what
    it was):

    - ``outcome_mode='linearized'`` (needs ``clicks`` and ``exposures``): runs
      the ENTIRE pipeline — redraws, studentized statistic, Fisher CI — on
      Deng's linearized ratio instead of the per-block rate, which is the
      honest estimand if the intervention moves viewer-seconds
      (:func:`livelift.analysis.robust.ics_gate` is the test for that). The
      returned ``estimate``/``ci_*`` are then in LINEARIZED CLICK units and must
      not be printed next to the primary number.
    - ``adjust='cuped_mv'`` (needs ``covariates``): multivariate CUPED over the
      deterministic schedule/clock matrix before testing. Turning this on for
      the confirmatory result is a PRE-REGISTRATION decision for the team, not
      a default a caller may flip.

    ``covariates`` must satisfy PREREGISTRATION §5c (fixed at schedule-draw
    time); pass
    :func:`livelift.analysis.adjust.build_deterministic_covariates`. Both
    transforms leave the outcome vector fixed across redraws, so the test stays
    exact.
    """
    y = np.asarray(y, float)
    z = np.asarray(z, int)
    y = _analysis_outcome(
        y, np.asarray(session_ids), outcome_mode, clicks, exposures, adjust, covariates
    )
    n_on, n_off = int(z.sum()), int(len(z) - z.sum())
    if min(n_on, n_off) < MIN_BLOCKS_PER_ARM:
        return RandomizationResult(
            estimate=diff_in_means(y, z),
            estimate_ht=ht_effect(y, z, 0.5),
            p_value=float("nan"),
            ci_low=float("nan"),
            ci_high=float("nan"),
            n_blocks=len(y),
            n_on=n_on,
            n_off=n_off,
            n_draws=0,
            estimable=False,
            reason=(
                f"Mỗi nhánh cần ít nhất {MIN_BLOCKS_PER_ARM} khối để kiểm định "
                f"(hiện có BẬT {n_on} / TẮT {n_off}) — chưa ước lượng được"
            ),
            outcome_mode=outcome_mode,
            adjust=adjust,
        )
    p, zmat = randomization_test(
        y,
        z,
        session_ids,
        phases,
        n_draws,
        seed,
        all_phases=all_phases,
        all_session_ids=all_session_ids,
        analyzed_mask=analyzed_mask,
        design_params=design_params,
    )
    lo, hi = randomization_ci(y, z, session_ids, phases, alpha, n_draws, seed, zmat=zmat)
    return RandomizationResult(
        estimate=diff_in_means(y, z),
        estimate_ht=ht_effect(y, z, 0.5),
        p_value=p,
        ci_low=lo,
        ci_high=hi,
        n_blocks=len(y),
        n_on=int(z.sum()),
        n_off=int(len(z) - z.sum()),
        n_draws=zmat.shape[0],
        outcome_mode=outcome_mode,
        adjust=adjust,
    )


# ---------------------------------------------------------------------------
# LATE under partial compliance (suggest mode / partner rooms)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LATEResult:
    late: float
    se: float
    itt: float
    first_stage: float  # compliance difference E[D|Z=1] - E[D|Z=0]


def late_wald(y: np.ndarray, z: np.ndarray, d: np.ndarray) -> LATEResult:
    """Wald / IV estimator: assignment Z instruments actual treatment D.

    LATE = ITT / first-stage. Delta-method SE. Refuse (nan) when the first
    stage is weak (< 0.1) — report ITT only in that case.
    """
    y = np.asarray(y, float)
    z = np.asarray(z, int)
    d = np.asarray(d, float)
    y1, y0 = y[z == 1], y[z == 0]
    d1, d0 = d[z == 1], d[z == 0]
    itt = y1.mean() - y0.mean()
    fs = d1.mean() - d0.mean()
    if abs(fs) < 0.1:
        return LATEResult(float("nan"), float("nan"), float(itt), float(fs))
    late = itt / fs
    # delta method: var(itt)/fs^2 + itt^2 * var(fs) / fs^4 - 2*itt*cov/fs^3
    v_itt = y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0)
    v_fs = d1.var(ddof=1) / len(d1) + d0.var(ddof=1) / len(d0)
    cov1 = np.cov(y1, d1, ddof=1)[0, 1] / len(y1) if len(y1) > 1 else 0.0
    cov0 = np.cov(y0, d0, ddof=1)[0, 1] / len(y0) if len(y0) > 1 else 0.0
    cov = cov1 + cov0
    var = v_itt / fs**2 + itt**2 * v_fs / fs**4 - 2 * itt * cov / fs**3
    return LATEResult(float(late), float(np.sqrt(max(var, 0.0))), float(itt), float(fs))


# ---------------------------------------------------------------------------
# Moved out (gói P5a, 2026-09-08) — re-exported at the top of this module so
# ``from livelift.analysis.estimators import ...`` keeps working unchanged:
#   OLSResult, ols_fe_lin  -> livelift.analysis.robust
#   cuped_adjust           -> livelift.analysis.adjust
# New work on those two families goes to the new modules, not here.
#
# Gói P3+P4 (2026-09-09) kept that rule: `linearize_ratio`, `observed_ratio`,
# `cuped_adjust_mv` and `build_deterministic_covariates` were written in
# `adjust.py`, `ics_gate` in `robust.py`, and this file only gained the two
# opt-in switches of `analyze_outer` that route the outcome through them. They
# are imported, NOT re-exported: `__all__` above is the pre-split public API and
# stays frozen, so the P5a guard tests keep meaning what they meant.
# ---------------------------------------------------------------------------
