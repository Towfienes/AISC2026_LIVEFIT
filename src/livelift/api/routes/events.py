"""Event ingestion: comments (scrub-first, hard rule 1) and ticks."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter

from livelift.api import service
from livelift.api.schemas import CommentIn, CommentOut, TickIn, TickOut
from livelift.api.service import StoreDep
from livelift.ingest.pii import scrub
from livelift.nlp.intent import classify

router = APIRouter()

TICK_S = 30


@router.post("/sessions/{session_id}/comments", response_model=CommentOut)
def post_comment(session_id: str, body: CommentIn, store: StoreDep) -> CommentOut:
    """Store a comment. The raw text is scrubbed BEFORE any persistence or
    logging; only the scrubbed text exists beyond this function's locals.
    (Ingest already scrubs — running it again here is defense in depth and
    is idempotent.)"""
    session = service.require_session(store, session_id)
    now = service.now_utc()
    result = scrub(body.text)
    intent = classify(result.text)

    block_id = None
    if session["status"] == "live":
        elapsed = service.elapsed_seconds(session, now)
        block = service.block_at_offset(store.get_blocks(session_id), elapsed)
        if block is not None:
            block_id = block["block_id"]

    row = {
        "comment_id": service.new_id(),
        "session_id": session_id,
        "block_id": block_id,
        "ts": now,
        "text_scrubbed": result.text,
        "pii_kinds": sorted({m.kind for m in result.matches}),
        "intent_label": intent,
        "sentiment": None,
    }
    stored = store.add_comment(session_id, row)
    out = CommentOut(
        comment_id=stored["comment_id"],
        session_id=session_id,
        block_id=stored.get("block_id"),
        ts=stored["ts"],
        text=stored["text_scrubbed"],
        pii_kinds=list(stored.get("pii_kinds", [])),
        intent=stored.get("intent_label"),
    )
    store.publish(session_id, {"type": "comment", "data": out.model_dump(mode="json")})
    return out


@router.get("/sessions/{session_id}/comments", response_model=list[CommentOut])
def list_comments(session_id: str, store: StoreDep) -> list[CommentOut]:
    service.require_session(store, session_id)
    return [
        CommentOut(
            comment_id=c["comment_id"],
            session_id=session_id,
            block_id=c.get("block_id"),
            ts=c["ts"],
            text=c["text_scrubbed"],
            pii_kinds=list(c.get("pii_kinds", [])),
            intent=c.get("intent_label"),
        )
        for c in store.list_comments(session_id)
    ]


@router.post("/sessions/{session_id}/ticks", response_model=TickOut)
def post_tick(session_id: str, body: TickIn, store: StoreDep) -> TickOut:
    session = service.require_session(store, session_id)
    now = service.now_utc()
    # snap to the 30s bucket grid, aligned to session start when live
    start = session.get("start_ts")
    if start is not None:
        offset = (now - start).total_seconds()
        bucket = start + timedelta(seconds=int(offset // TICK_S) * TICK_S)
    else:
        bucket = now.replace(second=(now.second // TICK_S) * TICK_S, microsecond=0)

    pinned = service.current_pinned_product_id(store.list_interventions(session_id))
    row = {
        "ts_bucket": bucket,
        "viewers": body.viewers,
        "comment_rate": body.comment_rate,
        "like_rate": body.like_rate,
        "click_count": 0,
        "pinned_product_id": pinned,
    }
    stored = store.add_tick(session_id, row)
    out = TickOut(session_id=session_id, **{k: stored[k] for k in row})
    store.publish(session_id, {"type": "tick", "data": out.model_dump(mode="json")})
    return out


@router.get("/sessions/{session_id}/ticks", response_model=list[TickOut])
def list_ticks(session_id: str, store: StoreDep) -> list[TickOut]:
    service.require_session(store, session_id)
    return [TickOut(**{**t, "session_id": session_id}) for t in store.list_ticks(session_id)]
