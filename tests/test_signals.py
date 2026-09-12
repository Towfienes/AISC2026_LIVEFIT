"""Signal coverage matrix: the honest answer to "can it measure any video?"."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.core.signals import assess


def cap(cov, name):
    return next(c for c in cov.capabilities if c.name.startswith(name))


def test_own_full_session_unlocks_everything_but_orders():
    cov = assess(
        has_schedule=True,
        n_ticks=100,
        n_ticks_with_viewers=100,
        tick_coverage_share=0.95,
        n_comments=50,
        n_clicks_valid=20,
        n_clicks_raw=20,
        n_orders=0,
        n_reactions=0,
    )
    assert cap(cov, "thí nghiệm").status == "ok"
    assert cap(cov, "tỷ lệ nhấp").status == "ok"
    assert cap(cov, "đối soát").status == "missing"


def test_external_vod_gets_observational_capabilities_only():
    """A YouTube VOD of someone else's live: comments only. The matrix must
    say EXACTLY what that supports — radar yes, experiment impossible."""
    cov = assess(
        has_schedule=False,
        n_ticks=0,
        n_ticks_with_viewers=0,
        tick_coverage_share=0.0,
        n_comments=500,
        n_clicks_valid=0,
        n_clicks_raw=0,
        n_orders=0,
        n_reactions=0,
        analysis_only=True,
    )
    assert cap(cov, "radar").status == "ok"
    assert cap(cov, "thí nghiệm").status == "missing"
    assert "ngược thời gian" in next(s for s in cov.signals if s.name == "schedule").detail
    assert cap(cov, "tỷ lệ nhấp").status == "missing"


def test_degraded_telemetry_degrades_dependent_capabilities():
    cov = assess(
        has_schedule=True,
        n_ticks=20,
        n_ticks_with_viewers=20,
        tick_coverage_share=0.5,
        n_comments=10,
        n_clicks_valid=5,
        n_clicks_raw=5,
        n_orders=0,
        n_reactions=0,
    )
    assert cap(cov, "nhịp phiên").status == "degraded"
    assert cap(cov, "thí nghiệm").status == "degraded"


def test_no_shortlinks_means_ctr_is_declared_unmeasurable():
    cov = assess(
        has_schedule=True,
        n_ticks=100,
        n_ticks_with_viewers=100,
        tick_coverage_share=1.0,
        n_comments=10,
        n_clicks_valid=0,
        n_clicks_raw=0,
        n_orders=0,
        n_reactions=0,
    )
    assert cap(cov, "tỷ lệ nhấp").status == "missing"
    assert "link đo" in next(s for s in cov.signals if s.name == "clicks").detail


def test_comment_tempo_ticks_are_not_counted_as_viewer_telemetry():
    """Regression, live-fire 10/09/2026 (`docs/benchmarks/live-fire-da-nguon.md`).

    A replay analysis writes one tick per 30 s to carry the comment tempo and
    fills ``viewers`` with a placeholder 0.0 — a finished VOD does not expose
    concurrent viewers. Grading those rows as telemetry made the matrix report
    "nhịp phiên (người xem theo thời gian): ok" on a session whose viewer
    column is entirely placeholder. The count of rows is not the question; the
    count of rows carrying a viewer number is.
    """
    cov = assess(
        has_schedule=False,
        n_ticks=141,  # 70 minutes of video at one bucket per 30 s
        n_ticks_with_viewers=0,  # ...none of which knows how many people watched
        tick_coverage_share=1.0,
        n_comments=23,
        n_clicks_valid=0,
        n_clicks_raw=0,
        n_orders=0,
        n_reactions=0,
        analysis_only=True,
    )
    ticks = next(s for s in cov.signals if s.name == "ticks")
    assert ticks.status == "missing"
    assert "nhịp bình luận" in ticks.detail.lower()
    assert cap(cov, "nhịp phiên").status == "missing"
    # Comments are real, so the capability they unlock stays available.
    assert cap(cov, "radar").status == "ok"


def test_partially_missing_viewer_numbers_degrade_the_ticks_signal():
    """Half the buckets carrying a viewer count is degraded telemetry, not ok."""
    cov = assess(
        has_schedule=True,
        n_ticks=100,
        n_ticks_with_viewers=50,
        tick_coverage_share=1.0,
        n_comments=10,
        n_clicks_valid=5,
        n_clicks_raw=5,
        n_orders=0,
        n_reactions=0,
    )
    ticks = next(s for s in cov.signals if s.name == "ticks")
    assert ticks.status == "degraded"
    assert "50/100" in ticks.detail
    assert cap(cov, "nhịp phiên").status == "degraded"


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


def test_signals_endpoint_end_to_end(client):
    sid = client.post(
        "/sessions",
        json={
            "platform": "youtube",
            "mode": "auto",
            "planned_duration_min": 60,
        },
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 3})
    client.post(f"/sessions/{sid}/start")
    client.post(f"/sessions/{sid}/ticks", json={"viewers": 50})

    res = client.get(f"/sessions/{sid}/signals")
    assert res.status_code == 200
    body = res.json()
    names = {s["name"] for s in body["signals"]}
    assert names == {"schedule", "ticks", "comments", "clicks", "orders", "reactions"}
    schedule = next(s for s in body["signals"] if s["name"] == "schedule")
    assert schedule["status"] == "ok"
    exp = next(c for c in body["capabilities"] if "thí nghiệm" in c["name"])
    assert exp["status"] == "missing"  # no clicks yet -> declared, not hidden


def test_signals_endpoint_bad_id_is_404(client):
    assert client.get("/sessions/nope/signals").status_code == 404


def test_signals_endpoint_refuses_to_claim_viewers_from_tempo_only_ticks(client):
    """End-to-end guard for the live-fire 10/09/2026 finding.

    Ticks that carry only a comment rate — exactly what
    ``POST /replays/youtube`` writes for a finished VOD — must never make the
    endpoint announce the viewers-over-time capability.
    """
    sid = client.post(
        "/sessions",
        json={"platform": "replay", "mode": "auto", "planned_duration_min": 5},
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 3})
    client.post(f"/sessions/{sid}/start")
    for rate in (4.0, 8.0, 2.0):
        assert (
            client.post(
                f"/sessions/{sid}/ticks", json={"viewers": 0.0, "comment_rate": rate}
            ).status_code
            < 400
        )

    body = client.get(f"/sessions/{sid}/signals").json()
    ticks = next(s for s in body["signals"] if s["name"] == "ticks")
    assert ticks["status"] == "missing"
    rhythm = next(c for c in body["capabilities"] if c["name"].startswith("nhịp phiên"))
    assert rhythm["status"] == "missing"
    ctr = next(c for c in body["capabilities"] if c["name"].startswith("tỷ lệ nhấp"))
    assert ctr["status"] == "missing"


# ---------------------------------------------------------------------------
# Click: MỘT định nghĩa cho mọi màn hình (tiền đăng ký §4.1)
# ---------------------------------------------------------------------------
#
# Sự cố 12/09 (kiem-chung-van-hanh.md §2.4a): `/signals` chấm tín hiệu bằng SỐ
# DÒNG click, còn báo cáo và ước lượng viên dùng click HỢP LỆ. Một phiên có 93
# cú bấm bot được báo "clicks: ok — 93 lượt nhấp" và "thí nghiệm nhân quả: ok —
# đủ tín hiệu", trong khi `/report` cùng phiên cho clicks = 0 ở mọi khối và
# diff_in_means = null. Hai màn hình, hai sự thật, không một lời giải thích.


def sig(cov, name):
    return next(s for s in cov.signals if s.name == name)


def test_all_clicks_flagged_invalid_is_a_missing_signal_not_an_ok_one():
    cov = assess(
        has_schedule=True,
        n_ticks=60,
        n_ticks_with_viewers=60,
        tick_coverage_share=1.0,
        n_comments=62,
        n_clicks_valid=0,  # bộ lọc GIVT gắn cờ toàn bộ
        n_clicks_raw=93,
        n_orders=0,
        n_reactions=0,
    )
    clicks = sig(cov, "clicks")
    assert clicks.status == "missing"
    assert clicks.detail.startswith("0 ")
    assert "93" in clicks.detail
    # ...và năng lực phụ thuộc nó KHÔNG được khoe là đủ tín hiệu.
    assert cap(cov, "thí nghiệm").status == "missing"
    assert cap(cov, "tỷ lệ nhấp").status == "missing"


def test_click_signal_leads_with_the_valid_number_and_labels_the_raw_one():
    """Số ĐẦU TIÊN trong detail là con số phân tích dùng; số thô đi kèm, có nhãn."""
    cov = assess(
        has_schedule=True,
        n_ticks=60,
        n_ticks_with_viewers=60,
        tick_coverage_share=1.0,
        n_comments=86,
        n_clicks_valid=210,
        n_clicks_raw=212,
        n_orders=0,
        n_reactions=0,
    )
    clicks = sig(cov, "clicks")
    assert clicks.status == "ok"
    assert clicks.detail.startswith("210 ")
    assert "212" not in clicks.detail, "số thô không được trộn vào câu chính"
    assert clicks.secondary is not None
    assert "212" in clicks.secondary
    assert "2" in clicks.secondary  # số bị gắn cờ
    assert cap(cov, "thí nghiệm").status == "ok"


def test_mostly_flagged_traffic_degrades_instead_of_passing_silently():
    cov = assess(
        has_schedule=True,
        n_ticks=60,
        n_ticks_with_viewers=60,
        tick_coverage_share=1.0,
        n_comments=30,
        n_clicks_valid=4,
        n_clicks_raw=40,
        n_orders=0,
        n_reactions=0,
    )
    clicks = sig(cov, "clicks")
    assert clicks.status == "degraded"
    assert clicks.detail.startswith("4 ")
    assert cap(cov, "thí nghiệm").status == "degraded"


def test_no_link_at_all_is_still_told_apart_from_zero_valid():
    """ "Chưa có link đo" và "có link, 0 cú hợp lệ" là hai sự thật khác nhau."""
    khong_link = assess(
        has_schedule=True,
        n_ticks=60,
        n_ticks_with_viewers=60,
        tick_coverage_share=1.0,
        n_comments=10,
        n_clicks_valid=0,
        n_clicks_raw=0,
        n_orders=0,
        n_reactions=0,
    )
    assert sig(khong_link, "clicks").secondary is None
    assert "link đo" in sig(khong_link, "clicks").detail
    assert "hợp lệ" not in sig(khong_link, "clicks").detail


def test_signals_endpoint_reports_the_same_click_number_as_bao_cao(client):
    """Chốt chặn end-to-end: hai màn hình phải nói cùng một con số.

    Bốn người xem thật + ba cú bấm bot trên cùng link đo. `/signals` và
    `/bao-cao` được hỏi độc lập; con số phải khớp, và số thô phải hiện ra
    ở cả hai chỗ với nhãn riêng.
    """
    client.post(
        "/products",
        json={"product_id": "NH1", "name": "Nước hoa mini", "cost": 1, "price": 2, "stock": 9},
    )
    sid = client.post(
        "/sessions",
        json={"platform": "youtube", "mode": "auto", "planned_duration_min": 30},
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 7})
    client.post(f"/sessions/{sid}/start")
    code = client.post(
        "/shortlinks",
        json={"product_id": "NH1", "session_id": sid, "target_url": "https://shop.example/nh"},
    ).json()["code"]

    for i in range(4):
        client.get(
            f"/r/{code}",
            follow_redirects=False,
            headers={"user-agent": f"Mozilla/5.0 (Linux; Android 13; Khach-{i}) Mobile"},
        )
    for i in range(3):
        client.get(
            f"/r/{code}",
            follow_redirects=False,
            headers={"user-agent": f"python-urllib/3.12 bot-{i}"},
        )

    clicks_signal = next(
        s for s in client.get(f"/sessions/{sid}/signals").json()["signals"] if s["name"] == "clicks"
    )
    tong_quan = client.get(f"/sessions/{sid}/bao-cao").json()["tong_quan"]

    assert tong_quan["luot_nhap_hop_le"] == 4
    assert tong_quan["luot_nhap_tho"] == 7
    assert clicks_signal["detail"].startswith("4 ")
    assert "7" in clicks_signal["secondary"]
