from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from scripts.round2_demo_check import (
    HttpResult,
    prepare_demo_data,
    presenter_urls,
    run_checks,
    run_preflight,
    select_fresh_demo_session,
)

NOW = datetime(2026, 9, 21, 8, 0, tzinfo=UTC)


def _session(sid: str, title: str, *, status: str = "ended", minutes_ago: int = 100):
    return {
        "session_id": sid,
        "platform": "sim",
        "title": title,
        "mode": "auto",
        "status": status,
        "planned_duration_min": 60,
        "start_ts": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
        "end_ts": NOW.isoformat() if status == "ended" else None,
        "is_demo": True,
    }


def _payloads():
    sessions = [
        *[_session(f"d{i}", f"Demo vàng · DƯƠNG rõ #{i}") for i in range(1, 4)],
        *[_session(f"n{i}", f"Demo vàng · NULL (KTC chứa 0) #{i}") for i in range(1, 3)],
        _session("t1", "Demo vàng · CHƯA ĐỦ ĐIỀU KIỆN"),
        _session("stale", "Phiên demo cũ", status="live", minutes_ago=70),
        _session("fresh", "Phiên demo mới", status="live", minutes_ago=5),
    ]
    return sessions, {
        "/api/health": {
            "status": "ok",
            "storage_mode": "postgres",
            "storage_ok": True,
            "durable": True,
        },
        "/api/sessions?env=demo": sessions,
        "/api/sessions/fresh/state?role=operator": {
            "role": "operator",
            "session_id": "fresh",
            "status": "live",
            "is_demo": True,
            "current_block": {
                "index": 1,
                "phase": "early",
                "assignment": "OFF",
                "is_washout": False,
                "seconds_remaining": 120,
            },
        },
        "/api/sessions/fresh/state?role=host": {
            "pinned_product": None,
            "price": None,
            "stock": None,
            "elapsed_s": 300,
        },
        "/api/experiment/summary?env=real": {"env": "real", "n_sessions": 0},
    }


def _getter(payloads):
    def get(url: str) -> HttpResult:
        parsed = urlsplit(url)
        key = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        if parsed.netloc == "web.test":
            return HttpResult(200, b"<html></html>")
        if key not in payloads:
            return HttpResult(404, b"{}")
        return HttpResult(200, json.dumps(payloads[key]).encode())

    return get


def _poster(payloads, calls):
    def post(url: str, body: dict | None) -> HttpResult:
        parsed = urlsplit(url)
        calls.append((parsed.path, body))
        if parsed.path == "/api/demo/seed-vang":
            return HttpResult(
                200,
                json.dumps({"ket_qua": {f"golden-{i}": {} for i in range(6)}}).encode(),
            )
        if parsed.path == "/api/demo/seed":
            return HttpResult(200, json.dumps({"replay_session_id": "fresh"}).encode())
        return HttpResult(404, b"{}")

    return post


def test_preflight_pass_resolve_runtime_and_never_select_stale():
    _sessions, payloads = _payloads()
    checks, urls = run_preflight(
        "http://api.test/api", "http://web.test", get=_getter(payloads), now=NOW
    )
    assert checks
    assert all(check.passed for check in checks)
    assert any("/desk?session=fresh" in url for url in urls)
    assert all("stale" not in url for url in urls)
    assert any("phien=d1" in url for url in urls)
    assert any("phien=n1" in url for url in urls)
    assert any("phien=t1" in url for url in urls)


def test_stale_live_session_is_not_fresh():
    stale = _session("stale", "cũ", status="live", minutes_ago=61)
    selected, count = select_fresh_demo_session([stale], NOW)
    assert selected is None
    assert count == 1


def test_missing_golden_and_current_block_fail_closed():
    sessions, payloads = _payloads()
    payloads["/api/sessions?env=demo"] = [s for s in sessions if "NULL" not in s["title"]]
    payloads["/api/sessions/fresh/state?role=operator"]["current_block"] = None
    checks, urls = run_preflight(
        "http://api.test/api", "http://web.test", get=_getter(payloads), now=NOW
    )
    by_name = {check.name: check for check in checks}
    assert not by_name["Demo Vàng present"].passed
    assert not by_name["Valid current block"].passed
    assert not by_name["Presenter web routes reachable"].passed
    assert urls == []


def test_host_contract_rejects_assignment_leak():
    _sessions, payloads = _payloads()
    payloads["/api/sessions/fresh/state?role=host"]["assignment"] = "OFF"
    checks, _ = run_preflight(
        "http://api.test/api", "http://web.test", get=_getter(payloads), now=NOW
    )
    host = next(check for check in checks if check.name == "Blinded host API contract")
    assert not host.passed


def test_memory_requires_explicit_rehearsal_override():
    _sessions, payloads = _payloads()
    payloads["/api/health"].update(storage_mode="memory+snapshot", durable=False)
    strict, _ = run_preflight(
        "http://api.test/api", "http://web.test", get=_getter(payloads), now=NOW
    )
    relaxed, _ = run_preflight(
        "http://api.test/api",
        "http://web.test",
        get=_getter(payloads),
        now=NOW,
        require_durable=False,
    )
    assert not next(c for c in strict if c.name == "Durable database mode").passed
    assert next(c for c in relaxed if c.name == "Durable database mode").passed


def test_presenter_urls_are_runtime_values_not_fixed_uuid():
    urls = presenter_urls(
        "http://web.test", "live runtime", {"duong": "d", "null": "n", "thieu": "t"}
    )
    assert "http://web.test/desk?session=live%20runtime" in urls
    assert "http://web.test/host?session=live%20runtime" in urls
    assert len(urls) == 7


def test_default_invocation_performs_zero_posts():
    _sessions, payloads = _payloads()
    calls = []
    checks, urls = run_checks(
        "http://api.test/api",
        "http://web.test",
        get=_getter(payloads),
        post=_poster(payloads, calls),
        now=NOW,
    )
    assert all(check.passed for check in checks)
    assert urls
    assert calls == []


def test_prepare_demo_posts_official_seeds_then_resolves_runtime_session():
    sessions, payloads = _payloads()
    sessions[:] = [s for s in sessions if s["session_id"] == "stale"]
    calls = []

    def preparing_post(url: str, body: dict | None) -> HttpResult:
        path = urlsplit(url).path
        calls.append((path, body))
        if path == "/api/demo/seed-vang":
            golden = [
                *[_session(f"generated-d{i}", f"Demo vàng · DƯƠNG rõ #{i}") for i in range(3)],
                *[_session(f"generated-n{i}", f"Demo vàng · NULL #{i}") for i in range(2)],
                _session("generated-t", "Demo vàng · CHƯA ĐỦ ĐIỀU KIỆN"),
            ]
            sessions.extend(golden)
            return HttpResult(
                200,
                json.dumps({"ket_qua": {s["session_id"]: {} for s in golden}}).encode(),
            )
        if path == "/api/demo/seed":
            runtime_id = "runtime-created-9f"
            sessions.append(
                _session(runtime_id, "Phiên demo vừa tạo", status="live", minutes_ago=5)
            )
            payloads[f"/api/sessions/{runtime_id}/state?role=operator"] = {
                "session_id": runtime_id,
                "status": "live",
                "is_demo": True,
                "current_block": {
                    "index": 1,
                    "assignment": "OFF",
                    "seconds_remaining": 120,
                },
            }
            payloads[f"/api/sessions/{runtime_id}/state?role=host"] = {
                "pinned_product": None,
                "price": None,
                "stock": None,
                "elapsed_s": 300,
            }
            return HttpResult(200, json.dumps({"replay_session_id": runtime_id}).encode())
        return HttpResult(404, b"{}")

    checks, urls = run_checks(
        "http://api.test/api",
        "http://web.test",
        prepare=True,
        get=_getter(payloads),
        post=preparing_post,
        now=NOW,
    )
    assert calls == [
        ("/api/demo/seed-vang", None),
        ("/api/demo/seed", {"n_sessions": 1, "duration_min": 60}),
    ]
    assert all(check.passed for check in checks)
    assert any("/desk?session=runtime-created-9f" in url for url in urls)
    assert all("00000000-0000-0000-0000-000000000000" not in url for url in urls)


def test_prepare_errors_fail_closed_but_still_run_read_only_preflight():
    _sessions, payloads = _payloads()
    calls = []

    def failing_post(url: str, body: dict | None) -> HttpResult:
        calls.append((urlsplit(url).path, body))
        return HttpResult(503, b'{"detail":"unavailable"}')

    checks, urls = run_checks(
        "http://api.test/api",
        "http://web.test",
        prepare=True,
        get=_getter(payloads),
        post=failing_post,
        now=NOW,
    )
    by_name = {check.name: check for check in checks}
    assert not by_name["Prepare Demo Vàng"].passed
    assert not by_name["Prepare fresh demo session"].passed
    assert by_name["API service reachable"].passed
    assert urls
    assert len(calls) == 2


def test_prepare_only_posts_demo_endpoints_and_real_summary_stays_read_only():
    _sessions, payloads = _payloads()
    post_calls = []
    get_calls = []
    base_get = _getter(payloads)

    def tracking_get(url: str) -> HttpResult:
        get_calls.append(
            urlsplit(url).path + (f"?{urlsplit(url).query}" if urlsplit(url).query else "")
        )
        return base_get(url)

    checks, _ = run_checks(
        "http://api.test/api",
        "http://web.test",
        prepare=True,
        get=tracking_get,
        post=_poster(payloads, post_calls),
        now=NOW,
    )
    assert all(check.passed for check in checks)
    assert {path for path, _body in post_calls} == {
        "/api/demo/seed-vang",
        "/api/demo/seed",
    }
    assert "/api/experiment/summary?env=real" in get_calls
    assert all("env=real" not in path for path, _body in post_calls)


def test_prepare_network_error_fails_closed():
    def raising_post(_url: str, _body: dict | None) -> HttpResult:
        raise OSError("offline")

    checks = prepare_demo_data("http://api.test/api", post=raising_post)
    assert len(checks) == 2
    assert all(not check.passed for check in checks)
