"""Executable user journeys — the product's real stories, end to end.

Not unit tests: each test walks a COMPLETE story the way a real person would,
through the public API only, with realistic Vietnamese comment traffic
(PII-laden, teencode, mixed intents) and realistic timing structure. If a
story breaks anywhere along its path, the product is broken for that person
regardless of how green the unit tests are — this file is the harness's
"hình dung người dùng sử dụng thực tế" made executable.

Journeys:
1. Tổ vận hành Live Lab chạy một phiên thí nghiệm trọn vẹn.
2. Người dẫn (host) nhìn màn hình của mình suốt phiên — và không bao giờ
   thấy thứ gì tiết lộ nhánh thí nghiệm.
3. Nhà phân tích mở kết quả gộp sau nhiều phiên.
4. Người mới dán một "video" không có tín hiệu gì ngoài bình luận.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore

# Realistic comment traffic: (text, expected_pii). Teencode, diacritics loss,
# PII, mixed intents — what a real Vietnamese shopping live actually looks like.
TRAFFIC = [
    ("chào shop buổi tối", False),
    ("giá bao nhiêu vậy shop", False),
    ("0901234567 ship về Gò Vấp giúp em", True),
    ("size M còn ko ạ", False),
    ("dat qua giam di shop", False),
    ("chot 1 don mau den nha", False),
    ("ship cod đc ko, em ở 12 Nguyễn Trãi", True),
    ("sđt em là không chín không tám bảy sáu năm bốn ba hai", True),
    ("phi ship ve tinh bao nhieu", False),
    ("lấy 2 hộp nha, mail em hoa123@gmail.com", True),
    ("❤❤❤ hóng sale", False),
    ("mắc hơn shopee rồi shop ơi", False),
]


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


def _setup_live_session(client, mode="auto", minutes=60):
    for i, (name, price) in enumerate(
        [("Áo thun nam", 199000), ("Bình giữ nhiệt", 95000), ("Khăn choàng", 120000)]
    ):
        r = client.post(
            "/products",
            json={
                "product_id": f"J{i}",
                "name": name,
                "cost": price // 2,
                "price": price,
                "stock": 40,
            },
        )
        assert r.status_code == 200
    sid = client.post(
        "/sessions",
        json={
            "platform": "youtube",
            "mode": mode,
            "planned_duration_min": minutes,
            "title": "Phiên hành trình người dùng",
        },
    ).json()["session_id"]
    sched = client.post(f"/sessions/{sid}/schedule", json={"seed": 99}).json()
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    return sid, sched


def test_journey_operator_runs_a_full_experiment_session(client):
    """Tổ vận hành: sản phẩm → phiên → bốc lịch → phát sóng → traffic thật
    → thẻ hành động → can thiệp → kết thúc → QC-grade dữ liệu sạch."""
    sid, sched = _setup_live_session(client)

    # traffic đổ vào như phiên thật
    stored_texts = []
    for i, (text, _) in enumerate(TRAFFIC):
        client.post(f"/sessions/{sid}/ticks", json={"viewers": 60 + 5 * i})
        r = client.post(f"/sessions/{sid}/comments", json={"text": text})
        assert r.status_code == 200
        stored_texts.append(r.json()["text"])

    # KHÔNG một mảnh PII nào được sống sót trong dữ liệu lưu
    joined = " ".join(stored_texts)
    for fragment in (
        "0901234567",
        "0901",
        "Nguyễn Trãi",
        "hoa123@gmail.com",
        "không chín không tám",
    ):
        assert fragment not in joined, f"PII lọt: {fragment!r}"
    n_scrubbed = sum(1 for t in stored_texts if "[" in t)
    expected_pii = sum(1 for _, has in TRAFFIC if has)
    assert n_scrubbed >= expected_pii

    # link đo click — định nghĩa vận hành của biến kết quả
    code = client.post(
        "/shortlinks",
        json={"product_id": "J0", "session_id": sid, "target_url": "https://shop.example/ao-thun"},
    ).json()["code"]
    for _ in range(4):
        r = client.get(f"/r/{code}", follow_redirects=False)
        assert r.status_code == 302

    # trạng thái operator có thẻ hành động với đủ đồ nghề khoa học
    state = client.get(f"/sessions/{sid}/state?role=operator").json()
    assert state["current_block"] is not None
    assert len(state["cards"]) >= 1
    for card in state["cards"]:
        assert card["source"] == "forecast"
        assert card.get("ci_low") is None  # E2-04: forecast không mang khoảng

    # can thiệp tay đúng lý do được phép
    r = client.post(
        f"/sessions/{sid}/actions/override",
        json={"product_id": "J1", "reason": "hết hàng"},
    )
    assert r.status_code == 200

    # kết thúc và soát chất lượng cấp câu chuyện
    client.post(f"/sessions/{sid}/end")
    report = client.get(f"/sessions/{sid}/report").json()
    assert report["source"] == "experiment"
    assert report["compliance"]["override_count"] == 1

    signals = client.get(f"/sessions/{sid}/signals").json()
    by_name = {s["name"]: s["status"] for s in signals["signals"]}
    assert by_name["schedule"] == "ok"
    assert by_name["comments"] == "ok"
    assert by_name["clicks"] == "ok"

    # nhật ký can thiệp đầy đủ cho kiểm toán
    from livelift.core.quality import check_intervention_log

    # (qua API không lộ log thô — kiểm qua compliance đã đủ ở mức hành trình;
    #  check chi tiết nằm ở test_quality.py)
    assert check_intervention_log([]).passed  # sanity import


def test_journey_host_screen_never_leaks_through_a_whole_session(client):
    """Người dẫn nhìn màn hình CỦA HỌ nhiều lần suốt phiên: trước khi phát,
    trong từng khối, sau khi kết thúc — payload không bao giờ chứa thứ gì
    về BẬT/TẮT hay ranh giới khối."""
    sid, sched = _setup_live_session(client)
    forbidden = (
        "assignment",
        "block",
        "seconds_remaining",
        "phase",
        "propensity",
        "seed",
        "ON",
        "OFF",
        "cards",
    )

    for moment in range(6):  # nhìn đi nhìn lại như người thật
        r = client.get(f"/sessions/{sid}/state?role=host")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) <= {"pinned_product", "price", "stock", "elapsed_s"}
        raw = r.text
        for word in forbidden:
            assert f'"{word}"' not in raw, f"màn hình host lộ {word!r} ở lần nhìn {moment}"

    client.post(f"/sessions/{sid}/end")
    r = client.get(f"/sessions/{sid}/state?role=host")
    assert set(r.json().keys()) <= {"pinned_product", "price", "stock", "elapsed_s"}


def test_journey_analyst_reads_pooled_results_only_when_defensible(client):
    """Nhà phân tích mở /experiment/summary khi chưa đủ dữ liệu: hệ thống
    phải NÓI chưa đủ, không bịa số."""
    summary = client.get("/experiment/summary").json()
    assert summary["n_sessions"] == 0
    assert summary["estimate"] is None
    assert summary["message"] is not None  # lời giải thích tiếng Việt

    # một phiên duy nhất kết thúc vẫn chưa đủ (cần >= 2 phiên)
    sid, _ = _setup_live_session(client)
    client.post(f"/sessions/{sid}/ticks", json={"viewers": 80})
    client.post(f"/sessions/{sid}/end")
    summary = client.get("/experiment/summary").json()
    assert summary["estimate"] is None
    assert summary["message"] is not None


def test_journey_newcomer_analyzes_comment_only_source(client):
    """Người mới có mỗi bình luận (không lịch gán, không click): hệ thống
    trả đúng ranh giới — radar được, thí nghiệm thì không, và không có
    con số nhân quả nào xuất hiện."""
    # phiên "phân tích" tối thiểu: tạo qua store trực tiếp như replay pipeline
    sid = client.post(
        "/sessions",
        json={
            "platform": "replay",
            "mode": "auto",
            "planned_duration_min": 30,
            "title": "Phân tích: video ngoài",
        },
    ).json()["session_id"]
    # không schedule, không start -> không có block nào

    report = client.get(f"/sessions/{sid}/report").json()
    assert report["n_blocks"] == 0
    assert report["diff_in_means"] is None
    assert "quan sát" in report["label"]

    signals = client.get(f"/sessions/{sid}/signals").json()
    caps = {c["name"]: c["status"] for c in signals["capabilities"]}
    exp = next(v for k, v in caps.items() if "thí nghiệm" in k)
    assert exp == "missing"
