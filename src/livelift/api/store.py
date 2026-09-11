"""Storage backends for the API: in-memory (default) and PostgreSQL.

The :class:`Store` protocol is the single seam between routes and persistence.
``InMemoryStore`` is complete and is what tests and the zero-dependency demo
run on; ``PostgresStore`` maps the same methods onto the schema in
``src/livelift/migrations/0001_init.up.sql`` via ``psycopg_pool``. psycopg is
imported lazily so memory mode needs no database driver installed.

Concurrency model: the API runs on a single asyncio event loop and store
methods are synchronous, non-awaiting calls — for the in-memory backend every
method is therefore atomic with respect to request handlers (no lock needed).
The Postgres backend uses a connection pool; its calls block the loop briefly,
which is acceptable at pilot scale (a handful of concurrent sessions).

Pubsub: a tiny per-process asyncio broadcaster keyed by session_id feeds the
``/ws/{session_id}`` sockets. Both backends share the same broadcaster class;
a multi-process deployment would swap it for Redis pubsub behind the same
three methods.

PII note (hard rule 1): comment rows only ever carry ``text_scrubbed`` — the
store has no field, method, or log line for raw comment text.

Append-only note (migration 0006): ``assignment_event`` and ``exposure_event``
are the experiment's audit trail. Neither backend exposes an update or delete
method for them, and none may ever be added — enforcement of the same rule at
the database role level belongs to deploy.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol


def _new_id() -> str:
    return str(uuid.uuid4())


def _norm_value(v: Any) -> Any:
    """Normalize DB driver types to JSON-friendly Python types."""
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, Decimal):
        return float(v)
    return v


def _norm_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _norm_value(v) for k, v in row.items()}


# ---------------------------------------------------------------------------
# Pubsub
# ---------------------------------------------------------------------------


class Broadcaster:
    """Minimal per-process asyncio pubsub: one queue per WebSocket subscriber."""

    def __init__(self, maxsize: int = 256) -> None:
        self._maxsize = maxsize
        self._subs: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._maxsize)
        self._subs.setdefault(session_id, []).append(q)
        return q

    def unsubscribe(self, session_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        queues = self._subs.get(session_id)
        if not queues:
            return
        if q in queues:
            queues.remove(q)
        if not queues:
            self._subs.pop(session_id, None)

    def publish(self, session_id: str, message: dict[str, Any]) -> None:
        for q in list(self._subs.get(session_id, ())):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                # Slow consumer: drop its oldest message rather than blocking.
                try:
                    q.get_nowait()
                    q.put_nowait(message)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class ShortlinkCodeTakenError(Exception):
    """A shortlink code already exists.

    Shortlink codes are the operational definition of a product click, so a
    silent overwrite would misattribute clicks between products/sessions —
    an experiment-integrity bug. Both store backends must therefore REJECT a
    duplicate code rather than replace it; the API turns this into a 409.
    """


class Store(Protocol):
    """Persistence + pubsub seam used by every route module."""

    backend: str

    # products
    def create_product(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_products(self) -> list[dict[str, Any]]: ...
    def get_product(self, product_id: str) -> dict[str, Any] | None: ...

    # shortlinks
    def create_shortlink(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def get_shortlink(self, code: str) -> dict[str, Any] | None: ...

    # sessions
    def create_session(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_sessions(self) -> list[dict[str, Any]]: ...
    def get_session(self, session_id: str) -> dict[str, Any] | None: ...
    def update_session(self, session_id: str, fields: dict[str, Any]) -> dict[str, Any]: ...

    # blocks
    def save_schedule(
        self, session_id: str, block_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]: ...
    def get_blocks(self, session_id: str) -> list[dict[str, Any]]: ...
    def materialize_block_times(self, session_id: str, start_ts: datetime) -> None: ...
    def increment_override(self, block_id: str) -> None: ...

    # ticks
    def add_tick(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_ticks(self, session_id: str) -> list[dict[str, Any]]: ...

    # comments (scrubbed text only — hard rule 1)
    def add_comment(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_comments(self, session_id: str) -> list[dict[str, Any]]: ...

    # reactions (migration 0007): paid/visible audience events — superchat,
    # gift, sticker, membership, like. amount/currency carry the PUBLIC money
    # string YouTube prints in the chat frame; no author field exists here.
    def add_reaction(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_reactions(self, session_id: str) -> list[dict[str, Any]]: ...

    # clicks
    def add_click(self, session_id: str | None, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_clicks(self, session_id: str) -> list[dict[str, Any]]: ...
    def list_clicks_for_fingerprint(
        self, session_id: str, dedup_hash: str, shortlink_code: str | None
    ) -> list[dict[str, Any]]: ...

    # interventions
    def add_intervention(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_interventions(self, session_id: str) -> list[dict[str, Any]]: ...

    # assignment / exposure events — APPEND-ONLY (migration 0006).
    #
    # There is deliberately NO update_* or delete_* method for these two tables
    # in this protocol or in either backend. They are the experiment's audit
    # trail: the design as drawn before broadcast (assignment_event) and what
    # the desk actually did (exposure_event). A store that could edit them
    # would make the trail worthless — a corrected row and a tampered row look
    # identical afterwards. Corrections are expressed by APPENDING (a new
    # design draw carries a new design_hash; a wrong pin is followed by an
    # unpin), never by rewriting history (HARNESS.md §3: flag, don't edit).
    def add_assignment_events(
        self, session_id: str, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]: ...
    def list_assignment_events(self, session_id: str) -> list[dict[str, Any]]: ...
    def add_exposure_event(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_exposure_events(self, session_id: str) -> list[dict[str, Any]]: ...

    # orders
    def add_order(self, session_id: str | None, row: dict[str, Any]) -> dict[str, Any]: ...
    def list_orders(self, session_id: str) -> list[dict[str, Any]]: ...

    # pubsub
    def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]: ...
    def unsubscribe(self, session_id: str, q: asyncio.Queue[dict[str, Any]]) -> None: ...
    def publish(self, session_id: str, message: dict[str, Any]) -> None: ...

    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# In-memory backend
# ---------------------------------------------------------------------------


class InMemoryStore:
    """Complete dict-backed store. Safe for a single asyncio loop: methods
    never await, so each call is atomic w.r.t. request handlers."""

    backend = "memory"

    def __init__(self) -> None:
        self._products: dict[str, dict[str, Any]] = {}
        self._shortlinks: dict[str, dict[str, Any]] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._blocks: dict[str, list[dict[str, Any]]] = {}
        self._ticks: dict[str, list[dict[str, Any]]] = {}
        self._comments: dict[str, list[dict[str, Any]]] = {}
        # (platform, ext_id) -> stored row, per session: comment idempotency
        # (mirrors the partial unique index in migration 0002).
        self._comment_keys: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
        self._reactions: dict[str, list[dict[str, Any]]] = {}
        # (platform, ext_id) -> stored row, per session — same idempotency
        # contract as comments (mirrors the partial unique index in 0007).
        self._reaction_keys: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
        self._clicks: dict[str, list[dict[str, Any]]] = {}
        self._interventions: dict[str, list[dict[str, Any]]] = {}
        self._orders: dict[str, list[dict[str, Any]]] = {}
        # Append-only event tables (migration 0006) — written, never rewritten.
        self._assignment_events: dict[str, list[dict[str, Any]]] = {}
        self._exposure_events: dict[str, list[dict[str, Any]]] = {}
        self._broadcaster = Broadcaster()

    # -- products ----------------------------------------------------------
    def create_product(self, row: dict[str, Any]) -> dict[str, Any]:
        stored = dict(row)
        stored["margin"] = float(row["price"]) - float(row["cost"])
        self._products[row["product_id"]] = stored
        return dict(stored)

    def list_products(self) -> list[dict[str, Any]]:
        return [dict(p) for p in self._products.values()]

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        row = self._products.get(product_id)
        return dict(row) if row else None

    # -- shortlinks --------------------------------------------------------
    def create_shortlink(self, row: dict[str, Any]) -> dict[str, Any]:
        if row["code"] in self._shortlinks:
            raise ShortlinkCodeTakenError(row["code"])
        self._shortlinks[row["code"]] = dict(row)
        return dict(row)

    def get_shortlink(self, code: str) -> dict[str, Any] | None:
        row = self._shortlinks.get(code)
        return dict(row) if row else None

    # -- sessions ----------------------------------------------------------
    def create_session(self, row: dict[str, Any]) -> dict[str, Any]:
        self._sessions[row["session_id"]] = dict(row)
        return dict(row)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [dict(s) for s in self._sessions.values()]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        row = self._sessions.get(session_id)
        return dict(row) if row else None

    def update_session(self, session_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = self._sessions[session_id]
        row.update(fields)
        return dict(row)

    # -- blocks ------------------------------------------------------------
    def save_schedule(
        self, session_id: str, block_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        stored = []
        for r in block_rows:
            stored.append(
                {
                    "block_id": _new_id(),
                    "session_id": session_id,
                    "start_ts": None,
                    "end_ts": None,
                    "compliance_rate": None,
                    "override_count": 0,
                    "excluded_reason": None,
                    **r,
                }
            )
        self._blocks[session_id] = stored
        return [dict(b) for b in stored]

    def get_blocks(self, session_id: str) -> list[dict[str, Any]]:
        return [dict(b) for b in self._blocks.get(session_id, [])]

    def materialize_block_times(self, session_id: str, start_ts: datetime) -> None:
        for b in self._blocks.get(session_id, []):
            b["start_ts"] = start_ts + timedelta(seconds=b["start_offset_s"])
            b["end_ts"] = start_ts + timedelta(seconds=b["end_offset_s"])

    def increment_override(self, block_id: str) -> None:
        for blocks in self._blocks.values():
            for b in blocks:
                if b["block_id"] == block_id:
                    b["override_count"] += 1
                    return

    # -- ticks -------------------------------------------------------------
    def add_tick(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        # Upsert on ts_bucket — the same contract as Postgres' ON CONFLICT
        # (session_id, ts_bucket) DO UPDATE, so re-sending a tick (runner
        # restart, spool replay) never duplicates a bucket in either backend.
        rows = self._ticks.setdefault(session_id, [])
        for existing in rows:
            if existing["ts_bucket"] == row["ts_bucket"]:
                existing.update(row)
                return dict(existing)
        rows.append(dict(row))
        return dict(row)

    def list_ticks(self, session_id: str) -> list[dict[str, Any]]:
        return sorted((dict(t) for t in self._ticks.get(session_id, [])), key=_by_ts("ts_bucket"))

    # -- comments ----------------------------------------------------------
    def add_comment(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        # Idempotency on (platform, ext_id) when both are present: a duplicate
        # delivery returns the EXISTING row (same contract as the Postgres
        # partial unique index + ON CONFLICT DO NOTHING in migration 0002).
        platform, ext_id = row.get("platform"), row.get("ext_id")
        stored = dict(row)
        if platform and ext_id:
            keys = self._comment_keys.setdefault(session_id, {})
            existing = keys.get((platform, ext_id))
            if existing is not None:
                return dict(existing)
            keys[(platform, ext_id)] = stored
        self._comments.setdefault(session_id, []).append(stored)
        return dict(stored)

    def list_comments(self, session_id: str) -> list[dict[str, Any]]:
        return sorted((dict(c) for c in self._comments.get(session_id, [])), key=_by_ts("ts"))

    # -- reactions (migration 0007) ----------------------------------------
    def add_reaction(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        # Idempotency on (platform, ext_id) when both are present — a
        # duplicate delivery returns the EXISTING row, same contract as the
        # partial unique index + ON CONFLICT DO NOTHING in Postgres.
        platform, ext_id = row.get("platform"), row.get("ext_id")
        stored = {"amount": None, "currency": None, **row}
        if platform and ext_id:
            keys = self._reaction_keys.setdefault(session_id, {})
            existing = keys.get((platform, ext_id))
            if existing is not None:
                return dict(existing)
            keys[(platform, ext_id)] = stored
        self._reactions.setdefault(session_id, []).append(stored)
        return dict(stored)

    def list_reactions(self, session_id: str) -> list[dict[str, Any]]:
        return sorted((dict(r) for r in self._reactions.get(session_id, [])), key=_by_ts("ts_utc"))

    # -- clicks ------------------------------------------------------------
    def add_click(self, session_id: str | None, row: dict[str, Any]) -> dict[str, Any]:
        # Validity columns (migration 0004) default exactly like the SQL
        # schema: is_valid true, reason/ua_class NULL — so a caller that
        # predates classification stores a VALID click in both backends.
        stored = {"is_valid": True, "invalid_reason": None, "ua_class": None, **row}
        self._clicks.setdefault(session_id or "", []).append(stored)
        return dict(stored)

    def list_clicks(self, session_id: str) -> list[dict[str, Any]]:
        return sorted((dict(c) for c in self._clicks.get(session_id, [])), key=_by_ts("ts"))

    def list_clicks_for_fingerprint(
        self, session_id: str, dedup_hash: str, shortlink_code: str | None
    ) -> list[dict[str, Any]]:
        """Clicks of ONE (dedup_hash, shortlink) in a session, oldest first.

        The redirect classifies validity on the hot path and needs only this
        fingerprint's history (refractory + volume cap). Reading the whole
        session instead made every redirect cost O(clicks-so-far) — worst
        exactly during the bot bursts gói Q1 exists to catch. Both backends
        must return the same narrow slice (test_store_contract).
        """
        return sorted(
            (
                dict(c)
                for c in self._clicks.get(session_id, [])
                if c.get("dedup_hash") == dedup_hash and c.get("shortlink_code") == shortlink_code
            ),
            key=_by_ts("ts"),
        )

    # -- interventions -----------------------------------------------------
    def add_intervention(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        self._interventions.setdefault(session_id, []).append(dict(row))
        return dict(row)

    def list_interventions(self, session_id: str) -> list[dict[str, Any]]:
        return sorted((dict(i) for i in self._interventions.get(session_id, [])), key=_by_ts("ts"))

    # -- assignment / exposure events (APPEND-ONLY, migration 0006) --------
    #
    # No update/delete counterpart exists on purpose — see the Store protocol.
    def add_assignment_events(
        self, session_id: str, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Materialize the WHOLE schedule as it was drawn, in one append."""
        stored = [
            {
                "id": _new_id(),
                "session_id": session_id,
                "block_idx": r["block_idx"],
                "assignment": r.get("assignment"),
                "block_start_s": r["block_start_s"],
                "block_end_s": r["block_end_s"],
                "design_hash": r["design_hash"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
        self._assignment_events.setdefault(session_id, []).extend(stored)
        return [dict(r) for r in stored]

    def list_assignment_events(self, session_id: str) -> list[dict[str, Any]]:
        return sorted(
            (dict(r) for r in self._assignment_events.get(session_id, [])),
            key=lambda r: (r["created_at"], r["block_idx"]),
        )

    def add_exposure_event(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        stored = {
            "id": _new_id(),
            "session_id": session_id,
            "block_idx": row.get("block_idx"),
            "event_type": row["event_type"],
            "product_id": row.get("product_id"),
            "ts_utc": row["ts_utc"],
            "ack_latency_ms": row.get("ack_latency_ms"),
            "source": row["source"],
        }
        self._exposure_events.setdefault(session_id, []).append(stored)
        return dict(stored)

    def list_exposure_events(self, session_id: str) -> list[dict[str, Any]]:
        return sorted(
            (dict(r) for r in self._exposure_events.get(session_id, [])), key=_by_ts("ts_utc")
        )

    # -- orders ------------------------------------------------------------
    def add_order(self, session_id: str | None, row: dict[str, Any]) -> dict[str, Any]:
        self._orders.setdefault(session_id or "", []).append(dict(row))
        return dict(row)

    def list_orders(self, session_id: str) -> list[dict[str, Any]]:
        return sorted((dict(o) for o in self._orders.get(session_id, [])), key=_by_ts("ts"))

    # -- pubsub ------------------------------------------------------------
    def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        return self._broadcaster.subscribe(session_id)

    def unsubscribe(self, session_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._broadcaster.unsubscribe(session_id, q)

    def publish(self, session_id: str, message: dict[str, Any]) -> None:
        self._broadcaster.publish(session_id, message)

    def close(self) -> None:  # nothing to release
        return


def _by_ts(key: str):
    def sort_key(row: dict[str, Any]):
        v = row.get(key)
        return (v is None, v)

    return sort_key


# ---------------------------------------------------------------------------
# PostgreSQL backend
# ---------------------------------------------------------------------------


class PostgresStore:
    """Maps the Store protocol onto the SQL schema via psycopg3 + pool.

    psycopg is imported lazily inside ``__init__`` so that the default memory
    backend works without the driver installed. Timestamps are ``timestamptz``
    (UTC); callers always pass timezone-aware datetimes.
    """

    backend = "postgres"

    def __init__(self, conninfo: str, min_size: int = 1, max_size: int = 8) -> None:
        try:
            from psycopg.rows import dict_row
            from psycopg.types.json import Jsonb
            from psycopg_pool import ConnectionPool
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise RuntimeError(
                "STORE_BACKEND=postgres cần cài 'psycopg[binary,pool]' (pip install -e '.[server]')"
            ) from exc
        self._jsonb = Jsonb
        self._pool = ConnectionPool(
            conninfo,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        self._broadcaster = Broadcaster()

    # -- helpers -----------------------------------------------------------
    def _one(self, sql: str, params: tuple) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _norm_row(row) if row else None

    def _all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._pool.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_norm_row(r) for r in rows]

    def _exec(self, sql: str, params: tuple) -> None:
        with self._pool.connection() as conn:
            conn.execute(sql, params)

    # -- products ----------------------------------------------------------
    def create_product(self, row: dict[str, Any]) -> dict[str, Any]:
        out = self._one(
            """
            INSERT INTO product (product_id, name, category, cost, price, stock)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                name = EXCLUDED.name, category = EXCLUDED.category,
                cost = EXCLUDED.cost, price = EXCLUDED.price, stock = EXCLUDED.stock
            RETURNING *
            """,
            (
                row["product_id"],
                row["name"],
                row.get("category"),
                row["cost"],
                row["price"],
                row["stock"],
            ),
        )
        assert out is not None
        return out

    def list_products(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM product ORDER BY created_at")

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM product WHERE product_id = %s", (product_id,))

    # -- shortlinks --------------------------------------------------------
    def create_shortlink(self, row: dict[str, Any]) -> dict[str, Any]:
        import psycopg

        try:
            out = self._one(
                """
                INSERT INTO shortlink (code, product_id, session_id, target_url, created_at)
                VALUES (%s, %s, %s, %s, %s) RETURNING *
                """,
                (
                    row["code"],
                    row["product_id"],
                    row.get("session_id"),
                    row["target_url"],
                    row["created_at"],
                ),
            )
        except psycopg.errors.UniqueViolation as exc:
            raise ShortlinkCodeTakenError(row["code"]) from exc
        assert out is not None
        return out

    def get_shortlink(self, code: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM shortlink WHERE code = %s", (code,))

    # -- sessions ----------------------------------------------------------
    def create_session(self, row: dict[str, Any]) -> dict[str, Any]:
        out = self._one(
            """
            INSERT INTO live_session
                (session_id, platform, title, mode, status, planned_duration_min,
                 host_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (
                row["session_id"],
                row["platform"],
                row.get("title"),
                row["mode"],
                row["status"],
                row["planned_duration_min"],
                row.get("host_id"),
                row["created_at"],
            ),
        )
        assert out is not None
        return out

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM live_session ORDER BY created_at")

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM live_session WHERE session_id = %s", (session_id,))

    def update_session(self, session_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        allowed = ("status", "start_ts", "end_ts", "design", "title", "mode", "runsheet")
        sets, params = [], []
        for key in allowed:
            if key in fields:
                sets.append(f"{key} = %s")
                value = fields[key]
                if key in ("design", "runsheet") and value is not None:
                    value = self._jsonb(value)
                params.append(value)
        params.append(session_id)
        # S608: safe — column names come from the fixed `allowed` tuple above,
        # never from caller input; values go through placeholders.
        out = self._one(
            f"UPDATE live_session SET {', '.join(sets)} WHERE session_id = %s RETURNING *",  # noqa: S608
            tuple(params),
        )
        assert out is not None
        return out

    # -- blocks ------------------------------------------------------------
    def save_schedule(
        self, session_id: str, block_rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM experiment_block WHERE session_id = %s", (session_id,))
            for r in block_rows:
                conn.execute(
                    """
                    INSERT INTO experiment_block
                        (session_id, block_index, phase, assignment, propensity,
                         is_washout, start_offset_s, end_offset_s)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session_id,
                        r["block_index"],
                        r["phase"],
                        r["assignment"],
                        r["propensity"],
                        r["is_washout"],
                        r["start_offset_s"],
                        r["end_offset_s"],
                    ),
                )
        return self.get_blocks(session_id)

    def get_blocks(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM experiment_block WHERE session_id = %s ORDER BY block_index",
            (session_id,),
        )

    def materialize_block_times(self, session_id: str, start_ts: datetime) -> None:
        self._exec(
            """
            UPDATE experiment_block
            SET start_ts = %s + make_interval(secs => start_offset_s),
                end_ts   = %s + make_interval(secs => end_offset_s)
            WHERE session_id = %s
            """,
            (start_ts, start_ts, session_id),
        )

    def increment_override(self, block_id: str) -> None:
        self._exec(
            "UPDATE experiment_block SET override_count = override_count + 1 WHERE block_id = %s",
            (block_id,),
        )

    # -- ticks -------------------------------------------------------------
    def add_tick(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        out = self._one(
            """
            INSERT INTO session_tick
                (session_id, ts_bucket, viewers, comment_rate, like_rate,
                 click_count, pinned_product_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, ts_bucket) DO UPDATE SET
                viewers = EXCLUDED.viewers, comment_rate = EXCLUDED.comment_rate,
                like_rate = EXCLUDED.like_rate, click_count = EXCLUDED.click_count,
                pinned_product_id = EXCLUDED.pinned_product_id
            RETURNING *
            """,
            (
                session_id,
                row["ts_bucket"],
                row["viewers"],
                row.get("comment_rate", 0.0),
                row.get("like_rate", 0.0),
                row.get("click_count", 0),
                row.get("pinned_product_id"),
            ),
        )
        assert out is not None
        return out

    def list_ticks(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM session_tick WHERE session_id = %s ORDER BY ts_bucket",
            (session_id,),
        )

    # -- comments ----------------------------------------------------------
    def add_comment(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        # Idempotency (migration 0002): the partial unique index on
        # (session_id, platform, ext_id) WHERE ext_id IS NOT NULL turns a
        # duplicate delivery into DO NOTHING; we then return the existing row
        # so the API answer is identical either way.
        out = self._one(
            """
            INSERT INTO comment_event
                (comment_id, session_id, block_id, ts, platform, ext_id,
                 text_scrubbed, pii_kinds, intent_label, intent_confidence, sentiment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, platform, ext_id) WHERE ext_id IS NOT NULL
                DO NOTHING
            RETURNING *
            """,
            (
                row["comment_id"],
                session_id,
                row.get("block_id"),
                row["ts"],
                row.get("platform"),
                row.get("ext_id"),
                row["text_scrubbed"],
                list(row.get("pii_kinds", [])),
                row.get("intent_label"),
                row.get("intent_confidence"),
                row.get("sentiment"),
            ),
        )
        if out is None:  # duplicate — fetch the row that won
            out = self._one(
                """
                SELECT * FROM comment_event
                WHERE session_id = %s AND platform = %s AND ext_id = %s
                """,
                (session_id, row.get("platform"), row.get("ext_id")),
            )
        assert out is not None
        return out

    def list_comments(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM comment_event WHERE session_id = %s ORDER BY ts",
            (session_id,),
        )

    # -- reactions (migration 0007) ----------------------------------------
    def add_reaction(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        # Same idempotency contract as comments: the partial unique index on
        # (session_id, platform, ext_id) WHERE ext_id IS NOT NULL turns a
        # duplicate delivery into DO NOTHING; the existing row is returned.
        out = self._one(
            """
            INSERT INTO reaction_event
                (reaction_id, session_id, ts_utc, kind, amount, currency, platform, ext_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, platform, ext_id) WHERE ext_id IS NOT NULL
                DO NOTHING
            RETURNING *
            """,
            (
                row["reaction_id"],
                session_id,
                row["ts_utc"],
                row["kind"],
                row.get("amount"),
                row.get("currency"),
                row.get("platform"),
                row.get("ext_id"),
            ),
        )
        if out is None:  # duplicate — fetch the row that won
            out = self._one(
                """
                SELECT * FROM reaction_event
                WHERE session_id = %s AND platform = %s AND ext_id = %s
                """,
                (session_id, row.get("platform"), row.get("ext_id")),
            )
        assert out is not None
        return out

    def list_reactions(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM reaction_event WHERE session_id = %s ORDER BY ts_utc",
            (session_id,),
        )

    # -- clicks ------------------------------------------------------------
    def add_click(self, session_id: str | None, row: dict[str, Any]) -> dict[str, Any]:
        out = self._one(
            """
            INSERT INTO click_event
                (click_id, session_id, block_id, ts, product_id, shortlink_code,
                 dedup_hash, is_valid, invalid_reason, ua_class)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (
                row["click_id"],
                session_id,
                row.get("block_id"),
                row["ts"],
                row.get("product_id"),
                row.get("shortlink_code"),
                row.get("dedup_hash"),
                row.get("is_valid", True),
                row.get("invalid_reason"),
                row.get("ua_class"),
            ),
        )
        assert out is not None
        return out

    def list_clicks(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM click_event WHERE session_id = %s ORDER BY ts",
            (session_id,),
        )

    def list_clicks_for_fingerprint(
        self, session_id: str, dedup_hash: str, shortlink_code: str | None
    ) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT * FROM click_event
            WHERE session_id = %s AND dedup_hash = %s AND shortlink_code IS NOT DISTINCT FROM %s
            ORDER BY ts
            """,
            (session_id, dedup_hash, shortlink_code),
        )

    # -- interventions -----------------------------------------------------
    def add_intervention(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        candidates = row.get("candidates_json")
        out = self._one(
            """
            INSERT INTO intervention_log
                (action_id, session_id, block_id, ts, client_ts, action_type,
                 product_id, source, inner_propensity, candidates_json, executed,
                 override_reason, seconds_since_last_switch)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (
                row["action_id"],
                session_id,
                row.get("block_id"),
                row["ts"],
                row.get("client_ts"),
                row["action_type"],
                row.get("product_id"),
                row["source"],
                row.get("inner_propensity"),
                self._jsonb(candidates) if candidates is not None else None,
                row.get("executed", True),
                row.get("override_reason"),
                row.get("seconds_since_last_switch"),
            ),
        )
        assert out is not None
        return out

    def list_interventions(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM intervention_log WHERE session_id = %s ORDER BY ts",
            (session_id,),
        )

    # -- assignment / exposure events (APPEND-ONLY, migration 0006) --------
    #
    # No update/delete counterpart exists on purpose — see the Store protocol.
    def add_assignment_events(
        self, session_id: str, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Materialize the WHOLE schedule as it was drawn, in ONE transaction.

        One connection for the batch: a half-written schedule would be an audit
        trail that disagrees with itself, and the append is the only chance to
        record the design as drawn (there is no update path to repair it).
        """
        if not rows:
            return []
        inserted: list[dict[str, Any]] = []
        with self._pool.connection() as conn:
            for r in rows:
                out = conn.execute(
                    """
                    INSERT INTO assignment_event
                        (session_id, block_idx, assignment, block_start_s, block_end_s,
                         design_hash, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
                    """,
                    (
                        session_id,
                        r["block_idx"],
                        r.get("assignment"),
                        r["block_start_s"],
                        r["block_end_s"],
                        r["design_hash"],
                        r["created_at"],
                    ),
                ).fetchone()
                assert out is not None
                inserted.append(_norm_row(out))
        return inserted

    def list_assignment_events(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM assignment_event WHERE session_id = %s ORDER BY created_at, block_idx",
            (session_id,),
        )

    def add_exposure_event(self, session_id: str, row: dict[str, Any]) -> dict[str, Any]:
        out = self._one(
            """
            INSERT INTO exposure_event
                (session_id, block_idx, event_type, product_id, ts_utc, ack_latency_ms, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (
                session_id,
                row.get("block_idx"),
                row["event_type"],
                row.get("product_id"),
                row["ts_utc"],
                row.get("ack_latency_ms"),
                row["source"],
            ),
        )
        assert out is not None
        return out

    def list_exposure_events(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM exposure_event WHERE session_id = %s ORDER BY ts_utc",
            (session_id,),
        )

    # -- orders ------------------------------------------------------------
    def add_order(self, session_id: str | None, row: dict[str, Any]) -> dict[str, Any]:
        out = self._one(
            """
            INSERT INTO order_event
                (order_id, session_id, block_id, ts, product_id, qty, gross, fees, net_margin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (
                row["order_id"],
                session_id,
                row.get("block_id"),
                row["ts"],
                row.get("product_id"),
                row.get("qty", 1),
                row.get("gross", 0),
                row.get("fees", 0),
                row.get("net_margin"),
            ),
        )
        assert out is not None
        return out

    def list_orders(self, session_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM order_event WHERE session_id = %s ORDER BY ts",
            (session_id,),
        )

    # -- pubsub ------------------------------------------------------------
    def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        return self._broadcaster.subscribe(session_id)

    def unsubscribe(self, session_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._broadcaster.unsubscribe(session_id, q)

    def publish(self, session_id: str, message: dict[str, Any]) -> None:
        self._broadcaster.publish(session_id, message)

    def close(self) -> None:
        self._pool.close()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_store(backend: str | None = None) -> Store:
    """Build the store selected by ``backend`` or the STORE_BACKEND env var
    ("memory" default | "postgres")."""
    name = (backend or os.environ.get("STORE_BACKEND", "memory")).strip().lower()
    if name == "postgres":
        from livelift.config import get_settings  # lazy: needs pydantic-settings

        return PostgresStore(get_settings().database_url)
    if name != "memory":
        raise ValueError(f"unknown STORE_BACKEND: {name!r} (expected 'memory' or 'postgres')")
    return InMemoryStore()
