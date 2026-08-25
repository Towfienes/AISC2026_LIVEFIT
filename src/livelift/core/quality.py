"""Post-session data-quality checks (plan §8.3) — pure functions over rows.

Runs at T+30' after every session. ANY failing check pages the team. Checks
never mutate data: a failed block/session gets flagged for exclusion with a
reason, never edited (HARNESS.md §3).
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

from livelift.ingest.pii import scrub


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_block_integrity(scheduled_blocks: list[dict], recorded_blocks: list[dict]) -> CheckResult:
    """Recorded blocks must match the pre-generated schedule exactly."""
    ok = len(scheduled_blocks) == len(recorded_blocks)
    mismatches = []
    if ok:
        for s, r in zip(scheduled_blocks, recorded_blocks, strict=True):
            for key in ("block_index", "assignment", "is_washout"):
                if s.get(key) != r.get(key):
                    mismatches.append(f"block {s.get('block_index')}: {key}")
        ok = not mismatches
    detail = f"{len(recorded_blocks)}/{len(scheduled_blocks)} blocks" + (
        f"; mismatches: {mismatches[:5]}" if mismatches else ""
    )
    return CheckResult("block_integrity", ok, detail)


def check_assignment_balance(blocks: list[dict], lo: float = 0.4, hi: float = 0.6) -> CheckResult:
    meas = [b for b in blocks if not b.get("is_washout")]
    if not meas:
        return CheckResult("assignment_balance", False, "no measurement blocks")
    share_on = sum(1 for b in meas if b.get("assignment") == "ON") / len(meas)
    return CheckResult("assignment_balance", lo <= share_on <= hi, f"ON share = {share_on:.2f}")


def check_event_continuity(
    tick_timestamps_s: list[float], session_duration_s: float, max_gap_s: float = 60.0
) -> CheckResult:
    """No gap longer than ``max_gap_s`` in the tick stream."""
    if not tick_timestamps_s:
        return CheckResult("event_continuity", False, "no ticks recorded")
    ts = sorted(tick_timestamps_s)
    gaps = [b - a for a, b in zip(ts, ts[1:], strict=False)]
    gaps.append(ts[0] - 0.0)
    gaps.append(session_duration_s - ts[-1])
    worst = max(gaps) if gaps else 0.0
    return CheckResult("event_continuity", worst <= max_gap_s, f"max gap = {worst:.0f}s")


def check_intervention_log(interventions: list[dict]) -> CheckResult:
    """Every executed action needs block_id, source and a propensity."""
    bad = [
        i.get("action_id", "?")
        for i in interventions
        if i.get("executed")
        and (
            i.get("block_id") in (None, "")
            or i.get("inner_propensity") is None
            or i.get("source") in (None, "")
        )
    ]
    return CheckResult(
        "intervention_log_complete",
        not bad,
        "ok" if not bad else f"{len(bad)} incomplete rows, e.g. {bad[:3]}",
    )


def check_pii_clean(
    scrubbed_texts: Iterable[str], sample_size: int = 50, seed: int = 7
) -> CheckResult:
    """Re-run the scrubber over a random sample of STORED comments; finding any
    phone/address/email in supposedly-scrubbed text is a hard failure."""
    texts = list(scrubbed_texts)
    rng = random.Random(seed)
    sample = rng.sample(texts, min(sample_size, len(texts))) if texts else []
    dirty = 0
    kinds: set[str] = set()
    for t in sample:
        res = scrub(t)
        hard = [m for m in res.matches if m.kind in ("phone", "email", "address", "order")]
        if hard:
            dirty += 1
            kinds |= {m.kind for m in hard}
    return CheckResult(
        "pii_clean",
        dirty == 0,
        f"sampled {len(sample)}; leaks: {dirty}" + (f" ({sorted(kinds)})" if kinds else ""),
    )


def check_order_reconciliation(
    db_order_total: float, platform_report_total: float, tolerance: float = 0.01
) -> CheckResult:
    if platform_report_total <= 0:
        ok = db_order_total == 0
        return CheckResult("order_reconciliation", ok, "platform total is zero")
    rel = abs(db_order_total - platform_report_total) / platform_report_total
    return CheckResult(
        "order_reconciliation",
        rel <= tolerance,
        f"db={db_order_total:.0f} platform={platform_report_total:.0f} diff={rel:.1%}",
    )


def run_all(
    scheduled_blocks: list[dict],
    recorded_blocks: list[dict],
    tick_timestamps_s: list[float],
    session_duration_s: float,
    interventions: list[dict],
    scrubbed_texts: Iterable[str],
    db_order_total: float,
    platform_report_total: float,
) -> list[CheckResult]:
    return [
        check_block_integrity(scheduled_blocks, recorded_blocks),
        check_assignment_balance(recorded_blocks),
        check_event_continuity(tick_timestamps_s, session_duration_s),
        check_intervention_log(interventions),
        check_pii_clean(scrubbed_texts),
        check_order_reconciliation(db_order_total, platform_report_total),
    ]
