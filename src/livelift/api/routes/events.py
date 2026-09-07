"""Event ingestion: comments (scrub-first, hard rule 1) and ticks.

Timestamps: when the client sends the platform timestamp (``ts_utc``) it is
authoritative for the event — block attribution near a boundary must follow
when the comment happened on-platform, not when the POST arrived (a runner
retry or spool replay can be minutes late). Without ``ts_utc`` the server
clock stamps the row, as before.

Idempotency: (platform, ext_id) is the dedup key — both store backends return
the existing row instead of inserting a duplicate, so a runner restart or a
spool replay is safe. Duplicate deliveries are not re-published to WebSocket
subscribers.

Auth: when the INGEST_TOKEN setting is non-empty, both POST endpoints require
``Authorization: Bearer <token>``. Read endpoints stay open.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from livelift.api import service
from livelift.api.schemas import CommentIn, CommentOut, TickIn, TickOut
from livelift.api.service import StoreDep
from livelift.config import get_settings
from livelift.ingest.pii import scrub
from livelift.nlp.intent import classify_with_confidence

router = APIRouter()

TICK_S = 30


def require_ingest_auth(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Reject write requests without the bearer token when INGEST_TOKEN is set.

    Empty token (default) disables the check entirely — dev, demo, and tests
    keep working with no header.
    """
    token = get_settings().ingest_token
    if not token:
        return
    if authorization != f"Bearer {token}":
        raise HTTPException(
            status_code=401,
            detail=(
                "Thiếu hoặc sai token ingest — cần header 'Authorization: Bearer <INGEST_TOKEN>'"
            ),
        )


IngestAuth = Depends(require_ingest_auth)


@router.post(
    "/sessions/{session_id}/comments",
    response_model=CommentOut,
    dependencies=[IngestAuth],
)
def post_comment(session_id: str, body: CommentIn, store: StoreDep) -> CommentOut:
    """Store a comment. The raw text is scrubbed BEFORE any persistence or
    logging; only the scrubbed text exists beyond this function's locals.
    (Ingest already scrubs — running it again here is defense in depth and
    is idempotent.)"""
    session = service.require_session(store, session_id)
    now = service.now_utc()
    ts = body.ts_utc or now
    result = scrub(body.text)
    intent, intent_confidence = classify_with_confidence(result.text)

    block_id = None
    if session["status"] == "live":
        # Attribute by the EVENT time, not arrival time: a delayed delivery
        # near a block boundary must land in the block it happened in.
        elapsed = service.elapsed_seconds(session, ts)
        block = service.block_at_offset(store.get_blocks(session_id), elapsed)
        if block is not None:
            block_id = block["block_id"]

    row = {
        "comment_id": service.new_id(),
        "session_id": session_id,
        "block_id": block_id,
        "ts": ts,
        "platform": body.platform,
        "ext_id": body.ext_id,
        "text_scrubbed": result.text,
        "pii_kinds": sorted({m.kind for m in result.matches}),
        "intent_label": intent,
        "intent_confidence": intent_confidence,
        "sentiment": None,
    }
    stored = store.add_comment(session_id, row)
    # The store returns the EXISTING row for a (platform, ext_id) duplicate —
    # answer idempotently but do not broadcast the same comment twice.
    is_duplicate = stored["comment_id"] != row["comment_id"]
    out = CommentOut(
        comment_id=stored["comment_id"],
        session_id=session_id,
        block_id=stored.get("block_id"),
        ts=stored["ts"],
        text=stored["text_scrubbed"],
        pii_kinds=list(stored.get("pii_kinds", [])),
        intent=stored.get("intent_label"),
        intent_confidence=stored.get("intent_confidence"),
    )
    if not is_duplicate:
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
            intent_confidence=c.get("intent_confidence"),
        )
        for c in store.list_comments(session_id)
    ]


@router.post(
    "/sessions/{session_id}/ticks",
    response_model=TickOut,
    dependencies=[IngestAuth],
)
def post_tick(session_id: str, body: TickIn, store: StoreDep) -> TickOut:
    session = service.require_session(store, session_id)
    ts = body.ts_utc or service.now_utc()
    # snap to the 30s bucket grid, aligned to session start when live
    start = session.get("start_ts")
    if start is not None:
        offset = (ts - start).total_seconds()
        bucket = start + timedelta(seconds=int(offset // TICK_S) * TICK_S)
    else:
        bucket = ts.replace(second=(ts.second // TICK_S) * TICK_S, microsecond=0)

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
