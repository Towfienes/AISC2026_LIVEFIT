"""Case người dùng thật — mười hành trình đầu-cuối, viết theo NGƯỜI, không theo hàm.

Repo đã có 719 test, nhưng phần lớn là test đơn vị/hợp đồng: chúng khoá từng
mảnh máy móc. Tệp này khoá thứ khác — **một người thật ngồi xuống và làm xong
việc của họ**. Mỗi test là một hành trình trọn vẹn qua đúng những đường HTTP mà
giao diện gọi, theo đúng thứ tự một chủ shop bấm, và nó chỉ xanh khi hành trình
đó *dùng được*, không phải khi từng endpoint trả 200.

Nguồn của mười case: `docs/benchmarks/kiem-chung-van-hanh.md` (đóng vai người
dùng trên API thật ngày 11/09/2026, tìm ra 8 lỗi) và
`docs/mo-hinh-van-hanh-kol.md` (ba chế độ dùng + bốn kịch bản KOL).

**Quy tắc của tệp này — quan trọng khi đọc một test đỏ:**

* Mỗi test mô tả **hành vi ĐÚNG** (cái người dùng kỳ vọng), không bao giờ mô tả
  hành vi hỏng hiện tại. Một test ở đây đỏ nghĩa là sản phẩm còn hỏng, không
  phải test sai.
* Năm kỳ vọng ở đây được viết khi lỗi tương ứng **còn hỏng** (lỗi 4, 5, 6, 7, 8
  trong mục 5 của bản kiểm chứng) và từng mang ``xfail(strict=False)``. Cả năm
  đã được các gói sửa hoàn tất trong cùng ngày 12/09 và chuyển sang XPASS, nên
  nhãn xfail được gỡ: từ đây chúng là **chốt chặn tái diễn** thật — hỏng lại là
  đỏ, không im lặng. Mỗi test vẫn ghi số hiệu lỗi cũ trong docstring để người
  đọc sau biết nó canh cái gì.
* Chỗ nào tên trường/endpoint chưa chốt khi tệp này được viết (cờ "chạy thử",
  đường đóng phiên), test **dò trong `/openapi.json`** thay vì đóng đinh một cái
  tên: bản sửa đặt tên kiểu gì hợp lý cũng làm test xanh.

**Không gọi mạng thật.** Chat replay YouTube được sinh tại chỗ đúng định dạng
yt-dlp trả về và bơm qua ``download_chat_replay`` đã monkeypatch; mọi thứ khác
chạy trên ``InMemoryStore``.

**Đồng hồ phiên.** Một phiên switchback 30–60 phút không thể chờ thật. Test dời
``start_ts`` của phiên trong kho (đúng thủ thuật của ``tests/test_autopilot.py``)
để đưa phiên tới từng giây cần thiết. Mọi sự kiện vẫn đi qua đúng route sản
xuất — bình luận vẫn bị lọc PII, cú bấm vẫn bị bộ lọc GIVT chấm như thật; chỉ
mốc thời gian là ảo.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api import autopilot, service
from livelift.api.main import create_app
from livelift.api.routes import replays
from livelift.api.store import InMemoryStore, SnapshotManager
from livelift.ingest.youtube_replay import DownloadResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _quiet_autopilot(monkeypatch):
    """Bộ thực thi tự động TẮT mặc định trong tệp này.

    Không phải vì nó sai — case 7 bật nó lên và kiểm chứng nó chạy — mà vì một
    vòng quét nền mỗi 5 giây sẽ ghim xen vào giữa các hành trình khác và làm
    kết quả phụ thuộc tốc độ máy. Case 7 gọi thẳng một nhịp quét, không chờ.
    """
    monkeypatch.setenv("LIVELIFT_AUTOPILOT", "0")
    autopilot.reset_heartbeats()
    replays._JOBS.clear()
    yield
    autopilot.reset_heartbeats()
    replays._JOBS.clear()


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def client(store):
    app = create_app(store=store)
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Chat replay giả lập — đúng định dạng tệp `*.live_chat.json` của yt-dlp
# ---------------------------------------------------------------------------


def _chat_replay_text(messages: list[tuple[float, str]]) -> str:
    """Nội dung tệp chat replay: một JSON mỗi dòng, có tên tác giả như tệp thật.

    Tên tác giả CỐ TÌNH có mặt: đường nạp phải vứt chúng đi trước khi ghi
    (quy tắc cứng 1), và case 1 kiểm chứng đúng điều đó.
    """
    lines = []
    for i, (offset_s, text) in enumerate(messages):
        lines.append(
            json.dumps(
                {
                    "replayChatItemAction": {
                        "actions": [
                            {
                                "addChatItemAction": {
                                    "item": {
                                        "liveChatTextMessageRenderer": {
                                            "message": {"runs": [{"text": text}]},
                                            "authorName": {"simpleText": f"Khan Gia So {i}"},
                                            "authorExternalChannelId": f"UCkhangia{i:06d}",
                                            "id": f"msg-{i:05d}",
                                        }
                                    }
                                }
                            }
                        ],
                        "videoOffsetTimeMsec": str(int(offset_s * 1000)),
                    },
                    "isLive": False,
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines) + "\n"


def _fake_download(messages: list[tuple[float, str]], *, title: str, duration_s: float):
    """Thay ``download_chat_replay``: ghi tệp chat vào thư mục tạm của job."""

    def fake(url: str, out_dir, **kwargs) -> DownloadResult:
        path = Path(out_dir) / "fixture.live_chat.json"
        path.write_text(_chat_replay_text(messages), encoding="utf-8")
        return DownloadResult(chat_path=path, video_title=title, duration_s=duration_s, error=None)

    return fake


def _load_replay(client, monkeypatch, messages, *, title, duration_s, url):
    """Nạp một buổi live ĐÃ KẾT THÚC và trả về trạng thái job (đã xong)."""
    monkeypatch.setattr(
        replays,
        "download_chat_replay",
        _fake_download(messages, title=title, duration_s=duration_s),
    )
    r = client.post("/replays/youtube", json={"url": url})
    assert r.status_code == 202, r.text
    job = client.get(f"/replays/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


# Buổi live nước hoa (ngành hàng của bản kiểm chứng 11/09): PII thật kiểu
# Việt Nam, teencode, ý định trộn lẫn — đúng thứ một buổi bán hàng thật sinh ra.
PERFUME_CHAT: list[tuple[float, str]] = [
    (12.0, "chào shop, hôm nay có mùi nào mới không ạ"),
    (48.0, "chai này bao nhiêu tiền vậy shop"),
    (95.0, "mùi này để lâu có bay không ad"),
    (150.0, "chốt 1 chai nước hoa nam nha shop"),
    (185.0, "sđt em 0912345678, ship về Gò Vấp giúp em nhé"),
    (240.0, "mắc hơn shopee rồi shop ơi"),
    (300.0, "ship cod được không ạ, em ở 25 Nguyễn Trãi quận 5"),
    (355.0, "cho e xin size chai 50ml"),
    (420.0, "dat 2 chai nha shop"),
    (480.0, "mail em la huongthom88@gmail.com gui bill giup e"),
    (540.0, "phí ship về Đà Nẵng bao nhiêu shop"),
    (600.0, "❤❤❤ hóng sale"),
    (660.0, "chốt đơn chai xám nha"),
    (720.0, "shop còn hàng không ạ"),
    (780.0, "mùi này giống chai bên kia quá"),
    (840.0, "lấy 1 chai mini thôi ạ"),
    (900.0, "bao giờ shop live lại vậy"),
    (960.0, "cho em hỏi giá chai 100ml"),
    (1020.0, "chot don, ship gap giup em"),
    (1080.0, "shop tư vấn mùi cho nữ với"),
]


# ---------------------------------------------------------------------------
# Đồng hồ phiên + mô phỏng một phiên thí nghiệm có đo được
# ---------------------------------------------------------------------------


@contextmanager
def _session_clock_at(store, session_id: str, offset_s: float):
    """Đưa phiên về đúng giây ``offset_s`` của buổi phát, rồi trả lại như cũ.

    Không giả lập hành vi nào: route vẫn tự tính khối hiện tại từ
    ``now - start_ts`` như trên máy chủ thật. Chỉ mốc bắt đầu là ảo.
    """
    saved = store.get_session(session_id)["start_ts"]
    store.update_session(session_id, {"start_ts": service.now_utc() - timedelta(seconds=offset_s)})
    try:
        yield
    finally:
        store.update_session(session_id, {"start_ts": saved})


def _click_at(client, store, session_id: str, code: str, offset_s: float, ua: str):
    """Một người xem bấm link đo ở giây ``offset_s`` của phiên.

    Cú bấm đi qua đúng ``GET /r/{code}`` nên vẫn được bộ lọc GIVT/refractory
    chấm thật; sau đó dấu thời gian của dòng click được đặt về đúng giây ấy
    (đồng hồ tường của máy test chỉ trôi vài mili-giây cho cả phiên 60 phút).
    """
    truoc = len(store.list_clicks(session_id))
    with _session_clock_at(store, session_id, offset_s):
        r = client.get(f"/r/{code}", follow_redirects=False, headers={"user-agent": ua})
    assert r.status_code == 302
    # Đường redirect nuốt mọi lỗi ghi log để cú chuyển hướng không bao giờ hỏng;
    # ở đây phải kiểm tra thật sự có dòng mới, nếu không sẽ dời nhầm dòng cũ.
    assert len(store.list_clicks(session_id)) == truoc + 1, "cú bấm không được ghi lại"
    start = store.get_session(session_id)["start_ts"]
    store._clicks[session_id][-1]["ts"] = start + timedelta(seconds=offset_s)
    return r


def _measurement_blocks(schedule: dict) -> list[dict]:
    return [b for b in schedule["blocks"] if not b["is_washout"]]


def _run_measured_session(
    client,
    store,
    *,
    title: str,
    duration_min: int = 30,
    block_min: int = 5,
    seed: int = 2026,
    mode: str = "auto",
    create_extra: dict | None = None,
    clicks_per_block: int = 4,
    invalid_clicks: int = 0,
    pin_on_blocks: int = 2,
) -> dict:
    """Chạy TRỌN một phiên thí nghiệm: sản phẩm → lịch → phát sóng → người xem
    (bình luận + số người xem + cú bấm) → ghim trong khối BẬT → kết thúc.

    Đây là hành trình chuẩn mà case 2 và case 4 dùng lại. Trả về mọi thứ người
    gọi cần để khẳng định: session_id, lịch gán, số cú bấm hợp lệ/thô.
    """
    # Danh mục dùng chung toàn hệ thống (chưa tách theo chủ): gọi lần thứ hai
    # trên cùng một kho là chuyện bình thường, nên chấp nhận cả 409.
    for i in range(3):
        r = client.post(
            "/products",
            json={
                "product_id": f"KC{i}",
                "name": f"Nước hoa mini số {i}",
                "category": "nuoc-hoa",
                "cost": 60000 + 1000 * i,
                "price": 199000 + 1000 * i,
                "stock": 50,
            },
        )
        assert r.status_code in (200, 409), r.text

    body = {
        "platform": "youtube",
        "mode": mode,
        "planned_duration_min": duration_min,
        "title": title,
    }
    if create_extra:
        body.update(create_extra)
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]

    r = client.post(
        f"/sessions/{sid}/schedule",
        json={"block_min": block_min, "washout_min": 0, "jitter_s": 0, "seed": seed},
    )
    assert r.status_code == 200, r.text
    schedule = r.json()
    assert client.post(f"/sessions/{sid}/start").status_code == 200

    duration_s = duration_min * 60
    start_ts = service.now_utc() - timedelta(seconds=duration_s)
    store.update_session(sid, {"start_ts": start_ts})
    store.materialize_block_times(sid, start_ts)

    # Link đo: bắt buộc kèm session_id, nếu không cú bấm biến mất khỏi thí
    # nghiệm (cái bẫy số 1 trong mo-hinh-van-hanh-kol.md §5.2).
    code = client.post(
        "/shortlinks",
        json={
            "product_id": "KC0",
            "session_id": sid,
            "target_url": "https://shop.example/nuoc-hoa-mini",
        },
    ).json()["code"]

    # Telemetry người xem: một điểm đo mỗi 30 giây, suốt phiên.
    for k in range(0, duration_s, 30):
        r = client.post(
            f"/sessions/{sid}/ticks",
            json={
                "viewers": 48 + (k // 30) % 9,
                "comment_rate": 2.0,
                "ts_utc": (start_ts + timedelta(seconds=k)).isoformat(),
            },
        )
        assert r.status_code == 200, r.text

    blocks = _measurement_blocks(schedule)
    on_blocks = [b for b in blocks if b["assignment"] == "ON"]

    # Ghim trong các khối BẬT — không có bước này, nhánh điều trị không hề
    # được điều trị và thí nghiệm rỗng ruột (kiểm chứng 11/09 §2.2b).
    for b in on_blocks[:pin_on_blocks]:
        with _session_clock_at(store, sid, b["start_offset_s"] + 30):
            r = client.post(f"/sessions/{sid}/actions/execute", json={})
        assert r.status_code == 200, r.text

    # Bình luận + cú bấm rải đều trong cửa sổ phân tích của từng khối
    # (sau burn-in 60 giây, nếu không cú bấm rơi vào vùng bị loại).
    n_valid = n_raw = 0
    for bi, b in enumerate(blocks):
        lo, hi = b["start_offset_s"], b["end_offset_s"]
        for j, text in enumerate(
            (f"khối {bi} chốt đơn nha shop", f"khối {bi} giá bao nhiêu vậy ạ")
        ):
            client.post(
                f"/sessions/{sid}/comments",
                json={
                    "text": text,
                    "ts_utc": (start_ts + timedelta(seconds=lo + 40 + 90 * j)).isoformat(),
                },
            )
        span = max(hi - lo - 100, 30)
        for j in range(clicks_per_block):
            offset = lo + 70 + span * j / max(clicks_per_block, 1)
            _click_at(
                client,
                store,
                sid,
                code,
                offset,
                f"Mozilla/5.0 (Linux; Android 13; Nguoi-xem-{bi}-{j}) AppleWebKit/537.36",
            )
            n_valid += 1
            n_raw += 1

    # Traffic bot (tuỳ chọn): bị bộ lọc GIVT gắn cờ, KHÔNG bị xoá.
    for j in range(invalid_clicks):
        b = blocks[j % len(blocks)]
        _click_at(
            client,
            store,
            sid,
            code,
            b["start_offset_s"] + 100,
            f"python-urllib/3.12 con-bot-{j}",
        )
        n_raw += 1

    assert client.post(f"/sessions/{sid}/end").status_code == 200
    return {
        "session_id": sid,
        "schedule": schedule,
        "blocks": blocks,
        "on_blocks": on_blocks,
        "shortlink_code": code,
        "n_valid_clicks": n_valid,
        "n_raw_clicks": n_raw,
    }


def _first_number(text: str) -> int | None:
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else None


def _signal(body: dict, name: str) -> dict:
    return next(s for s in body["signals"] if s["name"] == name)


def _capability(body: dict, needle: str) -> dict:
    return next(c for c in body["capabilities"] if needle in c["name"])


# ===========================================================================
# CASE 1 — "Chủ shop phân tích buổi live của NGƯỜI KHÁC"
# ===========================================================================


def test_case_1_shop_owner_analyses_someone_elses_finished_live(client, monkeypatch):
    """Case 1 — "Chủ shop dán link một buổi live của người khác rồi đọc phân tích".

    Đây là chế độ QUAN SÁT, con đường DUY NHẤT "dán link là xong"
    (mo-hinh-van-hanh-kol.md §1.1). Hành trình: dán một buổi YouTube đã kết
    thúc còn chat replay → chờ job → đọc báo cáo tiếng Việt.

    Kỳ vọng của người dùng, đủ cả hai vế:

    * CÓ: nhịp bình luận, phân bố ý định, và PII đã bị che TRƯỚC khi ghi.
    * KHÔNG: bất kỳ con số nhân quả nào, và ma trận tín hiệu phải nói THẲNG
      cái gì thiếu (số người xem, link đo, lịch gán) — "thiếu nguồn" khác hẳn
      "đo được bằng 0".
    """
    job = _load_replay(
        client,
        monkeypatch,
        PERFUME_CHAT,
        title="Live nước hoa chính hãng tối thứ Sáu",
        duration_s=1200.0,
        url="https://www.youtube.com/watch?v=ZU_0QJzsR6w",
    )
    assert job["n_comments"] == len(PERFUME_CHAT)
    sid = job["session_id"]

    session = client.get(f"/sessions/{sid}").json()
    assert session["platform"] == "replay"
    assert session["status"] == "ended"
    assert session["design"]["analysis_only"] is True

    # --- CÓ: bình luận đã che PII, đã gắn nhãn ý định -------------------
    comments = client.get(f"/sessions/{sid}/comments").json()
    assert len(comments) == len(PERFUME_CHAT)
    joined = " ".join(c["text"] for c in comments)
    for leak in ("0912345678", "huongthom88@gmail.com", "Nguyễn Trãi", "Khan Gia So"):
        assert leak not in joined, f"PII/tác giả lọt ra ngoài: {leak!r}"
    assert "[SĐT]" in joined
    assert all(c["intent"] is not None for c in comments)

    bao_cao = client.get(f"/sessions/{sid}/bao-cao").json()
    assert bao_cao["loai_phien"] == "quan_sat"
    assert "KHÔNG có số nhân quả" in bao_cao["nhan"]
    assert bao_cao["tong_quan"]["tong_binh_luan"] == len(PERFUME_CHAT)
    assert bao_cao["tong_quan"]["dinh_binh_luan"] is not None, (
        "buổi live có bình luận thì phải rút ra được nhịp bình luận"
    )
    assert bao_cao["phan_bo_y_dinh"]["tong"] == len(PERFUME_CHAT)
    assert bao_cao["phan_bo_y_dinh"]["caveat"], "phân bố ý định phải đi kèm caveat bắt buộc"
    assert bao_cao["pii_da_che"], "phải thống kê được PII đã che"
    assert "phone" in bao_cao["pii_da_che"]

    # --- KHÔNG: không một con số nhân quả nào ---------------------------
    assert bao_cao["ket_qua_thi_nghiem"] is None
    report = client.get(f"/sessions/{sid}/report").json()
    assert report["n_blocks"] == 0
    assert report["diff_in_means"] is None
    assert "quan sát" in report["label"]
    for cau in bao_cao["goi_y_chien_thuat"]:
        assert "quan sát, chưa kiểm chứng nhân quả" in cau, (
            f"gợi ý trên phiên quan sát phải dán nhãn quan sát: {cau!r}"
        )

    # --- Ma trận tín hiệu tuyên bố ĐÚNG cái gì thiếu --------------------
    signals = client.get(f"/sessions/{sid}/signals").json()
    assert _signal(signals, "comments")["status"] == "ok"
    assert _signal(signals, "schedule")["status"] == "missing"
    assert _signal(signals, "clicks")["status"] == "missing"
    ticks_signal = _signal(signals, "ticks")
    assert ticks_signal["status"] == "missing", (
        "VOD đã kết thúc không còn lộ số người xem — cột đó là chỗ trống, không phải 0"
    )
    assert ticks_signal["detail"], "thiếu tín hiệu thì phải nói LÝ DO, không để trống"
    assert _capability(signals, "thí nghiệm nhân quả")["status"] == "missing"
    assert _capability(signals, "radar ý định")["status"] == "ok"
    # số người xem là None + có lý do, tuyệt đối không phải số 0
    assert bao_cao["tong_quan"]["nguoi_xem"] is None
    assert bao_cao["tong_quan"]["thieu"].get("nguoi_xem")

    # Phiên quan sát không bao giờ được lọt vào kết quả gộp.
    assert client.get("/experiment/summary").json()["n_sessions"] == 0


def test_case_1_finished_replay_offers_no_pin_cards(client, monkeypatch):
    """Case 1 (chốt lỗi 8) — "Buổi live đã phát xong thì đừng mời tôi ghim hàng".

    Tiếp ngay hành trình trên: chủ shop mở bảng điều khiển của phiên phân tích.
    Buổi live ấy đã phát xong từ lâu và là của người khác — không thể ghim gì
    được nữa. Thẻ "Ghim ..." ở đây là lời mời thao tác vô nghĩa, và ba sản phẩm
    demo trong kho chẳng liên quan gì tới video (kiem-chung-van-hanh.md §1.5).
    """
    for i in range(3):
        client.post(
            "/products",
            json={
                "product_id": f"DEMO{i}",
                "name": f"Sản phẩm demo {i}",
                "cost": 10000,
                "price": 50000,
                "stock": 40,
            },
        )
    job = _load_replay(
        client,
        monkeypatch,
        PERFUME_CHAT,
        title="Live nước hoa chính hãng tối thứ Sáu",
        duration_s=1200.0,
        url="https://www.youtube.com/watch?v=ZU_0QJzsR6w",
    )
    state = client.get(f"/sessions/{job['session_id']}/state").json()
    assert state["status"] == "ended"
    assert state["cards"] == [], (
        "phiên QUAN SÁT đã kết thúc không được mời ghim hàng: "
        f"vẫn còn {[c['headline'] for c in state['cards']]}"
    )


# ===========================================================================
# CASE 2 — "Chủ shop chạy phiên thí nghiệm đầu tiên"
# ===========================================================================


def test_case_2_shop_owner_runs_their_first_experiment_session(client, store):
    """Case 2 — "Tôi muốn tự chạy một phiên thí nghiệm và cầm về con số thật".

    Hành trình đầy đủ của chế độ 3: tạo sản phẩm → tạo phiên → bốc lịch BẬT/TẮT
    → phát sóng → người xem đổ vào (bình luận + số người xem + bấm link đo) →
    ghim trong khối BẬT → kết thúc → đọc kết quả.

    Ba khẳng định người dùng quan tâm:
      1. có số nhân quả thật (ước lượng + p-value + số lần vẽ lại);
      2. tuân thủ > 0 — nhánh BẬT thật sự đã được can thiệp;
      3. số cú bấm mà ma trận tín hiệu khoe KHỚP với số trong báo cáo
         (kiểm chứng 11/09 §2.4a: hai màn hình từng đá nhau, chủ shop được bảo
         "đủ tín hiệu" rồi nhận về số rỗng).
    """
    run = _run_measured_session(
        client,
        store,
        title="Phiên thí nghiệm đầu tiên của shop",
        duration_min=60,
        block_min=5,
        clicks_per_block=4,
        pin_on_blocks=3,
    )
    sid = run["session_id"]

    # 1. Số nhân quả thật, chạy đúng đường phân tích tiền đăng ký.
    bao_cao = client.get(f"/sessions/{sid}/bao-cao").json()
    assert bao_cao["loai_phien"] == "thi_nghiem"
    ket_qua = bao_cao["ket_qua_thi_nghiem"]
    assert ket_qua is not None
    assert ket_qua["estimable"] is True, (
        f"phiên có đủ khối đo được mà vẫn không ước lượng được: {ket_qua['message']!r}"
    )
    assert ket_qua["n_blocks"] >= 4
    assert ket_qua["n_on"] >= 2
    assert ket_qua["n_off"] >= 2
    assert ket_qua["estimate"] is not None
    assert ket_qua["p_value"] is not None
    assert 0.0 <= ket_qua["p_value"] <= 1.0
    assert ket_qua["n_draws"] is not None
    assert ket_qua["n_draws"] > 0

    report = client.get(f"/sessions/{sid}/report").json()
    assert report["source"] == "experiment"
    assert report["diff_in_means"] is not None
    assert report["n_blocks"] >= 4

    # 2. Tuân thủ > 0: nhánh BẬT đã thật sự được can thiệp.
    compliance = report["compliance"]
    assert compliance["on_blocks"] > 0
    assert compliance["on_blocks_with_pin"] >= 3
    assert compliance["compliance_rate"] is not None
    assert compliance["compliance_rate"] > 0.0, (
        "chế độ tự động mà không ghim gì thì thí nghiệm rỗng ruột — kiểm chứng 11/09 §2.2b"
    )

    # 3. Hai màn hình phải nói cùng một con số.
    signals = client.get(f"/sessions/{sid}/signals").json()
    assert _signal(signals, "schedule")["status"] == "ok"
    assert _signal(signals, "comments")["status"] == "ok"
    assert _signal(signals, "clicks")["status"] == "ok"
    assert _capability(signals, "thí nghiệm nhân quả")["status"] == "ok"

    so_trong_signals = _first_number(_signal(signals, "clicks")["detail"])
    so_trong_bao_cao = bao_cao["tong_quan"]["luot_nhap_hop_le"]
    assert so_trong_bao_cao == run["n_valid_clicks"]
    assert so_trong_signals == so_trong_bao_cao, (
        "/signals và /bao-cao phải nói cùng một con số nhấp — "
        f"/signals: {so_trong_signals}, /bao-cao: {so_trong_bao_cao}"
    )

    # Cam kết thiết kế công bố TRƯỚC khi phát sóng vẫn còn nguyên sau phiên —
    # đây là thứ chủ shop đưa cho người phản biện để chứng minh lịch gán không
    # bị đụng vào giữa chừng.
    detail = client.get(f"/sessions/{sid}").json()
    assert detail["status"] == "ended"
    assert detail["design"]["design_hash"] == run["schedule"]["design_hash"]


def test_case_2_signal_matrix_does_not_overstate_clicks_when_bots_click(client, store):
    """Case 2 (chốt lỗi 5) — "Hệ thống bảo tôi đủ tín hiệu, rồi trả về số rỗng".

    Cùng hành trình trên, nhưng có traffic bot — chuyện bình thường với một link
    công khai. Bộ lọc GIVT gắn cờ đúng (và KHÔNG xoá, đúng thiết kế). Cái từng
    sai là ở tầng hiển thị: ma trận tín hiệu khoe con số THÔ trong khi phân tích
    dùng số HỢP LỆ, nên chủ shop được bảo "đủ tín hiệu" rồi nhận về số rỗng mà
    không một lời giải thích (kiem-chung-van-hanh.md §2.4a).
    """
    run = _run_measured_session(
        client,
        store,
        title="Phiên có traffic bot",
        duration_min=30,
        block_min=5,
        clicks_per_block=3,
        invalid_clicks=6,
        pin_on_blocks=2,
    )
    sid = run["session_id"]
    assert run["n_raw_clicks"] > run["n_valid_clicks"], "kịch bản phải thật sự có nhấp bị gắn cờ"

    bao_cao = client.get(f"/sessions/{sid}/bao-cao").json()
    hop_le = bao_cao["tong_quan"]["luot_nhap_hop_le"]
    assert hop_le == run["n_valid_clicks"]

    detail = _signal(client.get(f"/sessions/{sid}/signals").json(), "clicks")["detail"]
    so_khoe = _first_number(detail)
    assert so_khoe == hop_le or str(hop_le) in detail, (
        "ma trận tín hiệu phải hoặc nói thẳng con số HỢP LỆ, hoặc nêu cả hai con số "
        f"(thô và hợp lệ) — hiện đang khoe {so_khoe} trong khi phân tích dùng {hop_le} "
        f"và không nhắc tới con số ấy ở đâu: {detail!r}"
    )


# ===========================================================================
# CASE 3 — "Người dùng chọn cấu hình phiên không may"
# ===========================================================================


@pytest.mark.parametrize(
    ("duration_min", "block_min"),
    [
        (50, 10),  # "phiên 50 phút, đổi khối mỗi 10 phút" — lựa chọn rất tự nhiên
        (25, 5),
        (30, 6),
        (5, 1),
        (10, 2),
        (15, 3),
        (35, 7),
        (40, 8),
    ],
)
def test_case_3_unlucky_session_configs_never_answer_5xx(client, duration_min, block_min):
    """Case 3 — "Tôi gõ một cấu hình phiên bình thường và hệ thống sập".

    Bản kiểm chứng 11/09 (§2.1) tìm ra quy luật tất định: hễ
    ``planned_duration_min / block_min == 5`` thì bước bốc lịch trả HTTP 500 với
    thân rỗng — chết ngay ở bước bắt buộc, không một lời giải thích.
    "Phiên 50 phút, đổi khối mỗi 10 phút" là lựa chọn rất tự nhiên của chủ shop.

    Kỳ vọng: hoặc bốc được lịch (200) và phát sóng được, hoặc từ chối bằng 400
    kèm thông báo tiếng Việt nói được PHẢI LÀM GÌ. **Không bao giờ 5xx.**
    """
    sid = client.post(
        "/sessions",
        json={
            "platform": "youtube",
            "mode": "auto",
            "planned_duration_min": duration_min,
            "title": f"Phiên {duration_min} phút, khối {block_min} phút",
        },
    ).json()["session_id"]

    r = client.post(
        f"/sessions/{sid}/schedule",
        json={"block_min": block_min, "washout_min": 0, "jitter_s": 0, "seed": 4242},
    )
    assert r.status_code < 500, (
        f"cấu hình {duration_min}/{block_min} trả {r.status_code} — "
        f"lỗi cấu hình của người dùng không bao giờ được là lỗi máy chủ: {r.text[:200]}"
    )
    assert r.status_code in (200, 400), r.text

    if r.status_code == 400:
        detail = r.json()["detail"]
        assert detail is not None
        assert detail.strip(), "400 mà thông báo rỗng thì vô dụng như 500"
        assert any(tu in detail for tu in ("khối", "phiên", "thiết kế", "thời lượng")), (
            f"thông báo phải là tiếng Việt nói rõ vướng ở đâu: {detail!r}"
        )
        return

    # Bốc được lịch thì phải phát sóng được — không nửa vời.
    body = r.json()
    assert body["n_on"] + body["n_off"] == len(_measurement_blocks(body))
    assert client.post(f"/sessions/{sid}/start").status_code == 200


# ===========================================================================
# CASE 4 — "Chủ shop chạy thử rồi chạy thật"
# ===========================================================================

#: Tên trường cờ "chạy thử" chưa chốt khi tệp này được viết — test dò trong
#: openapi.json nên bất kỳ cách đặt tên hợp lý nào cũng làm nó xanh.
DRY_RUN_FIELDS = (
    "chay_thu",
    "la_chay_thu",
    "dry_run",
    "is_dry_run",
    "test_run",
    "trial",
    "practice",
    "exclude_from_summary",
)


def _dry_run_field(client) -> str | None:
    schema = client.get("/openapi.json").json()["components"]["schemas"].get("SessionCreate", {})
    props = set(schema.get("properties", {}))
    return next((name for name in DRY_RUN_FIELDS if name in props), None)


def test_case_4_a_practice_run_never_pollutes_the_pooled_result(client, store):
    """Case 4 (chốt lỗi 7) — "Tôi bấm thử một phát cho quen tay, rồi mới chạy thật".

    Ai cũng chạy thử trước buổi live đầu tiên. Trước 12/09 mọi phiên đã kết thúc
    có lịch gán đều bị gộp vào ``/experiment/summary``, nên chạy thử một lần là
    **làm bẩn kết quả của chính mình**, và không có nút gỡ
    (kiem-chung-van-hanh.md §2.4c — hai phiên dò lỗi sống 1 giây đã lọt vĩnh viễn
    vào kết quả gộp).

    Kỳ vọng: phiên đánh dấu chạy thử nằm ngoài kết quả tổng; hai phiên thật thì
    có mặt đầy đủ.
    """
    field = _dry_run_field(client)
    assert field is not None, (
        "không có cách nào đánh dấu một phiên là CHẠY THỬ — "
        f"POST /sessions không nhận trường nào trong {DRY_RUN_FIELDS}"
    )

    thu = _run_measured_session(
        client,
        store,
        title="Phiên chạy thử cho quen tay",
        duration_min=30,
        seed=11,
        clicks_per_block=2,
        create_extra={field: True},
    )
    that_1 = _run_measured_session(
        client, store, title="Phiên thật tối thứ Sáu", duration_min=30, seed=12, clicks_per_block=2
    )
    that_2 = _run_measured_session(
        client, store, title="Phiên thật tối thứ Bảy", duration_min=30, seed=13, clicks_per_block=2
    )

    summary = client.get("/experiment/summary").json()
    assert summary["n_sessions"] == 2, (
        "kết quả tổng phải gộp đúng hai phiên THẬT, không gộp phiên chạy thử — "
        f"đang gộp {summary['n_sessions']} phiên"
    )
    # ...và phiên chạy thử vẫn còn nguyên để chủ shop tự xem lại, chỉ là không gộp.
    assert client.get(f"/sessions/{thu['session_id']}/report").status_code == 200
    for run in (that_1, that_2):
        assert client.get(f"/sessions/{run['session_id']}/report").json()["n_blocks"] > 0


# ===========================================================================
# CASE 5 — "Phiên quan sát bị bỏ giữa chừng"
# ===========================================================================


def _abandon_endpoints(client, session_id: str) -> list[tuple[str, str]]:
    """Mọi đường có thể dùng để ĐÓNG/HUỶ một phiên, dò từ openapi.json."""
    paths = client.get("/openapi.json").json()["paths"]
    found: list[tuple[str, str]] = []
    for path, ops in paths.items():
        if "{session_id}" not in path:
            continue
        tail = path.rsplit("{session_id}", 1)[-1].strip("/")
        named = any(k in tail for k in ("cancel", "huy", "close", "abandon", "abort", "archive"))
        if "post" in ops and named:
            found.append(("post", path.replace("{session_id}", session_id)))
        if "delete" in ops and (named or tail == ""):
            found.append(("delete", path.replace("{session_id}", session_id)))
    return found


def test_case_5_an_abandoned_observation_session_can_be_closed(client):
    """Case 5 (chốt lỗi 6) — "Tôi mở phiên quan sát để gõ tay, rồi bỏ giữa chừng".

    Chế độ quan sát cho nhập bình luận ngay khi phiên còn `planned` — đó là
    điểm cộng thật (kiểm chứng 11/09 §3.2). Nhưng phiên chưa từng phát sóng thì
    **không đóng lại được**: danh sách phiên của chủ shop tích tụ những dòng
    "đang chờ" không bao giờ biến mất, và đường vòng duy nhất là bắt họ dựng cả
    bộ máy thí nghiệm mà họ không định dùng, chỉ để bấm được nút kết thúc.

    Kỳ vọng: có MỘT đường nào đó đóng/huỷ được phiên, và sau đó phiên không còn
    nằm ở `planned`.
    """
    sid = client.post(
        "/sessions",
        json={
            "platform": "tiktok",
            "mode": "suggest",
            "planned_duration_min": 15,
            "title": "Nhập tay khi live TikTok",
        },
    ).json()["session_id"]

    for text in (
        "chị ơi cái áo khoác này còn size M không",
        "chốt 1 cái màu đen nha chị",
        "ship về Bình Dương bao nhiêu ạ",
    ):
        assert client.post(f"/sessions/{sid}/comments", json={"text": text}).status_code == 200, (
            "chế độ quan sát phải nhận bình luận ngay khi phiên còn planned"
        )

    responses = [("post", client.post(f"/sessions/{sid}/end"))]
    for method, url in _abandon_endpoints(client, sid):
        responses.append((method, client.request(method.upper(), url)))

    assert any(r.status_code < 300 for _m, r in responses), (
        "không có đường nào đóng được phiên quan sát — nó sẽ kẹt ở `planned` mãi mãi; "
        f"đã thử: {[(m, r.status_code) for m, r in responses]}"
    )
    # Xoá hẳn cũng là một câu trả lời hợp lệ cho "tôi bỏ phiên này"; điều không
    # chấp nhận được là phiên còn đó mà vẫn nằm ở `planned`.
    detail = client.get(f"/sessions/{sid}")
    assert detail.status_code in (200, 404)
    if detail.status_code == 200:
        status = detail.json()["status"]
        assert status != "planned", f"đóng xong mà phiên vẫn ở trạng thái {status!r}"
        # Đóng một phiên quan sát KHÔNG được biến nó thành phiên thí nghiệm.
        assert client.get(f"/sessions/{sid}/report").json()["diff_in_means"] is None


# ===========================================================================
# CASE 6 — "Máy chủ khởi động lại giữa phiên"
# ===========================================================================


def test_case_6_a_restart_mid_session_does_not_lose_the_data(client, store, tmp_path):
    """Case 6 — "Máy chủ khởi động lại giữa phiên, dữ liệu của tôi còn không?".

    Ngày 11/09/2026 câu trả lời là KHÔNG: tiến trình API khởi động lại lúc
    13:05:53 và **13 phiên live thật cùng 17.535 bình luận biến mất vĩnh viễn**
    (kiểm chứng 11/09, mục 0) vì kho nằm hoàn toàn trong RAM.

    Hành trình ở đây đúng như hôm đó: đang live, dữ liệu đang đổ vào, tiến trình
    chết. Kỳ vọng: bật lại là thấy lại — phiên, bình luận, điểm đo, cú bấm, và
    cả lịch gán (không có lịch thì phiên không còn là thí nghiệm nữa).
    """
    sid = client.post(
        "/sessions",
        json={
            "platform": "youtube",
            "mode": "auto",
            "planned_duration_min": 60,
            "title": "Phiên đang live lúc máy chủ chết",
        },
    ).json()["session_id"]
    assert client.post(f"/sessions/{sid}/schedule", json={"seed": 7}).status_code == 200
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    client.post(
        "/products",
        json={
            "product_id": "KC-SNAP",
            "name": "Bình giữ nhiệt 500ml",
            "cost": 40000,
            "price": 95000,
            "stock": 30,
        },
    )
    code = client.post(
        "/shortlinks",
        json={
            "product_id": "KC-SNAP",
            "session_id": sid,
            "target_url": "https://shop.example/binh",
        },
    ).json()["code"]
    for i in range(12):
        client.post(f"/sessions/{sid}/comments", json={"text": f"chốt đơn số {i} nha shop"})
        client.post(f"/sessions/{sid}/ticks", json={"viewers": 70 + i, "comment_rate": 6})
    client.get(f"/r/{code}", follow_redirects=False, headers={"user-agent": "Mozilla/5.0 (X11)"})

    truoc = store.counts()
    assert truoc["comments"] == 12

    # --- tiến trình chết ------------------------------------------------
    snapshot_path = tmp_path / "livelift-store.json"
    SnapshotManager(store, snapshot_path, 1.0).dump_now(force=True)
    assert snapshot_path.exists(), "không có ảnh chụp thì khởi động lại là mất sạch"

    # --- tiến trình bật lại: kho MỚI, đọc lại từ đĩa ---------------------
    kho_moi = InMemoryStore()
    manager = SnapshotManager(kho_moi, snapshot_path, 1.0)
    sau = manager.restore()
    kho_moi.snapshot = manager
    assert sau is not None, "ảnh chụp có trên đĩa mà không khôi phục được"
    for bang in ("sessions", "comments", "ticks", "clicks", "products", "shortlinks"):
        assert sau[bang] == truoc[bang], f"bảng {bang} mất dữ liệu sau khi khởi động lại"

    app_moi = create_app(store=kho_moi)
    with TestClient(app_moi) as c2:
        session = c2.get(f"/sessions/{sid}").json()
        assert session["status"] == "live", "phiên đang phát phải vẫn đang phát sau restart"
        assert session["design"]["design_hash"], "mất lịch gán là mất luôn tính hợp lệ thí nghiệm"
        assert len(c2.get(f"/sessions/{sid}/comments").json()) == 12
        assert len(c2.get(f"/sessions/{sid}/schedule").json()) == len(
            client.get(f"/sessions/{sid}/schedule").json()
        )
        # mốc thời gian phải trở về đúng KIỂU datetime, không phải chuỗi:
        # một bản khôi phục biến ts thành chuỗi trông như chạy được rồi nói dối.
        assert kho_moi.get_session(sid)["start_ts"].tzinfo is not None
        # ...và người dùng phải ĐỌC ĐƯỢC trên /health rằng dữ liệu đang được chụp
        # lại, kèm mức mất mát tối đa — không phải đoán bằng niềm tin.
        health = c2.get("/health").json()
        assert health["storage_mode"] == "memory+snapshot"
        assert "ảnh chụp" in (health["storage_warning"] or "")
        assert health["snapshot"]["restored_at_startup"] == sau


# ===========================================================================
# CASE 7 — "Chế độ tự động chạy một mình"
# ===========================================================================


def _live_auto_session(client, store, *, seed_arm="ON"):
    """Phiên auto đang phát, đồng hồ đã ở giữa khối đo đầu tiên."""
    client.post(
        "/products",
        json={
            "product_id": "KC-AUTO",
            "name": "Set 5 khăn lau đa năng",
            "cost": 20000,
            "price": 79000,
            "stock": 60,
        },
    )
    sid = client.post(
        "/sessions",
        json={
            "platform": "youtube",
            "mode": "auto",
            "planned_duration_min": 90,
            "title": "Phiên tự động 90 phút",
        },
    ).json()["session_id"]
    seed = None
    for candidate in range(80):
        blocks = client.post(
            f"/sessions/{sid}/schedule",
            json={"block_min": 5, "washout_min": 0, "jitter_s": 0, "seed": candidate},
        ).json()["blocks"]
        first = next(b for b in blocks if not b["is_washout"])
        if first["assignment"] == seed_arm:
            seed = candidate
            break
    assert seed is not None
    blocks = client.post(
        f"/sessions/{sid}/schedule",
        json={"block_min": 5, "washout_min": 0, "jitter_s": 0, "seed": seed},
    ).json()["blocks"]
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    return sid, [b for b in blocks if not b["is_washout"]]


def test_case_7_auto_mode_either_acts_by_itself_or_says_out_loud_that_it_did_not(
    client, store, monkeypatch
):
    """Case 7 — "Tôi chọn chế độ Tự động, vậy hệ thống tự làm chứ?".

    Đến 11/09 câu trả lời là KHÔNG, và tệ hơn: **không ai nói cho chủ shop
    biết**. Phiên gắn nhãn `auto`, lịch có 4 khối BẬT, không khối nào được ghim,
    tuân thủ = 0, `diff_in_means` = null — trong khi mọi endpoint vẫn trả 200 và
    không một cảnh báo nào (§2.2b).

    Kỳ vọng — một trong hai, không bao giờ là im lặng:
      (a) bộ thực thi bật: phiên auto qua biên khối thì CÓ hành động tự động;
      (b) bộ thực thi tắt: bàn điều khiển phải BÁO ĐỘNG bằng tiếng Việt.
    """
    # --- (a) bộ thực thi bật: nó phải thật sự ghim ----------------------
    sid, blocks = _live_auto_session(client, store, seed_arm="ON")
    dau_khoi = blocks[0]["start_offset_s"] + 30
    monkeypatch.setenv("LIVELIFT_AUTOPILOT", "1")
    with _session_clock_at(store, sid, dau_khoi):
        autopilot.step_all(store, now=service.now_utc())
        state = client.get(f"/sessions/{sid}/state").json()

    exposures = store.list_exposure_events(sid)
    assert exposures, "chế độ tự động qua một khối BẬT mà không có hành động nào"
    assert exposures[0]["source"] == "model"
    assert exposures[0]["block_idx"] == blocks[0]["block_index"]
    assert state["autopilot"] is not None, "phiên auto phải cho bàn thấy trạng thái bộ thực thi"
    assert state["autopilot"]["enabled"] is True
    assert state["autopilot"]["on_blocks_done"] >= 1
    assert state["autopilot"]["alarm"] is None, "đang chạy đúng thì đừng báo động"
    assert state["pinned_product"] is not None

    # --- (b) bộ thực thi tắt: phải BÁO ĐỘNG, không được im lặng ---------
    monkeypatch.setenv("LIVELIFT_AUTOPILOT", "0")
    sid2, blocks2 = _live_auto_session(client, store, seed_arm="ON")
    qua_hai_khoi = blocks2[2]["start_offset_s"] + 30
    with _session_clock_at(store, sid2, qua_hai_khoi):
        state2 = client.get(f"/sessions/{sid2}/state").json()

    assert not store.list_exposure_events(sid2)
    auto = state2["autopilot"]
    assert auto is not None
    assert auto["enabled"] is False
    assert auto["alarm"], (
        "phiên TỰ ĐỘNG đã trôi qua khối BẬT mà không ghim gì thì phải báo động — "
        "im lặng chính là lỗi đã xảy ra ngày 11/09"
    )
    assert "BÁO ĐỘNG" in auto["alarm"]
    assert auto["missed_on_blocks"], "các khối BẬT đã trôi qua phải được gọi tên"

    # Báo động là việc của bàn điều khiển; màn hình người dẫn tuyệt đối không thấy.
    host = client.get(f"/sessions/{sid2}/state", params={"role": "host"})
    assert "autopilot" not in host.json()
    assert "BÁO ĐỘNG" not in host.text


# ===========================================================================
# CASE 8 — "Người dẫn không được biết gì"
# ===========================================================================

HOST_FIELDS = {"pinned_product", "price", "stock", "elapsed_s"}

#: Những từ mà chỉ cần xuất hiện trên màn hình người dẫn là giao thức làm mù đã
#: hỏng — và hỏng thì KHÔNG sửa được sau khi phiên đã chạy.
FORBIDDEN_ON_HOST = (
    "assignment",
    "block",
    "current_block",
    "seconds_remaining",
    "phase",
    "propensity",
    "seed",
    "design_hash",
    "cards",
    "autopilot",
    "mode",
)


def test_case_8_the_host_screen_never_reveals_the_arm_not_even_mid_on_block(client, store):
    """Case 8 — "Người dẫn nhìn màn hình của mình suốt phiên và không đoán ra gì".

    Người dẫn hào hứng hơn ở khối BẬT là nhiễu trực tiếp vào chính thứ đang đo
    (mo-hinh-van-hanh-kol.md §1.3, điều kiện 7). Nên màn hình `/host` chỉ được
    mang đúng 4 trường — và phải đúng ở mọi thời điểm, kể cả **giữa một khối BẬT
    vừa được ghim**, là lúc dễ rò rỉ nhất.
    """
    run_sid, blocks = _live_auto_session(client, store, seed_arm="ON")
    on_block = blocks[0]
    off_block = next(b for b in blocks if b["assignment"] == "OFF")

    moments = [
        ("trước khi có gì xảy ra", on_block["start_offset_s"] + 5),
        ("giữa khối BẬT", on_block["start_offset_s"] + 120),
        ("giữa khối TẮT", off_block["start_offset_s"] + 120),
    ]
    # Ghim trong khối BẬT: từ đây trở đi màn hình host CÓ hiện tên sản phẩm —
    # đúng thiết kế — nhưng vẫn không được lộ nhánh gán.
    with _session_clock_at(store, run_sid, on_block["start_offset_s"] + 60):
        assert client.post(f"/sessions/{run_sid}/actions/execute", json={}).status_code == 200

    for ten_thoi_diem, offset in moments:
        with _session_clock_at(store, run_sid, offset):
            r = client.get(f"/sessions/{run_sid}/state", params={"role": "host"})
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == HOST_FIELDS, (
            f"màn hình người dẫn ({ten_thoi_diem}) có thừa/thiếu trường: {sorted(body)}"
        )
        for tu in FORBIDDEN_ON_HOST:
            assert f'"{tu}"' not in r.text, f"lộ {tu!r} trên màn hình người dẫn ({ten_thoi_diem})"
        assert '"ON"' not in r.text, f"lộ nhánh gán ({ten_thoi_diem})"
        assert '"OFF"' not in r.text, f"lộ nhánh gán ({ten_thoi_diem})"

    # Sau khi kết thúc cũng vậy.
    assert client.post(f"/sessions/{run_sid}/end").status_code == 200
    r = client.get(f"/sessions/{run_sid}/state", params={"role": "host"})
    assert set(r.json().keys()) == HOST_FIELDS


# ===========================================================================
# CASE 9 — "Bấm vào sản phẩm vừa tạo"
# ===========================================================================


def test_case_9_pinning_a_product_you_just_created_is_answered_truthfully(client, store):
    """Case 9 (chốt lỗi 4) — "Tôi vừa nhập hàng xong, bấm ghim thì bị bảo là hết hàng".

    Kho có 11 sản phẩm nhưng bàn chỉ gợi ý 3 thẻ. Chủ shop ghim một sản phẩm
    vừa tạo, còn nguyên 50 cái trong kho → **409**, kèm thông báo nói sai sự
    thật ("đã hết hàng hoặc danh sách gợi ý vừa thay đổi") và khuyên "chờ thẻ
    mới rồi thử lại" — thẻ sẽ không bao giờ đổi thành sản phẩm đó. Chính cái 409
    này kéo tuân thủ của phiên kiểm chứng xuống 25% thay vì 50%
    (kiem-chung-van-hanh.md §2.4b).

    Kỳ vọng: hoặc ghim được, hoặc từ chối bằng một lý do ĐÚNG SỰ THẬT.
    """
    sid, blocks = _live_auto_session(client, store, seed_arm="ON")
    # Kho có nhiều hàng hơn số thẻ bàn gợi ý (3) — đúng tình huống thật: 11 sản
    # phẩm trong kho, 3 thẻ trên màn hình.
    for hau_to in ("A", "B", "C", "D"):
        client.post(
            "/products",
            json={
                "product_id": f"KC-KHO-{hau_to}",
                "name": f"Hàng sẵn kho {hau_to}",
                "cost": 20000,
                "price": 89000,
                "stock": 25,
            },
        )
    r = client.post(
        "/products",
        json={
            "product_id": "ZZ-MOI-NHAP",
            "name": "Sáp thơm để xe hương cà phê",
            "cost": 15000,
            "price": 59000,
            "stock": 50,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["stock"] == 50

    the_goi_y = client.get(f"/sessions/{sid}/state").json()["cards"]
    assert "ZZ-MOI-NHAP" not in {c["product_id"] for c in the_goi_y}, (
        "kịch bản chỉ có nghĩa khi sản phẩm mới nằm NGOÀI ba thẻ gợi ý"
    )

    with _session_clock_at(store, sid, blocks[0]["start_offset_s"] + 60):
        r = client.post(f"/sessions/{sid}/actions/execute", json={"product_id": "ZZ-MOI-NHAP"})

    assert r.status_code < 500, r.text
    if r.status_code == 200:
        return  # ghim được sản phẩm của chính mình — kết thúc đẹp nhất

    detail = r.json()["detail"]
    assert "hết hàng" not in detail, (
        f"sản phẩm còn 50 cái trong kho mà thông báo bảo hết hàng: {detail!r}"
    )
    assert "Chờ thẻ mới rồi thử lại" not in detail, (
        "khuyên chờ là khuyên vô ích — danh sách gợi ý không bao giờ đổi thành "
        f"sản phẩm này: {detail!r}"
    )
    assert detail.strip(), "từ chối thì phải nói lý do thật"


# ===========================================================================
# CASE 10 — "Buổi live chat cực thưa / toàn chữ số"
# ===========================================================================

SPARSE_CHAT: list[tuple[float, str]] = [
    (float(90 + 190 * i), text)
    for i, text in enumerate(
        [
            "alo alo nghe rõ không mọi người",
            "hôm nay live gì vậy shop",
            "mình mới vào",
            "shop ơi",
            "đẹp đó",
            "bao nhiêu vậy",
            "hihi",
            "ủa",
            "còn hàng hong",
            "để mình suy nghĩ",
            "ok",
            "nghe rõ rồi",
            "shop nói to lên xíu",
            "mạng mình lag quá",
            "chốt cái này nha",
            "cảm ơn shop",
            "mai live nữa hong",
            "👍",
            "hehe",
            "bye shop",
            "mình out trước",
            "good night",
            "ngủ ngon mọi người",
        ]
    )
]

# Buổi đấu giá: khán giả chỉ gõ con số trả giá, không một câu tiếng Việt nào.
_BID_LADDER = [1, 2, 3, 5, 7, *range(10, 60, 5), *range(60, 200, 20), *range(200, 520, 40)]
AUCTION_CHAT: list[tuple[float, str]] = [
    (float(30 + 6 * i), str(gia)) for i, gia in enumerate(_BID_LADDER)
]


def test_case_10_a_nearly_silent_live_reports_an_honest_empty_state(client, monkeypatch):
    """Case 10a — "Buổi live 78 phút mà chỉ có 23 người nhắn".

    Rất nhiều buổi live thật như vậy (đo 10/09: 16 video vào được, chỉ 7 buổi
    đạt 100 bình luận, và **một buổi 715 phút có 0 bình luận**). Hệ thống không
    được vỡ, cũng không được nặn ra "khoảnh khắc" từ nhiễu: phải ra **trạng thái
    rỗng CÓ GIẢI THÍCH**.
    """
    job = _load_replay(
        client,
        monkeypatch,
        SPARSE_CHAT,
        title="Live tâm sự cuối tuần",
        duration_s=78 * 60,
        url="https://www.youtube.com/watch?v=1NMt8BChQrI",
    )
    assert job["n_comments"] == len(SPARSE_CHAT)
    sid = job["session_id"]

    bao_cao = client.get(f"/sessions/{sid}/bao-cao").json()
    assert bao_cao["loai_phien"] == "quan_sat"
    assert bao_cao["tong_quan"]["tong_binh_luan"] == len(SPARSE_CHAT)

    # Không nặn khoảnh khắc từ chuỗi thưa — và phải NÓI vì sao rỗng.
    assert bao_cao["khoanh_khac"] == [], "chat thưa như vậy không có spike nào đáng gọi tên"
    assert bao_cao["khoanh_khac_ghi_chu"], "rỗng thì phải giải thích vì sao rỗng"

    # Mỗi ô trống mang một lý do, không bao giờ là số 0 giả.
    thieu = bao_cao["tong_quan"]["thieu"]
    assert bao_cao["tong_quan"]["nguoi_xem"] is None
    assert thieu.get("nguoi_xem")
    assert bao_cao["tong_quan"]["luot_nhap_hop_le"] is None
    assert thieu.get("luot_nhap")
    assert bao_cao["ket_qua_thi_nghiem"] is None

    signals = client.get(f"/sessions/{sid}/signals").json()
    assert _capability(signals, "radar ý định")["status"] == "ok"
    for ten in ("thí nghiệm nhân quả", "tỷ lệ nhấp", "đối soát doanh thu"):
        cap = _capability(signals, ten)
        assert cap["status"] == "missing"
        assert cap["reason"], f"năng lực {ten!r} thiếu thì phải nói thiếu CÁI GÌ"


def test_case_10_an_all_numeric_auction_live_does_not_break_anything(client, monkeypatch):
    """Case 10b — "Buổi đấu giá: khán giả chỉ gõ toàn chữ số".

    Chat đấu giá là "1", "2", "250" — không câu nào là tiếng Việt. Bộ phân loại
    ý định, bộ lọc PII và báo cáo đều phải đi qua được, và tuyệt đối không được
    biến một chuỗi số thành câu nhân quả.
    """
    job = _load_replay(
        client,
        monkeypatch,
        AUCTION_CHAT,
        title="Đấu giá đá quý tối nay",
        duration_s=10 * 60,
        url="https://www.youtube.com/watch?v=47oGShxf80A",
    )
    assert job["n_comments"] == len(AUCTION_CHAT)
    sid = job["session_id"]

    comments = client.get(f"/sessions/{sid}/comments").json()
    assert len(comments) == len(AUCTION_CHAT)
    assert all(c["intent"] is not None for c in comments), (
        "mọi bình luận phải có nhãn (kể cả nhãn 'khác') — None là một lỗ hổng im lặng"
    )

    bao_cao = client.get(f"/sessions/{sid}/bao-cao").json()
    assert bao_cao["phan_bo_y_dinh"]["tong"] == len(AUCTION_CHAT)
    assert sum(bao_cao["phan_bo_y_dinh"]["dem_theo_nhan"].values()) == len(AUCTION_CHAT)
    assert bao_cao["ket_qua_thi_nghiem"] is None
    for cau in bao_cao["goi_y_chien_thuat"]:
        assert "quan sát, chưa kiểm chứng nhân quả" in cau, (
            f"không được suy diễn nhân quả từ một chuỗi chữ số: {cau!r}"
        )
    assert client.get(f"/sessions/{sid}/report").status_code == 200
    assert client.get(f"/sessions/{sid}/signals").status_code == 200
