"""VLiveBench collector: capture one public TikTok LIVE room to scrubbed JSONL.

ISOLATED mini-project (see README.md): runs in its own venv/process, writes
only to ``collectors/tiktok_public/data/`` (gitignored), and nothing in
``src/livelift`` may ever import from here. The one allowed dependency
direction is collectors -> livelift, used solely for the PII filter.

Privacy at capture time (HARD project rule 1):
- ``livelift.ingest.pii.scrub`` runs on every comment BEFORE the write; raw
  text never touches disk and is never logged.
- No commenter identity is captured — records carry only the (public) host
  room name, a timestamp, the scrubbed text, and the event type.

The TikTokLive library is reverse-engineered and may break without notice;
this script therefore reconnects with exponential backoff and treats every
attribute of the event objects defensively.

Usage:
    python collect.py --username some_public_channel [--max-minutes 90]
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from livelift.ingest.pii import scrub
except ImportError:  # pragma: no cover — setup guidance for a fresh clone
    print(
        "livelift is not installed in this venv. From collectors/tiktok_public run:\n"
        "    pip install -e ../..",
        file=sys.stderr,
    )
    raise

try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import CommentEvent, ConnectEvent, GiftEvent, RoomUserSeqEvent
except ImportError:  # pragma: no cover
    print(
        "TikTokLive is not installed. From collectors/tiktok_public run:\n"
        "    pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise

logger = logging.getLogger("vlivebench.collect")

DATA_DIR = Path(__file__).resolve().parent / "data"
RECONNECT_BASE_S = 5.0
RECONNECT_MAX_S = 300.0


class JsonlWriter:
    """One JSONL file per (re)connect session, flushed per line."""

    def __init__(self, out_dir: Path, room: str) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safe_room = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in room)
        self.path = out_dir / f"{safe_room}_{stamp}.jsonl"
        self._fh = self.path.open("a", encoding="utf-8")
        self.lines = 0

    def write(self, record: dict[str, Any]) -> None:
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()
        self.lines += 1

    def close(self) -> None:
        self._fh.close()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _record(room: str, event_type: str, text: str, value: float | None = None) -> dict[str, Any]:
    """Build one output record. ``text`` is scrubbed HERE, before any write."""
    result = scrub(text)
    rec: dict[str, Any] = {
        "ts": _now_iso(),
        "room": room,
        "text_scrubbed": result.text,
        "event_type": event_type,
    }
    if value is not None:
        rec["value"] = value
    return rec


async def _collect_once(username: str, writer: JsonlWriter, stop_at: float | None) -> None:
    """One connect -> capture -> disconnect cycle."""
    client = TikTokLiveClient(unique_id=username)
    room = username.lstrip("@")

    @client.on(ConnectEvent)
    async def on_connect(_: Any) -> None:
        logger.info("connected to @%s -> %s", room, writer.path.name)

    @client.on(CommentEvent)
    async def on_comment(event: Any) -> None:
        text = getattr(event, "comment", None)
        if text:
            writer.write(_record(room, "comment", str(text)))

    @client.on(GiftEvent)
    async def on_gift(event: Any) -> None:
        gift = getattr(event, "gift", None)
        name = getattr(gift, "name", None) or "unknown_gift"
        count = getattr(event, "repeat_count", None)
        writer.write(_record(room, "gift", str(name), float(count) if count is not None else None))

    @client.on(RoomUserSeqEvent)
    async def on_viewers(event: Any) -> None:
        total = getattr(event, "total", None)
        if total is None:
            total = getattr(event, "m_total", None)
        if total is not None:
            writer.write(_record(room, "viewer_count", "", float(total)))

    stopper: asyncio.Task[None] | None = None
    if stop_at is not None:
        remaining = stop_at - asyncio.get_running_loop().time()
        if remaining <= 0:
            return

        async def _stop_later() -> None:
            await asyncio.sleep(remaining)
            logger.info("max duration reached; disconnecting")
            with contextlib.suppress(Exception):
                await client.disconnect()

        stopper = asyncio.create_task(_stop_later())

    try:
        await client.connect()  # runs until the room ends or we disconnect
    finally:
        if stopper is not None:
            stopper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stopper
        with contextlib.suppress(Exception):
            await client.disconnect()


async def collect(username: str, out_dir: Path, max_minutes: float | None) -> None:
    """Reconnect loop: a fresh client and a fresh JSONL file per attempt."""
    loop = asyncio.get_running_loop()
    stop_at = loop.time() + max_minutes * 60 if max_minutes else None
    backoff = RECONNECT_BASE_S
    while True:
        if stop_at is not None and loop.time() >= stop_at:
            logger.info("max duration reached; stopping")
            return
        writer = JsonlWriter(out_dir, username)
        try:
            await _collect_once(username, writer, stop_at)
            logger.info("stream ended normally (%d lines captured)", writer.lines)
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # reverse-engineered lib: anything can happen
            logger.warning(
                "disconnected (%s) after %d lines; reconnecting in %.0fs",
                type(exc).__name__,
                writer.lines,
                backoff,
            )
        finally:
            writer.close()
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, RECONNECT_MAX_S)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture one public TikTok LIVE room to scrubbed JSONL (VLiveBench)."
    )
    parser.add_argument("--username", required=True, help="public @username of the LIVE room")
    parser.add_argument("--out-dir", default=str(DATA_DIR), help="output directory (gitignored)")
    parser.add_argument(
        "--max-minutes", type=float, default=None, help="stop after this many minutes"
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        asyncio.run(collect(args.username, Path(args.out_dir), args.max_minutes))
    except KeyboardInterrupt:
        logger.info("Ctrl+C — collector stopped cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
