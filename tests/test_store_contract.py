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
from datetime import UTC, datetime

import pytest

from livelift.api.store import InMemoryStore, ShortlinkCodeTakenError

NOW = datetime.now(UTC)


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
