"""Statistical power / MDE calculator with every correction that matters.

Base formula (J-PAL): relative MDE ≈ (z_{1-α/2} + z_{power}) · CV · √(2/n_arm)
(≈ 4·CV/√n_arm at 80% power, 5% two-sided — the plan's approximation).

Corrections applied multiplicatively (docs/research synthesis §3.2):
- ÷ compliance                        (ITT dilution — biggest term off Live Lab)
- × √(design effect)                  (session-cluster ICC: 1 + (m-1)·ρ_sess)
- × √((1+ρ_r)/(1-ρ_r))               (residual serial correlation of blocks)
- × √(1 - burn_in_share)⁻¹ ≈ effective-n loss from analysis burn-in
- × √(1 - R²)                         (CUPED/CUPAC variance reduction)

HARD RULE (plan §1.4): from week 5 the CV, ICC and ρ_r fed into this module
must be MEASURED values from pilot sessions, not assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy.stats import norm


@dataclass(frozen=True)
class PowerInputs:
    cv: float  # coefficient of variation of the block outcome (within-session)
    n_blocks_total: int  # measurement blocks across all sessions
    n_sessions: int
    alpha: float = 0.05
    power: float = 0.80
    compliance: float = 0.95  # auto mode ≈ 0.95; suggest mode measured
    icc_session: float = 0.0  # session-level ICC (measured in calibration)
    resid_autocorr: float = 0.0  # residual lag-1 autocorrelation after FE
    burn_in_share: float = 0.0  # share of block minutes dropped as burn-in
    var_reduction_r2: float = 0.0  # CUPED/CUPAC R² (measured)


def mde_relative(inp: PowerInputs) -> float:
    """Minimum detectable RELATIVE effect on the block outcome (e.g. 0.18 = 18%)."""
    if inp.n_blocks_total < 4 or inp.n_sessions < 1:
        return float("inf")
    n_arm = inp.n_blocks_total / 2
    z = norm.ppf(1 - inp.alpha / 2) + norm.ppf(inp.power)
    base = z * inp.cv * (2 / n_arm) ** 0.5

    m = inp.n_blocks_total / inp.n_sessions  # blocks per session (cluster size)
    deff_cluster = 1 + (m - 1) * max(inp.icc_session, 0.0)
    rho = min(max(inp.resid_autocorr, -0.99), 0.99)
    deff_serial = (1 + rho) / (1 - rho)
    eff_n_scale = 1.0 / max(1.0 - inp.burn_in_share, 1e-9)
    vr = max(0.0, min(inp.var_reduction_r2, 0.95))

    mde = base
    mde *= deff_cluster**0.5
    mde *= deff_serial**0.5
    mde *= eff_n_scale**0.5
    mde *= (1 - vr) ** 0.5
    mde /= max(inp.compliance, 1e-9)
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
    icc_session: float = 0.05,
    resid_autocorr: float = 0.2,
    burn_in_share: float = 0.2,
    var_reduction_r2: float = 0.3,
) -> list[dict]:
    """MDE table across scenarios × CV — the honest two-scenario power table
    (no-partner vs with-partner) required by the research synthesis (L2)."""
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
                icc_session=icc_session,
                resid_autocorr=resid_autocorr,
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
