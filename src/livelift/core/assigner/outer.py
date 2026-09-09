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
  HBS WP 26-012). At p=0.5 the acceptance rule is exchangeable between the two
  arms, so the marginal propensity stays exactly 0.5 for every block — recorded
  as such. At p≠0.5 that symmetry argument FAILS: conditioning on the balance
  constraint shifts the per-block marginal propensity away from p, so the
  logged p would be wrong as an IPW propensity. :func:`draw_assignments`
  therefore warns when p≠0.5 is combined with rerandomization; inference must
  then rely on redraws from this very mechanism (which stay valid), never on
  the logged p.
- **Transition balance** (research 08/09): the acceptance rule additionally
  requires, over the measurement-block chain, at least ``min_transition_pairs``
  adjacent same-arm pairs of EACH kind — #(ON,ON) ≥ k and #(OFF,OFF) ≥ k —
  with |#(ON,ON) − #(OFF,OFF)| ≤ 1. The carryover-robust sensitivity
  estimators (adjacent-pair HT of Ni, Kalfountzou & Bojinov, HBS WP 26-012;
  block-section CRT of Liu & Zhong, arXiv:2602.23257) only use same-arm
  adjacent pairs, and under unconstrained Bernoulli a session can come out
  degenerate (too few pairs of one kind) with non-trivial probability. This is
  the single-stream substitute for blocked sequential rerandomization (Zeng et
  al., SRSB, arXiv:2604.02489, Algorithm 3), which needs parallel units and
  cannot apply to one stream. Short sessions degrade the requirement
  gracefully (``realized_transition_pairs`` / ``constraint_met`` + a
  pre-broadcast warning at the API layer) instead of looping forever.
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

import hashlib
import json
import random
import warnings
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

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
    min_transition_pairs: int = 3
    max_redraws: int = 10_000

    def __post_init__(self) -> None:
        if self.block_min <= 0:
            raise ValueError("block_min must be > 0")
        if self.washout_min < 0 or self.jitter_s < 0:
            raise ValueError("washout_min and jitter_s must be >= 0")
        if not 0.0 < self.p < 1.0:
            raise ValueError("p must be in (0, 1)")
        if self.min_transition_pairs < 0:
            raise ValueError("min_transition_pairs must be >= 0")


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
    realized_min_per_arm_per_phase: int = 0
    """Smallest per-arm-per-phase guarantee the layout could actually deliver.

    ``DesignParams.min_per_arm_per_phase`` is a request; short phases cap it.
    Recording the realized value keeps the design claim honest — see
    :meth:`constraint_met`.
    """
    realized_transition_pairs: int = 0
    """Same-arm adjacent-pair guarantee the chain could actually deliver.

    ``DesignParams.min_transition_pairs`` is a request; a short measurement
    chain caps it (see :func:`_transition_requirement`). ``0`` means the
    transition constraint was not enforced at all — the flag, not silence,
    carries that fact to the operator (flag-don't-drop)."""

    @property
    def constraint_met(self) -> bool:
        """Whether the schedule delivers the requested balance guarantees."""
        return (
            self.realized_min_per_arm_per_phase >= self.params.min_per_arm_per_phase
            and self.realized_transition_pairs >= self.params.min_transition_pairs
        )

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


def design_hash(design_params: DesignParams | Mapping[str, Any], seed: int) -> str:
    """SHA-256 commitment over the design that will be broadcast (gói Q3).

    The schedule is a deterministic function of (``DesignParams``, ``seed``), so
    hashing exactly that pair fingerprints the whole randomization. Publishing
    the hash BEFORE the session — and storing it with the assignment rows —
    makes the design falsifiable after the fact: anyone holding the design json
    can recompute the hash and see that the parameters were not touched
    mid-session. This is the single-team analogue of PlanOut's parameter
    namespacing (Bakshy, Eckles & Bernstein, WWW 2014) and of the "commit the
    design, then run" discipline in Fabijan et al. (KDD 2019).

    The hash is over CANONICAL JSON — ``sort_keys=True`` and fixed separators —
    so key order, whitespace, and dict construction order cannot change it. A
    field added to :class:`DesignParams` later WILL change the hash of an
    otherwise identical design; that is intended (it is a different design), and
    it is why the design json itself, not only the hash, stays persisted.

    Pure: no clock, no RNG, no I/O. ``design_params`` may be a
    :class:`DesignParams` or the plain mapping persisted in
    ``live_session.design['params']``.
    """
    params: dict[str, Any] = (
        asdict(design_params) if isinstance(design_params, DesignParams) else dict(design_params)
    )
    canonical = json.dumps(
        {"params": params, "seed": int(seed)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
        n = (duration_min - 2 * length + washout) // (length + washout) if (length + washout) else 0
        if n >= 4:
            return [2 * length] + [length] * (n - 2) + [2 * length]
        # too short for a doubled-endpoint layout — fall through to uniform

    n = 1 + (duration_min - length) // (length + washout) if (length + washout) else 1
    return [length] * max(n, 1)


def _phase_of(midpoint_s: float, session_s: float) -> str:
    """Phase = which third of the session the block's midpoint falls into."""
    idx = min(int(midpoint_s / session_s * len(PHASES)), len(PHASES) - 1)
    return PHASES[idx]


def _transition_requirement(
    phases: list[str],
    min_per_arm_per_phase: int,
    min_transition_pairs: int,
) -> int:
    """Same-arm adjacent-pair requirement the chain can actually support.

    ``min_transition_pairs`` is a request; the feasibility cap keeps short
    sessions from making the joint acceptance set empty (and the redraw loop
    from spinning to ``max_redraws``): a chain of n blocks has n−1 adjacent
    pairs, k pairs of each kind consume 2k of them, and every stratum with an
    active arm-balance requirement forces at least one switch pair inside its
    span (strata are contiguous by the midpoint definition), as does the mere
    presence of both arms — so k ≤ (n_pairs − forced_switches) / 2. The cap is
    a necessary bound, not a sufficiency proof; the ``max_redraws`` guard in
    :func:`draw_assignments` stays as the loud backstop. Measured acceptance
    rates for the standard 30–90-minute layouts are all comfortably nonzero
    (research log 08/09).
    """
    if min_transition_pairs <= 0 or len(phases) < 2:
        return 0
    strata_sizes: dict[str, int] = {}
    for ph in phases:
        strata_sizes[ph] = strata_sizes.get(ph, 0) + 1
    active = sum(1 for size in strata_sizes.values() if min(min_per_arm_per_phase, size // 2) >= 1)
    n_pairs = len(phases) - 1
    return min(min_transition_pairs, max(0, (n_pairs - max(1, active)) // 2))


def draw_assignments(
    phases: list[str],
    rng: random.Random,
    p: float = 0.5,
    min_per_arm_per_phase: int = 2,
    max_redraws: int = 10_000,
    min_transition_pairs: int = 3,
) -> tuple[list[str], int]:
    """The production assignment mechanism: i.i.d. Bernoulli(p) with
    rerandomization (arm-balance + transition-balance acceptance rule).

    Redraws until (a) each phase stratum contains at least
    ``min_per_arm_per_phase`` blocks of each arm and (b) the measurement chain
    holds at least ``min_transition_pairs`` adjacent same-arm pairs of EACH
    kind — #(ON,ON) ≥ k AND #(OFF,OFF) ≥ k AND |#(ON,ON) − #(OFF,OFF)| ≤ 1.
    Both requirements are capped at what the layout can possibly hold, so
    short sessions degrade gracefully instead of looping forever. Returns the
    accepted assignment vector and the number of redraws used.

    The transition rule is deliberately SYMMETRIC under the arm swap ON↔OFF
    (the swap maps #(ON,ON) ↔ #(OFF,OFF), leaving the three conditions
    invariant). At p=0.5 the proposal distribution is also swap-invariant, so
    conditioning on acceptance preserves P(block = ON) = 0.5 exactly for every
    block — an asymmetric variant (e.g. a floor on ON-pairs only) would bias
    the logged propensity. At p≠0.5 that exchangeability argument fails for
    BOTH constraints, so a warning is emitted — the logged p must not be used
    as an IPW propensity then (see module docstring).

    This function is the single source of truth for the assignment
    distribution: `generate_schedule` uses it to assign, and the randomization
    test re-draws from it to build the reference distribution — which is why
    the transition constraint needs no separate inference machinery.
    """
    strata: dict[str, list[int]] = {}
    for i, ph in enumerate(phases):
        strata.setdefault(ph, []).append(i)
    # The constraint is capped by what each stratum can physically hold. That
    # cap BINDS at ordinary session lengths (endpoint doubling spends 4L of the
    # timeline on 2 blocks), so the schedule can silently deliver a weaker
    # guarantee than the docs advertise. The realized value is returned so the
    # caller can record it and warn (audit 30/08).
    required = {ph: min(min_per_arm_per_phase, len(idx) // 2) for ph, idx in strata.items()}
    required_trans = _transition_requirement(phases, min_per_arm_per_phase, min_transition_pairs)

    if p != 0.5 and (any(req > 0 for req in required.values()) or required_trans > 0):
        warnings.warn(
            "p != 0.5 kết hợp rerandomization: xác suất biên mỗi khối không còn "
            "đúng bằng p — propensity ghi trong log KHÔNG dùng được cho suy diễn "
            "IPW; kiểm định ngẫu nhiên hóa vẫn hợp lệ vì vẽ lại bằng đúng cơ chế "
            "này (xem docstring module outer.py).",
            stacklevel=2,
        )

    for redraw in range(max_redraws):
        arms = [ON if rng.random() < p else OFF for _ in phases]
        ok = True
        for ph, idx in strata.items():
            n_on = sum(1 for i in idx if arms[i] == ON)
            if n_on < required[ph] or (len(idx) - n_on) < required[ph]:
                ok = False
                break
        if ok and required_trans > 0:
            n_on_on = n_off_off = 0
            for prev, nxt in zip(arms, arms[1:], strict=False):
                if prev == nxt:
                    if prev == ON:
                        n_on_on += 1
                    else:
                        n_off_off += 1
            ok = (
                n_on_on >= required_trans
                and n_off_off >= required_trans
                and abs(n_on_on - n_off_off) <= 1
            )
        if ok:
            return arms, redraw
    raise RuntimeError(f"rerandomization failed to satisfy constraints in {max_redraws} draws")


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
    phases = [_phase_of(starts[m] + lengths[m] * 30, total_s) for m in range(n_meas)]

    arms, n_redraws = draw_assignments(
        phases,
        rng,
        p=params.p,
        min_per_arm_per_phase=params.min_per_arm_per_phase,
        max_redraws=params.max_redraws,
        min_transition_pairs=params.min_transition_pairs,
    )
    # What the layout could actually guarantee, per stratum and per chain.
    stratum_sizes = [phases.count(ph) for ph in PHASES if ph in phases]
    realized_min = min(
        (min(params.min_per_arm_per_phase, size // 2) for size in stratum_sizes),
        default=0,
    )
    realized_transition = _transition_requirement(
        phases, params.min_per_arm_per_phase, params.min_transition_pairs
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
        realized_min_per_arm_per_phase=realized_min,
        realized_transition_pairs=realized_transition,
        blocks=tuple(blocks),
    )
