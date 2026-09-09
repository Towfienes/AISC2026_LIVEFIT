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

The ORDER-count endpoint (gói Q4, PREREGISTRATION §4.2) reuses this same
machinery through :func:`order_mde_table`: orders are a rare count, so the CV
is the Poisson one (:func:`poisson_cv`) and the resulting MDE is a FLOOR, not a
forecast. Everything that enters it is a prior or an assumption and every row
of the generated report says so — see that function's docstring, in particular
the standing prohibition on mapping KuaiLive onto the purchase funnel.
"""

from __future__ import annotations

from collections.abc import Sequence
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


# ---------------------------------------------------------------------------
# Order-count MDE (gói Q4) — the SECONDARY endpoint of PREREGISTRATION §4.2
# ---------------------------------------------------------------------------

FUNNEL_PV_TO_CART = 0.0933
"""Prior: share of product page views that reach a cart.

Source: Taobao **UserBehavior** log (Alibaba Tianchi dataset #649, 100M
user-item interactions, Nov–Dec 2017) — the pv → cart step. This is a PRIOR
from a different platform and a different year, used to convert clicks into an
order-count SCENARIO. It is never presented as a LiveLift measurement.
"""

FUNNEL_CART_TO_BUY = 0.2433
"""Prior: share of carts that convert to a purchase (same Tianchi #649 log).

``FUNNEL_PV_TO_CART * FUNNEL_CART_TO_BUY`` ≈ 2.27% click → order overall.
Swept over :data:`Q2_GRID` because this is the step a livestream funnel departs
from most: the prior value sits between the 0.15 and 0.25 grid points.
"""

Q2_GRID: tuple[float, ...] = (0.15, 0.25, 0.35, 0.5)
"""Pre-registered sweep of the cart → buy step (q2) for the order-count table."""

PARTNER_AUDIENCE_MULTIPLIER = 4.9
"""Audience multiplier of the PARTNER branch, as a scenario (not a measurement).

Source: the live-streaming-e-commerce study arXiv:2106.03415, where sessions
run with an established seller/host draw an audience about 4.9× a self-run
session's. Applied to the audience grid only — the funnel and the click rate
stay identical, because nothing in that source speaks to either.
"""

FUNNEL_SOURCE_NOTE = (
    "Prior funnel: Taobao UserBehavior (Tianchi #649) pv→giỏ 9,33% × giỏ→mua 24,33%. "
    "Nhân khán giả nhánh đối tác ×4,9 (arXiv:2106.03415). "
    "KHÔNG dùng KuaiLive cho funnel: 'click' của KuaiLive là VÀO PHÒNG, không phải "
    "nhấp sản phẩm ghim — map sang phễu mua hàng là sai ngữ nghĩa."
)


def _measurement_block_seconds(
    session_minutes: int, block_min: int, endpoint_double: bool
) -> list[int]:
    """Nominal length of every MEASUREMENT block, in seconds.

    Mirrors the layout ``core.assigner.outer._block_lengths_min`` produces with
    ``washout_min = 0``: ``[2L, L, ..., L, 2L]`` when the doubled-endpoint rule
    fits, uniform ``L`` otherwise. Boundary jitter is ignored — it is
    zero-mean and cancels over the session.
    """
    n = blocks_in_session(session_minutes, block_min, endpoint_double)
    if n <= 0:
        return []
    length_s = block_min * 60
    if endpoint_double and n >= 4 and session_minutes >= 6 * block_min:
        return [2 * length_s] + [length_s] * (n - 2) + [2 * length_s]
    return [length_s] * n


def analysis_window_seconds(
    session_minutes: int,
    block_min: int,
    endpoint_double: bool = True,
    burn_in_s: int = 60,
) -> list[float]:
    """Seconds of each measurement block that actually carry the outcome.

    Same rule as :func:`livelift.core.features.block_frame`: the window starts
    ``min(burn_in_s, max(duration - 30, 0))`` into the block. The doubled
    endpoint blocks therefore keep a LARGER share of their minutes than the
    interior ones — which is exactly why the ON/OFF time split of a schedule is
    not 0.5 (see ``core.quality.check_telemetry_delivery``).
    """
    out: list[float] = []
    for d in _measurement_block_seconds(session_minutes, block_min, endpoint_double):
        out.append(float(d - min(burn_in_s, max(d - 30, 0))))
    return out


def poisson_cv(expected_counts: Sequence[float]) -> float:
    """CV of the block RATE outcome when the block COUNT is pure Poisson.

    For ``y_k = 1000 · n_k / E_k`` with ``n_k ~ Poisson(λ_k)`` and a constant
    underlying rate ``r = λ_k / E_k``:

        Var_pois = mean_k(1000² · λ_k / E_k²) = 1000² · r · mean_k(1/E_k)
        mean(y)  = 1000 · r
        CV       = √Var_pois / mean(y) = √(mean_k(1/λ_k))

    This is the same quantity :func:`poisson_floor` measures on real data, so
    the two agree by construction — ``poisson_floor`` reads it off observed
    clicks, this reads it off an assumed λ. Blocks with λ = 0 make the CV
    infinite (a rate you cannot measure), which is reported as ``inf`` rather
    than silently dropped.
    """
    lams = [float(x) for x in expected_counts]
    if not lams:
        return float("nan")
    if any(x <= 0 for x in lams):
        return float("inf")
    return float(np.sqrt(np.mean([1.0 / x for x in lams])))


def expected_orders(
    click_rate_per_1000vs: float,
    exposure_viewer_s: float,
    q1_pv_to_cart: float = FUNNEL_PV_TO_CART,
    q2_cart_to_buy: float = FUNNEL_CART_TO_BUY,
) -> float:
    """Expected ORDERS from a click rate and an exposure, through the funnel.

    ``click_rate_per_1000vs`` is the project's primary outcome unit (valid
    clicks per 1000 viewer-seconds), so this is the one conversion between the
    measured endpoint and the order endpoint — kept in one place so no report
    can invent a second one.
    """
    clicks = click_rate_per_1000vs * exposure_viewer_s / 1000.0
    return clicks * q1_pv_to_cart * q2_cart_to_buy


def order_mde_table(
    click_rate_per_1000vs: float,
    sessions_grid: Sequence[int],
    audience_grid: Sequence[float],
    q2_grid: Sequence[float] = Q2_GRID,
    *,
    session_minutes: int = 90,
    block_min: int = 5,
    endpoint_double: bool = True,
    burn_in_s: int = 60,
    q1_pv_to_cart: float = FUNNEL_PV_TO_CART,
    compliance: float = 0.95,
    partner_multiplier: float = PARTNER_AUDIENCE_MULTIPLIER,
    include_partner: bool = True,
    alpha: float = 0.05,
    power: float = 0.80,
) -> list[dict]:
    """MDE on the ORDER-count endpoint, over sessions × audience × q2.

    **This is a SCENARIO table, not a measurement.** Three inputs are priors or
    assumptions and every row says so:

    - ``click_rate_per_1000vs`` — the project has no measured product-click
      rate yet (pilot-only quantity; ``SimParams.base_click_prob_per_min`` is
      flagged as an assumption in the simulator).
    - the funnel ``q1 × q2`` — Taobao UserBehavior (Tianchi #649):
      pv→cart 9.33%, cart→buy 24.33%, ≈2.27% overall. ``q2`` is swept.
    - ``partner_multiplier`` — ×4.9 audience for the partner branch
      (arXiv:2106.03415), applied to the audience only.

    **KuaiLive MUST NOT be mapped onto this funnel.** KuaiLive's "click" event
    is a room ENTRY, not a click on a pinned product; it shares a name with the
    project's outcome and nothing else. Using it here would produce a
    conversion rate that measures a different act entirely
    (docs/benchmarks/kuailive-calibration.md states the same limit for
    ``base_click_prob_per_min``).

    Method: orders per block are rare, so their variance is dominated by
    counting noise. Each block's expected order count is
    ``λ_k = click_rate/1000 · audience · window_k · q1 · q2``; the CV fed to the
    SAME :func:`mde_relative` machinery is the Poisson one,
    ``√(mean_k 1/λ_k)`` (:func:`poisson_cv`). The result is therefore a
    **floor**: real sessions carry systematic variance on top of the arrival
    noise, so the achievable order MDE can only be LARGER than these numbers.
    Reported as such — never as "the MDE we will get".

    Audience is treated as a constant concurrent viewer count over the session;
    the phase curve (ramp-up / wind-down) is not modelled here, so the exposure
    of a real session with the same peak audience is somewhat lower.
    """
    windows = analysis_window_seconds(session_minutes, block_min, endpoint_double, burn_in_s)
    blocks_per_session = len(windows)
    branches: list[tuple[str, float]] = [("không đối tác", 1.0)]
    if include_partner:
        branches.append((f"có đối tác (×{partner_multiplier:g})", float(partner_multiplier)))

    rows: list[dict] = []
    for n_sessions in sessions_grid:
        for audience in audience_grid:
            for branch_name, mult in branches:
                eff_audience = float(audience) * mult
                for q2 in q2_grid:
                    lams = [
                        expected_orders(click_rate_per_1000vs, eff_audience * w, q1_pv_to_cart, q2)
                        for w in windows
                    ]
                    total_blocks = blocks_per_session * int(n_sessions)
                    cv = poisson_cv(lams)
                    mde = mde_relative(
                        PowerInputs(
                            cv=cv,
                            n_blocks_total=total_blocks,
                            n_sessions=int(n_sessions),
                            alpha=alpha,
                            power=power,
                            compliance=compliance,
                        )
                    )
                    orders_session = float(sum(lams))
                    rows.append(
                        {
                            "branch": branch_name,
                            "n_sessions": int(n_sessions),
                            "audience": float(audience),
                            "audience_effective": eff_audience,
                            "q1": q1_pv_to_cart,
                            "q2": float(q2),
                            "click_to_order": q1_pv_to_cart * float(q2),
                            "blocks_per_session": blocks_per_session,
                            "n_blocks_total": total_blocks,
                            "orders_per_block": orders_session / max(blocks_per_session, 1),
                            "orders_per_session": orders_session,
                            "orders_total": orders_session * int(n_sessions),
                            "cv_poisson": cv,
                            "mde_relative": mde,
                            "mde_orders_per_session": mde * orders_session,
                        }
                    )
    return rows
