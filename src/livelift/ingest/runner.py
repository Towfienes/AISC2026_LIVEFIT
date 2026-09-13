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

from livelift.config import get_settings
from livelift.ingest.base import ApiSink, IngestSink
from livelift.ingest.facebook import FacebookLiveClient
from livelift.ingest.shopee import ShopeeLiveClient
from livelift.ingest.youtube import YouTubeLiveChatClient
from livelift.ingest.youtube_ytdlp import YouTubeYtdlpClient

logger = logging.getLogger("livelift.ingest.runner")

HEARTBEAT_EVERY_S = 60.0

PlatformClient = YouTubeLiveChatClient | FacebookLiveClient | YouTubeYtdlpClient | ShopeeLiveClient

YOUTUBE_BACKENDS = ("api", "ytdlp")


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
    sink: IngestSink | None = None,
) -> None:
    while True:
        await asyncio.sleep(every_s)
        # Kho chết giữa phiên (13/09): nếu API/kho không nhận nữa, sink ghi
        # thẳng vào spool và vòng đọc vẫn chạy êm — đúng cái làm sự cố trở
        # nên VÔ HÌNH. Heartbeat phải hét lên đều đặn, vì đây là dòng log duy
        # nhất người vận hành còn nhìn khi mọi thứ khác trông vẫn bình thường.
        if getattr(sink, "spool_mode", False):
            logger.error(
                "BÁO ĐỘNG: máy chủ/kho KHÔNG nhận dữ liệu — %d bản ghi đang nằm trong %s, "
                "CHƯA có trong cơ sở dữ liệu. Sửa kho xong phải nạp bù: %s",
                getattr(sink, "spooled", 0),
                getattr(sink, "spool_path", "?"),
                getattr(sink, "replay_command", "python -m livelift.ingest.spool_replay <file>"),
            )
        # The platform client records its most recent poll error (None when
        # healthy) — surfacing it here means a stuck loop (expired token,
        # exhausted quota) is visible in every heartbeat, not only in the
        # one log line at the moment it broke. The API-usage percentage (read
        # from Facebook's X-App-Usage/X-Page-Usage headers) is the early
        # warning for the *other* way a session dies: hitting the rate limit.
        last_error = getattr(client, "last_error", None)
        usage_pct = getattr(client, "last_usage_pct", None)
        spooled = getattr(sink, "spooled", 0)
        dropped = getattr(sink, "dropped", 0)
        logger.info(
            "heartbeat: comments seen=%d posted=%d | ticks seen=%d posted=%d | failures=%d"
            " | tải API: %s | spool: %s | mất hẳn: %d | lỗi gần nhất: %s",
            c.comments_seen,
            c.comments_posted,
            c.ticks_seen,
            c.ticks_posted,
            c.post_failures,
            "không rõ" if usage_pct is None else f"{usage_pct:.0f}%",
            (
                f"{spooled} bản ghi chờ nạp bù"
                if spooled
                else "không có (máy chủ đang nhận bình thường)"
            ),
            dropped,
            last_error or getattr(sink, "last_error", None) or "không có",
        )


def _build_client(platform: str) -> PlatformClient:
    """Pick the platform client, honoring INGEST_YOUTUBE_BACKEND.

    ``api`` (default) keeps the historical behavior: the official Data API,
    which needs YOUTUBE_API_KEY. ``ytdlp`` reads the same public live chat with
    yt-dlp and no credential at all — the path to use when the team has no key
    (see :mod:`livelift.ingest.youtube_ytdlp` for the measured tradeoffs).
    """
    if platform == "youtube":
        backend = (get_settings().ingest_youtube_backend or "api").strip().lower()
        if backend not in YOUTUBE_BACKENDS:
            raise ValueError(
                f"INGEST_YOUTUBE_BACKEND không hợp lệ: {backend!r} — "
                f"chỉ nhận {' hoặc '.join(YOUTUBE_BACKENDS)}"
            )
        if backend == "ytdlp":
            logger.warning(
                "YouTube backend = yt-dlp: KHÔNG cần API key, nhưng CÁCH TRUY CẬP NÀY "
                "TRÁI Điều khoản dịch vụ của YouTube (robots.txt chặn /live_chat và "
                "/youtubei/). Chỉ dùng cho phiên của chính nhóm / kiểm thử kỹ thuật / "
                "dự phòng khi mất key, và PHẢI khai báo trong phần phương pháp nếu dữ "
                "liệu này vào bài. Đường chuẩn: xin YOUTUBE_API_KEY (miễn phí, ~10 phút) "
                "rồi đặt INGEST_YOUTUBE_BACKEND=api."
            )
            logger.info(
                "Độ trễ giao tin đo thật ~25s (p90 ~37s); dấu thời gian bình luận vẫn là "
                "giờ nền tảng nên không lệch khối. Chạy runner quá khối cuối ít nhất 1 phút."
            )
            return YouTubeYtdlpClient()
        return YouTubeLiveChatClient()
    if platform == "facebook":
        return FacebookLiveClient()
    if platform == "shopee":
        # Đường CHÍNH THỨC duy nhất trong repo vừa cho bình luận vừa cho
        # tín hiệu chuyển đổi (gmv/orders/atc) — xem
        # docs/nen-tang-ho-tro.md §4. Chỉ đọc được shop ĐÃ ủy quyền.
        logger.info(
            "Shopee Live: API chính thức (Open Platform v2), hợp Điều khoản dịch vụ. "
            "Chỉ đọc được phiên của shop đã ủy quyền cho app này. Nhịp poll bình luận "
            "PHẢI < 10s vì get_latest_comment_list chỉ trả cửa sổ 10 giây gần nhất."
        )
        return ShopeeLiveClient()
    raise ValueError(f"unsupported platform: {platform}")


async def _run(platform: str, source_id: str, session_id: str, api_url: str) -> None:
    client = _build_client(platform)
    sink = ApiSink(api_url=api_url, session_id=session_id)
    counters = Counters()
    tasks = [
        asyncio.create_task(_pump_comments(client, source_id, sink, counters), name="comments"),
        asyncio.create_task(_pump_ticks(client, source_id, sink, counters), name="ticks"),
        asyncio.create_task(_heartbeat(counters, client, sink=sink), name="heartbeat"),
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
        # Kết thúc phiên mà spool còn bản ghi = cơ sở dữ liệu đang THIẾU dữ
        # liệu của chính phiên vừa chạy. Không được để dòng cuối cùng của
        # runner nói "xong" khi chưa xong.
        if sink.spooled:
            logger.error(
                "CHƯA XONG: %d bản ghi của phiên này nằm trong %s và CHƯA vào cơ sở dữ liệu. "
                "Chạy ngay sau khi kho sống lại: %s",
                sink.spooled,
                sink.spool_path,
                sink.replay_command,
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m livelift.ingest.runner",
        description="Stream one platform's live comments/viewers into the LiveLift API.",
    )
    parser.add_argument("--platform", required=True, choices=["youtube", "facebook", "shopee"])
    parser.add_argument(
        "--source-id",
        required=True,
        help="YouTube video id, Facebook live-video id, hoặc Shopee Live session_id",
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
