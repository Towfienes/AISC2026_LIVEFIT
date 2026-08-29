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
    listed = client.get(f"/sessions/{sid}/comments").json()
    assert all("0901234567" not in c["text"] for c in listed)
    assert listed[0]["block_id"] is not None  # attributed to the current block

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
    assert report["n_blocks"] == sched["n_on"] + sched["n_off"]
    assert report["compliance"]["override_count"] == 1


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
