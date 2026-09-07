"""Replay a spool file left behind by :class:`livelift.ingest.base.ApiSink`.

Usage:

    python -m livelift.ingest.spool_replay data/spool/<session_id>.jsonl \\
        --api-base http://localhost:8000

Each line is ``{"kind": ..., "path": "/sessions/<id>/comments", "payload":
{...}}`` with an already-scrubbed payload. Records are re-POSTed in file
order; the server's idempotency — (platform, ext_id) for comments, the
(session, ts_bucket) upsert for ticks — makes replaying the same file twice
safe, so the input file is never modified. Exit code 0 when every record was
accepted, 1 otherwise (re-run later to retry the rest).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

import httpx

logger = logging.getLogger("livelift.ingest.spool_replay")


async def replay_file(
    spool_path: Path,
    api_base: str,
    token: str = "",
    timeout_s: float = 10.0,
    client: httpx.AsyncClient | None = None,
) -> tuple[int, int]:
    """POST every record in ``spool_path``; returns (n_ok, n_failed).

    An injected ``client`` makes this testable without network access (it is
    then NOT closed here); the bearer header is sent per-request either way.
    """
    base = api_base.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=timeout_s)
    n_ok = n_failed = 0
    try:
        for line_no, line in enumerate(
            spool_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                path, payload = record["path"], record["payload"]
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.error("dòng %d không đúng định dạng spool — bỏ qua", line_no)
                n_failed += 1
                continue
            try:
                resp = await client.post(base + path, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                logger.error("dòng %d: POST %s lỗi mạng (%s)", line_no, path, type(exc).__name__)
                n_failed += 1
                continue
            if resp.status_code < 400:
                n_ok += 1
            else:
                logger.error("dòng %d: POST %s -> HTTP %d", line_no, path, resp.status_code)
                n_failed += 1
    finally:
        if owns_client:
            await client.aclose()
    return n_ok, n_failed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m livelift.ingest.spool_replay",
        description="Gửi lại các bản ghi spool (comment/tick) vào LiveLift API.",
    )
    parser.add_argument("file", help="đường dẫn file spool .jsonl (data/spool/<session_id>.jsonl)")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument(
        "--token",
        default=None,
        help="token ingest (mặc định: đọc INGEST_TOKEN từ môi trường/.env)",
    )
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    spool_path = Path(args.file)
    if not spool_path.is_file():
        logger.error("không tìm thấy file spool: %s", spool_path)
        return 1
    token = args.token
    if token is None:
        from livelift.config import get_settings

        token = get_settings().ingest_token
    n_ok, n_failed = asyncio.run(replay_file(spool_path, args.api_base, token=token))
    logger.info("gửi lại xong: thành công=%d, thất bại=%d (nguồn: %s)", n_ok, n_failed, spool_path)
    if n_failed:
        logger.error(
            "còn %d bản ghi chưa vào được API — chạy lại lệnh này sau khi API hoạt động "
            "(gửi trùng an toàn nhờ khóa idempotency)",
            n_failed,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
