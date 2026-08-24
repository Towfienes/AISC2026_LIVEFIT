"""Acceptance E3-01 + HARNESS gates for the outer-tier switchback assigner."""

import random
from collections import Counter

import pytest

from livelift.core.assigner.outer import (
    OFF,
    ON,
    DesignParams,
    draw_assignments,
    generate_schedule,
)

DESIGN = DesignParams()  # block 5', no washout, endpoint double, jitter 30s


def test_schedule_is_deterministic_given_seed():
    a = generate_schedule(90, DESIGN, seed=42)
    b = generate_schedule(90, DESIGN, seed=42)
    assert a.to_rows() == b.to_rows()


def test_different_seeds_differ():
    a = generate_schedule(90, DESIGN, seed=1)
    b = generate_schedule(90, DESIGN, seed=2)
    assert a.to_rows() != b.to_rows()


def test_endpoint_blocks_doubled():
    s = generate_schedule(90, DESIGN, seed=7)
    meas = s.measurement_blocks
    # 90 min, 5-min blocks, doubled endpoints: 16 blocks (2x10' + 14x5')
    assert len(meas) == 16
    # nominal durations before jitter: first/last 600s, middle 300s (±jitter)
    assert meas[0].duration_s >= 600 - DESIGN.jitter_s
    assert meas[-1].duration_s >= 600 - DESIGN.jitter_s


def test_blocks_cover_session_in_order_without_overlap():
    s = generate_schedule(90, DESIGN, seed=3)
    blocks = sorted(s.blocks, key=lambda b: b.start_offset_s)
    assert blocks[0].start_offset_s == 0
    for prev, nxt in zip(blocks, blocks[1:], strict=False):
        assert prev.end_offset_s == nxt.start_offset_s
    assert blocks[-1].end_offset_s <= 90 * 60


def test_acceptance_1000_schedules_balanced():
    """E3-01: 1000 draws -> ON share within [0.45, 0.55] overall and every
    phase contains at least min_per_arm_per_phase of each arm."""
    on_total = 0
    n_total = 0
    for seed in range(1000):
        s = generate_schedule(90, DESIGN, seed=seed)
        meas = s.measurement_blocks
        on_total += s.n_on
        n_total += len(meas)
        per_phase = Counter((b.phase, b.assignment) for b in meas)
        for phase in ("early", "mid", "late"):
            assert per_phase[(phase, ON)] >= DESIGN.min_per_arm_per_phase, seed
            assert per_phase[(phase, OFF)] >= DESIGN.min_per_arm_per_phase, seed
    share = on_total / n_total
    assert 0.45 <= share <= 0.55


def test_marginal_propensity_is_half_per_block_position():
    """Rerandomization must not distort the marginal P(ON) of any position."""
    n_draws = 4000
    counts = None
    for seed in range(n_draws):
        s = generate_schedule(60, DesignParams(jitter_s=0), seed=seed)
        arms = [b.assignment for b in s.measurement_blocks]
        if counts is None:
            counts = [0] * len(arms)
        for i, a in enumerate(arms):
            counts[i] += a == ON
    assert counts is not None
    for i, c in enumerate(counts):
        assert 0.45 <= c / n_draws <= 0.55, f"position {i}: {c / n_draws:.3f}"


def test_draw_assignments_respects_stratum_constraint():
    rng = random.Random(0)
    phases = ["early"] * 6 + ["mid"] * 6 + ["late"] * 6
    for _ in range(200):
        arms, _ = draw_assignments(phases, rng, min_per_arm_per_phase=2)
        c = Counter(zip(phases, arms, strict=True))
        for ph in ("early", "mid", "late"):
            assert c[(ph, ON)] >= 2
            assert c[(ph, OFF)] >= 2


def test_small_stratum_degrades_gracefully():
    rng = random.Random(0)
    arms, _ = draw_assignments(["early", "early", "mid"], rng, min_per_arm_per_phase=2)
    assert len(arms) == 3  # must not loop forever on an impossible constraint


def test_washout_mode_still_supported():
    s = generate_schedule(90, DesignParams(block_min=10, washout_min=2, endpoint_double=False), 5)
    washouts = [b for b in s.blocks if b.is_washout]
    meas = s.measurement_blocks
    assert len(washouts) == len(meas) - 1
    assert all(b.assignment is None and b.propensity is None for b in washouts)


def test_schedule_shorter_than_block_rejected():
    with pytest.raises(ValueError):
        generate_schedule(3, DesignParams(block_min=5), 1)


def test_propensity_recorded_as_p():
    s = generate_schedule(90, DESIGN, seed=11)
    assert all(b.propensity == DESIGN.p for b in s.measurement_blocks)
