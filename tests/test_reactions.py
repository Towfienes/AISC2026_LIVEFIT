"""Tín hiệu tim/quà/Super Chat (migration 0007): parser, store, API, replay.

SỐ THẬT từ live-fire (đếm 11/09/2026 trên 11 file chat replay của corpus
đa nguồn, mức addChatItemAction): 0 liveChatPaidMessageRenderer (Super Chat),
0 liveChatPaidStickerRenderer, 7 liveChatMembershipItemRenderer (3 buổi),
4 liveChatSponsorshipsGiftPurchaseAnnouncementRenderer (2 buổi),
40 GiftRedemption (đúng 4 lượt mua × 10 quà). Grep chuỗi thô đếm ra 10/8 vì
ticker (`addLiveChatTickerItemAction`) nhúng lại nguyên renderer — parser chỉ
đọc addChatItemAction nên mỗi sự kiện đếm một lần. Shop VN gần như không dùng
Super Chat — vì corpus không có dòng Super Chat thật nào, dòng superchat trong
fixture dựng theo đúng shape renderer công bố của YouTube
(purchaseAmountText.simpleText); các dòng membership/gift/redemption chép theo
shape THẬT đo được trong corpus, đã thay tên/kênh bằng placeholder
(PII-scrubbed).

Hard rule 1: parser không bao giờ đọc trường tác giả — kiểm bằng cách soi
toàn bộ output không chứa tên/kênh nào của fixture.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.routes import replays
from livelift.api.store import InMemoryStore
from livelift.ingest.youtube_replay import (
    DownloadResult,
    parse_live_chat_reaction_line,
    parse_live_chat_reactions_file,
    parse_purchase_amount,
)
from livelift.ingest.youtube_ytdlp import parse_live_chat_reaction_actions

FIXTURE = Path(__file__).parent / "data" / "live_chat_paid_fixture.jsonl"

# Placeholder authors/channels planted in the fixture — none may leak.
AUTHOR_STRINGS = [
    "Nguoi Tang A",
    "Nguoi Tang B",
    "Nguoi Tang C",
    "Nguoi Tang D",
    "Nguoi Nhan E",
    "Nguoi Xem F",
    "UCgiver",
    "UCgetter",
    "UCviewer",
]


@pytest.fixture
def client():
    app = create_app(store=InMemoryStore())
    replays._JOBS.clear()
    with TestClient(app) as c:
        yield c
    replays._JOBS.clear()


# ---------------------------------------------------------------------------
# parse_purchase_amount — chuỗi tiền CÔNG KHAI, không đoán mò
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("50.000 ₫", (50000.0, "₫")),  # VND: dấu chấm là phân tách nghìn
        ("$5.00", (5.0, "$")),  # 2 chữ số cuối sau dấu = phần thập phân
        ("SGD 10.50", (10.5, "SGD")),  # mã tiền đứng trước
        ("¥1,000", (1000.0, "¥")),  # phẩy nghìn
        ("1.234.567 ₫", (1234567.0, "₫")),  # nhiều nhóm nghìn
        ("", (None, None)),
        (None, (None, None)),
        ("miễn phí", (None, None)),  # không có chữ số -> tuyên bố thiếu
    ],
)
def test_parse_purchase_amount(text, expected):
    assert parse_purchase_amount(text) == expected


def test_parse_purchase_amount_never_returns_zero_for_unparseable():
    """Không-bịa-số: chuỗi không đọc được phải ra (None, None), không phải 0."""
    amount, currency = parse_purchase_amount("₫₫₫")
    assert amount is None
    assert currency is None


# ---------------------------------------------------------------------------
# Replay parser (offset-based) trên fixture shape thật
# ---------------------------------------------------------------------------


def test_parse_reactions_file_kinds_amounts_sorted_no_authors():
    reactions = parse_live_chat_reactions_file(FIXTURE)
    # 7 dòng fixture: 4 sự kiện trả tiền; redemption + text + placeholder bị bỏ
    assert [r.kind for r in reactions] == ["superchat", "sticker", "membership", "gift"]
    assert [r.offset_s for r in reactions] == [60.0, 120.0, 180.0, 240.0]  # sorted

    superchat = reactions[0]
    assert superchat.amount == 50000.0
    assert superchat.currency == "₫"
    assert superchat.ext_id == "paid-001"

    sticker = reactions[1]
    assert sticker.amount == 5.0
    assert sticker.currency == "$"

    # membership/gift không mang chuỗi tiền -> None, không phải 0 giả
    assert reactions[2].amount is None
    assert reactions[3].amount is None

    # hard rule 1: không trường tác giả nào rời khỏi parser
    dumped = repr(reactions)
    for name in AUTHOR_STRINGS:
        assert name not in dumped


def test_gift_redemption_is_not_counted_as_a_gift():
    """1 lượt mua quà = nhiều thông báo nhận (đo 4 mua vs 40 nhận trên cùng
    các buổi — đúng 4 × 10 quà) — đếm cả hai là nhân một sự kiện kinh tế lên
    theo số người nhận."""
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    redemption = next(line for line in lines if "GiftRedemption" in line)
    assert parse_live_chat_reaction_line(redemption) is None


def test_ticker_duplicate_of_an_event_is_not_counted_again():
    """Đo trên corpus thật: ticker (`addLiveChatTickerItemAction`) nhúng lại
    NGUYÊN renderer của sự kiện trong showItemEndpoint — vì thế grep chuỗi thô
    đếm 10 membership/8 gift trong khi số sự kiện thật là 7/4. Parser chỉ đọc
    addChatItemAction nên bản sao ticker không được đếm lần hai."""
    ticker_line = json.dumps(
        {
            "replayChatItemAction": {
                "actions": [
                    {
                        "addLiveChatTickerItemAction": {
                            "item": {
                                "liveChatTickerSponsorItemRenderer": {
                                    "showItemEndpoint": {
                                        "showLiveChatItemEndpoint": {
                                            "renderer": {
                                                "liveChatMembershipItemRenderer": {
                                                    "id": "member-003",
                                                    "timestampUsec": "1788970120000000",
                                                    "headerSubtext": {"simpleText": "Sơ cấp"},
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            "videoOffsetTimeMsec": "180000",
        }
    )
    assert parse_live_chat_reaction_line(ticker_line) is None
    assert parse_live_chat_reaction_actions(ticker_line) == []


def test_parse_reaction_line_skips_text_placeholder_and_garbage():
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    text_line = next(line for line in lines if "liveChatTextMessageRenderer" in line)
    placeholder = next(line for line in lines if "PlaceholderItemRenderer" in line)
    assert parse_live_chat_reaction_line(text_line) is None
    assert parse_live_chat_reaction_line(placeholder) is None
    assert parse_live_chat_reaction_line("") is None
    assert parse_live_chat_reaction_line("not json") is None
    assert parse_live_chat_reaction_line(json.dumps({"replayChatItemAction": {}})) is None


# ---------------------------------------------------------------------------
# Live parser (timestampUsec-based) — youtube_ytdlp
# ---------------------------------------------------------------------------


def test_live_reaction_parser_uses_absolute_timestamps():
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    superchat_line = next(line for line in lines if "PaidMessageRenderer" in line)
    out = parse_live_chat_reaction_actions(superchat_line)
    assert len(out) == 1
    r = out[0]
    assert r.kind == "superchat"
    assert r.platform == "youtube"
    assert r.ext_id == "paid-001"
    assert r.amount == 50000.0
    assert r.currency == "₫"
    # timestampUsec 1788970000000000 -> epoch giây 1788970000, aware UTC
    assert r.ts_utc == datetime.fromtimestamp(1_788_970_000, UTC)

    # redemption + text vẫn bị bỏ trên đường live
    redemption = next(line for line in lines if "GiftRedemption" in line)
    text_line = next(line for line in lines if "TextMessageRenderer" in line)
    assert parse_live_chat_reaction_actions(redemption) == []
    assert parse_live_chat_reaction_actions(text_line) == []
    assert parse_live_chat_reaction_actions("") == []


def test_live_reaction_parser_never_leaks_authors():
    dumped = repr(
        [
            r
            for line in FIXTURE.read_text(encoding="utf-8").splitlines()
            for r in parse_live_chat_reaction_actions(line)
        ]
    )
    for name in AUTHOR_STRINGS:
        assert name not in dumped


# ---------------------------------------------------------------------------
# API: POST/GET /sessions/{id}/reactions
# ---------------------------------------------------------------------------


def _session(client) -> str:
    r = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60}
    )
    return r.json()["session_id"]


def test_post_and_list_reactions_roundtrip(client):
    sid = _session(client)
    r = client.post(
        f"/sessions/{sid}/reactions",
        json={
            "kind": "superchat",
            "ts_utc": "2026-09-11T13:00:00+00:00",
            "amount": 50000,
            "currency": "₫",
            "platform": "youtube",
            "ext_id": "sc-1",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "superchat"
    assert body["amount"] == 50000
    assert body["currency"] == "₫"

    listed = client.get(f"/sessions/{sid}/reactions").json()
    assert len(listed) == 1
    assert listed[0]["ext_id"] == "sc-1"


def test_post_reaction_idempotent_on_platform_ext_id(client):
    sid = _session(client)
    payload = {"kind": "gift", "platform": "youtube", "ext_id": "gift-dup"}
    first = client.post(f"/sessions/{sid}/reactions", json=payload).json()
    second = client.post(f"/sessions/{sid}/reactions", json=payload).json()
    assert second["reaction_id"] == first["reaction_id"]
    assert len(client.get(f"/sessions/{sid}/reactions").json()) == 1


def test_post_reaction_validation(client):
    sid = _session(client)
    # kind ngoài danh sách -> 422
    assert client.post(f"/sessions/{sid}/reactions", json={"kind": "diamond"}).status_code == 422
    # ts_utc naive -> 422 (hard rule 7)
    assert (
        client.post(
            f"/sessions/{sid}/reactions",
            json={"kind": "like", "ts_utc": "2026-09-11T13:00:00"},
        ).status_code
        == 422
    )
    # amount âm -> 422
    assert (
        client.post(
            f"/sessions/{sid}/reactions", json={"kind": "superchat", "amount": -5}
        ).status_code
        == 422
    )
    # phiên không tồn tại -> 404
    assert (
        client.post(f"/sessions/{uuid.uuid4()}/reactions", json={"kind": "like"}).status_code == 404
    )


# ---------------------------------------------------------------------------
# Replay route end-to-end: paid events được lưu và ma trận tín hiệu nói CÓ
# ---------------------------------------------------------------------------


def _fake_download_paid():
    def fake(url: str, out_dir, **kwargs) -> DownloadResult:
        copy = Path(out_dir) / "vidpaid.live_chat.json"
        shutil.copyfile(FIXTURE, copy)
        return DownloadResult(
            chat_path=copy, video_title="Live có Super Chat", duration_s=600.0, error=None
        )

    return fake


def test_replay_route_stores_reactions(client, monkeypatch):
    monkeypatch.setattr(replays, "download_chat_replay", _fake_download_paid())
    r = client.post("/replays/youtube", json={"url": "https://youtu.be/vidpaid"})
    job = client.get(f"/replays/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done", job
    sid = job["session_id"]

    reactions = client.get(f"/sessions/{sid}/reactions").json()
    assert [x["kind"] for x in reactions] == ["superchat", "sticker", "membership", "gift"]
    superchat = reactions[0]
    assert superchat["amount"] == 50000.0
    assert superchat["currency"] == "₫"
    assert superchat["platform"] == "youtube"
    # ts_utc được neo theo offset video từ start_ts lùi lại
    ts = [datetime.fromisoformat(x["ts_utc"]) for x in reactions]
    assert ts == sorted(ts)
    assert (ts[1] - ts[0]).total_seconds() == 60.0

    # ma trận tín hiệu: buổi CÓ paid events -> reactions ok, đếm đúng
    signals = client.get(f"/sessions/{sid}/signals").json()
    reactions_sig = next(s for s in signals["signals"] if s["name"] == "reactions")
    assert reactions_sig["status"] == "ok"
    assert "4" in reactions_sig["detail"]

    # không tên người tặng nào lọt vào bất kỳ đâu của API
    dumped = json.dumps(reactions, ensure_ascii=False) + json.dumps(signals, ensure_ascii=False)
    for name in AUTHOR_STRINGS:
        assert name not in dumped


def test_replay_without_paid_events_declares_reactions_missing(client, monkeypatch):
    """Buổi không có Super Chat/quà (đa số shop VN): ô reactions phải là
    THIẾU kèm lý do nguồn, tuyệt đối không phải 0 lặng lẽ."""
    plain = Path(__file__).parent / "data" / "live_chat_fixture.jsonl"

    def fake(url: str, out_dir, **kwargs) -> DownloadResult:
        copy = Path(out_dir) / "vidplain.live_chat.json"
        shutil.copyfile(plain, copy)
        return DownloadResult(chat_path=copy, video_title="Live thường", duration_s=600.0)

    monkeypatch.setattr(replays, "download_chat_replay", fake)
    r = client.post("/replays/youtube", json={"url": "https://youtu.be/vidplain"})
    job = client.get(f"/replays/jobs/{r.json()['job_id']}").json()
    sid = job["session_id"]

    # fixture thường có 1 membership + 1 sticker -> thật ra CÓ 2 reactions
    reactions = client.get(f"/sessions/{sid}/reactions").json()
    assert [x["kind"] for x in reactions] == ["membership", "sticker"]

    # còn phiên thật sự không có sự kiện nào: kiểm tra qua assess trực tiếp
    from livelift.core.signals import assess

    cov = assess(
        has_schedule=False,
        n_ticks=20,
        n_ticks_with_viewers=0,
        tick_coverage_share=1.0,
        n_comments=100,
        n_clicks=0,
        n_orders=0,
        n_reactions=0,
        platform="replay",
        analysis_only=True,
    )
    sig = next(s for s in cov.signals if s.name == "reactions")
    assert sig.status == "missing"
    assert "chat replay" in sig.detail
    assert "không phải phép đo bằng 0" in sig.detail


# ---------------------------------------------------------------------------
# Ma trận tín hiệu: lý do THIẾU trung thực theo từng nguồn
# ---------------------------------------------------------------------------


def _cov(platform, n_reactions=0, analysis_only=False):
    from livelift.core.signals import assess

    return assess(
        has_schedule=False,
        n_ticks=0,
        n_ticks_with_viewers=0,
        tick_coverage_share=0.0,
        n_comments=0,
        n_clicks=0,
        n_orders=0,
        n_reactions=n_reactions,
        platform=platform,
        analysis_only=analysis_only,
    )


def test_reactions_missing_reason_is_per_source():
    live_yt = next(s for s in _cov("youtube").signals if s.name == "reactions")
    assert live_yt.status == "missing"
    assert "chưa" in live_yt.detail
    assert "ingest" in live_yt.detail

    tiktok = next(s for s in _cov("tiktok").signals if s.name == "reactions")
    assert tiktok.status == "missing"
    assert "TikTok" in tiktok.detail
    assert "không hoạt động" in tiktok.detail

    have = next(s for s in _cov("replay", n_reactions=7).signals if s.name == "reactions")
    assert have.status == "ok"
    assert "7" in have.detail


# ---------------------------------------------------------------------------
# Store contract bổ sung (memory; nhánh postgres nằm ở test_store_contract)
# ---------------------------------------------------------------------------


def test_inmemory_reaction_defaults_amount_currency_none():
    store = InMemoryStore()
    sid = store.create_session(
        {
            "session_id": str(uuid.uuid4()),
            "platform": "youtube",
            "title": "t",
            "mode": "auto",
            "status": "live",
            "planned_duration_min": 60,
            "host_id": None,
            "created_at": datetime.now(UTC),
        }
    )["session_id"]
    row = store.add_reaction(
        sid,
        {
            "reaction_id": str(uuid.uuid4()),
            "session_id": sid,
            "ts_utc": datetime.now(UTC),
            "kind": "membership",
            "platform": "youtube",
            "ext_id": "m-1",
        },
    )
    assert row["amount"] is None
    assert row["currency"] is None
