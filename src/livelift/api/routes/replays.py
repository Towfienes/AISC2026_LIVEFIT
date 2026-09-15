"""Replay analysis: ingest the chat replay of a finished YouTube VOD.

POST /replays/youtube starts a background job that downloads the chat replay
(yt-dlp), scrubs every comment (hard rule 1: scrub BEFORE any store), and
materializes an *analysis-only* session:

- ``platform="replay"``, ``status="ended"``, ``design={"analysis_only": true}``
- ``start_ts`` backdated by the video duration so comment timestamps line up
- NO experiment blocks — the original broadcast had no assignment schedule,
  so there is nothing to randomize over. This is intentional: the session is
  OBSERVATIONAL and the report route labels it as such (never experiment
  language, per the E2-04 corollary).

Scale note: the job registry is a module-level dict and the pipeline runs in
a FastAPI BackgroundTask on the single API process. Fine at pilot scale (a
handful of concurrent analyses); a queue worker would replace it beyond that.

Data hygiene: the downloaded ``.live_chat.json`` contains raw author names.
It lives only in a per-job temp dir and is deleted immediately after parsing —
it is never persisted, copied, or logged.
"""

from __future__ import annotations

import logging
import math
import shutil
import tempfile
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, field_validator

from livelift.api import service
from livelift.api.auth import chi_token
from livelift.api.service import StoreDep
from livelift.api.store import Store
from livelift.ingest.pii import scrub
from livelift.ingest.youtube_replay import (
    download_chat_replay,
    extract_video_id,
    parse_live_chat_file,
    parse_live_chat_reactions_file,
    synth_ticks_from_comments,
)
from livelift.nlp.intent import classify_with_confidence

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_COMMENTS = 20_000
TICK_S = 30

#: A video can advertise a ``live_chat`` track, download it, and have nothing
#: in it (measured 10/09/2026 on a 715-minute brand stream: the track existed,
#: the parsed chat was empty). The job still succeeded and reported
#: ``n_comments=0`` with no detail, so the operator got a session that looked
#: healthy and was empty. Say it instead.
EMPTY_CHAT_DETAIL = (
    "Chat replay tải về KHÔNG có bình luận nào — phiên phân tích rỗng. "
    "Thường gặp khi luồng có bật chat nhưng không ai nhắn, hoặc chat replay đã bị "
    "gỡ. Không có gì để phân tích: hãy chọn buổi live khác."
)

JobStatus = Literal["queued", "downloading", "ingesting", "done", "error"]


@dataclass
class JobState:
    """In-process state of one replay-analysis job (pilot-scale registry)."""

    job_id: str
    url: str
    status: JobStatus = "queued"
    detail: str | None = None
    session_id: str | None = None
    n_comments: int | None = None
    video_title: str | None = None


# Module-level registry: {job_id: JobState}. Single-process, pilot scale —
# jobs do not survive a restart (acceptable: re-submitting the URL re-runs
# the whole idempotent pipeline).
_JOBS: dict[str, JobState] = {}


class ReplayRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url phải bắt đầu bằng http:// hoặc https://")
        return v


class ReplayJobAccepted(BaseModel):
    job_id: str


class ReplayJobOut(BaseModel):
    job_id: str
    status: JobStatus
    detail: str | None = None
    session_id: str | None = None
    n_comments: int | None = None
    video_title: str | None = None


def _run_job(job_id: str, url: str, store: Store) -> None:
    """Full pipeline: download → parse → create session → scrub+store comments
    → synthetic comment-rate ticks. Runs in a BackgroundTask; every failure
    lands in the job registry as status='error' with a Vietnamese detail."""
    job = _JOBS[job_id]
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"livelift-replay-{job_id[:8]}-"))
    try:
        job.status = "downloading"
        from livelift.config import get_settings

        cookies_browser = get_settings().ytdlp_cookies_from_browser or None
        result = download_chat_replay(url, tmp_dir, cookies_from_browser=cookies_browser)
        job.video_title = result.video_title or None
        if result.error is not None or result.chat_path is None:
            job.status = "error"
            job.detail = result.error or "Không tải được chat replay"
            return

        job.status = "ingesting"
        comments = parse_live_chat_file(result.chat_path)
        # Paid events (Super Chat / gift / sticker / membership) come from the
        # SAME file and must be read before it is deleted. The parser reads
        # only offset, kind, public amount and event id — never the author.
        reactions = parse_live_chat_reactions_file(result.chat_path)
        # Data hygiene: the raw file contains author names — delete it the
        # moment parsing is done; only (offset, text) pairs remain in memory.
        result.chat_path.unlink(missing_ok=True)

        truncated = len(comments) > MAX_COMMENTS
        if truncated:
            comments = comments[:MAX_COMMENTS]

        duration_s = result.duration_s
        if duration_s <= 0:
            duration_s = comments[-1][0] if comments else 0.0
        duration_s = max(duration_s, 60.0)

        now = service.now_utc()
        start_ts = now - timedelta(seconds=duration_s)
        title = f"Phân tích: {result.video_title or url}"
        session = store.create_session(
            {
                "session_id": service.new_id(),
                "platform": "replay",
                "title": title,
                "mode": "auto",
                "status": "ended",
                "planned_duration_min": max(1, math.ceil(duration_s / 60)),
                "host_id": None,
                "start_ts": None,
                "end_ts": None,
                "design": None,
                "created_at": now,
            }
        )
        session_id = session["session_id"]
        # NO schedule/blocks are created — analysis sessions are observational
        # by design (the guard in reports.py depends on this).
        store.update_session(
            session_id,
            {
                "status": "ended",
                "start_ts": start_ts,
                "end_ts": now,
                "design": {
                    "analysis_only": True,
                    "source_url": url,
                    # Gói UI-KOL: the desk embeds the original video next to
                    # the analysis. Prefer the canonical id from yt-dlp
                    # metadata; fall back to parsing the submitted URL. None
                    # when neither knows — the UI then states the gap instead
                    # of showing a black frame.
                    "video_id": result.video_id or extract_video_id(url),
                },
            },
        )

        for offset_s, text in comments:
            scrubbed = scrub(text)  # BEFORE any store — hard rule 1
            intent, intent_confidence = classify_with_confidence(scrubbed.text)
            store.add_comment(
                session_id,
                {
                    "comment_id": service.new_id(),
                    "session_id": session_id,
                    "block_id": None,
                    "ts": start_ts + timedelta(seconds=offset_s),
                    "text_scrubbed": scrubbed.text,
                    "pii_kinds": sorted({m.kind for m in scrubbed.matches}),
                    "intent_label": intent,
                    "intent_confidence": intent_confidence,
                    "sentiment": None,
                },
            )

        # Paid events (migration 0007): most VN sales streams have NONE
        # (measured 0 Super Chat across the 11-replay live-fire corpus) — an
        # empty list here is a legitimate outcome that the signal matrix
        # declares as missing-with-reason, never as a fake 0.
        for reaction in reactions:
            store.add_reaction(
                session_id,
                {
                    "reaction_id": service.new_id(),
                    "session_id": session_id,
                    "ts_utc": start_ts + timedelta(seconds=reaction.offset_s),
                    "kind": reaction.kind,
                    "amount": reaction.amount,
                    "currency": reaction.currency,
                    "platform": "youtube",
                    "ext_id": reaction.ext_id,
                },
            )

        # Viewer counts are NOT available retroactively for a VOD — ticks
        # carry comment tempo only; viewers stays 0.0 and the UI must label
        # the series as unavailable (see synth_ticks_from_comments docstring).
        for bucket_start_s, rate in synth_ticks_from_comments(comments, duration_s, TICK_S):
            store.add_tick(
                session_id,
                {
                    "ts_bucket": start_ts + timedelta(seconds=bucket_start_s),
                    "viewers": 0.0,
                    "comment_rate": rate,
                    "like_rate": 0.0,
                    "click_count": 0,
                    "pinned_product_id": None,
                },
            )

        job.session_id = session_id
        job.n_comments = len(comments)
        job.status = "done"
        if truncated:
            job.detail = f"Đã cắt bớt: chỉ nhập {MAX_COMMENTS} bình luận đầu tiên"
        elif not comments:
            job.detail = EMPTY_CHAT_DETAIL
        else:
            job.detail = None
    except Exception:
        logger.exception("replay job %s failed", job_id)
        job.status = "error"
        job.detail = "Lỗi không mong muốn khi xử lý chat replay — xem log máy chủ"
    finally:
        # Belt and braces: nothing from the download may outlive the job.
        shutil.rmtree(tmp_dir, ignore_errors=True)


@chi_token
@router.post("/replays/youtube", response_model=ReplayJobAccepted, status_code=202)
def start_replay_analysis(
    body: ReplayRequest, background: BackgroundTasks, store: StoreDep
) -> ReplayJobAccepted:
    """Accept a YouTube VOD/live URL and start the analysis job (202)."""
    job_id = service.new_id()
    _JOBS[job_id] = JobState(job_id=job_id, url=body.url)
    background.add_task(_run_job, job_id, body.url, store)
    return ReplayJobAccepted(job_id=job_id)


@router.get("/replays/jobs/{job_id}", response_model=ReplayJobOut)
def get_replay_job(job_id: str) -> ReplayJobOut:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ phân tích")
    return ReplayJobOut(
        job_id=job.job_id,
        status=job.status,
        detail=job.detail,
        session_id=job.session_id,
        n_comments=job.n_comments,
        video_title=job.video_title,
    )
