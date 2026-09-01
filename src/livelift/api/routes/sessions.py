"""Session lifecycle: create → schedule (pre-live, hard rule 4) → start → end,
plus role-separated state (operator vs blinded host — rule L6)."""

from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter, HTTPException

from livelift.api import service
from livelift.api.cards import build_candidates, build_cards
from livelift.api.schemas import (
    BlockOut,
    HostState,
    OperatorBlockState,
    OperatorState,
    PinnedProduct,
    ProductIn,
    ProductOut,
    ScheduleOut,
    ScheduleRequest,
    SessionCreate,
    SessionDetail,
    SessionOut,
    ShortlinkIn,
    ShortlinkOut,
)
from livelift.api.service import StoreDep
from livelift.api.store import ShortlinkCodeTakenError
from livelift.core.assigner import DesignParams

router = APIRouter()


# -- products ---------------------------------------------------------------


@router.post("/products", response_model=ProductOut)
def create_product(body: ProductIn, store: StoreDep) -> ProductOut:
    row = body.model_dump()
    row["created_at"] = service.now_utc()
    return ProductOut(**store.create_product(row))


@router.get("/products", response_model=list[ProductOut])
def list_products(store: StoreDep) -> list[ProductOut]:
    return [ProductOut(**p) for p in store.list_products()]


# -- shortlinks -------------------------------------------------------------


@router.post("/shortlinks", response_model=ShortlinkOut)
def create_shortlink(body: ShortlinkIn, store: StoreDep) -> ShortlinkOut:
    if store.get_product(body.product_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    row = body.model_dump()
    row["created_at"] = service.now_utc()
    # Random 8-char code; retry on the (astronomically unlikely) collision so a
    # duplicate never silently overwrites an existing click-attribution link.
    for _ in range(5):
        row["code"] = secrets.token_urlsafe(6)[:8]
        try:
            return ShortlinkOut(**store.create_shortlink(row))
        except ShortlinkCodeTakenError:
            continue
    raise HTTPException(status_code=409, detail="Không sinh được mã liên kết, thử lại")


# -- sessions ---------------------------------------------------------------


@router.post("/sessions", response_model=SessionOut)
def create_session(body: SessionCreate, store: StoreDep) -> SessionOut:
    row = body.model_dump()
    row.update(
        session_id=service.new_id(),
        status="planned",
        start_ts=None,
        end_ts=None,
        design=None,
        created_at=service.now_utc(),
    )
    return SessionOut(**store.create_session(row))


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(store: StoreDep) -> list[SessionOut]:
    return [SessionOut(**s) for s in store.list_sessions()]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, store: StoreDep) -> SessionDetail:
    return SessionDetail(**service.require_session(store, session_id))


@router.post("/sessions/{session_id}/schedule", response_model=ScheduleOut)
def create_schedule(session_id: str, body: ScheduleRequest, store: StoreDep) -> ScheduleOut:
    """Generate + persist the switchback schedule. Only before broadcast:
    regenerating is allowed while planned/scheduled, never once live (the
    assignment must never be drawn during a session — plan §6.1)."""
    session = service.require_session(store, session_id)
    if session["status"] not in ("planned", "scheduled"):
        raise HTTPException(
            status_code=409,
            detail="Lịch gán chỉ được sinh TRƯỚC khi phát sóng — phiên đã bắt đầu hoặc kết thúc",
        )
    params = DesignParams(
        block_min=body.block_min, washout_min=body.washout_min, jitter_s=body.jitter_s
    )
    seed = body.seed if body.seed is not None else secrets.randbits(63)
    updated, blocks = service.schedule_session(store, session, params, seed)
    design = updated["design"]
    realized = int(design.get("realized_min_per_arm_per_phase", 0))
    warning = None
    if realized < params.min_per_arm_per_phase:
        n_meas = len([b for b in blocks if not b.get("is_washout")])
        warning = (
            f"Phiên {session['planned_duration_min']} phút chỉ cho {n_meas} khối, nên mỗi "
            f"giai đoạn chỉ đảm bảo được {realized} khối/nhánh (thiết kế yêu cầu "
            f"{params.min_per_arm_per_phase}). Kết quả sẽ kém tin cậy hơn — cân nhắc "
            f"phiên dài hơn (từ 90 phút) hoặc khối ngắn hơn."
        )
    return ScheduleOut(
        session_id=session_id,
        status=updated["status"],
        seed=design["seed"],
        n_redraws=design["n_redraws"],
        n_on=design["n_on"],
        n_off=design["n_off"],
        blocks=[BlockOut(**b) for b in blocks],
        realized_min_per_arm_per_phase=realized,
        warning=warning,
    )


@router.get("/sessions/{session_id}/schedule", response_model=list[BlockOut])
def get_schedule(session_id: str, store: StoreDep) -> list[BlockOut]:
    service.require_session(store, session_id)
    return [BlockOut(**b) for b in store.get_blocks(session_id)]


@router.post("/sessions/{session_id}/start", response_model=SessionOut)
def start_session(session_id: str, store: StoreDep) -> SessionOut:
    session = service.require_session(store, session_id)
    if session["status"] == "live":
        raise HTTPException(status_code=409, detail="Phiên đã đang phát")
    if session["status"] == "ended":
        raise HTTPException(status_code=409, detail="Phiên đã kết thúc")
    try:
        updated = service.start_session(store, session, service.now_utc())
    except service.ScheduleMissingError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "Chưa có lịch gán khối — phiên không được phép phát sóng khi chưa sinh "
                "và lưu lịch gán (quy tắc bất biến, kế hoạch §6.1). "
                "Gọi POST /sessions/{id}/schedule trước."
            ),
        ) from exc
    store.publish(session_id, {"type": "state", "data": {"status": "live"}})
    return SessionOut(**updated)


@router.post("/sessions/{session_id}/end", response_model=SessionOut)
def end_session(session_id: str, store: StoreDep) -> SessionOut:
    session = service.require_session(store, session_id)
    if session["status"] != "live":
        raise HTTPException(status_code=409, detail="Phiên không ở trạng thái đang phát")
    updated = store.update_session(session_id, {"status": "ended", "end_ts": service.now_utc()})
    store.publish(session_id, {"type": "state", "data": {"status": "ended"}})
    return SessionOut(**updated)


# -- state (operator vs host — DISTINCT response models, rule L6) -----------


@router.get("/sessions/{session_id}/state", response_model=OperatorState | HostState)
def get_state(
    session_id: str, store: StoreDep, role: Literal["operator", "host"] = "operator"
) -> OperatorState | HostState:
    session = service.require_session(store, session_id)
    now = service.now_utc()
    elapsed = service.elapsed_seconds(session, now)
    interventions = store.list_interventions(session_id)
    pinned_id = service.current_pinned_product_id(interventions)
    pinned = store.get_product(pinned_id) if pinned_id else None

    if role == "host":
        # BLINDING (L6): HostState structurally cannot carry block info.
        return HostState(
            pinned_product=pinned["name"] if pinned else None,
            price=float(pinned["price"]) if pinned else None,
            stock=int(pinned["stock"]) if pinned else None,
            elapsed_s=elapsed,
        )

    blocks = store.get_blocks(session_id)
    current = service.block_at_offset(blocks, elapsed) if session["status"] == "live" else None
    block_state = None
    if current is not None:
        block_state = OperatorBlockState(
            index=current["block_index"],
            phase=current["phase"],
            assignment=current["assignment"],
            is_washout=bool(current["is_washout"]),
            seconds_remaining=max(0.0, current["end_offset_s"] - elapsed),
        )
    recent_clicks: dict[str, int] = {}
    for c in store.list_clicks(session_id):
        pid = c.get("product_id")
        if pid:
            recent_clicks[pid] = recent_clicks.get(pid, 0) + 1
    candidates = build_candidates(store.list_products(), recent_clicks)
    cards = build_cards(candidates, {p["product_id"]: p for p in store.list_products()})
    return OperatorState(
        session_id=session_id,
        status=session["status"],
        mode=session["mode"],
        elapsed_s=elapsed,
        current_block=block_state,
        pinned_product=(
            PinnedProduct(
                product_id=pinned["product_id"],
                name=pinned["name"],
                price=float(pinned["price"]),
                stock=int(pinned["stock"]),
            )
            if pinned
            else None
        ),
        cards=cards,
    )
