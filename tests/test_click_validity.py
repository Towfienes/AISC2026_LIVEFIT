"""Valid-click classification (gói Q1) — IAB GIVT-lite, flag-don't-drop.

Every rule is exercised one by one, the τ sensitivity must move the counts in
the right direction, the redirect must stay a 302 even for bots, and the whole
module must remain blind to the treatment assignment. The sim gate at the end
injects bot clicks into simulated sessions with a KNOWN effect: the estimator
on VALID clicks stays calibrated while the raw series is visibly biased.
"""

from __future__ import annotations

import inspect
import random
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from livelift.analysis.estimators import diff_in_means
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.core import click_validity as cv_module
from livelift.core.assigner.outer import DesignParams, generate_schedule
from livelift.core.click_validity import (
    INVALID_REASONS,
    PriorClick,
    classify_click,
    recount_click_validity,
)
from livelift.core.features import Event, block_frame
from livelift.sim.simulator import SimParams, simulate_session, true_effect

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0"
BOT_UA = "Googlebot/2.1 (+http://www.google.com/bot.html)"
T0 = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Rule-by-rule unit tests (pure function)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ua",
    [
        BOT_UA,
        "curl/8.4.0",
        "Wget/1.21.3",
        "python-requests/2.31.0",
        "Scrapy/2.9 (+https://scrapy.org)",
        "Mozilla/5.0 HeadlessChrome/128.0",
        "PhantomJS/2.1.1",
        "Mozilla/5.0 (compatible; bingbot/2.0)",
        "some-crawler/1.0",
        "web spider deluxe",
    ],
)
def test_givt_ua_is_invalid(ua):
    is_valid, reason, ua_class = classify_click(ua, {}, "GET")
    assert is_valid is False
    assert reason == "givt_ua"
    assert ua_class == "givt"


def test_browser_and_unknown_ua_are_valid():
    assert classify_click(BROWSER_UA, {}, "GET") == (True, None, "browser")
    # No UA is suspicious but NOT auto-invalid — flagged only by other rules.
    assert classify_click(None, {}, "GET") == (True, None, "unknown")
    assert classify_click("   ", {}, "GET") == (True, None, "unknown")


@pytest.mark.parametrize(
    "headers",
    [
        {"Sec-Purpose": "prefetch;anonymous-client-ip"},
        {"sec-purpose": "prerender"},
        {"X-Moz": "prefetch"},
        {"x-purpose": "preview"},
    ],
)
def test_prefetch_headers_are_invalid(headers):
    is_valid, reason, ua_class = classify_click(BROWSER_UA, headers, "GET")
    assert is_valid is False
    assert reason == "prefetch"
    assert ua_class == "browser"


@pytest.mark.parametrize("method", ["POST", "HEAD", "OPTIONS", "put"])
def test_non_get_is_invalid(method):
    is_valid, reason, _ = classify_click(BROWSER_UA, {}, method)
    assert is_valid is False
    assert reason == "non_get"


def test_human_double_click_second_is_refractory():
    """2 click cách 3 giây của cùng một người: click 2 bị gắn cờ, không xóa."""
    first = classify_click(BROWSER_UA, {}, "GET", [])
    assert first == (True, None, "browser")
    second = classify_click(BROWSER_UA, {}, "GET", [PriorClick(age_s=3.0)])
    assert second == (False, "refractory", "browser")
    # Beyond τ the same fingerprint counts again.
    third = classify_click(BROWSER_UA, {}, "GET", [PriorClick(age_s=15.0)])
    assert third == (True, None, "browser")


def test_refractory_anchors_on_counted_clicks_only():
    """An UNCOUNTED (already-invalid) click must not extend the window."""
    priors = [PriorClick(age_s=3.0, counted=False), PriorClick(age_s=12.0, counted=True)]
    assert classify_click(BROWSER_UA, {}, "GET", priors)[0] is True


def test_volume_cap_per_hash_shortlink_block():
    spaced = [PriorClick(age_s=20.0 * (i + 1)) for i in range(5)]
    is_valid, reason, _ = classify_click(BROWSER_UA, {}, "GET", spaced)
    assert (is_valid, reason) == (False, "volume_cap")
    # Clicks from OTHER blocks do not count toward this block's cap.
    mixed = spaced[:3] + [
        PriorClick(age_s=200.0, same_block=False),
        PriorClick(age_s=300.0, same_block=False),
    ]
    assert classify_click(BROWSER_UA, {}, "GET", mixed)[0] is True
    # The cap is a parameter.
    assert classify_click(BROWSER_UA, {}, "GET", spaced[:3], volume_cap=3)[1] == "volume_cap"


def test_burst_collapses_to_one_valid_click():
    """10 click trong 5 giây cùng dedup_hash → đúng 1 click hợp lệ."""
    history: list[tuple[float, bool]] = []  # (ts, counted)
    verdicts = []
    for i in range(10):
        ts = i * 0.5
        priors = [PriorClick(age_s=ts - t, counted=c) for t, c in history]
        is_valid, reason, _ = classify_click(BROWSER_UA, {}, "GET", priors)
        verdicts.append((is_valid, reason))
        history.append((ts, is_valid))
    assert sum(1 for v, _ in verdicts if v) == 1
    assert verdicts[0] == (True, None)
    assert all(reason == "refractory" for v, reason in verdicts[1:] if not v)


# ---------------------------------------------------------------------------
# Recount (T+30' reconciliation, τ sensitivity)
# ---------------------------------------------------------------------------


def _row(i, ts_s, dedup_hash="h1", code="c1", block="b1", is_valid=True, reason=None):
    return {
        "click_id": f"k{i}",
        "ts": T0 + timedelta(seconds=ts_s),
        "dedup_hash": dedup_hash,
        "shortlink_code": code,
        "block_id": block,
        "is_valid": is_valid,
        "invalid_reason": reason,
    }


def _apply(rows, changes):
    by_id = {c["click_id"]: c for c in changes}
    out = []
    for r in rows:
        ch = by_id.get(r["click_id"])
        merged = dict(r)
        if ch is not None:
            merged["is_valid"] = ch["is_valid"]
            merged["invalid_reason"] = ch["invalid_reason"]
        out.append(merged)
    return out


def test_recount_tau_sensitivity_moves_the_right_way():
    """τ lớn hơn → cửa sổ refractory rộng hơn → SỐ CLICK HỢP LỆ không tăng."""
    rows = [_row(0, 0.0), _row(1, 7.0), _row(2, 20.0), _row(3, 45.0)]
    invalid_at = {}
    for tau in (5.0, 10.0, 30.0, 60.0):
        changes = recount_click_validity(rows, tau_s=tau)
        assert all(not c["is_valid"] for c in changes)  # rows start all-valid
        invalid_at[tau] = len(changes)
    assert invalid_at[5.0] == 0
    assert invalid_at[10.0] == 1
    assert invalid_at[30.0] == 2
    assert invalid_at[60.0] == 3
    assert invalid_at[5.0] <= invalid_at[10.0] <= invalid_at[30.0] <= invalid_at[60.0]


def test_recount_flags_and_unflags_and_is_idempotent():
    rows = [
        _row(0, 0.0),
        _row(1, 3.0),  # stored valid, actually refractory
        _row(2, 30.0, is_valid=False, reason="refractory"),  # stored wrong: 30s > τ
    ]
    changes = recount_click_validity(rows, tau_s=10.0)
    as_dict = {c["click_id"]: c for c in changes}
    assert as_dict["k1"]["is_valid"] is False
    assert as_dict["k1"]["invalid_reason"] == "refractory"
    assert as_dict["k2"]["is_valid"] is True
    assert as_dict["k2"]["invalid_reason"] is None
    # Applying the changes and recounting again changes nothing (fixed point).
    assert recount_click_validity(_apply(rows, changes), tau_s=10.0) == []


def test_recount_keeps_request_only_verdicts_and_ignores_them_as_anchors():
    """UA/headers không được lưu → 'givt_ua'/'prefetch'/'non_get' giữ nguyên,
    và click bot không được tính làm mốc refractory cho người thật."""
    rows = [
        _row(0, 0.0, is_valid=False, reason="givt_ua"),
        _row(1, 3.0),  # human 3s after the BOT click — must stay valid
    ]
    assert recount_click_validity(rows, tau_s=10.0) == []


def test_recount_rows_without_dedup_hash_stay_valid():
    rows = [_row(0, 0.0, dedup_hash=None), _row(1, 1.0, dedup_hash=None)]
    assert recount_click_validity(rows, tau_s=10.0) == []


def test_property_valid_count_never_exceeds_total():
    rng = random.Random(42)
    rows = []
    for i in range(300):
        rows.append(
            _row(
                i,
                ts_s=rng.uniform(0, 600),
                dedup_hash=rng.choice(["h1", "h2", "h3", "h4", None]),
                code=rng.choice(["c1", "c2"]),
                block=rng.choice(["b1", "b2", "b3"]),
            )
        )
    for tau in (5.0, 10.0, 30.0, 60.0):
        changes = recount_click_validity(rows, tau_s=tau)
        flagged = [c for c in changes if not c["is_valid"]]
        n_valid = len(rows) - len(flagged)
        assert 0 <= n_valid <= len(rows)
        assert all(c["invalid_reason"] in INVALID_REASONS for c in flagged)
        # fixed point after applying
        assert recount_click_validity(_apply(rows, changes), tau_s=tau) == []


# ---------------------------------------------------------------------------
# livelift-qc --recount-clicks (T+30' reconciliation hook)
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeConn:
    """Minimal psycopg-shaped connection: records every statement so the test
    can assert what the reconciliation actually writes."""

    def __init__(self, rows):
        self._rows = rows
        self.statements: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.statements.append((" ".join(sql.split()), params))
        return _FakeCursor(self._rows if sql.strip().upper().startswith("SELECT") else [])


def test_qc_recount_updates_flags_never_deletes_and_prints_sensitivity(capsys):
    """Hook đối soát T+30': đọc click của phiên, chạy lại quy tắc thời gian,
    CẬP NHẬT cờ (không bao giờ DELETE — flag-don't-drop) và in bảng τ ∈ {5,30,60}."""
    # Imported inside the test: quality_cli pulls in psycopg (optional `server`
    # extra), and the pure rules + sim gate above must stay importable without it.
    quality_cli = pytest.importorskip("livelift.core.quality_cli")

    # ts=0 valid; ts=3 stored valid but refractory at τ=10; ts=30 stored invalid
    # but 30 s after the last counted click, so it must be un-flagged.
    rows = [
        ("k0", T0, "h1", "c1", "b1", True, None),
        ("k1", T0 + timedelta(seconds=3), "h1", "c1", "b1", True, None),
        ("k2", T0 + timedelta(seconds=30), "h1", "c1", "b1", False, "refractory"),
    ]
    conn = _FakeConn(rows)
    quality_cli._recount_clicks(conn, "sid-1", 10.0)

    kinds = [s.split()[0].upper() for s, _ in conn.statements]
    assert kinds[0] == "SELECT"
    assert set(kinds[1:]) == {"UPDATE"}, "chỉ được UPDATE cờ"
    assert not any("DELETE" in s.upper() for s, _ in conn.statements), "không bao giờ xóa row"
    updates = {p[2]: (p[0], p[1]) for s, p in conn.statements if s.upper().startswith("UPDATE")}
    assert updates == {"k1": (False, "refractory"), "k2": (True, None)}

    out = capsys.readouterr().out
    assert "3 click, 2 cờ thay đổi" in out
    for tau in quality_cli.SENSITIVITY_TAUS:
        assert f"sensitivity τ={tau:g}s" in out
    # Đúng chiều: τ rộng hơn → số click hợp lệ không tăng (60 s nuốt cả k2).
    assert "τ=5s: 2/3 click hợp lệ" in out
    assert "τ=30s: 2/3 click hợp lệ" in out
    assert "τ=60s: 1/3 click hợp lệ" in out


# ---------------------------------------------------------------------------
# Assignment-blindness (pre-registered invariant)
# ---------------------------------------------------------------------------


def test_assignment_blindness():
    """Mọi quy tắc chỉ dùng thuộc tính request — hàm không được NHẬN nhánh gán,
    và module không được import gì từ bộ gán."""
    forbidden = {"assignment", "arm", "z", "propensity", "treatment", "schedule"}
    for fn in (classify_click, recount_click_validity):
        params = set(inspect.signature(fn).parameters)
        assert params.isdisjoint(forbidden), f"{fn.__name__} nhận tham số gán: {params & forbidden}"
    assert "ASSIGNMENT-BLINDNESS" in (cv_module.__doc__ or "")
    src = inspect.getsource(cv_module)
    assert "assigner" not in src, "click_validity không được import bộ gán"
    # PriorClick carries request history only: no field can name the arm.
    prior_fields = set(inspect.signature(PriorClick).parameters)
    assert prior_fields == {"age_s", "counted", "same_block"}


# ---------------------------------------------------------------------------
# API: redirect always 302, rows flagged in the store
# ---------------------------------------------------------------------------


@pytest.fixture
def client_and_store():
    store = InMemoryStore()
    app = create_app(store=store)
    with TestClient(app) as c:
        yield c, store


def _live_session_with_link(client):
    client.post(
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
    sid = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60}
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 7})
    client.post(f"/sessions/{sid}/start")
    code = client.post(
        "/shortlinks",
        json={"product_id": "P1", "session_id": sid, "target_url": "https://shop.example/p1"},
    ).json()["code"]
    return sid, code


def test_redirect_still_302_for_bot_ua_and_click_is_flagged(client_and_store):
    client, store = client_and_store
    sid, code = _live_session_with_link(client)

    r = client.get(f"/r/{code}", follow_redirects=False, headers={"User-Agent": BOT_UA})
    assert r.status_code == 302, "redirect KHÔNG BAO GIỜ được chặn — kể cả bot"
    assert r.headers["location"] == "https://shop.example/p1"

    clicks = store.list_clicks(sid)
    assert len(clicks) == 1, "flag-don't-drop: click bot vẫn được ghi"
    assert clicks[0]["is_valid"] is False
    assert clicks[0]["invalid_reason"] == "givt_ua"
    assert clicks[0]["ua_class"] == "givt"


def test_redirect_flags_rapid_double_click_as_refractory(client_and_store):
    client, store = client_and_store
    sid, code = _live_session_with_link(client)

    for _ in range(2):
        r = client.get(f"/r/{code}", follow_redirects=False, headers={"User-Agent": BROWSER_UA})
        assert r.status_code == 302

    clicks = store.list_clicks(sid)
    assert len(clicks) == 2
    assert clicks[0]["is_valid"] is True
    assert clicks[0]["ua_class"] == "browser"
    assert clicks[1]["is_valid"] is False
    assert clicks[1]["invalid_reason"] == "refractory"


def test_redirect_reads_only_the_matching_fingerprint(client_and_store):
    """Phân loại KHÔNG được quét toàn bộ click của phiên: mỗi redirect chỉ đọc
    lịch sử của đúng fingerprint đó trên đúng shortlink đó. Quét cả phiên làm
    redirect chậm dần theo số click — tệ nhất đúng lúc bot đang bắn."""
    client, store = client_and_store
    sid, code = _live_session_with_link(client)

    # The route swallows exceptions to protect the 302, so the spies RECORD
    # instead of raising — an assertion inside them would be logged and lost.
    calls: list[tuple[str, str | None]] = []
    narrow, full = store.list_clicks_for_fingerprint, store.list_clicks

    def spy_narrow(session_id, dedup_hash, shortlink_code):
        calls.append(("narrow", shortlink_code))
        return narrow(session_id, dedup_hash, shortlink_code)

    def spy_full(session_id):
        calls.append(("full_scan", None))
        return full(session_id)

    store.list_clicks_for_fingerprint = spy_narrow  # type: ignore[method-assign]
    store.list_clicks = spy_full  # type: ignore[method-assign]
    try:
        r = client.get(f"/r/{code}", follow_redirects=False, headers={"User-Agent": BROWSER_UA})
    finally:
        del store.list_clicks
        del store.list_clicks_for_fingerprint

    assert r.status_code == 302
    assert calls == [("narrow", code)], f"redirect phải đọc đúng một slice hẹp, đã gọi: {calls}"
    assert len(store.list_clicks(sid)) == 1


def test_experiment_summary_reports_raw_and_valid_click_totals(client_and_store):
    from tests.conftest import seed_phien_that_mo_phong

    client, store = client_and_store
    # Tổng nhấp thô/hợp lệ là số vận hành của KẾT QUẢ THẬT — seed phiên thật
    # mô phỏng (gói DEMO-THẬT: phiên demo không còn vào bản gộp mặc định).
    seed_phien_that_mo_phong(store)
    summary = client.get("/experiment/summary").json()
    assert summary["raw_clicks"] is not None
    assert summary["valid_clicks"] is not None
    assert 0 < summary["valid_clicks"] <= summary["raw_clicks"]


def test_session_report_blocks_carry_the_raw_click_series(client_and_store):
    """Tiền đăng ký §4.1: chuỗi raw là secondary BẮT BUỘC báo cáo kèm — mỗi
    dòng khối của báo cáo phiên phải mang clicks_raw bên cạnh click hợp lệ,
    nếu không thì lời hứa 'báo cáo song song' chỉ nằm trên giấy."""
    client, _ = client_and_store
    client.post("/demo/seed", json={"n_sessions": 2, "effect": 0.5, "duration_min": 40})
    ended = [s for s in client.get("/sessions").json() if s["status"] == "ended"]
    assert ended, "demo seed phải tạo phiên đã kết thúc"

    rows = client.get(f"/sessions/{ended[0]['session_id']}/report").json()["blocks"]
    assert rows
    for r in rows:
        assert "clicks_raw" in r, "thiếu chuỗi raw trong báo cáo khối"
        assert r["clicks_raw"] >= r["clicks"], "raw luôn ⊇ hợp lệ"


# ---------------------------------------------------------------------------
# Sim gate: injected bot traffic must not bias the VALID-click estimator
# ---------------------------------------------------------------------------


def _classify_stream(human_events, bot_bursts_per_click=2):
    """Run every (human + injected bot) click through the production
    classifier, in timestamp order, and return Events carrying the verdicts.

    Humans are distinct viewers (unique fingerprints); each human click
    triggers a burst of bot clicks 0.4/0.9s later with a crawler UA — traffic
    proportional to real interest, the pattern that inflates raw counts.
    """
    requests = []
    for i, ev in enumerate(human_events):
        if ev.kind != "click":
            continue
        requests.append((ev.ts_offset_s, BROWSER_UA, f"human-{i}"))
        for j in range(bot_bursts_per_click):
            requests.append((ev.ts_offset_s + 0.4 + 0.5 * j, BOT_UA, f"bot-{i}-{j}"))
    requests.sort(key=lambda r: r[0])

    history: dict[str, list[tuple[float, bool]]] = {}
    out, n_bot_valid = [], 0
    for ts, ua, fingerprint in requests:
        priors = [PriorClick(age_s=ts - t, counted=c) for t, c in history.get(fingerprint, [])]
        is_valid, _, _ = classify_click(ua, {}, "GET", priors)
        history.setdefault(fingerprint, []).append((ts, is_valid))
        if ua == BOT_UA and is_valid:
            n_bot_valid += 1
        out.append(Event("click", ts, product_id="P1", is_valid=is_valid))
    assert n_bot_valid == 0, "bộ phân loại phải bắt được toàn bộ bot UA"
    return out


@pytest.mark.slow
def test_gate_bot_injection_valid_estimator_stays_calibrated():
    """GATE (gói Q1): tiêm click bot vào phiên mô phỏng với ATE biết trước —
    ước lượng trên click HỢP LỆ giữ bias < 10% (tiêu chí E3-06), còn trên raw
    lệch rõ (+~200% với 2 bot/click người).

    Cấu hình nhẹ so với các gate hiệu chỉnh đầy đủ: 15 reps × 6 phiên × 90′,
    seed rút từ master seed cố định (mô thức run_validation). Đo 08/09/2026:
    bias valid +0,2% (sd giữa reps 13,6%), bias raw +201%, min raw/rep +99%.
    """
    n_reps, n_sessions = 15, 6
    params = SimParams(treatment_effect=0.4)
    design = DesignParams(jitter_s=0)
    seed_rng = random.Random(2026)

    biases_valid, biases_raw = [], []
    for _ in range(n_reps):
        ys_valid, ys_raw, zs, truths = [], [], [], []
        for _ in range(n_sessions):
            seed = seed_rng.randrange(2**32)
            schedule = generate_schedule(90, design, seed)
            out = simulate_session(schedule, params, seed)
            non_click = [e for e in out.events if e.kind != "click"]
            clicks = _classify_stream([e for e in out.events if e.kind == "click"])
            events = non_click + clicks

            frame_valid = block_frame(schedule, events, burn_in_s=60)
            frame_raw = block_frame(schedule, events, burn_in_s=60, include_invalid=True)
            for rv, rr in zip(frame_valid, frame_raw, strict=True):
                if not (rv.measurable and rr.measurable):
                    continue
                ys_valid.append(rv.y)
                ys_raw.append(rr.y)
                zs.append(rv.z)
            truths.append(true_effect(schedule, params, seed))

        truth = float(np.mean(truths))
        assert truth > 0
        y_v, y_r, z = np.array(ys_valid), np.array(ys_raw), np.array(zs)
        biases_valid.append((diff_in_means(y_v, z) - truth) / truth)
        biases_raw.append((diff_in_means(y_r, z) - truth) / truth)

    bias_valid = float(np.mean(biases_valid))
    bias_raw = float(np.mean(biases_raw))
    assert abs(bias_valid) < 0.10, (
        f"bias trên click hợp lệ {bias_valid:+.1%} vượt 10% dù bot đã bị gắn cờ"
    )
    # "Lệch rõ": ngưỡng 0,5 thận trọng gấp 5 lần gate chính; giá trị đo ≈ +2,0.
    assert bias_raw > 0.5, f"bias raw {bias_raw:+.1%} phải lệch rõ (bot làm phồng tử số)"
    assert min(biases_raw) > 0.3, "mọi rep raw đều phải lệch dương rõ"
    assert bias_raw > bias_valid
