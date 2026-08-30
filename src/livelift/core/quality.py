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
    """Recorded blocks must match the schedule generated BEFORE broadcast.

    Two distinct failures, reported differently because they mean different
    things:
    (a) no schedule was persisted at all -> there is no audit trail, so the
        randomization cannot be verified by anyone (including a judge). This
        must never read as a pass.
    (b) recorded blocks disagree with the schedule -> data loss or tampering.
    """
    if not scheduled_blocks:
        return CheckResult(
            "block_integrity",
            False,
            "KHÔNG có lịch gán lưu trước phiên (design['blocks'] rỗng) — "
            "không thể đối chiếu, mất dấu vết kiểm chứng ngẫu nhiên hóa",
        )
    if len(scheduled_blocks) != len(recorded_blocks):
        return CheckResult(
            "block_integrity",
            False,
            f"số khối lệch: ghi nhận {len(recorded_blocks)}, lịch gán {len(scheduled_blocks)}",
        )
    mismatches = []
    for sched, rec in zip(scheduled_blocks, recorded_blocks, strict=True):
        for key in ("block_index", "assignment", "is_washout"):
            if sched.get(key) != rec.get(key):
                mismatches.append(f"khối {sched.get('block_index')}: {key}")
    return CheckResult(
        "block_integrity",
        not mismatches,
        f"{len(recorded_blocks)} khối khớp lịch gán"
        if not mismatches
        else f"lệch so với lịch gán: {mismatches[:5]}",
    )


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


ALLOWED_OVERRIDE_REASONS = ("hết hàng", "sai giá", "sự cố kỹ thuật")


def check_intervention_log(interventions: list[dict]) -> CheckResult:
    """Every executed action must be auditable — but the rule differs by source.

    - ``source="model"``: the assignment probability MUST be logged. This is the
      scientific core: without a propensity the action cannot enter any
      off-policy or heterogeneous-effect estimate.
    - ``source="human"``: an operator override is not randomized, so it has NO
      propensity by definition. Requiring one made every legitimate override
      fail the gate (incident 27/08) — a quality gate that cries wolf gets
      ignored. What an override must carry instead is one of the three allowed
      reasons, so non-compliance stays measurable.
    - Every executed row, whatever the source, must name the block it ran in.
    """
    problems: list[str] = []
    for i in interventions:
        if not i.get("executed"):
            continue  # skipped/proposed rows may be partial
        action_id = i.get("action_id", "?")
        source = i.get("source") or ""
        if i.get("block_id") in (None, ""):
            problems.append(f"{action_id}: thiếu block_id")
        if not source:
            problems.append(f"{action_id}: thiếu source")
        elif source == "model" and i.get("inner_propensity") is None:
            problems.append(f"{action_id}: hành động của mô hình thiếu inner_propensity")
        elif source == "human":
            reason = i.get("override_reason")
            if not reason:
                problems.append(f"{action_id}: can thiệp tay thiếu override_reason")
            elif reason not in ALLOWED_OVERRIDE_REASONS:
                problems.append(f"{action_id}: lý do can thiệp không hợp lệ ({reason!r})")
    return CheckResult(
        "intervention_log_complete",
        not problems,
        "ok" if not problems else f"{len(problems)} vấn đề, ví dụ: {problems[:3]}",
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
