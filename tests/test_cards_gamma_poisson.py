"""Gamma-Poisson candidate scoring (approved method upgrade, 09/2026).

Inner-tier candidate intervals are no longer fabricated from a margin
heuristic: they are posterior intervals of a conjugate Gamma-Poisson click
rate in the primary-outcome units (clicks per 1000 viewer-seconds). That
makes the inner assigner's overlap-randomization behavior meaningful:
uniform exploration with propensity 1/k under genuine uncertainty, a
deterministic pick once the data separates the products.
"""

from __future__ import annotations

import random

import pytest

from livelift.api.cards import build_candidates
from livelift.core.assigner import choose_action
from livelift.core.features import Tick, product_exposure


def tick(i, viewers, pin):
    return Tick(
        bucket_start_s=i * 30,
        viewers=viewers,
        comment_count=0,
        like_count=0,
        click_count=0,
        pinned_product_id=pin,
    )


def product(pid, stock=5):
    return {"product_id": pid, "name": f"SP {pid}", "price": 100, "margin": 50, "stock": stock}


# -- product_exposure -------------------------------------------------------


def test_product_exposure_attributes_viewer_seconds_per_pin():
    ticks = [
        tick(0, 100, "A"),
        tick(1, 50, "A"),
        tick(2, 80, "B"),
        tick(3, 10, None),  # nothing pinned: exposure accrues to no product
        tick(4, 20, "B"),
    ]
    exp = product_exposure(ticks)
    assert exp == {"A": (100 + 50) * 30, "B": (80 + 20) * 30}
    assert None not in exp


# -- cold start: the point of the design ------------------------------------


def test_cold_start_identical_intervals_and_uniform_exploration():
    """With zero data all products share the prior: identical intervals ->
    full overlap -> the inner tier explores uniformly with propensity 1/3."""
    products = [product("A"), product("B"), product("C")]
    cands = build_candidates(products, {})
    assert len(cands) == 3
    distinct = {(c.estimate, c.ci_low, c.ci_high) for c in cands}
    assert len(distinct) == 1  # IDENTICAL estimate and interval
    assert cands[0].ci_low < cands[0].ci_high  # a real interval, not a point
    # prior mean is the fallback pooled rate: 1.0 click / 1000 viewer-seconds
    assert cands[0].estimate == pytest.approx(1.0)

    decision = choose_action(cands, random.Random(7))
    assert decision.randomized
    assert decision.inner_propensity == 1 / 3
    assert set(decision.overlap_set) == {"A", "B", "C"}


# -- shrinkage: the prior tames tiny-exposure outliers ----------------------


def test_prior_tames_huge_raw_rate_on_tiny_exposure():
    """X has 1 click on 30 viewer-seconds (raw rate ~33/1000vs); Y has 30
    clicks on 21_000 viewer-seconds (raw ~1.43). Raw rate ranks X first;
    the posterior mean ranks Y first."""
    products = [product("X"), product("Y"), product("Z")]
    ticks = [
        tick(0, 1.0, "X"),  # 30 viewer-seconds
        tick(1, 700.0, "Y"),  # 21_000 viewer-seconds
        tick(2, 1000.0, "Z"),
        tick(3, 1000.0, "Z"),  # 60_000 viewer-seconds
    ]
    clicks = {"X": 1, "Y": 30, "Z": 5}
    raw_rate = {"X": 1 / 0.03, "Y": 30 / 21.0, "Z": 5 / 60.0}
    assert raw_rate["X"] > raw_rate["Y"]  # the naive ranking being tamed

    cands = build_candidates(products, clicks, ticks)
    assert cands[0].product_id == "Y"


# -- separation: exploration stops when the data distinguishes products ----


def test_separated_intervals_yield_deterministic_choice():
    products = [product("A"), product("B")]
    # 90_000 viewer-seconds pinned on each product
    ticks = [tick(i, 1000.0, "A") for i in range(3)] + [tick(i + 3, 1000.0, "B") for i in range(3)]
    cands = build_candidates(products, {"A": 200, "B": 50}, ticks)
    a = next(c for c in cands if c.product_id == "A")
    b = next(c for c in cands if c.product_id == "B")
    assert a.ci_low > b.ci_high  # intervals no longer overlap

    decision = choose_action(cands, random.Random(0))
    assert decision.product_id == "A"
    assert decision.inner_propensity == 1.0
    assert not decision.randomized


# -- units sanity -----------------------------------------------------------


def test_estimates_are_clicks_per_1000_viewer_seconds():
    products = [product("A")]
    ticks = [tick(0, 1000.0, "A")]  # 30_000 viewer-seconds of exposure
    cands = build_candidates(products, {"A": 30}, ticks)
    # 30 clicks / 30_000 viewer-seconds = 1.0 click per 1000 viewer-seconds
    assert cands[0].estimate == pytest.approx(1.0, abs=0.25)  # +- prior pull
    assert cands[0].estimate > 0.1  # not per-viewer-second units (~0.001)


# -- store-row ticks (what the routes pass) ---------------------------------


def test_accepts_persisted_tick_rows():
    products = [product("A"), product("B")]
    rows = [
        {"viewers": 1000, "pinned_product_id": "A", "click_count": 0},
        {"viewers": 1000, "pinned_product_id": "B", "click_count": 0},
    ]
    cands = build_candidates(products, {"A": 60, "B": 6}, rows)
    assert cands[0].product_id == "A"
    assert all(c.ci_low >= 0.0 for c in cands)
