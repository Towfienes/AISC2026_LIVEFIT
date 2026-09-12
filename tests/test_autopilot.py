"""Gate (incident 12/09): `mode='auto'` must actually run the session.

Field report (docs/benchmarks/kiem-chung-van-hanh.md §2.2b) — a schedule with 4
ON blocks was drawn, the session went live, nothing intervened, and the report
came back `compliance_rate: 0.0`, `diff_in_means: null` while EVERY endpoint
answered 200 with no warning at all. `grep` confirmed no scheduler ever called
`execute_action`: "auto" was a label.

Two failures are gated here, because they are different failures:
  * the executor must pin, through the production path, idempotently, without
    racing a human and without touching OFF blocks;
  * the platform must SCREAM when a live auto session is producing no
    treatment — including when the executor is switched off or never started,
    which is exactly the case that stayed silent.

Time is forced by moving the session's `start_ts` backwards in the store, never
by sleeping: the real server clock still drives both the executor and
`execute_action`, so the block attribution under test is the production one.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from livelift.api import autopilot, service
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.core.quality import derive_compliance


@pytest.fixture(autouse=True)
def _clean_heartbeats():
    autopilot.reset_heartbeats()
    yield
    autopilot.reset_heartbeats()


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def client(store):
    app = create_app(store=store)
    with TestClient(app) as c:
        yield c


def _seed_products(client, n=3):
    for i in range(n):
        r = client.post(
            "/products",
            json={
                "product_id": f"SP{i}",
                "name": f"Sản phẩm số {i}",
                "category": "test",
                "cost": 10_000,
                "price": 40_000,
                "stock": 25,
            },
        )
        assert r.status_code == 200, r.text


def _live_auto_session(client, duration=60, block_min=5, seed=2026, mode="auto"):
    created = client.post(
        "/sessions",
        json={"platform": "sim", "mode": mode, "planned_duration_min": duration},
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]
    scheduled = client.post(
        f"/sessions/{session_id}/schedule",
        json={"block_min": block_min, "washout_min": 0, "jitter_s": 0, "seed": seed},
    )
    assert scheduled.status_code == 200, scheduled.text
    started = client.post(f"/sessions/{session_id}/start")
    assert started.status_code == 200, started.text
    return session_id, scheduled.json()["blocks"]


def _place_session_at(store, session_id, offset_s):
    """Force the session's elapsed time to `offset_s` — no sleeping.

    The server clock stays real; only the session's start moves, so the
    executor and `execute_action` both resolve the same block.
    """
    now = service.now_utc()
    store.update_session(session_id, {"start_ts": now - timedelta(seconds=offset_s)})
    return store.get_session(session_id)


def _block_midpoint(block):
    return (block["start_offset_s"] + block["end_offset_s"]) / 2


# ---------------------------------------------------------------------------
# 1. The headline gate: a session walked across several block changes
# ---------------------------------------------------------------------------


def test_auto_session_pins_every_on_block_it_lives_through(client, store):
    """Walk a live auto session across ALL its block changes.

    Before the fix this produced 0 exposures and compliance 0.0 while every
    call answered 200.
    """
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    measurement = [b for b in blocks if not b["is_washout"]]
    on_indices = [b["block_index"] for b in measurement if b["assignment"] == "ON"]
    assert len(on_indices) >= 2, "kịch bản cần ít nhất 2 khối BẬT để có nghĩa"

    for block in measurement:
        _place_session_at(store, session_id, _block_midpoint(block))
        autopilot.step_all(store)

    exposures = store.list_exposure_events(session_id)
    pins = [e for e in exposures if e["event_type"] == "pin" and e["source"] == "model"]
    assert [e["block_idx"] for e in pins] == on_indices, (
        "bộ thực thi phải ghim đúng một lần cho MỖI khối BẬT nó sống qua"
    )
    # not one single exposure lands in an OFF block
    off_indices = {b["block_index"] for b in measurement if b["assignment"] == "OFF"}
    assert not off_indices.intersection(e["block_idx"] for e in exposures)

    compliance = derive_compliance(store.list_assignment_events(session_id), exposures)
    assert compliance.n_on == len(on_indices)
    assert compliance.n_on_exposed == len(on_indices)
    assert compliance.compliance_rate == pytest.approx(1.0)
    assert compliance.n_off_exposed == 0, "nhánh đối chứng không được nhiễm"


def test_two_block_changes_are_enough_to_move_compliance_off_zero(client, store):
    """The minimal version of the gate the incident asked for: ≥ 2 changes."""
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    measurement = [b for b in blocks if not b["is_washout"]]

    seen = 0
    for block in measurement[:4]:  # at least three boundaries crossed
        _place_session_at(store, session_id, _block_midpoint(block))
        autopilot.step_all(store)
        seen += 1
    assert seen >= 3

    exposures = store.list_exposure_events(session_id)
    compliance = derive_compliance(store.list_assignment_events(session_id), exposures)
    assert compliance.compliance_rate > 0.0
    assert len(exposures) == sum(1 for b in measurement[:4] if b["assignment"] == "ON"), (
        "số exposure_event phải khớp đúng số khối BẬT đã đi qua"
    )


def test_the_pin_goes_through_the_production_path_with_a_logged_propensity(client, store):
    """Not a private pin helper: the inner-tier audit trail must be there."""
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _place_session_at(store, session_id, _block_midpoint(on_block))
    autopilot.step_all(store)

    interventions = store.list_interventions(session_id)
    assert len(interventions) == 1
    row = interventions[0]
    assert row["source"] == "model"
    assert row["inner_propensity"] is not None
    assert 0 < row["inner_propensity"] <= 1
    assert row["candidates_json"], "tập ứng viên phải được ghi lại (dấu vết kiểm chứng)"
    assert row["override_reason"] is None


# ---------------------------------------------------------------------------
# 2. Idempotency, restart safety, and not racing the desk
# ---------------------------------------------------------------------------


def test_repeated_sweeps_inside_one_block_pin_exactly_once(client, store):
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _place_session_at(store, session_id, _block_midpoint(on_block))

    for _ in range(6):
        autopilot.step_all(store)

    assert len(store.list_exposure_events(session_id)) == 1


def test_restarting_the_server_mid_block_neither_duplicates_nor_skips(client, store):
    """Idempotency comes from the stored exposure rows, not from memory.

    `reset_heartbeats()` is what a process restart looks like to this module:
    everything it knew is gone, only the store remains.
    """
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    measurement = [b for b in blocks if not b["is_washout"]]
    first_on = next(b for b in measurement if b["assignment"] == "ON")

    _place_session_at(store, session_id, _block_midpoint(first_on))
    autopilot.step_all(store)
    assert len(store.list_exposure_events(session_id)) == 1

    autopilot.reset_heartbeats()  # ← restart, same block still on air
    autopilot.step_all(store)
    assert len(store.list_exposure_events(session_id)) == 1, "khởi động lại KHÔNG được ghim trùng"

    # a later ON block, reached after the restart, is still served
    later_on = next(
        b
        for b in measurement
        if b["assignment"] == "ON" and b["block_index"] > first_on["block_index"]
    )
    _place_session_at(store, session_id, _block_midpoint(later_on))
    autopilot.step_all(store)
    indices = sorted(e["block_idx"] for e in store.list_exposure_events(session_id))
    assert indices == [first_on["block_index"], later_on["block_index"]], (
        "khởi động lại KHÔNG được bỏ sót khối BẬT tiếp theo"
    )


def test_a_manual_override_in_the_block_wins_and_is_not_overwritten(client, store):
    """The operator just acted in this block — hands off for the rest of it."""
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _place_session_at(store, session_id, _block_midpoint(on_block))

    manual = client.post(
        f"/sessions/{session_id}/actions/override",
        json={"product_id": "SP2", "reason": "hết hàng"},
    )
    assert manual.status_code == 200, manual.text

    autopilot.step_all(store)

    exposures = store.list_exposure_events(session_id)
    assert len(exposures) == 1
    assert exposures[0]["source"] == "human"
    assert service.current_pinned_product_id(store.list_interventions(session_id)) == "SP2"


def test_off_blocks_are_left_completely_alone(client, store):
    """The control arm invariant: the system does not act in an OFF block."""
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    off_blocks = [b for b in blocks if b["assignment"] == "OFF" and not b["is_washout"]]
    assert off_blocks
    for block in off_blocks:
        _place_session_at(store, session_id, _block_midpoint(block))
        assert autopilot.step_all(store) == []
    assert store.list_exposure_events(session_id) == []


def test_suggest_mode_and_planned_sessions_are_never_touched(client, store):
    _seed_products(client)
    session_id, blocks = _live_auto_session(client, mode="suggest")
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _place_session_at(store, session_id, _block_midpoint(on_block))
    autopilot.step_all(store)
    assert store.list_exposure_events(session_id) == []


def test_a_block_that_already_ended_is_never_pinned_retroactively(client, store):
    """Pinning "for" a past block would file a false exposure against the
    block currently on air. It is reported as missed instead."""
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    measurement = [b for b in blocks if not b["is_washout"]]
    first_on = next(b for b in measurement if b["assignment"] == "ON")

    # jump straight past the first ON block, landing in a much later one
    last_block = measurement[-1]
    _place_session_at(store, session_id, _block_midpoint(last_block))
    autopilot.step_all(store)

    exposures = store.list_exposure_events(session_id)
    assert first_on["block_index"] not in {e["block_idx"] for e in exposures}
    session = store.get_session(session_id)
    elapsed = service.elapsed_seconds(session, service.now_utc())
    missed = autopilot.missed_on_blocks(store.get_blocks(session_id), exposures, elapsed)
    assert first_on["block_index"] in missed


# ---------------------------------------------------------------------------
# 3. The alarm gate — silence is not an acceptable answer
# ---------------------------------------------------------------------------


def test_a_silent_auto_session_raises_an_alarm_on_the_operator_state(client, store):
    """N minutes live in auto mode with zero actions ⇒ the desk is told.

    This is the failure that produced "mọi endpoint vẫn trả 200 và không một
    cảnh báo nào" in the field report.
    """
    _seed_products(client)
    session_id, _ = _live_auto_session(client)
    _place_session_at(store, session_id, 12 * 60)  # 12 minutes, nothing done

    state = client.get(f"/sessions/{session_id}/state?role=operator")
    assert state.status_code == 200, state.text
    panel = state.json()["autopilot"]
    assert panel is not None
    assert panel["alarm"], "phiên auto 12 phút không hành động mà vẫn im lặng"
    assert "BÁO ĐỘNG" in panel["alarm"]
    assert panel["on_blocks_done"] == 0
    assert panel["on_blocks_total"] > 0
    assert panel["missed_on_blocks"], "các khối BẬT đã trôi qua phải được nêu tên"


def test_the_alarm_fires_even_when_the_executor_is_switched_off(client, store, monkeypatch):
    """The alarm is derived from stored exposures, not from the heartbeat."""
    monkeypatch.setenv("LIVELIFT_AUTOPILOT", "0")
    _seed_products(client)
    session_id, _ = _live_auto_session(client)
    _place_session_at(store, session_id, 12 * 60)

    panel = client.get(f"/sessions/{session_id}/state").json()["autopilot"]
    assert panel["enabled"] is False
    assert panel["alarm"]
    assert "BÁO ĐỘNG" in panel["alarm"]


def test_no_alarm_while_the_executor_is_keeping_up(client, store):
    """A working session must not cry wolf."""
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    measurement = [b for b in blocks if not b["is_washout"]]
    for block in measurement[:5]:
        _place_session_at(store, session_id, _block_midpoint(block))
        autopilot.step_all(store)

    panel = client.get(f"/sessions/{session_id}/state").json()["autopilot"]
    assert panel["alarm"] is None, panel["alarm"]
    assert panel["actions_taken"] > 0
    assert panel["last_run_ts"] is not None, "nhịp tim phải cho thấy hệ thống đang tự chạy"


def test_alarm_stays_quiet_before_the_threshold_and_for_other_modes(client, store):
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    first = [b for b in blocks if not b["is_washout"]][0]
    _place_session_at(store, session_id, max(1.0, _block_midpoint(first) / 2))
    session = store.get_session(session_id)
    elapsed = service.elapsed_seconds(session, service.now_utc())
    assert (
        autopilot.silence_alarm(
            session, store.get_blocks(session_id), [], elapsed, threshold_s=300.0
        )
        is None
    )
    # a suggest-mode session has no executor and therefore no alarm
    assert (
        autopilot.silence_alarm(
            {**session, "mode": "suggest"}, store.get_blocks(session_id), [], 3600.0, 300.0
        )
        is None
    )


def test_suggest_sessions_get_no_autopilot_panel(client, store):
    _seed_products(client)
    session_id, _ = _live_auto_session(client, mode="suggest")
    assert client.get(f"/sessions/{session_id}/state").json()["autopilot"] is None


def test_host_state_never_leaks_the_autopilot_panel(client, store):
    """Rule L6: the panel names block indices — the host must not see it."""
    _seed_products(client)
    session_id, _ = _live_auto_session(client)
    host = client.get(f"/sessions/{session_id}/state?role=host").json()
    assert "autopilot" not in host
    assert "missed_on_blocks" not in host


# ---------------------------------------------------------------------------
# 4. The switch
# ---------------------------------------------------------------------------


def test_the_executor_can_be_switched_off_by_configuration(monkeypatch):
    assert autopilot.is_enabled() is True  # default ON for auto sessions
    for value in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("LIVELIFT_AUTOPILOT", value)
        assert autopilot.is_enabled() is False, value
    monkeypatch.setenv("LIVELIFT_AUTOPILOT", "1")
    assert autopilot.is_enabled() is True


def test_switched_off_means_start_creates_no_task(store, monkeypatch):
    monkeypatch.setenv("LIVELIFT_AUTOPILOT", "0")
    assert autopilot.start(store) is None


def test_the_background_loop_really_sweeps_and_stops_cleanly(client, store):
    """The wiring itself, not just the step function.

    Everything else here drives `step_all` by hand; without this the task could
    be dead on arrival and every other gate would still pass — which is exactly
    the shape of the original bug (a mechanism nobody ever invoked).
    """
    _seed_products(client)
    session_id, blocks = _live_auto_session(client)
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _place_session_at(store, session_id, _block_midpoint(on_block))

    async def drive():
        task = asyncio.create_task(autopilot.run_forever(store, tick_s=0.01))
        for _ in range(200):  # ≤ 2 s of polling, exits as soon as it lands
            await asyncio.sleep(0.01)
            if store.list_exposure_events(session_id):
                break
        await autopilot.stop(task)
        assert task.cancelled() or task.done()

    asyncio.run(drive())
    assert len(store.list_exposure_events(session_id)) == 1


def test_a_bad_interval_falls_back_to_the_default_instead_of_crashing(monkeypatch):
    monkeypatch.setenv("LIVELIFT_AUTOPILOT_TICK_S", "không-phải-số")
    assert autopilot.tick_seconds() == autopilot.DEFAULT_TICK_S
    monkeypatch.setenv("LIVELIFT_AUTOPILOT_TICK_S", "-3")
    assert autopilot.tick_seconds() == autopilot.DEFAULT_TICK_S
    monkeypatch.setenv("LIVELIFT_AUTOPILOT_SILENCE_MIN", "2")
    assert autopilot.silence_alarm_after_s() == 120.0


def test_an_operational_refusal_is_reported_not_swallowed(client, store):
    """No product in stock ⇒ the desk learns why nothing was pinned."""
    session_id, blocks = _live_auto_session(client)  # no products created
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _place_session_at(store, session_id, _block_midpoint(on_block))

    lines = autopilot.step_all(store)
    assert lines
    assert "THẤT BẠI" in lines[0]
    panel = client.get(f"/sessions/{session_id}/state").json()["autopilot"]
    assert panel["last_error"], "lý do không ghim được phải hiện ra, không nuốt im"


def test_a_stuck_session_does_not_grow_the_log_one_line_per_sweep(client, store):
    """The executor runs every few seconds for hours — nothing may grow per tick.

    A block whose pin keeps being refused stays pending on purpose (stock can
    come back), so the refusal repeats; only a CHANGE is logged, and the
    heartbeat log is a ring either way.
    """
    session_id, blocks = _live_auto_session(client)  # no products in stock
    on_block = next(b for b in blocks if b["assignment"] == "ON" and not b["is_washout"])
    _place_session_at(store, session_id, _block_midpoint(on_block))

    for _ in range(120):
        autopilot.step_all(store)

    hb = autopilot.heartbeat(session_id)
    assert len(hb.log) == 1, "cùng một lý do lặp lại không được ghi lại mỗi vòng quét"
    assert len(hb.log) <= autopilot.LOG_KEEP
