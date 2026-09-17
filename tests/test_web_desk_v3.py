"""Gói C — Bàn trợ live v3 (/desk): các cổng C1–C12.

Nguồn yêu cầu: báo cáo đánh giá UI 17/09/2026, mục "Luồng C/D" (ảnh f06, f08,
d01, d02, f12) và "Bàn 1920×1080" (ảnh d04). Hai loại kiểm tra:

- CHẠY THẬT các hàm thuần của bàn bằng node (tách nguyên văn khỏi mã nguồn,
  node ≥ 22 tự bỏ chú thích kiểu — cùng cách tests/test_web_wizard_v3.py), cấp
  cho chúng DỮ LIỆU THẬT của máy chủ: câu 409 của khối TẮT, phản hồi
  ``ExecuteOut`` khi máy chủ bốc thăm, thẻ khởi động lạnh, lịch khối, phiên.
- Đọc mã nguồn cho phần bố cục/JSX mà tsc không thấy (liếc 1 giây ở 1366×768,
  khoá nút theo khối, hero phiên đã kết thúc…).

Luật trung thực đi kèm: màn người dẫn không bao giờ dùng thẻ hành động hay đồng
hồ khối (không lộ BẬT/TẮT), không bịa số dự báo, nhãn dữ liệu mẫu bằng tiếng Việt.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SRC = WEB / "src"
DESK_PAGE = SRC / "app" / "desk" / "page.tsx"
USE_DESK = SRC / "lib" / "useDesk.ts"
FORMAT_TS = SRC / "lib" / "format.ts"
ACTION_CARD = SRC / "components" / "ActionCard.tsx"
BLOCK_CLOCK = SRC / "components" / "BlockClock.tsx"
STATUS_BAR = SRC / "components" / "StatusBar.tsx"
SIGNAL_TILES = SRC / "components" / "SignalTiles.tsx"
TYPES_TS = SRC / "lib" / "types.ts"
API_TS = SRC / "lib" / "api.ts"
INGEST_PANEL = SRC / "components" / "IngestPanel.tsx"
HOST_VIEW = SRC / "components" / "HostView.tsx"

DESK_RENDER_PATH = [
    DESK_PAGE,
    ACTION_CARD,
    BLOCK_CLOCK,
    STATUS_BAR,
    SIGNAL_TILES,
    SRC / "components" / "BlockStrip.tsx",
    SRC / "components" / "CommentFeed.tsx",
    SRC / "components" / "CommentRadar.tsx",
]


def raw(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def code(src: str) -> str:
    """Mã nguồn đã bỏ chú thích — chú thích trích nguyên văn chính các mẫu bị cấm."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


def _opening_tag(src: str, start: int) -> str:
    depth = 0
    for j in range(start, len(src)):
        ch = src[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == ">" and depth == 0:
            return src[start : j + 1]
    return src[start:]


def _function_body(src: str, name: str) -> str:
    """Thân một hàm cấp cao nhất (tới dòng `}` ở cột 0)."""
    m = re.search(rf"(?m)^(?:export )?(?:default )?function {name}\b", src)
    assert m, f"không tìm thấy hàm {name}"
    end = src.index("\n}\n", m.start())
    return src[m.start() : end + 2]


# ---------------------------------------------------------------------------
# chạy hàm thuần bằng node
# ---------------------------------------------------------------------------
def extract(src: str, name: str) -> str:
    """Tách nguyên văn một khai báo cấp cao nhất (function/class/const)."""
    lines = src.replace("\r\n", "\n").split("\n")
    head = re.compile(rf"^(?:export )?(?:(?:async )?function|class|const) {re.escape(name)}\b")
    for i, line in enumerate(lines):
        if not head.match(line):
            continue
        is_const = re.match(r"^(?:export )?const ", line) is not None
        if is_const and line.rstrip().endswith(";"):
            return line
        for j in range(i + 1, len(lines)):
            end = lines[j].rstrip()
            if is_const and end and not end[0].isspace() and end.endswith(";"):
                return "\n".join(lines[i : j + 1])
            if not is_const and end == "}":
                return "\n".join(lines[i : j + 1])
        break
    raise AssertionError(f"không tách được khai báo {name}")


PURE = [
    (FORMAT_TS, ["TZ", "numberFmt", "vndFmt", "timeFmt", "dateFmt"]),
    (FORMAT_TS, ["fmtNumber", "fmtVnd", "fmtPct", "fmtTimeHCM", "fmtDateHCM"]),
    (TYPES_TS, ["CHART"]),
    (API_TS, ["sanitizeCard", "sanitizeCards"]),
    (
        USE_DESK,
        [
            "DeskCommandError",
            "isNetworkError",
            "toCommandError",
            "readExecuteOutcome",
            "executeNotice",
        ],
    ),
    (
        DESK_PAGE,
        [
            "clicksObservedFrom",
            "reportHrefFor",
            "sentence",
            "commandAlert",
            "allowsSimulatedSource",
        ],
    ),
    (
        ACTION_CARD,
        [
            "PRIMARY_VERB",
            "NO_FORECAST_BASIS",
            "FORECAST_RANK_NOTE",
            "forecastLacksData",
            "estimateDisplay",
            "viRationale",
        ],
    ),
    (
        SIGNAL_TILES,
        # COMMENTS_FIX kéo theo BUY_INTENTS: extract() đọc tới dòng `;` kế tiếp ở cột 0
        ["LOADING_HINT", "COMMENTS_FIX", "fmtRate", "tailDelta", "buildSignalTiles"],
    ),
    (BLOCK_CLOCK, ["deriveCurrentBlock", "blockShape", "actionLockReason"]),
    (STATUS_BAR, ["STATUS_VI", "PLATFORM_VI", "sessionOptionLabel"]),
]


def node_eval(tmp_path: Path, expr: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("không có node — bỏ qua phần chạy thử hàm thuần")
    module = "\n\n".join(extract(raw(path), n) for path, names in PURE for n in names)
    script = tmp_path / "desk_pure.mts"
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


def js(value) -> str:
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------------------
# máy chủ THẬT (kho trong bộ nhớ)
# ---------------------------------------------------------------------------
@pytest.fixture
def api():
    from fastapi.testclient import TestClient

    from livelift.api.main import create_app
    from livelift.api.store import InMemoryStore

    with TestClient(create_app(store=InMemoryStore())) as client:
        yield client


def _products(client, n: int = 3) -> None:
    for i in range(1, n + 1):
        r = client.post(
            "/products",
            json={
                "product_id": f"P{i}",
                "name": f"Bình giữ nhiệt {i}",
                "category": "gia-dung",
                "cost": 20000,
                "price": 53000 + i * 1000,
                "stock": 1200,
            },
        )
        assert r.status_code == 200, r.text


def _live_session(client, first: str) -> str:
    """Phiên đang phát có khối ĐẦU TIÊN là `first` ("ON"/"OFF")."""
    r = client.post(
        "/sessions",
        json={"platform": "youtube", "mode": "suggest", "planned_duration_min": 60},
    )
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]
    for seed in range(80):
        blocks = client.post(f"/sessions/{sid}/schedule", json={"seed": seed}).json()["blocks"]
        head = next(b for b in blocks if not b["is_washout"])
        if head["start_offset_s"] == 0 and head["assignment"] == first:
            break
    else:  # pragma: no cover - lịch luôn có cả hai kiểu khối đầu trong 80 seed
        pytest.fail(f"không tìm được seed có khối đầu {first}")
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    return sid


def _run_card_strings() -> tuple[str, str, str]:
    """Ba câu mà runCard của trang truyền cho commandAlert — đọc nguyên văn."""
    src = code(raw(DESK_PAGE))
    m = re.search(
        r"commandAlert\(\s*`(Không thực hiện được thẻ[^`]*)`,\s*e,"
        r"\s*\"([^\"]*)\",\s*\"([^\"]*)\",?\s*\)",
        src,
    )
    assert m, "runCard không còn gọi commandAlert(lead, e, ifNetwork, otherwise)"
    lead = m.group(1).replace("${card.headline}", "Ghim Bình giữ nhiệt 2")
    return lead, m.group(2), m.group(3)


# ===========================================================================
# C1 — lỗi 409 giữ NGUYÊN câu máy chủ; chỉ lỗi mạng mới nói "kiểm tra kết nối"
# ===========================================================================
def test_c1_409_khoi_tat_hien_nguyen_cau_may_chu(api, tmp_path):
    _products(api)
    sid = _live_session(api, "OFF")
    r = api.post(
        f"/sessions/{sid}/actions/execute", json={"card_id": "card-1-P2", "product_id": "P2"}
    )
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail.startswith("Khối TẮT")

    lead, if_network, otherwise = _run_card_strings()
    assert "kiểm tra kết nối" in if_network.lower()
    assert "kiểm tra kết nối" not in otherwise.lower(), (
        "câu dành cho từ chối nghiệp vụ không được dặn kiểm tra kết nối"
    )

    # request() của api.ts ném Error(detail) — đúng đường đó ở đây.
    got = node_eval(
        tmp_path,
        f"""(() => {{
          const e = toCommandError(new Error({js(detail)}), "Máy chủ không nhận lệnh ghim.");
          const alert = commandAlert({js(lead)}, e, {js(if_network)}, {js(otherwise)});
          return [e.network, e.message, alert];
        }})()""",
    )
    network, message, alert = got
    assert network is False
    assert message == detail, "câu 409 của máy chủ phải được giữ NGUYÊN VĂN"
    assert detail in alert
    assert "kiểm tra kết nối" not in alert.lower(), alert
    assert "trả lại danh sách" in alert


def test_c1_chi_loi_mang_that_moi_noi_kiem_tra_ket_noi(tmp_path):
    lead, if_network, otherwise = _run_card_strings()
    got = node_eval(
        tmp_path,
        f"""[
          new TypeError("Failed to fetch"),
          new DOMException("The operation was aborted.", "AbortError"),
          new Error("API 500 Internal Server Error — /sessions/x/actions/execute"),
          new Error(""),
        ].map((err) => {{
          const e = toCommandError(err, "Máy chủ không nhận lệnh ghim.");
          const alert = commandAlert({js(lead)}, e, {js(if_network)}, {js(otherwise)});
          return [e.network, e.message, alert];
        }})""",
    )
    (net1, _, alert1), (net2, _, alert2), (net3, msg3, alert3), (net4, msg4, _) = got
    assert net1 is True
    assert "kiểm tra kết nối" in alert1.lower()
    assert net2 is True
    assert "kiểm tra kết nối" in alert2.lower()
    # Máy chủ trả mã lỗi không kèm câu tiếng Việt: vẫn là TỪ CHỐI, không phải mất mạng.
    assert net3 is False
    assert "kiểm tra kết nối" not in alert3.lower()
    assert "Máy chủ không nhận lệnh ghim." in msg3
    assert net4 is False
    assert msg4 == "Máy chủ không nhận lệnh ghim."


def test_c1_use_desk_khong_nuot_cau_may_chu():
    src = code(raw(USE_DESK))
    body = src[src.index("const execute = useCallback") : src.index("const skip = useCallback")]
    assert "throw toCommandError(" in body, "execute phải ném lỗi giữ câu máy chủ"
    assert "kiểm tra kết nối API" not in src, "câu cố định 'kiểm tra kết nối API' đã quay lại"
    end = src[src.index("const endSession = useCallback") :]
    assert "throw toCommandError(" in end[:900], "Kết thúc phiên cũng phải giữ câu máy chủ"


# ===========================================================================
# C2 — khối TẮT/trôi ⇒ khoá nút, lý do ngắn có HÌNH + CHỮ
# ===========================================================================
def test_c2_khoa_nut_theo_lich_that(api, tmp_path):
    _products(api)
    sid = _live_session(api, "OFF")
    blocks = api.get(f"/sessions/{sid}/schedule").json()
    off = next(b for b in blocks if not b["is_washout"] and b["assignment"] == "OFF")
    on = next(b for b in blocks if not b["is_washout"] and b["assignment"] == "ON")
    washout = dict(off, is_washout=True, assignment=None)
    last_end = max(b["end_offset_s"] for b in blocks)
    got = node_eval(
        tmp_path,
        f"""(() => {{
          const blocks = {js(blocks)};
          const at = (bs, s) => actionLockReason(deriveCurrentBlock(bs, null, s), bs.length > 0);
          return [
            at(blocks, {off["start_offset_s"] + 1}),
            at(blocks, {on["start_offset_s"] + 1}),
            at([{js(washout)}], {off["start_offset_s"] + 1}),
            at(blocks, {last_end + 60}),
            actionLockReason(null, false),
          ];
        }})()""",
    )
    in_off, in_on, in_washout, outside, unknown = got
    assert in_off == {"shape": "off", "text": "Khối TẮT — vận hành như thường lệ"}
    assert in_on is None, "khối BẬT phải để nút mở"
    assert in_washout is not None
    assert in_washout["shape"] == "drift"
    assert outside is not None, "ngoài khung khối máy chủ cũng trả 409"
    assert unknown is None, "chưa biết lịch thì không đoán mà khoá"


def test_c2_the_bi_khoa_thay_nut_bang_ly_do():
    card = code(raw(ACTION_CARD))
    body = _function_body(card, "ActionCard")
    i_lock = body.index("<LockNote")
    assert i_lock < body.index("<AutoCountdown") < body.index("onClick={onExecute}"), (
        "nhánh khoá phải đứng TRƯỚC nút Thực hiện — khối TẮT không còn nút bấm được"
    )
    lock = _function_body(card, "LockNote")
    assert "<StatusMark" in lock, "lý do khoá phải có HÌNH + CHỮ"
    assert "lock.text" in lock, "lý do khoá phải có HÌNH + CHỮ"

    page = code(raw(DESK_PAGE))
    tag = _opening_tag(page, page.index("<ActionCard"))
    assert "locked={cardLock}" in tag
    assert "actionLockReason(" in page


def test_c2_man_nguoi_dan_khong_dung_the_hanh_dong_hay_dong_ho_khoi():
    host = code(raw(HOST_VIEW))
    for name in ("ActionCard", "BlockClock", "actionLockReason", "BlockStrip"):
        assert name not in host, f"màn người dẫn không được dùng {name} (lộ BẬT/TẮT)"


# ===========================================================================
# C3 — máy chủ bốc thăm: đọc ExecuteOut và nói rõ đã ghim gì
# ===========================================================================
def test_c3_boc_tham_that_cua_may_chu_duoc_noi_ro(api, tmp_path):
    _products(api)
    sid = _live_session(api, "ON")
    state = api.get(f"/sessions/{sid}/state").json()
    cards = state["cards"]
    assert len(cards) == 3
    card = next(c for c in cards if c["product_id"] == "P2")
    r = api.post(
        f"/sessions/{sid}/actions/execute",
        json={"card_id": card["card_id"], "product_id": card["product_id"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Khởi động lạnh: ba sản phẩm ngang nhau ⇒ máy chủ bốc thăm trong cả ba.
    assert body["randomized"] is True
    assert len(body["overlap_set"]) == 3
    names = {c["product_id"]: c["product_name"] for c in cards}

    got = node_eval(
        tmp_path,
        f"""(() => {{
          const names = {js(names)};
          const o = readExecuteOutcome({js(card)}, {js(body)}, (pid) => names[pid] ?? pid);
          return [o, executeNotice(o)];
        }})()""",
    )
    outcome, notice = got
    assert outcome["pinnedProductId"] == body["product_id"]
    assert outcome["randomized"] is True
    assert outcome["poolSize"] == 3
    pinned_name = names[body["product_id"]]
    assert notice.startswith(
        f"Hệ thống bốc thăm công bằng giữa 3 sản phẩm ngang nhau, đã ghim: {pinned_name}"
    ), notice
    if body["product_id"] != card["product_id"]:
        assert card["product_name"] in notice, "ghim khác thẻ thì phải nói thẻ vừa bấm là gì"
    assert "không cần ghim tay lại" in notice


def test_c3_khong_boc_tham_thi_im_lang_khac_the_thi_noi(tmp_path):
    card = {"product_id": "P1", "product_name": "Bình giữ nhiệt 1"}
    got = node_eval(
        tmp_path,
        f"""(() => {{
          const card = {js(card)};
          const nameOf = (pid) => (pid === "P9" ? "Sáp thơm" : pid);
          const plain = (pid) => ({{ product_id: pid, randomized: false, overlap_set: [pid] }});
          return [
            executeNotice(readExecuteOutcome(card, plain("P1"), nameOf)),
            executeNotice(readExecuteOutcome(card, plain("P9"), nameOf)),
            executeNotice(readExecuteOutcome(card, {{ ok: true }}, nameOf)),
            executeNotice(readExecuteOutcome(card, null, nameOf)),
          ];
        }})()""",
    )
    same, differs, old_server, empty = got
    assert same is None, "ghim đúng thẻ, không bốc thăm: không có gì bất ngờ để báo"
    assert differs is not None
    assert "Sáp thơm" in differs
    assert "Bình giữ nhiệt 1" in differs
    assert old_server is None, "máy chủ cũ không gửi trường: không đoán"
    assert empty is None, "máy chủ cũ không gửi trường: không đoán"


def test_c3_ban_doc_phan_hoi_va_hien_xac_nhan_canh_the():
    desk = code(raw(USE_DESK))
    assert re.search(r"raw\s*=\s*await\s+apiExecute\(", desk), "phản hồi execute bị vứt đi"
    assert "readExecuteOutcome(card, raw" in desk
    page = code(raw(DESK_PAGE))
    run = page[page.index("const runCard") : page.index("const endSession")]
    assert "executeNotice(outcome)" in run
    notice = page[page.index("{notice ?") :][:900]
    assert 'role="status"' in notice, "xác nhận bốc thăm phải được trình đọc màn hình đọc"
    assert "ⓘ" in notice, "xác nhận có HÌNH + CHỮ"


# ===========================================================================
# C4 — phiên kết thúc sớm giữa khối: ĐÃ KẾT THÚC + Xem báo cáo phiên
# ===========================================================================
def test_c4_hero_da_ket_thuc_thang_moi_trang_thai_khoi():
    src = code(raw(BLOCK_CLOCK))
    assert re.search(r"const view = sessionEnded \? null : liveView", src), (
        "kết thúc sớm giữa khối BẬT vẫn phải coi như không còn khối nào chạy"
    )
    assert re.search(r'const heroWord = sessionEnded \? "ĐÃ KẾT THÚC"', src)
    assert re.search(r"const hideCountdown = sessionEnded \|\|", src), (
        "phiên đã đóng không được còn 'Chuyển khối sau …'"
    )
    link = _opening_tag(src, src.index("<Link href={reportHref}"))
    assert 'buttonCls("primary")' in link, "nút báo cáo phải NỔI BẬT (nút chính)"
    assert "Xem báo cáo phiên" in src[src.index("<Link href={reportHref}") :][:300]

    page = code(raw(DESK_PAGE))
    tag = _opening_tag(page, page.index("<BlockClock"))
    assert "sessionEnded={sessionEnded}" in tag
    assert "reportHref={reportHref}" in tag
    assert "const reportHref = reportHrefFor(desk.connection, desk.sessionId)" in page


def test_c4_ban_xem_thu_khong_moi_mo_bao_cao_khong_ton_tai(tmp_path):
    """Phản biện: phiên mẫu 'mock-ended-01' hiện nút chính 'Xem báo cáo phiên'
    dẫn tới /bao-cao/mock-ended-01 — trang đó chỉ đọc máy chủ nên luôn lỗi."""
    got = node_eval(
        tmp_path,
        """[
          reportHrefFor("mock", "mock-ended-01"),
          reportHrefFor("connecting", "abc"),
          reportHrefFor("live", null),
          reportHrefFor("live", "abc"),
        ]""",
    )
    assert got == [None, None, None, "/bao-cao/abc"]
    # Trang /bao-cao không có nhánh dữ liệu mẫu — lý do bản xem thử không có link.
    assert "mock" not in code(raw(SRC / "app" / "bao-cao" / "[id]" / "page.tsx"))

    page = code(raw(DESK_PAGE))
    # Mọi link báo cáo trên bàn đi qua CÙNG điều kiện (hero + đầu cột tín hiệu).
    assert page.count("/bao-cao/") == 1, "đường /bao-cao/ phải chỉ dựng trong reportHrefFor"
    tiles = page[page.index("<SignalTiles") :][:600]
    assert re.search(r"meta=\{\s*reportHref \?", tiles), (
        "link 'Báo cáo phiên →' ở cột tín hiệu phải theo cùng điều kiện với hero"
    )
    # Không có link thì hero không được hứa "kết luận nằm trong báo cáo".
    clock = code(raw(BLOCK_CLOCK))
    sub = clock[clock.index("const heroSub = sessionEnded") :][:400]
    assert re.search(r"\?\s*!reportHref\s*\?", sub), sub


def test_c4_ket_thuc_phien_live_duy_nhat_khong_hat_ve_trang_rong():
    page = code(raw(DESK_PAGE))
    assert re.search(r"const showEmpty = nothingToShow && !\(deskShown", page), (
        "kết thúc phiên live duy nhất từng đổi bàn thành 'Chưa có phiên nào đang chạy' — "
        "mất luôn hero ĐÃ KẾT THÚC và nút Xem báo cáo phiên"
    )
    assert "setDeskShown(true)" in page


def test_c4_trang_thai_phien_theo_ca_poll_khong_chi_websocket():
    src = code(raw(USE_DESK))
    pull = src[src.index("const pull = async") : src.index("pull();")]
    assert "st.status" in pull, (
        "socket đang nối lại lúc phiên kết thúc thì bàn không bao giờ biết phiên đã đóng"
    )
    assert "setSessions(" in pull, (
        "socket đang nối lại lúc phiên kết thúc thì bàn không bao giờ biết phiên đã đóng"
    )


# ===========================================================================
# C5 — liếc 1 giây ở 1366×768: nút của thẻ #1 trong màn đầu tiên
# ===========================================================================
def test_c5_dau_trang_gon_khi_dang_phat():
    page = code(raw(DESK_PAGE))
    header = _opening_tag(page, page.index("<PageHeader"))
    assert 'size="sm"' in header
    assert re.search(r"lead=\{\s*onAir\s*\?\s*undefined", header), (
        "câu dẫn của PageHeader phải ẩn khi phiên đang phát"
    )


def test_c5_the_lich_cao_vua_noi_dung_va_hero_hai_cot():
    src = code(raw(BLOCK_CLOCK))
    section = _opening_tag(
        src, src.rindex("<section", 0, src.index('aria-label="Đồng hồ vận hành"'))
    )
    assert "items-start" in section, "thẻ LỊCH BẬT/TẮT bị kéo cao bằng thẻ khối (~285px)"
    assert re.search(r"sm:grid-cols-\[minmax\(0,1fr\)_auto\]", src), (
        "chữ trạng thái và đếm ngược phải đứng CẠNH nhau, không chồng thành một cột cao"
    )
    schedule = src[src.index("Lịch BẬT / TẮT") - 700 : src.index("Lịch BẬT / TẮT")]
    card = schedule[schedule.rindex("<Card") :]
    assert not re.search(r"\b(h-full|flex-1|self-stretch)\b", card)


def test_c5_status_bar_mot_dong_va_ket_thuc_tach_khoi_cong_tac():
    src = code(raw(STATUS_BAR))
    body = _function_body(src, "StatusBar")
    # Không còn nhãn chữ nhìn thấy trước ô chọn (chỉ aria-label).
    assert not re.search(r">\s*Phiên đang xem", body), "nhãn chữ 'Phiên đang xem' ăn ~110px"
    select = _opening_tag(body, body.index("<select"))
    width = re.search(r"max-w-\[(\d+)rem\]", select)
    assert width, "ô chọn phiên quá rộng cho một dòng ở 1366"
    assert int(width.group(1)) <= 18, "ô chọn phiên quá rộng cho một dòng ở 1366"
    assert "designHash" not in body, "mã thiết kế đã chuyển xuống thẻ lịch (C10)"

    i_mode = body.index("<ModeToggle")
    i_end = body.index("<EndSessionControl")
    assert i_mode < i_end
    wrapper = body[body.rindex("<div", 0, i_end) : i_end]
    assert "ml-auto" in wrapper, (
        "Kết thúc phiên phải đứng riêng ở mép phải, sau vạch ngăn — xa công tắc Gợi ý/Tự động"
    )
    assert "border-l" in wrapper, (
        "Kết thúc phiên phải đứng riêng ở mép phải, sau vạch ngăn — xa công tắc Gợi ý/Tự động"
    )


def test_c5_goi_y_cuon_khong_dung_mau_canh_bao():
    page = code(raw(DESK_PAGE))
    i = page.index("cuộn để xem hết")
    tag = page[page.rindex("<p", 0, i) : i]
    assert not re.search(r"warn|amber|orange|crit", tag), (
        "gợi ý cuộn là thông tin, không phải cảnh báo"
    )


# ===========================================================================
# C6 — số theo vi-VN, một động từ, không bịa "+100%"
# ===========================================================================
def test_c6_the_khoi_dong_lanh_that_ghi_chua_du_du_lieu(api, tmp_path):
    _products(api)
    sid = _live_session(api, "ON")
    cards = api.get(f"/sessions/{sid}/state").json()["cards"]
    assert {c["estimate"] for c in cards} == {1.0}, "dữ liệu thật: mọi thẻ khởi động lạnh bằng nhau"
    varied = [dict(c, estimate=e) for c, e in zip(cards, (0.8, 0.5, 0.2), strict=True)]
    experiment = dict(cards[0], source="experiment", ci_low=0.1, ci_high=0.3)
    got = node_eval(
        tmp_path,
        f"""(() => {{
          const cards = {js(cards)};
          const varied = {js(varied)};
          return [
            cards.map((c) => forecastLacksData(c, cards)),
            varied.map((c) => forecastLacksData(c, varied)),
            forecastLacksData(cards[0], [cards[0]]),
            forecastLacksData(cards[0], [cards[0]], {{ clicksObserved: false }}),
            forecastLacksData(varied[0], varied, {{ clicksObserved: null }}),
            forecastLacksData({js(experiment)}, [{js(experiment)}], {{ clicksObserved: false }}),
            NO_FORECAST_BASIS,
          ];
        }})()""",
    )
    cold, distinct, single_unknown, single_no_clicks, unknown, experiment_card, words = got
    assert cold == [True, True, True], "ba thẻ '+100%' giống hệt nhau là con số không mang tin"
    assert distinct == [False, False, False]
    assert single_unknown is False
    assert single_no_clicks is True, "phiên chưa có lượt bấm nào: dự báo chỉ là tiên nghiệm"
    assert unknown is False
    assert experiment_card is False, "thẻ thí nghiệm là phép đo, luôn có cơ sở"
    assert words == "chưa đủ dữ liệu để dự báo"


def test_c6_ly_do_cua_may_chu_theo_dinh_dang_vi_vn(api, tmp_path):
    _products(api)
    sid = _live_session(api, "ON")
    rationales = [c["rationale"] for c in api.get(f"/sessions/{sid}/state").json()["cards"]]
    assert any(re.search(r"\d,\d{3}đ", r) for r in rationales), "máy chủ in số kiểu Anh (53,000đ)"
    samples = [*rationales, "Còn 1,200 trong kho", "Giá 45.000 ₫ đã đúng", "Tặng 5 đồng xu"]
    got = node_eval(
        tmp_path, f"[{js(samples)}.map((t) => viRationale(t)), fmtVnd(34000), fmtNumber(1200)]"
    )
    out, vnd, num = got
    for before, after in zip(rationales, out[: len(rationales)], strict=True):
        money = re.search(r"(\d{1,3}(?:,\d{3})+)đ", before)
        assert money, before
        value = int(money.group(1).replace(",", ""))
        assert money.group(0) not in after
        assert after.count("₫") == 1, after
        assert f"{value:,}".replace(",", ".") in after, after
    assert vnd in out[0] or "₫" in out[0]
    assert out[-3] == f"Còn {num} trong kho"
    assert out[-2] == "Giá 45.000 ₫ đã đúng", "chuỗi đã đúng định dạng phải giữ nguyên"
    assert out[-1] == "Tặng 5 đồng xu", "'đồng' là chữ, không phải ký hiệu tiền"


def test_c6_mot_dong_tu_cho_nut_chinh_va_dung_ham_dinh_dang_chung():
    src = code(raw(ACTION_CARD))
    assert re.search(r"import \{[^}]*\bfmtVnd\b[^}]*\} from \"@/lib/format\"", src)
    assert re.search(r"import \{[^}]*\bfmtNumber\b[^}]*\} from \"@/lib/format\"", src)
    assert "Ghim ngay" not in src, "một hành động hai tên: 'Ghim ngay' và 'Thực hiện'"
    assert 'export const PRIMARY_VERB = "Thực hiện";' in src
    assert "{PRIMARY_VERB}" in src
    body = _function_body(src, "ActionCard")
    assert "const shown = noBasis ? null : estimateDisplay(card, peerCount)" in body, (
        "chưa có cơ sở dữ liệu thì câu 'chưa đủ dữ liệu' phải THAY con số"
    )
    assert body.index("<NoBasisNote") < body.index("shown.text"), (
        "chưa có cơ sở dữ liệu thì câu 'chưa đủ dữ liệu' phải THAY con số"
    )
    assert "fmtPct(card.estimate)" not in body, (
        "thẻ không được tự in phần trăm — mọi ước lượng đi qua estimateDisplay"
    )
    page = code(raw(DESK_PAGE))
    tag = _opening_tag(page, page.index("<ActionCard"))
    assert "noForecastBasis={forecastLacksData(" in tag
    assert "peerCount={desk.cards.length}" in tag


def _clicks_session(client) -> tuple[str, str]:
    """Phiên thật có Link đo: ghim P1 rồi P2 (mỗi sản phẩm 3 điểm đo), tạo link
    cho P1 nhưng CHƯA ai bấm. Trả (session_id, mã link)."""
    from datetime import datetime, timedelta

    _products(client)
    sid = _live_session(client, "ON")
    sess = next(s for s in client.get("/sessions").json() if s["session_id"] == sid)
    start = datetime.fromisoformat(sess["start_ts"].replace("Z", "+00:00"))

    def ticks(frm: int) -> None:
        for i in range(frm, frm + 3):
            r = client.post(
                f"/sessions/{sid}/ticks",
                json={
                    "viewers": 500,
                    "comment_rate": 3,
                    "ts_utc": (start + timedelta(seconds=30 * i + 1)).isoformat(),
                },
            )
            assert r.status_code == 200, r.text

    for pid, frm in (("P1", 0), ("P2", 3)):
        r = client.post(
            f"/sessions/{sid}/actions/override", json={"product_id": pid, "reason": "hết hàng"}
        )
        assert r.status_code == 200, r.text
        ticks(frm)
    r = client.post(
        "/shortlinks",
        json={"product_id": "P1", "session_id": sid, "target_url": "https://example.com"},
    )
    assert r.status_code == 200, r.text
    return sid, r.json()["code"]


def _click_link(client, code_: str, n: int, tag: str) -> None:
    """n lượt bấm từ n trình duyệt khác nhau (không bị gắn cờ bấm dồn)."""
    for k in range(n):
        client.get(
            f"/r/{code_}",
            follow_redirects=False,
            headers={
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    f"Chrome/120.{tag}.{k}"
                ),
                "x-forwarded-for": f"10.0.{tag}.{k}",
            },
        )


def test_c6_du_bao_doc_luot_bam_tu_ma_tran_khong_tu_tick(api, tmp_path):
    """Phản biện P1: `tick.click_count` máy chủ luôn lưu 0 cho phiên thật —
    suy 'đã có lượt bấm' từ tick làm mọi thẻ mãi ghi 'chưa đủ dữ liệu để dự báo'
    (và nhấp nháy mỗi khi WebSocket báo một lượt bấm)."""
    sid, link = _clicks_session(api)
    before = api.get(f"/sessions/{sid}/signals").json()
    _click_link(api, link, 8, "1")
    ticks = api.get(f"/sessions/{sid}/ticks").json()
    after = api.get(f"/sessions/{sid}/signals").json()
    cards = api.get(f"/sessions/{sid}/state").json()["cards"]

    # Từ 17/09/2026 máy chủ đếm lượt bấm HỢP LỆ theo mốc từ bảng click
    # (trước đó tick luôn mang 0 với phiên thật). Bàn vẫn đọc "đã quan sát lượt
    # bấm" từ ma trận tín hiệu — nguồn được kiểm định — không từ tick.
    assert ticks, "phiên phải có điểm đo"
    assert sum(t["click_count"] for t in ticks) >= 1, "tick phải mang lượt bấm hợp lệ thật"
    assert {s["name"]: s["status"] for s in after["signals"]}["clicks"] == "ok"
    assert {s["name"]: s["status"] for s in before["signals"]}["clicks"] == "degraded", (
        "có link mà chưa ai bấm là 'degraded'"
    )
    assert len({round(c["estimate"], 9) for c in cards}) > 1, "mô hình đã tách được sản phẩm"

    no_link = api.post(
        "/sessions", json={"platform": "youtube", "mode": "suggest", "planned_duration_min": 60}
    ).json()["session_id"]
    no_link_cov = api.get(f"/sessions/{no_link}/signals").json()
    got = node_eval(
        tmp_path,
        f"""(() => {{
          const cards = {js(cards)};
          const observed = clicksObservedFrom({js(after)});
          return [
            observed,
            clicksObservedFrom({js(before)}),
            clicksObservedFrom({js(no_link_cov)}),
            clicksObservedFrom(null),
            clicksObservedFrom({{ session_id: "x", signals: [], capabilities: [] }}),
            cards.map((c) => forecastLacksData(c, cards, {{ clicksObserved: observed }})),
          ];
        }})()""",
    )
    observed, link_no_click, no_link_state, no_matrix, no_row, lacks = got
    assert observed is True, "ma trận nói clicks=ok thì phiên ĐÃ có lượt bấm"
    assert link_no_click is False
    assert no_link_state is False
    assert no_matrix is None
    assert no_row is None
    assert lacks == [False, False, False], "đã có lượt bấm thật thì thẻ phải hiện dự báo"

    page = code(raw(DESK_PAGE))
    assert "const clicksObserved = clicksObservedFrom(signalCov)" in page
    assert "click_count" not in _function_body(page, "clicksObservedFrom")


def test_c6_suy_giam_vi_luot_bam_bi_gan_co_van_la_da_co_luot_bam(tmp_path):
    """`degraded` có hai nghĩa: có link mà chưa ai bấm (không có số thô) và có
    lượt bấm hợp lệ nhưng đa số bị gắn cờ (máy chủ kèm số thô `secondary`)."""
    from livelift.core.signals import _clicks_state

    thin = _clicks_state(2, 9, 1)
    empty = _clicks_state(0, 0, 1)
    assert thin.status == empty.status == "degraded"
    assert thin.secondary
    assert not empty.secondary

    def cov(state) -> dict:
        return {
            "session_id": "x",
            "signals": [
                {
                    "name": state.name,
                    "status": state.status,
                    "detail": state.detail,
                    "secondary": state.secondary,
                }
            ],
            "capabilities": [],
        }

    got = node_eval(
        tmp_path,
        f"[clicksObservedFrom({js(cov(thin))}), clicksObservedFrom({js(cov(empty))})]",
    )
    assert got == [True, False]


def test_c6_du_bao_khong_in_phan_tram_tang(api, tmp_path):
    """Phản biện P2: `estimate` của thẻ dự báo là lượt bấm / 1000 người-xem-giây
    (cards.build_candidates); fmtPct in 0,17 thành '+17%' màu xanh."""
    sid, link = _clicks_session(api)
    _click_link(api, link, 8, "2")
    # Thẻ đúng như bàn nhận: getCards → sanitizeCards (bù hạng theo thứ tự API).
    cards = node_eval(
        tmp_path, f"sanitizeCards({js(api.get(f'/sessions/{sid}/state').json()['cards'])})"
    )
    assert all(c["source"] == "forecast" for c in cards)
    assert all(0 < c["estimate"] < 1 for c in cards), [c["estimate"] for c in cards]
    no_estimate = dict(cards[0], estimate=None)
    experiment = dict(cards[0], source="experiment", estimate=0.18, ci_low=0.05, ci_high=0.31)
    negative = dict(experiment, estimate=-0.04)
    got = node_eval(
        tmp_path,
        f"""(() => {{
          const cards = {js(cards)};
          return [
            cards.map((c) => estimateDisplay(c, cards.length)),
            estimateDisplay(cards[0], 1),
            estimateDisplay(cards[1], null),
            estimateDisplay({js(no_estimate)}, 3),
            estimateDisplay({js(experiment)}, 3),
            estimateDisplay({js(negative)}, 3),
            FORECAST_RANK_NOTE,
          ];
        }})()""",
    )
    forecasts, single, unknown_of, missing, measured, measured_neg, note = got
    for card, shown in zip(cards, forecasts, strict=True):
        assert "%" not in shown["text"], shown
        assert shown["tone"] == "neutral", "thứ hạng dự báo không được tô xanh như tin tốt"
        assert shown["text"] == f"hạng {card['rank']}/{len(cards)} theo dự báo lượt bấm"
        assert shown["label"] == note
    assert "không phải % tăng" in note
    assert single["text"] == "gợi ý duy nhất theo dự báo lượt bấm"
    assert unknown_of["text"] == "hạng 2 theo dự báo lượt bấm", (
        "không biết mẫu số thì không nói 'duy nhất'"
    )
    assert missing is None
    assert measured == {"text": "+18%", "label": "tác động đo được", "tone": "good"}
    assert measured_neg["tone"] == "crit"


# ===========================================================================
# C7 — Bộ thu bình luận trên bàn, không đẩy thẻ hành động khỏi màn đầu
# ===========================================================================
def test_c7_bo_thu_binh_luan_dat_o_cot_giua_voi_du_prop():
    page = code(raw(DESK_PAGE))
    i = page.index("<IngestPanel")
    tag = _opening_tag(page, i)
    for prop in (
        "compact",
        "sessionId={",
        "sessionPlatform={",
        "sessionStatus={",
        "allowSimulated={",
    ):
        assert prop in tag, f"IngestPanel trên bàn thiếu {prop}"
    # Không nằm trong vùng dính đầu trang, không nằm trong cột hành động.
    assert i > page.index("<BlockClock"), "bộ thu trong vùng dính sẽ đẩy thẻ #1 xuống"
    column = page[page.rindex("<div", 0, page.rindex("{showIngest", 0, i)) : i]
    assert "xl:col-start-2" in column, "bộ thu phải ở đầu CỘT GIỮA"
    assert "xl:col-start-3" not in column

    helper = _function_body(page, "allowsSimulatedSource")
    assert "dry_run" in helper
    assert "is_demo" in helper
    assert "allowSimulated?: boolean" in code(raw(INGEST_PANEL)), (
        "IngestPanel chưa nhận allowSimulated"
    )


def test_c7_nguon_mo_phong_chi_cho_phien_chay_thu_hoac_du_lieu_mau(api, tmp_path):
    r = api.post(
        "/sessions",
        json={"platform": "youtube", "mode": "suggest", "planned_duration_min": 60},
    )
    real = r.json()
    assert real["dry_run"] is False
    assert real["is_demo"] is False
    dry = api.post(
        "/sessions",
        json={
            "platform": "youtube",
            "mode": "suggest",
            "planned_duration_min": 60,
            "dry_run": True,
        },
    ).json()
    assert dry["dry_run"] is True
    legacy = {k: v for k, v in real.items() if k != "dry_run"}
    got = node_eval(
        tmp_path,
        f"""[
          allowsSimulatedSource({js(real)}),
          allowsSimulatedSource({js(dry)}),
          allowsSimulatedSource({js(dict(real, is_demo=True))}),
          allowsSimulatedSource({js(legacy)}),
          allowsSimulatedSource(null),
        ]""",
    )
    assert got == [False, True, True, False, False]


def test_c7_o_binh_luan_thieu_nguon_chi_cach_bat_bo_thu():
    tiles = code(raw(SIGNAL_TILES))
    fix = re.search(r"export const COMMENTS_FIX =\s*\"([^\"]+)\"", tiles)
    assert fix, "ô Bình luận THIẾU nguồn phải có lối ra"
    assert "Bộ thu bình luận" in fix.group(1)
    button = re.search(r"“([^”]+)”\.?$", fix.group(1))
    assert button, fix.group(1)
    assert button.group(1) in raw(INGEST_PANEL), (
        f"câu hướng dẫn nhắc nút {button.group(1)!r} nhưng IngestPanel không có nút đó"
    )
    tile = _function_body(tiles, "Tile")
    assert "tile.fix" in tile
    comment = tiles[tiles.index('key: "comments"', tiles.index("commentsAbsent")) :][:900]
    assert "fix:" in comment, "bản xem thử không có bộ thu — không được mời bật"
    assert 'connection !== "live"' in comment, "bản xem thử không có bộ thu — không được mời bật"
    page = code(raw(DESK_PAGE))
    assert "Bộ thu bình luận" in page


def test_c7_o_binh_luan_khong_noi_chua_co_binh_luan_khi_binh_luan_dang_ve(api, tmp_path):
    """Phản biện P1: nguồn không gửi điểm đo nhịp (kênh YouTube ẩn số người xem)
    nhưng bình luận vẫn về — ô Bình luận từng báo 'chưa nhận được bình luận
    nào — bộ thu chưa bật' và mời bật lại một bộ thu đang chạy."""
    sid = _live_session(api, "ON")
    empty_signals = api.get(f"/sessions/{sid}/signals").json()
    for text in ("giá bao nhiêu vậy shop", "chốt đơn nha", "size M còn không"):
        r = api.post(f"/sessions/{sid}/comments", json={"text": text})
        assert r.status_code == 200, r.text
    signals = api.get(f"/sessions/{sid}/signals").json()
    assert {s["name"]: s["status"] for s in signals["signals"]}["comments"] == "ok"
    assert api.get(f"/sessions/{sid}/ticks").json() == [], "đường chạy này không có điểm đo nhịp"
    comments = [
        {
            "comment_id": c["comment_id"],
            "offset_s": 30 + i,
            "ts": c["ts"],
            "text_scrubbed": c["text"],
            "intent_label": c["intent"],
            "pii_kinds": c.get("pii_kinds") or [],
        }
        for i, c in enumerate(api.get(f"/sessions/{sid}/comments").json())
    ]
    assert len(comments) == 3

    got = node_eval(
        tmp_path,
        f"""(() => {{
          const tile = (signals, comments, ended, connection = "live") =>
            buildSignalTiles({{
              signals, connection, viewers: 0, ticks: [], clicksPerMin: null,
              reactionsTotal: null, comments, nowS: 60, ended,
            }}).find((t) => t.key === "comments");
          const pick = (t) => [t.state, t.reason ?? null, t.fix ?? null];
          return [
            pick(tile({js(signals)}, {js(comments)}, false)),
            pick(tile({js(signals)}, {js(comments)}, true)),
            pick(tile({js(signals)}, [], false)),
            pick(tile({js(empty_signals)}, {js(comments)}, false)),
            pick(tile({js(empty_signals)}, [], false)),
            pick(tile({js(empty_signals)}, [], true)),
            pick(tile(null, [], false, "mock")),
            COMMENTS_FIX,
          ];
        }})()""",
    )
    flowing, flowing_ended, server_has, stale_matrix, none_yet, none_ended, mock, fix = got
    for label, (state, reason, tip) in (
        ("bình luận đang về", flowing),
        ("phiên đã kết thúc có bình luận", flowing_ended),
        ("máy chủ có bình luận, bàn chưa tải", server_has),
        ("ma trận cũ, bình luận đã về", stale_matrix),
    ):
        assert state == "degraded", label
        assert "chưa nhận được bình luận nào" not in reason, label
        assert "không ghi được bình luận nào" not in reason, label
        assert "điểm đo nhịp" in reason, label
        assert tip is None, f"{label}: bộ thu đang chạy — không mời bật lại"
    assert none_yet[0] == "missing"
    assert "chưa nhận được bình luận nào" in none_yet[1]
    assert none_yet[2] == fix, "thật sự chưa có bình luận thì chỉ cách bật bộ thu"
    assert none_ended[1] == "phiên không ghi được bình luận nào"
    assert none_ended[2] is None
    assert mock[2] is None, "bản xem thử không có bộ thu — không mời bật"


# ===========================================================================
# C8–C12
# ===========================================================================
def test_c8_o_chon_phien_hien_ten_gio_khong_uuid(api, tmp_path):
    _products(api)
    sid = _live_session(api, "ON")
    session = next(s for s in api.get("/sessions").json() if s["session_id"] == sid)
    untitled = dict(session, title=None)
    unaired = dict(session, title=None, start_ts=None, status="planned")
    demo = dict(session, is_demo=True, status="ended")
    got = node_eval(
        tmp_path,
        f"[{js(session)}, {js(untitled)}, {js(unaired)}, {js(demo)}]"
        ".map((s) => sessionOptionLabel(s))",
    )
    titled, no_title, planned, demo_label = got
    for label in got:
        assert sid not in label, f"UUID lọt vào ô chọn phiên: {label}"
        assert sid[:8] not in label, f"UUID lọt vào ô chọn phiên: {label}"
    assert titled.startswith(session["title"])
    assert "YouTube" in titled
    assert "đang live" in titled
    assert re.match(r"^Phiên lên sóng \d{2}:\d{2} \d{2}/\d{2}", no_title), no_title
    assert planned.startswith("Phiên chưa đặt tên, chưa lên sóng")
    assert "mới lập" in planned
    assert "dữ liệu mẫu" in demo_label
    assert "đã kết thúc" in demo_label

    bar = code(raw(STATUS_BAR))
    option = bar[bar.index("<option") :][:200]
    assert "sessionOptionLabel(s)" in option


def test_c9_ket_thuc_phien_xac_nhan_hai_buoc_tai_cho():
    for path in (DESK_PAGE, STATUS_BAR):
        assert not re.search(r"\bconfirm\(", code(raw(path))), (
            f"{path.name}: còn hộp confirm trình duyệt"
        )
    bar = code(raw(STATUS_BAR))
    control = _function_body(bar, "EndSessionControl")
    assert "Kết thúc ngay" in control
    assert "Huỷ" in control
    cancel = control[control.rindex("<Button", 0, control.index("Huỷ")) : control.index("Huỷ")]
    assert "autoFocus" in cancel, "bước hai phải đặt focus vào lựa chọn AN TOÀN"
    assert "setTimeout" in control, "bước xác nhận phải tự huỷ"


def test_c10_khong_con_ma_tk():
    for path in DESK_RENDER_PATH:
        assert "Mã TK" not in code(raw(path)), f"{path.name}: còn viết tắt 'Mã TK'"
    assert "Mã bằng chứng lịch" in code(raw(BLOCK_CLOCK))


def test_c11_tu_dong_khong_co_nut_chet_va_kiem_tra_gan_nhat():
    card = code(raw(ACTION_CARD))
    auto = _function_body(card, "AutoCountdown")
    assert "<Button" not in auto
    assert "disabled" not in auto
    assert "auto_execute_in_s" in auto, "chế độ tự động phải có đếm ngược tới lúc tự ghim"
    assert "disabled" not in _function_body(card, "ActionCard"), "không còn nút xám bị vô hiệu"
    page = code(raw(DESK_PAGE))
    assert "Nhịp tim" not in page
    assert "Kiểm tra gần nhất" in page


def test_ban_trong_dung_thuat_ngu_thong_nhat():
    """Phản biện P2: trên cùng màn trống, câu dẫn nói 'dữ liệu mẫu' còn nút nói
    'dữ liệu mô phỏng'; nút phụ gọi bàn là 'bàn điều khiển'."""
    empty = _function_body(code(raw(DESK_PAGE)), "EmptyDesk")
    assert "Xem thử với dữ liệu mẫu" in empty
    assert "mô phỏng" not in empty
    assert "bàn điều khiển" not in empty.lower()
    assert "Vẫn mở Bàn trợ live với phiên đã kết thúc" in empty


def test_c12_nhan_du_lieu_mau_tieng_viet():
    for path in DESK_RENDER_PATH:
        assert "DEMO DATA" not in code(raw(path)), f"{path.name}: nhãn demo tiếng Anh"
    badge = _function_body(code(raw(STATUS_BAR)), "DemoBadge")
    assert "DỮ LIỆU MẪU" in badge
