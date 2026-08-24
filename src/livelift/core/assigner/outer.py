"""Outer-tier randomization: switchback schedule generator.

Design decisions (docs/research/2026-08-24-switchback-design.md, synthesis §3.1):

- **Block length**: standardized (default 5 min); the FIRST and LAST measurement
  blocks are doubled (~10 min) per the optimal-design prescription of Bojinov,
  Simchi-Levi & Zhao (Management Science 69(7), 2023, arXiv:2009.00148) — the
  endpoints of a switchback carry asymmetric carryover exposure.
- **No design washout by default** (``washout_min=0``): following Hu & Wager
  (JBES, arXiv:2209.00197) we log everything and drop a *burn-in* window at
  ANALYSIS time (sensitivity over b ∈ {0..3} min) instead of discarding
  broadcast minutes irrevocably. ``washout_min > 0`` is still supported for the
  pre-registered sensitivity comparison.
- **Assignment**: i.i.d. Bernoulli(p=0.5) per block, with **rerandomization**:
  redraw the whole sequence until every session phase (early/mid/late) has at
  least ``min_per_arm_per_phase`` blocks of each arm (Ni, Kalfountzou & Bojinov,
  HBS WP 26-012). The acceptance rule is symmetric in the arms, so the marginal
  propensity remains exactly p for every block — recorded as such.
- **Boundary jitter**: interior block boundaries are shifted by ±``jitter_s``
  seconds so switches never sync with the show's script rhythm (Xiong, Chin &
  Taylor, arXiv:2406.06768).
- The whole schedule is a deterministic function of ``seed`` and is generated
  and persisted BEFORE the session goes live — never during broadcast.

Randomization inference MUST redraw assignments with the very same production
function (:func:`draw_assignments`), not an ad-hoc shuffle — see
:mod:`livelift.analysis.estimators`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

PHASES = ("early", "mid", "late")

ON = "ON"
OFF = "OFF"


@dataclass(frozen=True)
class DesignParams:
    """Pre-registered design parameters for a session's schedule."""

    block_min: int = 5
    washout_min: int = 0
    endpoint_double: bool = True
    jitter_s: int = 30
    p: float = 0.5
    min_per_arm_per_phase: int = 2
    max_redraws: int = 10_000

    def __post_init__(self) -> None:
        if self.block_min <= 0:
            raise ValueError("block_min must be > 0")
        if self.washout_min < 0 or self.jitter_s < 0:
            raise ValueError("washout_min and jitter_s must be >= 0")
        if not 0.0 < self.p < 1.0:
            raise ValueError("p must be in (0, 1)")


@dataclass(frozen=True)
class Block:
    """One interval of the session timeline.

    Offsets are seconds from session start. ``assignment`` is ``None`` for
    washout intervals (excluded from analysis by design when washout_min > 0).
    """

    index: int
    phase: str
    start_offset_s: int
    end_offset_s: int
    is_washout: bool
    assignment: str | None
    propensity: float | None

    @property
    def duration_s(self) -> int:
        return self.end_offset_s - self.start_offset_s


@dataclass(frozen=True)
class Schedule:
    session_duration_min: int
    params: DesignParams
    seed: int
    n_redraws: int
    blocks: tuple[Block, ...] = field(default_factory=tuple)

    @property
    def measurement_blocks(self) -> tuple[Block, ...]:
        return tuple(b for b in self.blocks if not b.is_washout)

    @property
    def n_on(self) -> int:
        return sum(1 for b in self.measurement_blocks if b.assignment == ON)

    @property
    def n_off(self) -> int:
        return sum(1 for b in self.measurement_blocks if b.assignment == OFF)

    def to_rows(self) -> list[dict]:
        """Rows ready for insertion into ``experiment_block``."""
        return [
            {
                "block_index": b.index,
                "phase": b.phase,
                "start_offset_s": b.start_offset_s,
                "end_offset_s": b.end_offset_s,
                "is_washout": b.is_washout,
                "assignment": b.assignment,
                "propensity": b.propensity,
            }
            for b in self.blocks
        ]


def _block_lengths_min(duration_min: int, params: DesignParams) -> list[int]:
    """Nominal measurement-block lengths covering the session.

    With endpoint doubling the layout is [2L, L, ..., L, 2L]; washouts (if any)
    sit between consecutive measurement blocks. Trailing time too short for a
    full block stays unscheduled — no partial blocks (unequal exposure would
    distort the block-level outcome).
    """
    length, washout = params.block_min, params.washout_min
    if duration_min < length:
        raise ValueError("session shorter than one block")

    if params.endpoint_double:
        # total(n) = 4L + (n-2)L + (n-1)w  for n >= 2 doubled-endpoint layout
        n = (duration_min - 2 * length + washout) // (length + washout) if (
            length + washout
        ) else 0
        if n >= 4:
            return [2 * length] + [length] * (n - 2) + [2 * length]
        # too short for a doubled-endpoint layout — fall through to uniform

    n = 1 + (duration_min - length) // (length + washout) if (length + washout) else 1
    return [length] * max(n, 1)


def _phase_of(midpoint_s: float, session_s: float) -> str:
    """Phase = which third of the session the block's midpoint falls into."""
    idx = min(int(midpoint_s / session_s * len(PHASES)), len(PHASES) - 1)
    return PHASES[idx]


def draw_assignments(
    phases: list[str],
    rng: random.Random,
    p: float = 0.5,
    min_per_arm_per_phase: int = 2,
    max_redraws: int = 10_000,
) -> tuple[list[str], int]:
    """The production assignment mechanism: i.i.d. Bernoulli(p) with symmetric
    rerandomization.

    Redraws until each phase stratum contains at least ``min_per_arm_per_phase``
    blocks of each arm — capped at what the stratum size can possibly hold, so
    small strata degrade gracefully instead of looping forever. Returns the
    accepted assignment vector and the number of redraws used.

    This function is the single source of truth for the assignment
    distribution: `generate_schedule` uses it to assign, and the randomization
    test re-draws from it to build the reference distribution.
    """
    strata: dict[str, list[int]] = {}
    for i, ph in enumerate(phases):
        strata.setdefault(ph, []).append(i)
    required = {ph: min(min_per_arm_per_phase, len(idx) // 2) for ph, idx in strata.items()}

    for redraw in range(max_redraws):
        arms = [ON if rng.random() < p else OFF for _ in phases]
        ok = True
        for ph, idx in strata.items():
            n_on = sum(1 for i in idx if arms[i] == ON)
            if n_on < required[ph] or (len(idx) - n_on) < required[ph]:
                ok = False
                break
        if ok:
            return arms, redraw
    raise RuntimeError(
        f"rerandomization failed to satisfy constraints in {max_redraws} draws"
    )


def generate_schedule(
    session_duration_min: int,
    params: DesignParams | None = None,
    seed: int = 0,
) -> Schedule:
    """Generate the full pre-session switchback schedule (pure, seed-determined)."""
    params = params or DesignParams()
    rng = random.Random(seed)

    lengths = _block_lengths_min(session_duration_min, params)
    n_meas = len(lengths)
    washout_s = params.washout_min * 60
    session_s = session_duration_min * 60

    # Nominal boundaries, then jitter interior measurement-block boundaries.
    starts: list[int] = []
    cursor = 0
    for m, length in enumerate(lengths):
        if m > 0:
            cursor += washout_s
        starts.append(cursor)
        cursor += length * 60
    total_s = cursor

    offsets = [0] * (n_meas + 1)  # jitter per interior boundary
    if params.jitter_s > 0 and n_meas > 1:
        max_shift = min(params.jitter_s, (params.block_min * 60) // 3)
        for j in range(1, n_meas):
            offsets[j] = rng.randint(-max_shift, max_shift)

    # Phases from nominal (pre-jitter) midpoints — stable strata definitions.
    phases = [
        _phase_of(starts[m] + lengths[m] * 30, total_s) for m in range(n_meas)
    ]

    arms, n_redraws = draw_assignments(
        phases, rng, params.p, params.min_per_arm_per_phase, params.max_redraws
    )

    blocks: list[Block] = []
    out_index = 0
    for m in range(n_meas):
        start = starts[m] + offsets[m]
        end = starts[m] + lengths[m] * 60 + offsets[m + 1]
        if m > 0 and washout_s > 0:
            w_start = starts[m] - washout_s + offsets[m]
            blocks.append(
                Block(
                    index=out_index,
                    phase=phases[m],
                    start_offset_s=w_start,
                    end_offset_s=start,
                    is_washout=True,
                    assignment=None,
                    propensity=None,
                )
            )
            out_index += 1
        blocks.append(
            Block(
                index=out_index,
                phase=phases[m],
                start_offset_s=start,
                end_offset_s=min(end, session_s),
                is_washout=False,
                assignment=arms[m],
                propensity=params.p,
            )
        )
        out_index += 1

    return Schedule(
        session_duration_min=session_duration_min,
        params=params,
        seed=seed,
        n_redraws=n_redraws,
        blocks=tuple(blocks),
    )
