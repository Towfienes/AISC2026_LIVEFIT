"""Shared route helpers: store access, server clock, session lookups, block
attribution, and schedule/start orchestration.

This module is a thin I/O-edge layer (HARNESS.md §1): all decision logic
(assignment, candidate choice, estimation) lives in ``livelift.core`` and
``livelift.analysis`` — nothing here draws randomness or computes statistics.

Timestamps: :func:`now_utc` is the single authoritative server clock (hard
rule 7 — UTC ``timestamptz`` everywhere, no naive datetimes).
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, fields
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request

from livelift.api.store import Store
from livelift.core.assigner import Block, DesignParams, Schedule, design_hash, generate_schedule


class ScheduleMissingError(RuntimeError):
    """Raised when a session is asked to go live without a persisted schedule
    (hard rule 4: no schedule, no broadcast)."""


def get_store(request: Request) -> Store:
    """FastAPI dependency: the app-wide store built at startup."""
    return request.app.state.store


StoreDep = Annotated[Store, Depends(get_store)]


def now_utc() -> datetime:
    """Server-side authoritative clock — always timezone-aware UTC."""
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


def require_session(store: Store, session_id: str) -> dict[str, Any]:
    """Fetch a session or 404.

    The id is validated as a UUID first: passing a malformed id straight to
    Postgres raised InvalidTextRepresentation and surfaced as a 500 with an ASGI
    traceback (incident 27/08). A typo in a URL is a client mistake, not a
    server fault — it gets the same Vietnamese 404 as a well-formed id that
    does not exist. Every session-scoped route goes through here, so fixing it
    once covers all of them.
    """
    try:
        uuid.UUID(str(session_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(  # noqa: B904 — the cause adds nothing for the client
            status_code=404, detail="Không tìm thấy phiên live (mã phiên không hợp lệ)"
        ) from None
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên live")
    return session


def elapsed_seconds(session: dict[str, Any], now: datetime) -> float:
    """Seconds since the session went live (0 before start; frozen at end_ts
    for ended sessions)."""
    start = session.get("start_ts")
    if start is None:
        return 0.0
    end = session.get("end_ts")
    ref = end if session.get("status") == "ended" and end is not None else now
    return max(0.0, (ref - start).total_seconds())


def block_at_offset(blocks: list[dict[str, Any]], offset_s: float) -> dict[str, Any] | None:
    """The block (washout included) whose [start, end) window contains the
    offset, or None outside every block."""
    for block in blocks:
        if block["start_offset_s"] <= offset_s < block["end_offset_s"]:
            return block
    return None


def current_pinned_product_id(interventions: list[dict[str, Any]]) -> str | None:
    """Replay the intervention log (already ts-ordered) to the current pin."""
    pinned: str | None = None
    for row in interventions:
        if not row.get("executed", True):
            continue
        if row.get("action_type") == "pin" and row.get("product_id"):
            pinned = row["product_id"]
        elif row.get("action_type") == "unpin":
            pinned = None
    return pinned


def schedule_session(
    store: Store,
    session: dict[str, Any],
    params: DesignParams,
    seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate + persist the pre-session schedule and its design json.

    Returns (updated session, stored block rows). The design (params + seed +
    draw diagnostics) is persisted alongside the blocks so the schedule can be
    reproduced and audited (hard rule 4 / HARNESS §6 seed discipline).

    Two artifacts are written here and nowhere else (gói Q3):

    * ``design_hash`` — the SHA-256 commitment over (params, seed). It goes in
      the design json, is returned by ``POST /schedule``, and is shown on the
      desk, so the design that will run is published BEFORE broadcast.
    * ``assignment_event`` rows — the ENTIRE schedule materialized once, at
      draw time, into the append-only table. ``experiment_block`` is mutable
      (override_count, compliance_rate, excluded_reason); these rows are not,
      which is what lets a reader prove afterwards that the assignments were
      not touched mid-session. A redraw (allowed while planned/scheduled)
      appends a second set under its own hash rather than replacing the first.
    """
    schedule = generate_schedule(session["planned_duration_min"], params, seed)
    blocks = store.save_schedule(session["session_id"], schedule.to_rows())
    d_hash = design_hash(params, schedule.seed)
    drawn_at = now_utc()
    store.add_assignment_events(
        session["session_id"],
        [
            {
                "block_idx": row["block_index"],
                "assignment": row["assignment"],
                "block_start_s": row["start_offset_s"],
                "block_end_s": row["end_offset_s"],
                "design_hash": d_hash,
                "created_at": drawn_at,
            }
            for row in schedule.to_rows()
        ],
    )
    design = {
        "params": asdict(params),
        "seed": schedule.seed,
        "design_hash": d_hash,
        "n_redraws": schedule.n_redraws,
        "n_on": schedule.n_on,
        "n_off": schedule.n_off,
        "realized_min_per_arm_per_phase": schedule.realized_min_per_arm_per_phase,
        "realized_transition_pairs": schedule.realized_transition_pairs,
        # The schedule VERBATIM as drawn before broadcast. This is the
        # pre-registration audit trail: the post-session QC gate compares it
        # against the blocks that actually ran, and a judge can verify the
        # randomization was not touched mid-session. Omitting it made
        # block_integrity unpassable for any API-created session (incident
        # 27/08).
        "blocks": schedule.to_rows(),
    }
    updated = store.update_session(session["session_id"], {"status": "scheduled", "design": design})
    return updated, blocks


def start_session(store: Store, session: dict[str, Any], start_ts: datetime) -> dict[str, Any]:
    """Set the session live and materialize block wall-clock times.

    Hard rule 4: refuses to start when no persisted schedule exists.
    """
    session_id = session["session_id"]
    if not store.get_blocks(session_id):
        raise ScheduleMissingError(session_id)
    updated = store.update_session(session_id, {"status": "live", "start_ts": start_ts})
    store.materialize_block_times(session_id, start_ts)
    return updated


def is_analysis_only(session: dict[str, Any]) -> bool:
    """True for an observational analysis of someone else's finished video.

    Such a session has no assignment schedule and never will (you cannot
    randomize the past), so no experiment quantity may be displayed for it and
    no action may be offered on it. The flag lives in ``design`` because that
    is what :func:`livelift.api.routes.replays` persists; this is the ONE
    reader, so route modules never re-spell the lookup and drift apart.
    """
    return bool((session.get("design") or {}).get("analysis_only"))


def session_design_hash(session: dict[str, Any]) -> str | None:
    """The commitment hash of the design this session is scheduled under.

    ``None`` for sessions scheduled before gói Q3 (and for replay/observational
    sessions that never had a schedule) — the honest answer is "no commitment
    was published", never a hash recomputed after the fact, which would prove
    nothing about what actually ran.
    """
    return (session.get("design") or {}).get("design_hash")


def rebuild_design_params(session: dict[str, Any]) -> DesignParams:
    """The :class:`DesignParams` persisted in the session's design json.

    Unknown keys are dropped (schema evolution), missing ones fall back to the
    dataclass defaults. Randomization inference MUST redraw with these — the
    session's own p / rerandomization constraint — not with the defaults, or
    the reference distribution belongs to a design nobody ran.

    Exception to the default-fallback rule (08/09): a design json persisted
    BEFORE the transition-balance constraint existed carries no
    ``min_transition_pairs`` key — that session RAN without the constraint, so
    the honest reconstruction is 0 (off), not today's default of 3. Falling
    back to 3 would redraw a design nobody ran."""
    design = session.get("design") or {}
    raw_params = design.get("params") or {}
    allowed = {f.name for f in fields(DesignParams)}
    kept = {k: v for k, v in raw_params.items() if k in allowed}
    if raw_params and "min_transition_pairs" not in raw_params:
        kept["min_transition_pairs"] = 0
    return DesignParams(**kept)


def rebuild_schedule(session: dict[str, Any], blocks: list[dict[str, Any]]) -> Schedule:
    """Reconstruct the core :class:`Schedule` from persisted design + blocks,
    for analysis (``block_frame``) over stored data."""
    design = session.get("design") or {}
    params = rebuild_design_params(session)
    block_objs = tuple(
        Block(
            index=b["block_index"],
            phase=b["phase"],
            start_offset_s=b["start_offset_s"],
            end_offset_s=b["end_offset_s"],
            is_washout=bool(b["is_washout"]),
            assignment=b["assignment"],
            propensity=b["propensity"],
        )
        for b in sorted(blocks, key=lambda r: r["block_index"])
    )
    return Schedule(
        session_duration_min=session["planned_duration_min"],
        params=params,
        seed=int(design.get("seed", 0)),
        n_redraws=int(design.get("n_redraws", 0)),
        blocks=block_objs,
    )
