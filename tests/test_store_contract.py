"""Store-contract tests: both backends must agree on behavior.

Incident 27/08: ``/demo/seed`` returned 500 on the second call because
InMemoryStore silently overwrote a duplicate shortlink code while
PostgresStore raised a UniqueViolation. Tests only exercised the in-memory
backend, so the divergence never showed up until it hit the real database.

These tests pin the contract itself. The postgres half is marked ``db`` and
runs only when a database is available (``docker compose up -d db``).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest

from livelift.api.store import InMemoryStore, ShortlinkCodeTakenError

NOW = datetime.now(UTC)


def _session_row() -> dict:
    return {
        "session_id": str(uuid.uuid4()),
        "platform": "youtube",
        "title": "contract",
        "mode": "auto",
        "status": "live",
        "planned_duration_min": 60,
        "host_id": None,
        "created_at": NOW,
    }


def _comment_row(session_id: str, ext_id: str | None) -> dict:
    return {
        "comment_id": str(uuid.uuid4()),
        "session_id": session_id,
        "block_id": None,
        "ts": NOW,
        "platform": "youtube" if ext_id else None,
        "ext_id": ext_id,
        "text_scrubbed": "chốt đơn [SĐT]",
        "pii_kinds": ["phone"],
        "intent_label": "chot_don",
        "intent_confidence": 0.5,
        "sentiment": None,
    }


def _tick_row(viewers: float) -> dict:
    return {
        "ts_bucket": NOW,
        "viewers": viewers,
        "comment_rate": 1.0,
        "like_rate": 0.0,
        "click_count": 0,
        "pinned_product_id": None,
    }


def _product(pid: str = "P1") -> dict:
    return {
        "product_id": pid,
        "name": "Bình giữ nhiệt",
        "category": "test",
        "cost": 42000,
        "price": 95000,
        "stock": 10,
        "created_at": NOW,
    }


def _link(code: str, pid: str = "P1") -> dict:
    return {
        "code": code,
        "product_id": pid,
        "session_id": None,
        "target_url": "https://shop.example/p1",
        "created_at": NOW,
    }


def _stores():
    """Every available backend, so contract tests run against all of them."""
    yield "memory", InMemoryStore()
    url = os.environ.get("DATABASE_URL")
    if url:
        from livelift.api.store import PostgresStore

        yield "postgres", PostgresStore(url)


@pytest.mark.parametrize(("name", "store"), list(_stores()), ids=lambda v: getattr(v, "backend", v))
def test_duplicate_shortlink_code_rejected(name, store):
    """A duplicate code must RAISE in every backend — never overwrite.

    Shortlink codes are the operational definition of a click, so a silent
    overwrite would misattribute clicks between products.
    """
    if name == "postgres":
        pytest.importorskip("psycopg")
    store.create_product(_product())
    code = f"contract-{name}-{NOW.timestamp():.0f}"
    store.create_shortlink(_link(code))
    with pytest.raises(ShortlinkCodeTakenError):
        store.create_shortlink(_link(code))


def test_product_upsert_is_idempotent():
    """Re-creating the same product must not raise (demo re-seeding relies on it)."""
    store = InMemoryStore()
    store.create_product(_product())
    again = store.create_product({**_product(), "stock": 99})
    assert again["stock"] == 99


@pytest.mark.parametrize(("name", "store"), list(_stores()), ids=lambda v: getattr(v, "backend", v))
def test_comment_platform_ext_id_is_idempotent(name, store):
    """(platform, ext_id) is the comment idempotency key in EVERY backend: a
    duplicate delivery (runner restart, spool replay) returns the existing
    row instead of inserting a second one. Rows without ext_id (manual posts)
    are exempt."""
    if name == "postgres":
        pytest.importorskip("psycopg")
    sid = store.create_session(_session_row())["session_id"]

    first = store.add_comment(sid, _comment_row(sid, ext_id="dup-1"))
    second = store.add_comment(sid, _comment_row(sid, ext_id="dup-1"))
    assert second["comment_id"] == first["comment_id"]
    assert len(store.list_comments(sid)) == 1
    # intent_confidence (migration 0003) round-trips in every backend
    assert first["intent_confidence"] == pytest.approx(0.5)
    assert store.list_comments(sid)[0]["intent_confidence"] == pytest.approx(0.5)

    store.add_comment(sid, _comment_row(sid, ext_id="dup-2"))
    assert len(store.list_comments(sid)) == 2

    # No ext_id -> no dedup key -> both rows insert.
    store.add_comment(sid, _comment_row(sid, ext_id=None))
    store.add_comment(sid, _comment_row(sid, ext_id=None))
    assert len(store.list_comments(sid)) == 4


@pytest.mark.parametrize(("name", "store"), list(_stores()), ids=lambda v: getattr(v, "backend", v))
def test_tick_bucket_upserts_in_every_backend(name, store):
    """Re-sending a tick for an existing (session, ts_bucket) must UPDATE the
    bucket, not append a duplicate — Postgres has always done this via ON
    CONFLICT; the in-memory backend must match (spool replay relies on it)."""
    if name == "postgres":
        pytest.importorskip("psycopg")
    sid = store.create_session(_session_row())["session_id"]

    store.add_tick(sid, _tick_row(viewers=10.0))
    store.add_tick(sid, _tick_row(viewers=25.0))
    ticks = store.list_ticks(sid)
    assert len(ticks) == 1
    assert ticks[0]["viewers"] == 25.0
