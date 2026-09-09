"""Action execution (inner-tier randomization) and manual overrides.

Every executed action lands in ``intervention_log`` with block_id, server ts,
source, inner_propensity and the full candidate set (candidates_json) —
the three fields no competing tool records (description §9.2).

It ALSO lands in the append-only ``exposure_event`` table (gói Q3, migration
0006): the same fact recorded as "what was actually on screen, when", separate
from the mutable intervention log. ``intervention_log`` stays the decision
record (why this product, at what propensity); ``exposure_event`` is the
exposure record compliance is derived from
(:func:`livelift.core.quality.derive_compliance`)."""

from __future__ import annotations

import random

from fastapi import APIRouter, HTTPException

from livelift.api import service
from livelift.api.cards import build_candidates
from livelift.api.schemas import (
    CandidateOut,
    ExecuteOut,
    ExecuteRequest,
    OverrideOut,
    OverrideRequest,
)
from livelift.api.service import StoreDep
from livelift.core.assigner import Candidate, choose_action, intervals_overlap

router = APIRouter()

# Operational randomness for the inner tier. Not seeded per-request: the
# realized choice does not need to be reproducible — validity comes from the
# LOGGED propensity, not from replaying the draw (§6.2).
_rng = random.Random()


def _seconds_since_last_switch(blocks: list[dict], elapsed: float) -> float | None:
    """Seconds since the last block boundary before `elapsed` (diagnostic
    covariate for carryover analysis — research P0 item 5)."""
    boundaries = sorted(b["start_offset_s"] for b in blocks)
    past = [b for b in boundaries if b <= elapsed]
    return elapsed - past[-1] if past else None


def product_id_from_card(card_id: str | None) -> str | None:
    """Extract the product from a desk card id (``card-{rank}-{product_id}``,
    see :func:`livelift.api.cards.build_cards`).

    Fallback for clients that send only ``card_id``: before this, the request
    carried no usable product and the server randomized over the WHOLE
    candidate set — the operator clicked card A and product B got pinned.
    """
    if not card_id:
        return None
    parts = card_id.split("-", 2)
    if len(parts) == 3 and parts[0] == "card" and parts[2]:
        return parts[2]
    return None


def scope_candidates_to_product(
    candidates: list[Candidate], product_id: str
) -> list[Candidate] | None:
    """Scope the inner-tier candidate set to the card the desk clicked.

    Keeps the §6.2 exploration contract with the clicked card as the anchor:
    every candidate whose Gamma-Poisson interval overlaps the clicked card's
    interval stays in (randomized with a logged propensity — exploration
    among statistically indistinguishable products is free); once intervals
    separate, the set collapses to exactly the clicked product. Returns
    ``None`` when the product is no longer a candidate (out of stock, or the
    suggestion set changed since the desk rendered the card).
    """
    target = next((c for c in candidates if c.product_id == product_id), None)
    if target is None:
        return None
    return [c for c in candidates if intervals_overlap(target, c)]


@router.post("/sessions/{session_id}/actions/execute", response_model=ExecuteOut)
def execute_action(session_id: str, body: ExecuteRequest, store: StoreDep) -> ExecuteOut:
    """Execute a pin through the system (source='model').

    Only inside an ON block of a live session: during OFF blocks the operator
    runs their usual playbook and the system must not intervene — executing
    there would contaminate the control arm."""
    session = service.require_session(store, session_id)
    if session["status"] != "live":
        raise HTTPException(status_code=409, detail="Phiên chưa phát hoặc đã kết thúc")

    now = service.now_utc()
    elapsed = service.elapsed_seconds(session, now)
    blocks = store.get_blocks(session_id)
    block = service.block_at_offset(blocks, elapsed)
    if block is None:
        raise HTTPException(status_code=409, detail="Ngoài khung khối thí nghiệm")
    if block["is_washout"]:
        raise HTTPException(status_code=409, detail="Đang trong khoảng washout")
    if block["assignment"] != "ON":
        raise HTTPException(
            status_code=409,
            detail=(
                "Khối TẮT: đội vận hành làm theo cách thường lệ — hệ thống không "
                "can thiệp để bảo toàn nhánh đối chứng"
            ),
        )

    recent_clicks: dict[str, int] = {}
    for c in store.list_clicks(session_id):
        pid = c.get("product_id")
        if pid:
            recent_clicks[pid] = recent_clicks.get(pid, 0) + 1
    candidates = build_candidates(
        store.list_products(), recent_clicks, store.list_ticks(session_id)
    )
    if not candidates:
        raise HTTPException(status_code=409, detail="Không có sản phẩm còn hàng để ghim")

    requested = body.product_id or product_id_from_card(body.card_id)
    if requested is not None:
        # Desk clicked a specific card: scope to that card's overlap set.
        # NEVER fall back silently to the full candidate set — that is exactly
        # the "clicked card A, pinned product B" bug.
        scoped = scope_candidates_to_product(candidates, requested)
        if scoped is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Thẻ không còn hợp lệ — sản phẩm đã hết hàng hoặc danh sách "
                    "gợi ý vừa thay đổi. Chờ thẻ mới rồi thử lại."
                ),
            )
        candidates = scoped

    decision = choose_action(candidates, _rng)
    row = {
        "action_id": service.new_id(),
        "block_id": block["block_id"],
        "ts": now,
        "client_ts": None,
        "action_type": "pin",
        "product_id": decision.product_id,
        "source": "model",
        "inner_propensity": decision.inner_propensity,
        "candidates_json": decision.candidates_json(),
        "executed": True,
        "override_reason": None,
        "seconds_since_last_switch": _seconds_since_last_switch(blocks, elapsed),
    }
    store.add_intervention(session_id, row)
    store.add_exposure_event(
        session_id,
        {
            "block_idx": block["block_index"],
            "event_type": "pin",
            "product_id": decision.product_id,
            "ts_utc": now,
            # ack_latency_ms needs the desk's client_ts, which the execute
            # request does not carry yet — NULL is the honest value, not 0.
            "ack_latency_ms": None,
            "source": "model",
        },
    )
    store.publish(
        session_id,
        {"type": "state", "data": {"pinned_product_id": decision.product_id}},
    )
    return ExecuteOut(
        action_id=row["action_id"],
        block_index=block["block_index"],
        product_id=decision.product_id,
        inner_propensity=decision.inner_propensity,
        randomized=decision.randomized,
        overlap_set=list(decision.overlap_set),
        considered=[CandidateOut(**c) for c in decision.candidates_json()],
    )


@router.post("/sessions/{session_id}/actions/override", response_model=OverrideOut)
def override_action(session_id: str, body: OverrideRequest, store: StoreDep) -> OverrideOut:
    """Manual intervention (source='human'). The reason field is restricted to
    the three allowed safety reasons at the type level — anything else is a
    422 before this handler runs (hard rule 5)."""
    session = service.require_session(store, session_id)
    now = service.now_utc()
    elapsed = service.elapsed_seconds(session, now)
    blocks = store.get_blocks(session_id)
    block = service.block_at_offset(blocks, elapsed) if session["status"] == "live" else None

    action_type = "pin" if body.product_id else "unpin"
    row = {
        "action_id": service.new_id(),
        "block_id": block["block_id"] if block else None,
        "ts": now,
        "client_ts": None,
        "action_type": action_type,
        "product_id": body.product_id,
        "source": "human",
        "inner_propensity": None,
        "candidates_json": None,
        "executed": True,
        "override_reason": body.reason,
        "seconds_since_last_switch": _seconds_since_last_switch(blocks, elapsed) if block else None,
    }
    store.add_intervention(session_id, row)
    store.add_exposure_event(
        session_id,
        {
            # None when the override lands outside every block (not live yet /
            # already ended). Kept as a row rather than dropped — flag,
            # don't drop; derive_compliance counts it as unattributed.
            "block_idx": block["block_index"] if block else None,
            "event_type": action_type,
            "product_id": body.product_id,
            "ts_utc": now,
            "ack_latency_ms": None,
            "source": "human",
        },
    )
    if block is not None:
        store.increment_override(block["block_id"])
    store.publish(session_id, {"type": "state", "data": {"pinned_product_id": body.product_id}})
    return OverrideOut(
        action_id=row["action_id"],
        action_type=action_type,
        product_id=body.product_id,
        override_reason=body.reason,
        block_index=block["block_index"] if block else None,
    )
