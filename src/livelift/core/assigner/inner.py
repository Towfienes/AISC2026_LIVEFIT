"""Inner-tier randomization: controlled exploration among candidate products.

Design (project description §6.2): inside an ON block, when the model proposes
pinning a product, we look at the candidate set with their estimate intervals.

- If the top candidate's interval does NOT overlap any other candidate's, the
  model is confident: pick the top deterministically, ``inner_propensity = 1``.
- If one or more candidates' intervals overlap the top's, the model cannot
  distinguish them: pick uniformly at random within that overlap set and log
  ``inner_propensity = 1 / k``. Expected cost of exploration is ~zero (the
  candidates are statistically indistinguishable to the model) while the
  logged propensity makes the data valid for off-policy / heterogeneous-effect
  estimation later.

Every decision must be logged to ``intervention_log`` with the full candidate
set (``candidates_json``), the chosen product, and the propensity.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    """A candidate product with the model's interval estimate for the action's
    short-term value (e.g. predicted CTR uplift of pinning it now)."""

    product_id: str
    estimate: float
    ci_low: float
    ci_high: float

    def __post_init__(self) -> None:
        if not (self.ci_low <= self.estimate <= self.ci_high):
            raise ValueError(
                f"candidate {self.product_id}: estimate must lie inside "
                f"[ci_low, ci_high], got {self.ci_low}, {self.estimate}, {self.ci_high}"
            )


@dataclass(frozen=True)
class InnerDecision:
    product_id: str
    inner_propensity: float
    randomized: bool
    considered: tuple[Candidate, ...]
    overlap_set: tuple[str, ...]

    def candidates_json(self) -> list[dict]:
        """Serializable form for ``intervention_log.candidates_json``."""
        return [
            {
                "product_id": c.product_id,
                "estimate": c.estimate,
                "ci_low": c.ci_low,
                "ci_high": c.ci_high,
                "in_overlap_set": c.product_id in self.overlap_set,
            }
            for c in self.considered
        ]


def _intervals_overlap(a: Candidate, b: Candidate) -> bool:
    return a.ci_low <= b.ci_high and b.ci_low <= a.ci_high


def choose_action(candidates: list[Candidate], rng: random.Random) -> InnerDecision:
    """Choose which product to pin, randomizing only under model uncertainty.

    The overlap set is every candidate whose interval overlaps the interval of
    the best candidate (highest point estimate). Ties in the point estimate are
    broken by product_id ordering before overlap detection, so the function is
    deterministic given (candidates, rng state).
    """
    if not candidates:
        raise ValueError("no candidates")

    ordered = sorted(candidates, key=lambda c: (-c.estimate, c.product_id))
    top = ordered[0]
    overlap = [c for c in ordered if _intervals_overlap(top, c)]

    if len(overlap) == 1:
        return InnerDecision(
            product_id=top.product_id,
            inner_propensity=1.0,
            randomized=False,
            considered=tuple(ordered),
            overlap_set=(top.product_id,),
        )

    chosen = overlap[rng.randrange(len(overlap))]
    return InnerDecision(
        product_id=chosen.product_id,
        inner_propensity=1.0 / len(overlap),
        randomized=True,
        considered=tuple(ordered),
        overlap_set=tuple(c.product_id for c in overlap),
    )
