"""Livestream session simulator with known ground-truth treatment effects.

Purpose (research synthesis §5): validate the whole causal pipeline —
assignment → events → block outcomes → estimators — on synthetic sessions
where the true effect is injected and therefore known. This is what turns
"we opened a shop" into "our estimator is demonstrably calibrated".

Mechanics (5-second clock by default):
- **Arrivals**: non-homogeneous Poisson. Rate = base × phase curve (ramp-up,
  plateau, wind-down) × session-level shock (lognormal) on the ARRIVAL RATE.
- **Departures**: per-viewer geometric hazard from a mean-stay parameter.
- **Clicks**: each present viewer clicks the pinned product with per-tick
  probability p_click × AR(1) noise (serial correlation) × treatment lift,
  optionally × a per-viewer frailty and a per-session click multiplier
  (see "Heterogeneity knobs" below).
- **Treatment**: ON blocks multiply click propensity by (1 + effect).
- **Carryover knob**: after a switch, the previous arm's lift decays with an
  exponential half-life instead of vanishing — the interference mechanism
  switchback designs worry about. Set 0 for a clean world; sweep upward for
  sensitivity studies.
- **Comments/likes**: Poisson proportional to viewers (for covariates/radar).

Heterogeneity knobs (gói P1-K2, 2026-09-09 — both DEFAULT OFF)
--------------------------------------------------------------
``session_shock_sd`` does **not** create outcome ICC, contrary to what the
docstring of this module claimed until 09/09. The primary outcome is a RATE —
valid clicks per 1000 viewer-seconds — and the arrival shock scales the
numerator and the denominator together, so it moves a block's *sampling noise*
(a busier session measures its rate more precisely) but leaves E[y] alone. A
correlation between blocks of the same session in the LEVEL of y needs a
session-level factor on the click propensity itself. Two knobs add the real
thing, so calibration can be tested against a world with the clustering the
literature reports rather than one silently free of it:

- ``click_frailty_cv`` — per-viewer frailty ``u_i ~ Gamma(1/cv², cv²)``
  (mean 1, sd = cv) multiplying that viewer's click probability. Audiences are
  not homogeneous; this produces over-dispersed block click counts (a
  Gamma-Poisson / negative-binomial-like world).
- ``session_click_sigma`` — a session-level multiplier
  ``exp(N(0, σ²) − σ²/2)`` (mean 1) on the base click probability, drawn
  INDEPENDENTLY of the arrival shock. This is what puts a common level shift on
  every block of a session, i.e. genuine outcome ICC.

MEASURED σ → ICC map (09/09; 400 sessions x 90 min, 5-minute blocks, burn-in
60 s, zero effect; ICC = one-way ANOVA of block ``y`` clustered by session,
:func:`livelift.sim.report.session_icc`; ± is a cluster-bootstrap SE over
sessions, :func:`livelift.sim.report.session_icc_bootstrap_se`).

REGENERATE with ``python analysis/calibration/bang_icc_mo_phong.py`` — it
rewrites ``docs/benchmarks/sim-icc-map.md``, which is the canonical copy and
carries the same numbers plus the mean-y and within-variance columns. A measured
table with no command behind it is a table the reader has to take on trust.

==========  ==================  ==========================
σ           ICC(y)              note
==========  ==================  ==========================
0.000       +0.008 ± 0.005      knob off — see caveat below
0.030       +0.018 ± 0.006      target 0.02
0.060       +0.048 ± 0.008      target 0.05  <- gate world
0.095       +0.101 ± 0.011      target 0.10
0.100       +0.110 ± 0.012      brief's coarse grid
0.200       +0.333 ± 0.021      brief's coarse grid
0.300       +0.535 ± 0.023      brief's coarse grid
==========  ==================  ==========================

CAVEAT, measured not assumed: with the knob OFF the world is not exactly
ICC = 0 but ICC ≈ 0.008 ± 0.005. Part of that is the one-way ANOVA estimator
meeting heteroskedastic clusters — ``session_shock_sd`` makes some sessions
far busier, hence their block rates far less noisy, and unequal within-cluster
variances bias ICC(1) upward — and part is the session-average of the AR(1)
propensity noise. So "σ=0" should be read as "≈0.01", not "0". The knob's job
is to move ICC to a *known, dialled* level, and it does: 0.03/0.06/0.095 land
on 0.02/0.05/0.10 within one bootstrap SE.

SECOND CAVEAT, and a correction to this package's own first draft: per-viewer
frailty was expected to leave session ICC untouched. It does NOT. The audience
is finite (~500 arrivals in a 90-minute session), so the session's MEAN frailty
is itself a random session-level factor with CV ≈ cv/√N, and that shows up as
ICC. Measured on the same 400-session harness, by the SAME command as the table
above — both maps are regenerated together into
``docs/benchmarks/sim-icc-map.md``, and their ``knob = 0`` rows are the same
world and must agree, which is the file's own self-check. (Mean y stays 1.00 in
every row — neither knob shifts the level.)

================  ==========  ===========================
world             ICC(y)      mean WITHIN-session var(y)
================  ==========  ===========================
both knobs off    +0.008      0.0853
frailty cv=0.5    +0.022      0.0883
frailty cv=1.0    +0.038      0.0992
frailty cv=1.5    +0.059      0.1229
frailty cv=2.0    +0.083      0.1536
session σ=0.06    +0.048      0.0855
================  ==========  ===========================

The clean separator is the WITHIN-session variance: frailty over-disperses the
blocks themselves, the session knob moves whole sessions and leaves block-level
dispersion alone. Dial ICC with ``session_click_sigma``; reach for
``click_frailty_cv`` when the question is over-dispersion, and expect the ICC
side-effect in the table above.

Both knobs draw from their own RNG streams, so with the defaults (0.0) not one
draw is taken and every previously recorded seed reproduces bit-for-bit — a
test asserts exactly that.

Ground truth via common random numbers: :func:`true_effect` re-simulates the
same session (same seed → same arrivals, stays, noise, frailties, session
click multiplier) under all-ON and all-OFF and differences the block outcomes.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace

from livelift.core.assigner.outer import ON, Schedule
from livelift.core.features import Event


@dataclass(frozen=True)
class SimParams:
    """Simulator parameters.

    Defaults CALIBRATED against KuaiLive (SIGIR 2026; 1.16M shop rooms,
    445k entries — docs/benchmarks/kuailive-calibration.md, 02/09):
    engaged-viewer dwell mean 10.0 min (median 3.6), comment rate
    0.016/viewer·min, like rate 0.014/viewer·min. Platform caveat: Kuaishou
    shop-room behaviour, to be re-measured on the team's own Facebook pilots
    (week-3 calibration). ``base_click_prob_per_min`` CANNOT be calibrated
    from KuaiLive (its "click" means entering a room, not clicking a pinned
    product) and stays an assumption until pilot data exists.
    """

    tick_s: int = 5
    base_arrival_per_min: float = 6.0  # new viewers per minute at plateau
    mean_stay_min: float = 10.0  # KuaiLive engaged-viewer mean
    base_click_prob_per_min: float = 0.06  # ASSUMPTION — pilot-only quantity
    comment_rate_per_viewer_min: float = 0.016  # KuaiLive shop rooms
    like_rate_per_viewer_min: float = 0.014  # KuaiLive shop rooms
    treatment_effect: float = 0.15  # multiplicative lift on click propensity in ON
    carryover_halflife_s: float = 0.0  # 0 = no carryover; >0 = interference
    session_shock_sd: float = 0.25  # lognormal sigma on the ARRIVAL rate (not ICC)
    ar1_rho: float = 0.5  # serial correlation of click-propensity noise
    ar1_sd: float = 0.15
    # --- heterogeneity knobs (gói P1-K2) — see the module docstring ----------
    # Per-viewer frailty u_i ~ Gamma(shape=1/cv^2, scale=cv^2), mean 1, sd=cv.
    # 0.0 = homogeneous audience (the historical behaviour, bit-for-bit).
    click_frailty_cv: float = 0.0
    # Session-level click multiplier exp(N(0, sigma^2) - sigma^2/2), mean 1.
    # THIS is the knob that creates outcome ICC. 0.0 = no session clustering.
    session_click_sigma: float = 0.0


@dataclass(frozen=True)
class SimOutput:
    events: list[Event]
    viewers_trace: list[float]


def _phase_curve(t_s: float, session_s: float) -> float:
    """Audience shape: ramp up over first 15%, plateau, decay last 15%."""
    x = t_s / session_s
    if x < 0.15:
        return 0.3 + 0.7 * (x / 0.15)
    if x > 0.85:
        return 1.0 - 0.6 * ((x - 0.85) / 0.15)
    return 1.0


def _treatment_exposure(t_s: float, schedule: Schedule, override: str | None) -> float:
    """Instantaneous treatment intensity in [0,1] at time t, including
    exponential carryover from earlier ON exposure when the knob is set."""
    if override == "all_on":
        return 1.0
    if override == "all_off":
        return 0.0
    current = 0.0
    for b in schedule.measurement_blocks:
        if b.start_offset_s <= t_s < b.end_offset_s:
            current = 1.0 if b.assignment == ON else 0.0
            break
    return current


def _carryover_exposure(
    t_s: float, schedule: Schedule, halflife_s: float, override: str | None
) -> float:
    """Exposure with carryover: current arm + decaying influence of the most
    recent preceding ON block that already ended."""
    exposure = _treatment_exposure(t_s, schedule, override)
    if halflife_s <= 0 or override is not None:
        return exposure
    if exposure >= 1.0:
        return 1.0
    # decaying tail from the last ON block that ended before t
    last_on_end: float | None = None
    for b in schedule.measurement_blocks:
        if b.assignment == ON and b.end_offset_s <= t_s:
            last_on_end = float(b.end_offset_s)
    if last_on_end is None:
        return exposure
    decay = 0.5 ** ((t_s - last_on_end) / halflife_s)
    return max(exposure, decay)


_FRAILTY_STREAM = 0xF7A11
"""XOR offset for the per-viewer frailty stream (see :func:`simulate_session`)."""

_SESSION_CLICK_STREAM = 0x1CC01
"""XOR offset for the session-level click-multiplier stream."""


def session_click_multiplier(seed: int, sigma: float) -> float:
    """The session's click-propensity multiplier: ``exp(N(0, σ²) − σ²/2)``.

    Mean exactly 1 — the ``−σ²/2`` is what keeps it so. Without that term the
    knob would raise the average click rate by ``exp(σ²/2)`` as a side effect
    (13% at σ=0.5) and every effect measured "at ICC 0.05" would silently be an
    effect measured in a busier world as well.

    Pure and public so the map from (seed, σ) to the multiplier can be checked
    exactly instead of inferred from simulator output.
    """
    if sigma <= 0:
        return 1.0
    return math.exp(random.Random(seed ^ _SESSION_CLICK_STREAM).gauss(0.0, sigma) - sigma**2 / 2)


def simulate_session(
    schedule: Schedule,
    params: SimParams,
    seed: int,
    override: str | None = None,
) -> SimOutput:
    """Simulate one session. ``override``: None (use schedule), "all_on",
    "all_off" — the latter two are the CRN counterfactual arms.

    RNG discipline: one stream drives arrivals/stays/noise identically across
    overrides (common random numbers); a separate stream drives click draws so
    the treatment changes click *probabilities*, not the shared trajectory.

    The two heterogeneity knobs (gói P1-K2) get their OWN streams, derived from
    ``seed`` exactly the way ``click_rng`` is. Two consequences, both wanted:

    1. They are shared across the counterfactual arms, so a viewer's frailty and
       the session's click multiplier are part of the *world*, not of the
       treatment — CRN keeps holding and :func:`true_effect` stays honest.
    2. When a knob is 0 (the default) NOTHING is drawn from its stream and the
       world/click streams are consumed in exactly the historical order, so
       every recorded seed reproduces bit-for-bit.
    """
    cv = params.click_frailty_cv
    sigma = params.session_click_sigma
    if cv < 0:
        raise ValueError(f"click_frailty_cv phải ≥ 0 (nhận {cv})")
    if sigma < 0:
        raise ValueError(f"session_click_sigma phải ≥ 0 (nhận {sigma})")

    world_rng = random.Random(seed)  # arrivals, stays, noise — shared across arms
    click_rng = random.Random(seed ^ 0x5EED)  # click/comment/like draws

    session_s = schedule.session_duration_min * 60
    tick = params.tick_s
    session_shock = math.exp(world_rng.gauss(0.0, params.session_shock_sd))

    # Session-level click multiplier — the ICC knob. Mean-1 lognormal, drawn
    # from its own stream so arrival volume and click propensity are not
    # accidentally tied together and the CRN arms share the same value.
    session_click_mult = session_click_multiplier(seed, sigma)

    use_frailty = cv > 0
    frailty_rng = random.Random(seed ^ _FRAILTY_STREAM)
    frailty_shape = 1.0 / cv**2 if use_frailty else 0.0
    frailty_scale = cv**2 if use_frailty else 0.0

    events: list[Event] = []
    viewers_trace: list[float] = []
    stays: list[float] = []  # remaining stay seconds per present viewer
    frailties: list[float] = []  # parallel to `stays`; stays empty when knob off
    ar_noise = 0.0

    p_click_tick = params.base_click_prob_per_min * tick / 60.0 * session_click_mult
    arrival_tick = params.base_arrival_per_min * tick / 60.0
    hazard = tick / (params.mean_stay_min * 60.0)

    t = 0
    while t < session_s:
        phase_mult = _phase_curve(t, session_s)

        # arrivals (world stream — identical across counterfactual arms)
        lam = arrival_tick * phase_mult * session_shock
        n_arrive = _poisson(world_rng, lam)
        for _ in range(n_arrive):
            stay = -math.log(max(world_rng.random(), 1e-12)) / hazard * tick
            stays.append(stay)
            if use_frailty:
                frailties.append(frailty_rng.gammavariate(frailty_shape, frailty_scale))

        # departures
        if use_frailty:
            alive = [(s - tick, u) for s, u in zip(stays, frailties, strict=True) if s - tick > 0]
            stays = [s for s, _ in alive]
            frailties = [u for _, u in alive]
        else:
            stays = [s - tick for s in stays]
            stays = [s for s in stays if s > 0]
        n_viewers = len(stays)

        # AR(1) noise on click propensity (world stream)
        ar_noise = params.ar1_rho * ar_noise + world_rng.gauss(0.0, params.ar1_sd)
        noise_mult = math.exp(ar_noise - params.ar1_sd**2 / (2 * (1 - params.ar1_rho**2 + 1e-9)))

        exposure = _carryover_exposure(t, schedule, params.carryover_halflife_s, override)
        lift = 1.0 + params.treatment_effect * exposure
        p_raw = p_click_tick * noise_mult * lift
        p_click = min(p_raw, 1.0)

        if use_frailty:
            # Heterogeneous viewers: one Bernoulli draw each, at that viewer's
            # own propensity. (The homogeneous path keeps the historical
            # `_binomial` call — including its normal approximation above 100
            # viewers — so seeds recorded before this knob existed still
            # reproduce exactly.)
            n_clicks = _frailty_clicks(click_rng, p_raw, frailties)
        else:
            n_clicks = _binomial(click_rng, n_viewers, p_click)
        for _ in range(n_clicks):
            events.append(Event("click", t + click_rng.random() * tick, product_id="P1"))

        n_comments = _poisson(
            click_rng, n_viewers * params.comment_rate_per_viewer_min * tick / 60.0
        )
        for _ in range(n_comments):
            events.append(Event("comment", t + click_rng.random() * tick))
        n_likes = _poisson(click_rng, n_viewers * params.like_rate_per_viewer_min * tick / 60.0)
        for _ in range(n_likes):
            events.append(Event("like", t + click_rng.random() * tick))

        events.append(Event("viewer_count", t, value=float(n_viewers)))
        viewers_trace.append(float(n_viewers))
        t += tick

    return SimOutput(events=events, viewers_trace=viewers_trace)


def true_effect(schedule: Schedule, params: SimParams, seed: int, burn_in_s: int = 60) -> float:
    """Ground-truth average block effect via common-random-number
    counterfactuals: simulate all-ON and all-OFF with the same world stream and
    difference the mean block outcomes."""
    from livelift.core.features import block_frame

    on = simulate_session(schedule, params, seed, override="all_on")
    off = simulate_session(schedule, params, seed, override="all_off")
    f_on = block_frame(schedule, on.events, burn_in_s=burn_in_s)
    f_off = block_frame(schedule, off.events, burn_in_s=burn_in_s)
    # Ground truth must be taken over the SAME blocks the estimator sees:
    # averaging over blocks the analysis excludes would make the comparison
    # target differ from the estimand and disguise real bias (audit 30/08).
    keep = [
        i for i, (a, b) in enumerate(zip(f_on, f_off, strict=True)) if a.measurable and b.measurable
    ]
    if not keep:
        return 0.0
    y_on = sum(f_on[i].y for i in keep) / len(keep)
    y_off = sum(f_off[i].y for i in keep) / len(keep)
    return y_on - y_off


def with_effect(params: SimParams, effect: float) -> SimParams:
    return replace(params, treatment_effect=effect)


# --- tiny exact samplers (stdlib random has no poisson/binomial) -----------


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 30:  # normal approximation for large rates
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    threshold = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= threshold:
            return k
        k += 1


def _frailty_clicks(rng: random.Random, p_base: float, frailties: list[float]) -> int:
    """Clicks this tick when each present viewer has her own frailty multiplier.

    Exact Bernoulli sum (one draw per viewer) — no normal approximation, because
    the whole point of the knob is the extra dispersion the approximation would
    smooth away. Each viewer's probability is clipped at 1.
    """
    return sum(1 for u in frailties if rng.random() < min(p_base * u, 1.0))


def _binomial(rng: random.Random, n: int, p: float) -> int:
    if n <= 0 or p <= 0:
        return 0
    if p >= 1:
        return n
    if n > 100:  # normal approximation
        mu, sd = n * p, math.sqrt(n * p * (1 - p))
        return min(n, max(0, round(rng.gauss(mu, sd))))
    return sum(1 for _ in range(n) if rng.random() < p)
