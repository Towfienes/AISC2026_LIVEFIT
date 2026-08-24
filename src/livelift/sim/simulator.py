"""Livestream session simulator with known ground-truth treatment effects.

Purpose (research synthesis §5): validate the whole causal pipeline —
assignment → events → block outcomes → estimators — on synthetic sessions
where the true effect is injected and therefore known. This is what turns
"we opened a shop" into "our estimator is demonstrably calibrated".

Mechanics (5-second clock by default):
- **Arrivals**: non-homogeneous Poisson. Rate = base × phase curve (ramp-up,
  plateau, wind-down) × session-level shock (lognormal — generates session ICC).
- **Departures**: per-viewer geometric hazard from a mean-stay parameter.
- **Clicks**: each present viewer clicks the pinned product with per-tick
  probability p_click × AR(1) noise (serial correlation) × treatment lift.
- **Treatment**: ON blocks multiply click propensity by (1 + effect).
- **Carryover knob**: after a switch, the previous arm's lift decays with an
  exponential half-life instead of vanishing — the interference mechanism
  switchback designs worry about. Set 0 for a clean world; sweep upward for
  sensitivity studies.
- **Comments/likes**: Poisson proportional to viewers (for covariates/radar).

Ground truth via common random numbers: :func:`true_effect` re-simulates the
same session (same seed → same arrivals, stays, noise) under all-ON and
all-OFF and differences the block outcomes.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace

from livelift.core.assigner.outer import ON, Schedule
from livelift.core.features import Event


@dataclass(frozen=True)
class SimParams:
    tick_s: int = 5
    base_arrival_per_min: float = 6.0  # new viewers per minute at plateau
    mean_stay_min: float = 6.0
    base_click_prob_per_min: float = 0.06  # per viewer per minute on pinned product
    comment_rate_per_viewer_min: float = 0.25
    like_rate_per_viewer_min: float = 0.8
    treatment_effect: float = 0.15  # multiplicative lift on click propensity in ON
    carryover_halflife_s: float = 0.0  # 0 = no carryover; >0 = interference
    session_shock_sd: float = 0.25  # lognormal sigma of session-level multiplier
    ar1_rho: float = 0.5  # serial correlation of click-propensity noise
    ar1_sd: float = 0.15


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


def _treatment_exposure(
    t_s: float, schedule: Schedule, override: str | None
) -> float:
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
    """
    world_rng = random.Random(seed)  # arrivals, stays, noise — shared across arms
    click_rng = random.Random(seed ^ 0x5EED)  # click/comment/like draws

    session_s = schedule.session_duration_min * 60
    tick = params.tick_s
    session_shock = math.exp(world_rng.gauss(0.0, params.session_shock_sd))

    events: list[Event] = []
    viewers_trace: list[float] = []
    stays: list[float] = []  # remaining stay seconds per present viewer
    ar_noise = 0.0

    p_click_tick = params.base_click_prob_per_min * tick / 60.0
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

        # departures
        stays = [s - tick for s in stays]
        stays = [s for s in stays if s > 0]
        n_viewers = len(stays)

        # AR(1) noise on click propensity (world stream)
        ar_noise = params.ar1_rho * ar_noise + world_rng.gauss(0.0, params.ar1_sd)
        noise_mult = math.exp(ar_noise - params.ar1_sd**2 / (2 * (1 - params.ar1_rho**2 + 1e-9)))

        exposure = _carryover_exposure(t, schedule, params.carryover_halflife_s, override)
        lift = 1.0 + params.treatment_effect * exposure
        p_click = min(p_click_tick * noise_mult * lift, 1.0)

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
    y_on = sum(r.y for r in f_on) / len(f_on)
    y_off = sum(r.y for r in f_off) / len(f_off)
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


def _binomial(rng: random.Random, n: int, p: float) -> int:
    if n <= 0 or p <= 0:
        return 0
    if p >= 1:
        return n
    if n > 100:  # normal approximation
        mu, sd = n * p, math.sqrt(n * p * (1 - p))
        return min(n, max(0, round(rng.gauss(mu, sd))))
    return sum(1 for _ in range(n) if rng.random() < p)
