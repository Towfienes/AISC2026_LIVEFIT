"""Khoảnh khắc nổi bật: comment-rate spikes on a session timeline. Pure.

The post-session report marks "moments" the way Feigua's replay timeline does:
minutes where the chat tempo jumps far above its own recent baseline, so the
operator can scrub the recording to that spot and see what was being said /
pinned. The detector is deliberately dumb and honest:

- baseline = MEDIAN of the previous ``window`` buckets (median, not mean — one
  earlier spike must not inflate the baseline and mask the next one);
- a bucket qualifies when rate >= ``min_ratio`` x baseline AND
  rate >= ``min_rate`` (absolute floor: on a quiet stream 0 -> 2 messages/min
  doubles the baseline yet means nothing);
- consecutive qualifying buckets merge into ONE moment at their peak bucket
  (a 90-second surge is one moment, not three);
- a series shorter than ``window`` + 1 yields NO moments — too little history
  to claim a baseline. The caller must SAY the series was too short (signal
  matrix philosophy: declare the gap, never infer from a short series).

No I/O, no clock, no randomness.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median

#: Default rolling-baseline length: 10 buckets of 30 s = 5 minutes of history.
DEFAULT_WINDOW = 10
#: A spike must at least double its baseline...
DEFAULT_MIN_RATIO = 2.0
#: ...and reach an absolute tempo (messages/min) worth a human's attention.
DEFAULT_MIN_RATE = 6.0


@dataclass(frozen=True)
class Moment:
    """One detected spike, at the peak bucket of its surge."""

    offset_s: float  # bucket start, seconds from session start
    rate: float  # comment rate at the peak (per minute)
    baseline: float  # rolling median of the prior window at the peak
    ratio: float | None  # rate / baseline; None when the baseline is 0


def detect_comment_spikes(
    buckets: Sequence[tuple[float, float]],
    *,
    window: int = DEFAULT_WINDOW,
    min_ratio: float = DEFAULT_MIN_RATIO,
    min_rate: float = DEFAULT_MIN_RATE,
    top_k: int = 3,
) -> list[Moment]:
    """Find up to ``top_k`` comment-rate spikes in ``(offset_s, rate)`` buckets.

    Returns moments sorted by rate, highest first. Input order does not matter
    (buckets are sorted by offset internally). An empty result means either no
    spike OR not enough history — the caller distinguishes the two via
    ``len(buckets) <= window`` and must declare the latter.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    if top_k <= 0:
        return []
    rows = sorted(buckets, key=lambda b: b[0])
    if len(rows) <= window:
        return []  # not enough history for any baseline — declared by caller

    qualifying: list[Moment] = []
    for i in range(window, len(rows)):
        offset_s, rate = rows[i]
        baseline = float(median(r for _o, r in rows[i - window : i]))
        if rate < min_rate:
            continue
        if baseline > 0 and rate < min_ratio * baseline:
            continue
        # baseline == 0: a burst out of silence that clears min_rate qualifies.
        qualifying.append(
            Moment(
                offset_s=float(offset_s),
                rate=float(rate),
                baseline=baseline,
                ratio=(float(rate) / baseline) if baseline > 0 else None,
            )
        )

    # Merge consecutive qualifying buckets into one moment at the peak. The
    # run is tracked by its LAST bucket offset (not the peak's): a surge whose
    # peak comes first must still absorb its trailing buckets.
    merged: list[Moment] = []
    run_last_offset: float | None = None
    bucket_step = _min_step(rows)
    for m in qualifying:
        adjacent = (
            merged
            and bucket_step is not None
            and run_last_offset is not None
            and m.offset_s - run_last_offset <= bucket_step
        )
        if adjacent:
            if m.rate > merged[-1].rate:
                merged[-1] = m
        else:
            merged.append(m)
        run_last_offset = m.offset_s

    merged.sort(key=lambda m: m.rate, reverse=True)
    return merged[:top_k]


def _min_step(rows: Sequence[tuple[float, float]]) -> float | None:
    """Smallest positive gap between consecutive bucket offsets (the grid)."""
    steps = [b[0] - a[0] for a, b in zip(rows, rows[1:], strict=False) if b[0] > a[0]]
    return min(steps) if steps else None
