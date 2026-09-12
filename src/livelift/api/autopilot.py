"""Bộ thực thi tự động — server-side executor for ``mode='auto'`` sessions.

Before 12/09 ``mode='auto'`` was a label and nothing else: the schedule was
drawn, the session went live, every ON block came and went, and no process ever
called ``POST /sessions/{id}/actions/execute``. Compliance came out 0.0,
``diff_in_means`` came out null, and every endpoint answered 200 without a
single warning (kiểm chứng vận hành 11/09, §2.2b). An experiment with an
un-treated treatment arm is not a weak experiment — it is no experiment, and
the platform must not stay quiet about it.

What this module does, and deliberately does not do:

* **ON block → pin, through the production path.** It calls
  :func:`livelift.api.routes.actions.execute_action` — the same function the
  desk calls — so the inner-tier randomization, the logged
  ``inner_propensity``, the ``candidates_json`` audit trail, the
  ``intervention_log`` row and the ``exposure_event`` row are all produced by
  one code path. There is no second pin implementation to drift.
* **OFF block → hands off.** Not "auto-unpin": ``execute_action`` refuses to
  act in an OFF block by design ("đội vận hành làm theo cách thường lệ — hệ
  thống không can thiệp để bảo toàn nhánh đối chứng"), and the only other
  write path, ``actions/override``, demands one of three human safety reasons.
  A robot claiming "hết hàng" to unpin would be a false audit record. The
  consequence is stated plainly rather than hidden: a pin placed in an ON
  block stays on screen until the next human action, so the OFF arm is
  "no system intervention", not "nothing pinned". Changing that needs a new
  pre-registered action type, not a background task inventing one.
* **Idempotent across restarts.** A block counts as handled when ANY
  ``exposure_event`` row carries its ``block_idx`` — model or human. Restarting
  the API mid-session therefore never double-pins a block that already has an
  exposure, and never skips the ON block currently on air if it has none.
* **Never races a human.** The same rule respects manual work: if the operator
  pinned or unpinned inside this block, the block has an exposure row and the
  autopilot leaves it alone for the rest of the block.
* **Never repairs the past.** An ON block that already ended without an
  exposure cannot be fixed by pinning now — that pin would land in the block
  currently on air and be attributed there. Those blocks are counted and
  reported (``missed_on_blocks``) instead of being silently papered over.

Alarm (``LIVELIFT_AUTOPILOT_SILENCE_MIN``): a live auto session that has run
past the threshold with zero system pins raises a Vietnamese alarm on
``GET /sessions/{id}/state``. The alarm is computed from the STORE, not from
this task's heartbeat, so it fires even when the executor is switched off or
never started — the silent-zero-compliance failure must be loud no matter why
it happened.

Known limitation — one process only. The loop lives inside the API process.
Run the API with a single worker (the project's docker/compose setup does).
With several uvicorn workers each process would run its own loop; the
exposure-row check makes a duplicate pin unlikely but not impossible, because
two workers can read "no exposure yet" in the same instant. The simple, honest
deployment rule is therefore: one worker, or ``LIVELIFT_AUTOPILOT=0`` on every
worker but one. A proper fix (an advisory lock in Postgres, or a separate
single-instance runner process) is out of this package's scope and is recorded
as a follow-up.

Configuration (environment variables, read here rather than in
``livelift.config`` only because that module is owned by another package in
flight — they belong there):

===============================  =========  =================================
``LIVELIFT_AUTOPILOT``           ``1``      ``0``/``false``/``no``/``off`` turns
                                            the executor off entirely.
``LIVELIFT_AUTOPILOT_TICK_S``    ``5``      Seconds between sweeps.
``LIVELIFT_AUTOPILOT_SILENCE_MIN`` ``5``    Minutes of a live auto session with
                                            zero system pins before the alarm.
===============================  =========  =================================
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from livelift.api import service
from livelift.api.store import Store

logger = logging.getLogger("livelift.autopilot")

DEFAULT_TICK_S = 5.0
DEFAULT_SILENCE_MIN = 5.0

_FALSEY = {"0", "false", "no", "off", ""}


def is_enabled() -> bool:
    """Whether the executor runs at all (default: yes, for auto sessions)."""
    return os.environ.get("LIVELIFT_AUTOPILOT", "1").strip().lower() not in _FALSEY


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning(
            "Biến môi trường %s = %r không phải số — dùng mặc định %s", name, raw, default
        )
        return default
    if value <= 0:
        logger.warning("Biến môi trường %s = %r phải > 0 — dùng mặc định %s", name, raw, default)
        return default
    return value


def tick_seconds() -> float:
    return _positive_float("LIVELIFT_AUTOPILOT_TICK_S", DEFAULT_TICK_S)


def silence_alarm_after_s() -> float:
    return _positive_float("LIVELIFT_AUTOPILOT_SILENCE_MIN", DEFAULT_SILENCE_MIN) * 60.0


# ---------------------------------------------------------------------------
# Heartbeat — so an operator can SEE the thing is running
# ---------------------------------------------------------------------------


@dataclass
class Heartbeat:
    """Per-session evidence that the executor is alive and what it has done."""

    last_run_ts: datetime | None = None
    actions_taken: int = 0
    last_action_ts: datetime | None = None
    last_error: str | None = None
    log: list[str] = field(default_factory=list)


_HEARTBEATS: dict[str, Heartbeat] = {}


def heartbeat(session_id: str) -> Heartbeat:
    return _HEARTBEATS.setdefault(session_id, Heartbeat())


def reset_heartbeats() -> None:
    """Drop all heartbeat state (tests; process restart semantics)."""
    _HEARTBEATS.clear()


LOG_KEEP = 50
"""Heartbeat log lines kept per session — a ring, not a growing list: a session
whose pins keep being refused would otherwise add a line per sweep forever."""


def _remember(hb: Heartbeat, message: str) -> None:
    hb.log.append(message)
    del hb.log[:-LOG_KEEP]


# ---------------------------------------------------------------------------
# Pure decision layer — no clock of its own, no I/O, fully testable
# ---------------------------------------------------------------------------


def handled_block_indices(exposure_events: list[dict[str, Any]]) -> set[int]:
    """Block indices that already carry an exposure — model OR human.

    One rule serves both requirements: idempotency after a restart (a block
    the executor already pinned is never pinned twice) and not racing the
    desk (a block a human just touched is left to the human).
    """
    handled: set[int] = set()
    for event in exposure_events:
        idx = event.get("block_idx")
        if idx is not None:
            handled.add(int(idx))
    return handled


def _measurement_on_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [b for b in blocks if b.get("assignment") == "ON" and not b.get("is_washout")]


def pending_on_block(
    blocks: list[dict[str, Any]],
    exposure_events: list[dict[str, Any]],
    elapsed_s: float,
) -> dict[str, Any] | None:
    """The ON block on air right now that still has no exposure, if any.

    Only the CURRENT block is eligible: pinning "for" a block that already
    ended would be recorded against the block on air instead, i.e. a false
    exposure record in the table compliance is derived from.
    """
    current = service.block_at_offset(blocks, elapsed_s)
    if current is None or current.get("is_washout") or current.get("assignment") != "ON":
        return None
    if int(current["block_index"]) in handled_block_indices(exposure_events):
        return None
    return current


def missed_on_blocks(
    blocks: list[dict[str, Any]],
    exposure_events: list[dict[str, Any]],
    elapsed_s: float,
) -> list[int]:
    """ON blocks that ended with no exposure at all — unrepairable, so named."""
    handled = handled_block_indices(exposure_events)
    return [
        int(b["block_index"])
        for b in _measurement_on_blocks(blocks)
        if b["end_offset_s"] <= elapsed_s and int(b["block_index"]) not in handled
    ]


def _system_pin_count(exposure_events: list[dict[str, Any]]) -> int:
    return sum(
        1 for e in exposure_events if e.get("event_type") == "pin" and e.get("source") == "model"
    )


def silence_alarm(
    session: dict[str, Any],
    blocks: list[dict[str, Any]],
    exposure_events: list[dict[str, Any]],
    elapsed_s: float,
    threshold_s: float | None = None,
) -> str | None:
    """Vietnamese alarm when an auto session is producing no treatment at all.

    Derived from stored facts, never from the executor's own heartbeat: a
    session whose executor never started is exactly the case that must scream.
    Returns ``None`` when there is nothing wrong.
    """
    if session.get("mode") != "auto" or session.get("status") != "live":
        return None
    on_blocks = _measurement_on_blocks(blocks)
    if not on_blocks:
        return None
    threshold = silence_alarm_after_s() if threshold_s is None else threshold_s

    missed = missed_on_blocks(blocks, exposure_events, elapsed_s)
    pins = _system_pin_count(exposure_events)
    parts: list[str] = []
    if pins == 0 and elapsed_s >= threshold:
        parts.append(
            f"BÁO ĐỘNG: phiên đang phát ở chế độ TỰ ĐỘNG nhưng sau "
            f"{elapsed_s / 60:.1f} phút vẫn CHƯA CÓ hành động ghim nào. Nhánh BẬT "
            f"chưa hề được can thiệp — tuân thủ = 0 và thí nghiệm sẽ không ước "
            f"lượng được gì. Kiểm tra bộ thực thi tự động (biến môi trường "
            f"LIVELIFT_AUTOPILOT) hoặc ghim tay ngay."
        )
    if missed:
        danh_sach = ", ".join(str(i) for i in missed)
        parts.append(
            f"BÁO ĐỘNG: {len(missed)} khối BẬT đã trôi qua mà không có hành động nào "
            f"(khối {danh_sach}). Không ghim bù được — các khối này sẽ được tính là "
            f"KHÔNG tuân thủ trong báo cáo."
        )
    return " ".join(parts) if parts else None


@dataclass(frozen=True)
class AutopilotView:
    """What the control desk gets to see about the executor."""

    enabled: bool
    last_run_ts: datetime | None
    actions_taken: int
    on_blocks_total: int
    on_blocks_done: int
    missed_on_blocks: tuple[int, ...]
    last_error: str | None
    alarm: str | None


def view(
    session: dict[str, Any],
    blocks: list[dict[str, Any]],
    exposure_events: list[dict[str, Any]],
    elapsed_s: float,
) -> AutopilotView:
    """Operator-facing status. OPERATOR ONLY — it names block indices and
    would break host blinding (rule L6) if it ever reached HostState."""
    hb = _HEARTBEATS.get(str(session.get("session_id")), Heartbeat())
    on_blocks = _measurement_on_blocks(blocks)
    handled = handled_block_indices(exposure_events)
    return AutopilotView(
        enabled=is_enabled(),
        last_run_ts=hb.last_run_ts,
        actions_taken=hb.actions_taken,
        on_blocks_total=len(on_blocks),
        on_blocks_done=sum(1 for b in on_blocks if int(b["block_index"]) in handled),
        missed_on_blocks=tuple(missed_on_blocks(blocks, exposure_events, elapsed_s)),
        last_error=hb.last_error,
        alarm=silence_alarm(session, blocks, exposure_events, elapsed_s),
    )


# ---------------------------------------------------------------------------
# Execution layer — synchronous on purpose, so tests drive it with a fake clock
# ---------------------------------------------------------------------------


def auto_sessions(store: Store) -> list[dict[str, Any]]:
    """Live sessions in auto mode, in store order."""
    return [
        s for s in store.list_sessions() if s.get("status") == "live" and s.get("mode") == "auto"
    ]


def step_session(store: Store, session: dict[str, Any], now: datetime) -> str | None:
    """Do at most one pin for this session. Returns the Vietnamese log line.

    ``now`` is passed in (never read from the clock here) so the gate can walk
    a session across block boundaries without sleeping.
    """
    session_id = str(session["session_id"])
    hb = heartbeat(session_id)
    hb.last_run_ts = now

    elapsed = service.elapsed_seconds(session, now)
    blocks = store.get_blocks(session_id)
    exposures = store.list_exposure_events(session_id)
    block = pending_on_block(blocks, exposures, elapsed)
    if block is None:
        return None

    # Deliberately the production route function, not a private pin helper:
    # inner-tier propensity, candidate audit trail, intervention log and
    # exposure row must come from one implementation.
    from livelift.api.routes.actions import execute_action
    from livelift.api.schemas import ExecuteRequest

    try:
        result = execute_action(session_id, ExecuteRequest(), store)
    except HTTPException as exc:
        # 409 here is information, not a crash: "không có sản phẩm còn hàng để
        # ghim" is a real operational state the desk must be told about. The
        # block stays pending on purpose — stock can come back — so the same
        # refusal repeats every sweep and is logged only when it CHANGES,
        # otherwise a stuck session would fill the log at one line per tick.
        message = (
            f"Tự động ghim THẤT BẠI ở khối {block['block_index']} (BẬT) của phiên "
            f"{session_id}: {exc.detail}"
        )
        if hb.last_error != str(exc.detail):
            logger.warning(message)
            _remember(hb, message)
        hb.last_error = str(exc.detail)
        return message
    except Exception as exc:  # pragma: no cover - defensive: never kill the loop
        hb.last_error = repr(exc)
        logger.exception("Bộ thực thi tự động gặp lỗi không lường trước ở phiên %s", session_id)
        return None

    hb.last_error = None
    hb.actions_taken += 1
    hb.last_action_ts = now
    message = (
        f"Tự động ghim sản phẩm {result.product_id} ở khối {result.block_index} (BẬT) "
        f"của phiên {session_id}, propensity nội tầng {result.inner_propensity:.3f}, "
        f"{len(result.overlap_set)} sản phẩm trong tập chồng lấn."
    )
    logger.info(message)
    _remember(hb, message)
    store.publish(
        session_id,
        {
            "type": "autopilot",
            "data": {
                "block_index": result.block_index,
                "product_id": result.product_id,
                "actions_taken": hb.actions_taken,
                "message": message,
            },
        },
    )
    return message


def step_all(store: Store, now: datetime | None = None) -> list[str]:
    """One sweep over every live auto session. Returns the log lines produced."""
    moment = now if now is not None else service.now_utc()
    lines: list[str] = []
    for session in auto_sessions(store):
        line = step_session(store, session, moment)
        if line:
            lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


async def run_forever(store: Store, tick_s: float | None = None) -> None:
    interval = tick_seconds() if tick_s is None else tick_s
    logger.info("Bộ thực thi tự động đã bật — quét mỗi %.1f giây.", interval)
    try:
        while True:
            # Sleep BEFORE the first sweep, not after. Blocks are minutes long
            # so one tick of delay at boot costs nothing, and it keeps the
            # executor out of the first moments of every process that builds an
            # app — including test clients, which would otherwise get a
            # nondeterministic pin landing in the middle of their assertions.
            await asyncio.sleep(interval)
            try:
                # to_thread: the store may be Postgres, and a blocking query
                # must not stall the event loop serving the desk.
                await asyncio.to_thread(step_all, store)
            except Exception:  # pragma: no cover - the loop must never die
                logger.exception("Vòng quét của bộ thực thi tự động lỗi — vẫn tiếp tục chạy.")
    except asyncio.CancelledError:
        logger.info("Bộ thực thi tự động đã dừng.")
        raise


def start(store: Store) -> asyncio.Task[None] | None:
    """Start the sweep task, or return None when switched off."""
    if not is_enabled():
        logger.warning(
            "Bộ thực thi tự động ĐANG TẮT (LIVELIFT_AUTOPILOT=0): phiên ở chế độ auto "
            "sẽ KHÔNG được ghim tự động — phải ghim tay, nếu không tuân thủ = 0."
        )
        return None
    return asyncio.create_task(run_forever(store))


async def stop(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
