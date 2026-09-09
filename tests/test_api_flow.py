"""End-to-end API flow on the in-memory store — no network, no DB.

Covers the hard project rules at the HTTP layer:
- rule 1: a comment with PII is stored/returned scrubbed everywhere
- rule 3: host state contains no block/assignment keys (blinding L6)
- rule 4: a session cannot start without a persisted schedule
- rule 5: only the three allowed override reasons pass validation
- L5: GET /r/{code} redirects AND logs a click
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


def make_product(client, pid="P1", stock=10):
    r = client.post(
        "/products",
        json={
            "product_id": pid,
            "name": f"Sản phẩm {pid}",
            "category": "test",
            "cost": 20000,
            "price": 50000,
            "stock": stock,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def make_session(client, mode="auto", duration=60):
    r = client.post(
        "/sessions",
        json={"platform": "youtube", "mode": mode, "planned_duration_min": duration},
    )
    assert r.status_code == 200, r.text
    return r.json()


def schedule(client, session_id, seed=7):
    r = client.post(f"/sessions/{session_id}/schedule", json={"seed": seed})
    assert r.status_code == 200, r.text
    return r.json()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["store_backend"] == "memory"


def test_start_without_schedule_refused(client):
    """Hard rule 4: no schedule, no broadcast."""
    session = make_session(client)
    r = client.post(f"/sessions/{session['session_id']}/start")
    assert r.status_code == 409
    assert "lịch gán" in r.json()["detail"].lower()


def test_schedule_locked_once_live(client):
    session = make_session(client)
    sid = session["session_id"]
    schedule(client, sid)
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    r = client.post(f"/sessions/{sid}/schedule", json={"seed": 1})
    assert r.status_code == 409


def test_schedule_warns_before_broadcast_when_transition_balance_degraded(client):
    """Research 08/09: a 30' session cannot hold 3 same-arm adjacent pairs of
    each kind — the operator must be told BEFORE going live (flag-don't-drop),
    and a 90' session must stay warning-free."""
    short = make_session(client, duration=30)
    r = schedule(client, short["session_id"])
    assert r["realized_transition_pairs"] == 1
    assert r["warning"] is not None
    assert "cặp khối liền kề" in r["warning"]

    full = make_session(client, duration=90)
    r = schedule(client, full["session_id"])
    assert r["realized_transition_pairs"] == 3
    assert r["warning"] is None


def test_full_flow(client):
    make_product(client, "P1")
    make_product(client, "P2")
    session = make_session(client)
    sid = session["session_id"]

    sched = schedule(client, sid, seed=11)
    assert sched["n_on"] + sched["n_off"] == len(
        [b for b in sched["blocks"] if not b["is_washout"]]
    )
    assert client.post(f"/sessions/{sid}/start").status_code == 200

    # --- operator state has experiment info; host state must NOT (L6) ---
    op = client.get(f"/sessions/{sid}/state", params={"role": "operator"}).json()
    assert op["current_block"] is not None
    assert op["current_block"]["assignment"] in ("ON", "OFF")
    assert len(op["cards"]) >= 1
    assert all(c["source"] == "forecast" for c in op["cards"])
    assert all(c.get("ci_low") is None for c in op["cards"])

    host = client.get(f"/sessions/{sid}/state", params={"role": "host"}).json()
    forbidden = {"assignment", "block", "current_block", "seconds_remaining", "cards", "mode"}
    assert forbidden.isdisjoint(host.keys()), host
    assert set(host.keys()) == {"pinned_product", "price", "stock", "elapsed_s"}

    # --- comment with PII is scrubbed everywhere (rule 1) ---
    r = client.post(
        f"/sessions/{sid}/comments",
        json={"text": "0901234567 ship về Gò Vấp nha shop"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "[SĐT]" in body["text"]
    assert "[ĐỊA CHỈ]" in body["text"]
    assert "0901234567" not in body["text"]
    assert "phone" in body["pii_kinds"]
    # intent_confidence (gói F) is stored and served: a float in [0, 1] from
    # the trained model, or None on the keyword-baseline fallback
    assert "intent_confidence" in body
    assert body["intent_confidence"] is None or 0.0 <= body["intent_confidence"] <= 1.0
    listed = client.get(f"/sessions/{sid}/comments").json()
    assert all("0901234567" not in c["text"] for c in listed)
    assert listed[0]["block_id"] is not None  # attributed to the current block
    assert listed[0]["intent_confidence"] == body["intent_confidence"]

    # --- ticks ---
    r = client.post(f"/sessions/{sid}/ticks", json={"viewers": 85, "comment_rate": 12})
    assert r.status_code == 200
    assert client.get(f"/sessions/{sid}/ticks").json()[0]["viewers"] == 85

    # --- shortlink redirect logs a click (L5) ---
    link = client.post(
        "/shortlinks",
        json={"product_id": "P1", "session_id": sid, "target_url": "https://shop.example/p1"},
    ).json()
    r = client.get(f"/r/{link['code']}", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "https://shop.example/p1"
    assert client.get("/r/khong-ton-tai", follow_redirects=False).status_code == 404

    # --- override: invalid reason rejected at validation (rule 5) ---
    r = client.post(
        f"/sessions/{sid}/actions/override",
        json={"product_id": "P1", "reason": "thích thì đổi"},
    )
    assert r.status_code == 422
    r = client.post(
        f"/sessions/{sid}/actions/override",
        json={"product_id": "P1", "reason": "hết hàng"},
    )
    assert r.status_code == 200
    assert r.json()["source"] == "human"

    # --- end + report ---
    assert client.post(f"/sessions/{sid}/end").status_code == 200
    report = client.get(f"/sessions/{sid}/report").json()
    assert report["source"] == "experiment"
    # The report contains only blocks that ACTUALLY AIRED. This session ends a
    # second after it starts, so the scheduled blocks beyond that never ran and
    # must be excluded — entering them as y = 0.0 attenuated the pooled
    # estimate by ~38% (audit 30/08).
    assert report["n_blocks"] <= sched["n_on"] + sched["n_off"]
    assert report["compliance"]["override_count"] == 1


def test_unaired_blocks_are_excluded_from_the_report(client):
    """Regression (audit 30/08): a session that ends early keeps its planned
    blocks in the schedule; they must NOT enter the analysis with y = 0.0."""
    make_product(client, "P1")
    session = make_session(client, duration=60)
    sid = session["session_id"]
    sched = client.post(f"/sessions/{sid}/schedule", json={"seed": 5}).json()
    client.post(f"/sessions/{sid}/start")
    client.post(f"/sessions/{sid}/end")

    report = client.get(f"/sessions/{sid}/report").json()
    scheduled = sched["n_on"] + sched["n_off"]
    assert scheduled >= 8, "cần đủ khối để phép kiểm có ý nghĩa"
    assert report["n_blocks"] < scheduled, (
        "khối chưa phát sóng vẫn lọt vào báo cáo — sẽ làm loãng ước lượng"
    )


def test_execute_only_in_on_blocks(client):
    """source='model' execution is refused during OFF blocks (control arm)."""
    make_product(client, "P1")
    session = make_session(client)
    sid = session["session_id"]

    # find a seed whose first block is ON, and one whose first block is OFF
    seed_on = seed_off = None
    for seed in range(60):
        blocks = client.post(f"/sessions/{sid}/schedule", json={"seed": seed}).json()["blocks"]
        first = next(b for b in blocks if not b["is_washout"])
        if first["assignment"] == "ON" and seed_on is None:
            seed_on = seed
        if first["assignment"] == "OFF" and seed_off is None:
            seed_off = seed
        if seed_on is not None and seed_off is not None:
            break
    assert seed_on is not None
    assert seed_off is not None

    # OFF first block: execute must be refused
    client.post(f"/sessions/{sid}/schedule", json={"seed": seed_off})
    client.post(f"/sessions/{sid}/start")
    r = client.post(f"/sessions/{sid}/actions/execute", json={})
    assert r.status_code == 409
    assert "TẮT" in r.json()["detail"]

    # ON first block (new session): execute succeeds and logs propensity
    session2 = make_session(client)
    sid2 = session2["session_id"]
    client.post(f"/sessions/{sid2}/schedule", json={"seed": seed_on})
    client.post(f"/sessions/{sid2}/start")
    r = client.post(f"/sessions/{sid2}/actions/execute", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "model"
    assert 0 < body["inner_propensity"] <= 1.0
    assert body["considered"], "candidates_json must be logged"

    # the pin now shows up in operator + host state
    op = client.get(f"/sessions/{sid2}/state").json()
    assert op["pinned_product"] is not None
    host = client.get(f"/sessions/{sid2}/state", params={"role": "host"}).json()
    assert host["pinned_product"] is not None


def test_execute_scopes_to_the_clicked_card(client):
    """Defect 09/2026: chỉ gửi card_id khiến server ngẫu nhiên hoá TOÀN BỘ tập
    ứng viên — bấm thẻ A có thể ghim sản phẩm B. Nay request chỉ định thẻ phải
    được scope vào overlap set của đúng thẻ đó."""
    make_product(client, "P1")
    make_product(client, "P2")
    make_product(client, "P3", stock=0)  # hết hàng — không bao giờ là ứng viên

    session = make_session(client)
    sid = session["session_id"]
    seed_on = next(
        seed
        for seed in range(60)
        if next(
            b
            for b in client.post(f"/sessions/{sid}/schedule", json={"seed": seed}).json()["blocks"]
            if not b["is_washout"]
        )["assignment"]
        == "ON"
    )
    client.post(f"/sessions/{sid}/schedule", json={"seed": seed_on})
    assert client.post(f"/sessions/{sid}/start").status_code == 200

    # product_id chỉ định: sản phẩm ghim phải nằm trong overlap set chứa thẻ đó
    r = client.post(
        f"/sessions/{sid}/actions/execute",
        json={"card_id": "card-0-P2", "product_id": "P2"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "P2" in body["overlap_set"]
    assert body["product_id"] in body["overlap_set"]

    # client cũ chỉ gửi card_id: vẫn scope qua product_id tách từ card_id
    r = client.post(f"/sessions/{sid}/actions/execute", json={"card_id": "card-1-P1"})
    assert r.status_code == 200, r.text
    assert "P1" in r.json()["overlap_set"]

    # thẻ trỏ sản phẩm không còn là ứng viên -> 409, tuyệt đối không ghim bừa
    r = client.post(f"/sessions/{sid}/actions/execute", json={"product_id": "P3"})
    assert r.status_code == 409
    assert "không còn hợp lệ" in r.json()["detail"]

    # không chỉ định thẻ: giữ hành vi cũ (chọn trên toàn bộ tập ứng viên)
    r = client.post(f"/sessions/{sid}/actions/execute", json={})
    assert r.status_code == 200, r.text


def test_demo_seed_and_experiment_summary(client):
    """Demo seeding produces analyzable sessions; the pooled summary runs the
    pre-registered estimator and returns experiment-source numbers with CI."""
    r = client.post("/demo/seed", json={"n_sessions": 3, "effect": 0.5, "duration_min": 40})
    assert r.status_code == 200, r.text
    seeded = r.json()
    assert len(seeded["session_ids"]) == 3

    summary = client.get("/experiment/summary").json()
    assert summary["source"] == "experiment"
    assert summary["n_sessions"] >= 3
    assert summary["n_blocks"] >= 8
    assert summary["estimate"] is not None
    assert summary["ci_low"] is not None
    assert summary["ci_low"] < summary["estimate"] < summary["ci_high"]
    assert summary["measured_cv"] is not None
    assert summary["power_table"], "power table must be filled from measured CV"
    # Review 06/09: at constant p=0.5 the Hájek/IPW number is identical to
    # `estimate` — it must not be published as a second estimator.
    assert "estimate_ht" not in summary

    # replay session is live and serves state for the web replay page
    replay = seeded["replay_session_id"]
    op = client.get(f"/sessions/{replay}/state").json()
    assert op["status"] == "live"

    # demo comments demonstrate the scrubber in the stored feed
    all_comments = []
    for sid in seeded["session_ids"]:
        all_comments += client.get(f"/sessions/{sid}/comments").json()
    joined = " ".join(c["text"] for c in all_comments)
    assert "0901234567" not in joined
    assert "[SĐT]" in joined


def test_summary_insufficient_data_message(client):
    summary = client.get("/experiment/summary").json()
    assert summary["estimate"] is None
    assert "Chưa đủ dữ liệu" in summary["message"]


# ---------------------------------------------------------------------------
# PREREGISTRATION §7 — freeze on effect estimates (RESULTS_FREEZE_UNTIL)
# ---------------------------------------------------------------------------


def _with_freeze(client, monkeypatch, value: str):
    """GET /experiment/summary with RESULTS_FREEZE_UNTIL set to ``value``."""
    from livelift.config import get_settings

    monkeypatch.setenv("RESULTS_FREEZE_UNTIL", value)
    get_settings.cache_clear()
    try:
        return client.get("/experiment/summary").json()
    finally:
        monkeypatch.delenv("RESULTS_FREEZE_UNTIL", raising=False)
        get_settings.cache_clear()


def test_summary_locked_before_freeze_date(client, monkeypatch):
    """§7: before the freeze date no inferential field may be served — the
    operational numbers §7 explicitly allows (sessions, blocks, CV, MDE,
    compliance) still are."""
    client.post("/demo/seed", json={"n_sessions": 3, "effect": 0.5, "duration_min": 40})
    summary = _with_freeze(client, monkeypatch, "2999-01-01")

    assert summary["estimable"] is False
    for field in ("estimate", "ci_low", "ci_high", "p_value", "n_draws"):
        assert summary[field] is None, f"{field} lọt qua khóa §7"
    assert "khóa đến 2999-01-01" in summary["message"]
    assert "§7" in summary["message"]
    # operational numbers still served
    assert summary["n_sessions"] >= 3
    assert summary["n_blocks"] >= 8
    assert summary["n_on"] + summary["n_off"] == summary["n_blocks"]
    assert summary["measured_cv"] is not None
    assert summary["power_table"], "bảng MDE là chỉ số vận hành — §7 cho phép"


def test_summary_unlocked_on_or_after_freeze_date(client, monkeypatch):
    client.post("/demo/seed", json={"n_sessions": 3, "effect": 0.5, "duration_min": 40})
    summary = _with_freeze(client, monkeypatch, "2000-01-01")
    assert summary["estimable"] is True
    assert summary["estimate"] is not None
    assert summary["p_value"] is not None
    assert summary["ci_low"] is not None


def test_summary_malformed_freeze_date_fails_closed(client, monkeypatch):
    """A typo in the freeze config must lock, never silently unlock."""
    client.post("/demo/seed", json={"n_sessions": 3, "effect": 0.5, "duration_min": 40})
    summary = _with_freeze(client, monkeypatch, "14/09/2026")
    assert summary["estimable"] is False
    assert summary["estimate"] is None
    assert "không hợp lệ" in summary["message"]


def test_summary_redraws_use_each_sessions_saved_design(client, monkeypatch):
    """Review 06/09: analyze_outer must receive the PERSISTED DesignParams of
    every pooled session (demo sessions store jitter_s=0, not the default 30)
    so redraws run the design that actually ran."""
    from livelift.analysis import estimators
    from livelift.api.routes import reports

    captured = {}

    def spy(*args, **kwargs):
        captured["design_params"] = kwargs.get("design_params")
        return estimators.analyze_outer(*args, **kwargs)

    monkeypatch.setattr(reports, "analyze_outer", spy)
    client.post("/demo/seed", json={"n_sessions": 2, "effect": 0.5, "duration_min": 40})
    summary = client.get("/experiment/summary").json()
    assert summary["estimate"] is not None

    params = captured.get("design_params")
    assert params, "design_params không được nối từ rebuild_design_params xuống analyze_outer"
    ended = [s for s in client.get("/sessions").json() if s["status"] == "ended"]
    assert {s["session_id"] for s in ended} <= set(params)
    assert all(p.jitter_s == 0 for p in params.values()), (
        "phải là DesignParams đã lưu của phiên (demo seed dùng jitter_s=0), "
        "không phải tham số mặc định"
    )


def test_rebuild_design_params_keeps_legacy_sessions_unconstrained():
    """Research 08/09: a design json persisted BEFORE the transition-balance
    constraint has no `min_transition_pairs` key — that session ran without the
    constraint, so RI redraws must reconstruct 0 (off), never today's default
    of 3 (a design nobody ran). New sessions persist the key and are honored."""
    from livelift.api.service import rebuild_design_params

    legacy = {"design": {"params": {"block_min": 5, "p": 0.5, "min_per_arm_per_phase": 2}}}
    assert rebuild_design_params(legacy).min_transition_pairs == 0

    current = {"design": {"params": {"block_min": 5, "min_transition_pairs": 3}}}
    assert rebuild_design_params(current).min_transition_pairs == 3

    # no persisted design at all -> plain defaults (documented fallback)
    assert rebuild_design_params({"design": None}).min_transition_pairs == 3


def test_demo_seed_is_repeatable(client):
    """Regression (incident 27/08): the user clicks "Xem thử ngay" more than
    once — the second seed must succeed, not 500 on a duplicate shortlink code."""
    first = client.post("/demo/seed", json={"n_sessions": 1})
    assert first.status_code == 200, first.text
    second = client.post("/demo/seed", json={"n_sessions": 1})
    assert second.status_code == 200, second.text
    codes_a = set(first.json()["shortlink_codes"])
    codes_b = set(second.json()["shortlink_codes"])
    assert codes_a
    assert codes_b
    assert not (codes_a & codes_b), "mã liên kết phải khác nhau giữa hai lần seed"
    # Both runs must leave usable sessions behind for the replay screen.
    sessions = client.get("/sessions").json()
    assert sum(1 for s in sessions if s["status"] == "ended") >= 2


# ---------------------------------------------------------------------------
# Gói Q3 — assignment_event / exposure_event + design_hash commitment
# ---------------------------------------------------------------------------


def first_measurement_seed(client, sid, arm="ON"):
    """Seed whose FIRST measurement block carries `arm` (schedules are cheap to
    redraw before broadcast, so this stays a plain search)."""
    for seed in range(60):
        blocks = client.post(f"/sessions/{sid}/schedule", json={"seed": seed}).json()["blocks"]
        first = next(b for b in blocks if not b["is_washout"])
        if first["assignment"] == arm:
            return seed
    raise AssertionError(f"không tìm được seed có khối đo đầu tiên {arm}")


def test_schedule_materializes_every_block_as_an_assignment_event(client):
    """POST /schedule vẽ lịch TRƯỚC phát sóng và materialize TOÀN BỘ lịch vào
    bảng chỉ-ghi-thêm: mỗi khối (kể cả washout) đúng một dòng, khớp offset và
    nhánh gán. Đây là bản gốc để đối chiếu về sau — experiment_block còn sửa
    được (override_count, excluded_reason), bảng này thì không."""
    session = make_session(client)
    sid = session["session_id"]
    body = schedule(client, sid, seed=11)

    store = client.app.state.store
    events = store.list_assignment_events(sid)
    assert len(events) == len(body["blocks"]), "thiếu/thừa sự kiện gán so với lịch"
    assert [e["block_idx"] for e in events] == [b["block_index"] for b in body["blocks"]]
    assert [e["assignment"] for e in events] == [b["assignment"] for b in body["blocks"]]
    assert [e["block_start_s"] for e in events] == [b["start_offset_s"] for b in body["blocks"]]
    assert [e["block_end_s"] for e in events] == [b["end_offset_s"] for b in body["blocks"]]
    assert {e["design_hash"] for e in events} == {body["design_hash"]}


def test_redraw_appends_a_second_committed_schedule(client):
    """Sinh lại lịch khi phiên chưa phát là hợp lệ — và KHÔNG được xóa lượt rút
    trước: cả hai lượt còn nguyên, mỗi lượt gắn design_hash của chính nó."""
    session = make_session(client)
    sid = session["session_id"]
    first = schedule(client, sid, seed=11)
    second = schedule(client, sid, seed=12)
    assert first["design_hash"] != second["design_hash"]

    store = client.app.state.store
    events = store.list_assignment_events(sid)
    assert {e["design_hash"] for e in events} == {first["design_hash"], second["design_hash"]}
    assert len(events) == len(first["blocks"]) + len(second["blocks"])
    # phiên hiện chạy dưới lượt rút SAU — trạng thái operator phải nói đúng thế
    state = client.get(f"/sessions/{sid}/state").json()
    assert state["design_hash"] == second["design_hash"]


def test_design_hash_is_published_before_broadcast_and_operator_only(client):
    """Hash cam kết thiết kế đi kèm phản hồi lịch, lưu vào phiên, hiện ở state
    vai operator — và TUYỆT ĐỐI không lọt vào payload vai host (quy tắc L6:
    nó là vân tay của cơ chế gán)."""
    make_product(client, "P1")
    session = make_session(client)
    sid = session["session_id"]
    body = schedule(client, sid, seed=11)
    assert len(body["design_hash"]) == 64
    assert set(body["design_hash"]) <= set("0123456789abcdef")

    detail = client.get(f"/sessions/{sid}").json()
    assert detail["design"]["design_hash"] == body["design_hash"]

    client.post(f"/sessions/{sid}/start")
    operator = client.get(f"/sessions/{sid}/state").json()
    assert operator["design_hash"] == body["design_hash"]

    host = client.get(f"/sessions/{sid}/state", params={"role": "host"}).json()
    assert "design_hash" not in host
    assert "seed" not in host


def test_session_without_schedule_has_no_design_hash(client):
    """Không có lịch thì không có cam kết — câu trả lời trung thực là None,
    không phải hash tính lại sau khi phiên đã xong (nó không chứng minh gì)."""
    session = make_session(client)
    state = client.get(f"/sessions/{session['session_id']}/state").json()
    assert state["design_hash"] is None


def test_execute_and_override_write_exposure_events(client):
    """Mỗi hành động của bàn để lại một dòng phơi nhiễm chỉ-ghi-thêm, kèm nguồn
    ('model' cho hệ thống, 'human' cho can thiệp tay), sản phẩm và chỉ số khối —
    tách khỏi intervention_log (bảng còn sửa được)."""
    make_product(client, "P1")
    session = make_session(client)
    sid = session["session_id"]
    seed_on = first_measurement_seed(client, sid, "ON")
    client.post(f"/sessions/{sid}/schedule", json={"seed": seed_on})
    client.post(f"/sessions/{sid}/start")

    assert client.post(f"/sessions/{sid}/actions/execute", json={}).status_code == 200
    r = client.post(
        f"/sessions/{sid}/actions/override",
        json={"product_id": "P1", "reason": "hết hàng"},
    )
    assert r.status_code == 200, r.text
    r = client.post(f"/sessions/{sid}/actions/override", json={"reason": "sai giá"})
    assert r.status_code == 200, r.text

    store = client.app.state.store
    events = store.list_exposure_events(sid)
    assert [e["event_type"] for e in events] == ["pin", "pin", "unpin"]
    assert [e["source"] for e in events] == ["model", "human", "human"]
    assert events[0]["product_id"] == "P1"
    assert events[2]["product_id"] is None
    assert all(e["block_idx"] == 0 for e in events), "cả ba hành động rơi trong khối đầu"
    # ack_latency_ms chưa đo được (bàn chưa gửi client_ts) — NULL, không phải 0
    assert all(e["ack_latency_ms"] is None for e in events)


def test_override_outside_any_block_is_still_recorded(client):
    """Can thiệp tay khi phiên chưa phát rơi ngoài mọi khối: dòng phơi nhiễm
    vẫn được ghi với block_idx = None (flag-don't-drop), không bị bỏ im lặng."""
    make_product(client, "P1")
    session = make_session(client)
    sid = session["session_id"]
    schedule(client, sid, seed=11)
    r = client.post(
        f"/sessions/{sid}/actions/override",
        json={"product_id": "P1", "reason": "hết hàng"},
    )
    assert r.status_code == 200, r.text

    events = client.app.state.store.list_exposure_events(sid)
    assert len(events) == 1
    assert events[0]["block_idx"] is None
    assert events[0]["source"] == "human"


def test_report_compliance_reads_the_event_tables(client):
    """Tỷ lệ tuân thủ trong báo cáo lấy từ hai bảng sự kiện khi có dữ liệu.
    Ghim của hệ thống trong khối BẬT tính là tuân thủ; ghim tay thì không —
    đó chính là phần bất tuân mà LATE dùng công cụ để xử lý."""
    make_product(client, "P1")
    session = make_session(client)
    sid = session["session_id"]
    seed_on = first_measurement_seed(client, sid, "ON")
    client.post(f"/sessions/{sid}/schedule", json={"seed": seed_on})
    client.post(f"/sessions/{sid}/start")
    assert client.post(f"/sessions/{sid}/actions/execute", json={}).status_code == 200

    store = client.app.state.store
    n_on = sum(1 for b in store.get_blocks(sid) if b["assignment"] == "ON")
    comp = client.get(f"/sessions/{sid}/report").json()["compliance"]
    assert comp["on_blocks"] == n_on
    assert comp["on_blocks_with_pin"] == 1
    assert comp["compliance_rate"] == pytest.approx(1 / n_on)


def test_report_compliance_falls_back_for_pre_q3_sessions(client):
    """Phiên cũ (không có dòng nào trong hai bảng sự kiện) vẫn phải ra số: rơi
    về đường intervention_log. Im lặng còn tệ hơn số cũ — nhưng hai nguồn không
    được TRỘN, nên fallback là toàn-bộ-hoặc-không cho mỗi phiên."""
    make_product(client, "P1")
    session = make_session(client)
    sid = session["session_id"]
    seed_on = first_measurement_seed(client, sid, "ON")
    client.post(f"/sessions/{sid}/schedule", json={"seed": seed_on})
    client.post(f"/sessions/{sid}/start")
    assert client.post(f"/sessions/{sid}/actions/execute", json={}).status_code == 200

    # mô phỏng phiên tiền-Q3: hai bảng sự kiện trống, intervention_log còn nguyên
    store = client.app.state.store
    store._assignment_events.pop(sid, None)
    store._exposure_events.pop(sid, None)

    n_on = sum(1 for b in store.get_blocks(sid) if b["assignment"] == "ON")
    comp = client.get(f"/sessions/{sid}/report").json()["compliance"]
    assert comp["on_blocks"] == n_on
    assert comp["on_blocks_with_pin"] == 1
    assert comp["compliance_rate"] == pytest.approx(1 / n_on)


def test_q3_session_with_no_exposure_reports_zero_not_the_legacy_number(client):
    """Phiên sinh lịch sau gói Q3 mà bàn không ghim gì có dấu vết ĐẦY ĐỦ và nói
    'không có phơi nhiễm nào' — tuân thủ 0%, không rơi về intervention_log. Nếu
    chuyển nguồn theo 'bảng phơi nhiễm rỗng' thì một dòng lạ trong log cũ sẽ
    lấn át dấu vết mới, tức là trả lời một câu hỏi khác."""
    make_product(client, "P1")
    session = make_session(client)
    sid = session["session_id"]
    seed_on = first_measurement_seed(client, sid, "ON")
    client.post(f"/sessions/{sid}/schedule", json={"seed": seed_on})
    client.post(f"/sessions/{sid}/start")

    store = client.app.state.store
    blocks = store.get_blocks(sid)
    on_block = next(b for b in blocks if b["assignment"] == "ON")
    # một dòng CHỈ có trong log cũ — đường Q3 phải bỏ qua nó
    store.add_intervention(
        sid,
        {
            "action_id": "legacy-1",
            "block_id": on_block["block_id"],
            "ts": on_block["start_ts"],
            "client_ts": None,
            "action_type": "pin",
            "product_id": "P1",
            "source": "model",
            "inner_propensity": 0.5,
            "candidates_json": None,
            "executed": True,
            "override_reason": None,
            "seconds_since_last_switch": 1.0,
        },
    )

    comp = client.get(f"/sessions/{sid}/report").json()["compliance"]
    assert comp["on_blocks_with_pin"] == 0
    assert comp["compliance_rate"] == 0.0
    assert comp["n_interventions"] == 1, (
        "log cũ vẫn được báo cáo, chỉ không dùng để suy ra tuân thủ"
    )


def test_demo_sessions_leave_the_same_event_trail_as_the_desk(client):
    """Bộ seed demo đóng vai bàn điều khiển nên phải để lại đúng dấu vết ấy:
    có sự kiện gán và sự kiện phơi nhiễm. Nếu không, demo âm thầm chạy đường
    tiền-Q3 và đường mới không bao giờ được thấy đầu-cuối."""
    r = client.post("/demo/seed", json={"n_sessions": 1})
    assert r.status_code == 200, r.text
    sid = r.json()["session_ids"][0]

    store = client.app.state.store
    assert store.list_assignment_events(sid), "demo thiếu sự kiện gán"
    exposures = store.list_exposure_events(sid)
    assert exposures, "demo thiếu sự kiện phơi nhiễm"
    assert all(e["source"] == "model" for e in exposures)
    assert all(e["event_type"] == "pin" for e in exposures)
    # khối được ghim phải là khối BẬT — demo không được làm nhiễm nhánh đối chứng
    on_idx = {b["block_index"] for b in store.get_blocks(sid) if b["assignment"] == "ON"}
    assert {e["block_idx"] for e in exposures} <= on_idx
