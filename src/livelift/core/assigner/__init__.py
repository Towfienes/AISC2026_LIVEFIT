"""Two-tier randomization for LiveLift experiments.

Outer tier (``outer``): switchback schedule over time blocks — generated and
persisted BEFORE the session starts, never during broadcast.

Inner tier (``inner``): action-level randomization among candidate products
whose estimate intervals overlap, with logged propensity.
"""

from livelift.core.assigner.inner import Candidate, InnerDecision, choose_action
from livelift.core.assigner.outer import (
    Block,
    DesignParams,
    Schedule,
    draw_assignments,
    generate_schedule,
)

__all__ = [
    "Block",
    "Candidate",
    "DesignParams",
    "InnerDecision",
    "Schedule",
    "choose_action",
    "draw_assignments",
    "generate_schedule",
]
