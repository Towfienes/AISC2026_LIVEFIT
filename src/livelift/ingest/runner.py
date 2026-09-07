"""Ingest runner: platform client -> PII scrub -> LiveLift API sink.

Usage:

    python -m livelift.ingest.runner --platform youtube --source-id VIDEO_ID \\
        --session-id 7b0e... --api-url http://localhost:8000

One process per live session. Two loops run concurrently (comments and
viewer ticks) plus a heartbeat that logs counts — only counts, never
content — every 60 seconds. Ctrl+C shuts down gracefully.

The PII guarantee does not live here: :class:`livelift.ingest.base.ApiSink`
scrubs inside ``post_comment`` before any transmit, so no wiring mistake in
this file can leak raw text.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
from dataclasses import dataclass

import httpx

from livelift.ingest.base import ApiSink, IngestSink
from livelift.ingest.facebook import FacebookLiveClient
from livelift.ingest.youtube import YouTubeLiveChatClient

logger = logging.getLogger("livelift.ingest.runner")

HEARTBEAT_EVERY_S = 60.0

PlatformClient = YouTubeLiveChatClient | FacebookLiveClient


@dataclass
class Counters:
    """Shared run counters. Counts only — no content ever stored here."""

    comments_seen: int = 0
    comments_posted: int = 0
    ticks_seen: int = 0
    ticks_posted: int = 0
    post_failures: int = 0


async def _pump_comments(
    client: PlatformClient, source_id: str, sink: IngestSink, c: Counters
) -> None:
    async for comment in client.iter_comments(source_id):
        c.comments_seen += 1
        if await sink.post_comment(comment):
            c.comments_posted += 1
        else:
            c.post_failures += 1


async def _pump_ticks(
    client: PlatformClient, source_id: str, sink: IngestSink, c: Counters
) -> None:
    async for tick in client.iter_viewers(source_id):
        c.ticks_seen += 1
        if await sink.post_tick(tick):
            c.ticks_posted += 1
        else:
            c.post_failures += 1


async def _heartbeat(
    c: Counters,
    client: PlatformClient | None = None,
    every_s: float = HEARTBEAT_EVERY_S,
) -> None:
    while True:
        await asyncio.sleep(every_s)
        # The platform client records its most recent poll error (None when
        # healthy) — surfacing it here means a stuck loop (expired token,
        # exhausted quota) is visible in every heartbeat, not only in the
        # one log line at the moment it broke.
        last_error = getattr(client, "last_error", None)
        logger.info(
            "heartbeat: comments seen=%d posted=%d | ticks seen=%d posted=%d | failures=%d"
            " | lỗi gần nhất: %s",
            c.comments_seen,
            c.comments_posted,
            c.ticks_seen,
            c.ticks_posted,
            c.post_failures,
            last_error or "không có",
        )


def _build_client(platform: str) -> PlatformClient:
    if platform == "youtube":
        return YouTubeLiveChatClient()
    if platform == "facebook":
        return FacebookLiveClient()
    raise ValueError(f"unsupported platform: {platform}")


async def _run(platform: str, source_id: str, session_id: str, api_url: str) -> None:
    client = _build_client(platform)
    sink = ApiSink(api_url=api_url, session_id=session_id)
    counters = Counters()
    tasks = [
        asyncio.create_task(_pump_comments(client, source_id, sink, counters), name="comments"),
        asyncio.create_task(_pump_ticks(client, source_id, sink, counters), name="ticks"),
        asyncio.create_task(_heartbeat(counters, client), name="heartbeat"),
    ]
    try:
        # First finished pump task ends the run (heartbeat never finishes on
        # its own); a crashed task surfaces its exception here.
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            exc = task.exception()
            if exc is not None:
                raise exc
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await sink.aclose()
        await client.aclose()
        logger.info(
            "final: comments seen=%d posted=%d | ticks seen=%d posted=%d | failures=%d",
            counters.comments_seen,
            counters.comments_posted,
            counters.ticks_seen,
            counters.ticks_posted,
            counters.post_failures,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m livelift.ingest.runner",
        description="Stream one platform's live comments/viewers into the LiveLift API.",
    )
    parser.add_argument("--platform", required=True, choices=["youtube", "facebook"])
    parser.add_argument(
        "--source-id",
        required=True,
        help="YouTube video id or Facebook live-video id",
    )
    parser.add_argument("--session-id", required=True, help="LiveLift session uuid")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info(
        "starting ingest: platform=%s source=%s session=%s api=%s",
        args.platform,
        args.source_id,
        args.session_id,
        args.api_url,
    )
    try:
        asyncio.run(_run(args.platform, args.source_id, args.session_id, args.api_url))
    except KeyboardInterrupt:
        logger.info("Ctrl+C received — ingest stopped cleanly")
        return 0
    except httpx.HTTPError as exc:
        logger.error("ingest aborted on transport error: %s", type(exc).__name__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
