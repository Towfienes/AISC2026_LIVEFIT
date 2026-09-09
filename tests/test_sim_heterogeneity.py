"""Gói P1-K2: the two heterogeneity knobs of the simulator.

The knobs exist so the calibration study can be run in a world that has the
clustering the switchback literature worries about, instead of a world that is
silently free of it. Two properties matter more than anything the knobs do:

1. **With the knobs off, nothing changed.** Every number the team has already
   published — the carryover table in ``sim/validate.py``, the gates in
   ``test_sim_validation.py`` — was measured on specific seeds. If adding the
   knobs shifted a single RNG draw, those numbers would silently stop being
   reproducible. A golden digest locks that down.
2. **With the knobs on, they do what their names say** — measured, not
   asserted: over-dispersion from frailty, session ICC from the session knob.
"""

import hashlib
import json
import math
import random

import numpy as np
import pytest

from livelift.core.assigner.outer import DesignParams, generate_schedule
from livelift.core.features import block_frame
from livelift.sim.report import session_icc
from livelift.sim.simulator import (
    _SESSION_CLICK_STREAM,
    SimParams,
    _frailty_clicks,
    session_click_multiplier,
    simulate_session,
    true_effect,
)


def _digest(seed: int, minutes: int, params: SimParams, override=None) -> str:
    schedule = generate_schedule(minutes, DesignParams(jitter_s=0), seed=seed)
    out = simulate_session(schedule, params, seed, override)
    payload = json.dumps(
        [[e.kind, repr(e.ts_offset_s), e.value, e.product_id] for e in out.events]
        + [out.viewers_trace],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _clicks(seed: int, minutes: int, params: SimParams) -> int:
    schedule = generate_schedule(minutes, DesignParams(jitter_s=0), seed=seed)
    out = simulate_session(schedule, params, seed)
    return sum(1 for e in out.events if e.kind == "click")


# ---------------------------------------------------------------------------
# 1. Bit-for-bit invariance with the knobs at their defaults
# ---------------------------------------------------------------------------

# Digests of the event stream produced by the simulator BEFORE the K2 knobs
# existed (computed against git HEAD of 2026-09-09, `sim/simulator.py`). They
# are the contract: the knobs get their own RNG streams and draw from them only
# when switched on, so a default-parameter simulation consumes the world and
# click streams in exactly the historical order.
GOLDEN_DEFAULT = {
    (1, 30): "5bda6f48f668850e",
    (7, 60): "85e5fa235764f35e",
}


@pytest.mark.parametrize(("seed", "minutes"), sorted(GOLDEN_DEFAULT))
def test_default_params_reproduce_pre_knob_stream_bit_for_bit(seed, minutes):
    assert _digest(seed, minutes, SimParams()) == GOLDEN_DEFAULT[(seed, minutes)]


@pytest.mark.parametrize("override", [None, "all_on", "all_off"])
@pytest.mark.parametrize(
    "params",
    [
        SimParams(),
        SimParams(treatment_effect=0.4),
        SimParams(carryover_halflife_s=120.0),
    ],
)
def test_explicit_zero_knobs_equal_defaults(params, override):
    """Writing the knobs out as 0.0 must be indistinguishable from omitting them.

    Guards against the knob code taking a draw "just to keep the stream aligned"
    — the whole point is that the zero path touches nothing.
    """
    explicit = SimParams(
        treatment_effect=params.treatment_effect,
        carryover_halflife_s=params.carryover_halflife_s,
        click_frailty_cv=0.0,
        session_click_sigma=0.0,
    )
    assert _digest(11, 45, explicit, override) == _digest(11, 45, params, override)


def test_knobs_are_off_by_default():
    assert SimParams().click_frailty_cv == 0.0
    assert SimParams().session_click_sigma == 0.0


@pytest.mark.parametrize(
    "kwargs",
    [{"click_frailty_cv": -0.1}, {"session_click_sigma": -0.01}],
)
def test_negative_knob_is_refused(kwargs):
    schedule = generate_schedule(30, DesignParams(jitter_s=0), seed=3)
    with pytest.raises(ValueError, match="≥ 0"):
        simulate_session(schedule, SimParams(**kwargs), seed=3)


# ---------------------------------------------------------------------------
# 2. The knobs actually change the world
# ---------------------------------------------------------------------------


def test_each_knob_changes_the_stream_when_on():
    base = _digest(5, 45, SimParams())
    assert _digest(5, 45, SimParams(click_frailty_cv=0.8)) != base
    assert _digest(5, 45, SimParams(session_click_sigma=0.2)) != base


@pytest.mark.parametrize(
    "params",
    [SimParams(click_frailty_cv=1.2), SimParams(session_click_sigma=0.3)],
)
def test_knobs_leave_the_audience_trajectory_untouched(params):
    """Neither knob may draw from the WORLD stream.

    Arrivals, stays and the AR(1) noise are common random numbers: they must be
    identical whatever the click-side heterogeneity is, or the knob would be
    changing the audience as a side effect and every comparison "same world,
    more clustering" would be false. Comparing the viewer trace is an exact
    check of that, not a statistical one.
    """
    schedule = generate_schedule(60, DesignParams(jitter_s=0), seed=8)
    plain = simulate_session(schedule, SimParams(), 8)
    knobbed = simulate_session(schedule, params, 8)
    assert plain.viewers_trace == knobbed.viewers_trace


def test_frailty_is_mean_one_so_click_volume_is_roughly_preserved():
    """Gamma(1/cv^2, cv^2) has mean 1: switching frailty on must not move the
    expected click count, only its dispersion. A knob that also shifted the
    LEVEL would silently change every effect estimate measured with it on."""
    rng = random.Random(0)
    homogeneous, heterogeneous = [], []
    for _ in range(60):
        seed = rng.randrange(2**40)
        schedule = generate_schedule(60, DesignParams(), seed)
        for params, bucket in (
            (SimParams(treatment_effect=0.0), homogeneous),
            (SimParams(treatment_effect=0.0, click_frailty_cv=1.0), heterogeneous),
        ):
            out = simulate_session(schedule, params, seed)
            bucket.append(sum(1 for e in out.events if e.kind == "click"))
    mean_hom = sum(homogeneous) / len(homogeneous)
    mean_het = sum(heterogeneous) / len(heterogeneous)
    assert mean_het == pytest.approx(mean_hom, rel=0.10), (
        f"frailty làm lệch mức nhấp: đồng nhất {mean_hom:.1f} vs không đồng nhất {mean_het:.1f}"
    )


def _measure(params: SimParams, n_sessions: int, minutes: int = 90, seed0: int = 909):
    """(session ICC of y, mean WITHIN-session variance of y) over n sessions."""
    seed_rng = random.Random(seed0)
    ys: list[float] = []
    sids: list[str] = []
    within: list[float] = []
    for s in range(n_sessions):
        seed = seed_rng.randrange(2**60)
        schedule = generate_schedule(minutes, DesignParams(), seed)
        out = simulate_session(schedule, params, seed)
        vals = [r.y for r in block_frame(schedule, out.events, burn_in_s=60) if r.measurable]
        if len(vals) < 2:
            continue
        ys.extend(vals)
        sids.extend([f"s{s}"] * len(vals))
        within.append(float(np.var(vals, ddof=1)))
    return session_icc(ys, sids), float(np.mean(within))


def _measure_icc(params: SimParams, n_sessions: int, minutes: int = 90, seed0: int = 909):
    return _measure(params, n_sessions, minutes, seed0)[0]


def test_the_two_knobs_are_distinguishable_by_within_session_dispersion():
    """The knobs are NOT interchangeable, and this is how you tell them apart.

    HONEST CORRECTION to the first draft of this package: per-viewer frailty was
    expected to leave session ICC alone. It does not — with a FINITE audience
    the session's mean frailty is itself a random session-level factor of CV
    ≈ cv/√N, so frailty leaks into ICC too. Measured on 400 sessions x 90 min
    by ``python analysis/calibration/bang_icc_mo_phong.py``, which rewrites
    ``docs/benchmarks/sim-icc-map.md`` — the canonical copy; the table below is
    quoted so the reader of this assertion sees what it rests on (mean y stays
    1.00 throughout, i.e. neither knob shifts the level):

    ================  ==========  ============================
    world             ICC(y)      mean WITHIN-session var(y)
    ================  ==========  ============================
    both knobs off    +0.008      0.0853
    frailty cv=0.5    +0.022      0.0883
    frailty cv=1.0    +0.038      0.0992
    frailty cv=1.5    +0.059      0.1229
    frailty cv=2.0    +0.083      0.1536
    session σ=0.06    +0.048      0.0855  <- ICC moved, dispersion did not
    ================  ==========  ============================

    So the discriminator is the WITHIN-session variance: frailty over-disperses
    blocks, the session knob shifts whole sessions and leaves block-level
    dispersion where it was. Use ``session_click_sigma`` to dial ICC;
    ``click_frailty_cv`` buys over-dispersion and only a by-product of ICC.
    """
    n = 60
    _, var_off = _measure(SimParams(treatment_effect=0.0), n, minutes=60)
    _, var_frailty = _measure(SimParams(treatment_effect=0.0, click_frailty_cv=1.5), n, minutes=60)
    icc_sigma, var_sigma = _measure(
        SimParams(treatment_effect=0.0, session_click_sigma=0.06), n, minutes=60
    )

    assert var_frailty > var_off * 1.15, (
        f"frailty phải làm phân tán khối: {var_off:.4f} -> {var_frailty:.4f}"
    )
    assert var_sigma == pytest.approx(var_off, rel=0.15), (
        f"knob phiên không được đổi phân tán trong-phiên: {var_off:.4f} -> {var_sigma:.4f}"
    )
    assert icc_sigma > 0.0, f"knob phiên phải nâng ICC: {icc_sigma:+.3f}"


@pytest.mark.slow
def test_session_click_sigma_reproduces_the_documented_icc_map():
    """The σ → ICC map quoted in the simulator docstring must be re-derivable.

    Measured 09/09 on 400 sessions x 90 min (± is a cluster-bootstrap SE):
    σ=0 → 0.008 ± 0.005, σ=0.03 → 0.018 ± 0.006, σ=0.06 → 0.048 ± 0.008,
    σ=0.095 → 0.101 ± 0.011. This test re-runs a cheaper 150-session version
    and checks the ORDERING and rough level, which is all 150 sessions can
    support: the point is to catch the map silently drifting, not to re-measure
    it to three decimals.
    """
    icc = {
        sigma: _measure_icc(
            SimParams(treatment_effect=0.0, session_click_sigma=sigma), n_sessions=150
        )
        for sigma in (0.0, 0.06, 0.095)
    }
    assert icc[0.0] < icc[0.06] < icc[0.095], icc
    assert icc[0.0] < 0.03, f"thế giới σ=0 không được có ICC đáng kể: {icc}"
    assert 0.02 < icc[0.06] < 0.09, f"σ=0.06 phải cho ICC quanh 0.05: {icc}"
    assert 0.06 < icc[0.095] < 0.15, f"σ=0.095 phải cho ICC quanh 0.10: {icc}"


def test_session_click_multiplier_is_mean_one_and_shared_across_crn_arms():
    """The session multiplier belongs to the WORLD, not to the treatment.

    If it were drawn from the click stream it would differ between the all-ON
    and all-OFF counterfactuals and :func:`true_effect` would be measuring the
    multiplier instead of the effect. With a zero treatment effect the two arms
    must therefore still be identical.
    """
    schedule = generate_schedule(60, DesignParams(jitter_s=0), seed=21)
    params = SimParams(treatment_effect=0.0, session_click_sigma=0.3, click_frailty_cv=0.6)
    assert true_effect(schedule, params, seed=21) == pytest.approx(0.0, abs=1e-9)


def test_session_click_multiplier_matches_its_closed_form():
    """exp(N(0, σ²) − σ²/2) drawn from the dedicated stream — recomputed here
    from the same seed so the knob cannot quietly become, say, exp(N(0, σ))."""
    seed, sigma = 4242, 0.25
    expected = math.exp(
        random.Random(seed ^ _SESSION_CLICK_STREAM).gauss(0.0, sigma) - sigma**2 / 2
    )
    assert session_click_multiplier(seed, sigma) == expected
    assert session_click_multiplier(seed, 0.0) == 1.0


def test_session_click_multiplier_is_wired_into_the_click_probability():
    """The multiplier must MULTIPLY ``base_click_prob_per_min`` and nothing else.

    Scaling the base probability by the closed-form draw and leaving the knob
    off has to reproduce the knob-on run: same click stream, same clicks.
    """
    seed, sigma = 4242, 0.25
    mult = session_click_multiplier(seed, sigma)
    base = SimParams(treatment_effect=0.0)
    scaled = SimParams(
        treatment_effect=0.0,
        base_click_prob_per_min=base.base_click_prob_per_min * mult,
    )
    with_knob = SimParams(treatment_effect=0.0, session_click_sigma=sigma)
    assert _clicks(seed, 60, scaled) == _clicks(seed, 60, with_knob)
    assert _clicks(seed, 60, base) != _clicks(seed, 60, with_knob)


def test_session_click_multiplier_averages_to_one():
    """Mean-1 over seeds — the property the ``−σ²/2`` term buys.

    Checked on the multiplier itself rather than on simulated click counts: the
    claim is about the draw, and 2000 cheap draws pin it far tighter than 2000
    session simulations could. Dropping the correction would push this to
    exp(σ²/2) = 1.133 at σ=0.5, which is ~11 standard errors away.
    """
    sigma = 0.5
    n = 2000
    values = [session_click_multiplier(s, sigma) for s in range(n)]
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    assert abs(mean - 1.0) < 4 * sd / math.sqrt(n), f"trung bình {mean:.4f} lệch khỏi 1"


def test_frailty_clicks_is_an_exact_bernoulli_sum():
    """Unit test of the heterogeneous click sampler: one draw per viewer, at
    that viewer's own probability, clipped at 1."""
    frailties = [0.0, 2.0, 100.0]

    class _Fixed(random.Random):
        def __init__(self, values):
            super().__init__()
            self._values = list(values)

        def random(self):
            return self._values.pop(0)

    # p_base = 0.1 -> per-viewer p = [0.0, 0.2, 1.0 (clipped)]
    assert _frailty_clicks(_Fixed([0.5, 0.5, 0.5]), 0.1, frailties) == 1
    assert _frailty_clicks(_Fixed([0.5, 0.1, 0.999999]), 0.1, frailties) == 2
    assert _frailty_clicks(_Fixed([]), 0.1, []) == 0
