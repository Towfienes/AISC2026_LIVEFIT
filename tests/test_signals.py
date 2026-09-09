"""Signal coverage matrix: the honest answer to "can it measure any video?"."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.core.signals import assess


def cap(cov, name):
    return next(c for c in cov.capabilities if c.name.startswith(name))


def test_own_full_session_unlocks_everything_but_orders():
    cov = assess(
        has_schedule=True,
        n_ticks=100,
        n_ticks_with_viewers=100,
        tick_coverage_share=0.95,
        n_comments=50,
        n_clicks=20,
        n_orders=0,
    )
    assert cap(cov, "thí nghiệm").status == "ok"
    assert cap(cov, "tỷ lệ nhấp").status == "ok"
    assert cap(cov, "đối soát").status == "missing"


def test_external_vod_gets_observational_capabilities_only():
    """A YouTube VOD of someone else's live: comments only. The matrix must
    say EXACTLY what that supports — radar yes, experiment impossible."""
    cov = assess(
        has_schedule=False,
        n_ticks=0,
        n_ticks_with_viewers=0,
        tick_coverage_share=0.0,
        n_comments=500,
        n_clicks=0,
        n_orders=0,
        analysis_only=True,
    )
    assert cap(cov, "radar").status == "ok"
    assert cap(cov, "thí nghiệm").status == "missing"
    assert "ngược thời gian" in next(s for s in cov.signals if s.name == "schedule").detail
    assert cap(cov, "tỷ lệ nhấp").status == "missing"


def test_degraded_telemetry_degrades_dependent_capabilities():
    cov = assess(
        has_schedule=True,
        n_ticks=20,
        n_ticks_with_viewers=20,
        tick_coverage_share=0.5,
        n_comments=10,
        n_clicks=5,
        n_orders=0,
    )
    assert cap(cov, "nhịp phiên").status == "degraded"
    assert cap(cov, "thí nghiệm").status == "degraded"


def test_no_shortlinks_means_ctr_is_declared_unmeasurable():
    cov = assess(
        has_schedule=True,
        n_ticks=100,
        n_ticks_with_viewers=100,
        tick_coverage_share=1.0,
        n_comments=10,
        n_clicks=0,
        n_orders=0,
    )
    assert cap(cov, "tỷ lệ nhấp").status == "missing"
    assert "link đo" in next(s for s in cov.signals if s.name == "clicks").detail


def test_comment_tempo_ticks_are_not_counted_as_viewer_telemetry():
    """Regression, live-fire 10/09/2026 (`docs/benchmarks/live-fire-da-nguon.md`).

    A replay analysis writes one tick per 30 s to carry the comment tempo and
    fills ``viewers`` with a placeholder 0.0 — a finished VOD does not expose
    concurrent viewers. Grading those rows as telemetry made the matrix report
    "nhịp phiên (người xem theo thời gian): ok" on a session whose viewer
    column is entirely placeholder. The count of rows is not the question; the
    count of rows carrying a viewer number is.
    """
    cov = assess(
        has_schedule=False,
        n_ticks=141,  # 70 minutes of video at one bucket per 30 s
        n_ticks_with_viewers=0,  # ...none of which knows how many people watched
        tick_coverage_share=1.0,
        n_comments=23,
        n_clicks=0,
        n_orders=0,
        analysis_only=True,
    )
    ticks = next(s for s in cov.signals if s.name == "ticks")
    assert ticks.status == "missing"
    assert "nhịp bình luận" in ticks.detail.lower()
    assert cap(cov, "nhịp phiên").status == "missing"
    # Comments are real, so the capability they unlock stays available.
    assert cap(cov, "radar").status == "ok"


def test_partially_missing_viewer_numbers_degrade_the_ticks_signal():
    """Half the buckets carrying a viewer count is degraded telemetry, not ok."""
    cov = assess(
        has_schedule=True,
        n_ticks=100,
        n_ticks_with_viewers=50,
        tick_coverage_share=1.0,
        n_comments=10,
        n_clicks=5,
        n_orders=0,
    )
    ticks = next(s for s in cov.signals if s.name == "ticks")
    assert ticks.status == "degraded"
    assert "50/100" in ticks.detail
    assert cap(cov, "nhịp phiên").status == "degraded"


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


def test_signals_endpoint_end_to_end(client):
    sid = client.post(
        "/sessions",
        json={
            "platform": "youtube",
            "mode": "auto",
            "planned_duration_min": 60,
        },
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 3})
    client.post(f"/sessions/{sid}/start")
    client.post(f"/sessions/{sid}/ticks", json={"viewers": 50})

    res = client.get(f"/sessions/{sid}/signals")
    assert res.status_code == 200
    body = res.json()
    names = {s["name"] for s in body["signals"]}
    assert names == {"schedule", "ticks", "comments", "clicks", "orders"}
    schedule = next(s for s in body["signals"] if s["name"] == "schedule")
    assert schedule["status"] == "ok"
    exp = next(c for c in body["capabilities"] if "thí nghiệm" in c["name"])
    assert exp["status"] == "missing"  # no clicks yet -> declared, not hidden


def test_signals_endpoint_bad_id_is_404(client):
    assert client.get("/sessions/nope/signals").status_code == 404


def test_signals_endpoint_refuses_to_claim_viewers_from_tempo_only_ticks(client):
    """End-to-end guard for the live-fire 10/09/2026 finding.

    Ticks that carry only a comment rate — exactly what
    ``POST /replays/youtube`` writes for a finished VOD — must never make the
    endpoint announce the viewers-over-time capability.
    """
    sid = client.post(
        "/sessions",
        json={"platform": "replay", "mode": "auto", "planned_duration_min": 5},
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 3})
    client.post(f"/sessions/{sid}/start")
    for rate in (4.0, 8.0, 2.0):
        assert (
            client.post(
                f"/sessions/{sid}/ticks", json={"viewers": 0.0, "comment_rate": rate}
            ).status_code
            < 400
        )

    body = client.get(f"/sessions/{sid}/signals").json()
    ticks = next(s for s in body["signals"] if s["name"] == "ticks")
    assert ticks["status"] == "missing"
    rhythm = next(c for c in body["capabilities"] if c["name"].startswith("nhịp phiên"))
    assert rhythm["status"] == "missing"
    ctr = next(c for c in body["capabilities"] if c["name"].startswith("tỷ lệ nhấp"))
    assert ctr["status"] == "missing"
