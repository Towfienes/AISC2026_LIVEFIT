"""Post-session QC checks (plan §8.3)."""

from livelift.core.quality import (
    check_assignment_balance,
    check_block_integrity,
    check_event_continuity,
    check_intervention_log,
    check_order_reconciliation,
    check_pii_clean,
    derive_compliance,
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


def timed_blocks(n_on=8, n_off=8, block_s=300):
    """Cùng bố cục `blocks()` nhưng có mốc thời gian — hai kiểm tra SRM (gói Q5)
    cần độ dài khối để tính tỷ lệ thời gian BẬT/TẮT."""
    rows = blocks(n_on, n_off)
    for i, r in enumerate(rows):
        r["start_offset_s"] = i * block_s
        r["end_offset_s"] = (i + 1) * block_s
    return rows


def test_run_all_returns_eight_results():
    """Bộ QC sau phiên: 6 mục gốc + 2 mục SRM đợt 1 (gói Q5)."""
    sched = timed_blocks()
    res = run_all(
        scheduled_blocks=sched,
        recorded_blocks=sched,
        tick_timestamps_s=[float(t) for t in range(0, 4800, 30)],
        session_duration_s=4800,
        interventions=[],
        scrubbed_texts=["giá bao nhiêu"],
        db_order_total=0,
        platform_report_total=0,
        analysis_blocks=sched,
    )
    assert len(res) == 8
    assert [r.name for r in res] == [
        "block_integrity",
        "assignment_balance",
        "assignment_integrity",
        "event_continuity",
        "telemetry_delivery",
        "intervention_log_complete",
        "pii_clean",
        "order_reconciliation",
    ]
    assert all(r.passed for r in res), [r for r in res if not r.passed]


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
        "action_id": "a1",
        "block_id": "b1",
        "source": "human",
        "executed": True,
        "inner_propensity": None,
    }
    assert not check_intervention_log([{**base, "override_reason": None}]).passed
    assert not check_intervention_log([{**base, "override_reason": "tui thích thế"}]).passed
    for reason in ("hết hàng", "sai giá", "sự cố kỹ thuật"):
        assert check_intervention_log([{**base, "override_reason": reason}]).passed


def test_model_action_without_propensity_still_fails():
    """The scientific core: a model action MUST log its assignment probability."""
    rows = [
        {
            "action_id": "m1",
            "block_id": "b1",
            "source": "model",
            "executed": True,
            "inner_propensity": None,
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


# ---------------------------------------------------------------------------
# derive_compliance — VIEW thuần trên hai bảng sự kiện (gói Q3)
# ---------------------------------------------------------------------------


def assignment_events(arms, design_hash="h"):
    """One assignment row per block; `None` in `arms` means a washout block."""
    return [
        {
            "block_idx": i,
            "assignment": arm,
            "block_start_s": i * 300,
            "block_end_s": (i + 1) * 300,
            "design_hash": design_hash,
        }
        for i, arm in enumerate(arms)
    ]


def pin(block_idx, source="model", product_id="P1", event_type="pin"):
    return {
        "block_idx": block_idx,
        "event_type": event_type,
        "product_id": product_id,
        "source": source,
    }


def test_derive_compliance_full_compliance():
    """Mọi khối BẬT đều có ghim của hệ thống, không khối TẮT nào bị ghim →
    tuân thủ 100%, nhiễm nhánh đối chứng 0%."""
    arms = ["ON", "OFF", "ON", "OFF"]
    exposures = [pin(0), pin(2)]
    view = derive_compliance(assignment_events(arms), exposures)
    assert view.n_on == 2
    assert view.n_off == 2
    assert view.compliance_rate == 1.0
    assert view.off_contamination_rate == 0.0
    assert all(b.compliant for b in view.per_block)


def test_derive_compliance_half_compliance():
    """Chỉ 1 trong 2 khối BẬT được ghim → 50%; khối BẬT không ghim bị đánh dấu
    không tuân thủ chứ không biến mất khỏi mẫu số."""
    arms = ["ON", "ON", "OFF", "OFF"]
    view = derive_compliance(assignment_events(arms), [pin(0)])
    assert view.compliance_rate == 0.5
    assert view.n_on_exposed == 1
    by_idx = {b.block_idx: b for b in view.per_block}
    assert by_idx[0].compliant
    assert not by_idx[1].compliant
    assert by_idx[1].exposed is False


def test_derive_compliance_counts_off_block_contamination():
    """Ghim của hệ thống trong khối TẮT là nhiễm nhánh đối chứng: khối đó KHÔNG
    tuân thủ, và tỷ lệ nhiễm được báo riêng — first-stage chỉ đếm khối BẬT sẽ
    báo 'tuân thủ hoàn hảo' cho đúng tình huống tệ nhất."""
    arms = ["ON", "OFF"]
    view = derive_compliance(assignment_events(arms), [pin(0), pin(1)])
    assert view.compliance_rate == 1.0
    assert view.off_contamination_rate == 1.0
    by_idx = {b.block_idx: b for b in view.per_block}
    assert not by_idx[1].compliant


def test_derive_compliance_human_pin_is_not_system_exposure():
    """Ghim tay cùng sản phẩm KHÔNG phải là hệ thống chạy chính sách — đó đúng
    là phần bất tuân mà LATE dùng biến công cụ để xử lý."""
    view = derive_compliance(assignment_events(["ON"]), [pin(0, source="human")])
    assert view.compliance_rate == 0.0
    assert view.per_block[0].n_model_pins == 0
    assert view.per_block[0].n_human_pins == 1


def test_derive_compliance_ignores_washout_and_unpin_rows():
    """Khối washout không gán gì nên không có 'tuân thủ' để đo; 'unpin' không
    phải phơi nhiễm."""
    arms = ["ON", None, "OFF"]
    view = derive_compliance(
        assignment_events(arms),
        [pin(0), pin(1), pin(2, event_type="unpin")],
    )
    assert [b.block_idx for b in view.per_block] == [0, 2]
    assert view.n_on == 1
    assert view.n_off == 1
    assert view.off_contamination_rate == 0.0
    assert view.n_unattributed_exposures == 1, "ghim trong washout không khớp khối nào"


def test_derive_compliance_reports_unattributed_exposures():
    """Hành động ngoài mọi khối (block_idx None) được ĐẾM RIÊNG, không bị bỏ
    im lặng — flag-don't-drop ở tầng phân tích."""
    view = derive_compliance(
        assignment_events(["ON"]),
        [pin(None, source="human"), pin(0)],
    )
    assert view.n_unattributed_exposures == 1
    assert view.compliance_rate == 1.0


def test_derive_compliance_on_empty_inputs():
    """Phiên chưa có dữ liệu: None chứ không phải 0 — 0 sẽ đọc như 'không ai
    tuân thủ', một khẳng định mà dữ liệu trống không cho phép."""
    view = derive_compliance([], [])
    assert view.compliance_rate is None
    assert view.off_contamination_rate is None
    assert view.per_block == ()
