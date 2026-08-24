"""Design-based estimation and randomization inference for the outer tier.

Pre-registered analysis pipeline (docs/research/2026-08-24-estimators.md):

- Unit of analysis: the BLOCK. Cluster: the SESSION. Never click-level rows.
- Primary test: randomization inference with a STUDENTIZED difference
  statistic, re-drawing assignments with the production assignment mechanism
  (:func:`livelift.core.assigner.outer.draw_assignments`) independently per
  session — the reference distribution therefore matches the actual design
  exactly (Bojinov & Shephard, JASA 2019).
- Point estimators: Horvitz–Thompson / inverse-propensity (design-based, fewest
  assumptions) and OLS with session fixed effects + Lin (2013) interacted
  covariates (variance-reduced). Report both.
- Confidence interval: inversion of the randomization test over a grid of
  constant additive effects (Fisher CI).
- LATE under partial compliance: Wald / IV estimator with assignment as the
  instrument, delta-method SE, first-stage compliance reported.
- CUPED-style covariate adjustment using pre-block covariates.

All functions are pure NumPy — no I/O, explicit seeds everywhere.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from livelift.core.assigner.outer import ON, draw_assignments

# ---------------------------------------------------------------------------
# Point estimators
# ---------------------------------------------------------------------------


def diff_in_means(y: np.ndarray, z: np.ndarray) -> float:
    y, z = np.asarray(y, float), np.asarray(z, int)
    if z.sum() == 0 or z.sum() == len(z):
        return float("nan")
    return float(y[z == 1].mean() - y[z == 0].mean())


def ht_effect(y: np.ndarray, z: np.ndarray, p: np.ndarray | float = 0.5) -> float:
    """Horvitz–Thompson estimate of the average block-level effect.

    With constant p=0.5 this reduces to 2*mean(y*z) - 2*mean(y*(1-z)); with
    per-block propensities (inner tier, holdback months) it stays unbiased.
    """
    y, z = np.asarray(y, float), np.asarray(z, int)
    p_arr = np.full_like(y, p) if np.isscalar(p) else np.asarray(p, float)
    n = len(y)
    return float((y * z / p_arr).sum() / n - (y * (1 - z) / (1 - p_arr)).sum() / n)


def studentized_stat(y: np.ndarray, z: np.ndarray) -> float:
    """Two-sample t-type statistic — studentization gives the randomization
    test better behavior under heteroskedasticity (Chung & Romano, 2013)."""
    y, z = np.asarray(y, float), np.asarray(z, int)
    y1, y0 = y[z == 1], y[z == 0]
    if len(y1) < 2 or len(y0) < 2:
        return float("nan")
    se = np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0))
    if se == 0:
        return 0.0
    return float((y1.mean() - y0.mean()) / se)


# ---------------------------------------------------------------------------
# Randomization inference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RandomizationResult:
    estimate: float  # difference in means (per-1000-viewer-second click rate)
    estimate_ht: float
    p_value: float
    ci_low: float
    ci_high: float
    n_blocks: int
    n_on: int
    n_off: int
    n_draws: int


def _redraw_matrix(
    session_ids: np.ndarray,
    phases: list[str],
    n_draws: int,
    seed: int,
) -> np.ndarray:
    """(n_draws, n_blocks) matrix of assignment redraws, using the production
    mechanism independently within each session."""
    rng = random.Random(seed)
    n = len(phases)
    sessions: dict = {}
    for i, s in enumerate(session_ids):
        sessions.setdefault(s, []).append(i)
    out = np.empty((n_draws, n), dtype=np.int8)
    for d in range(n_draws):
        for idx in sessions.values():
            arms, _ = draw_assignments([phases[i] for i in idx], rng)
            for i, arm in zip(idx, arms, strict=True):
                out[d, i] = 1 if arm == ON else 0
    return out


def _batch_studentized(y: np.ndarray, zmat: np.ndarray) -> np.ndarray:
    """Vectorized studentized statistic for every row of the redraw matrix."""
    y = np.asarray(y, float)
    n1 = zmat.sum(axis=1)
    n0 = zmat.shape[1] - n1
    s1 = zmat @ y
    s0 = y.sum() - s1
    m1, m0 = s1 / n1, s0 / n0
    q1 = zmat @ (y**2)
    q0 = (y**2).sum() - q1
    # unbiased variances
    v1 = (q1 - n1 * m1**2) / np.maximum(n1 - 1, 1)
    v0 = (q0 - n0 * m0**2) / np.maximum(n0 - 1, 1)
    se = np.sqrt(v1 / n1 + v0 / n0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(se > 0, (m1 - m0) / se, 0.0)


def randomization_test(
    y: np.ndarray,
    z: np.ndarray,
    session_ids: np.ndarray,
    phases: list[str],
    n_draws: int = 2000,
    seed: int = 12345,
    zmat: np.ndarray | None = None,
) -> tuple[float, np.ndarray]:
    """Two-sided randomization p-value for the sharp null of no effect.

    Returns (p_value, redraw_matrix) — the matrix can be reused for CI
    inversion so the expensive redraws happen once.
    """
    y = np.asarray(y, float)
    z = np.asarray(z, int)
    if zmat is None:
        zmat = _redraw_matrix(np.asarray(session_ids), list(phases), n_draws, seed)
    t_obs = studentized_stat(y, z)
    t_draws = _batch_studentized(y, zmat)
    # add-one correction keeps the p-value valid (never exactly 0)
    p = (1 + np.sum(np.abs(t_draws) >= abs(t_obs))) / (1 + len(t_draws))
    return float(p), zmat


def randomization_ci(
    y: np.ndarray,
    z: np.ndarray,
    session_ids: np.ndarray,
    phases: list[str],
    alpha: float = 0.05,
    n_draws: int = 2000,
    seed: int = 12345,
    zmat: np.ndarray | None = None,
) -> tuple[float, float]:
    """Fisher CI: invert the randomization test over constant additive effects.

    Under H0: effect = tau0 (sharp, additive), y - tau0*z restores the null;
    the CI is the set of tau0 not rejected at level alpha. Bounds located by
    bisection from the point estimate outward.
    """
    y = np.asarray(y, float)
    z = np.asarray(z, int)
    if zmat is None:
        zmat = _redraw_matrix(np.asarray(session_ids), list(phases), n_draws, seed)

    def pval(tau0: float) -> float:
        y_adj = y - tau0 * z
        t_obs = studentized_stat(y_adj, z)
        t_draws = _batch_studentized(y_adj, zmat)
        return (1 + np.sum(np.abs(t_draws) >= abs(t_obs))) / (1 + len(t_draws))

    tau_hat = diff_in_means(y, z)
    spread = max(float(np.std(y)) * 4, 1e-6)

    def search(direction: int) -> float:
        lo, hi = tau_hat, tau_hat + direction * spread
        # expand until rejected
        for _ in range(30):
            if pval(hi) < alpha:
                break
            hi += direction * spread
        else:
            return hi  # never rejected within range — CI effectively unbounded
        for _ in range(40):
            mid = (lo + hi) / 2
            if pval(mid) >= alpha:
                lo = mid
            else:
                hi = mid
        return lo

    return search(-1), search(+1)


def analyze_outer(
    y: np.ndarray,
    z: np.ndarray,
    session_ids: np.ndarray,
    phases: list[str],
    alpha: float = 0.05,
    n_draws: int = 2000,
    seed: int = 12345,
) -> RandomizationResult:
    """Full primary analysis: point estimates, p-value, Fisher CI."""
    y = np.asarray(y, float)
    z = np.asarray(z, int)
    p, zmat = randomization_test(y, z, session_ids, phases, n_draws, seed)
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
    )


# ---------------------------------------------------------------------------
# OLS with session fixed effects + Lin (2013) covariate interaction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OLSResult:
    estimate: float
    se_cluster: float
    n_blocks: int
    n_clusters: int


def ols_fe_lin(
    y: np.ndarray,
    z: np.ndarray,
    session_ids: np.ndarray,
    covariates: np.ndarray | None = None,
) -> OLSResult:
    """OLS of y on z with session fixed effects and Lin-interacted covariates,
    cluster-robust (CR1) standard errors by session.

    ``covariates``: (n, k) pre-treatment covariates (e.g. pre-block viewers,
    pre-block comment rate). They are globally centered, then included both as
    main effects and interacted with the centered treatment (Lin 2013), which
    cannot hurt asymptotic precision.
    """
    y = np.asarray(y, float)
    z = np.asarray(z, float)
    sess = np.asarray(session_ids)
    n = len(y)

    # within-session demeaning absorbs the session fixed effect
    def demean(v: np.ndarray) -> np.ndarray:
        out = v.astype(float).copy()
        for s in np.unique(sess):
            m = sess == s
            out[m] -= out[m].mean()
        return out

    y_t = demean(y)
    z_t = demean(z)
    cols = [z_t]
    if covariates is not None:
        x = np.asarray(covariates, float)
        if x.ndim == 1:
            x = x[:, None]
        x_c = x - x.mean(axis=0)
        x_t = np.column_stack([demean(x_c[:, j]) for j in range(x_c.shape[1])])
        zx = z_t[:, None] * x_c  # Lin interaction
        cols.extend([x_t, zx])
    design = np.column_stack(cols)

    beta, *_ = np.linalg.lstsq(design, y_t, rcond=None)
    resid = y_t - design @ beta
    bread = np.linalg.pinv(design.T @ design)

    clusters = np.unique(sess)
    meat = np.zeros((design.shape[1], design.shape[1]))
    for s in clusters:
        m = sess == s
        xg = design[m]
        ug = resid[m]
        v = xg.T @ ug
        meat += np.outer(v, v)
    g = len(clusters)
    k = design.shape[1]
    dof_correction = (g / max(g - 1, 1)) * ((n - 1) / max(n - k, 1))
    vcov = dof_correction * bread @ meat @ bread
    return OLSResult(
        estimate=float(beta[0]),
        se_cluster=float(np.sqrt(max(vcov[0, 0], 0.0))),
        n_blocks=n,
        n_clusters=g,
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
# CUPED
# ---------------------------------------------------------------------------


def cuped_adjust(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float]:
    """Classic CUPED: y_adj = y - theta*(x - mean(x)).

    Returns (adjusted outcome, variance reduction share). ``x`` must be
    pre-treatment (e.g. previous-block viewers) so the adjustment cannot leak
    treatment effect.
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
