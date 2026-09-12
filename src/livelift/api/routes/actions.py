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
from livelift.api.cards import MAX_CARDS, build_candidates, pin_cards_blocked_reason
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


def refusal_for_unpinnable_product(
    product_id: str,
    products_by_id: dict[str, dict],
    ranked: list[Candidate],
    *,
    from_card: bool,
) -> HTTPException:
    """The TRUE reason ``product_id`` cannot be pinned right now, as an error.

    Until 12/09 every one of these paths returned the same sentence — *"Thẻ
    không còn hợp lệ — sản phẩm đã hết hàng hoặc danh sách gợi ý vừa thay đổi.
    Chờ thẻ mới rồi thử lại."* — and on the case that actually happened in the
    field (a product created minutes earlier, ``stock = 50``, simply outside
    the three suggested cards) BOTH of its two stated reasons were false and
    its advice was unfollowable: the suggestion list never becomes that
    product, so "wait and retry" is an instruction to wait forever
    (``docs/benchmarks/kiem-chung-van-hanh.md`` §2.4b).

    Three genuinely different situations, three answers:

    * the product is not in the catalogue at all → 404, name it;
    * it is in the catalogue but out of stock → 409, quote the real stock;
    * it is in stock and eligible, but not among the ``MAX_CARDS`` suggested
      right now → 409, say WHERE it ranks and what can actually be done.

    ``from_card`` separates the two readings of the last case. A desk that
    clicked a rendered card is holding a STALE card (it was in the top set
    when it was drawn, it is not now), and refreshing really does fix that. A
    caller that named a product outright is not waiting for anything, so it is
    told the ranking rule and the one path that pins an unsuggested product —
    a human override, flagged as exactly that.
    """
    product = products_by_id.get(product_id)
    if product is None:
        detail = (
            f"Không tìm thấy sản phẩm «{product_id}» trong kho. "
            "Tạo sản phẩm bằng POST /products rồi ghim lại."
        )
        if from_card:
            detail = (
                f"Thẻ trỏ tới sản phẩm «{product_id}» không còn trong kho "
                "(đã bị gỡ khỏi danh mục). Tải lại GET /sessions/{id}/state để lấy "
                "danh sách thẻ hiện hành."
            )
        return HTTPException(status_code=404, detail=detail)

    stock = int(product.get("stock") or 0)
    if stock <= 0:
        return HTTPException(
            status_code=409,
            detail=(
                f"«{product.get('name') or product_id}» đang HẾT HÀNG (tồn kho {stock}) "
                "nên không được đề xuất ghim. Cập nhật tồn kho rồi ghim lại."
            ),
        )

    order = [c.product_id for c in ranked]
    rank = order.index(product_id) + 1 if product_id in order else len(order)
    name = product.get("name") or product_id
    if from_card:
        return HTTPException(
            status_code=409,
            detail=(
                f"Thẻ đã cũ: «{name}» còn {stock} trong kho nhưng hiện KHÔNG nằm trong "
                f"{MAX_CARDS} thẻ gợi ý (đang xếp thứ {rank}/{len(order)} theo tỷ lệ nhấp "
                "hợp lệ ước lượng). Tải lại GET /sessions/{id}/state để lấy danh sách thẻ "
                "hiện hành rồi bấm một thẻ trong đó."
            ),
        )
    return HTTPException(
        status_code=409,
        detail=(
            f"«{name}» còn {stock} trong kho và vẫn đủ điều kiện lên thẻ, nhưng bàn chỉ "
            f"gợi ý {MAX_CARDS} sản phẩm xếp đầu theo tỷ lệ nhấp hợp lệ ước lượng; sản phẩm "
            f"này đang đứng thứ {rank}/{len(order)}. Hệ thống chỉ tự ghim trong tập gợi ý "
            "vì propensity của tầng trong được ghi trên đúng tập đó (kế hoạch §6.2); ghim "
            "ngoài tập sẽ làm bản ghi ngẫu nhiên hoá sai sự thật. Muốn ghim ĐÚNG sản phẩm "
            "này: bấm POST /sessions/{id}/actions/override kèm một trong ba lý do cho phép "
            "— thao tác đó được ghi là can thiệp của NGƯỜI (không tính vào tuân thủ của "
            "nhánh BẬT), hoặc chọn một trong các thẻ đang được gợi ý."
        ),
    )


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
    # ONE definition of "this session cannot be acted on", shared with the desk
    # state that decides whether to offer cards at all — so the refusal and the
    # empty card list can never tell two different stories.
    blocked = pin_cards_blocked_reason(session["status"], service.is_analysis_only(session))
    if blocked is not None:
        raise HTTPException(status_code=409, detail=f"Không ghim được: {blocked}.")

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
    products = store.list_products()
    # The FULL ranking, not just the displayed slice: a refusal has to be able
    # to say where the requested product actually stands. The suggestion set
    # stays `MAX_CARDS` — that limit is the desk's, and it is the one the
    # inner-tier propensity is logged over (§6.2).
    ranked = build_candidates(
        products, recent_clicks, store.list_ticks(session_id), top_k=max(len(products), 1)
    )
    candidates = ranked[:MAX_CARDS]
    if not candidates:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Không có sản phẩm nào còn hàng để ghim: cả {len(products)} sản phẩm "
                "trong kho đều có tồn kho 0. Cập nhật tồn kho bằng POST /products."
            ),
        )

    requested = body.product_id or product_id_from_card(body.card_id)
    if requested is not None:
        # Desk clicked a specific card: scope to that card's overlap set.
        # NEVER fall back silently to the full candidate set — that is exactly
        # the "clicked card A, pinned product B" bug.
        scoped = scope_candidates_to_product(candidates, requested)
        if scoped is None:
            raise refusal_for_unpinnable_product(
                requested,
                {p["product_id"]: p for p in products},
                ranked,
                # A desk sends card_id AND product_id for the same card; a
                # script that names a product outright sends no card at all.
                from_card=product_id_from_card(body.card_id) == requested,
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
