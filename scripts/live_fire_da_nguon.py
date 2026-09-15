#!/usr/bin/env python3
"""Sinh lại benchmark live-fire đa nguồn (`docs/benchmarks/live-fire-da-nguon.md`).

Mọi phép đo trong tài liệu đó đi qua **chính API công khai** của hệ thống —
`POST /replays/youtube`, `GET /sessions/...` — không có đường tắt vào store.
Script này chỉ là người lái; nó không tự phân tích gì cả.

Chạy (từ thư mục gốc repo, API đã bật):

    .venv/Scripts/python -m uvicorn livelift.api.main:app --port 8010

    .venv/Scripts/python scripts/live_fire_da_nguon.py nap ZU_0QJzsR6w gT0LDiBta2k
    .venv/Scripts/python scripts/live_fire_da_nguon.py bang
    .venv/Scripts/python scripts/live_fire_da_nguon.py colap ZU_0QJzsR6w gT0LDiBta2k
    .venv/Scripts/python scripts/live_fire_da_nguon.py song-song 1NMt8BChQrI fhv_rKUeEIc

Bốn lệnh:

``nap``        nạp từng video qua API, đo thời gian tải / thời gian nạp, in trạng
               thái job (kể cả các trạng thái hỏng: không có chat, chat rỗng).
``bang``       đọc lại MỌI phiên ``platform=replay`` trên API và in bảng benchmark
               (mật độ, phân bố ý định, độ tự tin, PII).
``colap``      phép kiểm chống rò rỉ giữa các phiên, **đối chiếu với sự thật gốc**:
               tải lại chat của đúng video đó, lọc PII bằng cùng hàm ``scrub``, so
               tập văn bản với thứ API trả về. Bằng nhau ⇒ không rò rỉ.
``song-song``  bắn hai job cùng lúc (chúng thật sự chồng nhau vì ``_run_job`` chạy
               trong thread pool của FastAPI) rồi chạy lại phép kiểm trên.

QUYỀN RIÊNG TƯ: ``colap`` tải file ``.live_chat.json`` thô — file này CHỨA TÊN
người bình luận. Nó nằm trong một thư mục tạm riêng và bị xoá ngay sau khi parse,
kể cả khi script lỗi. Không có gì thô được ghi vào ``data/``.

PHÁP LÝ: chỉ đọc nội dung CÔNG KHAI, không tải video, chỉ chat + metadata. Xem
phần ToS trong ``src/livelift/ingest/youtube_ytdlp.py`` trước khi mở rộng quy mô.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from livelift.ingest.pii import scrub  # noqa: E402
from livelift.ingest.youtube_replay import (  # noqa: E402
    download_chat_replay,
    parse_live_chat_file,
)

DEFAULT_API = "http://127.0.0.1:8010"
POLL_S = 0.4
JOB_TIMEOUT_S = 1800


def _url(video_id: str) -> str:
    if video_id.startswith(("http://", "https://")):
        return video_id
    return f"https://www.youtube.com/watch?v={video_id}"


def _require_http(api: str) -> str:
    """Reject anything but http(s) before it reaches ``urlopen``.

    ``urlopen`` also speaks ``file:``; this script takes its target from the
    command line, so the scheme is checked once, here, and the two call sites
    below can then silence S310 honestly.
    """
    if not api.startswith(("http://", "https://")):
        raise ValueError(f"--api phải bắt đầu bằng http:// hoặc https:// (nhận: {api!r})")
    return api.rstrip("/")


def _get(api: str, path: str):
    url = _require_http(api) + path
    with urllib.request.urlopen(url, timeout=300) as r:  # noqa: S310 — scheme checked above
        return json.loads(r.read().decode("utf-8"))


def _headers_ghi() -> dict[str, str]:
    """Header cho lời gọi GHI.

    ``POST /replays/youtube`` ở mức bảo vệ NGẶT NHẤT (nó bắt máy chủ tải nội
    dung bên ngoài — xem ``src/livelift/api/auth.py``), nên khi API đích có
    đặt ``INGEST_TOKEN`` thì script này phải đính token, đúng như bộ thu và
    ``spool_replay`` vẫn làm. API chạy cục bộ không đặt token ⇒ không có
    header nào, hành vi y như cũ.
    """
    from livelift.config import get_settings

    token = get_settings().ingest_token
    head = {"Content-Type": "application/json"}
    if token:
        head["Authorization"] = f"Bearer {token}"
    return head


def _post(api: str, path: str, payload: dict):
    req = urllib.request.Request(  # noqa: S310 — scheme checked in _require_http
        _require_http(api) + path,
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers_ghi(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:  # noqa: S310 — same
        return json.loads(r.read().decode("utf-8"))


def _quantile(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    i = q * (len(xs) - 1)
    lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


# ---------------------------------------------------------------------------
# nap
# ---------------------------------------------------------------------------


def submit(api: str, video_id: str) -> str:
    return _post(api, "/replays/youtube", {"url": _url(video_id)})["job_id"]


def wait(api: str, job_id: str, t0: float) -> tuple[dict, dict[str, float]]:
    """Poll a job to completion, recording when each phase was first seen."""
    phases: dict[str, float] = {}
    last = None
    job: dict = {}
    while True:
        job = _get(api, f"/replays/jobs/{job_id}")
        if job["status"] != last:
            phases[job["status"]] = time.monotonic() - t0
            last = job["status"]
        if job["status"] in ("done", "error"):
            return job, phases
        if time.monotonic() - t0 > JOB_TIMEOUT_S:
            return job, phases
        time.sleep(POLL_S)


def cmd_nap(api: str, video_ids: list[str]) -> int:
    rows = []
    for vid in video_ids:
        t0 = time.monotonic()
        job, phases = wait(api, submit(api, vid), t0)
        total = time.monotonic() - t0
        # "downloading" → "ingesting" is the yt-dlp download; the rest is
        # PII scrub + intent classification + store writes.
        tai = phases.get("ingesting", phases.get("done", phases.get("error", total))) - phases.get(
            "downloading", 0.0
        )
        nap = phases.get("done", total) - phases.get("ingesting", phases.get("done", total))
        rows.append((vid, job, total, tai, nap))
        print(
            f"{vid:14s} {job['status']:8s} n={str(job.get('n_comments')):>6s} "
            f"tổng={total:6.2f}s tải={tai:6.2f}s nạp={nap:5.2f}s"
            + (f"  ⚠ {job['detail']}" if job.get("detail") else "")
        )
        print(f"               {job.get('video_title') or ''}")
    ok = sum(1 for _v, j, *_ in rows if j["status"] == "done")
    total_n = sum(j.get("n_comments") or 0 for _v, j, *_ in rows)
    print(f"\n{ok}/{len(rows)} video vào được · {total_n} bình luận")
    return 0


# ---------------------------------------------------------------------------
# bang
# ---------------------------------------------------------------------------


def session_row(api: str, session: dict) -> dict:
    sid = session["session_id"]
    comments = _get(api, f"/sessions/{sid}/comments")
    ticks = _get(api, f"/sessions/{sid}/ticks")
    # A session that has not ended yet (the demo replay engine, or a live run)
    # has end_ts=None — fall back to the last tick so the row still prints.
    start_raw, end_raw = session.get("start_ts"), session.get("end_ts")
    if end_raw is None and ticks:
        end_raw = ticks[-1]["ts_bucket"]
    if start_raw is None or end_raw is None:
        minutes = 0.0
    else:
        start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
        minutes = max((end - start).total_seconds() / 60.0, 0.0)
    confs = [c["intent_confidence"] for c in comments if c.get("intent_confidence") is not None]
    kinds: Counter = Counter()
    with_pii = 0
    for c in comments:
        k = c.get("pii_kinds") or []
        if k:
            with_pii += 1
        kinds.update(k)
    return {
        "session_id": sid,
        "title": session["title"],
        "minutes": minutes,
        "n": len(comments),
        "density": len(comments) / minutes if minutes else 0.0,
        "peak": max((t["comment_rate"] for t in ticks), default=0.0),
        "n_ticks": len(ticks),
        "ticks_with_viewers": sum(1 for t in ticks if (t.get("viewers") or 0) > 0),
        "intent": dict(Counter(c.get("intent") for c in comments)),
        "conf": (
            {
                "median": statistics.median(confs),
                "p10": _quantile(confs, 0.10),
                "p90": _quantile(confs, 0.90),
                "below_045": sum(1 for c in confs if c < 0.45) / len(confs),
            }
            if confs
            else None
        ),
        "pii_comments": with_pii,
        "pii_kinds": dict(kinds),
    }


def cmd_bang(api: str) -> int:
    sessions = [s for s in _get(api, "/sessions") if s["platform"] == "replay"]
    rows = sorted((session_row(api, s) for s in sessions), key=lambda r: -r["n"])
    header = f"{'phút':>7} {'bình luận':>9} {'mật độ':>7} {'đỉnh':>6} {'PII':>6} {'hành động':>9}"
    print(header + "  buổi")
    for r in rows:
        act = sum(v for k, v in r["intent"].items() if k not in (None, "khac"))
        share = f"{act / r['n']:6.1%}" if r["n"] else "     —"
        pii = f"{r['pii_comments'] / r['n']:5.1%}" if r["n"] else "    —"
        print(
            f"{r['minutes']:7.1f} {r['n']:9d} {r['density']:7.2f} {r['peak']:6.0f} "
            f"{pii:>6} {share:>9}  {r['title'][:52]}"
        )
    print(f"\nTỔNG: {len(rows)} phiên · {sum(r['n'] for r in rows)} bình luận")
    print("\n-- độ tự tin (trung vị · p10 · p90 · tỷ lệ dưới ngưỡng abstain 0,45) --")
    for r in rows:
        if r["conf"]:
            c = r["conf"]
            print(
                f"  {c['median']:.3f} · {c['p10']:.3f} · {c['p90']:.3f} · "
                f"{c['below_045']:5.1%}   {r['title'][:48]}"
            )
    return 0


# ---------------------------------------------------------------------------
# colap / song-song
# ---------------------------------------------------------------------------


def ground_truth(video_id: str) -> list[str] | None:
    """Scrubbed texts of one video's chat, from a fresh download.

    The raw file carries author names, so it lives in a private temp directory
    that is removed in ``finally`` — the same hygiene rule the route follows.
    """
    tmp = Path(tempfile.mkdtemp(prefix="livelift-truth-"))
    try:
        result = download_chat_replay(_url(video_id), tmp)
        if result.error is not None or result.chat_path is None:
            print(f"  ! không tải được chat của {video_id}: {result.error}")
            return None
        return sorted(scrub(text).text for _offset, text in parse_live_chat_file(result.chat_path))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_isolation(api: str, pairs: dict[str, str]) -> bool:
    """True when every session holds EXACTLY its own video's comments."""
    ok = True
    seen_ids: Counter = Counter()
    for vid, sid in pairs.items():
        comments = _get(api, f"/sessions/{sid}/comments")
        seen_ids.update(c["comment_id"] for c in comments)
        truth = ground_truth(vid)
        if truth is None:
            ok = False
            continue
        api_texts = sorted(c["text"] for c in comments)
        one_session = {c["session_id"] for c in comments} <= {sid}
        same = api_texts == truth and one_session
        ok &= same
        print(
            f"  {'OK ' if same else 'FAIL'} {vid:14s} api={len(api_texts):5d} "
            f"gốc={len(truth):5d} một_session_id={one_session}"
        )
    dupes = sum(1 for n in seen_ids.values() if n > 1)
    print(f"  comment_id trùng giữa các phiên: {dupes}")
    return ok and dupes == 0


def cmd_colap(api: str, video_ids: list[str]) -> int:
    pairs: dict[str, str] = {}
    for vid in video_ids:
        t0 = time.monotonic()
        job, _ = wait(api, submit(api, vid), t0)
        if job.get("session_id"):
            pairs[vid] = job["session_id"]
        else:
            print(f"  bỏ qua {vid}: {job['status']} — {job.get('detail')}")
    ok = check_isolation(api, pairs)
    print("CÔ LẬP:", "ĐẠT" if ok else "KHÔNG ĐẠT")
    return 0 if ok else 1


def cmd_song_song(api: str, a: str, b: str) -> int:
    """Two analyses running at the same time must not contaminate each other."""
    jobs: dict[str, str] = {}
    barrier = threading.Barrier(2)

    def fire(vid: str) -> None:
        barrier.wait()
        jobs[vid] = submit(api, vid)

    threads = [threading.Thread(target=fire, args=(v,)) for v in (a, b)]
    t0 = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    pairs: dict[str, str] = {}
    for vid, jid in jobs.items():
        job, _ = wait(api, jid, t0)
        print(f"  {vid:14s} xong ở t+{time.monotonic() - t0:5.1f}s  n={job.get('n_comments')}")
        if job.get("session_id"):
            pairs[vid] = job["session_id"]
    ok = check_isolation(api, pairs) and len(set(pairs.values())) == len(pairs)
    print("CÔ LẬP KHI CHẠY SONG SONG:", "ĐẠT" if ok else "KHÔNG ĐẠT")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--api", default=DEFAULT_API, help=f"gốc API (mặc định {DEFAULT_API})")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_nap = sub.add_parser("nap", help="nạp video qua POST /replays/youtube")
    p_nap.add_argument("video_ids", nargs="+")
    sub.add_parser("bang", help="in bảng benchmark của mọi phiên replay")
    p_col = sub.add_parser("colap", help="kiểm rò rỉ, đối chiếu với sự thật gốc")
    p_col.add_argument("video_ids", nargs="+")
    p_ss = sub.add_parser("song-song", help="hai job chồng nhau rồi kiểm rò rỉ")
    p_ss.add_argument("a")
    p_ss.add_argument("b")
    args = parser.parse_args(argv)

    try:
        _get(args.api, "/health")
    except (urllib.error.URLError, OSError) as exc:
        print(f"Không gọi được API ở {args.api}: {exc}", file=sys.stderr)
        print(
            "Bật API trước: .venv/Scripts/python -m uvicorn livelift.api.main:app --port 8010",
            file=sys.stderr,
        )
        return 2

    if args.cmd == "nap":
        return cmd_nap(args.api, args.video_ids)
    if args.cmd == "bang":
        return cmd_bang(args.api)
    if args.cmd == "colap":
        return cmd_colap(args.api, args.video_ids)
    return cmd_song_song(args.api, args.a, args.b)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
