"""End-to-end ingest: a REAL ApiSink posting into the REAL FastAPI app.

This is the test that was missing when the sink sent ``text_scrubbed`` while
the API required ``text``: each side passed its own unit tests, yet not one
live comment could travel between them (every POST answered 422 and was
dropped). Here the sink's HTTP client is wired straight into the ASGI app, so
the two contracts are exercised against each other:

- comment/tick payloads built by the sink are accepted by the routes,
- the source timestamp (``ts_utc``) is stored and drives block attribution,
- re-sending (runner restart, spool replay) creates no duplicates,
- INGEST_TOKEN protects the write path and the sink's bearer header opens it,
- a spooled record is delivered later by ``spool_replay``.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import get_settings
from livelift.ingest.base import ApiSink, RawComment, RawTick
from livelift.ingest.spool_replay import replay_file

API_BASE = "http://api.test"


@pytest.fixture
def app_env():
    store = InMemoryStore()
    app = create_app(store=store)
    with TestClient(app) as tc:  # runs lifespan -> app.state.store is set
        yield app, store, tc


def _sink_for(app, session_id: str, **kwargs) -> tuple[ApiSink, httpx.AsyncClient]:
    """A real ApiSink whose httpx client talks ASGI directly to the app."""
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=API_BASE)
    kwargs.setdefault("spool_dir", None)
    kwargs.setdefault("token", "")
    sink = ApiSink(
        api_url=API_BASE, session_id=session_id, client=client, base_delay_s=0.0, **kwargs
    )
    return sink, client


def _live_session(tc: TestClient) -> tuple[str, datetime, list[dict]]:
    """Create + schedule + start a session; returns (id, start_ts, blocks)."""
    sid = tc.post(
        "/sessions",
        json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60},
    ).json()["session_id"]
    sched = tc.post(f"/sessions/{sid}/schedule", json={"seed": 7})
    assert sched.status_code == 200, sched.text
    started = tc.post(f"/sessions/{sid}/start")
    assert started.status_code == 200, started.text
    start_ts = datetime.fromisoformat(started.json()["start_ts"])
    return sid, start_ts, sched.json()["blocks"]


def _post_comment(app, sid: str, comment: RawComment, **sink_kwargs) -> bool:
    async def run() -> bool:
        sink, client = _sink_for(app, sid, **sink_kwargs)
        try:
            return await sink.post_comment(comment)
        finally:
            await client.aclose()

    return asyncio.run(run())


def _post_tick(app, sid: str, tick: RawTick, **sink_kwargs) -> bool:
    async def run() -> bool:
        sink, client = _sink_for(app, sid, **sink_kwargs)
        try:
            return await sink.post_tick(tick)
        finally:
            await client.aclose()

    return asyncio.run(run())


def test_comment_travels_sink_to_store_with_source_ts_and_ext_id(app_env):
    app, store, tc = app_env
    sid, start_ts, blocks = _live_session(tc)

    # Source timestamp inside the SECOND block while the wall clock still sits
    # at ~offset 0: attribution must follow the platform time, not arrival.
    second_block = blocks[1]
    ts = start_ts + timedelta(seconds=second_block["start_offset_s"] + 10)
    comment = RawComment(
        platform="youtube",
        ext_id="LCC.e2e-1",
        ts_utc=ts,
        text="chốt đơn nhé, sđt 0901234567",
    )
    assert _post_comment(app, sid, comment) is True

    rows = store.list_comments(sid)
    assert len(rows) == 1
    row = rows[0]
    assert "0901234567" not in row["text_scrubbed"]  # hard rule 1
    assert "[SĐT]" in row["text_scrubbed"]
    assert row["ts"] == ts  # source timestamp kept, not server arrival time
    assert row["platform"] == "youtube"
    assert row["ext_id"] == "LCC.e2e-1"
    assert row["block_id"] == second_block["block_id"]  # attributed by ts_utc

    # Re-send (runner restart / spool replay): idempotent, no duplicate.
    assert _post_comment(app, sid, comment) is True
    assert len(store.list_comments(sid)) == 1

    # A different comment still inserts.
    other = RawComment("youtube", "LCC.e2e-2", ts, "còn màu đen không")
    assert _post_comment(app, sid, other) is True
    assert len(store.list_comments(sid)) == 2


def test_tick_travels_sink_to_store_and_rebuckets_by_source_ts(app_env):
    app, store, tc = app_env
    sid, start_ts, _ = _live_session(tc)

    ts = start_ts + timedelta(seconds=95)  # bucket [90, 120) on the start grid
    tick = RawTick(platform="youtube", ts_utc=ts, viewers=137.0)
    assert _post_tick(app, sid, tick) is True

    ticks = store.list_ticks(sid)
    assert len(ticks) == 1
    assert ticks[0]["viewers"] == 137.0
    assert ticks[0]["ts_bucket"] == start_ts + timedelta(seconds=90)

    # Same bucket re-sent -> upsert, not a duplicate row.
    assert _post_tick(app, sid, RawTick("youtube", ts, 140.0)) is True
    ticks = store.list_ticks(sid)
    assert len(ticks) == 1
    assert ticks[0]["viewers"] == 140.0


def test_ingest_token_gates_writes_and_spool_replay_recovers(app_env, tmp_path, monkeypatch):
    app, store, tc = app_env
    sid, start_ts, _ = _live_session(tc)

    monkeypatch.setenv("INGEST_TOKEN", "bi-mat-e2e")
    get_settings.cache_clear()
    try:
        comment = RawComment(
            platform="youtube",
            ext_id="LCC.auth-1",
            ts_utc=start_ts + timedelta(seconds=5),
            text="giữ giúp em, sđt 0901234567",
        )

        # No token -> 401 -> not stored, but spooled locally (scrubbed only).
        assert _post_comment(app, sid, comment, token="", spool_dir=tmp_path) is False
        assert store.list_comments(sid) == []
        spool_file = tmp_path / f"{sid}.jsonl"
        assert spool_file.is_file()
        assert "0901234567" not in spool_file.read_text(encoding="utf-8")

        # Correct bearer token -> accepted.
        with_token = RawComment(
            platform="youtube",
            ext_id="LCC.auth-2",
            ts_utc=start_ts + timedelta(seconds=6),
            text="ship về đâu vậy",
        )
        assert _post_comment(app, sid, with_token, token="bi-mat-e2e") is True
        assert len(store.list_comments(sid)) == 1

        # Reads stay open without a token.
        assert tc.get(f"/sessions/{sid}/comments").status_code == 200

        # Backfill: spool_replay delivers the spooled comment with the token…
        async def run_replay() -> tuple[int, int]:
            client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app))
            try:
                return await replay_file(spool_file, API_BASE, token="bi-mat-e2e", client=client)
            finally:
                await client.aclose()

        n_ok, n_failed = asyncio.run(run_replay())
        assert (n_ok, n_failed) == (1, 0)
        stored = {c["ext_id"] for c in store.list_comments(sid)}
        assert stored == {"LCC.auth-1", "LCC.auth-2"}

        # …and replaying the same file again duplicates nothing (idempotency).
        n_ok, n_failed = asyncio.run(run_replay())
        assert (n_ok, n_failed) == (1, 0)
        assert len(store.list_comments(sid)) == 2
    finally:
        monkeypatch.delenv("INGEST_TOKEN", raising=False)
        get_settings.cache_clear()


def test_wrong_token_is_rejected_in_vietnamese(app_env, monkeypatch):
    app, store, tc = app_env
    sid, _, _ = _live_session(tc)
    monkeypatch.setenv("INGEST_TOKEN", "dung-token")
    get_settings.cache_clear()
    try:
        r = tc.post(
            f"/sessions/{sid}/ticks",
            json={"viewers": 5},
            headers={"Authorization": "Bearer sai-token"},
        )
        assert r.status_code == 401
        assert "token ingest" in r.json()["detail"]
    finally:
        monkeypatch.delenv("INGEST_TOKEN", raising=False)
        get_settings.cache_clear()


def test_spool_replay_reports_malformed_lines(app_env, tmp_path):
    app, _, tc = app_env
    sid, start_ts, _ = _live_session(tc)
    good = {
        "kind": "tick",
        "path": f"/sessions/{sid}/ticks",
        "payload": {
            "platform": "youtube",
            "ts_utc": (start_ts + timedelta(seconds=35)).isoformat(),
            "viewers": 9.0,
        },
    }
    spool_file = tmp_path / f"{sid}.jsonl"
    spool_file.write_text(json.dumps(good) + "\nkhông-phải-json\n", encoding="utf-8")

    async def run_replay() -> tuple[int, int]:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app))
        try:
            return await replay_file(spool_file, API_BASE, client=client)
        finally:
            await client.aclose()

    n_ok, n_failed = asyncio.run(run_replay())
    assert (n_ok, n_failed) == (1, 1)
    assert tc.get(f"/sessions/{sid}/ticks").json()[0]["viewers"] == 9.0
