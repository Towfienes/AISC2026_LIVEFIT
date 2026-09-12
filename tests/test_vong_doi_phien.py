"""Vòng đời phiên: đóng được, đếm đúng, và chỉ mời thao tác khi thao tác được.

Ba chốt chặn cho ba sự cố tìm ra ngày 11/09/2026 bằng cách đóng vai người dùng
thật (`docs/benchmarks/kiem-chung-van-hanh.md`), sửa ngày 12/09 (gói C):

* **§3.3** — phiên quan sát chưa từng phát sóng KHÔNG đóng lại được: `POST /end`
  trả 409 và phiên kẹt ở `planned` vĩnh viễn. Đường vòng duy nhất là dựng cả bộ
  máy thí nghiệm rồi bấm phát sóng, chỉ để đóng một dòng.
* **§2.4c** — `/experiment/summary` gộp MỌI phiên đã kết thúc có lịch gán, không
  phân biệt thật/chạy thử. Hai phiên dò lỗi sống 1 giây đã lọt vĩnh viễn vào kết
  quả gộp, không có nút gỡ.
* **§1.5** — `GET /state` trên phiên phân tích ĐÃ KẾT THÚC vẫn trả ba thẻ mời
  "Ghim ..." những sản phẩm demo không liên quan gì tới video.

Tệp này canh hợp đồng ở tầng API và tầng hàm thuần. Hành trình người dùng đầu-
cuối tương ứng nằm ở `tests/test_case_nguoi_dung_that.py` (case 1, 4, 5).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.cards import pin_cards_blocked_reason
from livelift.api.main import create_app
from livelift.api.routes.reports import _excluded_session_counts, _in_analysis_sample
from livelift.api.store import InMemoryStore


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def client(store):
    app = create_app(store=store)
    with TestClient(app) as c:
        yield c


def _session(client, **extra) -> str:
    body = {"platform": "tiktok", "mode": "suggest", "planned_duration_min": 15}
    body.update(extra)
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


# ===========================================================================
# §3.3 — một phiên chưa từng phát sóng vẫn phải đóng được
# ===========================================================================


def test_end_on_a_never_aired_session_closes_it_as_cancelled(client):
    """`POST /end` là nút người dùng đã bấm — nó phải LÀM ĐƯỢC việc, và ghi
    đúng sự thật: phiên này chưa từng lên sóng nên nó `cancelled`, không
    `ended`."""
    sid = _session(client, title="Nhập tay khi live TikTok")
    assert (
        client.post(f"/sessions/{sid}/comments", json={"text": "còn size M không shop"}).status_code
        == 200
    )

    r = client.post(f"/sessions/{sid}/end")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "cancelled"
    assert body["start_ts"] is None, "phiên chưa phát sóng thì không được sinh mốc bắt đầu"
    assert body["end_ts"] is not None, "đóng lúc nào phải ghi lại"


def test_cancel_endpoint_is_explicit_and_idempotent(client):
    sid = _session(client)
    first = client.post(f"/sessions/{sid}/cancel")
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "cancelled"

    second = client.post(f"/sessions/{sid}/cancel")
    assert second.status_code == 200, "huỷ một phiên đã huỷ là việc đã xong, không phải lỗi"
    assert second.json()["end_ts"] == first.json()["end_ts"], "không được dời mốc đóng"


def test_a_cancelled_session_can_never_be_reopened(client):
    sid = _session(client, platform="youtube", mode="auto", planned_duration_min=30)
    assert client.post(f"/sessions/{sid}/schedule", json={"seed": 5}).status_code == 200
    assert client.post(f"/sessions/{sid}/cancel").status_code == 200

    start = client.post(f"/sessions/{sid}/start")
    assert start.status_code == 409
    assert "đã huỷ" in start.json()["detail"]
    assert client.post(f"/sessions/{sid}/schedule", json={"seed": 6}).status_code == 409
    assert client.get(f"/sessions/{sid}").json()["start_ts"] is None


def test_a_broadcast_that_happened_cannot_be_cancelled_away(client):
    """Huỷ chỉ dành cho phiên CHƯA phát. Một buổi phát đã diễn ra là sự thật —
    xoá nó bằng một nút bấm là cách nhanh nhất làm bẩn mẫu phân tích."""
    sid = _session(client, platform="youtube", mode="auto", planned_duration_min=30)
    client.post(f"/sessions/{sid}/schedule", json={"seed": 5})
    assert client.post(f"/sessions/{sid}/start").status_code == 200

    live = client.post(f"/sessions/{sid}/cancel")
    assert live.status_code == 409
    assert "end" in live.json()["detail"], "phải chỉ đúng đường thay thế"

    assert client.post(f"/sessions/{sid}/end").json()["status"] == "ended"
    ended = client.post(f"/sessions/{sid}/cancel")
    assert ended.status_code == 409
    again = client.post(f"/sessions/{sid}/end")
    assert again.status_code == 409
    assert "đã kết thúc" in again.json()["detail"]


def test_closing_an_observation_session_does_not_turn_it_into_an_experiment(client):
    sid = _session(client)
    client.post(f"/sessions/{sid}/comments", json={"text": "chốt 1 cái màu đen nha chị"})
    client.post(f"/sessions/{sid}/end")

    report = client.get(f"/sessions/{sid}/report").json()
    assert report["diff_in_means"] is None
    assert report["n_blocks"] == 0
    assert client.get("/experiment/summary").json()["n_sessions"] == 0


# ===========================================================================
# §2.4c — phiên chạy thử không được gộp vào kết quả
# ===========================================================================


def _row(status: str, **extra) -> dict:
    row = {"session_id": "s", "status": status, "design": None}
    row.update(extra)
    return row


def test_analysis_sample_rule_is_decidable_without_looking_at_any_outcome():
    assert _in_analysis_sample(_row("ended")) is True
    assert _in_analysis_sample(_row("ended", dry_run=True)) is False
    assert _in_analysis_sample(_row("ended", design={"analysis_only": True})) is False
    for status in ("planned", "scheduled", "live", "cancelled"):
        assert _in_analysis_sample(_row(status)) is False


def test_every_exclusion_is_counted_and_named():
    """Một phiên bị loại mà không ai thấy thì không phân biệt được với một
    phiên chưa từng tồn tại."""
    counts = _excluded_session_counts(
        [
            _row("ended"),
            _row("ended", dry_run=True),
            _row("ended", design={"analysis_only": True}),
            _row("cancelled"),
            _row("live"),
        ]
    )
    assert sum(counts.values()) == 4
    labels = " | ".join(counts)
    assert "CHẠY THỬ" in labels
    assert "quan sát" in labels
    assert "huỷ" in labels


def test_a_dry_run_session_is_declared_at_creation_and_stays_out(client):
    sid = _session(client, platform="youtube", mode="auto", planned_duration_min=30, dry_run=True)
    assert client.get(f"/sessions/{sid}").json()["dry_run"] is True

    client.post(f"/sessions/{sid}/schedule", json={"seed": 5})
    client.post(f"/sessions/{sid}/start")
    client.post(f"/sessions/{sid}/end")

    summary = client.get("/experiment/summary").json()
    assert summary["n_sessions"] == 0
    assert any("CHẠY THỬ" in reason for reason in summary["sessions_excluded"])
    # ...nhưng phiên vẫn xem được riêng: loại khỏi mẫu gộp, không phải xoá.
    assert client.get(f"/sessions/{sid}/report").status_code == 200
    assert client.get(f"/sessions/{sid}/bao-cao").status_code == 200


def test_a_real_session_is_never_silently_left_out(client):
    """Mặc định phải là "tính vào kết quả" — im lặng bỏ một phiên thật ra
    ngoài còn tệ hơn gộp nhầm một phiên thử."""
    sid = _session(client, platform="youtube", mode="auto", planned_duration_min=30)
    assert client.get(f"/sessions/{sid}").json()["dry_run"] is False
    client.post(f"/sessions/{sid}/schedule", json={"seed": 5})
    client.post(f"/sessions/{sid}/start")
    client.post(f"/sessions/{sid}/end")
    summary = client.get("/experiment/summary").json()
    assert not any("CHẠY THỬ" in reason for reason in summary["sessions_excluded"])


def test_the_dry_run_flag_cannot_be_flipped_after_the_fact(store, client):
    """LIÊM CHÍNH (§8.2): cờ này phải là quyết định TRƯỚC phiên.

    Một cột bật/tắt được sau khi đã thấy kết quả không phải quy tắc tiền đăng
    ký — nó là cái nút loại bỏ những phiên có số liệu không vừa ý.
    """
    that = _session(client, platform="youtube", mode="auto", planned_duration_min=30)
    thu = _session(client, platform="youtube", mode="auto", planned_duration_min=30, dry_run=True)

    store.update_session(that, {"dry_run": True})
    store.update_session(thu, {"dry_run": False})
    assert store.get_session(that)["dry_run"] is False
    assert store.get_session(thu)["dry_run"] is True

    # ...và không route nào NHẬN cờ này ngoài lúc tạo phiên.
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    mang_co = {n for n, s in schemas.items() if "dry_run" in (s.get("properties") or {})}
    assert "SessionCreate" in mang_co
    assert mang_co <= {"SessionCreate", "SessionOut", "SessionDetail"}, (
        f"có schema khác nhận cờ chạy thử: {sorted(mang_co)}"
    )


# ===========================================================================
# §1.5 — chỉ mời ghim hàng ở nơi ghim được
# ===========================================================================


def test_pin_cards_are_blocked_exactly_where_pinning_is_impossible():
    assert pin_cards_blocked_reason("live", analysis_only=False) is None
    for status in ("planned", "scheduled", "ended", "cancelled"):
        assert pin_cards_blocked_reason(status, analysis_only=False)
    # phiên phân tích video người khác: kể cả khi trạng thái nói "live"
    assert "người khác" in (pin_cards_blocked_reason("live", analysis_only=True) or "")


def test_card_list_and_execute_refusal_tell_the_same_story(client):
    """Danh sách thẻ rỗng và câu từ chối của `/actions/execute` phải cùng một
    nguồn — nếu không, bàn điều khiển và máy chủ lại kể hai câu chuyện."""
    client.post(
        "/products",
        json={"product_id": "D1", "name": "Bình giữ nhiệt", "cost": 1, "price": 2, "stock": 40},
    )
    sid = _session(client, platform="youtube", mode="auto", planned_duration_min=30)

    state = client.get(f"/sessions/{sid}/state").json()
    assert state["cards"] == [], "phiên chưa phát sóng thì không mời ghim"
    assert state["cards_note"]

    r = client.post(f"/sessions/{sid}/actions/execute", json={})
    assert r.status_code == 409
    assert state["cards_note"] in r.json()["detail"]


def test_a_live_session_still_gets_its_cards(client):
    """Chốt chặn ngược: bản vá không được làm bàn điều khiển câm ở đúng lúc
    nó phải nói."""
    client.post(
        "/products",
        json={"product_id": "D1", "name": "Bình giữ nhiệt", "cost": 1, "price": 2, "stock": 40},
    )
    sid = _session(client, platform="youtube", mode="auto", planned_duration_min=30)
    client.post(f"/sessions/{sid}/schedule", json={"seed": 5})
    client.post(f"/sessions/{sid}/start")

    state = client.get(f"/sessions/{sid}/state").json()
    assert len(state["cards"]) >= 1
    assert state["cards_note"] is None

    client.post(f"/sessions/{sid}/end")
    after = client.get(f"/sessions/{sid}/state").json()
    assert after["cards"] == []
    assert "kết thúc" in after["cards_note"]
