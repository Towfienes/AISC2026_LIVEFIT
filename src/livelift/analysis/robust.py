"""Regression-adjusted secondary estimator and its cluster-robust variance.

Split out of :mod:`livelift.analysis.estimators` on 2026-09-08 (gói P5a) so the
robust-variance work of the 2026-09-07 programme (wild cluster bootstrap,
imposed-null / ICS refinements for the small number of session clusters) lands
here rather than on the file that also holds the primary randomization test.
``estimators`` re-exports everything below, so no import site changed.

What belongs in this module: the MODEL-BASED arm of the analysis — a
regression estimate plus whatever machinery makes its standard error credible
with few clusters. It is the secondary, never the primary: the primary number
comes from randomization inference over the design that was actually run
(:mod:`livelift.analysis.estimators`), which needs no variance model at all.
Keeping the two arms in separate files makes it harder to quietly promote a
model-based interval into the headline.

Also here (gói P3, 2026-09-09): :func:`ics_gate`, the denominator-endogeneity
check. It is not a variance estimator, but it belongs to the same family — it
exists to say whether the credible reading of the primary number needs a
different estimand, and like everything else in this file it is a diagnostic
that must never be promoted to the headline.

References: Lin, "Agnostic notes on regression adjustments to experimental
data", Annals of Applied Statistics 7(1), 2013; Cameron, Gelbach & Miller,
"Bootstrap-based improvements for inference with clustered errors", REStat
90(3), 2008, for the CR1 correction used below; arXiv:2510.01127 (ICS) for
:func:`ics_gate`.

Pure NumPy — no I/O, no hidden RNG.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

__all__ = ["ICSGate", "OLSResult", "ics_gate", "ols_fe_lin"]


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
# P3 — is the DENOMINATOR itself moved by the intervention? (ICS gate)
# ---------------------------------------------------------------------------

ICS_ALPHA = 0.10
"""Flag level of :func:`ics_gate`.

Deliberately LOOSER than the 0.05 of the primary test and the 0.005 of the
post-session QC family. This gate does not reject a hypothesis anybody wants to
believe; it decides whether a caveat gets printed next to the result. Missing a
real denominator effect (reporting a ratio as if its denominator were fixed)
costs far more than printing one caveat too often, so the error rates are
tilted on purpose.
"""

ICS_FLAGGED_MESSAGE = (
    "mẫu số có dấu hiệu chịu can thiệp (p < 0,10) → đọc kèm estimand mẫu-số-cố-định"
)
ICS_CLEAR_MESSAGE = (
    "chưa thấy dấu hiệu mẫu số chịu can thiệp — KHÔNG phải bằng chứng mẫu số ngoại sinh"
)
ICS_UNTESTABLE_MESSAGE = "không kiểm định được mẫu số (thiết kế quá nhỏ để studentize)"


@dataclass(frozen=True)
class ICSGate:
    """Outcome of the denominator-endogeneity check. ``message`` is user-facing."""

    p_value: float  # NaN when the design cannot be tested at all
    estimate: float  # mean exposure ON − mean exposure OFF, in viewer-seconds
    n_draws: int
    alpha: float
    flagged: bool
    message: str


def ics_gate(
    exposures: np.ndarray,
    z: np.ndarray,
    redraw_fn: Callable[[np.ndarray, np.ndarray], tuple[float, np.ndarray]],
    alpha: float = ICS_ALPHA,
) -> ICSGate:
    """Randomization test with the DENOMINATOR as the outcome (arXiv:2510.01127).

    The primary metric is valid clicks per 1000 viewer-seconds. That division is
    only innocent if viewer-seconds are unaffected by the intervention. They are
    not obviously so: pinning a product card is a visible change to the room,
    and it can plausibly hold viewers or drive them away. If it does, the
    per-block rate and the pooled ratio answer different questions, and the
    contrast that survives is the FIXED-DENOMINATOR one
    (:func:`livelift.analysis.adjust.linearize_ratio` with a pinned r0).

    So: run exactly the pre-registered primary test — the production redraws,
    the studentized statistic, the same p-value machinery — but with
    ``exposures`` in place of y. A small p says the assignment moves the
    denominator.

    ``redraw_fn(y, z) -> (p_value, zmat)`` is the production randomization test
    with the session ids / phases / full schedule / persisted DesignParams
    already bound; in the API path that is
    :func:`livelift.analysis.estimators.randomization_test` under a partial.
    It is INJECTED rather than imported: ``estimators`` imports this module, so
    importing back would be a circular import, and the one-way dependency edge
    is what keeps this file editable without reopening the primary test
    (guarded by ``tests/test_estimators.py::
    test_new_modules_never_import_back_from_estimators``).

    THIS IS NOT AN SRM CHECK, and it must not be filed with them.
    PREREGISTRATION §8.1 forbids running SRM on viewers / comments / clicks
    precisely because they are post-treatment: an imbalance there is the effect
    the experiment is measuring, not a pipeline fault. Exposure is post-treatment
    in exactly that sense. The difference is what the flag MEANS: an SRM failure
    says "the data is broken, investigate the pipeline"; this gate says "the
    estimand needs a footnote". Nothing here excludes a block, drops a session
    or changes the primary number (flag-don't-drop, HARNESS §3) — the only
    consequence is which estimand the reader is told to read alongside.

    A non-significant result is NOT evidence that the denominator is exogenous:
    with a few dozen sessions this test has little power against a small
    denominator effect, and ``ICS_CLEAR_MESSAGE`` says so rather than granting a
    clean bill of health.
    """
    exposures = np.asarray(exposures, float)
    z = np.asarray(z, int)
    if exposures.shape != z.shape:
        raise ValueError(f"exposures và z phải cùng độ dài (nhận {exposures.shape} và {z.shape})")
    p_value, zmat = redraw_fn(exposures, z)
    n_on = int(z.sum())
    n_off = int(len(z) - n_on)
    if n_on and n_off:
        estimate = float(exposures[z == 1].mean() - exposures[z == 0].mean())
    else:
        estimate = float("nan")
    n_draws = int(np.asarray(zmat).shape[0]) if zmat is not None else 0
    if not np.isfinite(p_value):
        return ICSGate(
            p_value=float("nan"),
            estimate=estimate,
            n_draws=n_draws,
            alpha=float(alpha),
            flagged=False,
            message=ICS_UNTESTABLE_MESSAGE,
        )
    flagged = bool(p_value < alpha)
    return ICSGate(
        p_value=float(p_value),
        estimate=estimate,
        n_draws=n_draws,
        alpha=float(alpha),
        flagged=flagged,
        message=ICS_FLAGGED_MESSAGE if flagged else ICS_CLEAR_MESSAGE,
    )
