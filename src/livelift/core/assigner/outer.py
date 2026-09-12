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
  pre-broadcast warning at the API layer) instead of looping forever — the
  degradation level is computed by an EXACT feasibility search
  (:func:`_transition_requirement`), never by an approximate bound: a bound
  that over-promises by one pair makes the joint acceptance set empty and the
  redraw loop grind to ``max_redraws`` (incident 12/09, HTTP 500 on every
  layout of exactly 5 measurement blocks).
- **Infeasible configurations never crash**: a session shorter than one block
  raises :class:`ScheduleInfeasibleError` with a Vietnamese explanation and a
  concrete alternative, which the API turns into a 400. An empty 500 is never
  an acceptable answer to a configuration question.
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
from functools import lru_cache
from typing import Any

PHASES = ("early", "mid", "late")

ON = "ON"
OFF = "OFF"


class ScheduleInfeasibleError(ValueError):
    """The requested design cannot produce a schedule at all.

    Carries a Vietnamese, operator-readable explanation AND a concrete
    alternative configuration. Subclasses :class:`ValueError` so callers that
    already guard ``generate_schedule`` with ``except ValueError`` keep
    working; the API layer catches it by name and answers 400, never 500 —
    a configuration the operator can fix is a client answer, not a server
    fault (incident 12/09).
    """


class RerandomizationExhaustedError(RuntimeError):
    """``max_redraws`` draws went by without hitting the acceptance set.

    Since 12/09 the requirement level is computed by exact feasibility search,
    so the acceptance set is provably non-empty whenever this function is
    reached — this exception therefore means "acceptable but astronomically
    rare under the requested p", not "impossible". Kept as a loud backstop
    rather than a silent relaxation: relaxing the constraint here would change
    the assignment mechanism mid-flight and poison the randomization-test
    reference distribution, which redraws through this very function.
    """


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
        # A real, operator-fixable configuration mistake ("phiên 5 phút, khối
        # 10 phút"). Say what is wrong AND what to type instead — before
        # 12/09 this surfaced as an empty HTTP 500.
        suggested = max(1, duration_min // 4)
        raise ScheduleInfeasibleError(
            f"Phiên {duration_min} phút ngắn hơn một khối {length} phút nên không sinh "
            f"được lịch gán nào. Hãy chọn khối ≤ {duration_min} phút (gợi ý: "
            f"{suggested} phút, cho khoảng 4 khối) hoặc kéo dài phiên lên ít nhất "
            f"{length} phút."
        )

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


_FEASIBILITY_STATE_BUDGET = 200_000
"""Hard ceiling on the search frontier of :func:`_acceptance_set_nonempty`.

Hitting it answers "not feasible", i.e. the requirement degrades one step
further. The search may therefore be conservative, never optimistic — an
optimistic answer is exactly what produced the 12/09 outage.
"""


def _acceptance_set_nonempty(
    phases: tuple[str, ...],
    min_per_arm_per_phase: int,
    k: int,
) -> bool:
    """Does ANY assignment vector satisfy arm balance AND k transition pairs?

    Constructive (a dynamic program that builds a witness), so a ``True``
    answer means the acceptance set of :func:`draw_assignments` is non-empty —
    which is the property the redraw loop needs and the old closed-form bound
    did not deliver.

    Acceptance is: every phase stratum holds ≥ ``required[ph]`` blocks of each
    arm, and over the whole chain #(ON,ON) ≥ k, #(OFF,OFF) ≥ k,
    |#(ON,ON) − #(OFF,OFF)| ≤ 1.

    State per position: the still-open strata counters (each capped at its own
    requirement — counting past it carries no information), the two same-arm
    pair counts, and the previous arm. Two prunings keep it small and keep it
    SOUND:

    * a stratum's counters are dropped, after checking its requirement, once
      its last block has been placed — for the contiguous strata this module
      produces that leaves exactly one open stratum at a time;
    * witnesses are searched with #(ON,ON) ≤ k+1 and #(OFF,OFF) ≤ k+1. Both
      counts are non-decreasing along the chain, so this is not a mid-path
      cut: it restricts the search to witnesses whose FINAL counts are that
      small. Adding same-arm pairs is never forced by the arm-balance rule (a
      strictly alternating chain has zero of them and satisfies every stratum
      requirement ≤ size//2), so a minimal witness is expected to exist; if it
      did not, the answer would be a needless extra degradation, never a
      false promise. Checked against exhaustive enumeration for every
      contiguous 3-stratum layout up to 13 blocks — 3.432 cases, zero
      disagreement (``test_transition_requirement_matches_exhaustive_search``).
    """
    if k <= 0:
        # No transition requirement. Arm balance alone is always satisfiable:
        # required[ph] ≤ size//2 by construction, so half-and-half works.
        return True
    n = len(phases)
    if n < 2:
        return False

    sizes: dict[str, int] = {}
    for ph in phases:
        sizes[ph] = sizes.get(ph, 0) + 1
    required = {ph: min(min_per_arm_per_phase, size // 2) for ph, size in sizes.items()}
    last_at = {ph: i for i, ph in enumerate(phases)}
    cap = k + 1

    # (open stratum counters, #(ON,ON), #(OFF,OFF), previous arm)
    states: set[tuple[tuple[tuple[str, int, int], ...], int, int, str | None]] = {((), 0, 0, None)}
    for i, ph in enumerate(phases):
        req = required[ph]
        counter_cap = req + 1
        nxt: set[tuple[tuple[tuple[str, int, int], ...], int, int, str | None]] = set()
        for counters, n_on_on, n_off_off, last in states:
            open_counters = {c[0]: (c[1], c[2]) for c in counters}
            on_seen, off_seen = open_counters.get(ph, (0, 0))
            for arm in (ON, OFF):
                a, b = n_on_on, n_off_off
                if last == arm:
                    if arm == ON:
                        a += 1
                    else:
                        b += 1
                if a > cap or b > cap:
                    continue
                new_on = min(on_seen + (1 if arm == ON else 0), counter_cap)
                new_off = min(off_seen + (1 if arm == OFF else 0), counter_cap)
                if i == last_at[ph]:
                    if new_on < req or new_off < req:
                        continue  # this stratum can never be repaired later
                    kept = {p: v for p, v in open_counters.items() if p != ph}
                else:
                    kept = dict(open_counters)
                    kept[ph] = (new_on, new_off)
                nxt.add((tuple(sorted((p, u, v) for p, (u, v) in kept.items())), a, b, arm))
        states = nxt
        if not states:
            return False
        if len(states) > _FEASIBILITY_STATE_BUDGET:
            return False  # bail out conservatively — never over-promise
    return any(a >= k and b >= k and abs(a - b) <= 1 for _, a, b, _ in states)


@lru_cache(maxsize=1024)
def _transition_requirement_cached(
    phases: tuple[str, ...],
    min_per_arm_per_phase: int,
    min_transition_pairs: int,
) -> int:
    if min_transition_pairs <= 0 or len(phases) < 2:
        return 0
    for k in range(min_transition_pairs, 0, -1):
        if _acceptance_set_nonempty(phases, min_per_arm_per_phase, k):
            return k
    return 0


def _transition_requirement(
    phases: list[str] | tuple[str, ...],
    min_per_arm_per_phase: int,
    min_transition_pairs: int,
) -> int:
    """Same-arm adjacent-pair requirement the chain can actually support.

    ``min_transition_pairs`` is a request; short chains cannot hold it and the
    requirement degrades to the largest level whose JOINT acceptance set (arm
    balance ∧ transition balance) is provably non-empty — found by exact
    search, high level first (:func:`_acceptance_set_nonempty`).

    Until 12/09 this was a closed-form necessary bound
    (``k ≤ (n_pairs − forced_switches) / 2``) that ignored how the forced
    switches interact with the run structure. It over-promised on 8 of the
    layouts reachable from the API — most visibly EVERY layout of exactly 5
    measurement blocks, phases ``[early, early, mid, late, late]``: arm
    balance forces a switch inside the early pair and inside the late pair, so
    the only candidate same-arm pairs are (1,2) and (2,3), which share block 2
    and therefore cannot be one (ON,ON) and one (OFF,OFF) at the same time.
    The acceptance set was EMPTY, so ``POST /schedule`` burned 10.000 draws and
    answered an empty HTTP 500 for every seed — deterministically, for
    "phiên 50 phút, khối 10 phút" among others.

    Cached: randomization inference redraws through :func:`draw_assignments`
    hundreds of times per session with the very same phase vector.
    """
    return _transition_requirement_cached(
        tuple(phases), min_per_arm_per_phase, min_transition_pairs
    )


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
    raise RerandomizationExhaustedError(
        f"Không bốc được lịch gán thỏa ràng buộc sau {max_redraws} lần vẽ lại "
        f"(chuỗi {len(phases)} khối, p={p}, ≥{min_per_arm_per_phase} khối/nhánh/giai đoạn, "
        f"≥{required_trans} cặp khối liền kề cùng nhánh). Tập chấp nhận không rỗng nhưng "
        f"quá hiếm với p ≠ 0,5 — hãy dùng p = 0,5 hoặc nới ràng buộc thiết kế."
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
