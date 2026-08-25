"""Action-card and inner-candidate generation.

Two distinct artifacts come out of the same heuristic, and the distinction IS
the E2-04 rule:

- :func:`build_candidates` — internal ``Candidate`` objects with interval
  estimates. The intervals exist ONLY so the inner assigner can detect model
  uncertainty (overlap) and randomize with a logged propensity. They are never
  displayed.
- :func:`build_cards` — the ``ActionCard`` payloads shown on the desk. They
  are ``source='forecast'`` and therefore carry NO interval fields (the
  schema validator would reject them anyway).

The scoring heuristic is deliberately simple and transparent (description
§4.2: margin-weighted with a recent-click signal — no full optimization in
competition season). Model A (LightGBM forecast) can replace ``_score``
behind the same signatures later.
"""

from __future__ import annotations

import math
from typing import Any

from livelift.api.schemas import ActionCard
from livelift.core.assigner import Candidate

MAX_CARDS = 3


def _score(product: dict[str, Any], recent_clicks: int, total_recent_clicks: int) -> float:
    """Margin share x recent-interest multiplier, in [0, ~2]."""
    price = float(product.get("price") or 0.0)
    margin = float(product.get("margin") or 0.0)
    margin_share = margin / price if price > 0 else 0.0
    interest = recent_clicks / total_recent_clicks if total_recent_clicks > 0 else 0.0
    return margin_share * (1.0 + interest)


def build_candidates(
    products: list[dict[str, Any]],
    recent_clicks_by_product: dict[str, int],
    top_k: int = MAX_CARDS,
) -> list[Candidate]:
    """Rank in-stock products and wrap the top ``top_k`` as inner-tier
    candidates with uncertainty intervals.

    Interval width shrinks with click evidence (±0.5/√(1+n)): with little
    data the intervals overlap, so the inner assigner explores; as evidence
    accumulates they separate and the choice becomes deterministic — exactly
    the "controlled exploration" contract of §6.2.
    """
    in_stock = [p for p in products if int(p.get("stock") or 0) > 0]
    total_recent = sum(recent_clicks_by_product.get(p["product_id"], 0) for p in in_stock)
    scored = sorted(
        in_stock,
        key=lambda p: (
            -_score(p, recent_clicks_by_product.get(p["product_id"], 0), total_recent),
            p["product_id"],
        ),
    )
    candidates = []
    for p in scored[:top_k]:
        n_clicks = recent_clicks_by_product.get(p["product_id"], 0)
        est = _score(p, n_clicks, total_recent)
        half_width = 0.5 / math.sqrt(1.0 + n_clicks)
        candidates.append(
            Candidate(
                product_id=p["product_id"],
                estimate=est,
                ci_low=est - half_width,
                ci_high=est + half_width,
            )
        )
    return candidates


def build_cards(
    candidates: list[Candidate],
    products_by_id: dict[str, dict[str, Any]],
) -> list[ActionCard]:
    """Forecast cards for the desk — E2-04: no interval fields, ever."""
    cards = []
    for i, c in enumerate(candidates):
        product = products_by_id.get(c.product_id, {})
        name = str(product.get("name") or c.product_id)
        margin = float(product.get("margin") or 0.0)
        cards.append(
            ActionCard(
                card_id=f"card-{i}-{c.product_id}",
                action_type="pin",
                product_id=c.product_id,
                product_name=name,
                headline=f"Ghim {name}",
                rationale=(
                    f"Biên lợi nhuận {margin:,.0f}đ/sản phẩm, còn "
                    f"{int(product.get('stock') or 0)} trong kho"
                ),
                source="forecast",
                estimate=round(c.estimate, 4),
            )
        )
    return cards
