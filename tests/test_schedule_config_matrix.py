"""Gate (incident 12/09): NO session configuration may answer HTTP 5xx.

Reproduction that started this file — `POST /sessions/{id}/schedule` returned an
empty `500 Internal Server Error` for EVERY seed whenever the layout came out to
exactly five measurement blocks: 5/1, 10/2, 15/3, 25/5, 50/10, 75/15 … i.e. the
whole band `5 <= planned_duration_min / block_min < 6`. "Phiên 50 phút, khối 10
phút" is an ordinary thing for a shop owner to type.

Root cause — `_transition_requirement` capped the transition-balance request
with a closed-form NECESSARY bound that ignored how the arm-balance-forced
switches interact with the run structure. For phases
`[early, early, mid, late, late]` it promised k = 1 while the joint acceptance
set was EMPTY (arm balance forces a switch inside the early pair and inside the
late pair, so the only candidate same-arm pairs are (1,2) and (2,3) — they share
block 2 and cannot be one (ON,ON) and one (OFF,OFF) at once). `draw_assignments`
then burned all 10.000 redraws and raised, and the route let a bare RuntimeError
become a 500 with no body.

The gates below are the two halves of the fix:
  * the requirement level is now computed by EXACT feasibility search — checked
    here against exhaustive enumeration, so an approximate shortcut cannot creep
    back in;
  * genuinely impossible configurations answer 400 with a Vietnamese
    explanation AND an alternative, never an empty 500.
"""

from __future__ import annotations

import itertools

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.core.assigner.outer import (
    OFF,
    ON,
    DesignParams,
    RerandomizationExhaustedError,
    ScheduleInfeasibleError,
    _acceptance_set_nonempty,
    _transition_requirement,
    generate_schedule,
)


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


def _same_arm_pairs(arms):
    a = sum(1 for x, y in zip(arms, arms[1:], strict=False) if x == y == ON)
    b = sum(1 for x, y in zip(arms, arms[1:], strict=False) if x == y == OFF)
    return a, b


# ---------------------------------------------------------------------------
# 1. The exact reproduction, at the pure-function level
# ---------------------------------------------------------------------------

FIVE_BLOCK_LAYOUTS = [(5, 1), (10, 2), (15, 3), (20, 4), (25, 5), (50, 10), (75, 15)]


@pytest.mark.parametrize(("duration", "block"), FIVE_BLOCK_LAYOUTS)
def test_five_block_layouts_generate_instead_of_exploding(duration, block):
    """The deterministic 500: every seed failed, 20/20 in the field report."""
    for seed in range(20):
        schedule = generate_schedule(duration, DesignParams(block_min=block), seed=seed)
        assert len(schedule.measurement_blocks) == 5
        # degraded to the level that IS feasible, and said so
        assert schedule.realized_transition_pairs == 0
        assert not schedule.constraint_met
        assert schedule.n_redraws < schedule.params.max_redraws


def test_the_five_block_acceptance_set_really_is_empty_at_one_pair():
    """Why 0 and not 1 — the degradation is forced, not a shrug.

    Guards the direction that matters: if someone "optimizes" the search into
    promising k=1 again for this layout, the acceptance set is empty again and
    the 500 comes back.
    """
    phases = ("early", "early", "mid", "late", "late")
    assert not _acceptance_set_nonempty(phases, 2, 1)
    assert _transition_requirement(list(phases), 2, 3) == 0

    # exhaustive confirmation, straight from the acceptance predicate
    feasible = []
    for arms in itertools.product((ON, OFF), repeat=5):
        if arms[0] == arms[1] or arms[3] == arms[4]:
            continue  # early / late strata each need one block of each arm
        a, b = _same_arm_pairs(arms)
        if a >= 1 and b >= 1 and abs(a - b) <= 1:
            feasible.append(arms)
    assert feasible == []


# ---------------------------------------------------------------------------
# 2. The requirement level must equal exhaustive truth, not an estimate
# ---------------------------------------------------------------------------


def _brute_force_max_pairs(phases, min_per_arm_per_phase, min_transition_pairs):
    strata: dict[str, list[int]] = {}
    for i, ph in enumerate(phases):
        strata.setdefault(ph, []).append(i)
    required = {ph: min(min_per_arm_per_phase, len(ix) // 2) for ph, ix in strata.items()}
    best = 0
    for arms in itertools.product((ON, OFF), repeat=len(phases)):
        ok = True
        for ph, ix in strata.items():
            n_on = sum(1 for i in ix if arms[i] == ON)
            if n_on < required[ph] or (len(ix) - n_on) < required[ph]:
                ok = False
                break
        if not ok:
            continue
        a, b = _same_arm_pairs(arms)
        if abs(a - b) <= 1:
            best = max(best, min(a, b))
    return min(best, min_transition_pairs)


def test_transition_requirement_matches_exhaustive_search():
    """Exact, not conservative-and-hopeful: 3.432 layouts, zero disagreement.

    Covers every contiguous early/mid/late split up to 13 blocks × every
    arm-balance level the design uses × every transition request. Both
    directions fail the test: over-promising empties the acceptance set (the
    12/09 outage), under-promising weakens designs that are perfectly runnable.
    """
    checked = 0
    for n in range(2, 14):
        for cut_a, cut_b in itertools.combinations(range(1, n), 2):
            phases = ["early"] * cut_a + ["mid"] * (cut_b - cut_a) + ["late"] * (n - cut_b)
            for min_per_arm in (0, 1, 2):
                for request in (0, 1, 2, 3):
                    expected = _brute_force_max_pairs(phases, min_per_arm, request)
                    got = _transition_requirement(phases, min_per_arm, request)
                    assert got == expected, (phases, min_per_arm, request, got, expected)
                    checked += 1
    assert checked == 3432


def test_accepted_schedules_actually_hold_the_requirement_they_claim():
    """The claim on the Schedule must be the property of the drawn vector."""
    for duration, block in ((5, 1), (25, 5), (30, 5), (50, 10), (60, 5), (90, 5), (120, 3)):
        for seed in range(15):
            schedule = generate_schedule(duration, DesignParams(block_min=block), seed=seed)
            k = schedule.realized_transition_pairs
            if k <= 0:
                continue
            arms = [b.assignment for b in schedule.measurement_blocks]
            a, b = _same_arm_pairs(arms)
            assert a >= k, (duration, block, seed, a, k)
            assert b >= k, (duration, block, seed, b, k)
            assert abs(a - b) <= 1, (duration, block, seed, a, b)


# ---------------------------------------------------------------------------
# 3. The sweep: nothing in a wide configuration space may raise
# ---------------------------------------------------------------------------


def test_no_configuration_exhausts_the_redraw_loop():
    """Pure-function sweep — 5..240 minutes × 9 block lengths × 2 washouts.

    Either a Schedule, or a ScheduleInfeasibleError that explains itself in
    Vietnamese. RerandomizationExhaustedError (the 500's cause) must not occur
    anywhere in the space the API can reach.
    """
    infeasible = 0
    generated = 0
    for duration in range(5, 241, 1):
        for block in (1, 2, 3, 5, 10, 15, 20, 30, 60):
            for washout in (0, 2):
                params = DesignParams(block_min=block, washout_min=washout)
                try:
                    generate_schedule(duration, params, seed=7)
                    generated += 1
                except ScheduleInfeasibleError as exc:
                    infeasible += 1
                    text = str(exc)
                    assert "phút" in text, text  # Vietnamese, not a bare repr
                    assert "Hãy chọn" in text or "kéo dài" in text, text
                except RerandomizationExhaustedError as exc:  # pragma: no cover
                    pytest.fail(f"{duration}'/{block}' washout={washout}: {exc}")
    assert generated > 3500
    assert infeasible > 0  # the 400 branch is real, not dead code


# ---------------------------------------------------------------------------
# 4. The same sweep over HTTP — the gate the incident asked for
# ---------------------------------------------------------------------------

GRID = list(itertools.product((30, 45, 50, 60, 90, 120), (2, 3, 5, 10)))


def test_schedule_endpoint_never_answers_5xx_over_the_config_grid(client):
    """Every duration × block the desk offers: 200, or 400 that helps.

    50/10 — "phiên 50 phút, đổi khối mỗi 10 phút" — is in this grid and used to
    be a hard 500 on every seed.
    """
    for duration, block in GRID:
        created = client.post(
            "/sessions",
            json={"platform": "sim", "mode": "auto", "planned_duration_min": duration},
        )
        assert created.status_code == 200, created.text
        session_id = created.json()["session_id"]
        response = client.post(
            f"/sessions/{session_id}/schedule",
            json={"block_min": block, "washout_min": 0, "jitter_s": 0, "seed": 4242},
        )
        assert response.status_code < 500, (
            f"{duration} phút / khối {block} phút → HTTP {response.status_code}: {response.text}"
        )
        if response.status_code == 200:
            body = response.json()
            assert body["blocks"], (duration, block)
        else:
            assert response.status_code == 400, (duration, block, response.text)
            assert response.json()["detail"].strip(), "400 câm cũng không chấp nhận được"


def test_fifty_minute_ten_minute_block_now_schedules_with_a_useful_warning(client):
    """The exact configuration from the field report, end to end."""
    created = client.post(
        "/sessions",
        json={"platform": "sim", "mode": "auto", "planned_duration_min": 50},
    )
    session_id = created.json()["session_id"]
    response = client.post(
        f"/sessions/{session_id}/schedule",
        json={"block_min": 10, "washout_min": 0, "jitter_s": 0, "seed": 4242},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len([b for b in body["blocks"] if not b["is_washout"]]) == 5
    assert body["realized_transition_pairs"] == 0
    # the operator is told BEFORE broadcast, and told what to type instead
    assert body["warning"]
    assert "khối 4 phút" in body["warning"], body["warning"]


def test_session_shorter_than_one_block_is_a_400_with_an_alternative(client):
    """`planned_duration_min=5, block_min=10` used to be a 500 as well."""
    created = client.post(
        "/sessions",
        json={"platform": "sim", "mode": "auto", "planned_duration_min": 5},
    )
    session_id = created.json()["session_id"]
    response = client.post(
        f"/sessions/{session_id}/schedule",
        json={"block_min": 10, "washout_min": 0, "jitter_s": 0, "seed": 1},
    )
    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert "ngắn hơn một khối" in detail, detail
    assert "gợi ý" in detail, detail
