"""The key-free YouTube live path (``livelift.ingest.youtube_ytdlp``).

Fixture provenance: ``tests/data/live_chat_live_fixture.jsonl`` holds REAL
lines captured on 2026-09-09 from a live broadcast (yt-dlp 2026.08.19,
``--sub-langs live_chat`` on a stream with ~860 concurrent viewers) plus one
line from a finished VOD's chat replay, so both on-disk shapes are covered.
Sanitized before landing in the repo: author names/channel ids replaced with
placeholders and every message text passed through ``livelift.ingest.pii.scrub``
— the repo must not carry a stranger's raw comment (hard rule 1).

Covered behaviors:
- parsing both shapes (live pseudo-action and replay action) off one parser;
- author identity never leaves the parser, and never reaches the sink payload;
- the tail loop: incremental reads, ``.part`` → final rename, end of stream;
- crash → relaunch → backlog de-duplication; fatal vs. retryable exits;
- viewers: a hidden count yields NO tick (never a fake 0) and is declared
  missing in the signal matrix;
- backend selection through INGEST_YOUTUBE_BACKEND.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from pathlib import Path

import httpx
import pytest

from livelift.core.signals import assess
from livelift.ingest.base import ApiSink
from livelift.ingest.youtube_ytdlp import (
    ERR_NO_CHAT,
    ERR_UNAVAILABLE,
    ERR_VIEWERS_HIDDEN,
    STALE_TEMP_AFTER_S,
    TEMP_PREFIX,
    YouTubeYtdlpClient,
    classify_exit,
    parse_live_chat_actions,
)

FIXTURE = Path(__file__).parent / "data" / "live_chat_live_fixture.jsonl"
FIXTURE_LINES = FIXTURE.read_text(encoding="utf-8").splitlines()
# Placeholders that replaced the real identities in the fixture; nothing that
# the parser emits may ever contain them.
AUTHOR_MARKERS = ("Người xem", "UCplaceholder")


def _all_comments(lines: list[str]) -> list:
    out = []
    for line in lines:
        out.extend(parse_live_chat_actions(line))
    return out


# --- parsing real captured lines -------------------------------------------


def test_parses_real_live_and_replay_lines():
    comments = _all_comments(FIXTURE_LINES)
    # 5 live text messages + 1 replay text message; placeholder and viewer
    # engagement renderers are not chat messages.
    assert len(comments) == 6
    assert {c.platform for c in comments} == {"youtube"}
    assert all(c.ts_utc.tzinfo is not None for c in comments)
    assert all(c.text.strip() for c in comments)
    assert len({c.ext_id for c in comments}) == 6


def test_timestamp_comes_from_timestamp_usec_not_offset():
    """``videoOffsetTimeMsec`` is relative to the DOWNLOADER's start on a live
    stream (negative for the connect backlog) — useless as a clock. The event
    time must be YouTube's absolute ``timestampUsec``."""
    line = next(
        line
        for line in FIXTURE_LINES
        if '"isLive": true' in line and "liveChatTextMessageRenderer" in line
    )
    obj = json.loads(line)
    renderer = obj["replayChatItemAction"]["actions"][0]["addChatItemAction"]["item"][
        "liveChatTextMessageRenderer"
    ]
    (comment,) = parse_live_chat_actions(line)
    assert comment.ts_utc.timestamp() == pytest.approx(int(renderer["timestampUsec"]) / 1e6)
    # the fixture's backlog line really does carry a negative offset
    assert float(obj["videoOffsetTimeMsec"]) < 0
    assert comment.ts_utc.year >= 2026


def test_replay_shape_without_islive_still_parses():
    line = next(line for line in FIXTURE_LINES if '"isLive"' not in line)
    (comment,) = parse_live_chat_actions(line)
    assert comment.ext_id
    assert comment.text.strip()


def test_vietnamese_diacritics_survive():
    texts = " ".join(c.text for c in _all_comments(FIXTURE_LINES))
    assert any(ch in texts for ch in "ạảãăâđêôơư")


def test_author_identity_never_leaves_the_parser():
    raw = FIXTURE.read_text(encoding="utf-8")
    assert any(m in raw for m in AUTHOR_MARKERS), "fixture must contain author fields to be a test"
    for comment in _all_comments(FIXTURE_LINES):
        assert comment.author_ext_id is None
        blob = f"{comment.ext_id} {comment.text}"
        for marker in AUTHOR_MARKERS:
            assert marker not in blob


def test_non_text_renderers_are_skipped():
    for line in FIXTURE_LINES:
        if "liveChatPlaceholderItemRenderer" in line or "ViewerEngagement" in line:
            assert parse_live_chat_actions(line) == []


def test_all_actions_in_one_line_are_returned():
    """A fragment line can carry several actions; the offset-only VOD parser
    reads the first, this one must not lose the rest."""
    template = json.loads(
        next(line for line in FIXTURE_LINES if "liveChatTextMessageRenderer" in line)
    )
    action = template["replayChatItemAction"]["actions"][0]
    second = json.loads(json.dumps(action))
    second["addChatItemAction"]["item"]["liveChatTextMessageRenderer"]["id"] = "second-id"
    template["replayChatItemAction"]["actions"] = [action, second]
    comments = parse_live_chat_actions(json.dumps(template))
    assert len(comments) == 2
    assert comments[1].ext_id == "second-id"


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "not json",
        "[1, 2, 3]",
        '"a string"',
        "{}",
        '{"replayChatItemAction": {"actions": "not-a-list"}}',
        '{"replayChatItemAction": {"actions": [{"addChatItemAction": {"item": {}}}]}}',
        # missing timestampUsec -> unusable as an event
        '{"replayChatItemAction": {"actions": [{"addChatItemAction": {"item":'
        ' {"liveChatTextMessageRenderer": {"id": "x", "message": {"runs":'
        ' [{"text": "hi"}]}}}}}]}}',
        # empty text after joining runs
        '{"replayChatItemAction": {"actions": [{"addChatItemAction": {"item":'
        ' {"liveChatTextMessageRenderer": {"id": "x", "timestampUsec": "1788970000000000",'
        ' "message": {"runs": [{"text": "   "}]}}}}}]}}',
    ],
)
def test_malformed_lines_yield_nothing(line):
    assert parse_live_chat_actions(line) == []


def test_scrubbed_payload_carries_no_author_field():
    """End of hard rule 1 for this path: what the sink actually transmits."""
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content.decode()))
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sink = ApiSink("http://api", "sess-1", client=client, spool_dir=None, token="")
    comment = _all_comments(FIXTURE_LINES)[0]
    assert asyncio.run(sink.post_comment(comment)) is True
    (payload,) = captured
    assert "author" not in json.dumps(payload)
    for marker in AUTHOR_MARKERS:
        assert marker not in json.dumps(payload, ensure_ascii=False)
    assert payload["platform"] == "youtube"


# --- fake yt-dlp process: drives the real tail loop -------------------------


class FakeProc:
    """Mimics the slice of asyncio.subprocess.Process the tailer uses, and
    writes chat lines the way yt-dlp does: append to ``<id>.live_chat.json.part``,
    flush, then rename to the final name when the stream ends."""

    def __init__(
        self,
        out_dir: Path,
        chunks: list[list[str]],
        returncode: int = 0,
        log: str = "",
        rename_at_end: bool = True,
        step_s: float = 0.02,
    ) -> None:
        self.returncode = None
        self._out_dir = out_dir
        self._chunks = chunks
        self._rc = returncode
        self._log = log
        self._rename = rename_at_end
        self._step_s = step_s
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def _run(self) -> None:
        part = self._out_dir / "vid.live_chat.json.part"
        for chunk in self._chunks:
            await asyncio.sleep(self._step_s)
            with part.open("ab") as fh:
                fh.write(("\n".join(chunk) + "\n").encode("utf-8"))
        await asyncio.sleep(self._step_s)
        (self._out_dir / "ytdlp.log").write_text(self._log, encoding="utf-8")
        if self._rename and part.exists():
            part.rename(self._out_dir / "vid.live_chat.json")
        self.returncode = self._rc

    async def wait(self) -> int:
        # A real process that was killed is reaped and reports its code; it
        # does not hand the caller a CancelledError.
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        return self.returncode

    def kill(self) -> None:
        self._task.cancel()
        self.returncode = -9


def _client(launcher, tmp_path, **kw) -> YouTubeYtdlpClient:
    return YouTubeYtdlpClient(chat_launcher=launcher, workdir=tmp_path, tail_poll_s=0.005, **kw)


def _drain(client: YouTubeYtdlpClient, video_id: str = "vid") -> list:
    async def go():
        return [c async for c in client.iter_comments(video_id)]

    return asyncio.run(asyncio.wait_for(go(), timeout=15))


def test_tail_loop_reads_incrementally_and_stops_at_end_of_stream(tmp_path):
    text_lines = [line for line in FIXTURE_LINES if "liveChatTextMessageRenderer" in line]
    chunks = [text_lines[:2], text_lines[2:4], text_lines[4:]]

    async def launcher(video_id, out_dir):
        return FakeProc(out_dir, chunks, returncode=0)

    client = _client(launcher, tmp_path)
    comments = _drain(client)
    assert len(comments) == 6
    assert client.last_error is None


def test_temp_files_with_raw_authors_are_deleted(tmp_path):
    """yt-dlp's file holds raw author names — it must not survive the run."""
    text_lines = [line for line in FIXTURE_LINES if "liveChatTextMessageRenderer" in line]

    async def launcher(video_id, out_dir):
        return FakeProc(out_dir, [text_lines], returncode=0)

    client = _client(launcher, tmp_path)
    assert _drain(client)
    assert list(tmp_path.rglob("*.live_chat.json*")) == []
    assert list(tmp_path.iterdir()) == []


def test_aclose_kills_an_abandoned_download_and_deletes_raw_chat(tmp_path):
    """Regression from a real live-fire run: the runner cancels the comment
    pump, which raises in the CONSUMER and leaves the async generator merely
    suspended — its finally never ran, so a yt-dlp process kept downloading and
    a temp dir with 182 KB of raw chat (author names) survived. aclose() must
    clean up on its own."""
    text_lines = [line for line in FIXTURE_LINES if "liveChatTextMessageRenderer" in line]
    procs: list[FakeProc] = []

    async def launcher(video_id, out_dir):
        proc = FakeProc(out_dir, [text_lines[:1], text_lines[1:]], returncode=0, step_s=5.0)
        procs.append(proc)
        return proc

    async def go():
        client = _client(launcher, tmp_path)
        agen = client.iter_comments("vid")
        await agen.asend(None)  # first comment, download still running
        # NO agen.aclose(): exactly what a cancelled pump task leaves behind.
        await client.aclose()
        return client

    client = asyncio.run(asyncio.wait_for(go(), timeout=15))
    assert procs
    assert procs[0].returncode is not None, "yt-dlp process must be killed"
    assert list(tmp_path.rglob("*.live_chat.json*")) == []
    assert client._temp_dirs == []


def test_startup_sweeps_raw_chat_left_by_a_hard_killed_run(tmp_path):
    """A `kill -9` / killed container / `timeout` gives Python no chance to
    clean up — measured in a real runner run: 121 KB of raw chat with author
    names stayed on disk. The next client startup must sweep it, without ever
    deleting a directory another session is still writing to."""
    stale = tmp_path / f"{TEMP_PREFIX}dead"
    stale.mkdir()
    (stale / "vid.live_chat.json.part").write_text('{"authorName": "x"}', encoding="utf-8")
    old = time.time() - STALE_TEMP_AFTER_S - 60
    os.utime(stale / "vid.live_chat.json.part", (old, old))
    os.utime(stale, (old, old))

    active = tmp_path / f"{TEMP_PREFIX}running"
    active.mkdir()
    (active / "vid.live_chat.json.part").write_text('{"authorName": "y"}', encoding="utf-8")

    unrelated = tmp_path / "some-other-tempdir"
    unrelated.mkdir()

    YouTubeYtdlpClient(metadata_fetch=None, workdir=tmp_path)

    assert not stale.exists()
    assert active.exists(), "a session still writing must never be swept"
    assert unrelated.exists(), "only our own prefix may be touched"


def test_relaunch_after_crash_dedupes_the_replayed_backlog(tmp_path, monkeypatch):
    monkeypatch.setattr("livelift.ingest.youtube_ytdlp.RELAUNCH_BASE_S", 0.01)
    text_lines = [line for line in FIXTURE_LINES if "liveChatTextMessageRenderer" in line]
    extra = json.loads(text_lines[0])
    extra["replayChatItemAction"]["actions"][0]["addChatItemAction"]["item"][
        "liveChatTextMessageRenderer"
    ]["id"] = "after-restart"
    calls: list[int] = []

    async def launcher(video_id, out_dir):
        calls.append(1)
        if len(calls) == 1:
            # died mid-stream: network blip, no rename, non-zero exit
            return FakeProc(
                out_dir,
                [text_lines[:3]],
                returncode=1,
                log="ERROR: unable to download video data: <urlopen error timed out>",
                rename_at_end=False,
            )
        # YouTube replays the recent backlog on reconnect + one new message
        return FakeProc(out_dir, [text_lines + [json.dumps(extra)]], returncode=0)

    client = _client(launcher, tmp_path)
    comments = _drain(client)
    assert len(calls) == 2
    ids = [c.ext_id for c in comments]
    assert len(ids) == len(set(ids)), "backlog after reconnect must not be re-emitted"
    assert "after-restart" in ids
    assert len(ids) == 7


def test_windows_rename_race_is_treated_as_clean_end(tmp_path):
    """Verified against the real tool: a reader holding the .part makes
    yt-dlp's rename fail (WinError 32) and exit 1 with all data already
    written. That must end the run, not trigger an endless relaunch."""
    text_lines = [line for line in FIXTURE_LINES if "liveChatTextMessageRenderer" in line]
    calls: list[int] = []

    async def launcher(video_id, out_dir):
        calls.append(1)
        return FakeProc(
            out_dir,
            [text_lines],
            returncode=1,
            log="ERROR: Unable to rename file: [WinError 32] ... Giving up after 3 retries",
            rename_at_end=False,
        )

    client = _client(launcher, tmp_path)
    comments = _drain(client)
    assert len(calls) == 1
    assert len(comments) == 6


def test_a_failed_spawn_is_retried_not_fatal(tmp_path, monkeypatch):
    """Failing to start the process (no fd / no memory / no temp space) must
    not end a 90-minute session — that is what the relaunch loop is for."""
    monkeypatch.setattr("livelift.ingest.youtube_ytdlp.RELAUNCH_BASE_S", 0.01)
    text_lines = [line for line in FIXTURE_LINES if "liveChatTextMessageRenderer" in line]
    calls: list[int] = []

    async def launcher(video_id, out_dir):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("cannot spawn")
        return FakeProc(out_dir, [text_lines], returncode=0)

    client = _client(launcher, tmp_path)
    assert len(_drain(client)) == 6
    assert len(calls) == 2


def test_missing_ytdlp_module_fails_loudly_instead_of_looping(tmp_path):
    """The child exits 1 with an ImportError — a config error that a retry
    loop would bury under a 60-second heartbeat message."""

    async def launcher(video_id, out_dir):
        return FakeProc(
            out_dir, [[]], returncode=1, log="No module named yt_dlp", rename_at_end=False
        )

    client = _client(launcher, tmp_path)
    with pytest.raises(RuntimeError, match="yt-dlp"):
        _drain(client)


def test_fatal_exit_raises_instead_of_spinning(tmp_path):
    async def launcher(video_id, out_dir):
        return FakeProc(out_dir, [[]], returncode=1, log="ERROR: [youtube] vid: Video unavailable")

    client = _client(launcher, tmp_path)
    with pytest.raises(RuntimeError) as err:
        _drain(client)
    assert ERR_UNAVAILABLE in str(err.value)


def test_bot_check_keeps_the_loop_alive_with_a_loud_error(tmp_path, monkeypatch):
    """A fast retry cannot fix the anti-bot check and dying loses the session:
    pause long, keep the last_error visible in every heartbeat."""
    monkeypatch.setattr("livelift.ingest.youtube_ytdlp.BLOCKED_BACKOFF_S", 0.01)
    text_lines = [line for line in FIXTURE_LINES if "liveChatTextMessageRenderer" in line]
    calls: list[int] = []
    seen_error: list[str] = []

    async def launcher(video_id, out_dir):
        calls.append(1)
        if len(calls) == 1:
            return FakeProc(
                out_dir,
                [[]],
                returncode=1,
                log="ERROR: [youtube] vid: Sign in to confirm you’re not a bot.",
            )
        seen_error.append(client.last_error or "")
        return FakeProc(out_dir, [text_lines], returncode=0)

    client = _client(launcher, tmp_path)
    comments = _drain(client)
    assert len(comments) == 6
    assert "YTDLP_COOKIES_FROM_BROWSER" in seen_error[0]


@pytest.mark.parametrize(
    ("rc", "log", "kind"),
    [
        (0, "", "ended"),
        (1, "ERROR: Unable to rename file: [WinError 32]", "ended"),
        (1, "ERROR: Sign in to confirm you’re not a bot.", "blocked"),
        (1, "ERROR: [youtube] x: Private video. Sign in if you've been granted access", "fatal"),
        (1, "ERROR: [youtube] x: Video unavailable", "fatal"),
        (1, "ERROR: [youtube] x: This live event will begin in 3 hours", "wait"),
        (1, "ERROR: unable to download: HTTP Error 503: Service Unavailable", "retry"),
    ],
)
def test_classify_exit(rc, log, kind):
    assert classify_exit(rc, log)[0] == kind


# --- viewers ----------------------------------------------------------------


def _collect_ticks(client: YouTubeYtdlpClient, n: int, every_s: float = 0.0) -> list:
    async def go():
        out = []
        async for tick in client.iter_viewers("vid", every_s=every_s):
            out.append(tick)
            if len(out) >= n:
                break
        return out

    return asyncio.run(asyncio.wait_for(go(), timeout=10))


def test_viewer_ticks_carry_the_real_concurrent_count(tmp_path):
    counts = iter([863, 892, 908])

    async def meta(video_id):
        return {"live_status": "is_live", "concurrent_view_count": next(counts)}

    client = YouTubeYtdlpClient(metadata_fetch=meta, workdir=tmp_path)
    ticks = _collect_ticks(client, 3)
    assert [t.viewers for t in ticks] == [863.0, 892.0, 908.0]
    assert all(t.platform == "youtube" and t.ts_utc.tzinfo is not None for t in ticks)


def test_hidden_viewer_count_yields_no_tick_and_declares_the_signal_missing(tmp_path):
    """HONESTY: a channel that hides its viewer count must NOT become a stream
    of zeros. No tick is emitted, the operator sees why in the heartbeat, and
    the signal matrix reports 'ticks' missing so no capability silently
    degrades into a fabricated curve."""
    polls: list[int] = []

    async def meta(video_id):
        polls.append(1)
        if len(polls) >= 3:
            return {"live_status": "was_live"}  # ends the loop
        return {"live_status": "is_live", "concurrent_view_count": None}

    client = YouTubeYtdlpClient(metadata_fetch=meta, workdir=tmp_path)

    async def go():
        return [t async for t in client.iter_viewers("vid", every_s=0.0)]

    ticks = asyncio.run(asyncio.wait_for(go(), timeout=10))
    assert ticks == []
    assert client.viewers_hidden is True
    assert client.last_error == ERR_VIEWERS_HIDDEN
    assert polls  # the loop really ran; it just refused to invent a number

    coverage = assess(
        has_schedule=True,
        n_ticks=len(ticks),
        n_ticks_with_viewers=len(ticks),
        tick_coverage_share=0.0,
        n_comments=42,
        n_clicks_valid=0,
        n_clicks_raw=0,
        n_orders=0,
        # the live ytdlp path does not pump reactions yet — declared, not faked
        n_reactions=0,
        platform="youtube",
    )
    ticks_signal = next(s for s in coverage.signals if s.name == "ticks")
    assert ticks_signal.status == "missing"
    rhythm = next(c for c in coverage.capabilities if c.name.startswith("nhịp phiên"))
    assert rhythm.status == "missing"
    experiment = next(c for c in coverage.capabilities if c.name.startswith("thí nghiệm"))
    assert experiment.status == "missing"


def test_viewer_loop_stops_when_the_broadcast_ends(tmp_path):
    async def meta(video_id):
        return {"live_status": "was_live", "concurrent_view_count": None}

    client = YouTubeYtdlpClient(metadata_fetch=meta, workdir=tmp_path)

    async def go():
        return [t async for t in client.iter_viewers("vid", every_s=0.0)]

    assert asyncio.run(asyncio.wait_for(go(), timeout=10)) == []


def test_viewer_poll_error_does_not_kill_the_loop(tmp_path, monkeypatch):
    calls: list[int] = []

    async def meta(video_id):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("network down")
        return {"live_status": "is_live", "concurrent_view_count": 12}

    client = YouTubeYtdlpClient(metadata_fetch=meta, workdir=tmp_path)
    ticks = _collect_ticks(client, 1, every_s=0.0)
    assert [t.viewers for t in ticks] == [12.0]


# --- preflight and backend selection ---------------------------------------


def test_preflight_rejects_a_video_that_is_not_live(tmp_path):
    async def meta(video_id):
        return {"live_status": "was_live", "subtitles": {"live_chat": [{}]}}

    client = YouTubeYtdlpClient(metadata_fetch=meta, workdir=tmp_path)
    with pytest.raises(RuntimeError, match="phát trực tiếp"):
        asyncio.run(client.get_active_live_chat_id("vid"))


def test_preflight_rejects_a_live_stream_without_chat(tmp_path):
    async def meta(video_id):
        return {"live_status": "is_live", "subtitles": {}}

    client = YouTubeYtdlpClient(metadata_fetch=meta, workdir=tmp_path)
    with pytest.raises(RuntimeError) as err:
        asyncio.run(client.get_active_live_chat_id("vid"))
    assert ERR_NO_CHAT in str(err.value)


def test_preflight_accepts_a_live_stream_with_chat(tmp_path):
    async def meta(video_id):
        return {"live_status": "is_live", "subtitles": {"live_chat": [{"ext": "json"}]}}

    client = YouTubeYtdlpClient(metadata_fetch=meta, workdir=tmp_path)
    assert asyncio.run(client.get_active_live_chat_id("vid")) == "vid"


def _build(monkeypatch, value: str | None):
    from livelift.config import get_settings
    from livelift.ingest import runner

    if value is None:
        monkeypatch.delenv("INGEST_YOUTUBE_BACKEND", raising=False)
    else:
        monkeypatch.setenv("INGEST_YOUTUBE_BACKEND", value)
    get_settings.cache_clear()
    try:
        return runner._build_client("youtube")
    finally:
        get_settings.cache_clear()


def test_default_backend_is_unchanged_api(monkeypatch):
    from livelift.ingest.youtube import YouTubeLiveChatClient

    assert isinstance(_build(monkeypatch, None), YouTubeLiveChatClient)


@pytest.mark.parametrize("value", ["ytdlp", "YTDLP", " ytdlp "])
def test_env_selects_the_keyless_backend(monkeypatch, value):
    assert isinstance(_build(monkeypatch, value), YouTubeYtdlpClient)


def test_unknown_backend_fails_loudly(monkeypatch):
    with pytest.raises(ValueError, match="INGEST_YOUTUBE_BACKEND"):
        _build(monkeypatch, "scrape")
