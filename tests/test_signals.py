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
    # Sửa 17/09/2026: bản cũ KHÔNG truyền số link mà vẫn đặt tên "no shortlinks"
    # — đúng lỗi HDSD giới hạn #8 (0 lượt bấm bị đọc là "không có link đo").
    # Nay phải khai số link thật: 0 link mới là "chưa tạo link đo".
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
        n_shortlinks=0,
    )
    assert cap(cov, "tỷ lệ nhấp").status == "missing"
    clicks = next(s for s in cov.signals if s.name == "clicks")
    assert clicks.status == "missing"
    assert "chưa tạo link đo" in clicks.detail


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
        n_shortlinks=0,
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


# ---------------------------------------------------------------------------
# Link đo: "chưa tạo link" khác "có link, chưa ai bấm" (kiểm toán 17/09/2026)
# ---------------------------------------------------------------------------
#
# HDSD giới hạn #8: phiên đã tạo link qua POST /shortlinks nhưng chưa ai bấm bị
# `/signals` báo "không có link đo". Nhánh 0 dòng click không biết số link.


def _cov_links(n_shortlinks, n_clicks_valid=0, n_clicks_raw=0):
    return assess(
        has_schedule=True,
        n_ticks=60,
        n_ticks_with_viewers=60,
        tick_coverage_share=1.0,
        n_comments=10,
        n_clicks_valid=n_clicks_valid,
        n_clicks_raw=n_clicks_raw,
        n_orders=0,
        n_reactions=0,
        n_shortlinks=n_shortlinks,
    )


def test_links_but_no_clicks_is_degraded_not_missing_and_never_ok():
    """Có link đo, 0 lượt bấm ⇒ ``degraded``.

    Không ``missing``: link có thật, đường chuyển hướng ghi mọi cú bấm, số 0 là
    số đo. Không ``ok``: sự cố 10/09 "nhận vơ năng lực" — hạ tầng có mà tử số
    rỗng thì "thí nghiệm nhân quả" KHÔNG được nói "đủ tín hiệu".
    """
    cov = _cov_links(n_shortlinks=3)
    clicks = sig(cov, "clicks")
    assert clicks.status == "degraded"
    assert "3 link đo" in clicks.detail
    assert "chưa ai bấm" in clicks.detail
    assert "chưa tạo" not in clicks.detail
    assert "không có link" not in clicks.detail
    assert clicks.secondary is None, "0 dòng click thì không có số thô nào để kèm"
    for name in ("tỷ lệ nhấp", "thí nghiệm"):
        assert cap(cov, name).status == "degraded", name
        assert cap(cov, name).reason != "đủ tín hiệu"


def test_zero_links_is_missing_with_the_create_link_wording():
    cov = _cov_links(n_shortlinks=0)
    clicks = sig(cov, "clicks")
    assert clicks.status == "missing"
    assert clicks.detail.startswith("chưa tạo link đo")
    assert cap(cov, "thí nghiệm").status == "missing"


def test_uncounted_links_claim_neither_case():
    """Caller không đếm link (None): không được nói "chưa tạo" (có thể sai)
    cũng không được nói "đã tạo N link" (bịa số)."""
    clicks = sig(_cov_links(n_shortlinks=None), "clicks")
    assert clicks.status == "missing"
    assert "chưa tạo" not in clicks.detail
    assert "đã tạo" not in clicks.detail


def test_link_count_never_changes_grading_once_click_rows_exist():
    """Số link chỉ quyết định nhánh 0 dòng click; có click thì chấm theo click
    HỢP LỆ như cũ (§4.1) — số link không được nâng hay hạ trạng thái."""
    for n_links in (None, 0, 5):
        assert sig(_cov_links(n_links, 20, 20), "clicks").status == "ok"
        assert sig(_cov_links(n_links, 0, 9), "clicks").status == "missing"


# ---------------------------------------------------------------------------
# Video ngoài (analysis_only): thiếu lượt bấm là do CẤU TRÚC, không do quên
# ---------------------------------------------------------------------------
#
# Phản biện 17/09/2026: sau khi tách "chưa tạo link" khỏi "có link, chưa ai
# bấm", phiên phân tích replay của người khác bị báo "chưa tạo link đo cho
# phiên này" — như thể người bán quên làm. Gắn thêm link qua POST /shortlinks
# (route không kiểm phiên) còn đẩy ô sang degraded kèm lời khuyên "kiểm tra
# bình luận ghim" trên một video không ai bấm được nữa.


def _cov_video_ngoai(n_shortlinks, n_clicks_valid=0, n_clicks_raw=0):
    return assess(
        has_schedule=False,
        n_ticks=141,
        n_ticks_with_viewers=0,
        tick_coverage_share=1.0,
        n_comments=500,
        n_clicks_valid=n_clicks_valid,
        n_clicks_raw=n_clicks_raw,
        n_orders=0,
        n_reactions=0,
        platform="replay",
        analysis_only=True,
        n_shortlinks=n_shortlinks,
    )


@pytest.mark.parametrize("n_links", [None, 0, 1, 3])
def test_external_video_clicks_are_missing_for_a_structural_reason(n_links):
    """Mọi số link (kể cả không đếm) cho cùng một sự thật: video ngoài, đã xong."""
    cov = _cov_video_ngoai(n_links)
    clicks = sig(cov, "clicks")
    assert clicks.status == "missing"
    assert clicks.detail.startswith("video ngoài")
    assert "không có lượt bấm để đếm" in clicks.detail
    # Không câu nào đổ cho người bán hay bảo họ đi làm một việc vô ích.
    for cam in ("chưa tạo", "đã tạo", "chưa ai bấm", "bình luận ghim", "chưa ghi nhận"):
        assert cam not in clicks.detail, (n_links, cam)
    assert clicks.secondary is None
    # Năng lực nhấp không được rời mức missing nhờ một link gắn sau.
    for name in ("tỷ lệ nhấp", "thí nghiệm"):
        assert cap(cov, name).status == "missing", (n_links, name)


def test_external_video_detail_does_not_depend_on_the_link_count():
    details = {sig(_cov_video_ngoai(n), "clicks").detail for n in (None, 0, 1, 7)}
    assert len(details) == 1, details


def test_external_video_with_click_rows_stays_missing_but_names_the_rows():
    """Link gắn vào phiên phân tích SAU buổi phát rồi có người bấm: dòng click
    có thật nên phải được NÊU (không giấu, số thô vẫn kèm nhãn), nhưng không
    phải lượt bấm của khán giả video — không được chấm ok như tử số chính."""
    cov = _cov_video_ngoai(n_shortlinks=1, n_clicks_valid=4, n_clicks_raw=5)
    clicks = sig(cov, "clicks")
    assert clicks.status == "missing"
    assert clicks.detail.startswith("video ngoài")
    assert "5 lượt bấm" in clicks.detail
    assert "không phải khán giả" in clicks.detail
    assert "HỢP LỆ qua link đo" not in clicks.detail
    assert clicks.secondary is not None
    assert "5 lượt nhấp đã ghi" in clicks.secondary
    assert cap(cov, "tỷ lệ nhấp").status == "missing"


def test_own_session_without_analysis_flag_keeps_the_create_link_wording():
    """Chỉ cờ analysis_only đổi câu; phiên của mình vẫn được nhắc tạo link."""
    cov = assess(
        has_schedule=True,
        n_ticks=60,
        n_ticks_with_viewers=60,
        tick_coverage_share=1.0,
        n_comments=10,
        n_clicks_valid=0,
        n_clicks_raw=0,
        n_orders=0,
        n_reactions=0,
        platform="youtube",
        analysis_only=False,
        n_shortlinks=0,
    )
    assert sig(cov, "clicks").detail.startswith("chưa tạo link đo")
