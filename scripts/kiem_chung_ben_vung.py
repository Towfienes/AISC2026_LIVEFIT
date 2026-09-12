#!/usr/bin/env python3
"""Chứng minh dữ liệu SỐNG SÓT qua một lần tiến trình API chết.

Vì sao có tệp này (sự cố 11/09/2026): lúc 13:05:53 tiến trình API khởi động
lại và 13 phiên live thật + 17.535 bình luận biến mất vĩnh viễn, vì kho chỉ
nằm trong RAM. Không ai phát hiện cho tới khi ngồi đếm tay. Lời hứa "đã bền
vững rồi" mà không có phép thử thì chính là thứ đã hỏng — nên phép thử ở đây
làm đúng cái đã xảy ra: nạp dữ liệu thật qua API, **giết cứng** tiến trình
(TerminateProcess/SIGKILL, không chạy hàm tắt máy nào), bật lại, rồi đếm.

Cách chạy (API thật ở cổng 8000 KHÔNG bị đụng tới — script tự mở cổng riêng):

    # đường chính: PostgreSQL (cần: docker compose up -d db && livelift-migrate up)
    .venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend postgres

    # đường dự phòng: kho memory + ảnh chụp định kỳ
    .venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend memory --interval 3

    # đối chứng ÂM: memory, tắt ảnh chụp — PHẢI mất dữ liệu (và script báo ĐẠT
    # khi nó mất đúng như dự đoán; một cơ chế an toàn chỉ đáng tin khi ta cũng
    # đo được thế giới không có nó)
    .venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend memory --no-snapshot

Mã thoát 0 = kết quả ĐÚNG như dự đoán của chế độ đang đo; 1 = sai.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.console import configure  # noqa: E402

N_COMMENTS = 25
N_TICKS = 5
STARTUP_TIMEOUT_S = 60.0


# ---------------------------------------------------------------------------
# HTTP nhỏ gọn (chỉ dùng thư viện chuẩn — script kiểm chứng không được kéo thêm
# phụ thuộc, nếu không chính nó lại là thứ hỏng trước)
# ---------------------------------------------------------------------------


def _call(method: str, url: str, body: dict | None = None, timeout: float = 20.0) -> dict | list:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)  # noqa: S310 - luôn là http://127.0.0.1
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _wait_healthy(base: str, deadline_s: float) -> dict:
    end = time.monotonic() + deadline_s
    last: Exception | None = None
    while time.monotonic() < end:
        try:
            return _call("GET", f"{base}/health", timeout=5.0)  # type: ignore[return-value]
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last = exc
            time.sleep(0.4)
    raise RuntimeError(f"API không lên trong {deadline_s:.0f} giây: {last}")


# ---------------------------------------------------------------------------
# Tiến trình API
# ---------------------------------------------------------------------------


def _spawn(env: dict[str, str], port: int, log_path: Path) -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "livelift.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "info",
    ]
    handle = log_path.open("a", encoding="utf-8")
    return subprocess.Popen(  # noqa: S603 - lệnh cố định, không có đầu vào người dùng
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )


def _hard_kill(proc: subprocess.Popen) -> None:
    """Giết CỨNG: không SIGTERM, không chạy hàm tắt máy, không chụp ảnh lần cuối.

    Đây là điểm mấu chốt của phép thử. Nếu tắt lịch sự thì lifespan sẽ chụp ảnh
    lần cuối và kho memory *luôn* sống sót — ta sẽ tự lừa mình. Sự cố thật là
    một tiến trình biến mất giữa chừng.
    """
    proc.kill()
    proc.wait(timeout=30)


# ---------------------------------------------------------------------------
# Nạp và đếm
# ---------------------------------------------------------------------------


def _load_session(base: str, tag: str) -> dict:
    product_id = f"KCBV-{tag}"
    _call(
        "POST",
        f"{base}/products",
        {
            "product_id": product_id,
            "name": "Bình giữ nhiệt kiểm chứng bền vững",
            "category": "kiem-chung",
            "cost": 42000,
            "price": 95000,
            "stock": 50,
        },
    )
    session = _call(
        "POST",
        f"{base}/sessions",
        {
            "platform": "youtube",
            "title": f"Phiên kiểm chứng bền vững {tag}",
            "mode": "suggest",
            "planned_duration_min": 30,
        },
    )
    assert isinstance(session, dict)
    sid = session["session_id"]
    for i in range(N_COMMENTS):
        _call(
            "POST",
            f"{base}/sessions/{sid}/comments",
            {
                "text": f"chốt đơn cho em cái số {i} ạ, ship về Hải Phòng nhé",
                "platform": "youtube",
                "ext_id": f"{tag}-cmt-{i}",
            },
        )
    for i in range(N_TICKS):
        _call("POST", f"{base}/sessions/{sid}/ticks", {"viewers": 300 + i * 7})
    return {"session_id": sid, "product_id": product_id, "title": session["title"]}


def _count(base: str, sid: str) -> dict:
    try:
        session = _call("GET", f"{base}/sessions/{sid}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"con_phien": False, "n_comments": 0, "n_ticks": 0, "title": None}
        raise
    assert isinstance(session, dict)
    comments = _call("GET", f"{base}/sessions/{sid}/comments")
    ticks = _call("GET", f"{base}/sessions/{sid}/ticks")
    return {
        "con_phien": True,
        "n_comments": len(comments),  # type: ignore[arg-type]
        "n_ticks": len(ticks),  # type: ignore[arg-type]
        "title": session.get("title"),
    }


# ---------------------------------------------------------------------------
# Chạy phép thử
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    base = f"http://127.0.0.1:{args.port}"
    tag = datetime.now(UTC).strftime("%H%M%S")
    workdir = Path(tempfile.mkdtemp(prefix="livelift-benvung-"))
    log_path = workdir / "uvicorn.log"
    snapshot_path = workdir / "snapshot" / "store.json"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["STORE_BACKEND"] = args.backend
    env["STORE_SNAPSHOT_ENABLED"] = "false" if args.no_snapshot else "true"
    env["STORE_SNAPSHOT_PATH"] = str(snapshot_path)
    env["STORE_SNAPSHOT_INTERVAL_S"] = str(args.interval)
    if args.database_url:
        env["DATABASE_URL"] = args.database_url

    expect_survives = args.backend == "postgres" or not args.no_snapshot
    che_do = {
        ("postgres", False): "postgres",
        ("postgres", True): "postgres",
        ("memory", False): "memory + ảnh chụp",
        ("memory", True): "memory KHÔNG ảnh chụp (đối chứng âm)",
    }[(args.backend, args.no_snapshot)]

    print(f"== Kiểm chứng bền vững — chế độ: {che_do} ==")
    print(f"   cổng {args.port} (API thật ở 8000 không bị đụng tới) · nhật ký: {log_path}")

    proc = _spawn(env, args.port, log_path)
    try:
        health = _wait_healthy(base, STARTUP_TIMEOUT_S)
        print(
            f"   /health: store_backend={health.get('store_backend')} "
            f"storage_mode={health.get('storage_mode')} durable={health.get('durable')}"
        )
        if health.get("storage_warning"):
            print(f"   cảnh báo: {health['storage_warning']}")

        loaded = _load_session(base, tag)
        before = _count(base, loaded["session_id"])
        print(
            f"   đã nạp: phiên {loaded['session_id']} · "
            f"{before['n_comments']} bình luận · {before['n_ticks']} tick"
        )
        if before["n_comments"] != N_COMMENTS:
            print(f"   ✗ nạp không đủ ({before['n_comments']}/{N_COMMENTS}) — dừng")
            return 1

        if args.backend == "memory" and not args.no_snapshot:
            wait = args.interval + 2.0
            print(f"   chờ {wait:.0f} giây cho một chu kỳ chụp ảnh đi qua…")
            time.sleep(wait)

        print("   GIẾT CỨNG tiến trình (không chạy hàm tắt máy — đúng như sự cố thật)")
        _hard_kill(proc)
    finally:
        if proc.poll() is None:
            proc.kill()

    proc2 = _spawn(env, args.port, log_path)
    try:
        _wait_healthy(base, STARTUP_TIMEOUT_S)
        after = _count(base, loaded["session_id"])
        print(
            f"   sau khi bật lại: phiên {'CÒN' if after['con_phien'] else 'MẤT'} · "
            f"{after['n_comments']} bình luận · {after['n_ticks']} tick"
        )
    finally:
        proc2.terminate()
        try:
            proc2.wait(timeout=20)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc2.kill()

    survived = (
        after["con_phien"]
        and after["n_comments"] == before["n_comments"]
        and after["n_ticks"] == before["n_ticks"]
        and after["title"] == before["title"]
    )
    ok = survived == expect_survives
    print()
    if expect_survives:
        print("   DỰ ĐOÁN: dữ liệu phải còn nguyên sau khi tiến trình chết.")
    else:
        print("   DỰ ĐOÁN: dữ liệu phải MẤT (đối chứng âm — chứng minh phép thử có răng).")
    print(f"   THỰC TẾ : dữ liệu {'còn nguyên' if survived else 'đã mất'}.")
    print(f"   KẾT LUẬN: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    if ok and not args.keep:
        shutil.rmtree(workdir, ignore_errors=True)
    else:
        print(f"   giữ lại thư mục làm việc để soi: {workdir}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    configure()
    p = argparse.ArgumentParser(description="Chứng minh dữ liệu sống sót qua restart tiến trình")
    p.add_argument("--backend", choices=("memory", "postgres"), default="memory")
    p.add_argument("--port", type=int, default=8099, help="cổng riêng, mặc định 8099")
    p.add_argument("--interval", type=float, default=3.0, help="chu kỳ chụp ảnh (giây)")
    p.add_argument("--no-snapshot", action="store_true", help="tắt ảnh chụp (đối chứng âm)")
    p.add_argument("--database-url", default="", help="ghi đè DATABASE_URL cho chế độ postgres")
    p.add_argument("--keep", action="store_true", help="giữ thư mục làm việc kể cả khi đạt")
    args = p.parse_args(argv)
    if args.port == 8000:
        p.error("cổng 8000 đang chạy API thật với dữ liệu phiên live — chọn cổng khác")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
