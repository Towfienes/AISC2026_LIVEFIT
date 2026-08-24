"""Acceptance E3-04: inner-tier randomization over overlapping candidates."""

import random

import pytest

from livelift.core.assigner.inner import Candidate, choose_action


def c(pid: str, est: float, lo: float, hi: float) -> Candidate:
    return Candidate(product_id=pid, estimate=est, ci_low=lo, ci_high=hi)


def test_no_overlap_is_deterministic_with_propensity_one():
    cands = [c("A", 0.9, 0.85, 0.95), c("B", 0.5, 0.45, 0.55)]
    rng = random.Random(0)
    for _ in range(50):
        d = choose_action(cands, rng)
        assert d.product_id == "A"
        assert d.inner_propensity == 1.0
        assert not d.randomized
        assert d.overlap_set == ("A",)


def test_overlapping_pair_uniform_choice():
    """Acceptance: two overlapping candidates -> selection rate ~50/50."""
    cands = [c("A", 0.60, 0.50, 0.70), c("B", 0.58, 0.48, 0.68)]
    rng = random.Random(42)
    picks = {"A": 0, "B": 0}
    n = 10_000
    for _ in range(n):
        d = choose_action(cands, rng)
        assert d.inner_propensity == 0.5
        assert d.randomized
        assert set(d.overlap_set) == {"A", "B"}
        picks[d.product_id] += 1
    assert 0.47 <= picks["A"] / n <= 0.53


def test_three_way_overlap_propensity_third():
    cands = [
        c("A", 0.60, 0.50, 0.70),
        c("B", 0.58, 0.48, 0.68),
        c("C", 0.55, 0.45, 0.65),
    ]
    d = choose_action(cands, random.Random(1))
    assert d.inner_propensity == pytest.approx(1 / 3)
    assert len(d.overlap_set) == 3


def test_only_overlap_with_top_counts():
    """C overlaps B but not A (the top): overlap set is {A} only -> deterministic."""
    cands = [
        c("A", 0.90, 0.86, 0.94),
        c("B", 0.80, 0.75, 0.85),
        c("C", 0.78, 0.73, 0.83),
    ]
    d = choose_action(cands, random.Random(2))
    assert d.product_id == "A"
    assert d.inner_propensity == 1.0


def test_candidates_json_marks_overlap_membership():
    cands = [c("A", 0.60, 0.50, 0.70), c("B", 0.58, 0.48, 0.68), c("Z", 0.10, 0.05, 0.15)]
    d = choose_action(cands, random.Random(3))
    js = d.candidates_json()
    by_id = {row["product_id"]: row for row in js}
    assert by_id["A"]["in_overlap_set"]
    assert by_id["B"]["in_overlap_set"]
    assert not by_id["Z"]["in_overlap_set"]
    # full candidate set is logged — required for intervention_log.candidates_json
    assert len(js) == 3


def test_empty_candidates_rejected():
    with pytest.raises(ValueError):
        choose_action([], random.Random(0))


def test_invalid_interval_rejected():
    with pytest.raises(ValueError):
        c("A", 0.9, 0.95, 0.85)
