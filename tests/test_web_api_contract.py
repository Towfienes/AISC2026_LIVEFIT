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
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore

WEB_LIB = Path(__file__).resolve().parents[1] / "web" / "src" / "lib"
API_TS = WEB_LIB / "api.ts"
TYPES_TS = WEB_LIB / "types.ts"
USE_DESK_TS = WEB_LIB / "useDesk.ts"

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
    for bad in (
        "/sessions/{}/host",
        "/sessions/{}/cards",
        "/sessions/{}/execute",
        "/sessions/{}/override",
    ):
        assert bad not in called, f"api.ts lại gọi {bad} — đường dẫn này không tồn tại"
        assert bad not in routes, f"{bad} bất ngờ xuất hiện trong API — cập nhật lại test"


def test_host_state_is_requested_with_role_host():
    """Blinding: the host screen must ask for role=host, never the operator
    payload (which carries assignment + seconds_remaining)."""
    src = API_TS.read_text(encoding="utf-8")
    host_fn = src[src.index("export async function getHostState") :]
    host_fn = host_fn[: host_fn.index("\n}\n") + 3]
    assert "role=host" in host_fn, "getHostState phải gọi /state?role=host"
    assert "getState(" not in host_fn, (
        "getHostState không được rơi về payload operator — đó là rò rỉ làm mù"
    )


# ---------------------------------------------------------------------------
# WebSocket envelope contract — {type, data} on EVERY frame
#
# Defect 09/2026: the server always publishes {"type": ..., "data": ...} but
# the web client read msg.tick / msg.comment / msg.state (fields that never
# existed) and swallowed the resulting errors, so every push was silently
# dropped. These tests lock BOTH ends to the envelope so they cannot diverge
# again without a red test.
# ---------------------------------------------------------------------------

WS_TYPES = ("hello", "tick", "comment", "state", "click")


def _envelope(msg: dict, expected_type: str) -> dict:
    """Assert one frame is a {type, data} envelope and return its data."""
    assert set(msg) == {"type", "data"}, f"khung WS phải đúng {{type, data}}: {msg}"
    assert msg["type"] == expected_type, f"mong loại '{expected_type}', nhận: {msg}"
    assert msg["type"] in WS_TYPES
    assert isinstance(msg["data"], dict)
    return msg["data"]


def test_ws_frames_are_type_data_envelopes():
    """Every message kind the server publishes arrives as {type, data} with
    the payload keys the web client (types.ts) relies on."""
    app = create_app(store=InMemoryStore())
    with TestClient(app) as client:
        r = client.post(
            "/products",
            json={
                "product_id": "P1",
                "name": "Sản phẩm P1",
                "category": "test",
                "cost": 20000,
                "price": 50000,
                "stock": 10,
            },
        )
        assert r.status_code == 200, r.text
        r = client.post(
            "/sessions",
            json={"platform": "youtube", "mode": "suggest", "planned_duration_min": 60},
        )
        sid = r.json()["session_id"]
        assert client.post(f"/sessions/{sid}/schedule", json={"seed": 7}).status_code == 200

        with client.websocket_connect(f"/ws/{sid}") as ws:
            hello = _envelope(ws.receive_json(), "hello")
            assert hello == {"session_id": sid}

            assert client.post(f"/sessions/{sid}/start").status_code == 200
            assert _envelope(ws.receive_json(), "state") == {"status": "live"}

            r = client.post(f"/sessions/{sid}/ticks", json={"viewers": 42, "comment_rate": 3})
            assert r.status_code == 200, r.text
            tick = _envelope(ws.receive_json(), "tick")
            assert {
                "ts_bucket",
                "viewers",
                "comment_rate",
                "like_rate",
                "click_count",
                "pinned_product_id",
            } <= set(tick)

            r = client.post(f"/sessions/{sid}/comments", json={"text": "chốt đơn nha shop"})
            assert r.status_code == 200, r.text
            comment = _envelope(ws.receive_json(), "comment")
            assert {"comment_id", "ts", "text", "pii_kinds", "intent"} <= set(comment)

            # state push từ hành động (override chạy được ở mọi khối)
            r = client.post(
                f"/sessions/{sid}/actions/override",
                json={"product_id": "P1", "reason": "hết hàng"},
            )
            assert r.status_code == 200, r.text
            assert _envelope(ws.receive_json(), "state") == {"pinned_product_id": "P1"}

            link = client.post(
                "/shortlinks",
                json={
                    "product_id": "P1",
                    "session_id": sid,
                    "target_url": "https://shop.vidu.vn/p1",
                },
            ).json()
            assert client.get(f"/r/{link['code']}", follow_redirects=False).status_code == 302
            # gói Q1: khung click mang thêm cờ hợp lệ để bàn điều khiển phân
            # biệt click người / click bị gắn cờ ngay trong phiên
            assert _envelope(ws.receive_json(), "click") == {"product_id": "P1", "is_valid": True}

            assert client.post(f"/sessions/{sid}/end").status_code == 200
            assert _envelope(ws.receive_json(), "state") == {"status": "ended"}


def test_web_ws_types_declare_the_envelope():
    """types.ts must type WsMessage as {type, data} unions for every server
    message kind — never the pre-09/2026 msg.tick/msg.state shapes."""
    src = TYPES_TS.read_text(encoding="utf-8")
    m = re.search(r"export type WsMessage[\s\S]*?\};", src)
    assert m, "types.ts không còn khai báo WsMessage"
    union = m.group(0)
    for kind in ("tick", "comment", "state", "click"):
        assert re.search(rf'type:\s*"{kind}";\s*data:', union), (
            f'WsMessage thiếu nhánh envelope {{type: "{kind}", data}} — '
            "client sẽ lệch hợp đồng với server"
        )
    for legacy in (
        "tick: Tick",
        "state: SessionState",
        "comment: CommentItem",
        "cards: ActionCardData",
    ):
        assert legacy not in union, (
            f"WsMessage quay lại shape cũ '{legacy}' — server chỉ gửi {{type, data}}"
        )


def test_web_desk_handles_click_and_partial_state():
    """useDesk must have a 'click' branch and must NOT read full-state fields
    (elapsed_s/mode/current_block) off the partial 'state' patch."""
    src = USE_DESK_TS.read_text(encoding="utf-8")
    assert 'case "click"' in src, "useDesk thiếu nhánh xử lý thông điệp 'click'"
    assert 'case "state"' in src, "useDesk thiếu nhánh xử lý thông điệp 'state'"
    for stale in ("msg.state.elapsed_s", "msg.state.mode", "msg.state.current_block"):
        assert stale not in src, (
            f"useDesk đọc '{stale}' — payload 'state' là bản vá một phần, "
            "không phải SessionState đầy đủ"
        )


# ---------------------------------------------------------------------------
# Gói Q3 — design_hash trên payload operator, KHÔNG bao giờ trên payload host
# ---------------------------------------------------------------------------


def test_design_hash_is_in_the_operator_payload_and_typed_in_the_web_client():
    """Bàn điều khiển hiển thị cam kết thiết kế, nên `design_hash` phải có thật
    trong payload operator VÀ được khai báo trong types.ts — hai đầu lệch nhau
    chính là lỗi 27/08 (giao diện đọc trường máy chủ không gửi)."""
    app = create_app(store=InMemoryStore())
    with TestClient(app) as client:
        r = client.post(
            "/sessions",
            json={"platform": "youtube", "mode": "suggest", "planned_duration_min": 60},
        )
        sid = r.json()["session_id"]
        sched = client.post(f"/sessions/{sid}/schedule", json={"seed": 7})
        assert sched.status_code == 200, sched.text
        assert len(sched.json()["design_hash"]) == 64

        state = client.get(f"/sessions/{sid}/state?role=operator").json()
        assert state["design_hash"] == sched.json()["design_hash"]

    src = TYPES_TS.read_text(encoding="utf-8")
    m = re.search(r"export interface SessionState \{[\s\S]*?\n\}", src)
    assert m, "types.ts không còn khai báo SessionState"
    assert re.search(r"design_hash:\s*string \| null;", m.group(0)), (
        "SessionState thiếu design_hash — bàn sẽ đọc undefined"
    )


def test_host_payload_never_carries_the_design_hash():
    """Quy tắc L6: design_hash là vân tay của cơ chế gán. Nó không được nằm
    trong payload host, và client vẫn phải liệt kê nó ở lớp phòng thủ thứ hai."""
    app = create_app(store=InMemoryStore())
    with TestClient(app) as client:
        r = client.post(
            "/sessions",
            json={"platform": "youtube", "mode": "suggest", "planned_duration_min": 60},
        )
        sid = r.json()["session_id"]
        assert client.post(f"/sessions/{sid}/schedule", json={"seed": 7}).status_code == 200
        host = client.get(f"/sessions/{sid}/state?role=host").json()
        assert "design_hash" not in host

    api_src = API_TS.read_text(encoding="utf-8")
    forbidden = re.search(r"const HOST_FORBIDDEN_KEYS = \[[\s\S]*?\] as const;", api_src)
    assert forbidden, "api.ts không còn danh sách khóa cấm cho payload host"
    assert '"design_hash"' in forbidden.group(0), (
        "HOST_FORBIDDEN_KEYS thiếu design_hash — mất lớp phòng thủ thứ hai"
    )
