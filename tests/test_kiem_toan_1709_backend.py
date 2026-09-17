"""Kiểm toán 17/09/2026 — gói B (backend): hai sửa lỗi đi qua API thật.

B1 · HDSD giới hạn #8: phiên ĐÃ tạo link đo mà chưa ai bấm bị ``/signals`` báo
"không có link đo". Nhánh 0 dòng click của ``core.signals`` không biết số
link; nay route đếm ``store.count_shortlinks`` và truyền vào. Ba sự thật khác
nhau phải được nói khác nhau: chưa tạo link (missing), có link chưa ai bấm
(degraded — số 0 là số đo thật nhưng chưa đủ để so khối BẬT với khối TẮT, xem
sự cố 10/09 "nhận vơ năng lực" trong docs/incident-log.md), có lượt bấm
(chấm theo nhấp hợp lệ như cũ). ``/bao-cao`` phải nói cùng một sự thật.
Phản biện: phiên phân tích video ngoài (``analysis_only``) luôn THIẾU với lý do
cấu trúc — không bao giờ "chưa tạo link đo", kể cả khi có link gắn sau.

B3 · ``POST /sessions`` không có tiêu đề: trước đây lưu ``title=None`` và mọi ô
chọn phiên chỉ in UUID. Nay máy chủ đặt ``"Live dd/mm HH:MM · <Nền tảng> · <N>
phút"`` theo giờ Việt Nam — và tên ấy KHÔNG BAO GIỜ được khớp dấu vết phiên mô
phỏng của migration 0009 (một phiên thật bị backfill thành demo sẽ âm thầm
biến mất khỏi kết quả).

(B2 — tham số bình luận Facebook ``live_filter=no_filter`` +
``order=chronological`` — được khoá trong ``tests/test_facebook_readiness.py``
ngay cạnh các test vòng poll mà nó thuộc về.)
"""

from __future__ import annotations

import re
import typing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api import service
from livelift.api.main import create_app
from livelift.api.routes.demo import VANG_TITLE_PREFIX
from livelift.api.routes.sessions import TEN_NEN_TANG, ten_phien_mac_dinh
from livelift.api.schemas import Platform
from livelift.api.store import InMemoryStore

MIGRATION_0009 = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "livelift"
    / "migrations"
    / "0009_is_demo.up.sql"
)


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    with TestClient(app) as c:
        yield c


def _clicks(client, sid: str) -> dict:
    return next(
        s for s in client.get(f"/sessions/{sid}/signals").json()["signals"] if s["name"] == "clicks"
    )


def _cap(client, sid: str, prefix: str) -> dict:
    return next(
        c
        for c in client.get(f"/sessions/{sid}/signals").json()["capabilities"]
        if c["name"].startswith(prefix)
    )


def _phien_dang_chay(client, title: str | None = "phiên kiểm toán") -> str:
    body: dict = {"platform": "youtube", "mode": "auto", "planned_duration_min": 30}
    if title is not None:
        body["title"] = title
    sid = client.post("/sessions", json=body).json()["session_id"]
    client.post(f"/sessions/{sid}/schedule", json={"seed": 11})
    client.post(f"/sessions/{sid}/start")
    return sid


def _tao_link(client, sid: str | None, pid: str = "KT1") -> str:
    client.post(
        "/products",
        json={"product_id": pid, "name": "Son môi", "cost": 1, "price": 2, "stock": 5},
    )
    res = client.post(
        "/shortlinks",
        json={"product_id": pid, "session_id": sid, "target_url": "https://shop.example/son"},
    )
    assert res.status_code == 200, res.text
    return res.json()["code"]


# ---------------------------------------------------------------------------
# B1 — link đo: "chưa tạo" ≠ "có link, chưa ai bấm"
# ---------------------------------------------------------------------------


def test_signals_session_without_link_says_no_link_was_created(client):
    sid = _phien_dang_chay(client)
    clicks = _clicks(client, sid)
    assert clicks["status"] == "missing"
    assert clicks["detail"].startswith("chưa tạo link đo")
    assert _cap(client, sid, "thí nghiệm")["status"] == "missing"


def test_signals_link_created_but_unclicked_is_not_reported_as_no_link(client):
    """Đúng kịch bản giới hạn #8: link tạo qua POST /shortlinks, chưa ai bấm."""
    sid = _phien_dang_chay(client)
    _tao_link(client, sid)
    _tao_link(client, sid)

    clicks = _clicks(client, sid)
    assert clicks["status"] == "degraded"
    assert "đã tạo 2 link đo" in clicks["detail"]
    assert "chưa ai bấm" in clicks["detail"]
    assert "không có link" not in clicks["detail"]
    assert "chưa tạo" not in clicks["detail"]
    assert clicks["secondary"] is None
    # Có ống dẫn không phải có tín hiệu: không năng lực nào được "đủ tín hiệu"
    # nhờ một tử số rỗng (sự cố 10/09 "nhận vơ năng lực").
    for prefix in ("tỷ lệ nhấp", "thí nghiệm"):
        cap = _cap(client, sid, prefix)
        assert cap["status"] != "ok", prefix
        assert cap["reason"] != "đủ tín hiệu", prefix


def test_signals_only_count_links_of_this_session(client):
    """Link của phiên KHÁC hay link không gắn phiên không được tính cho phiên này."""
    sid = _phien_dang_chay(client)
    khac = _phien_dang_chay(client, "phiên khác")
    _tao_link(client, khac)
    _tao_link(client, None)

    clicks = _clicks(client, sid)
    assert clicks["status"] == "missing"
    assert clicks["detail"].startswith("chưa tạo link đo")
    assert "đã tạo 1 link đo" in _clicks(client, khac)["detail"]


def test_first_real_click_moves_the_signal_off_the_no_click_branch(client):
    sid = _phien_dang_chay(client)
    code = _tao_link(client, sid)
    client.get(
        f"/r/{code}",
        follow_redirects=False,
        headers={"user-agent": "Mozilla/5.0 (Linux; Android 13; Khach-1) Mobile"},
    )
    clicks = _clicks(client, sid)
    assert "chưa ai bấm" not in clicks["detail"]
    assert clicks["detail"].startswith("1 ")


def test_bao_cao_agrees_with_signals_on_links_without_clicks(client):
    """Hai màn hình, một sự thật: có link chưa ai bấm thì ô báo cáo là SỐ 0 kèm
    lý do (phép đo), còn không có link thì là THIẾU (None) — không tráo nhau."""
    co_link = _phien_dang_chay(client)
    _tao_link(client, co_link)
    tq = client.get(f"/sessions/{co_link}/bao-cao").json()["tong_quan"]
    assert tq["luot_nhap_hop_le"] == 0
    assert tq["luot_nhap_tho"] == 0
    assert tq["thieu"]["luot_nhap"] == _clicks(client, co_link)["detail"]
    assert "chưa ai bấm" in tq["thieu"]["luot_nhap"]

    khong_link = _phien_dang_chay(client, "phiên không link")
    tq = client.get(f"/sessions/{khong_link}/bao-cao").json()["tong_quan"]
    assert tq["luot_nhap_hop_le"] is None
    assert tq["luot_nhap_tho"] is None
    assert tq["thieu"]["luot_nhap"].startswith("chưa tạo link đo")


# ---------------------------------------------------------------------------
# B1 (phản biện) — video ngoài: thiếu lượt bấm do CẤU TRÚC, không do quên
# ---------------------------------------------------------------------------


@pytest.fixture
def kho_va_client():
    store = InMemoryStore()
    app = create_app(store=store)
    with TestClient(app) as c:
        yield store, c


def _phien_video_ngoai(store: InMemoryStore) -> str:
    """Đúng hình dạng ``routes/replays.py`` lưu: replay, ended, analysis_only,
    không lịch gán. Dựng thẳng vào kho để khỏi giả lập yt-dlp."""
    now = service.now_utc()
    sid = service.new_id()
    store.create_session(
        {
            "session_id": sid,
            "platform": "replay",
            "title": "Phân tích: live của shop khác",
            "mode": "auto",
            "status": "ended",
            "planned_duration_min": 20,
            "host_id": None,
            "start_ts": None,
            "end_ts": None,
            "design": None,
            "created_at": now,
        }
    )
    store.update_session(
        sid,
        {
            "start_ts": now - timedelta(minutes=20),
            "end_ts": now,
            "design": {"analysis_only": True, "source_url": "https://youtu.be/x"},
        },
    )
    return sid


@pytest.mark.parametrize("so_link", [0, 1])
def test_external_video_never_says_create_a_link(kho_va_client, so_link):
    """Phiên phân tích replay của người khác: /signals và /bao-cao nói cùng một
    lý do cấu trúc, dù có gắn link vào phiên sau đó (POST /shortlinks không
    kiểm phiên) hay không."""
    store, client = kho_va_client
    sid = _phien_video_ngoai(store)
    for i in range(so_link):
        _tao_link(client, sid, pid=f"VN{i}")

    clicks = _clicks(client, sid)
    assert clicks["status"] == "missing"
    assert clicks["detail"].startswith("video ngoài")
    for cam in ("chưa tạo", "đã tạo", "chưa ai bấm", "bình luận ghim"):
        assert cam not in clicks["detail"], cam
    assert _cap(client, sid, "tỷ lệ nhấp")["status"] == "missing"

    tq = client.get(f"/sessions/{sid}/bao-cao").json()["tong_quan"]
    # Không phải "số 0 đo được": ô là THIẾU (None) kèm đúng câu của ma trận.
    assert tq["luot_nhap_hop_le"] is None
    assert tq["luot_nhap_tho"] is None
    assert tq["thieu"]["luot_nhap"] == clicks["detail"]


# ---------------------------------------------------------------------------
# B3 — tên phiên mặc định do máy chủ đặt
# ---------------------------------------------------------------------------


def _dong_ho(monkeypatch, when: datetime) -> None:
    monkeypatch.setattr(service, "now_utc", lambda: when)


def test_session_without_title_gets_readable_vietnam_time_name(client, monkeypatch):
    _dong_ho(monkeypatch, datetime(2026, 9, 17, 0, 38, 12, tzinfo=UTC))
    res = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 30}
    )
    assert res.status_code == 200, res.text
    out = res.json()
    # 00:38 UTC = 07:38 giờ Việt Nam.
    assert out["title"] == "Live 17/09 07:38 · YouTube · 30 phút"
    # Tên được LƯU, không chỉ trả về một lần.
    assert client.get(f"/sessions/{out['session_id']}").json()["title"] == out["title"]
    assert {s["session_id"]: s["title"] for s in client.get("/sessions").json()}[
        out["session_id"]
    ] == out["title"]


def test_default_name_uses_the_vietnam_date_across_midnight_utc(client, monkeypatch):
    # 17:30 UTC ngày 16 = 00:30 ngày 17 ở Việt Nam: ngày trong tên phải là 17/09.
    _dong_ho(monkeypatch, datetime(2026, 9, 16, 17, 30, tzinfo=UTC))
    out = client.post(
        "/sessions",
        json={"platform": "facebook", "title": None, "planned_duration_min": 90},
    ).json()
    assert out["title"] == "Live 17/09 00:30 · Facebook · 90 phút"


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_title_is_treated_as_missing(client, monkeypatch, blank):
    _dong_ho(monkeypatch, datetime(2026, 9, 17, 12, 5, tzinfo=UTC))
    out = client.post(
        "/sessions", json={"platform": "tiktok", "title": blank, "planned_duration_min": 45}
    ).json()
    assert out["title"] == "Live 17/09 19:05 · TikTok · 45 phút"


def test_explicit_title_is_kept_verbatim(client):
    out = client.post(
        "/sessions",
        json={"platform": "youtube", "title": "Xả kho thứ Sáu", "planned_duration_min": 60},
    ).json()
    assert out["title"] == "Xả kho thứ Sáu"


def test_default_name_matches_asia_ho_chi_minh_zone():
    """Múi +7 cố định phải trùng múi IANA Asia/Ho_Chi_Minh trên cả năm."""
    zoneinfo = pytest.importorskip("zoneinfo")
    try:
        hcm = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")
    except zoneinfo.ZoneInfoNotFoundError:
        pytest.skip("máy này không có dữ liệu múi giờ IANA (tzdata)")
    for month in range(1, 13):
        for hour in (0, 16, 17, 23):
            when = datetime(2026, month, 28, hour, 59, tzinfo=UTC)
            local = when.astimezone(hcm)
            assert ten_phien_mac_dinh("youtube", 30, when) == (
                f"Live {local:%d/%m %H:%M} · YouTube · 30 phút"
            )


def _like_to_regex(pattern: str) -> re.Pattern[str]:
    out = "".join(".*" if ch == "%" else "." if ch == "_" else re.escape(ch) for ch in pattern)
    return re.compile(rf"^{out}$", re.DOTALL)


def test_default_name_never_matches_the_demo_backfill_of_migration_0009():
    """Tên mặc định không được làm phiên thật trông như dữ liệu mẫu.

    Mẫu LIKE được đọc từ CHÍNH file migration, để test đi theo nếu mẫu đổi.
    Thử mọi nền tảng phiên hợp lệ, cả nền tảng lạ, nhiều thời lượng.
    """
    sql = MIGRATION_0009.read_text(encoding="utf-8")
    like_patterns = re.findall(r"title\s+LIKE\s+'([^']*)'", sql)
    assert like_patterns, "không tìm thấy mẫu title LIKE trong migration 0009"
    regexes = [_like_to_regex(p) for p in like_patterns]

    platforms = [*typing.get_args(Platform), "shopee", "nen-tang-la"]
    when = datetime(2026, 9, 17, 0, 38, tzinfo=UTC)
    for platform in platforms:
        for minutes in (5, 30, 480):
            ten = ten_phien_mac_dinh(platform, minutes, when)
            assert ten.startswith("Live ")
            for rx in regexes:
                assert not rx.match(ten), (ten, rx.pattern)
            assert not ten.startswith(VANG_TITLE_PREFIX)


def test_every_session_platform_has_a_pretty_name():
    """Không nền tảng phiên hợp lệ nào lộ mã thô ("youtube") trong tên."""
    for platform in typing.get_args(Platform):
        assert platform in TEN_NEN_TANG, platform
        assert TEN_NEN_TANG[platform] != platform


def test_default_name_does_not_change_the_demo_flag(client):
    """is_demo chỉ do cổng token quyết định — tên mặc định không đổi nó."""
    co_ten = client.post(
        "/sessions", json={"platform": "replay", "title": "A", "planned_duration_min": 30}
    ).json()
    khong_ten = client.post(
        "/sessions", json={"platform": "replay", "planned_duration_min": 30}
    ).json()
    assert khong_ten["title"].startswith("Live ")
    assert khong_ten.get("is_demo") == co_ten.get("is_demo")
