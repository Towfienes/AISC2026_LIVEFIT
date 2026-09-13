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

Durability (incident 11/09/2026): ``InMemoryStore`` lost 13 real sessions and
17.535 comments when the API process restarted — RAM is not storage. Two
answers live in this module and both are needed:

* ``PostgresStore`` — the real answer. Survives anything the process does.
* ``SnapshotManager`` — the fallback for memory mode (demo, competition
  laptop, no Docker): every ``store_snapshot_interval_s`` seconds the WHOLE
  in-memory state is serialized and written atomically to one JSON file, and
  read back at startup. It costs a bounded window (at most one interval of
  the newest events), never a whole session. It is not a substitute for
  Postgres and ``durability_info`` says so out loud on ``/health``.

Why serialization is safe here: ``export_json`` never awaits, so — like every
other store method — it is atomic with respect to request handlers; only the
disk write is pushed to a thread.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
import logging
import os
import threading
import time
import uuid
import weakref
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger("livelift.store")


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
# Hạn giờ — sự cố 13/09/2026 ("API treo 30 giây khi PostgreSQL chết")
# ---------------------------------------------------------------------------
#
# Khi cơ sở dữ liệu chết, mọi lần đọc kho đứng im đúng 30 giây rồi trả
# "Internal Server Error" trần: đó là ``ConnectionPool.timeout`` mặc định của
# psycopg_pool. Trang web đặt hạn 2,5 giây cho phép thử nên nó luôn thất bại và
# báo "Chưa kết nối được máy chủ" NGAY CẢ KHI API còn sống. Bốn con số dưới đây
# là ranh giới giữa "hỏng nhanh, nói rõ" và "treo im lặng".
#
# Vì sao là các con số này (đo trên máy chạy demo, cổng không ai nghe):
#   - connect_timeout=3  → libpq bỏ cuộc sau ~3,0s (đo được 3,013s). Đây là
#     tham số duy nhất cứu được trường hợp máy chủ *nuốt gói* (không refuse),
#     mà mặc định của libpq là chờ VÔ HẠN.
#   - pool timeout=2,0s  → lấy kết nối từ pool hỏng bật lỗi sau ~2,0s thay vì
#     30s. Cố ý NGẮN HƠN hạn 2,5 giây mà trang web đặt cho mỗi lời gọi: máy chủ
#     trả lời sau khi client đã bỏ cuộc thì câu 503 tiếng Việt viết kỹ đến mấy
#     cũng không ai đọc được, người dùng chỉ thấy "không kết nối được máy chủ"
#     — đúng cái nhầm lẫn API-chết-hay-DB-chết của ngày 13/09.
#   - statement_timeout=8s → chặn truy vấn đã cầm được kết nối nhưng chạy mãi
#     (khóa bảng, máy chủ lết). Phải LỚN HƠN pool timeout: nó bảo vệ pha khác,
#     và một truy vấn thật trên phiên live có thể chạy vài giây.
#   - ping 1,5s          → /health phải trả lời dưới 3 giây kể cả khi kho chết,
#     nên lần thử kết nối của nó phải ngắn hơn hẳn hạn của route thường.
#
# libpq làm tròn connect_timeout < 2 lên 2 giây, nên đừng đặt 1.
DEFAULT_CONNECT_TIMEOUT_S = 3
DEFAULT_POOL_TIMEOUT_S = 2.0
DEFAULT_STATEMENT_TIMEOUT_S = 8.0
DEFAULT_PING_TIMEOUT_S = 1.5
# Kết quả ping được nhớ trong ngần này giây. Trang web hỏi /health liên tục
# (mỗi vài giây, nhiều tab); nếu mỗi lần hỏi là một lần mở kết nối thì chính
# cái đồng hồ đo sức khỏe lại đấm vào cơ sở dữ liệu. 5 giây đủ ngắn để người
# vận hành thấy DB chết gần như tức thì, đủ dài để 20 tab không thành 20 lần
# kết nối mỗi giây.
DEFAULT_PING_CACHE_S = 5.0
# Đóng pool khi DB đã chết: mỗi luồng nền của psycopg_pool bị chờ đủ `timeout`
# giây (mặc định 5,0 × số luồng) nên tắt máy sạch cũng mất hàng chục giây.
DEFAULT_CLOSE_TIMEOUT_S = 1.0


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


_SESSION_WRITE_ONCE: frozenset[str] = frozenset({"session_id", "platform", "dry_run", "is_demo"})
"""Session columns fixed at creation — ``update_session`` silently ignores them.

``dry_run`` and ``is_demo`` are the load-bearing ones: each decides whether a
session counts in a pooled result, so both have to be decisions taken BEFORE
the session runs (PREREGISTRATION §8.2). A column that can be flipped later is
not a pre-registration rule, it is a switch for dropping sessions whose numbers
you did not like — and for ``is_demo`` the reverse flip would be worse still:
relabeling a real session as "sample data" after seeing its numbers, or
laundering a demo session into the real pool. The SQL store gets the same
guarantee from the fixed ``allowed`` tuple in its own ``update_session``.

The two flags answer DIFFERENT questions (gói DEMO-THẬT, 12/09/2026):
``is_demo`` — is this data REAL at all? (machine-generated sample sessions from
/demo/seed and scripts/seed_demo_vang.py; no broadcast ever happened);
``dry_run`` — is this REAL session counted? (a real practice run, declared at
creation). Demo data is excluded from every real scientific output and always
labeled; a dry run is real data that merely stays out of the pooled sample.
"""


class ShortlinkCodeTakenError(Exception):
    """A shortlink code already exists.

    Shortlink codes are the operational definition of a product click, so a
    silent overwrite would misattribute clicks between products/sessions —
    an experiment-integrity bug. Both store backends must therefore REJECT a
    duplicate code rather than replace it; the API turns this into a 409.
    """


class StoreUnavailableError(RuntimeError):
    """Kho dữ liệu KHÔNG trả lời (sự cố 13/09/2026).

    Ngày 13/09/2026 PostgreSQL chết hẳn giữa phiên. Mỗi lần đọc kho treo đúng
    30 giây (thời gian chờ mặc định của ``ConnectionPool``) rồi bật lên thành
    ``Internal Server Error`` trần — không ai đọc ra được là *cơ sở dữ liệu đã
    chết*. Ngoại lệ này là câu trả lời có nghĩa: mọi lỗi kết nối/hết giờ của
    tầng Postgres được dịch sang đây kèm câu tiếng Việt, và ``main.py`` biến nó
    thành HTTP 503 có thân đọc được thay vì 500 trống.

    ``message`` là câu tiếng Việt cho người vận hành; ``cause_text`` giữ nguyên
    văn lỗi của driver để log/gỡ rối — không được ném nguyên văn đó ra cho
    người dùng vì nó là tiếng Anh và không nói phải làm gì.
    """

    def __init__(self, message: str, *, cause_text: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.cause_text = cause_text


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

    # Kiểm tra sống/chết của kho, RẺ và có HẠN GIỜ (sự cố 13/09/2026).
    # Trả về None nếu kho trả lời được; ném StoreUnavailableError nếu không.
    # /health gọi nó trước khi dám tuyên bố durable=true — trước đó /health chỉ
    # đọc tên backend rồi khẳng định "dữ liệu nằm trong PostgreSQL" kể cả khi
    # không còn ai nghe ở cổng 5432.
    def ping(self, timeout_s: float = ...) -> None: ...

    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Snapshot codec + atomic file writer
# ---------------------------------------------------------------------------

SNAPSHOT_FORMAT = 1
"""Bumped whenever the on-disk layout changes. import_json REFUSES any other
value rather than guessing — a snapshot half-understood is worse than none."""

_DT_TAG = "__dt__"
_DEC_TAG = "__dec__"

# Temp files are unique per process AND per write, so two writers (should one
# ever exist) can never hand each other a half-written file to rename.
_tmp_counter = itertools.count()


class SnapshotError(Exception):
    """A snapshot file could not be read, parsed, or trusted."""


def _snapshot_default(obj: Any) -> Any:
    """JSON encoder for the two non-JSON types the store actually holds."""
    if isinstance(obj, datetime):
        return {_DT_TAG: obj.isoformat()}
    if isinstance(obj, Decimal):
        return {_DEC_TAG: str(obj)}
    raise TypeError(f"không tuần tự hoá được kiểu {type(obj).__name__} trong ảnh chụp kho")


def _snapshot_hook(d: dict[str, Any]) -> Any:
    """Inverse of :func:`_snapshot_default` — restores real datetime/Decimal."""
    if len(d) == 1:
        if _DT_TAG in d:
            return datetime.fromisoformat(d[_DT_TAG])
        if _DEC_TAG in d:
            return Decimal(d[_DEC_TAG])
    return d


def _rebuild_dedup_index(
    rows_by_session: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[tuple[str, str], dict[str, Any]]]:
    """Rebuild a (platform, ext_id) -> row index from the rows themselves.

    First row wins, matching the live insert path: ``add_comment`` keeps the
    row that arrived first and returns it for every duplicate after.
    """
    index: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    for session_id, rows in rows_by_session.items():
        keys: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            platform, ext_id = row.get("platform"), row.get("ext_id")
            if platform and ext_id:
                keys.setdefault((platform, ext_id), row)
        if keys:
            index[session_id] = keys
    return index


def write_snapshot_atomic(path: Path, payload: str) -> None:
    """Write ``payload`` so that ``path`` is either the OLD file or the NEW
    one — never a truncated mix.

    The sequence matters: write the whole document to a temp file in the same
    directory, flush + fsync it, then ``os.replace``. ``os.replace`` is atomic
    on POSIX and on Windows (MoveFileEx/REPLACE_EXISTING), and same-directory
    keeps it on one volume where that guarantee holds. A crash at any point
    leaves the previous good snapshot in place.

    On failure the temp file is removed: a data-safety mechanism that fills the
    data directory with rubbish on every failed attempt is its own outage.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{next(_tmp_counter)}")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def quarantine_snapshot(path: Path) -> Path | None:
    """Move an unreadable snapshot aside instead of deleting or overwriting it.

    Keeps the evidence for a post-mortem (HARNESS §3 wants a root cause, and
    the broken file is the only witness) and stops the next dump from silently
    erasing it.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    spoiled = path.with_name(f"{path.name}.hong-{stamp}")
    try:
        os.replace(path, spoiled)
    except OSError:  # pragma: no cover - filesystem-dependent
        return None
    return spoiled


# ---------------------------------------------------------------------------
# In-memory backend
# ---------------------------------------------------------------------------


class InMemoryStore:
    """Complete dict-backed store. Safe for a single asyncio loop: methods
    never await, so each call is atomic w.r.t. request handlers.

    RAM is not storage (incident 11/09/2026). Attach a :class:`SnapshotManager`
    — ``attach_snapshot(store)`` does it from config — to get periodic atomic
    dumps and restore-on-startup. Without one, a restart loses everything.
    """

    backend = "memory"

    def __init__(self) -> None:
        # Bumped by every method that CHANGES state. The snapshot loop dumps
        # only when this moved, so an idle session costs zero disk writes and
        # a duplicate delivery (which returns the existing row) costs none
        # either.
        self._rev = 0
        # Set by attach_snapshot(); read by durability_info() for /health.
        self.snapshot: SnapshotManager | None = None
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
        self._rev += 1
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
        self._rev += 1
        return dict(row)

    def get_shortlink(self, code: str) -> dict[str, Any] | None:
        row = self._shortlinks.get(code)
        return dict(row) if row else None

    # -- sessions ----------------------------------------------------------
    def create_session(self, row: dict[str, Any]) -> dict[str, Any]:
        self._sessions[row["session_id"]] = dict(row)
        self._rev += 1
        return dict(row)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [dict(s) for s in self._sessions.values()]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        row = self._sessions.get(session_id)
        return dict(row) if row else None

    def update_session(self, session_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = self._sessions[session_id]
        # Same write-once columns as the SQL store's `allowed` tuple: the
        # sample-inclusion flag is fixed at creation (PREREGISTRATION §8.2) and
        # the two backends must not disagree about that (lesson of 27/08).
        row.update({k: v for k, v in fields.items() if k not in _SESSION_WRITE_ONCE})
        self._rev += 1
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
        self._rev += 1
        return [dict(b) for b in stored]

    def get_blocks(self, session_id: str) -> list[dict[str, Any]]:
        return [dict(b) for b in self._blocks.get(session_id, [])]

    def materialize_block_times(self, session_id: str, start_ts: datetime) -> None:
        for b in self._blocks.get(session_id, []):
            b["start_ts"] = start_ts + timedelta(seconds=b["start_offset_s"])
            b["end_ts"] = start_ts + timedelta(seconds=b["end_offset_s"])
        self._rev += 1

    def increment_override(self, block_id: str) -> None:
        for blocks in self._blocks.values():
            for b in blocks:
                if b["block_id"] == block_id:
                    b["override_count"] += 1
                    self._rev += 1
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
                self._rev += 1
                return dict(existing)
        rows.append(dict(row))
        self._rev += 1
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
        self._rev += 1
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
        self._rev += 1
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
        self._rev += 1
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
        self._rev += 1
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
        self._rev += 1
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
        self._rev += 1
        return dict(stored)

    def list_exposure_events(self, session_id: str) -> list[dict[str, Any]]:
        return sorted(
            (dict(r) for r in self._exposure_events.get(session_id, [])), key=_by_ts("ts_utc")
        )

    # -- orders ------------------------------------------------------------
    def add_order(self, session_id: str | None, row: dict[str, Any]) -> dict[str, Any]:
        self._orders.setdefault(session_id or "", []).append(dict(row))
        self._rev += 1
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

    # -- snapshot (durability, incident 11/09/2026) ------------------------
    #
    # export_json / import_json are the whole persistence contract of the
    # memory backend. They are deliberately SYNCHRONOUS and never await, so
    # like every other method here they are atomic with respect to request
    # handlers: nothing can mutate a dict half-way through serialization.
    def export_json(self) -> str:
        """Serialize the ENTIRE store to one JSON document.

        Datetimes and Decimals are tagged (``{"__dt__": ...}``) so they come
        back as the same Python types — a restore that turned timestamps into
        strings would break every block-attribution and report calculation
        downstream, i.e. it would look like it worked and silently lie.

        The dedup key maps (``_comment_keys``/``_reaction_keys``) are NOT
        written: they are rebuilt on import from the rows themselves, which
        also restores the object identity they rely on.
        """
        state = {
            "format": SNAPSHOT_FORMAT,
            "backend": self.backend,
            "saved_at": datetime.now(UTC),
            "rev": self._rev,
            "products": self._products,
            "shortlinks": self._shortlinks,
            "sessions": self._sessions,
            "blocks": self._blocks,
            "ticks": self._ticks,
            "comments": self._comments,
            "reactions": self._reactions,
            "clicks": self._clicks,
            "interventions": self._interventions,
            "orders": self._orders,
            "assignment_events": self._assignment_events,
            "exposure_events": self._exposure_events,
        }
        return json.dumps(state, default=_snapshot_default, ensure_ascii=False)

    def import_json(self, text: str) -> dict[str, int]:
        """Replace the whole state with a snapshot document.

        Returns a count per table so the caller can log what was recovered.
        Raises :class:`SnapshotError` on anything it does not recognize —
        a half-understood snapshot must never be loaded as if it were whole.
        """
        try:
            state = json.loads(text, object_hook=_snapshot_hook)
        except (ValueError, TypeError) as exc:
            raise SnapshotError(f"ảnh chụp không đọc được: {exc}") from exc
        if not isinstance(state, dict):
            raise SnapshotError("ảnh chụp không phải một đối tượng JSON")
        fmt = state.get("format")
        if fmt != SNAPSHOT_FORMAT:
            raise SnapshotError(
                f"ảnh chụp định dạng {fmt!r}, mã này chỉ đọc định dạng {SNAPSHOT_FORMAT}"
            )

        def _table(key: str) -> dict[str, Any]:
            value = state.get(key, {})
            if not isinstance(value, dict):
                raise SnapshotError(f"bảng {key!r} trong ảnh chụp không phải đối tượng")
            return value

        self._products = _table("products")
        self._shortlinks = _table("shortlinks")
        self._sessions = _table("sessions")
        self._blocks = _table("blocks")
        self._ticks = _table("ticks")
        self._comments = _table("comments")
        self._reactions = _table("reactions")
        self._clicks = _table("clicks")
        self._interventions = _table("interventions")
        self._orders = _table("orders")
        self._assignment_events = _table("assignment_events")
        self._exposure_events = _table("exposure_events")

        # Rebuild the idempotency indexes by identity: the value must be the
        # SAME dict that sits in the rows list, or a duplicate delivery after
        # a restart would return a detached copy.
        self._comment_keys = _rebuild_dedup_index(self._comments)
        self._reaction_keys = _rebuild_dedup_index(self._reactions)

        self._rev += 1
        return self.counts()

    def counts(self) -> dict[str, int]:
        """Row counts per table — what a recovery log line reports."""
        return {
            "sessions": len(self._sessions),
            "products": len(self._products),
            "shortlinks": len(self._shortlinks),
            "comments": sum(len(v) for v in self._comments.values()),
            "ticks": sum(len(v) for v in self._ticks.values()),
            "clicks": sum(len(v) for v in self._clicks.values()),
            "reactions": sum(len(v) for v in self._reactions.values()),
            "orders": sum(len(v) for v in self._orders.values()),
            "interventions": sum(len(v) for v in self._interventions.values()),
            "assignment_events": sum(len(v) for v in self._assignment_events.values()),
            "exposure_events": sum(len(v) for v in self._exposure_events.values()),
        }

    def ping(self, timeout_s: float = DEFAULT_PING_TIMEOUT_S) -> None:
        """Luôn sống: kho nằm ngay trong tiến trình này.

        Không có mạng, không có socket, không thể "chết mà vẫn báo xanh" như
        Postgres ngày 13/09/2026. Vẫn hiện diện để ``/health`` gọi một đường
        duy nhất cho mọi backend, và ``timeout_s`` bị bỏ qua một cách có ý.
        """
        return

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

# Câu nói sự thật khi cơ sở dữ liệu chết. Một nguồn duy nhất cho cả /health
# (storage_warning) lẫn thân 503 của route — hai chỗ nói hai kiểu thì người vận
# hành phải đoán xem chỗ nào đúng.
STORE_DOWN_CORE = (
    "KHÔNG kết nối được PostgreSQL — hệ thống đang KHÔNG lưu được dữ liệu, mọi ghi sẽ thất bại."
)
STORE_DOWN_FIX = (
    "Cách xử lý: bật lại cơ sở dữ liệu (python scripts/bat_postgres.py hoặc "
    "docker compose up -d db), hoặc đặt STORE_BACKEND=memory rồi khởi động lại API để "
    "chạy tạm bằng RAM — chấp nhận mất dữ liệu khi khởi động lại."
)
STORE_DOWN_WARNING = f"{STORE_DOWN_CORE} {STORE_DOWN_FIX}"
STORE_DOWN_DETAIL = (
    "Yêu cầu này cần đọc kho dữ liệu nhưng kho không trả lời trong hạn giờ. "
    f"{STORE_DOWN_CORE} {STORE_DOWN_FIX}"
)


def _connect_kwargs(
    conninfo: str,
    *,
    row_factory: Any,
    connect_timeout_s: int,
    statement_timeout_s: float,
) -> dict[str, Any]:
    """Tham số kết nối cho pool: hạn giờ ép vào, nhưng KHÔNG đè cấu hình người dùng.

    ``psycopg.connect`` nhận thẳng các tham số conninfo dạng từ khóa, nên không
    cần nối chuỗi (và không cần lo trích dẫn). Nhưng nếu người vận hành đã tự
    ghi ``connect_timeout``/``options`` trong DATABASE_URL thì con số của họ
    thắng: một mặc định an toàn được phép thêm vào chỗ trống, không được phép
    ghi đè lựa chọn có chủ ý.
    """
    kwargs: dict[str, Any] = {"row_factory": row_factory}
    try:
        from psycopg.conninfo import conninfo_to_dict

        existing = conninfo_to_dict(conninfo)
    except Exception:  # noqa: BLE001 - chuỗi lạ thì cứ áp mặc định an toàn
        existing = {}
    if "connect_timeout" not in existing:
        kwargs["connect_timeout"] = int(connect_timeout_s)
    if "options" not in existing:
        kwargs["options"] = f"-c statement_timeout={int(statement_timeout_s * 1000)}"
    return kwargs


class PostgresStore:
    """Maps the Store protocol onto the SQL schema via psycopg3 + pool.

    psycopg is imported lazily inside ``__init__`` so that the default memory
    backend works without the driver installed. Timestamps are ``timestamptz``
    (UTC); callers always pass timezone-aware datetimes.

    Hạn giờ (sự cố 13/09/2026): mọi đường ra cơ sở dữ liệu đều có hạn — chờ kết
    nối (``connect_timeout``), chờ pool cấp kết nối (``ConnectionPool.timeout``)
    và chờ truy vấn chạy (``statement_timeout``). Trước đó chỉ có mặc định của
    thư viện: 30 giây treo rồi 500 trần. Mọi lỗi của ba pha ấy được dịch sang
    :class:`StoreUnavailableError` để route trả 503 kèm câu tiếng Việt.
    """

    backend = "postgres"

    def __init__(
        self,
        conninfo: str,
        min_size: int = 1,
        max_size: int = 8,
        *,
        connect_timeout_s: int = DEFAULT_CONNECT_TIMEOUT_S,
        pool_timeout_s: float = DEFAULT_POOL_TIMEOUT_S,
        statement_timeout_s: float = DEFAULT_STATEMENT_TIMEOUT_S,
        close_timeout_s: float = DEFAULT_CLOSE_TIMEOUT_S,
    ) -> None:
        try:
            from psycopg.rows import dict_row
            from psycopg.types.json import Jsonb
            from psycopg_pool import ConnectionPool
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise RuntimeError(
                "STORE_BACKEND=postgres cần cài 'psycopg[binary,pool]' (pip install -e '.[server]')"
            ) from exc
        self._jsonb = Jsonb
        self._pool_timeout_s = float(pool_timeout_s)
        self._close_timeout_s = float(close_timeout_s)
        self._pool = ConnectionPool(
            conninfo,
            min_size=min_size,
            max_size=max_size,
            kwargs=_connect_kwargs(
                conninfo,
                row_factory=dict_row,
                connect_timeout_s=connect_timeout_s,
                statement_timeout_s=statement_timeout_s,
            ),
            # KHÔNG để mặc định 30,0: đây chính là con số người vận hành đếm
            # được khi /sessions treo ngày 13/09/2026.
            timeout=self._pool_timeout_s,
            # open=True và KHÔNG chờ kết nối đầu tiên: API vẫn phải khởi động
            # được khi DB đang chết, để /health còn có chỗ mà nói ra sự thật.
            open=True,
        )
        self._broadcaster = Broadcaster()

    # -- helpers -----------------------------------------------------------
    @contextlib.contextmanager
    def _connection(self, timeout_s: float | None = None):
        """Mượn một kết nối, và dịch MỌI lỗi hạ tầng sang tiếng Việt.

        Một chỗ duy nhất: nếu mỗi phương thức tự bắt lỗi thì chỉ cần quên một
        chỗ là sự cố 13/09 quay lại đúng ở chỗ đó. ``psycopg.OperationalError``
        là cha chung của ``PoolTimeout``/``PoolClosed``/kết nối đứt/truy vấn bị
        hủy vì quá ``statement_timeout`` — đúng tập hợp "kho không trả lời".
        Lỗi dữ liệu (ràng buộc, trùng khóa) KHÔNG thuộc nhánh này nên vẫn nổi
        lên nguyên vẹn cho route xử lý (ví dụ 409 của shortlink).
        """
        import psycopg

        try:
            with self._pool.connection(
                timeout=self._pool_timeout_s if timeout_s is None else timeout_s
            ) as conn:
                yield conn
        except psycopg.OperationalError as exc:
            raise StoreUnavailableError(STORE_DOWN_DETAIL, cause_text=str(exc).strip()) from exc

    def _one(self, sql: str, params: tuple) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return _norm_row(row) if row else None

    def _all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_norm_row(r) for r in rows]

    def _exec(self, sql: str, params: tuple) -> None:
        with self._connection() as conn:
            conn.execute(sql, params)

    def ping(self, timeout_s: float = DEFAULT_PING_TIMEOUT_S) -> None:
        """``SELECT 1`` có hạn giờ NGẮN — nền của một /health không nói dối.

        Hạn riêng, ngắn hơn hạn của route thường: ``/health`` phải trả lời
        nhanh kể cả khi cơ sở dữ liệu đã chết, vì đó đúng là lúc người vận hành
        bấm vào nó.

        Hai pha đều bị chặn: chờ pool cấp kết nối (``timeout_s``) VÀ chờ máy chủ
        chạy xong ``SELECT 1``. Một máy chủ còn mở cổng nhưng đã lết (khóa bảng,
        hết bộ nhớ) sẽ cấp kết nối rồi im — không chặn pha hai thì /health vẫn
        treo. ``SET`` nằm trong giao dịch của psycopg (autocommit tắt) nên nó
        được hoàn tác khi kết nối về pool, không rò sang truy vấn khác.
        """
        with self._connection(timeout_s=timeout_s) as conn:
            conn.execute(f"SET statement_timeout = {max(1, int(timeout_s * 1000))}")
            conn.execute("SELECT 1")

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
                 host_id, created_at, dry_run, is_demo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
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
                # Write-once (migrations 0008/0009): neither `dry_run` nor
                # `is_demo` is in update_session's allowed columns, so both
                # sample-inclusion rules are fixed at creation and no later
                # call can flip them.
                bool(row.get("dry_run", False)),
                bool(row.get("is_demo", False)),
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
        with self._connection() as conn:
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
        with self._connection() as conn:
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
        # Hạn giờ tường minh: khi DB đã chết, psycopg_pool chờ TỪNG luồng nền
        # đủ `timeout` giây (mặc định 5,0) nên tắt máy sạch mất hàng chục giây
        # — đúng kiểu treo mà sự cố 13/09/2026 đã dạy là không chấp nhận được.
        self._pool.close(timeout=self._close_timeout_s)


# ---------------------------------------------------------------------------
# Snapshot manager: restore at startup, dump periodically, dump on shutdown
# ---------------------------------------------------------------------------


class SnapshotManager:
    """Keeps one :class:`InMemoryStore` mirrored to one file on disk.

    Three moments, and all three are needed:

    * **startup** — ``restore()`` loads the file if it is there. This is the
      moment the incident of 11/09/2026 had no answer for.
    * **every ``interval_s``** — ``_loop()`` dumps, but ONLY if the store
      changed since the last dump (``_rev``). Writing happens in a worker
      thread so a slow disk never stalls the event loop, and the hot write
      path (``POST /comments``) touches no file at all.
    * **shutdown** — ``stop()`` dumps one last time, synchronously, so an
      orderly restart loses nothing at all.

    A dump that fails is logged and retried on the next tick; it never
    propagates into a request or kills the process. Durability machinery that
    can take the API down has made things worse, not better.
    """

    def __init__(self, store: InMemoryStore, path: Path, interval_s: float) -> None:
        self.store = store
        self.path = Path(path)
        # A sub-second cadence would dump continuously under live traffic and
        # buy nothing — one second is the floor.
        self.interval_s = max(1.0, float(interval_s))
        self._task: asyncio.Task[None] | None = None
        # Revision that is currently ON DISK (None = nothing written yet).
        self._last_rev: int | None = None
        self._last_saved_at: datetime | None = None
        self._last_error: str | None = None
        self._restored: dict[str, int] | None = None
        # Guards the file itself: the periodic writer lives in a worker thread
        # while stop() writes from the caller's thread. See _commit().
        self._write_lock = threading.Lock()

    # -- startup -----------------------------------------------------------
    def restore(self) -> dict[str, int] | None:
        """Load the snapshot into the store. Returns row counts, or None."""
        if not self.path.exists():
            log.info(
                "Chưa có ảnh chụp kho tại %s — bắt đầu với kho rỗng (đây là lần chạy đầu).",
                self.path,
            )
            return None
        try:
            counts = self.store.import_json(self.path.read_text(encoding="utf-8"))
        except (OSError, SnapshotError) as exc:
            spoiled = quarantine_snapshot(self.path)
            self._last_error = str(exc)
            log.error(
                "Ảnh chụp kho tại %s KHÔNG đọc được (%s). Đã chuyển tệp hỏng sang %s và "
                "bắt đầu với kho rỗng — dữ liệu cũ chưa mất, hãy kiểm tra tệp đó trước "
                "khi phát sóng tiếp.",
                self.path,
                exc,
                spoiled or "(không đổi tên được)",
            )
            return None
        self._restored = counts
        # Nothing new to write yet: the file already matches this state.
        self._last_rev = self.store._rev
        log.warning(
            "Đã KHÔI PHỤC kho từ ảnh chụp %s: %d phiên, %d bình luận, %d tick, %d lượt nhấp.",
            self.path,
            counts["sessions"],
            counts["comments"],
            counts["ticks"],
            counts["clicks"],
        )
        return counts

    # -- dumping -----------------------------------------------------------
    def _commit(self, rev: int, payload: str, *, force: bool) -> bool:
        """Put ``payload`` on disk, but NEVER behind a newer snapshot.

        Two writers can be in flight at once: the periodic task (its disk write
        runs in a worker thread) and ``stop()``'s final synchronous dump. If the
        older of the two happened to land last, the file would silently go
        BACKWARDS and lose the very events shutdown was trying to save — a
        data-loss bug hiding inside the data-loss fix. The lock serializes the
        two, and the revision check makes the outcome independent of who wins
        the race: an older payload is dropped, not written.
        """
        with self._write_lock:
            if not force and self._last_rev is not None and rev <= self._last_rev:
                return False
            write_snapshot_atomic(self.path, payload)
            self._last_rev = rev
            self._last_saved_at = datetime.now(UTC)
            self._last_error = None
            return True

    def dump_now(self, *, force: bool = False) -> bool:
        """Serialize + write synchronously. Returns True if a file was written."""
        rev = self.store._rev
        if not force and rev == self._last_rev:
            return False
        return self._commit(rev, self.store.export_json(), force=force)

    async def _dump_async(self) -> bool:
        rev = self.store._rev
        if rev == self._last_rev:
            return False
        # export_json never awaits => the state cannot change under it.
        payload = self.store.export_json()
        # The disk write goes to a worker thread so a slow disk never stalls
        # the event loop (measured 135 ms of the 242 ms total at 17.535 comments).
        return await asyncio.to_thread(self._commit, rev, payload, force=False)

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval_s)
            try:
                await self._dump_async()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - never let a dump kill the API
                self._last_error = str(exc)
                log.error(
                    "Ghi ảnh chụp kho vào %s thất bại (%s) — sẽ thử lại sau %.0f giây. "
                    "Ảnh chụp trước đó vẫn còn nguyên.",
                    self.path,
                    exc,
                    self.interval_s,
                )

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        """Start the periodic dump task (requires a running event loop)."""
        if self._task is not None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            log.warning(
                "Không có vòng lặp asyncio đang chạy — ảnh chụp kho chỉ được ghi khi gọi tay "
                "hoặc lúc tắt, KHÔNG ghi định kỳ."
            )
            return
        self._task = loop.create_task(self._loop(), name="livelift-snapshot")
        log.info(
            "Ảnh chụp kho ĐANG BẬT: ghi %s mỗi %.0f giây (chỉ ghi khi có thay đổi).",
            self.path,
            self.interval_s,
        )

    def stop(self) -> None:
        """Cancel the loop and take one final snapshot."""
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
        try:
            wrote = self.dump_now()
        except Exception as exc:  # noqa: BLE001 - shutdown must not raise
            self._last_error = str(exc)
            log.error(
                "Không ghi được ảnh chụp cuối vào %s (%s) — ảnh chụp gần nhất (%s) vẫn dùng được.",
                self.path,
                exc,
                self._last_saved_at or "chưa có",
            )
            return
        if wrote:
            log.info("Đã ghi ảnh chụp kho lần cuối trước khi tắt: %s", self.path)

    # -- reporting ---------------------------------------------------------
    def status(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "interval_s": self.interval_s,
            "running": self._task is not None and not self._task.done(),
            "last_saved_at": self._last_saved_at.isoformat() if self._last_saved_at else None,
            "restored_at_startup": self._restored,
            "last_error": self._last_error,
        }


def attach_snapshot(
    store: Store,
    *,
    enabled: bool | None = None,
    path: str | Path | None = None,
    interval_s: float | None = None,
) -> SnapshotManager | None:
    """Wire snapshotting onto ``store`` according to config. Returns the
    manager, or None when it does not apply (Postgres) or is switched off.

    Only the memory backend gets one: Postgres already survives a restart, and
    dumping a copy of it to a JSON file would be a second source of truth.
    The check is ``isinstance`` rather than ``backend == "memory"`` because
    snapshotting reads that class's own state directly — a different store that
    merely called itself "memory" would have nothing to serialize.
    """
    if not isinstance(store, InMemoryStore):
        return None
    if enabled is None or path is None or interval_s is None:
        from livelift.config import get_settings  # lazy: needs pydantic-settings

        settings = get_settings()
        enabled = settings.store_snapshot_enabled if enabled is None else enabled
        path = settings.store_snapshot_path if path is None else path
        interval_s = settings.store_snapshot_interval_s if interval_s is None else interval_s
    if not enabled:
        log.warning("%s", MEMORY_NO_SNAPSHOT_WARNING)
        return None
    manager = SnapshotManager(store, Path(path), interval_s)
    manager.restore()
    manager.start()
    store.snapshot = manager
    return manager


# ---------------------------------------------------------------------------
# What /health must say about data safety
# ---------------------------------------------------------------------------

MEMORY_NO_SNAPSHOT_WARNING = (
    "NGUY HIỂM — dữ liệu chỉ nằm trong RAM và KHÔNG có ảnh chụp: khởi động lại tiến "
    "trình là mất sạch mọi phiên. Ngày 11/09/2026 hệ thống đã mất 13 phiên live thật "
    "và 17.535 bình luận đúng theo cách này, không khôi phục được. Trước khi lên sóng "
    "thật hãy bật Postgres (STORE_BACKEND=postgres), hoặc ít nhất bật lại ảnh chụp "
    "(STORE_SNAPSHOT_ENABLED=true)."
)

POSTGRES_NOTE = (
    "Dữ liệu nằm trong PostgreSQL — khởi động lại tiến trình API không mất gì. "
    "Đây là chế độ dành cho phiên live thật."
)


def durability_info(store: Store) -> dict[str, Any]:
    """Answer the only question an operator needs before going live: *if this
    process dies right now, what do I lose?*

    ``/health`` merges this, so the answer is one HTTP call away instead of
    being folklore — the incident of 11/09/2026 was invisible until someone
    counted rows by hand.
    """
    backend = getattr(store, "backend", "unknown")
    if backend == "postgres":
        return {
            "storage_mode": "postgres",
            "durable": True,
            "storage_warning": None,
            "snapshot": None,
            "storage_note": POSTGRES_NOTE,
        }
    manager: SnapshotManager | None = getattr(store, "snapshot", None)
    if manager is None:
        return {
            "storage_mode": "memory",
            "durable": False,
            "storage_warning": MEMORY_NO_SNAPSHOT_WARNING,
            "snapshot": None,
            "storage_note": None,
        }
    return {
        "storage_mode": "memory+snapshot",
        "durable": False,
        "storage_warning": (
            f"Dữ liệu nằm trong RAM, có ảnh chụp mỗi {manager.interval_s:.0f} giây tại "
            f"{manager.path}. Khởi động lại chỉ mất tối đa {manager.interval_s:.0f} giây "
            "sự kiện cuối cùng, không mất cả phiên. Đủ cho demo và thi đấu; phiên live "
            "thật vẫn nên chạy STORE_BACKEND=postgres."
        ),
        "snapshot": manager.status(),
        "storage_note": None,
    }


# ---------------------------------------------------------------------------
# /health phải NÓI THẬT: hỏi kho trước khi tuyên bố bền vững (sự cố 13/09/2026)
# ---------------------------------------------------------------------------
#
# ``durability_info`` ở trên chỉ đọc TÊN backend. Ngày 13/09/2026 PostgreSQL
# chết hẳn (không ai nghe ở cổng 5432) mà /health vẫn trả 200 trong 0,002 giây
# với durable=true và câu "Dữ liệu nằm trong PostgreSQL — khởi động lại không
# mất gì". Người vận hành nhìn thấy màu xanh trong khi hệ thống không ghi được
# một dòng nào. Đó là bịa: tuyên bố một điều mà chưa hề kiểm tra.
#
# Từ nay: hỏi kho một câu rẻ, có hạn giờ, rồi mới dám nói. Giữ nguyên
# ``durability_info`` thuần (không I/O) — nó vẫn là hàm mô tả cấu hình, còn
# ``storage_health`` là hàm mô tả THỰC TẾ.

# Khóa theo id() nhưng GIỮ KÈM một weakref để kiểm chứng: id của một đối tượng
# đã bị thu hồi có thể được cấp lại cho đối tượng khác, và một kết quả ping của
# kho CŨ dán lên kho MỚI đúng là kiểu nói dối mà gói này đang đi sửa.
_ping_cache: dict[int, tuple[float, dict[str, Any], Any]] = {}
_ping_lock = threading.Lock()


def reset_store_ping_cache() -> None:
    """Xóa bộ nhớ đệm ping (dùng trong test và khi đổi kho giữa chừng)."""
    with _ping_lock:
        _ping_cache.clear()


def store_ping(
    store: Store,
    *,
    timeout_s: float = DEFAULT_PING_TIMEOUT_S,
    cache_s: float = DEFAULT_PING_CACHE_S,
) -> dict[str, Any]:
    """Hỏi kho "còn sống không?" và trả lời KÈM BẰNG CHỨNG.

    Trả về ``{"ok", "checked_at", "latency_ms", "cached", "timeout_s", "error"}``.
    Không bao giờ ném: người gọi là ``/health``, mà một trang sức khỏe tự sập
    thì vô dụng đúng lúc cần nhất.

    Đệm ``cache_s`` giây theo từng đối tượng kho: trang web hỏi /health liên tục
    nên nếu mỗi lần hỏi là một lần mở kết nối thì chính cái đồng hồ đo lại làm
    hỏng thứ nó đo. ``cached=True`` nói thẳng rằng con số này là lần đo trước —
    một kết quả cũ được dán nhãn thì vẫn là sự thật, giấu việc dán nhãn mới là
    nói dối.
    """
    key = id(store)
    now = time.monotonic()
    try:
        ref: Any = weakref.ref(store)
    except TypeError:  # pragma: no cover - kho không cho weakref ⇒ không đệm
        ref = None
    if cache_s > 0 and ref is not None:
        with _ping_lock:
            hit = _ping_cache.get(key)
        if hit is not None and hit[2]() is store and (now - hit[0]) < cache_s:
            return {**hit[1], "cached": True}

    t0 = time.perf_counter()
    ping = getattr(store, "ping", None)
    result: dict[str, Any]
    if ping is None:
        # Kho không biết tự kiểm tra: nói ĐÚNG điều đó, đừng đoán là nó ổn.
        result = {
            "ok": False,
            "latency_ms": 0.0,
            "timeout_s": timeout_s,
            "error": "Kho này không hỗ trợ kiểm tra kết nối (thiếu phương thức ping).",
        }
    else:
        try:
            ping(timeout_s)
            result = {
                "ok": True,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
                "timeout_s": timeout_s,
                "error": None,
            }
        except StoreUnavailableError as exc:
            result = {
                "ok": False,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
                "timeout_s": timeout_s,
                "error": exc.cause_text or exc.message,
            }
        except Exception as exc:  # noqa: BLE001 - /health không được tự sập
            result = {
                "ok": False,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
                "timeout_s": timeout_s,
                "error": f"{type(exc).__name__}: {exc}".strip(),
            }
    result["checked_at"] = datetime.now(UTC).isoformat()
    if cache_s > 0 and ref is not None:
        with _ping_lock:
            # Dọn các mục có kho đã bị thu hồi: một tiến trình chỉ có một kho
            # nên bộ đệm không bao giờ lớn, nhưng một tiến trình dựng nhiều kho
            # (chính là bộ test) thì không có lý do gì để giữ rác lại.
            for k in [k for k, v in _ping_cache.items() if v[2]() is None]:
                del _ping_cache[k]
            _ping_cache[key] = (now, result, ref)
    return {**result, "cached": False}


def storage_health(
    store: Store,
    *,
    timeout_s: float = DEFAULT_PING_TIMEOUT_S,
    cache_s: float = DEFAULT_PING_CACHE_S,
) -> dict[str, Any]:
    """``durability_info`` + bằng chứng kho còn sống. Đây là thứ /health trả.

    Thêm hai trường so với ``durability_info``:

    * ``storage_ok`` — kho có trả lời hay không (``None`` nếu không cần hỏi);
    * ``storage_ping`` — lần đo: độ trễ, hạn giờ, lỗi thô, có phải bản đệm.

    Với ``memory``/``memory+snapshot``: kho nằm trong chính tiến trình này, hỏi
    nó cũng chỉ là hỏi chính mình, nên phần còn lại của thân giữ NGUYÊN như
    trước (cảnh báo mất dữ liệu khi khởi động lại vẫn là cảnh báo đúng).

    Với ``postgres`` mà ping thất bại: ``durable`` hạ xuống ``False``,
    ``storage_note`` (câu "khởi động lại không mất gì") bị GỠ, và
    ``storage_warning`` nói ra điều đang thật sự xảy ra.
    """
    info = durability_info(store)
    ping = store_ping(store, timeout_s=timeout_s, cache_s=cache_s)
    if info["storage_mode"] != "postgres":
        return {**info, "storage_ok": ping["ok"], "storage_ping": ping}
    if ping["ok"]:
        return {**info, "storage_ok": True, "storage_ping": ping}
    return {
        **info,
        "durable": False,
        "storage_ok": False,
        "storage_warning": STORE_DOWN_WARNING,
        "storage_note": None,
        "storage_ping": ping,
    }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_store(backend: str | None = None) -> Store:
    """Build the store selected by ``backend`` or the STORE_BACKEND env var
    ("memory" default | "postgres")."""
    raw = backend if backend is not None else os.environ.get("STORE_BACKEND")
    name = (raw or "memory").strip().lower()
    if name == "postgres":
        from livelift.config import get_settings  # lazy: needs pydantic-settings

        s = get_settings()
        # Hạn giờ đi kèm kho ngay từ lúc dựng: một kho Postgres không có hạn
        # giờ là một kho biết treo 30 giây (sự cố 13/09/2026).
        return PostgresStore(
            s.database_url,
            connect_timeout_s=s.store_connect_timeout_s,
            pool_timeout_s=s.store_pool_timeout_s,
            statement_timeout_s=s.store_statement_timeout_s,
        )
    if name != "memory":
        raise ValueError(f"unknown STORE_BACKEND: {name!r} (expected 'memory' or 'postgres')")
    if raw is None and _database_url_is_configured():
        # The exact trap of incident 25/08/2026: a database is configured, it
        # is probably even running, and the API quietly keeps everything in RAM
        # because the backend is chosen by a DIFFERENT variable. One WARNING
        # line per process start is cheap next to what silence cost on
        # 11/09/2026.
        log.warning(
            "Đã cấu hình DATABASE_URL nhưng CHƯA đặt STORE_BACKEND — API chạy kho "
            "'memory', dữ liệu nằm trong RAM và mất khi khởi động lại. Muốn dùng cơ sở "
            "dữ liệu thì đặt STORE_BACKEND=postgres (xem docs/luu-tru-du-lieu.md)."
        )
    return InMemoryStore()


def _database_url_is_configured() -> bool:
    """True when someone DELIBERATELY pointed this deployment at a database.

    Checking only ``os.environ`` would miss the most common local setup — and
    it is exactly the one that bit us: ``.env`` carries DATABASE_URL, nobody
    sets STORE_BACKEND, and the API runs on RAM without a word. But
    ``Settings.database_url`` has a non-empty built-in default, so "non-empty"
    alone would be true always and the warning would mean nothing. Compare
    against that default instead: different value ⇒ somebody configured it.
    """
    if os.environ.get("DATABASE_URL"):
        return True
    try:
        from livelift.config import Settings, get_settings

        default = Settings.model_fields["database_url"].default
        return get_settings().database_url != default
    except Exception:  # noqa: BLE001 - a config problem must not break startup
        return False
