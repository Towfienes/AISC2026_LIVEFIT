"""Event normalization: raw platform events → 30s ticks → block-level outcomes.

Two layers:

1. :func:`build_ticks` — collapse the event stream into fixed 30-second buckets
   (``session_tick`` rows). Viewer counts are snapshots carried forward;
   comments/likes/clicks are counts per bucket.

2. :func:`block_frame` — join ticks/clicks onto the experiment schedule and
   compute the block-level analysis dataset. The primary outcome is
   **exposure-weighted click rate**: clicks per 1000 viewer-seconds within the
   block's analysis window. The analysis window drops the first ``burn_in_s``
   seconds of each block (Hu & Wager, arXiv:2209.00197 — burn-in at analysis
   time instead of design washout). Pre-block covariates (viewers, comment
   rate in the trailing window before the block) are attached for variance
   reduction (CUPED/CUPAC-style).

Everything here is pure: no clocks, no I/O.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from livelift.core.assigner.outer import ON, Schedule

EventKind = Literal["comment", "like", "click", "viewer_count", "pin"]


@dataclass(frozen=True)
class Event:
    """A normalized session event. ``ts_offset_s`` is seconds from session start."""

    kind: EventKind
    ts_offset_s: float
    value: float = 1.0  # viewer_count: the count; others: unused
    product_id: str | None = None


@dataclass(frozen=True)
class Tick:
    bucket_start_s: int
    viewers: float
    comment_count: int
    like_count: int
    click_count: int
    pinned_product_id: str | None


def build_ticks(
    events: Iterable[Event],
    session_duration_s: int,
    tick_s: int = 30,
) -> list[Tick]:
    """Aggregate events into fixed buckets. Viewer count carries forward the
    last snapshot; the pinned product carries forward the last pin event.

    Buckets BEFORE the first viewer snapshot and AFTER the last one are not
    emitted: there is no measurement there, and forward-filling to the planned
    session end invented exposure for blocks that never aired (audit 30/08).
    """
    n_buckets = max(1, -(-session_duration_s // tick_s))  # ceil
    comments = [0] * n_buckets
    likes = [0] * n_buckets
    clicks = [0] * n_buckets
    viewer_snapshots: list[list[float]] = [[] for _ in range(n_buckets)]
    pins: list[tuple[float, str | None]] = []

    for ev in sorted(events, key=lambda e: e.ts_offset_s):
        if not 0 <= ev.ts_offset_s < session_duration_s:
            continue
        b = int(ev.ts_offset_s // tick_s)
        if ev.kind == "comment":
            comments[b] += 1
        elif ev.kind == "like":
            likes[b] += 1
        elif ev.kind == "click":
            clicks[b] += 1
        elif ev.kind == "viewer_count":
            viewer_snapshots[b].append(ev.value)
        elif ev.kind == "pin":
            pins.append((ev.ts_offset_s, ev.product_id))

    # Only buckets covered by real viewer telemetry are measured.
    observed = [b for b, snaps in enumerate(viewer_snapshots) if snaps]
    first_obs = observed[0] if observed else None
    last_obs = observed[-1] if observed else None

    ticks: list[Tick] = []
    last_viewers = 0.0
    pin_idx = 0
    current_pin: str | None = None
    for b in range(n_buckets):
        if first_obs is None or b < first_obs or b > last_obs:
            continue
        bucket_start = b * tick_s
        bucket_end = bucket_start + tick_s
        if viewer_snapshots[b]:
            last_viewers = sum(viewer_snapshots[b]) / len(viewer_snapshots[b])
        while pin_idx < len(pins) and pins[pin_idx][0] < bucket_end:
            current_pin = pins[pin_idx][1]
            pin_idx += 1
        ticks.append(
            Tick(
                bucket_start_s=bucket_start,
                viewers=last_viewers,
                comment_count=comments[b],
                like_count=likes[b],
                click_count=clicks[b],
                pinned_product_id=current_pin,
            )
        )
    return ticks


@dataclass(frozen=True)
class BlockRecord:
    """One analysis row: a measurement block with outcome and covariates."""

    block_index: int
    phase: str
    assignment: str  # ON / OFF
    z: int  # 1 if ON
    propensity: float
    start_offset_s: int
    end_offset_s: int
    exposure_viewer_s: float
    clicks: int
    y: float  # clicks per 1000 viewer-seconds in the analysis window
    pre_viewers: float  # mean viewers in the trailing pre-block window
    pre_comment_rate: float  # comments/min in the trailing pre-block window
    # Arousal proxy (S-O-R: sensory/social stimuli -> arousal -> impulsive
    # purchase; Nguyễn et al., IMCOM 2026): like tempo before the block. Used
    # ONLY as a pre-treatment covariate for variance reduction / heterogeneity
    # exploration — never as an outcome.
    pre_like_rate: float  # likes/min in the trailing pre-block window
    # Measurability. A block scheduled past the moment the host actually
    # stopped streaming, or one with no viewer telemetry, carries NO outcome —
    # it must be EXCLUDED, never entered as y = 0.0. Feeding fabricated zeros
    # into the estimator attenuated the effect by ~38% and dropped Fisher-CI
    # coverage to 72% (audit 30/08).
    measurable: bool = True
    exclude_reason: str | None = None


def _window_stats(
    events: list[Event], start_s: float, end_s: float, tick_viewers: list[tuple[float, float]]
) -> tuple[float, int, int, int]:
    """(viewer-seconds, clicks, comments, likes) within [start_s, end_s).

    ``tick_viewers`` is a list of (bucket_start_s, viewers) with bucket width
    inferred from consecutive entries; exposure integrates the carried-forward
    viewer count over the window.
    """
    clicks = sum(1 for e in events if e.kind == "click" and start_s <= e.ts_offset_s < end_s)
    comments = sum(1 for e in events if e.kind == "comment" and start_s <= e.ts_offset_s < end_s)
    likes = sum(1 for e in events if e.kind == "like" and start_s <= e.ts_offset_s < end_s)

    exposure = 0.0
    for i, (t0, viewers) in enumerate(tick_viewers):
        t1 = (
            tick_viewers[i + 1][0]
            if i + 1 < len(tick_viewers)
            else t0 + (tick_viewers[1][0] - tick_viewers[0][0] if len(tick_viewers) > 1 else 30.0)
        )
        lo, hi = max(t0, start_s), min(t1, end_s)
        if hi > lo:
            exposure += viewers * (hi - lo)
    return exposure, clicks, comments, likes


MIN_EXPOSURE_VIEWER_S = 60.0
"""Minimum viewer-seconds for a block to carry an outcome.

One viewer for one minute. Below this the click rate is dominated by counting
noise (a single click implies a rate of 1000+), so the block is excluded rather
than allowed to swing the unweighted mean. Pre-registered rule.
"""


def block_frame(
    schedule: Schedule,
    events: Iterable[Event],
    burn_in_s: int = 60,
    pre_window_s: int = 120,
    tick_s: int = 30,
    live_until_s: float | None = None,
) -> list[BlockRecord]:
    """Build the block-level analysis dataset from the schedule and events.

    ``burn_in_s`` seconds at the start of every measurement block are excluded
    from the outcome window (carryover burn-in).

    ``live_until_s`` is when the broadcast ACTUALLY ended, in seconds from
    start. Sessions routinely end before the planned duration, and the schedule
    keeps its planned blocks; without this bound those never-aired blocks were
    given fabricated exposure and a hard ``y = 0.0``, which attenuated the
    estimate by ~38% and dropped Fisher-CI coverage to 72% (audit 30/08).
    Blocks that did not air — or whose measured window carries less than
    ``MIN_EXPOSURE_VIEWER_S`` of exposure — come back with ``measurable=False``
    and MUST be dropped before estimation.
    """
    ev_list = sorted(events, key=lambda e: e.ts_offset_s)
    session_s = schedule.session_duration_min * 60
    horizon = session_s if live_until_s is None else min(session_s, max(live_until_s, 0.0))
    ticks = build_ticks(ev_list, session_s, tick_s)
    tick_viewers = [(float(t.bucket_start_s), t.viewers) for t in ticks]

    records: list[BlockRecord] = []
    for b in schedule.measurement_blocks:
        win_start = b.start_offset_s + min(burn_in_s, max(b.duration_s - 30, 0))
        # Clip the outcome window to the real broadcast span.
        win_end = min(float(b.end_offset_s), horizon)
        unmeasurable: str | None = None
        if win_end <= win_start:
            unmeasurable = "khối không phát sóng (phiên kết thúc trước khối này)"
        exposure, clicks, _, _ = _window_stats(ev_list, win_start, win_end, tick_viewers)
        if unmeasurable is None and exposure < MIN_EXPOSURE_VIEWER_S:
            unmeasurable = (
                f"phơi nhiễm {exposure:.0f} giây·người xem < ngưỡng "
                f"{MIN_EXPOSURE_VIEWER_S:.0f} — tỷ lệ nhấp không đo được"
            )
        pre_start = max(0.0, b.start_offset_s - pre_window_s)
        pre_exp, _, pre_comments, pre_likes = _window_stats(
            ev_list, pre_start, b.start_offset_s, tick_viewers
        )
        pre_seconds = max(b.start_offset_s - pre_start, 1e-9)
        assert b.assignment is not None
        assert b.propensity is not None
        records.append(
            BlockRecord(
                block_index=b.index,
                phase=b.phase,
                assignment=b.assignment,
                z=1 if b.assignment == ON else 0,
                propensity=b.propensity,
                start_offset_s=b.start_offset_s,
                end_offset_s=b.end_offset_s,
                exposure_viewer_s=exposure,
                clicks=clicks,
                y=(clicks / exposure * 1000.0) if exposure > 0 else 0.0,
                measurable=unmeasurable is None,
                exclude_reason=unmeasurable,
                pre_viewers=pre_exp / pre_seconds,
                pre_comment_rate=pre_comments / (pre_seconds / 60.0),
                pre_like_rate=pre_likes / (pre_seconds / 60.0),
            )
        )
    return records


def blocks_to_dicts(records: list[BlockRecord]) -> list[dict]:
    return [
        {
            "block_index": r.block_index,
            "phase": r.phase,
            "assignment": r.assignment,
            "z": r.z,
            "propensity": r.propensity,
            "exposure_viewer_s": r.exposure_viewer_s,
            "clicks": r.clicks,
            "y": r.y,
            "pre_viewers": r.pre_viewers,
            "pre_comment_rate": r.pre_comment_rate,
            "pre_like_rate": r.pre_like_rate,
            "measurable": r.measurable,
            "exclude_reason": r.exclude_reason,
        }
        for r in records
    ]
