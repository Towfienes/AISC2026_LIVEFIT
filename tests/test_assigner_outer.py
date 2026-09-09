"""Acceptance E3-01 + HARNESS gates for the outer-tier switchback assigner."""

import random
from collections import Counter
from dataclasses import asdict

import pytest

from livelift.core.assigner.outer import (
    OFF,
    ON,
    DesignParams,
    design_hash,
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
    """Rerandomization must not distort the marginal P(ON) of any position.

    Research 08/09: moved from 60' to the default 90' confirmatory length —
    under the added transition-balance constraint the 60' layout (10 blocks)
    accepts only ~0.4% of draws, which would make this quick test spend ~10M
    Bernoulli draws; the symmetry argument being tested is length-independent.
    """
    n_draws = 4000
    counts = None
    for seed in range(n_draws):
        s = generate_schedule(90, DesignParams(jitter_s=0), seed=seed)
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


# ---------------------------------------------------------------------------
# Review 06/09 — rerandomization preserves the marginal propensity ONLY at
# p=0.5; combining p≠0.5 with the balance constraint must warn.
# ---------------------------------------------------------------------------


def test_draw_assignments_warns_on_p_not_half_with_rerandomization():
    rng = random.Random(0)
    phases = ["early"] * 8 + ["mid"] * 8 + ["late"] * 8
    with pytest.warns(UserWarning, match="rerandomization"):
        draw_assignments(phases, rng, p=0.3)


def test_draw_assignments_silent_at_half_or_without_constraint(recwarn):
    rng = random.Random(0)
    phases = ["early"] * 8 + ["mid"] * 8 + ["late"] * 8
    draw_assignments(phases, rng, p=0.5)  # symmetric case: marginal stays p
    # no constraint at all — 08/09: the transition constraint is rerandomization
    # too, so it must be disabled here as well for the call to stay silent
    draw_assignments(phases, rng, p=0.3, min_per_arm_per_phase=0, min_transition_pairs=0)
    assert not [w for w in recwarn.list if issubclass(w.category, UserWarning)]


def test_draw_assignments_warns_on_p_not_half_with_transition_constraint_only():
    """08/09: the transition constraint alone is enough conditioning to break
    the p≠0.5 marginal — the warning must fire even with the phase constraint
    off."""
    rng = random.Random(0)
    phases = ["early"] * 8 + ["mid"] * 8 + ["late"] * 8
    with pytest.warns(UserWarning, match="rerandomization"):
        draw_assignments(phases, rng, p=0.3, min_per_arm_per_phase=0)


# ---------------------------------------------------------------------------
# Research 08/09 (arXiv:2604.02489, HBS WP 26-012, arXiv:2602.23257) —
# transition-balance acceptance: every accepted schedule must hold ≥3 adjacent
# (ON,ON) and ≥3 (OFF,OFF) pairs with |difference| ≤ 1, so the carryover-robust
# sensitivity estimators (adjacent-pair HT, CRT) never meet a degenerate
# session. Symmetric under ON↔OFF, hence marginal propensity stays 0.5.
# ---------------------------------------------------------------------------


def _same_arm_pairs(schedule):
    """(#(ON,ON), #(OFF,OFF)) over the measurement chain, in block order."""
    arms = [b.assignment for b in schedule.measurement_blocks]
    n_on_on = sum(1 for a, b in zip(arms, arms[1:], strict=False) if a == b == ON)
    n_off_off = sum(1 for a, b in zip(arms, arms[1:], strict=False) if a == b == OFF)
    return n_on_on, n_off_off


def test_every_accepted_schedule_satisfies_transition_balance():
    """(c) Every accepted 90' schedule delivers the full constraint and says so."""
    for seed in range(300):
        s = generate_schedule(90, DESIGN, seed=seed)
        n_on_on, n_off_off = _same_arm_pairs(s)
        assert n_on_on >= 3, (seed, n_on_on)
        assert n_off_off >= 3, (seed, n_off_off)
        assert abs(n_on_on - n_off_off) <= 1, (seed, n_on_on, n_off_off)
        assert s.realized_transition_pairs == 3
        assert s.constraint_met


def test_transition_balance_keeps_marginal_on_rate_at_half():
    """(a) The added conditioning is ON↔OFF symmetric, so the pooled ON share
    over many schedules must stay at 0.5 (band ≈ ±9σ of the pooled share)."""
    on = total = 0
    for seed in range(2000):
        s = generate_schedule(90, DESIGN, seed=seed)
        on += s.n_on
        total += len(s.measurement_blocks)
    share = on / total
    assert 0.48 <= share <= 0.52, f"pooled ON share {share:.4f} — đối xứng bị phá"


def test_redraw_cost_of_default_90min_schedule_stays_small():
    """(b) The joint acceptance rate of the 90' default layout is ~10%, i.e. a
    measured mean of ~9.4 redraws (phase constraint alone: ~2.3). The research
    agenda hoped for < 5; that target is NOT reachable with the exact
    pre-registered constraint — asserted honestly at < 15 (≈ 11σ above the
    measured mean) so a real regression of the acceptance set still fails."""
    n_seeds = 500
    total_redraws = sum(generate_schedule(90, DESIGN, seed=s).n_redraws for s in range(n_seeds))
    mean_redraws = total_redraws / n_seeds
    assert mean_redraws < 15, (
        f"số lần redraw trung bình đo được = {mean_redraws:.2f} (kỳ vọng ~9.4; "
        f"agenda từng hy vọng < 5 — không đạt được với đúng ràng buộc tiền đăng ký)"
    )


def test_short_session_degrades_transition_constraint_with_flag():
    """(d) A 30' session (4 measurement blocks) cannot hold 3 pairs of each
    kind: the requirement is capped (realized 1), the flag says the design
    guarantee is NOT met, and generation terminates without spinning."""
    for seed in range(20):
        s = generate_schedule(30, DESIGN, seed=seed)
        assert len(s.measurement_blocks) == 4
        assert s.realized_transition_pairs == 1
        assert not s.constraint_met
        # the degraded requirement is still enforced symmetrically
        n_on_on, n_off_off = _same_arm_pairs(s)
        assert n_on_on >= 1
        assert n_off_off >= 1
        assert abs(n_on_on - n_off_off) <= 1
        assert s.n_redraws < s.params.max_redraws


def test_transition_requirement_can_be_disabled_per_design():
    """min_transition_pairs=0 must reproduce the pre-08/09 mechanism — needed
    for honest RI redraws of sessions persisted before the constraint."""
    s = generate_schedule(90, DesignParams(min_transition_pairs=0), seed=104)
    assert s.realized_transition_pairs == 0
    assert s.constraint_met  # phase guarantee alone is the whole request now
    # some seed violates the (never requested) transition rule — the knob is real
    violated = False
    for seed in range(60):
        s = generate_schedule(90, DesignParams(min_transition_pairs=0), seed=seed)
        n_on_on, n_off_off = _same_arm_pairs(s)
        if n_on_on < 3 or n_off_off < 3 or abs(n_on_on - n_off_off) > 1:
            violated = True
            break
    assert violated, "tắt ràng buộc mà mọi lịch vẫn thỏa — test mất khả năng phân biệt"


# ---------------------------------------------------------------------------
# design_hash — cam kết thiết kế (gói Q3)
# ---------------------------------------------------------------------------


def test_design_hash_is_stable_for_the_same_design():
    """Cùng tham số + cùng seed → cùng hash, gọi bao nhiêu lần cũng thế. Cam kết
    mà đổi giữa hai lần tính thì không cam kết được gì."""
    a = design_hash(DesignParams(), 42)
    b = design_hash(DesignParams(), 42)
    assert a == b
    assert len(a) == 64
    assert set(a) <= set("0123456789abcdef")


def test_design_hash_changes_when_any_field_changes():
    """Đổi MỘT trường bất kỳ (kể cả seed) là một thiết kế khác → hash khác.
    Nếu không, đổi thiết kế giữa chừng sẽ lọt qua cam kết mà không ai thấy."""
    base = design_hash(DesignParams(), 42)
    assert design_hash(DesignParams(), 43) != base
    assert design_hash(DesignParams(block_min=10), 42) != base
    assert design_hash(DesignParams(washout_min=1), 42) != base
    assert design_hash(DesignParams(jitter_s=0), 42) != base
    assert design_hash(DesignParams(p=0.4), 42) != base
    assert design_hash(DesignParams(min_per_arm_per_phase=3), 42) != base
    assert design_hash(DesignParams(min_transition_pairs=2), 42) != base
    assert design_hash(DesignParams(endpoint_double=False), 42) != base
    assert design_hash(DesignParams(max_redraws=9_999), 42) != base


def test_design_hash_accepts_the_persisted_params_mapping():
    """Hash tính lại từ `live_session.design['params']` (dict) phải trùng hash
    tính từ dataclass — đó là cách người ngoài kiểm chứng cam kết. Thứ tự khóa
    trong dict không được ảnh hưởng (JSON chuẩn tắc, sorted keys)."""
    params = DesignParams(block_min=7, jitter_s=15)
    as_dict = asdict(params)
    shuffled = dict(reversed(list(as_dict.items())))
    assert design_hash(as_dict, 7) == design_hash(params, 7)
    assert design_hash(shuffled, 7) == design_hash(params, 7)


def test_design_hash_is_pure():
    """Hàm thuần: không đọc đồng hồ, không rút ngẫu nhiên — hash không phụ thuộc
    trạng thái RNG toàn cục."""
    random.seed(1)
    a = design_hash(DesignParams(), 5)
    random.seed(999)
    [random.random() for _ in range(10)]
    assert design_hash(DesignParams(), 5) == a
