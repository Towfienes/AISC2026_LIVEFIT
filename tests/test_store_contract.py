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
from datetime import UTC, datetime, timedelta

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
def test_click_validity_columns_round_trip_and_default_valid(name, store):
    """Migration 0004 contract: both backends store is_valid/invalid_reason/
    ua_class, and a click written WITHOUT the fields (legacy caller, demo
    seeder) defaults to a VALID click — exactly like the SQL DEFAULT."""
    if name == "postgres":
        pytest.importorskip("psycopg")
    sid = store.create_session(_session_row())["session_id"]

    flagged = store.add_click(
        sid,
        {
            "click_id": str(uuid.uuid4()),
            "block_id": None,
            "ts": NOW,
            "product_id": None,
            "shortlink_code": None,
            "dedup_hash": "abc123",
            "is_valid": False,
            "invalid_reason": "givt_ua",
            "ua_class": "givt",
        },
    )
    assert flagged["is_valid"] is False
    assert flagged["invalid_reason"] == "givt_ua"
    assert flagged["ua_class"] == "givt"

    legacy = store.add_click(
        sid,
        {
            "click_id": str(uuid.uuid4()),
            "block_id": None,
            "ts": NOW,
            "product_id": None,
            "shortlink_code": None,
            "dedup_hash": None,
        },
    )
    assert legacy["is_valid"] is True
    assert legacy["invalid_reason"] is None

    listed = {c["click_id"]: c for c in store.list_clicks(sid)}
    assert listed[flagged["click_id"]]["is_valid"] is False
    assert listed[legacy["click_id"]]["is_valid"] is True


@pytest.mark.parametrize(("name", "store"), list(_stores()), ids=lambda v: getattr(v, "backend", v))
def test_clicks_for_fingerprint_is_narrow_in_every_backend(name, store):
    """The redirect classifies validity from ONE fingerprint's history, so the
    store must hand back exactly that slice — same rows, same order, in both
    backends. A backend that returned the whole session would silently make
    every redirect O(clicks-so-far) and would let clicks from another viewer
    or another shortlink trip the refractory rule."""
    if name == "postgres":
        pytest.importorskip("psycopg")
    store.create_product(_product())
    sid = store.create_session(_session_row())["session_id"]
    code_a = f"fp-a-{name}-{NOW.timestamp():.0f}"
    code_b = f"fp-b-{name}-{NOW.timestamp():.0f}"
    store.create_shortlink(_link(code_a))
    store.create_shortlink(_link(code_b))

    def _click(dedup_hash, code, secs):
        return store.add_click(
            sid,
            {
                "click_id": str(uuid.uuid4()),
                "block_id": None,
                "ts": NOW + timedelta(seconds=secs),
                "product_id": "P1",
                "shortlink_code": code,
                "dedup_hash": dedup_hash,
            },
        )["click_id"]

    mine_1 = _click("hash-me", code_a, 1)
    mine_2 = _click("hash-me", code_a, 2)
    _click("hash-me", code_b, 3)  # same viewer, OTHER shortlink
    _click("hash-other", code_a, 4)  # other viewer, same shortlink

    got = store.list_clicks_for_fingerprint(sid, "hash-me", code_a)
    assert [c["click_id"] for c in got] == [mine_1, mine_2], "đúng slice, đúng thứ tự theo ts"
    assert len(store.list_clicks(sid)) == 4, "flag-don't-drop: mọi click vẫn nằm trong phiên"
    assert store.list_clicks_for_fingerprint(sid, "khong-ton-tai", code_a) == []


def _assignment_rows(design_hash: str = "hash-a") -> list[dict]:
    return [
        {
            "block_idx": 0,
            "assignment": "ON",
            "block_start_s": 0,
            "block_end_s": 600,
            "design_hash": design_hash,
            "created_at": NOW,
        },
        {
            "block_idx": 1,
            "assignment": None,  # washout
            "block_start_s": 600,
            "block_end_s": 660,
            "design_hash": design_hash,
            "created_at": NOW,
        },
        {
            "block_idx": 2,
            "assignment": "OFF",
            "block_start_s": 660,
            "block_end_s": 960,
            "design_hash": design_hash,
            "created_at": NOW,
        },
    ]


@pytest.mark.parametrize(("name", "store"), list(_stores()), ids=lambda v: getattr(v, "backend", v))
def test_assignment_events_round_trip_in_every_backend(name, store):
    """Migration 0006: the WHOLE schedule (washout rows included) is
    materialized once at draw time and comes back identically from both
    backends, ordered by (created_at, block_idx)."""
    if name == "postgres":
        pytest.importorskip("psycopg")
    sid = store.create_session(_session_row())["session_id"]

    written = store.add_assignment_events(sid, _assignment_rows())
    assert len(written) == 3
    rows = store.list_assignment_events(sid)
    assert [r["block_idx"] for r in rows] == [0, 1, 2]
    assert [r["assignment"] for r in rows] == ["ON", None, "OFF"]
    assert rows[0]["block_start_s"] == 0
    assert rows[0]["block_end_s"] == 600
    assert {r["design_hash"] for r in rows} == {"hash-a"}
    assert all(r["id"] for r in rows), "mỗi sự kiện gán có id riêng"


@pytest.mark.parametrize(("name", "store"), list(_stores()), ids=lambda v: getattr(v, "backend", v))
def test_assignment_events_are_append_only_across_redraws(name, store):
    """Sinh lại lịch (được phép khi phiên chưa phát) KHÔNG xóa lượt rút trước:
    hai lượt cùng tồn tại, phân biệt bằng design_hash. Không có đường nào trong
    store để sửa hay xóa row cũ — đó là toàn bộ giá trị của dấu vết kiểm chứng."""
    if name == "postgres":
        pytest.importorskip("psycopg")
    sid = store.create_session(_session_row())["session_id"]

    store.add_assignment_events(sid, _assignment_rows("hash-a"))
    store.add_assignment_events(sid, _assignment_rows("hash-b"))
    rows = store.list_assignment_events(sid)
    assert len(rows) == 6, "lượt rút cũ phải còn nguyên"
    assert sorted({r["design_hash"] for r in rows}) == ["hash-a", "hash-b"]
    per_hash = [r["block_idx"] for r in rows if r["design_hash"] == "hash-b"]
    assert per_hash == [0, 1, 2]


@pytest.mark.parametrize(("name", "store"), list(_stores()), ids=lambda v: getattr(v, "backend", v))
def test_exposure_events_round_trip_in_every_backend(name, store):
    """Exposure rows keep source/product/block_idx and come back ts-ordered.
    A row outside every block (block_idx None) is STORED, not dropped."""
    if name == "postgres":
        pytest.importorskip("psycopg")
    store.create_product(_product())
    sid = store.create_session(_session_row())["session_id"]

    store.add_exposure_event(
        sid,
        {
            "block_idx": 0,
            "event_type": "pin",
            "product_id": "P1",
            "ts_utc": NOW + timedelta(seconds=10),
            "ack_latency_ms": 120,
            "source": "model",
        },
    )
    store.add_exposure_event(
        sid,
        {
            "block_idx": None,
            "event_type": "unpin",
            "product_id": None,
            "ts_utc": NOW + timedelta(seconds=20),
            "ack_latency_ms": None,
            "source": "human",
        },
    )
    rows = store.list_exposure_events(sid)
    assert [r["event_type"] for r in rows] == ["pin", "unpin"]
    assert rows[0]["source"] == "model"
    assert rows[0]["product_id"] == "P1"
    assert rows[0]["ack_latency_ms"] == 120
    assert rows[1]["block_idx"] is None, "hành động ngoài khối vẫn được ghi (flag-don't-drop)"
    assert rows[1]["ack_latency_ms"] is None


@pytest.mark.parametrize(("name", "store"), list(_stores()), ids=lambda v: getattr(v, "backend", v))
def test_event_tables_expose_no_mutation_method(name, store):
    """APPEND-ONLY cưỡng chế ở tầng ứng dụng: không backend nào được có method
    sửa/xóa hai bảng sự kiện. Một dấu vết kiểm chứng sửa được thì vô giá trị —
    row đã sửa và row bị can thiệp trông y hệt nhau về sau."""
    if name == "postgres":
        pytest.importorskip("psycopg")
    for table in ("assignment_event", "assignment_events", "exposure_event", "exposure_events"):
        for verb in ("update", "delete", "remove", "clear", "set", "edit"):
            attr = f"{verb}_{table}"
            assert not hasattr(store, attr), (
                f"{type(store).__name__}.{attr} tồn tại — bảng {table} phải chỉ-ghi-thêm"
            )
    # ...and the append/read methods that MUST exist.
    for attr in (
        "add_assignment_events",
        "list_assignment_events",
        "add_exposure_event",
        "list_exposure_events",
    ):
        assert callable(getattr(store, attr)), f"thiếu {attr}"


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
