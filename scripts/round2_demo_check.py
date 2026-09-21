#!/usr/bin/env python3
"""Preflight cho demo AISC Round 2, mặc định hoàn toàn chỉ đọc.

Mặc định script chỉ đọc HTTP/API đang chạy. Tuỳ chọn chủ động
``--prepare-demo`` mới gieo dữ liệu MÔ PHỎNG qua hai endpoint chính thức; nó
không khởi động service, reset kho hay chạm vào phiên thật. HTTP 200 không phải
bằng chứng UI usable; UI correctness vẫn phải qua browser tests hiện có hoặc
diễn tập thủ công.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from livelift.console import configure

TIMEOUT_S = 8
GOLDEN_PREFIX = "Demo vàng · "
HOST_ALLOWED_KEYS = {"pinned_product", "price", "stock", "elapsed_s"}


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    evidence: str
    action: str = "—"


Getter = Callable[[str], HttpResult]
Poster = Callable[[str, dict[str, Any] | None], HttpResult]


def http_get(url: str) -> HttpResult:
    """GET một URL và giữ cả phản hồi 4xx/5xx làm evidence."""
    if urllib.parse.urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("preflight chỉ chấp nhận URL http:// hoặc https://")
    req = urllib.request.Request(  # noqa: S310 — scheme checked above
        url, headers={"User-Agent": "LiveLift-Round2-Preflight/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as response:  # noqa: S310 — checked
            return HttpResult(response.status, response.read())
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, exc.read())


def http_post(url: str, body: dict[str, Any] | None = None) -> HttpResult:
    """POST JSON tới một endpoint demo chính thức và giữ 4xx/5xx làm evidence."""
    if urllib.parse.urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("preflight chỉ chấp nhận URL http:// hoặc https://")
    data = json.dumps(body).encode("utf-8") if body is not None else b""
    req = urllib.request.Request(  # noqa: S310 — scheme checked above
        url,
        data=data,
        method="POST",
        headers={
            "User-Agent": "LiveLift-Round2-Preflight/1.0",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as response:  # noqa: S310 — checked
            return HttpResult(response.status, response.read())
    except urllib.error.HTTPError as exc:
        return HttpResult(exc.code, exc.read())


def _json(result: HttpResult) -> Any:
    try:
        return json.loads(result.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def select_fresh_demo_session(
    sessions: list[dict[str, Any]], now: datetime
) -> tuple[dict[str, Any] | None, int]:
    """Chọn phiên demo live mới nhất còn nằm trong planned duration.

    Trả thêm số phiên mang status=live nhưng đã quá giờ để bảng preflight nói
    rõ vì sao không chọn chúng. Không có UUID cố định hay title-specific hack.
    """
    fresh: list[tuple[datetime, dict[str, Any]]] = []
    stale = 0
    for session in sessions:
        if not session.get("is_demo") or session.get("status") != "live":
            continue
        start = _dt(session.get("start_ts"))
        duration = session.get("planned_duration_min")
        if start is None or not isinstance(duration, (int, float)) or duration <= 0:
            stale += 1
            continue
        if start <= now < start + timedelta(minutes=float(duration)):
            fresh.append((start, session))
        else:
            stale += 1
    fresh.sort(key=lambda item: item[0], reverse=True)
    return (fresh[0][1] if fresh else None), stale


def presenter_urls(web: str, live_id: str, golden: dict[str, str]) -> list[str]:
    quote = urllib.parse.quote
    return [
        f"{web}/",
        f"{web}/desk?session={quote(live_id, safe='')}",
        f"{web}/host?session={quote(live_id, safe='')}",
        f"{web}/ket-qua",
        *(
            f"{web}/ket-qua?phien={quote(golden[key], safe='')}"
            for key in ("duong", "null", "thieu")
        ),
    ]


def prepare_demo_data(api: str, *, post: Poster = http_post) -> list[Check]:
    """Chủ động gieo CHỈ dữ liệu demo qua các endpoint chính thức hiện có."""
    api = api.rstrip("/")
    checks: list[Check] = []

    try:
        golden_result = post(f"{api}/demo/seed-vang", None)
    except (OSError, ValueError) as exc:
        golden_result = HttpResult(0, b"")
        golden_error = type(exc).__name__
    else:
        golden_error = ""
    golden = _json(golden_result)
    golden_rows = golden.get("ket_qua") if isinstance(golden, dict) else None
    checks.append(
        Check(
            "Prepare Demo Vàng",
            golden_result.status == 200 and isinstance(golden_rows, dict) and len(golden_rows) >= 6,
            f"POST /demo/seed-vang => {golden_result.status or golden_error}; "
            f"rows={len(golden_rows) if isinstance(golden_rows, dict) else 0}",
            "Kiểm tra quyền ghi demo/API; không dùng ?gieo_lai=true và không reset kho.",
        )
    )

    try:
        live_result = post(f"{api}/demo/seed", {"n_sessions": 1, "duration_min": 60})
    except (OSError, ValueError) as exc:
        live_result = HttpResult(0, b"")
        live_error = type(exc).__name__
    else:
        live_error = ""
    live = _json(live_result)
    replay_id = live.get("replay_session_id") if isinstance(live, dict) else None
    checks.append(
        Check(
            "Prepare fresh demo session",
            live_result.status == 200 and isinstance(replay_id, str) and bool(replay_id),
            f"POST /demo/seed => {live_result.status or live_error}; "
            f"replay_session_id={'returned' if isinstance(replay_id, str) else 'missing'}",
            "Kiểm tra quyền ghi demo/API; checker không kết thúc hay xoá phiên cũ.",
        )
    )
    return checks


def run_checks(
    api: str,
    web: str,
    *,
    prepare: bool = False,
    get: Getter = http_get,
    post: Poster = http_post,
    now: datetime | None = None,
    require_durable: bool = True,
) -> tuple[list[Check], list[str]]:
    """Chuẩn bị khi được opt-in, rồi luôn chạy cùng một bộ preflight chỉ đọc."""
    preparation = prepare_demo_data(api, post=post) if prepare else []
    preflight, urls = run_preflight(
        api,
        web,
        get=get,
        now=now,
        require_durable=require_durable,
    )
    return preparation + preflight, urls


def run_preflight(
    api: str,
    web: str,
    *,
    get: Getter = http_get,
    now: datetime | None = None,
    require_durable: bool = True,
) -> tuple[list[Check], list[str]]:
    """Chạy các contract checks; không thực hiện request ghi."""
    api = api.rstrip("/")
    web = web.rstrip("/")
    now = (now or datetime.now(UTC)).astimezone(UTC)
    checks: list[Check] = []

    try:
        home = get(f"{web}/")
    except (OSError, ValueError) as exc:
        home = HttpResult(0, b"")
        home_error = type(exc).__name__
    else:
        home_error = ""
    checks.append(
        Check(
            "Web service reachable",
            home.status == 200,
            f"GET / => {home.status or home_error}",
            "Bật web service; HTTP 200 chỉ xác nhận route trả lời, không chứng minh UI usable.",
        )
    )

    try:
        health_result = get(f"{api}/health")
    except (OSError, ValueError) as exc:
        health_result = HttpResult(0, b"")
        health_error = type(exc).__name__
    else:
        health_error = ""
    health = _json(health_result)
    health_ok = health_result.status == 200 and isinstance(health, dict)
    checks.append(
        Check(
            "API service reachable",
            health_ok,
            f"GET /health => {health_result.status or health_error}",
            "Bật API và kiểm tra log; không tiếp tục coi các route phụ là PASS.",
        )
    )
    if not health_ok:
        return checks, []

    storage_mode = health.get("storage_mode")
    storage_ok = health.get("storage_ok") is True
    checks.append(
        Check(
            "Health/storage contract",
            health.get("status") == "ok" and storage_ok and isinstance(storage_mode, str),
            f"status={health.get('status')}, storage_mode={storage_mode}, "
            f"storage_ok={health.get('storage_ok')}",
            "Sửa storage cho tới khi /health tự khai status=ok và storage_ok=true.",
        )
    )
    durable = health.get("durable") is True
    checks.append(
        Check(
            "Durable database mode",
            durable or not require_durable,
            f"storage_mode={storage_mode}, durable={str(durable).lower()}",
            "Dùng Postgres cho lần kiểm chính thức; chỉ dùng --allow-memory khi diễn tập có chủ ý.",
        )
    )

    result_result = get(f"{api}/experiment/summary?env=real")
    result = _json(result_result)
    checks.append(
        Check(
            "Real result API contract",
            result_result.status == 200
            and isinstance(result, dict)
            and result.get("env") == "real",
            f"summary={result_result.status}, "
            f"env={result.get('env') if isinstance(result, dict) else None}, "
            f"n_sessions={result.get('n_sessions') if isinstance(result, dict) else None}",
            "Kết quả mặc định phải tiếp tục là env=real; không thay bằng demo.",
        )
    )

    try:
        sessions_result = get(f"{api}/sessions?env=demo")
    except (OSError, ValueError) as exc:
        sessions_result = HttpResult(0, b"")
        sessions_error = type(exc).__name__
    else:
        sessions_error = ""
    sessions_raw = _json(sessions_result)
    sessions = sessions_raw if isinstance(sessions_raw, list) else []
    sessions_contract = sessions_result.status == 200 and isinstance(sessions_raw, list)
    checks.append(
        Check(
            "Demo sessions API contract",
            sessions_contract
            and all(isinstance(s, dict) and s.get("is_demo") is True for s in sessions),
            f"GET /sessions?env=demo => {sessions_result.status or sessions_error}; "
            f"rows={len(sessions)}",
            "Kiểm tra session API và cờ is_demo; không dùng session không nhãn cho demo.",
        )
    )
    if not sessions_contract:
        return checks, []

    golden_rows = [
        s
        for s in sessions
        if isinstance(s.get("title"), str) and s["title"].startswith(GOLDEN_PREFIX)
    ]
    golden: dict[str, str] = {}
    for key, token in (("duong", "DƯƠNG rõ"), ("null", "NULL"), ("thieu", "CHƯA ĐỦ")):
        row = next((s for s in golden_rows if token in s.get("title", "")), None)
        if row and row.get("status") == "ended" and isinstance(row.get("session_id"), str):
            golden[key] = row["session_id"]
    checks.append(
        Check(
            "Demo Vàng present",
            set(golden) == {"duong", "null", "thieu"} and len(golden_rows) >= 6,
            f"golden_rows={len(golden_rows)}, states={','.join(sorted(golden)) or 'none'}",
            "Chạy chủ động: POST /demo/seed-vang; xác nhận mọi phiên mang is_demo=true.",
        )
    )

    selected, stale_count = select_fresh_demo_session(sessions, now)
    selected_id = selected.get("session_id") if selected else None
    checks.append(
        Check(
            "Fresh live demo session",
            isinstance(selected_id, str),
            f"selected={selected_id or 'none'}, stale_live={stale_count}",
            "Seed một phiên demo đang phát mới; không chọn phiên status=live đã quá duration.",
        )
    )
    if not isinstance(selected_id, str):
        checks.extend(
            [
                Check(
                    "Valid current block",
                    False,
                    "không có fresh live demo session để hỏi operator state",
                    "Seed phiên demo mới rồi chạy lại preflight.",
                ),
                Check(
                    "Blinded host API contract",
                    False,
                    "không có runtime session id để hỏi host state",
                    "Seed phiên demo mới; không dùng UUID lưu trong tài liệu.",
                ),
                Check(
                    "Presenter web routes reachable",
                    False,
                    "presenter URLs chưa resolve được",
                    "Chuẩn bị phiên demo mới rồi chạy lại; kiểm UI bằng browser/manual riêng.",
                ),
            ]
        )
        return checks, []

    operator_result = get(
        f"{api}/sessions/{urllib.parse.quote(selected_id, safe='')}/state?role=operator"
    )
    operator = _json(operator_result)
    block = operator.get("current_block") if isinstance(operator, dict) else None
    block_ok = (
        operator_result.status == 200
        and isinstance(operator, dict)
        and operator.get("session_id") == selected_id
        and operator.get("status") == "live"
        and operator.get("is_demo") is True
        and isinstance(block, dict)
        and isinstance(block.get("index"), int)
        and block.get("assignment") in {"ON", "OFF"}
        and block.get("seconds_remaining", 0) > 0
    )
    checks.append(
        Check(
            "Valid current block",
            block_ok,
            f"operator={operator_result.status}, "
            f"block={block if isinstance(block, dict) else None}",
            "Phiên đang NGOÀI KHỐI hoặc contract operator sai; seed mới và kiểm tra lại lịch.",
        )
    )

    host_result = get(f"{api}/sessions/{urllib.parse.quote(selected_id, safe='')}/state?role=host")
    host = _json(host_result)
    host_keys = set(host) if isinstance(host, dict) else set()
    checks.append(
        Check(
            "Blinded host API contract",
            host_result.status == 200
            and host_keys <= HOST_ALLOWED_KEYS
            and "elapsed_s" in host_keys,
            f"host={host_result.status}, keys={','.join(sorted(host_keys)) or 'none'}",
            "Host payload phải chỉ có pinned_product, price, stock, elapsed_s.",
        )
    )

    urls = (
        presenter_urls(web, selected_id, golden)
        if set(golden) == {"duong", "null", "thieu"}
        else []
    )
    route_statuses: list[str] = []
    routes_ok = bool(urls)
    for url in urls:
        route_result = get(url)
        route_statuses.append(f"{urllib.parse.urlsplit(url).path}:{route_result.status}")
        routes_ok = routes_ok and route_result.status == 200
    checks.append(
        Check(
            "Presenter web routes reachable",
            routes_ok,
            ", ".join(route_statuses) if route_statuses else "URLs chưa resolve được",
            "Sửa route/service hoặc chuẩn bị đủ session; sau đó chạy browser tests/"
            "manual rehearsal riêng.",
        )
    )
    return checks, urls


def _cell(text: str, limit: int = 72) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def print_report(checks: list[Check], urls: list[str], *, prepared: bool = False) -> None:
    mode = "PREPARE DEMO + PREFLIGHT" if prepared else "READ-ONLY PREFLIGHT"
    print(f"\nAISC ROUND 2 — {mode}")
    print(f"{'CHECK':31} | {'RESULT':6} | {'EVIDENCE':72} | PRESENTER ACTION")
    print("-" * 142)
    for check in checks:
        result = "PASS" if check.passed else "FAIL"
        evidence = _cell(check.evidence)
        action = _cell(check.action, 54)
        print(f"{_cell(check.name, 31):31} | {result:6} | {evidence:72} | {action}")
    print()
    print("Presenter URLs (runtime-resolved; HTTP reachability is not a UI usability claim):")
    if urls:
        for url in urls:
            print(f"  {url}")
    else:
        print("  Chưa resolve được vì thiếu preflight evidence.")
    failed = sum(not check.passed for check in checks)
    print(f"\nTOTAL: {len(checks) - failed} PASS · {failed} FAIL")


def main(argv: list[str] | None = None) -> int:
    configure()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        help="Gốc đi qua Caddy, ví dụ http://localhost (API tự dùng /api).",
    )
    parser.add_argument("--api", help="API riêng, ví dụ http://127.0.0.1:8000")
    parser.add_argument("--web", help="Web riêng, ví dụ http://127.0.0.1:3000")
    parser.add_argument(
        "--allow-memory",
        action="store_true",
        help="Cho phép kho không bền khi chỉ diễn tập; bảng vẫn in storage_mode/durable.",
    )
    parser.add_argument(
        "--prepare-demo",
        action="store_true",
        help=(
            "Opt-in ghi dữ liệu MÔ PHỎNG: POST /demo/seed-vang và /demo/seed, "
            "rồi chạy cùng preflight. Mặc định không POST."
        ),
    )
    args = parser.parse_args(argv)
    if args.base:
        base = args.base.rstrip("/")
        api = (args.api or f"{base}/api").rstrip("/")
        web = (args.web or base).rstrip("/")
    else:
        api = (args.api or "http://127.0.0.1:8000").rstrip("/")
        web = (args.web or "http://127.0.0.1:3000").rstrip("/")
    try:
        checks, urls = run_checks(
            api,
            web,
            prepare=args.prepare_demo,
            require_durable=not args.allow_memory,
        )
    except (OSError, ValueError) as exc:
        checks = [
            Check(
                "Preflight completed",
                False,
                f"{type(exc).__name__}: {exc}",
                "Kiểm tra service/URL rồi chạy lại; không coi lỗi checker là PASS.",
            )
        ]
        urls = []
    print_report(checks, urls, prepared=args.prepare_demo)
    return 0 if checks and all(check.passed for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
