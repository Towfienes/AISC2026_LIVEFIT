"""YouTube VOD chat-replay pipeline: parser, tick synthesis, and the
/replays/* routes end-to-end on the in-memory store (download monkeypatched).

Hard-rule coverage:
- rule 1 (PII): comment text is scrubbed before store; author names from the
  yt-dlp file never leave the parser.
- E2-04 corollary: the resulting session is observational — its report has no
  diff_in_means, no blocks, and carries the observational label.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.routes import replays
from livelift.api.store import InMemoryStore
from livelift.ingest.youtube_replay import (
    ERR_NO_CHAT,
    DownloadResult,
    parse_live_chat_file,
    parse_live_chat_line,
    synth_ticks_from_comments,
)

FIXTURE = Path(__file__).parent / "data" / "live_chat_fixture.jsonl"

AUTHOR_NAMES = [
    "Nguyen Van A",
    "Tran Thi B",
    "Le Van C",
    "Pham Thi D",
    "Hoang Van E",
    "Vo Thi F",
    "Dang Van G",
    "Bui Thi H",
    "Ngo Van I",
]


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    replays._JOBS.clear()
    with TestClient(app) as c:
        yield c
    replays._JOBS.clear()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def test_parse_file_sorted_text_only_no_authors():
    comments = parse_live_chat_file(FIXTURE)
    offsets = [c[0] for c in comments]
    assert offsets == sorted(offsets)
    # 9 fixture lines: 7 text messages, 1 membership + 1 sticker skipped
    assert offsets == [5.0, 15.0, 30.0, 45.0, 90.0, 120.0, 150.0]
    assert all(isinstance(c, tuple) and len(c) == 2 for c in comments)
    joined = " ".join(text for _off, text in comments)
    for name in AUTHOR_NAMES:
        assert name not in joined  # author fields must never leave the parser
    assert "UCauthor" not in joined


def test_parse_line_offset_str_and_int_and_toplevel_fallback():
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    # line 4 has an int offset inside replayChatItemAction
    off, text = parse_live_chat_line(lines[3])
    assert off == 90.0
    assert text == "áo này đẹp quá ❤"  # standard emoji concatenated via emojiId
    # line 8 carries the offset only at the top level (fallback path)
    off, text = parse_live_chat_line(lines[7])
    assert off == 30.0
    assert "quận 7" in text


def test_parse_line_custom_emoji_uses_shortcut():
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    off, text = parse_live_chat_line(lines[8])
    assert off == 150.0
    assert text == "mê quá trời :ao_dai:"
    assert "UCchannel" not in text  # custom emoji id is not leaked


def test_parse_line_skips_non_text_and_garbage():
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    assert parse_live_chat_line(lines[2]) is None  # membership item
    assert parse_live_chat_line(lines[4]) is None  # paid sticker
    assert parse_live_chat_line("") is None
    assert parse_live_chat_line("not json at all") is None
    assert parse_live_chat_line(json.dumps({"replayChatItemAction": {}})) is None
    # a text item without any offset is dropped
    no_offset = {
        "replayChatItemAction": {
            "actions": [
                {
                    "addChatItemAction": {
                        "item": {
                            "liveChatTextMessageRenderer": {"message": {"runs": [{"text": "x"}]}}
                        }
                    }
                }
            ]
        }
    }
    assert parse_live_chat_line(json.dumps(no_offset)) is None


# ---------------------------------------------------------------------------
# Tick synthesis
# ---------------------------------------------------------------------------


def test_synth_ticks_rates_per_minute():
    comments = [(0.0, "a"), (10.0, "b"), (35.0, "c"), (95.0, "d")]
    ticks = synth_ticks_from_comments(comments, duration_s=120.0, tick_s=30)
    assert ticks == [(0.0, 4.0), (30.0, 2.0), (60.0, 0.0), (90.0, 2.0)]


def test_synth_ticks_extends_past_duration_and_handles_empty():
    # a comment beyond the reported duration still lands in the last bucket
    ticks = synth_ticks_from_comments([(70.0, "late")], duration_s=60.0, tick_s=30)
    assert ticks[-1] == (60.0, 2.0)
    assert synth_ticks_from_comments([], duration_s=0.0, tick_s=30) == [(0.0, 0.0)]


# ---------------------------------------------------------------------------
# Routes end-to-end (download monkeypatched onto the fixture)
# ---------------------------------------------------------------------------


def _fake_download(title="Live bán áo dài", duration=600.0):
    """Return a download_chat_replay stand-in serving a COPY of the fixture
    (the pipeline deletes the file after parsing)."""

    def fake(url: str, out_dir, **kwargs) -> DownloadResult:
        copy = Path(out_dir) / "vid123.live_chat.json"
        shutil.copyfile(FIXTURE, copy)
        fake.chat_path = copy
        return DownloadResult(chat_path=copy, video_title=title, duration_s=duration, error=None)

    fake.chat_path = None
    return fake


def test_replay_route_end_to_end(client, monkeypatch):
    fake = _fake_download()
    monkeypatch.setattr(replays, "download_chat_replay", fake)

    r = client.post("/replays/youtube", json={"url": "https://www.youtube.com/watch?v=vid123"})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]

    job = client.get(f"/replays/jobs/{job_id}").json()
    assert job["status"] == "done", job
    assert job["n_comments"] == 7
    assert job["video_title"] == "Live bán áo dài"
    sid = job["session_id"]
    assert sid

    # data hygiene: the downloaded chat file (raw author names) is deleted
    assert fake.chat_path is not None
    assert not fake.chat_path.exists()

    # session created per the contract
    session = client.get(f"/sessions/{sid}").json()
    assert session["platform"] == "replay"
    assert session["status"] == "ended"
    assert session["title"] == "Phân tích: Live bán áo dài"
    assert session["planned_duration_min"] == 10
    assert session["design"]["analysis_only"] is True
    assert session["design"]["source_url"] == "https://www.youtube.com/watch?v=vid123"
    assert session["start_ts"] is not None  # backdated by video duration

    # no experiment blocks — intentional (observational session)
    assert client.get(f"/sessions/{sid}/schedule").json() == []

    # comments scrubbed BEFORE store (rule 1) and intent-classified
    comments = client.get(f"/sessions/{sid}/comments").json()
    assert len(comments) == 7
    joined = " ".join(c["text"] for c in comments)
    assert "[SĐT]" in joined
    assert "0901234567" not in joined
    for name in AUTHOR_NAMES:
        assert name not in joined
    phone_comment = next(c for c in comments if "[SĐT]" in c["text"])
    assert "phone" in phone_comment["pii_kinds"]
    assert any(c["intent"] == "chot_don" for c in comments)
    assert all(c["block_id"] is None for c in comments)

    # ticks: comment tempo only — viewers not retroactively available
    ticks = client.get(f"/sessions/{sid}/ticks").json()
    assert len(ticks) == 20  # 600 s / 30 s buckets
    assert all(t["viewers"] == 0.0 for t in ticks)
    assert sum(t["comment_rate"] for t in ticks) > 0

    # report: OBSERVATIONAL — no experiment language, no diff, no blocks
    report = client.get(f"/sessions/{sid}/report").json()
    assert report["label"] == "phân tích quan sát — không phải thí nghiệm"
    assert report["diff_in_means"] is None
    assert report["blocks"] == []
    assert report["n_blocks"] == 0

    # the pooled experiment summary must not count the analysis session
    summary = client.get("/experiment/summary").json()
    assert summary["n_sessions"] == 0


def test_replay_route_truncation_cap(client, monkeypatch):
    monkeypatch.setattr(replays, "download_chat_replay", _fake_download())
    monkeypatch.setattr(replays, "MAX_COMMENTS", 3)

    r = client.post("/replays/youtube", json={"url": "https://youtu.be/vid123"})
    job = client.get(f"/replays/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done"
    assert job["n_comments"] == 3
    assert "cắt bớt" in job["detail"].lower()


def test_replay_route_says_so_when_the_chat_replay_is_empty(client, monkeypatch):
    """Regression, live-fire 10/09/2026 (`docs/benchmarks/live-fire-da-nguon.md`).

    Video ``TdLWyV3hNao`` (715 min) advertised a ``live_chat`` track, the
    download succeeded, and the parsed chat held zero messages. The job
    reported ``status=done, n_comments=0, detail=null`` — a session that looked
    healthy and was empty, plus 1430 all-zero tick rows. An empty result is a
    legitimate outcome, but it has to be stated.
    """

    def empty(url: str, out_dir, **kwargs) -> DownloadResult:
        path = Path(out_dir) / "vid123.live_chat.json"
        path.write_text("", encoding="utf-8")
        return DownloadResult(
            chat_path=path, video_title="Live không ai nhắn", duration_s=600.0, error=None
        )

    monkeypatch.setattr(replays, "download_chat_replay", empty)
    r = client.post("/replays/youtube", json={"url": "https://youtu.be/vid123"})
    job = client.get(f"/replays/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done"
    assert job["n_comments"] == 0
    assert job["detail"], "một phiên rỗng phải được nói ra, không im lặng"
    assert "rỗng" in job["detail"]

    # ...and the coverage matrix must not dress the empty session up as usable.
    body = client.get(f"/sessions/{job['session_id']}/signals").json()
    assert next(s for s in body["signals"] if s["name"] == "comments")["status"] == "missing"
    assert next(s for s in body["signals"] if s["name"] == "ticks")["status"] == "missing"
    assert all(c["status"] == "missing" for c in body["capabilities"])


def test_replay_route_download_error(client, monkeypatch):
    def failing(url: str, out_dir, **kwargs) -> DownloadResult:
        return DownloadResult(
            chat_path=None, video_title="Video X", duration_s=0.0, error=ERR_NO_CHAT
        )

    monkeypatch.setattr(replays, "download_chat_replay", failing)
    r = client.post("/replays/youtube", json={"url": "https://youtu.be/gone"})
    assert r.status_code == 202
    job = client.get(f"/replays/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "error"
    assert "chat replay" in job["detail"]
    assert job["session_id"] is None


def test_replay_job_not_found_and_bad_url(client):
    assert client.get("/replays/jobs/khong-ton-tai").status_code == 404
    assert client.post("/replays/youtube", json={"url": "ftp://x"}).status_code == 422
