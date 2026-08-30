"""Post-session QC checks (plan §8.3)."""

from livelift.core.quality import (
    check_assignment_balance,
    check_block_integrity,
    check_event_continuity,
    check_intervention_log,
    check_order_reconciliation,
    check_pii_clean,
    run_all,
)


def blocks(n_on=8, n_off=8):
    out = []
    for i in range(n_on):
        out.append({"block_index": i, "assignment": "ON", "is_washout": False})
    for i in range(n_off):
        out.append({"block_index": n_on + i, "assignment": "OFF", "is_washout": False})
    return out


def test_block_integrity_pass_and_fail():
    sched = blocks()
    assert check_block_integrity(sched, sched).passed
    assert not check_block_integrity(sched, sched[:-1]).passed
    tampered = [dict(b) for b in sched]
    tampered[0]["assignment"] = "OFF"
    assert not check_block_integrity(sched, tampered).passed


def test_assignment_balance():
    assert check_assignment_balance(blocks(8, 8)).passed
    assert not check_assignment_balance(blocks(14, 2)).passed
    assert not check_assignment_balance([]).passed


def test_event_continuity():
    ok = [float(t) for t in range(0, 5400, 30)]
    assert check_event_continuity(ok, 5400).passed
    gap = [t for t in ok if not 1000 <= t <= 1200]
    assert not check_event_continuity(gap, 5400).passed
    assert not check_event_continuity([], 5400).passed


def test_intervention_log_completeness():
    good = [
        {
            "action_id": "a",
            "block_id": "b1",
            "inner_propensity": 0.5,
            "source": "model",
            "executed": True,
        }
    ]
    assert check_intervention_log(good).passed
    bad = [
        {
            "action_id": "a",
            "block_id": None,
            "inner_propensity": 0.5,
            "source": "model",
            "executed": True,
        }
    ]
    assert not check_intervention_log(bad).passed
    # unexecuted rows may be partial
    skipped = [
        {
            "action_id": "a",
            "block_id": None,
            "inner_propensity": None,
            "source": "",
            "executed": False,
        }
    ]
    assert check_intervention_log(skipped).passed


def test_pii_clean_detects_leak():
    clean = ["[SĐT] chốt 1 hộp", "giá bao nhiêu shop"] * 30
    assert check_pii_clean(clean).passed
    leaked = clean + ["gọi em 0901234567 nha"]
    assert not check_pii_clean(leaked, sample_size=len(leaked)).passed


def test_order_reconciliation():
    assert check_order_reconciliation(1_000_000, 1_000_000).passed
    assert check_order_reconciliation(1_005_000, 1_000_000).passed  # within 1%
    assert not check_order_reconciliation(1_100_000, 1_000_000).passed
    assert check_order_reconciliation(0, 0).passed


def test_run_all_returns_six_results():
    res = run_all(
        scheduled_blocks=blocks(),
        recorded_blocks=blocks(),
        tick_timestamps_s=[float(t) for t in range(0, 5400, 30)],
        session_duration_s=5400,
        interventions=[],
        scrubbed_texts=["giá bao nhiêu"],
        db_order_total=0,
        platform_report_total=0,
    )
    assert len(res) == 6
    assert all(r.passed for r in res)


# --- incident 27/08: the gate was crying wolf on clean sessions -------------


def test_human_override_passes_without_propensity():
    """An operator override is not randomized, so it has no propensity by
    definition. Requiring one made every legitimate override fail the gate."""
    rows = [
        {
            "action_id": "a1",
            "block_id": "b1",
            "source": "human",
            "executed": True,
            "inner_propensity": None,
            "override_reason": "hết hàng",
        }
    ]
    assert check_intervention_log(rows).passed


def test_human_override_needs_an_allowed_reason():
    base = {
        "action_id": "a1", "block_id": "b1", "source": "human",
        "executed": True, "inner_propensity": None,
    }
    assert not check_intervention_log([{**base, "override_reason": None}]).passed
    assert not check_intervention_log([{**base, "override_reason": "tui thích thế"}]).passed
    for reason in ("hết hàng", "sai giá", "sự cố kỹ thuật"):
        assert check_intervention_log([{**base, "override_reason": reason}]).passed


def test_model_action_without_propensity_still_fails():
    """The scientific core: a model action MUST log its assignment probability."""
    rows = [
        {
            "action_id": "m1", "block_id": "b1", "source": "model",
            "executed": True, "inner_propensity": None,
        }
    ]
    assert not check_intervention_log(rows).passed


def test_missing_schedule_is_a_distinct_failure():
    """No persisted schedule = no audit trail; it must never read as a pass,
    and its message must differ from a mismatch."""
    res = check_block_integrity([], blocks(2, 2))
    assert not res.passed
    assert "lịch gán" in res.detail.lower()

    mismatch = [dict(b) for b in blocks(2, 2)]
    mismatch[0]["assignment"] = "OFF"
    res2 = check_block_integrity(blocks(2, 2), mismatch)
    assert not res2.passed
    assert res2.detail != res.detail


def test_early_finished_session_passes_continuity():
    """Continuity is judged over the REAL elapsed window; a session that ended
    at 20 minutes must not be charged for the 70 unplayed minutes."""
    ticks = [float(t) for t in range(0, 1200, 30)]
    assert check_event_continuity(ticks, 1200).passed  # real window
    assert not check_event_continuity(ticks, 5400).passed  # planned window (old bug)
