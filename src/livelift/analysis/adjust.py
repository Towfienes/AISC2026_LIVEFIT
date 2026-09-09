"""Covariate adjustment of the block-level outcome (CUPED family).

Split out of :mod:`livelift.analysis.estimators` on 2026-09-08 (gói P5a) so the
adjustment work of the 2026-09-07 programme (CUPED-mv, ratio-metric
linearization) lands here instead of piling onto the file that also holds the
primary randomization test. ``estimators`` re-exports the classic
:func:`cuped_adjust`, so no import site changed.

What belongs in this module: anything that transforms the OUTCOME using
pre-treatment information before it reaches an estimator. The admissibility
rule is shared by every member of the family and is the reason they live
together: a covariate is valid only if it was FIXED at schedule-draw time
(PREREGISTRATION.md §5c). Adding a second covariate or a delta-method
linearization does not relax that rule.

Contents (gói P3+P4, 2026-09-09 — added BEFORE the week-6 pre-registration
freeze, every one of them on a SENSITIVITY path that is off by default):

- :func:`observed_ratio` / :func:`linearize_ratio` — Deng's delta-method
  linearization of a ratio metric, for the case where the intervention can move
  the DENOMINATOR (viewer-seconds) and not only the numerator (clicks).
- :func:`delta_var_ratio` — the clustered delta-method variance of the pooled
  ratio. DESCRIPTIVE ONLY (see its docstring): at this experiment's cluster
  count it is not a credible interval.
- :func:`build_deterministic_covariates` — the only covariate matrix that is
  admissible under §5c without further argument, because every column is a
  function of the SCHEDULE and the CLOCK alone.
- :func:`cuped_adjust_mv` — multivariate (ridge) CUPED over that matrix.

References:

- Deng, Xu, Kohavi & Walker, "Improving the sensitivity of online controlled
  experiments by utilizing pre-experiment data", WSDM 2013, §3.2 (classic
  CUPED, :func:`cuped_adjust`).
- Deng, Knoblich & Lu, "Applying the Delta Method in Metric Analytics", KDD
  2018 / arXiv:1803.06336 (ratio metrics, clustered delta-method variance,
  linearization — :func:`linearize_ratio`, :func:`delta_var_ratio`).
- arXiv:2608.24038 (CUPED-mv), read for :func:`cuped_adjust_mv`: multiple
  covariates with a shrinkage estimate of theta and out-of-fold selection.
- arXiv:2606.27662 (regime map), read for the small-cluster caveat repeated in
  :func:`delta_var_ratio`.

Every formula below is written out in its own docstring so it can be checked
without opening the paper (HARNESS §4). Research note:
``docs/research-log.md``, entry 2026-09-09.

Pure NumPy — no I/O, no hidden RNG.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

__all__ = [
    "COVARIATE_NAMES",
    "LOCAL_TZ",
    "SPLINE_KNOT_MIN",
    "CupedMVResult",
    "build_deterministic_covariates",
    "cuped_adjust",
    "cuped_adjust_mv",
    "delta_var_ratio",
    "linearize_ratio",
    "observed_ratio",
]


def cuped_adjust(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float]:
    """Classic CUPED: y_adj = y - theta*(x - mean(x)).

    Returns (adjusted outcome, variance reduction share). ``x`` must be fixed
    at schedule-draw time (PREREGISTRATION.md §5c): valid covariates are
    pre-SESSION history — viewers at room open, host / platform / weekday /
    time-slot features — or deterministic schedule covariates (block index,
    normalized position t/T, phase, block length). Previous-block metrics
    (``pre_viewers``, ``pre_comment_rate``, ``pre_like_rate``) are NOT valid:
    block k-1 was itself randomized and rerandomization correlates adjacent
    assignments (measured −0.169), so they are post-treatment and would bias
    the estimate.
    """
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    vx = x.var(ddof=1)
    if vx == 0:
        return y.copy(), 0.0
    theta = np.cov(y, x, ddof=1)[0, 1] / vx
    y_adj = y - theta * (x - x.mean())
    vr = 1.0 - y_adj.var(ddof=1) / y.var(ddof=1) if y.var(ddof=1) > 0 else 0.0
    return y_adj, float(vr)


# ---------------------------------------------------------------------------
# P3 — ratio metric with an ENDOGENOUS denominator (Deng, arXiv:1803.06336)
# ---------------------------------------------------------------------------


def observed_ratio(clicks: np.ndarray, exposures: np.ndarray) -> float:
    """Pooled ratio r0 = sum(clicks) / sum(exposures) OF THE OBSERVED SAMPLE.

    This is the constant that :func:`linearize_ratio` pins. Returns NaN when
    total exposure is zero — there is no ratio to speak of, and a 0/0 must not
    be silently turned into 0.0.
    """
    total_x = float(np.asarray(exposures, float).sum())
    if total_x <= 0:
        return float("nan")
    return float(np.asarray(clicks, float).sum()) / total_x


def linearize_ratio(clicks: np.ndarray, exposures: np.ndarray, r0: float) -> np.ndarray:
    """Delta-method linearization of the ratio metric: L_b = clicks_b − r0·exposures_b.

    Deng, Knoblich & Lu (KDD 2018 / arXiv:1803.06336): a ratio of sums
    R = ΣY_b / ΣX_b is not an average of per-unit values, so it cannot be fed
    to a unit-level estimator directly. The linearized value L_b makes the
    ratio behave like an ordinary additive metric — mean(L) = 0 at r0 = R by
    construction, and a difference in mean L between arms is, to first order,
    the ratio contrast times mean exposure.

    WHY IT MATTERS HERE: the primary outcome divides valid clicks by
    viewer-seconds. Viewer-seconds are POST-TREATMENT — pinning a card can
    plausibly change how many people stay in the room — so the denominator is
    not guaranteed exogenous. When it is not, the per-block rate y_b answers a
    different question from the pooled ratio, and the honest fallback is a
    fixed-denominator estimand: exactly what L_b with a PINNED r0 gives.

    PRE-REGISTERED CONVENTION FOR r0 (PREREGISTRATION §5e, added 09/09 before
    the freeze). ``r0`` is the pooled ratio of the OBSERVED sample
    (:func:`observed_ratio`) and is FIXED — computed ONCE from the data as it
    was recorded, then held constant across every randomization redraw, every
    Fisher-CI grid point and every bootstrap replicate. It is a property of the
    sample, not of an assignment vector. Recomputing r0 inside a redraw would
    make the outcome vector move with the assignment being tested and destroy
    the exactness of the randomization test — the whole reason the primary
    inference is design-based. The caller therefore passes r0 explicitly rather
    than letting this function derive it per call.

    UNITS. L_b is in CLICKS (clicks minus the clicks the pooled rate predicts
    for that block's exposure), NOT in the primary unit "valid clicks per 1000
    viewer-seconds". An estimate produced on the linearized path must never be
    printed next to, or compared numerically with, the primary estimate; only
    its sign and its significance are comparable.
    """
    clicks = np.asarray(clicks, float)
    exposures = np.asarray(exposures, float)
    if clicks.shape != exposures.shape:
        raise ValueError(
            f"clicks và exposures phải cùng độ dài (nhận {clicks.shape} và {exposures.shape})"
        )
    return clicks - float(r0) * exposures


def delta_var_ratio(clicks: np.ndarray, exposures: np.ndarray, cluster_ids: np.ndarray) -> float:
    """Clustered delta-method variance of the pooled ratio R = ΣY / ΣX.

    Formula (Deng, Knoblich & Lu, KDD 2018 / arXiv:1803.06336, the ratio-metric
    delta-method result — eq. (6) in the arXiv version), written out here so it
    can be checked without opening the paper. With clusters k = 1..K, cluster
    totals Y_k and X_k, R = ΣY_k / ΣX_k and L_k = Y_k − R·X_k:

        Var(R̂) ≈ K · Σ_k L_k²  /  ((K − 1) · (Σ_k X_k)²)

    which is the usual delta expansion
    Var(Ȳ/X̄) ≈ (1/X̄²)·Var(Ȳ − R·X̄) / K after substituting X̄ = ΣX_k / K and
    using Σ_k L_k = 0 (so the sample mean of L_k is exactly zero).

    CLUSTER = SESSION, never the block and never the click: session-level shocks
    (a good host night, a platform push) dominate, and treating blocks as
    independent would understate this variance badly.

    *** DESCRIPTIVE ONLY — NOT A CONFIDENCE INTERVAL FOR THIS EXPERIMENT. ***
    This is a normal-approximation variance whose coverage relies on a
    cluster count large enough for a CLT over clusters. The pre-registered
    sample is K = 18–31 sessions (PREREGISTRATION §6), which sits inside the
    regime where that approximation is measurably off (arXiv:2606.27662): with
    a couple of dozen clusters a nominal 95% interval built this way routinely
    covers well under 95%. It is provided to DESCRIBE the variance decomposition
    (how much of the ratio's uncertainty is between-session), to sanity-check
    other variance machinery, and to be reported as a diagnostic. The primary
    interval remains the Fisher CI from randomization inference
    (:func:`livelift.analysis.estimators.randomization_ci`), which needs no
    cluster CLT at all.

    Returns NaN when there are fewer than two clusters or no exposure.
    """
    clicks = np.asarray(clicks, float)
    exposures = np.asarray(exposures, float)
    cid = np.asarray(cluster_ids)
    if not (clicks.shape == exposures.shape == cid.shape):
        raise ValueError("clicks, exposures và cluster_ids phải cùng độ dài")
    total_x = float(exposures.sum())
    keys = np.unique(cid)
    n_clusters = len(keys)
    if n_clusters < 2 or total_x <= 0:
        return float("nan")
    ratio = float(clicks.sum()) / total_x
    lin = np.array([float((clicks[cid == k] - ratio * exposures[cid == k]).sum()) for k in keys])
    return float(n_clusters * np.sum(lin**2) / ((n_clusters - 1) * total_x**2))


# ---------------------------------------------------------------------------
# P4 — multivariate CUPED over DETERMINISTIC (schedule + clock) covariates
# ---------------------------------------------------------------------------

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
"""Wall clock the hour-of-day covariate is expressed in.

Shopping behavior follows the LOCAL day (lunch break, after-work evening peak),
not UTC. Storage stays UTC (HARNESS §6); only this covariate converts.
"""

SPLINE_KNOT_MIN = 45.0
"""Single interior knot of the minute-into-session spline, in minutes.

45 minutes is a SCHEDULE constant, not a fitted one: it is roughly the midpoint
of the planned 90-minute session, so the two spline pieces describe "first
half" and "second half" of a session. Fitting the knot to the outcome would
make the covariate matrix depend on the data and forfeit the invariance the
next docstring relies on.
"""

COVARIATE_NAMES: tuple[str, ...] = (
    "sin_hour",
    "cos_hour",
    "t_min",
    "t_min_sq",
    "t_min_hinge45_sq",
)
"""Column order of :func:`build_deterministic_covariates`."""


def build_deterministic_covariates(
    blocks: Iterable[Mapping[str, Any]], tz: ZoneInfo = LOCAL_TZ
) -> np.ndarray:
    """(n, 5) matrix of covariates fixed at schedule-draw time.

    Columns (:data:`COVARIATE_NAMES`):

    1. ``sin_hour`` = sin(2π·h/24), 2. ``cos_hour`` = cos(2π·h/24), where h is
       the hour-of-day (fractional, local :data:`LOCAL_TZ`) of the block's REAL
       start time. A sin/cos pair is the smallest basis that is continuous
       across midnight — a raw "hour" column would claim 23:59 and 00:01 are 24
       units apart.
    3-5. A degree-2 spline of t = the minute of the BLOCK MIDPOINT into the
       session: ``t``, ``t²``, ``max(0, t − 45)²``. The hinge term lets the
       second half of a session bend differently from the first without adding
       a discontinuity.

    ADMISSIBILITY (PREREGISTRATION §5c). Every column is a function of the
    SESSION START TIME and the SCHEDULE offsets alone. Both are decided before
    the assignment vector is drawn, so the matrix is bit-identical under any
    redraw of the assignment: randomization inference on a CUPED-adjusted
    outcome built from these columns stays EXACT. This is the property that
    makes them usable at all, and it is asserted by a test that permutes the
    assignment and compares the matrix.

    FORBIDDEN, explicitly (§5c): any within-session lag — ``pre_viewers``,
    ``pre_comment_rate``, ``pre_like_rate``, or anything measured in block k−1
    or in this block's burn-in window. Those windows sit inside a block that was
    itself randomized (adjacent assignments are correlated at −0.169 under
    rerandomization), so they are POST-TREATMENT: adjusting on them biases the
    estimate and silently breaks the exactness above. No amount of measured
    variance reduction buys that back.

    ``blocks``: mappings carrying ``start_ts`` (timezone-AWARE datetime — the
    block's real wall-clock start) and ``start_offset_s`` (seconds from session
    start); ``end_offset_s`` is used for the midpoint when present. A naive
    datetime is refused rather than assumed to be UTC (HARNESS §6).
    """
    rows: list[list[float]] = []
    for i, block in enumerate(blocks):
        start_ts = block.get("start_ts")
        if not isinstance(start_ts, datetime):
            raise ValueError(
                f"khối {i}: thiếu 'start_ts' (thời điểm bắt đầu thật của khối) — "
                "không suy ra được giờ-trong-ngày"
            )
        if start_ts.tzinfo is None or start_ts.utcoffset() is None:
            raise ValueError(
                f"khối {i}: 'start_ts' không có múi giờ — dự án cấm datetime naive "
                "(HARNESS §6); truyền datetime có tzinfo (UTC từ DB)"
            )
        local = start_ts.astimezone(tz)
        hour = local.hour + local.minute / 60.0 + local.second / 3600.0
        angle = 2.0 * np.pi * hour / 24.0
        start_s = float(block["start_offset_s"])
        end_s = float(block.get("end_offset_s", start_s))
        t_min = (start_s + end_s) / 2.0 / 60.0
        hinge = max(0.0, t_min - SPLINE_KNOT_MIN)
        rows.append(
            [float(np.sin(angle)), float(np.cos(angle)), t_min, t_min * t_min, hinge * hinge]
        )
    return np.asarray(rows, dtype=float).reshape(len(rows), len(COVARIATE_NAMES))


@dataclass(frozen=True)
class CupedMVResult:
    """Adjusted outcome plus the diagnostics needed to judge whether to use it."""

    y_adj: np.ndarray
    theta: np.ndarray  # in the ORIGINAL covariate scale; applies to (x - x̄)
    lambda_chosen: float
    r2_in_sample: float
    """In-sample R² of the covariate fit — OPTIMISTIC, reported for contrast."""
    r2_cv: float
    """Leave-one-SESSION-out R². The honest number: negative means the
    covariates predict worse than the grand mean out of session, i.e. the
    adjustment is fitting session noise. NaN when CV was not possible."""
    se_ratio: float
    """sqrt(var(y_adj)/var(y)) — the ESTIMATED standard-error ratio. Below 1 is
    a reduction. Estimated on the same sample that fitted theta, so it is a
    lower bound on the SE you will actually pay."""
    n_sessions: int
    cv_available: bool
    fold_thetas: tuple[np.ndarray, ...]
    """theta from each leave-one-session-out fold at the chosen lambda. Spread
    across folds is the practical test of whether theta means anything."""


def _ridge_fit(x: np.ndarray, y: np.ndarray, lam: float) -> tuple[np.ndarray, np.ndarray, float]:
    """Closed-form ridge on standardized covariates; theta returned in the
    ORIGINAL scale. Returns (theta, x_mean, y_mean).

    Standardization matters: the ridge penalty is NOT scale-invariant, and the
    raw columns here span minutes (~0-90) to minutes squared (~0-8100), so an
    unstandardized penalty would shrink the quadratic terms almost to zero
    whatever lambda says. The Gram matrix is divided by n as well, which puts
    lambda on the correlation scale so the same grid means the same amount of
    shrinkage regardless of how many blocks are pooled.
    """
    n = len(y)
    x_mean = x.mean(axis=0)
    xc = x - x_mean
    sd = xc.std(axis=0)
    live = sd > 1e-12
    scale = np.where(live, sd, 1.0)
    xs = xc / scale
    xs[:, ~live] = 0.0
    y_mean = float(y.mean())
    gram = xs.T @ xs / n + lam * np.eye(x.shape[1])
    theta_s = np.linalg.solve(gram, xs.T @ (y - y_mean) / n)
    theta_s = np.where(live, theta_s, 0.0)
    return theta_s / scale, x_mean, y_mean


def cuped_adjust_mv(
    y: np.ndarray,
    x: np.ndarray,
    session_ids: np.ndarray,
    ridge_lambdas: Sequence[float] = (0.1, 1.0, 10.0),
) -> CupedMVResult:
    """Multivariate CUPED: Ỹ = y − θ̂ᵀ(x − x̄), θ̂ by ridge with leave-one-session-out CV.

    ``x`` must be the DETERMINISTIC covariate matrix of
    :func:`build_deterministic_covariates` (or any matrix satisfying the same
    §5c rule). The whole method rests on that: because x is a function of the
    schedule and the clock only, and y is the recorded outcome, Ỹ is FIXED
    before any assignment is redrawn. Randomization inference run on Ỹ is
    therefore still EXACT — the reference distribution redraws z while the
    outcome vector stands still, exactly as on the unadjusted path.
    (The same argument is what forbids within-session lags here; see
    :func:`build_deterministic_covariates`.)

    Why ridge and why leave-one-SESSION-out. Five covariates fitted on a few
    hundred correlated blocks from a couple of dozen sessions overfit easily,
    and ordinary K-fold CV would leak: blocks of one session share its shocks,
    so a random fold puts near-duplicates on both sides and reports a variance
    reduction that will not survive the next session. Holding out whole
    sessions asks the question that matters — does this adjustment help on a
    session it has never seen? Lambda is picked by minimizing that
    out-of-session squared error over ``ridge_lambdas``. Sources: arXiv:2608.24038
    (CUPED-mv) for the multivariate/shrinkage form.

    READ ``r2_cv`` BEFORE USING THIS. PREREGISTRATION §5c already records the
    measurement that on the calibrated simulator the within-session variance is
    essentially all Poisson counting noise (CV 0.352 vs floor 0.356, reducible
    share ≈ 0). In that regime NO covariate can help and this function will
    correctly return se_ratio ≈ 1 and r2_cv ≈ 0 or below. It earns its keep only
    if the real sessions turn out to carry a systematic diurnal / position
    signal that the simulator does not model.

    With fewer than two sessions the CV cannot run at all; the function then
    falls back to the LARGEST lambda offered (the most shrinkage, i.e. the
    least adjustment) and flags ``cv_available=False`` rather than picking a
    lambda by looking at in-sample fit, which would always choose the smallest.
    """
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    if x.ndim == 1:
        x = x[:, None]
    sess = np.asarray(session_ids)
    if x.shape[0] != len(y) or len(sess) != len(y):
        raise ValueError(
            f"y, x và session_ids phải cùng số hàng (nhận {len(y)}, {x.shape[0]}, {len(sess)})"
        )
    lambdas = tuple(float(v) for v in ridge_lambdas)
    if not lambdas:
        raise ValueError("ridge_lambdas rỗng — cần ít nhất một giá trị λ")

    keys = list(np.unique(sess))
    n_sessions = len(keys)
    tss = float(((y - y.mean()) ** 2).sum())

    def loso_sse(lam: float) -> tuple[float, list[np.ndarray]]:
        sse = 0.0
        thetas: list[np.ndarray] = []
        for k in keys:
            held = sess == k
            train = ~held
            if train.sum() < 2:
                continue
            theta, x_mean, y_mean = _ridge_fit(x[train], y[train], lam)
            thetas.append(theta)
            pred = y_mean + (x[held] - x_mean) @ theta
            sse += float(((y[held] - pred) ** 2).sum())
        return sse, thetas

    cv_available = n_sessions >= 2
    if cv_available:
        scored = [(loso_sse(lam)[0], lam) for lam in lambdas]
        best_sse, lambda_chosen = min(scored, key=lambda pair: (pair[0], pair[1]))
        _, fold_thetas = loso_sse(lambda_chosen)
        r2_cv = 1.0 - best_sse / tss if tss > 0 else float("nan")
    else:
        lambda_chosen = max(lambdas)
        fold_thetas = []
        r2_cv = float("nan")

    theta, x_mean, y_mean = _ridge_fit(x, y, lambda_chosen)
    y_adj = y - (x - x_mean) @ theta
    resid = y - (y_mean + (x - x_mean) @ theta)
    r2_in = 1.0 - float((resid**2).sum()) / tss if tss > 0 else float("nan")
    var_y = float(y.var(ddof=1)) if len(y) > 1 else 0.0
    se_ratio = float(np.sqrt(y_adj.var(ddof=1) / var_y)) if var_y > 0 else 1.0
    return CupedMVResult(
        y_adj=y_adj,
        theta=theta,
        lambda_chosen=float(lambda_chosen),
        r2_in_sample=r2_in,
        r2_cv=float(r2_cv),
        se_ratio=se_ratio,
        n_sessions=n_sessions,
        cv_available=cv_available,
        fold_thetas=tuple(fold_thetas),
    )
