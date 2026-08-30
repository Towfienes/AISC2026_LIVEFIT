"""API robustness regressions (incident 27/08).

A malformed session id used to reach Postgres verbatim and blow up as a 500
with an ASGI traceback; a typo in a URL is a client mistake and must answer
with the same Vietnamese 404 as a well-formed but unknown id.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore

ABSENT_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize(
    "path",
    [
        "/sessions/{sid}",
        "/sessions/{sid}/state",
        "/sessions/{sid}/report",
        "/sessions/{sid}/comments",
        "/sessions/{sid}/ticks",
        "/sessions/{sid}/schedule",
    ],
)
def test_malformed_session_id_is_404_not_500(client, path):
    res = client.get(path.format(sid="nope-123"))
    assert res.status_code == 404, f"{path} -> {res.status_code}: {res.text[:200]}"
    assert "phiên" in res.json()["detail"].lower()


@pytest.mark.parametrize(
    "path",
    [
        "/sessions/{sid}",
        "/sessions/{sid}/state",
        "/sessions/{sid}/report",
    ],
)
def test_absent_but_valid_uuid_is_also_404(client, path):
    res = client.get(path.format(sid=ABSENT_UUID))
    assert res.status_code == 404


def test_schedule_is_persisted_into_design_for_the_qc_gate(client):
    """The QC block_integrity check compares experiment_block rows against
    design['blocks']; without it the gate can never pass (incident 27/08)."""
    sid = client.post(
        "/sessions",
        json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60},
    ).json()["session_id"]
    posted = client.post(f"/sessions/{sid}/schedule", json={"seed": 7}).json()
    session = client.get(f"/sessions/{sid}").json()

    design_blocks = (session.get("design") or {}).get("blocks")
    assert design_blocks, "design['blocks'] trống — mất dấu vết kiểm chứng"
    assert len(design_blocks) == len(posted["blocks"])
    for stored, drawn in zip(design_blocks, posted["blocks"], strict=True):
        assert stored["block_index"] == drawn["block_index"]
        assert stored["assignment"] == drawn["assignment"]
        assert stored["is_washout"] == drawn["is_washout"]


def test_qc_block_integrity_passes_on_an_api_created_session(client):
    """End-to-end: a session scheduled through the API must satisfy the gate."""
    from livelift.core.quality import check_block_integrity

    sid = client.post(
        "/sessions",
        json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60},
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 11})
    design_blocks = (client.get(f"/sessions/{sid}").json()["design"] or {})["blocks"]
    recorded = client.get(f"/sessions/{sid}/schedule").json()

    res = check_block_integrity(design_blocks, recorded)
    assert res.passed, res.detail
