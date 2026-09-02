"""E2-04 display-source rule (acceptance E2-04: automated test required).

A forecast number can never carry a confidence interval — enforced at the
schema layer so no route, template, or refactor can leak one."""

import pytest
from pydantic import ValidationError

from livelift.api.cards import build_candidates, build_cards
from livelift.api.schemas import ActionCard


def make_card(**overrides):
    base = {
        "card_id": "c1",
        "action_type": "pin",
        "product_id": "P1",
        "product_name": "Bình giữ nhiệt",
        "headline": "Ghim Bình giữ nhiệt",
        "rationale": "Biên lợi nhuận cao",
        "source": "forecast",
        "estimate": 0.42,
    }
    base.update(overrides)
    return ActionCard(**base)


def test_forecast_card_without_ci_is_valid():
    card = make_card()
    assert card.ci_low is None
    assert card.ci_high is None


def test_forecast_card_with_ci_rejected():
    with pytest.raises(ValidationError, match="E2-04"):
        make_card(ci_low=0.1)
    with pytest.raises(ValidationError, match="E2-04"):
        make_card(ci_high=0.9)
    with pytest.raises(ValidationError, match="E2-04"):
        make_card(ci_low=0.1, ci_high=0.9)


def test_experiment_card_with_ci_is_valid():
    card = make_card(source="experiment", ci_low=0.1, ci_high=0.9)
    assert card.ci_low == 0.1


def test_build_cards_never_emit_ci():
    products = [
        {"product_id": "A", "name": "SP A", "price": 100, "margin": 60, "stock": 5},
        {"product_id": "B", "name": "SP B", "price": 100, "margin": 40, "stock": 5},
        {"product_id": "C", "name": "SP C", "price": 100, "margin": 20, "stock": 5},
        {"product_id": "D", "name": "SP D", "price": 100, "margin": 10, "stock": 0},
    ]
    candidates = build_candidates(products, {"A": 3, "B": 1})
    cards = build_cards(candidates, {p["product_id"]: p for p in products})
    assert 1 <= len(cards) <= 3
    for card in cards:
        assert card.source == "forecast"
        assert card.ci_low is None
        assert card.ci_high is None
    # out-of-stock product must not be suggested
    assert all(c.product_id != "D" for c in cards)


def test_candidates_intervals_shrink_with_evidence():
    products = [
        {"product_id": "A", "name": "SP A", "price": 100, "margin": 50, "stock": 5},
        {"product_id": "B", "name": "SP B", "price": 100, "margin": 50, "stock": 5},
    ]
    sparse = build_candidates(products, {})
    # Evidence in the Gamma-Poisson model is MEASURED exposure alongside the
    # clicks (30/08 audit: a numerator without a measured denominator is not
    # evidence): 10 tick buckets of 1000 viewers pinned per product.
    ticks = [{"viewers": 1000, "pinned_product_id": pid} for pid in ["A", "B"] * 10]
    rich = build_candidates(products, {"A": 100, "B": 100}, ticks)
    width = lambda c: c.ci_high - c.ci_low  # noqa: E731
    assert width(rich[0]) < width(sparse[0])
