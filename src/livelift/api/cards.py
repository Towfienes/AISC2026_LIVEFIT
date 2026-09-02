"""Action-card and inner-candidate generation.

Two distinct artifacts come out of the same posterior, and the distinction IS
the E2-04 rule:

- :func:`build_candidates` — internal ``Candidate`` objects with interval
  estimates. The intervals exist ONLY so the inner assigner can detect model
  uncertainty (overlap) and randomize with a logged propensity. They are never
  displayed.
- :func:`build_cards` — the ``ActionCard`` payloads shown on the desk. They
  are ``source='forecast'`` and therefore carry NO interval fields (the
  schema validator would reject them anyway).

Scoring model (adversarial method review, 09/2026): a Gamma-Poisson conjugate
click rate per product, in the SAME units as the primary outcome — clicks per
1000 viewer-seconds. ``clicks_j`` within the session is the Poisson count; the
denominator is the viewer-seconds actually measured while product j was pinned
(:func:`livelift.core.features.product_exposure`), so numerator and
denominator share the same support (the lesson of the 30/08 audit). The
earlier margin heuristic FABRICATED its intervals, which made the inner tier's
overlap-randomization arbitrary; posterior intervals give that exploration
behavior a real statistical meaning.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from livelift.api.schemas import ActionCard
from livelift.core.assigner import Candidate
from livelift.core.features import Tick, product_exposure

MAX_CARDS = 3

UNIT_VIEWER_S = 1000.0
"""One exposure unit = 1000 viewer-seconds (the primary-outcome denominator)."""

PRIOR_PSEUDO_EXPOSURE_UNITS = 5.0
"""``n0``: prior pseudo-exposure, in units of 1000 viewer-seconds."""

FALLBACK_POOLED_RATE = 1.0
"""Clicks per 1000 viewer-seconds assumed when the session has no data at all."""

INTERVAL_K = 1.0
"""Candidate intervals are ``mu ± K*sd``. The width is tunable from pilot
logs; K=1 keeps healthy overlap early (more inner-tier exploration) without
letting clearly separated products keep randomizing."""


def _as_ticks(ticks: Sequence[Tick | Mapping[str, Any]] | None) -> list[Tick]:
    """Adapt persisted ``session_tick`` rows to feature-layer ``Tick``s.

    Only the fields :func:`product_exposure` reads (``viewers``,
    ``pinned_product_id``) matter here; the bucket offset is synthesized
    because store rows carry wall-clock buckets, not session offsets.
    """
    out: list[Tick] = []
    for i, t in enumerate(ticks or ()):
        if isinstance(t, Tick):
            out.append(t)
            continue
        out.append(
            Tick(
                bucket_start_s=i * 30,
                viewers=float(t.get("viewers") or 0.0),
                comment_count=0,
                like_count=0,
                click_count=int(t.get("click_count") or 0),
                pinned_product_id=t.get("pinned_product_id"),
            )
        )
    return out


def build_candidates(
    products: list[dict[str, Any]],
    recent_clicks_by_product: dict[str, int],
    ticks: Sequence[Tick | Mapping[str, Any]] | None = None,
    top_k: int = MAX_CARDS,
) -> list[Candidate]:
    """Score in-stock products with a Gamma-Poisson posterior and wrap the
    top ``top_k`` as inner-tier candidates with posterior intervals.

    Prior: ``a0 = pooled_rate * n0``, ``b0 = n0`` with ``n0 = 5`` units of
    pseudo-exposure, where ``pooled_rate`` is the session's overall clicks
    per 1000 viewer-seconds (falling back to ``FALLBACK_POOLED_RATE`` when
    nothing has been measured yet). Posterior per product j:
    ``alpha_j = a0 + clicks_j``, ``beta_j = b0 + exposure_units_j``;
    ``mu_j = alpha_j / beta_j``, ``sd_j = sqrt(alpha_j) / beta_j``; the
    candidate interval is ``mu ± INTERVAL_K * sd`` clipped at 0.

    COLD-START PROPERTY (the point of the design): with zero data every
    product carries exactly the prior, so all candidates have IDENTICAL
    estimates and intervals → the intervals fully overlap → the inner tier
    (:func:`livelift.core.assigner.choose_action`) explores uniformly with a
    correctly logged propensity ``1/k``, instead of locking onto an arbitrary
    margin ranking. As exposure accumulates, ``beta`` grows linearly while
    ``sqrt(alpha)`` grows sub-linearly: intervals shrink and separate, and
    the choice becomes deterministic — the controlled-exploration contract of
    §6.2.

    ``ticks`` may be feature-layer :class:`Tick` objects or persisted
    ``session_tick`` rows. Display ranking is by posterior mean descending,
    ties broken stably by ``product_id``.
    """
    in_stock = [p for p in products if int(p.get("stock") or 0) > 0]
    exposure_units = {
        pid: vs / UNIT_VIEWER_S for pid, vs in product_exposure(_as_ticks(ticks)).items()
    }
    total_clicks = sum(recent_clicks_by_product.values())
    total_units = sum(exposure_units.values())
    pooled_rate = total_clicks / total_units if total_units > 0 else FALLBACK_POOLED_RATE
    a0 = pooled_rate * PRIOR_PSEUDO_EXPOSURE_UNITS
    b0 = PRIOR_PSEUDO_EXPOSURE_UNITS

    posterior: list[tuple[str, float, float]] = []
    for p in in_stock:
        pid = p["product_id"]
        alpha = a0 + recent_clicks_by_product.get(pid, 0)
        beta = b0 + exposure_units.get(pid, 0.0)
        posterior.append((pid, alpha / beta, math.sqrt(alpha) / beta))
    posterior.sort(key=lambda item: (-item[1], item[0]))
    return [
        Candidate(
            product_id=pid,
            estimate=mu,
            ci_low=max(0.0, mu - INTERVAL_K * sd),
            ci_high=mu + INTERVAL_K * sd,
        )
        for pid, mu, sd in posterior[:top_k]
    ]


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
