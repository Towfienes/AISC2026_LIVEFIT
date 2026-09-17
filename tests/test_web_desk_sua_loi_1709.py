"""Bàn trợ live — bốn lỗi kiểm toán 17/09 (nhóm web-desk), bản CHẠY NHANH.

1. **P1 — bấm đúp vượt qua xác nhận "Kết thúc phiên"** (StatusBar.tsx). Hành vi
   trong trình duyệt thật nằm ở ``tests/test_web_desk_trinh_duyet.py`` (dấu
   ``slow``); tệp này giữ các bất biến mã nguồn + hàm thuần để bộ nhanh vẫn
   canh được bản sửa.
2. **P2 — đổi phiên lúc lệnh Thực hiện đang chạy** (useDesk.ts + desk/page.tsx):
   sản phẩm ghim, câu xác nhận bốc thăm và ô lỗi của phiên A không được hiện
   như thể thuộc về phiên B.
3. **P2 — ô NGƯỜI XEM "THIẾU nguồn" cạnh khung bộ thu đang in số người xem**:
   ma trận tín hiệu tải lại ngay khi bàn thấy nguồn mới có dữ liệu.
4. **P2 — thẻ hành động còn nút sống ngay sau khi kết thúc phiên**.

Hàm thuần được tách NGUYÊN VĂN khỏi mã nguồn và chạy bằng node (cùng cách
``tests/test_web_desk_v3.py``), cấp DỮ LIỆU THẬT của máy chủ (ma trận tín hiệu
trước/sau điểm đo đầu tiên, câu lý do thẻ rỗng của phiên đã đóng).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tests.test_web_desk_v3 import (
    DESK_PAGE,
    FORMAT_TS,
    STATUS_BAR,
    USE_DESK,
    _function_body,
    _live_session,
    _opening_tag,
    _products,
    code,
    extract,
    js,
    raw,
)

ROOT = Path(__file__).resolve().parents[1]
BROWSER_TEST = ROOT / "tests" / "test_web_desk_trinh_duyet.py"

PURE = [
    (FORMAT_TS, ["TZ", "numberFmt", "vndFmt", "timeFmt", "dateFmt"]),
    (FORMAT_TS, ["fmtNumber", "fmtVnd", "fmtPct", "fmtTimeHCM", "fmtDateHCM"]),
    (STATUS_BAR, ["onAirWhen", "sessionShortName", "CONFIRM_ARM_MS"]),
    (
        DESK_PAGE,
        [
            "alertForSession",
            "alertText",
            "CLOSED_CARDS_NOTE",
            "offeredCards",
            "cardsNoteFor",
            "feedsSeen",
            "FEED_SIGNAL",
            "matrixLagsFeeds",
            "MATRIX_POLL_MS",
            "MATRIX_POLL_FAST_MS",
            "matrixPollMs",
        ],
    ),
]


def node_eval(tmp_path: Path, expr: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("không có node — bỏ qua phần chạy thử hàm thuần")
    module = "\n\n".join(extract(raw(path), n) for path, names in PURE for n in names)
    script = tmp_path / "desk_fix_1709.mts"
    script.write_text(module + f"\nconsole.log(JSON.stringify({expr}));\n", encoding="utf-8")
    out = subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if out.returncode != 0 and "strip-types" in out.stderr and "bad option" in out.stderr:
        pytest.skip("node quá cũ, chưa bỏ được chú thích kiểu")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.fixture
def api():
    from fastapi.testclient import TestClient

    from livelift.api.main import create_app
    from livelift.api.store import InMemoryStore

    with TestClient(create_app(store=InMemoryStore())) as client:
        yield client


def _session(client, sid: str) -> dict:
    return next(s for s in client.get("/sessions").json() if s["session_id"] == sid)


# ===========================================================================
# 1. P1 — bấm đúp không vượt qua được bước xác nhận
# ===========================================================================
def test_p1_buoc_xac_nhan_co_khoa_thoi_gian_va_huy_dung_cho_nut_cu():
    bar = code(raw(STATUS_BAR))
    control = _function_body(bar, "EndSessionControl")
    confirm = control[control.index('role="group"') :]
    # Lớp THỜI GIAN: "Kết thúc ngay" khoá cho tới khi hết khoảng chưa nhận bấm.
    now_btn = confirm[confirm.rindex("<Button", 0, confirm.index("Kết thúc ngay")) :]
    assert "disabled={!armed}" in now_btn[: now_btn.index("Kết thúc ngay")]
    assert "if (!armed) return;" in now_btn[: now_btn.index("Kết thúc ngay")]
    assert "setTimeout(() => setArmed(true), CONFIRM_ARM_MS)" in control
    # Lớp HÌNH HỌC: "Huỷ" đứng CUỐI cụm (mép phải = chỗ nút cũ), rộng bằng nút
    # cũ nhờ nhãn bước một tàng hình, cặp nút không tách dòng.
    assert confirm.index("Kết thúc ngay") < confirm.index("Huỷ"), (
        "'Huỷ' phải đứng sau 'Kết thúc ngay' — mép phải là chỗ nút 'Kết thúc phiên' cũ"
    )
    assert 'className="invisible col-start-1 row-start-1"' in confirm
    assert "{END_LABEL}" in confirm[confirm.index("invisible") :][:120]
    pair = confirm[: confirm.index("Kết thúc ngay")]
    assert 'className="flex shrink-0 items-center gap-2"' in pair, "cặp nút không được tách dòng"
    assert "justify-end" in confirm[:200]
    cancel = confirm[confirm.rindex("<Button", 0, confirm.index("Huỷ")) : confirm.index("Huỷ")]
    assert "autoFocus" in cancel, "bước hai vẫn đặt focus vào lựa chọn AN TOÀN"


def test_p1_doi_phien_xoa_buoc_xac_nhan_va_cau_hoi_in_ten_phien():
    bar = code(raw(STATUS_BAR))
    render = _function_body(bar, "StatusBar")
    tag = _opening_tag(render, render.index("<EndSessionControl"))
    assert "key={sessionId" in tag, (
        "không có key theo phiên: bấm 'Kết thúc phiên' ở A rồi đổi sang B, bước xác nhận "
        "còn đó và 'Kết thúc ngay' kết thúc B"
    )
    assert "sessionName={session ? sessionShortName(session) : null}" in tag
    control = _function_body(bar, "EndSessionControl")
    assert "aria-label={sessionName ? `Xác nhận kết thúc ${sessionName}`" in control


def test_p1_khoang_khoa_dai_hon_nhap_dup_va_ten_phien_khong_bao_gio_la_uuid(api, tmp_path):
    _products(api)
    sid = _live_session(api, "ON")
    s = _session(api, sid)
    titled = dict(s, title="Live tối 17/09 — Son kem")
    untitled = dict(s, title="  ")
    unaired = dict(s, title=None, start_ts=None, status="planned")
    arm_ms, names = node_eval(
        tmp_path,
        f"[CONFIRM_ARM_MS, [{js(titled)}, {js(untitled)}, {js(unaired)}]"
        ".map((x) => sessionShortName(x))]",
    )
    # 500ms là ngưỡng nhấp đúp mặc định của Windows; quá 1 giây thì cú bấm có
    # chủ ý bị bỏ qua tới mức người vận hành tưởng nút hỏng.
    assert 500 < arm_ms <= 1000, arm_ms
    assert names[0] == "Live tối 17/09 — Son kem"
    assert re.fullmatch(r"Phiên lên sóng \d{2}:\d{2} \d{2}/\d{2}", names[1]), names[1]
    assert names[2] == "Phiên chưa đặt tên"
    for name in names:
        assert sid not in name, f"UUID lọt vào câu xác nhận: {name}"
        assert sid[:8] not in name, f"UUID lọt vào câu xác nhận: {name}"


def test_bo_test_trinh_duyet_khong_bao_gio_treo_bo_test_nhanh():
    """Tệp trình duyệt thật từng treo bộ test hơn 10 phút — canh cả ba chốt."""
    # Bỏ docstring đầu tệp: nó TRÍCH NGUYÊN VĂN lệnh evaluate từng gây treo.
    src = raw(BROWSER_TEST)
    src = src[src.index('"""', 3) + 3 :]
    assert re.search(r"(?m)^pytestmark = pytest\.mark\.slow$", src), (
        "test trình duyệt phải mang dấu slow để bộ nhanh -m 'not slow' bỏ qua"
    )
    assert "set_default_timeout(PW_TIMEOUT_MS)" in src
    assert "set_default_navigation_timeout(PW_TIMEOUT_MS)" in src
    for m in re.finditer(r"subprocess\.run\(", src):
        call = src[m.start() : src.index("\n    )", m.start())]
        assert "timeout=" in call, "mọi tiến trình con phải có hạn giờ"
    # evaluate CHỜ promise nó nhận được: gán promise đang treo làm giá trị trả về
    # là treo vĩnh viễn (nguyên nhân gốc).
    assert not re.search(r"evaluate\(\s*f?[\"']window\.pending\s*=", src)
    assert "context.close()" in src[src.index("def _page(") :][:1500]
    assert "finally:" in src[src.index("def browser(") :][:900]


# ===========================================================================
# 2. P2 — đổi phiên lúc lệnh Thực hiện đang chạy
# ===========================================================================
def test_p2_use_desk_khong_ghim_len_phien_vua_chuyen_sang():
    desk = code(raw(USE_DESK))
    assert "sessionIdRef.current = sessionId;" in desk
    execute = desk[
        desk.index("const execute = useCallback") : desk.index("const skip = useCallback")
    ]
    assert "const stillViewing = () => sessionIdRef.current === sentFor;" in execute
    after_await = execute[execute.index("await apiExecute(") :]
    pins = [m.start() for m in re.finditer(r"setPinned\(", after_await)]
    assert pins, "bàn phải hiện ngay sản phẩm máy chủ vừa ghim"
    for at in pins:
        line = after_await[after_await.rindex("\n", 0, at) : at]
        assert "stillViewing()" in line, f"setPinned sau await không kiểm tra phiên: {line!r}"
    reset = raw(USE_DESK)
    reset = reset[reset.index("// Reset per-session UI state on switch.") :]
    reset = reset[: reset.index("}, [sessionId]);")]
    assert "setPinned(null);" in reset, "sản phẩm ghim của phiên cũ phải rời hero khi đổi phiên"


def test_p2_trang_gan_xac_nhan_va_loi_theo_phien():
    page = code(raw(DESK_PAGE))
    run = page[page.index("const runCard") : page.index("const endSession")]
    assert "const sentFor = desk.sessionId;" in run
    assert "setNoticeFor(sentFor, text)" in run, "câu bốc thăm phải gắn vào phiên ĐÃ gửi lệnh"
    assert not re.search(r"\bsetNotice\(", page), "còn một ô xác nhận chung cho mọi phiên"
    assert "const notice = desk.sessionId ? (notices[desk.sessionId] ?? null) : null;" in page
    assert "useState<DeskAlert | null>(null)" in page
    for body in (run, page[page.index("const endSession = () =>") :][:1500]):
        assert "sessionId: sentFor," in body, "lỗi lệnh phải mang mã phiên của lệnh"
    tag = _opening_tag(page, page.index("<StatusBar"))
    assert "alert={alertText(alert, desk.sessionId)}" in tag
    assert "alert={alert}" not in tag


def test_p2_o_loi_tu_gan_ten_phien_khi_khong_con_xem_phien_do(tmp_path):
    alert = {
        "sessionId": "A",
        "sessionName": "Live tối 17/09 — Son kem",
        "message": "Không thực hiện được thẻ “Ghim Phấn phủ”: Khối TẮT. Thẻ đã được trả lại.",
    }
    same, other, back, empty = node_eval(
        tmp_path,
        f"[alertText({js(alert)}, 'A'), alertText({js(alert)}, 'B'),"
        f" alertText({js(alert)}, 'A'), alertText(null, 'A')]",
    )
    assert same == alert["message"], "đang xem đúng phiên thì giữ nguyên câu"
    assert other == (
        "Phiên “Live tối 17/09 — Son kem” (không phải phiên đang xem): " + alert["message"]
    )
    assert back == same, "quay lại phiên A thì câu lại là của phiên đang xem"
    assert empty is None


# ===========================================================================
# 3. P2 — ma trận tín hiệu không tụt lại sau khi bộ thu bắt đầu gửi số
# ===========================================================================
def test_p2_ma_tran_tai_lai_ngay_khi_diem_do_dau_tien_ve(api, tmp_path):
    _products(api)
    sid = _live_session(api, "ON")
    start = datetime.fromisoformat(_session(api, sid)["start_ts"].replace("Z", "+00:00"))
    before = api.get(f"/sessions/{sid}/signals").json()
    assert next(s for s in before["signals"] if s["name"] == "ticks")["status"] == "missing"
    tick = {"viewers": 82, "comment_rate": 0, "ts_utc": (start + timedelta(seconds=5)).isoformat()}
    assert api.post(f"/sessions/{sid}/ticks", json=tick).status_code == 200
    after = api.get(f"/sessions/{sid}/signals").json()
    assert next(s for s in after["signals"] if s["name"] == "ticks")["status"] != "missing"
    desk_ticks = [{"offset_s": 5, "viewers": 82, "click_count": 0}]

    got = node_eval(
        tmp_path,
        "(() => {"
        " const none = feedsSeen([], []);"
        f" const seen = feedsSeen({js(desk_ticks)}, []);"
        f" const before = {js(before)}; const after = {js(after)};"
        " return ["
        "  matrixLagsFeeds(before, none, seen),"
        "  matrixLagsFeeds(null, none, seen),"
        "  matrixLagsFeeds(after, seen, seen),"
        "  matrixLagsFeeds(before, none, none),"
        "  matrixPollMs(before, 'live'),"
        "  matrixPollMs(null, 'live'),"
        "  matrixPollMs(before, 'ended'),"
        "  MATRIX_POLL_MS,"
        " ];"
        "})()",
    )
    lag, lag_no_matrix, settled, nothing_new, fast, fast_null, ended_ms, slow_ms = got
    assert lag is True, "điểm đo đầu tiên về mà ma trận còn THIẾU nguồn ⇒ tải lại ngay"
    assert lag_no_matrix is True
    assert settled is False, "không có nguồn nào mới ⇒ không tải lại (không vòng lặp)"
    assert nothing_new is False
    assert fast == fast_null == 10000, "phiên đang phát còn thiếu nguồn: 10 giây, không 30"
    assert ended_ms == slow_ms == 30000


def test_p2_trang_goi_tai_lai_ma_tran_theo_nguon_moi():
    page = code(raw(DESK_PAGE))
    assert "if (matrixLagsFeeds(signalCov, prev, next)) pullMatrixRef.current?.();" in page
    assert "const feeds = feedsSeen(desk.ticks, desk.comments);" in page
    assert "matrixDelayRef.current = matrixPollMs(signalCov, sessionStatus);" in page
    assert "}, matrixDelayRef.current);" in page
    assert "setInterval(pullMatrix" not in page, "nhịp cố định 30 giây là gốc của lỗi"
    # Lần tải NGAY và lần tải theo nhịp có thể về lệch thứ tự.
    assert "if (cancelled || seq < covSeq) return;" in page


# ===========================================================================
# 4. P2 — phiên đã kết thúc không còn thẻ nào mời bấm
# ===========================================================================
def test_p2_phien_da_dong_khong_con_the_moi_bam(api, tmp_path):
    from livelift.api.cards import pin_cards_blocked_reason

    _products(api)
    sid = _live_session(api, "ON")
    live_cards = api.get(f"/sessions/{sid}/state").json()["cards"]
    assert api.post(f"/sessions/{sid}/end").status_code == 200
    ended_state = api.get(f"/sessions/{sid}/state").json()
    # Luật của máy chủ mà bàn áp SỚM (không chờ poll 5 giây): 0 thẻ + câu lý do.
    assert ended_state["cards"] == []
    assert ended_state["cards_note"] == pin_cards_blocked_reason("ended", False)

    cards = live_cards or [{"card_id": "card-1-P1", "product_id": "P1"}]
    got = node_eval(
        tmp_path,
        f"[offeredCards({js(cards)}, 'ended'), offeredCards({js(cards)}, 'cancelled'),"
        f" offeredCards({js(cards)}, 'live').length,"
        " cardsNoteFor(null, 'ended'), cardsNoteFor(null, 'cancelled'),"
        " cardsNoteFor(null, 'live'), cardsNoteFor('câu máy chủ', 'ended')]",
    )
    ended, cancelled, live_n, note_ended, note_cancelled, note_live, server_first = got
    assert ended == [], "thẻ của lần poll cũ không được còn nút sống"
    assert cancelled == []
    assert live_n == len(cards)
    assert note_ended == ended_state["cards_note"], "câu lý do phải NGUYÊN VĂN câu máy chủ"
    assert note_cancelled == pin_cards_blocked_reason("cancelled", False)
    assert note_live is None
    assert server_first == "câu máy chủ"


def test_p2_cot_hanh_dong_ve_tu_the_duoc_moi():
    page = code(raw(DESK_PAGE))
    assert "const cards = offeredCards(desk.cards, sessionStatus);" in page
    assert "const cardsNote = cardsNoteFor(desk.cardsNote, sessionStatus);" in page
    assert "desk.cards.map(" not in page
    assert "desk.cards.length" not in page
    column = page[page.index("{cards.length === 0 ? (") :]
    column = column[: column.index("</Card>")]
    assert "cardsNote ??" in column
    assert "desk.cardsNote" not in column
    assert "cards.map((c, i) => (" in column
