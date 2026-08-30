"""Contract gate: every API path the web client calls MUST exist in the API.

Incident 27/08: the web client and the FastAPI backend were built in parallel
and their paths diverged (`/sessions/{id}/host`, `/cards`, `/execute`,
`/override` — all 404). Because one failing call took down the whole
`Promise.all` poll, the control desk froze permanently while still reporting
"connected". Nothing in the test suite could see it: the backend tests only
tested the backend, the frontend build only type-checked the frontend.

This test reads the paths straight out of `web/src/lib/api.ts` and asserts each
one resolves against the real FastAPI route table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore

API_TS = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "api.ts"

# Template literals in api.ts, e.g. `/sessions/${sessionId}/state?role=operator`
_CALL_RE = re.compile(
    r"request<[^>]*>\(\s*[`\"']([^`\"']+)[`\"']"
    r"|request\(\s*[`\"']([^`\"']+)[`\"']"
)
_INTERP_RE = re.compile(r"\$\{[^}]*\}")


def web_called_paths() -> set[str]:
    """Every API path api.ts calls, normalized to `/a/{}/b` (params blanked)."""
    src = API_TS.read_text(encoding="utf-8")
    found: set[str] = set()
    for m in _CALL_RE.finditer(src):
        raw = m.group(1) or m.group(2)
        if not raw or not raw.startswith("/"):
            continue
        path = raw.split("?", 1)[0]
        found.add(_INTERP_RE.sub("{}", path))
    return found


def api_route_patterns(app) -> set[str]:
    """Every path the API serves, normalized the same way.

    Read from the OpenAPI schema rather than ``app.routes``: recent FastAPI
    versions keep included routers in opaque wrapper objects, and the schema is
    the version-independent source of truth for the documented surface.
    """
    schema = app.openapi()
    return {re.sub(r"\{[^}]*\}", "{}", path) for path in schema.get("paths", {})}


@pytest.fixture(scope="module")
def routes() -> set[str]:
    return api_route_patterns(create_app(store=InMemoryStore()))


def test_api_ts_is_readable():
    assert API_TS.exists(), f"không tìm thấy {API_TS}"
    assert web_called_paths(), "không trích được đường dẫn nào từ api.ts — regex hỏng?"


def test_every_web_path_exists_in_the_api(routes):
    called = web_called_paths()
    missing = sorted(p for p in called if p not in routes)
    assert not missing, (
        "Giao diện gọi đường dẫn KHÔNG tồn tại trong API "
        f"(sẽ trả 404 lúc chạy thật): {missing}\n"
        f"Đường dẫn API hiện có: {sorted(routes)}"
    )


def test_known_bad_paths_stay_gone(routes):
    """The exact four paths from incident 27/08 must never come back."""
    called = web_called_paths()
    for bad in ("/sessions/{}/host", "/sessions/{}/cards",
                "/sessions/{}/execute", "/sessions/{}/override"):
        assert bad not in called, f"api.ts lại gọi {bad} — đường dẫn này không tồn tại"
        assert bad not in routes, f"{bad} bất ngờ xuất hiện trong API — cập nhật lại test"


def test_host_state_is_requested_with_role_host():
    """Blinding: the host screen must ask for role=host, never the operator
    payload (which carries assignment + seconds_remaining)."""
    src = API_TS.read_text(encoding="utf-8")
    host_fn = src[src.index("export async function getHostState"):]
    host_fn = host_fn[: host_fn.index("\n}\n") + 3]
    assert "role=host" in host_fn, "getHostState phải gọi /state?role=host"
    assert "getState(" not in host_fn, (
        "getHostState không được rơi về payload operator — đó là rò rỉ làm mù"
    )
