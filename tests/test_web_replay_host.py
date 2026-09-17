"""Gate gói D: /replay (Xem lại phiên) và /host (Màn người dẫn).

Đánh giá UI 17/09/2026 (03-danh-gia-ui.md) bắt được tám lỗi trên hai màn này
mà ``tsc --noEmit`` và mọi gate cũ đều không thấy — vì chúng là lỗi NỘI DUNG
và BỐ CỤC, không phải lỗi kiểu. Các test dưới đây đọc thẳng mã nguồn (cùng
phong cách tests/test_web_*.py) và khoá từng lỗi:

D1  phiên demo ``is_demo=true`` bị in "PHÁT LẠI DỮ LIỆU THẬT";
D2  ``/replay?session=<id>`` luôn mở ``ended[0]`` (buổi CŨ NHẤT);
D3  cột "Hành động gợi ý" + khung what-if luôn rỗng với phiên từ API;
D4  trục x biểu đồ lặp nhãn phút, nhãn trục y chồng nhau khi biểu đồ thấp;
D5  tối đa 16x, khung đầu trống, câu "bạn không cần bấm gì" của màn live,
    nút "Tạm dừng cuộn" trên feed rỗng, không có TopNav;
D6  /host ở 390×844 chữ đè chữ (h-screen overflow-hidden + cỡ chữ cố định);
D7  /host chọn phiên MỘT LẦN lúc tải → mở trước khi phát sóng là khoá nhầm;
D8  câu giải thích trên /host dài và nhắc chữ "thí nghiệm".

Kiểm toán 17/09 (K1–K7, cuối file) — các lỗi ĐÃ XÁC NHẬN trên hai màn này,
khoá bằng hành vi thật (node chạy nguyên văn hàm thuần, máy chủ InMemoryStore):

K1  /host trơn chọn lại "phiên live mới nhất" MỖI lần poll → phiên mẫu của nút
    "Xem thử ngay" (hoặc phiên khách) cướp màn của buổi thật đang phát;
K2  /host?session=<phiên đã kết thúc> vẫn in "Sản phẩm đang ghim — giới thiệu
    ngay" với hàng ghim cũ;
K3  câu "không tìm thấy phiên" bảo mở lại "từ bàn" — Bàn trợ live không có nút;
K4  JS tĩnh của /host chứa assignment/block_index/propensity/design_hash (danh
    sách khoá cấm của api.ts + bộ sinh lịch khối của mock.ts);
K5  khung đầu tự tua không bảo đảm hai điểm phút khi bộ thu bật muộn;
K6  "Bắt đầu xem thử" (?session=mock-ended-01) mở một buổi THẬT khi máy chủ sống;
K7  phiên dry_run (có thể mang bình luận mô phỏng) bị in "PHÁT LẠI DỮ LIỆU THẬT".
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
SRC = WEB / "src"
REPLAY_PAGE = SRC / "app" / "replay" / "page.tsx"
USE_REPLAY = SRC / "lib" / "useReplay.ts"
REPLAY_CONTROLS = SRC / "components" / "ReplayControls.tsx"
RHYTHM_CHART = SRC / "components" / "RhythmChart.tsx"
HOST_VIEW = SRC / "components" / "HostView.tsx"
USE_HOST = SRC / "lib" / "useHost.ts"
HOST_PAGE = SRC / "app" / "host" / "page.tsx"
TYPES_TS = SRC / "lib" / "types.ts"
PICK_SESSION = SRC / "lib" / "pickSession.ts"
API_TS = SRC / "lib" / "api.ts"
MOCK_TS = SRC / "lib" / "mock.ts"
FORMAT_TS = SRC / "lib" / "format.ts"
LAYOUT = SRC / "app" / "layout.tsx"

TYPE_TOKENS = {"meta", "label", "body", "strong", "title", "num-s", "num-m", "num-l", "num-xl"}


def code(src: str) -> str:
    """Nguồn đã bỏ chú thích — các file này trích chính phản-mẫu bị cấm trong
    phần giải thích, tìm chuỗi thô sẽ bắt nhầm lời giải thích."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def function_body(src: str, signature: str) -> str:
    """Thân một hàm top-level: từ chữ ký tới dòng `}` đầu tiên ở cột 0."""
    i = src.index(signature)
    j = src.index("\n}\n", i)
    return src[i:j]


def text_size_classes(src: str) -> list[str]:
    """Mọi lớp cỡ chữ Tailwind (kể cả có tiền tố sm:/2xl:) trong mã nguồn."""
    out = []
    for m in re.finditer(r"(?<![\w-])(?:[a-z0-9]+:)*text-([a-z0-9-]+|\[[^\]]+\])", src):
        name = m.group(1)
        # text-<màu>/text-center… không phải cỡ chữ: chỉ giữ tên thuộc thang
        # Tailwind mặc định hoặc thang token.
        if re.fullmatch(r"xs|sm|base|lg|\d?xl|\[\d+px\]", name) or name in TYPE_TOKENS:
            out.append(m.group(0))
    return out


def pull_body(hook: str) -> str:
    """Thân hàm poll của useHost (từ `const pull` tới `const loop`)."""
    return hook[hook.index("const pull = async () => {") : hook.index("const loop = async () => {")]


# ---------------------------------------------------------------------------
# D1 — nhãn nguồn dữ liệu nói đúng: mẫu là MẪU, không bao giờ "THẬT"
# ---------------------------------------------------------------------------


def test_d1_phien_demo_tu_may_chu_duoc_ghi_du_lieu_mau():
    body = function_body(code(read(REPLAY_PAGE)), "function provenanceText(")
    assert "PHÁT LẠI DỮ LIỆU MẪU" in body, "phiên is_demo phải được ghi 'DỮ LIỆU MẪU'"
    i_that = body.index("PHÁT LẠI DỮ LIỆU THẬT")
    assert body.index("is_demo") < i_that, (
        "câu 'PHÁT LẠI DỮ LIỆU THẬT' phải nằm SAU phép kiểm is_demo — nếu không, "
        "phiên gieo mẫu lấy từ máy chủ lại bị gọi là dữ liệu thật (lỗi 17/09)"
    )
    assert body.index('rp.connection === "mock"') < i_that, (
        "bản mô phỏng khi mất máy chủ cũng phải được loại trước câu 'THẬT'"
    )


def test_d1_dang_tai_thi_khong_khang_dinh_du_lieu_that():
    body = function_body(code(read(REPLAY_PAGE)), "function provenanceText(")
    m = re.search(r"if \(!shown\) return \"([^\"]+)\"", body)
    assert m, "chưa có phiên nào trên màn thì dải băng không được khẳng định gì"
    assert "THẬT" not in m.group(1)
    assert "Đang tải" in m.group(1)


def test_d1_nhan_demo_bang_tieng_viet_theo_is_demo():
    src = code(read(REPLAY_PAGE))
    assert re.search(r"isSample\s*=\s*isMock\s*\|\|\s*shown\?\.is_demo === true", src), (
        "huy hiệu mẫu phải bật cho CẢ bản mô phỏng lẫn phiên is_demo từ máy chủ"
    )
    assert "DEMO — dữ liệu mẫu" in src, "dùng nhãn chung của dự án 'DEMO — dữ liệu mẫu'"
    assert "DemoBadge" not in src, "huy hiệu 'DEMO DATA' là tiếng Anh — không dùng trên /replay"


# ---------------------------------------------------------------------------
# D2 — /replay?session=<id> mở đúng buổi
# ---------------------------------------------------------------------------


def test_d2_trang_doc_session_bang_use_search_params_trong_suspense():
    src = code(read(REPLAY_PAGE))
    assert 'from "next/navigation"' in src
    assert "useSearchParams()" in src
    assert 'searchParams.get("session")' in src, "phải đọc đúng tham số ?session="
    assert re.search(r"useReplay\(requestedId\)", src), "mã phiên phải được đưa vào hook"
    page = function_body(src, "export default function ReplayPage(")
    suspense = (
        "useSearchParams phải nằm dưới ranh giới Suspense — thiếu nó `next build` "
        "của Next 14 từ chối prerender /replay"
    )
    assert "<Suspense" in page, suspense
    assert "<ReplayScreen />" in page, suspense
    assert "useSearchParams" not in page, "trang gốc (ngoài Suspense) không gọi useSearchParams"


def test_d2_hook_uu_tien_ma_trong_link_va_mac_dinh_la_buoi_moi_nhat():
    src = code(read(USE_REPLAY))
    assert not re.search(r"setSessionId\(ended\[0\]", src), (
        "không còn chỗ nào chọn thẳng ended[0] — máy chủ trả theo created_at tăng "
        "dần nên đó là buổi CŨ NHẤT"
    )
    pick = function_body(src, "export function pickReplaySession(")
    assert pick.index("requestedId") < pick.index("ended[0]"), (
        "mã trong link phải được xét TRƯỚC buổi mặc định"
    )
    newest = function_body(src, "export function endedNewestFirst(")
    assert '"ended"' in newest, "danh sách phát lại chỉ gồm buổi đã kết thúc"
    assert "finishedAt(b) - finishedAt(a)" in newest, "buổi kết thúc MỚI NHẤT phải lên đầu"
    assert src.count("pickReplaySession(ended, requestedRef.current)") >= 2, (
        "cả nhánh máy chủ lẫn nhánh mô phỏng phải chọn buổi theo mã trong link"
    )
    assert re.search(r"\}, \[requestedId, sessions\]\);", src), (
        "đổi ?session= sau khi trang đã mở (điều hướng phía client) phải chọn lại buổi"
    )


def test_d2_ma_khong_mo_duoc_thi_noi_ly_do_va_url_theo_lua_chon():
    hook = code(read(USE_REPLAY))
    for status in ('"not_ended"', '"not_found"'):
        assert status in hook, f"hook phải phân biệt trạng thái {status} của mã trong link"
    page = code(read(REPLAY_PAGE))
    notice = function_body(page, "function requestNotice(")
    assert "Không tìm thấy buổi trong link" in notice
    assert "chưa kết thúc" in notice
    assert "<Callout slim>{notice}</Callout>" in page, "lý do phải hiện lên màn, không chỉ ở state"
    assert re.search(r"router\.replace\(`/replay\?session=\$\{encodeURIComponent\(id\)\}`", page), (
        "chọn buổi khác trong ô chọn phải đổi URL — link chép ra mới mở lại đúng buổi"
    )


# ---------------------------------------------------------------------------
# D3 — "Hành động gợi ý" + "nếu hết hàng" có nội dung; rỗng thì nói lý do
# ---------------------------------------------------------------------------


def test_d3_mang_the_rong_khong_chan_duong_xep_lai_tu_ban_ghi():
    src = code(read(USE_REPLAY))
    assert "if (serverCards) return serverCards" not in src, (
        "mảng rỗng vẫn truthy — dòng này chặn đường xếp lại và làm cột thẻ chết"
    )
    assert "getCards" not in src, (
        "máy chủ không phát thẻ cho phiên đã kết thúc, và thẻ 'bây giờ' không phải "
        "thẻ 'tại phút T' của bản ghi — phát lại phải xếp thẻ từ bản ghi"
    )
    assert "replayCardsAt(recording, cardsOffset, excluded)" in src


def test_d3_san_pham_lay_tu_danh_muc_listproducts():
    src = code(read(USE_REPLAY))
    imports = src[: src.index('} from "./api";')]
    assert "listProducts" in imports, "phải import listProducts từ api.ts"
    loader = function_body(src, "async function loadApiRecording(")
    assert "listProducts()" in loader, "danh sách sản phẩm phải lấy từ danh mục của máy chủ"
    assert "catalogFailed" in loader, "danh mục hỏng phải được báo, không im lặng thành rỗng"
    assert "analysis ? [] : synthesizeTimeline(" in loader, (
        "phiên phân tích video người khác không bao giờ được tổng hợp thẻ"
    )


def test_d3_the_xep_lai_khong_bia_so():
    src = code(read(USE_REPLAY))
    for fn in ("export function replayCardsAt(", "function synthesizeTimeline("):
        body = function_body(src, fn)
        assert 'source: "forecast"' in body, f"{fn}: thẻ tổng hợp phía web chỉ là dự báo"
        assert "estimate: null" in body, f"{fn}: thẻ tổng hợp phía web không được mang con số"
        assert "rng(" not in body, f"{fn}: không có số ngẫu nhiên"
        assert "Math.random" not in body, f"{fn}: không có số ngẫu nhiên"
    assert "recomputeCards" not in src, (
        "recomputeCards (mock.ts) bù thẻ bằng ước lượng NGẪU NHIÊN — phát lại không dùng nó"
    )
    synth = function_body(src, "function synthesizeTimeline(")
    honest = (
        "không có lượt bấm theo sản phẩm thì lý do trên thẻ phải nói thẳng là thứ tự "
        "danh mục, không được nói 'xếp theo nhịp click'"
    )
    assert "measured" in synth, honest
    assert "thứ tự danh mục" in synth, honest


def test_d3_cau_rong_noi_dung_ly_do_khong_day_nguoi_dung_di_tim():
    raw = read(REPLAY_PAGE)
    src = code(raw)
    assert "kiểm tra tham số bên phải" not in raw, (
        "câu cũ bảo người dùng kiểm tra khung bên phải trong khi khung đó cũng trống"
    )
    reasons = function_body(src, "function cardsEmptyReason(")
    for why in ("rp.analysis", "catalogFailed", "products.length === 0", "rp.excluded.has"):
        assert why in reasons, f"câu rỗng của cột thẻ phải phân nhánh theo {why}"
    assert "function productsEmptyReason(" in src, "khung 'nếu hết hàng' rỗng cũng phải nói lý do"
    assert "what-if" not in src.lower(), "thuật ngữ tiếng Anh 'what-if' không lên giao diện"
    assert "phía client" not in src, "'phía client' là chữ của lập trình viên, không của người bán"


# ---------------------------------------------------------------------------
# D4 — biểu đồ nhịp: nhãn phút không lặp, nhãn trục y không chồng
# ---------------------------------------------------------------------------


def _minute_ticks_py(last_offset_s: int, steps: list[int], max_labels: int) -> list[int]:
    """Bản Python của `minuteTicks` — chạy trên CHÍNH hằng số đọc từ file."""
    span_min = max(1, -(-last_offset_s // 60))
    step = next((s for s in steps if span_min / s <= max_labels), None)
    if step is None:
        step = -(-span_min // max_labels // 60) * 60
    return [m * 60 for m in range(0, last_offset_s // 60 + 1, step)]


def test_d4_nhan_phut_truc_x_khong_bao_gio_lap():
    src = code(read(RHYTHM_CHART))
    fmt = function_body(src, "function fmtMinuteTick(")
    assert "Math.round" not in fmt, "làm tròn phút cho vạch mỗi 30 giây in ra `0' 1' 1' 2' 2'`"
    assert re.search(r"<XAxis[^>]*ticks=\{xTicks\}", src, re.S), (
        "vạch trục x phải đặt tường minh ở phút tròn, không để Recharts rải mỗi 30 s"
    )
    steps_m = re.search(r"const MINUTE_STEPS = \[([\d,\s]+)\]", src)
    max_m = re.search(r"const MAX_X_LABELS = (\d+);", src)
    assert steps_m, "không đọc được MINUTE_STEPS"
    assert max_m, "không đọc được MAX_X_LABELS"
    steps = [int(x) for x in steps_m.group(1).split(",")]
    max_labels = int(max_m.group(1))
    body = function_body(src, "function minuteTicks(")
    assert "m * 60" in body, "vạch phải là bội số nguyên của phút"
    assert "m += step" in body, "vạch phải đi theo bước phút tròn"
    for minutes in (1, 2, 3, 7, 30, 59, 60, 90, 117, 138, 180, 240):
        labels = [t // 60 for t in _minute_ticks_py(minutes * 60, steps, max_labels)]
        assert len(labels) == len(set(labels)), f"nhãn lặp ở phiên {minutes} phút: {labels}"
        assert len(labels) <= max_labels + 1, f"quá nhiều nhãn ở phiên {minutes} phút"


def test_d4_nhan_truc_y_khong_tran_sang_panel_ke_ben():
    src = code(read(RHYTHM_CHART))
    m = re.search(r"const MARGIN = \{ top: (\d+), right: \d+, left: \d+, bottom: (\d+) \}", src)
    assert m, "không đọc được lề panel"
    top, bottom = int(m.group(1)), int(m.group(2))
    # Nhãn 13px canh giữa vạch tràn ~6.5px ra ngoài vùng vẽ.
    why = (
        "panel không in trục x phải chừa ≥ 7px trên/dưới cho nửa dòng nhãn trục y — "
        f"lề {top}/{bottom} để nhãn '0' panel trên dính nhãn đỉnh panel dưới"
    )
    assert top >= 7, why
    assert bottom >= 7, why
    assert "margin={showAxis ? MARGIN_WITH_X_AXIS : MARGIN}" in src
    y_axis = re.search(r"<YAxis([\s\S]*?)/>", src)
    assert y_axis, "không đọc được trục y"
    assert 'interval="preserveStartEnd"' in y_axis.group(1), (
        "panel thấp: trục y phải bỏ bớt nhãn giữa thay vì in đè"
    )


# ---------------------------------------------------------------------------
# D5 — phát lại là phát lại: tốc độ, khung đầu, câu chữ, TopNav
# ---------------------------------------------------------------------------


def test_d5_co_toc_do_30x_va_60x():
    hook = code(read(USE_REPLAY))
    m = re.search(r"export type ReplaySpeed = ([^;]+);", hook)
    assert m, "không đọc được kiểu ReplaySpeed"
    assert {30, 60} <= {int(x) for x in re.findall(r"\d+", m.group(1))}, (
        "buổi 60 phút ở 16x mất ~4 phút — cần 30x/60x"
    )
    controls = code(read(REPLAY_CONTROLS))
    m = re.search(r"const SPEEDS: ReplaySpeed\[\] = \[([^\]]+)\]", controls)
    assert m, "không đọc được danh sách nút tốc độ"
    assert {30, 60} <= {int(x) for x in re.findall(r"\d+", m.group(1))}, (
        "nút 30x/60x phải có trên thanh điều khiển"
    )


def test_d5_khung_dau_tu_tua_toi_phut_co_so_lieu_va_nhac_bam_phat():
    hook = code(read(USE_REPLAY))
    assert hook.count("setT(firstFrameOffset(rec))") >= 2, (
        "cả bản ghi máy chủ lẫn bản mô phỏng phải mở ở phút đầu có số liệu, không ở 00:00 trống"
    )
    first = function_body(hook, "export function firstFrameOffset(")
    assert "Math.floor(x.offset_s / 60) > firstMinute" in first, (
        "biểu đồ cần hai điểm phút — khung đầu phải qua phút SAU phút của tick sớm nhất "
        "(không phải tick đầu có offset ≥ 60: xem K5)"
    )
    prompt = function_body(code(read(REPLAY_PAGE)), "function playPrompt(")
    assert "bấm Phát" in prompt, "dòng nhắc phải nói rõ việc cần làm: bấm Phát"
    assert "Đã tua sẵn tới" in prompt, "tự tua thì phải nói là đã tua, không để người xem ngơ ngác"


def test_d5_khong_muon_cau_cua_man_live():
    chart = code(read(RHYTHM_CHART))
    assert re.search(r"replay\s*\?\s*\"[^\"]*Bấm Phát", chart), (
        "trạng thái rỗng của biểu đồ trong ngữ cảnh phát lại phải bảo bấm Phát"
    )
    assert re.search(r"replay\s*\?[^:]*:\s*\"[^\"]*Bạn không cần bấm gì", chart), (
        "câu 'Bạn không cần bấm gì' chỉ còn ở nhánh màn live"
    )
    page = code(read(REPLAY_PAGE))
    m = re.search(r"<RhythmChart([\s\S]*?)/>", page)
    assert m, "không đọc được lời gọi <RhythmChart>"
    assert re.search(r"\breplay\b", m.group(1)), "/replay phải bật ngữ cảnh phát lại cho biểu đồ"
    assert "không cần làm gì" not in page, "câu 'bạn không cần làm gì' là của màn live"


def test_d5_feed_rong_khong_dung_comment_feed_va_nut_tam_dung_cuon():
    page = code(read(REPLAY_PAGE))
    i_empty = page.index("rp.visibleComments.length === 0 ?")
    i_feed = page.index("<CommentFeed")
    assert i_empty < i_feed, "CommentFeed (có nút 'Tạm dừng cuộn') chỉ dựng khi đã có bình luận"
    assert "<NoCommentsYet" in page[i_empty:i_feed], "feed rỗng phải có câu riêng của phát lại"
    empty = function_body(page, "function NoCommentsYet(")
    assert "Tạm dừng cuộn" not in empty
    assert "rp.seek(" in empty, "bình luận đầu tiên ở xa thì cho một nút tua thẳng tới đó"


def test_d5_replay_co_topnav_va_khong_bi_ep_mot_man():
    page = code(read(REPLAY_PAGE))
    nav = "/replay phải có TopNav như mọi trang 'Sau live' khác"
    assert 'import TopNav from "@/components/TopNav"' in page, nav
    assert "<TopNav />" in page, nav
    squeeze = "bố cục ép đúng một màn (h-screen overflow-hidden) bóp biểu đồ còn ~100 px"
    assert not re.search(r"(?<![\w-])h-screen", page), squeeze
    assert "overflow-hidden" not in page, squeeze
    assert "min-h-screen" in page


# ---------------------------------------------------------------------------
# D6 — /host đáp ứng: không chồng lấn ở 390×844, vẫn to ở 1366/TV
# ---------------------------------------------------------------------------


def test_d6_host_khong_con_khung_co_dinh_mot_man():
    src = code(read(HOST_VIEW))
    main = re.search(r"<main className=\"([^\"]+)\"", src)
    assert main, "không đọc được thẻ <main> của HostView"
    classes = main.group(1).split()
    overflow = "h-screen + nội dung cao hơn khung = chữ tràn lên header và xuống footer"
    assert "h-screen" not in classes, overflow
    assert "min-h-screen" in classes, overflow
    assert "overflow-hidden" not in classes, "overflow-hidden giấu mất tồn kho ở màn hẹp"
    section = re.search(r"<section className=\"([^\"]+)\"", src)
    assert section, "khối sản phẩm phải là một <section> riêng"
    section_cls = section.group(1).split()
    assert "min-h-0" not in section_cls, (
        "khối giữa không được co dưới chiều cao nội dung — đó là thứ đẩy chữ chồng lên nhau"
    )
    assert "px-4" in section_cls, "lề ngang px-12 cố định ăn mất 96px của màn 390px"
    assert "sm:px-8" in section_cls, "màn rộng hơn mới nới lề"


def test_d6_host_chi_dung_token_co_chu():
    src = code(read(HOST_VIEW))
    offenders = [
        c
        for c in text_size_classes(src)
        if c.split(":")[-1].removeprefix("text-") not in TYPE_TOKENS
    ]
    assert not offenders, (
        "HostView dùng cỡ chữ ngoài thang token (text-2xl/8xl… không co theo màn):\n"
        + "\n".join(offenders)
    )


def test_d6_ten_hang_nho_o_man_hep_va_len_bac_hien_thi_o_man_rong():
    src = code(read(HOST_VIEW))
    h1 = re.search(r"<h1 className=\"([^\"]+)\">\s*\{host\.product_name\}", src)
    assert h1, "không đọc được tiêu đề tên hàng"
    classes = h1.group(1).split()
    base = [c for c in classes if c.startswith("text-num-")]
    assert base, "tên hàng phải ở một bậc hiển thị của thang"
    assert base[0] != "text-num-xl", (
        "tên hàng num-xl (72px) ở 390px vỡ thành 5 dòng một-hai-chữ — bậc gốc phải nhỏ hơn"
    )
    assert any(re.fullmatch(r"(xl|lg):text-num-xl", c) for c in classes), (
        "ở 1366 (xl) và TV tên hàng vẫn phải lên bậc num-xl"
    )
    assert "[overflow-wrap:anywhere]" in classes, "tên hàng dài phải xuống dòng, không tràn ngang"
    clock = re.search(r"<div className=\"([^\"]+)\" aria-live=\"off\">", src)
    assert clock, "không đọc được đồng hồ"
    assert "text-num-s" in clock.group(1).split(), "đồng hồ ở màn hẹp phải nhỏ hơn"
    assert "lg:text-num-l" in clock.group(1), "đồng hồ ở màn rộng vẫn là num-l"
    for label in ("Giá", "Tồn kho"):
        m = re.search(r"<div className=\"([^\"]+)\">\s*" + label + r"\s*</div>", src)
        assert m, f"không đọc được nhãn {label}"
        assert "text-label" in m.group(1).split(), f"nhãn {label} phải nhỏ ở màn hẹp"
        assert "sm:text-title" in m.group(1), f"nhãn {label} lên bậc title ở màn rộng"


def test_d6_trang_thai_tren_host_co_hinh_va_chu():
    src = code(read(HOST_VIEW))
    for phrase in (
        "Mất kết nối tới máy chủ",
        "sắp hết — hối khách chốt",
        "Đồng hồ đã chạy hơn 4 giờ",
    ):
        i = src.index(phrase)
        assert "⚠" in src[max(0, i - 300) : i], f"'{phrase}' phải có ký hiệu, không chỉ màu"
    raw = read(HOST_VIEW)
    # nhãn docs/HUONG-DAN-SU-DUNG.md trích nguyên văn
    assert "Sản phẩm đang ghim" in raw
    assert "Chưa ghim sản phẩm" in raw


# ---------------------------------------------------------------------------
# D7 — /host: ?session= ưu tiên tuyệt đối, không có thì chọn lại mỗi lần poll
# ---------------------------------------------------------------------------


def test_d7_trang_host_doc_session_trong_suspense():
    src = code(read(HOST_PAGE))
    assert "useSearchParams()" in src
    assert re.search(r"useHost\(\s*searchParams\.get\(\"session\"\)", src), (
        "mã phiên trong link phải được đưa vào useHost"
    )
    page = function_body(src, "export default function HostPage(")
    assert "<Suspense" in page, "useSearchParams phải nằm dưới ranh giới Suspense"
    assert "<HostScreen />" in page, "useSearchParams phải nằm dưới ranh giới Suspense"
    assert "useSearchParams" not in page, "trang gốc (ngoài Suspense) không gọi useSearchParams"


def test_d7_chon_lai_phien_moi_lan_poll_khong_phai_mot_lan_luc_tai():
    src = code(read(USE_HOST))
    pull = pull_body(src)
    assert 'hostGet<SessionSummary[]>("/sessions"' in pull, (
        "danh sách phiên phải được đọc lại TRONG vòng poll"
    )
    assert "pickHostSession(" in pull, "phiên đang live phải được xét lại TRONG vòng poll"
    loop = src[src.index("const loop = async () => {") :]
    assert "await pull()" in loop, "vòng poll phải gọi hàm chọn phiên"
    assert "setTimeout(loop" in loop, "vòng poll phải tự nối đuôi"
    assert not re.search(r"(listSessions|hostGet)[^;]*\)\s*\.then", src), (
        "chọn phiên bằng một lời gọi .then lúc tải chính là lỗi khoá nhầm phiên"
    )
    assert "pickHostSession(list, shownSessionId, !shownReal)" in pull, (
        "không có tham số thì chọn qua pickHostSession (chỉ phiên ĐANG live, giữ phiên "
        "đang chiếu, bỏ phiên mẫu khi có phiên thật) — xem K1"
    )
    assert "pickCurrentSession" not in src, (
        "pickCurrentSession chọn phiên live MỚI NHẤT mỗi lần poll — chính là lỗi cướp màn K1"
    )


def test_d7_ma_trong_link_uu_tien_tuyet_doi():
    src = code(read(USE_HOST))
    pull = pull_body(src)
    i_req = pull.index("if (requested) {")
    assert i_req < pull.index("pickHostSession("), (
        "nhánh ?session= phải được xét trước việc tự chọn phiên"
    )
    # `if (!list) {` CUỐI là nhánh /host trơn; nhánh ?session= có một cái riêng ở đầu.
    req_block = pull[i_req : pull.rindex("if (!list) {")]
    assert "readHostState(requested)" in req_block
    assert re.search(r"return;\s*\}\s*$", req_block), (
        "nhánh ?session= phải kết thúc trong chính nó, không rơi xuống tự chọn phiên khác"
    )
    assert "setSessionNotFound(true)" in req_block, (
        "mã sai thì nói thẳng 'không tìm thấy', không lặng lẽ chiếu phiên khác"
    )
    assert "}, [requested]);" in src, "đổi mã trong link phải khởi động lại vòng poll"
    assert "Không tìm thấy phiên trong link" in code(read(HOST_VIEW))


def test_d7_man_host_van_bi_lam_mu():
    """Sửa chọn phiên không được mở đường nào tới nhánh BẬT/TẮT (L6)."""
    forbidden = (
        "getState(",
        "getSchedule",
        "getCards",
        "BlockInfo",
        "assignment",
        "current_block",
        "BlockStrip",
        "BlockClock",
        "StatusBar",
        "useDesk",
        "RhythmChart",
    )
    for path in (USE_HOST, HOST_VIEW, HOST_PAGE):
        src = code(read(path))
        for name in forbidden:
            assert name not in src, f"{path.name} chạm vào {name} — rò rỉ làm mù (L6)"
    ret = re.search(r"return \{ ([^}]+) \};\s*\}\s*$", code(read(USE_HOST)))
    assert ret, "không đọc được giá trị trả về của useHost"
    fields = {f.strip() for f in ret.group(1).split(",")}
    assert fields == {
        "host",
        "connection",
        "degraded",
        "sessionNotFound",
        "offAir",
        "concurrentLive",
        "sampleData",
    }, f"useHost chỉ được trả HostState + cờ đường truyền/nhãn, thấy: {sorted(fields)}"
    m = re.search(r"export interface HostState \{(.*?)\n\}", read(TYPES_TS), re.S)
    assert m, "không đọc được HostState"
    keys = re.findall(r"(?m)^\s+(\w+)\??:", m.group(1))
    assert keys == ["product_name", "price", "stock", "elapsed_s"], (
        f"HostState phải đúng 4 trường, thấy {keys}"
    )


# ---------------------------------------------------------------------------
# D8 — câu giải thích ngắn, không nhắc "thí nghiệm"
# ---------------------------------------------------------------------------


def test_d8_cau_giai_thich_tren_host_ngan_va_khong_nhac_thi_nghiem():
    src = code(read(HOST_VIEW))
    assert "thí nghiệm" not in src.lower(), (
        "nhắc 'thí nghiệm' trên màn người dẫn chính là gợi lại điều màn này muốn giấu"
    )
    m = re.search(r"<p className=\"text-body leading-snug text-sec\">([^<]+)</p>", src)
    assert m, "không đọc được câu giải thích dưới tiêu đề"
    sentence = " ".join(m.group(1).split())
    assert len(sentence) <= 60, f"câu giải thích phải ngắn (≤ 60 ký tự), đang là: {sentence!r}"


# ===========================================================================
# Kiểm toán 17/09 — K1–K7: chạy THẬT hàm thuần bằng node trên dữ liệu máy chủ
# ===========================================================================


def extract(src: str, name: str) -> str:
    """Tách nguyên văn một khai báo cấp cao nhất (function/const) — cùng cách
    tests/test_web_desk_v3.py; node ≥ 22 tự bỏ chú thích kiểu."""
    lines = src.replace("\r\n", "\n").split("\n")
    head = re.compile(rf"^(?:export )?(?:(?:async )?function|const) {re.escape(name)}\b")
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


def node_eval(tmp_path: Path, decls: list[tuple[Path, list[str]]], expr: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("không có node — bỏ qua phần chạy thử hàm thuần")
    module = "\n\n".join(extract(read(path), n) for path, names in decls for n in names)
    script = tmp_path / "replay_host_pure.mts"
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


PICK_HOST = [(PICK_SESSION, ["startedAt", "latest", "pickHostSession"])]


@pytest.fixture
def api():
    from fastapi.testclient import TestClient

    from livelift.api.main import create_app
    from livelift.api.store import InMemoryStore

    store = InMemoryStore()
    with TestClient(create_app(store=store)) as client:
        yield client, store


def _real_live_session(client, store, minutes_ago: int) -> str:
    """Phiên THẬT (không token = chế độ cục bộ) đang phát từ `minutes_ago` phút trước."""
    from datetime import timedelta

    from livelift.api import service

    r = client.post(
        "/sessions", json={"platform": "youtube", "mode": "suggest", "planned_duration_min": 90}
    )
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]
    assert client.post(f"/sessions/{sid}/schedule", json={"seed": 7}).status_code == 200
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    store.update_session(sid, {"start_ts": service.now_utc() - timedelta(minutes=minutes_ago)})
    return sid


# ---------------------------------------------------------------------------
# K1 — /host trơn: phiên mẫu / phiên đến sau không cướp màn buổi thật
# ---------------------------------------------------------------------------


def test_k1_xem_thu_ngay_khong_cuop_man_cua_buoi_that_dang_phat(api, tmp_path):
    """Kịch bản đã tái hiện: phiên thật live 40 phút, ai đó bấm "Xem thử ngay"
    (/demo/seed để lại phiên mẫu live với start_ts = now − 30 phút, MỚI hơn)."""
    client, store = api
    real = _real_live_session(client, store, minutes_ago=40)
    seed = client.post("/demo/seed", json={"n_sessions": 1})
    assert seed.status_code == 200, seed.text
    rows = client.get("/sessions").json()
    live = [r for r in rows if r["status"] == "live"]
    assert {r["is_demo"] for r in live} == {True, False}, "kịch bản cần cả phiên thật lẫn mẫu live"
    got = node_eval(
        tmp_path,
        PICK_HOST,
        f"[pickHostSession({js(rows)}, {js(real)}), pickHostSession({js(rows)}, null)]",
    )
    for pick in got:
        assert pick["session"]["session_id"] == real, (
            "màn người dẫn nhảy sang phiên mẫu mới hơn — người dẫn giới thiệu nhầm hàng"
        )
        assert pick["session"]["is_demo"] is False
        assert pick["liveCount"] == 1, "phiên mẫu không được tính là phiên cạnh tranh"


def test_k1_giu_phien_dang_chieu_khi_co_phien_that_thu_hai_len_song(api, tmp_path):
    client, store = api
    first = _real_live_session(client, store, minutes_ago=40)
    second = _real_live_session(client, store, minutes_ago=1)
    rows = client.get("/sessions").json()
    got = node_eval(
        tmp_path,
        PICK_HOST,
        f"[pickHostSession({js(rows)}, {js(first)}), pickHostSession({js(rows)}, null)]",
    )
    kept, fresh = got
    assert kept["session"]["session_id"] == first, "phiên đang chiếu còn live thì giữ nguyên"
    assert kept["liveCount"] == 2, "hai phiên thật cùng live phải được báo, không tự đổi"
    assert fresh["session"]["session_id"] == second, (
        "chưa chiếu gì thì chọn phiên lên sóng GẦN NHẤT (bug đồng hồ 328 giờ)"
    )


def test_k1_mo_truoc_gio_phat_van_bat_duoc_phien_vua_len_song(api, tmp_path):
    """Không được đổi lại lỗi gói D: màn mở trước giờ phát (đang chiếu phiên mẫu
    hoặc chưa chiếu gì) phải tự sang phiên thật vừa bấm phát; phiên thật xong
    thì màn trống, không lùi về hàng mẫu."""
    client, store = api
    seed = client.post("/demo/seed", json={"n_sessions": 1}).json()
    demo_live = seed["replay_session_id"]
    before = client.get("/sessions").json()
    real = _real_live_session(client, store, minutes_ago=0)
    during = client.get("/sessions").json()
    assert client.post(f"/sessions/{real}/end").status_code == 200
    after = client.get("/sessions").json()
    got = node_eval(
        tmp_path,
        PICK_HOST,
        "["
        f"pickHostSession({js(before)}, null),"
        f"pickHostSession({js(during)}, {js(demo_live)}),"
        f"pickHostSession({js(after)}, {js(real)}, false),"
        f"pickHostSession({js(after)}, null, true)"
        "]",
    )
    only_demo, demo_to_real, real_ended, fresh_tab = got
    assert only_demo["session"]["session_id"] == demo_live, "chưa có phiên thật: chiếu phiên mẫu"
    assert demo_to_real["session"]["session_id"] == real, "phiên thật lên sóng thay phiên mẫu"
    assert real_ended["session"] is None, (
        "màn đã chiếu phiên thật: buổi thật xong thì trống, không nhảy sang hàng mẫu"
    )
    assert fresh_tab["session"]["session_id"] == demo_live


def test_k1_hook_giu_phien_va_bao_nhieu_phien_cung_live():
    src = code(read(USE_HOST))
    pull = pull_body(src)
    assert "setConcurrentLive(picked.liveCount >= 2 ? picked.liveCount : 0)" in pull
    assert "if (h != null && isDemo === false) shownReal = true;" in src, (
        "màn phải nhớ đã từng chiếu phiên thật để không lùi về phiên mẫu"
    )
    view = code(read(HOST_VIEW))
    i = view.index("concurrentLive >= 2 ?")
    assert "⚠" in view[i : i + 400], "cảnh báo nhiều phiên phải có HÌNH + chữ"
    assert "không tự đổi" in view[i : i + 600]
    page = code(read(HOST_PAGE))
    assert "concurrentLive={concurrentLive}" in page
    assert "offAir={offAir}" in page


# ---------------------------------------------------------------------------
# K2 — /host?session=<phiên không live>: không in hàng ghim cũ
# ---------------------------------------------------------------------------


def test_k2_phien_da_ket_thuc_con_hang_ghim_nhung_man_khong_doc(api, tmp_path):
    client, _store = api
    seed = client.post("/demo/seed", json={"n_sessions": 1}).json()
    ended = seed["session_ids"][0]
    row = next(r for r in client.get("/sessions").json() if r["session_id"] == ended)
    assert row["status"] == "ended"
    host = client.get(f"/sessions/{ended}/state?role=host").json()
    assert host["pinned_product"], (
        "tiền đề: máy chủ VẪN trả hàng ghim cuối của phiên đã xong — web phải tự chặn"
    )
    got = node_eval(
        tmp_path,
        [(USE_HOST, ["offAirOf"])],
        "['live','ended','cancelled','planned','scheduled'].map(offAirOf)",
    )
    assert got == [None, "ended", "cancelled", "not_started", "not_started"], (
        "phiên huỷ (đóng mà chưa từng lên sóng) không được gọi là 'đã kết thúc'"
    )

    pull = pull_body(code(read(USE_HOST)))
    req = pull[pull.index("if (requested) {") : pull.index("pickHostSession(")]
    i_off = req.index("const off = offAirOf(row.status);")
    i_read = req.index("readHostState(requested)")
    assert i_off < i_read, "trạng thái phiên phải được xét TRƯỚC khi đọc hàng ghim"
    guard = req[i_off:i_read]
    assert "setOffAir(off);" in guard
    assert re.search(r"show\(null, null, row\.is_demo\);\s*return;", guard), (
        "phiên không live thì dừng ở đó — không bao giờ gọi /state?role=host"
    )


def test_k2_man_noi_ro_phien_da_ket_thuc_hoac_chua_len_song(tmp_path):
    got = node_eval(
        tmp_path,
        [(HOST_VIEW, ["REOPEN_HINT", "emptyStateText"])],
        "[emptyStateText('live', false, 'ended'), emptyStateText('live', false, 'not_started'),"
        " emptyStateText('live', false, null), emptyStateText('connecting', false, 'ended'),"
        " emptyStateText('live', false, 'cancelled')]",
    )
    ended, not_started, idle, connecting, cancelled = got
    assert "đã kết thúc" in ended["title"]
    assert ended["icon"], "trạng thái phải có HÌNH + chữ"
    assert "giới thiệu nhầm" in ended["detail"]
    assert "chưa lên sóng" in not_started["title"]
    assert not_started["icon"]
    assert "người trực" in not_started["detail"], (
        "người dẫn không bấm 'Bắt đầu phát sóng' — câu phải nói ai bấm"
    )
    assert "đã huỷ" in cancelled["title"]
    assert "kết thúc" not in cancelled["title"], "phiên huỷ chưa từng phát — không 'kết thúc'"
    assert "chưa từng lên sóng" in cancelled["detail"]
    assert cancelled["icon"], "trạng thái phải có HÌNH + chữ"
    assert idle["title"] == "Chưa ghim sản phẩm"
    assert connecting["title"] == "Đang kết nối…"
    for state in got:
        assert "giới thiệu ngay" not in state["title"], "màn trống không được mượn nhãn hàng ghim"


# ---------------------------------------------------------------------------
# K3 — câu "không tìm thấy phiên" chỉ tới đúng chỗ có nút
# ---------------------------------------------------------------------------


def test_k3_khong_bao_mo_lai_tu_ban_tro_live(tmp_path):
    got = node_eval(
        tmp_path,
        [(HOST_VIEW, ["REOPEN_HINT", "emptyStateText"])],
        "emptyStateText('live', true, null)",
    )
    assert got["title"] == "Không tìm thấy phiên trong link"
    assert "từ bàn" not in got["detail"], "Bàn trợ live không có nút mở màn người dẫn"
    assert "Chuẩn bị phiên" in got["detail"]
    assert "bước 4" in got["detail"]
    assert got["icon"]
    wizard = read(SRC / "app" / "chay-phien" / "page.tsx")
    assert "Mở màn hình người dẫn" in wizard, "câu dẫn phải khớp nhãn nút ở trang Chuẩn bị phiên"
    assert "Mở màn hình người dẫn" in got["detail"]


# ---------------------------------------------------------------------------
# K4 — JS tải về máy người dẫn không chứa khoá khối (tầng mạng, sự cố 27/08)
# ---------------------------------------------------------------------------

_IMPORT_RE = re.compile(
    r"""(?:^|\n)\s*(?:import|export)\s+(type\s+)?(?:[^"';]*?\s+from\s+)?["']([^"']+)["']"""
    r"""|import\(\s*["']([^"']+)["']\s*\)"""
)


def _resolve(spec: str, here: Path) -> Path | None:
    if spec.startswith("@/"):
        base = SRC / spec[2:]
    elif spec.startswith("."):
        base = Path(os.path.normpath(here.parent / spec))
    else:
        return None  # gói ngoài (react, next) — không phải mã của dự án
    for cand in (base, base.with_name(base.name + ".ts"), base.with_name(base.name + ".tsx")):
        if cand.is_file():
            return cand
    return None


def host_module_graph() -> set[Path]:
    """Mọi module của dự án mà trang /host (và layout gốc) tải ở runtime —
    bỏ `import type` vì chúng bị xoá khi build."""
    seen: set[Path] = set()
    todo = [HOST_PAGE, LAYOUT]
    while todo:
        path = todo.pop()
        if path in seen or path.suffix not in (".ts", ".tsx"):
            continue
        seen.add(path)
        for m in _IMPORT_RE.finditer(code(read(path))):
            if m.group(1):
                continue
            target = _resolve(m.group(2) or m.group(3), path)
            if target is not None:
                todo.append(target)
    return seen


HOST_BUNDLE_FORBIDDEN = (
    "assignment",
    "block_index",
    "propensity",
    "design_hash",
    "current_block",
    "seconds_remaining",
    "role=operator",
)


def test_k4_do_thi_import_cua_host_khong_co_api_ts_va_mock_ts():
    graph = host_module_graph()
    names = {p.relative_to(SRC).as_posix() for p in graph}
    assert "lib/useHost.ts" in names, names
    assert "components/HostView.tsx" in names, names
    assert "lib/pickSession.ts" in names, "trình đọc import phải đi được xuống module con"
    assert "lib/api.ts" not in names, (
        "api.ts mang danh sách khoá cấm + mọi đường operator — JS tĩnh của /host từng chứa "
        "'assignment', 'design_hash' (đo trên bản build 17/09)"
    )
    assert "lib/mock.ts" not in names, (
        "mock.ts mang bộ sinh lịch khối (block_index/assignment/propensity)"
    )


def test_k4_ma_trong_do_thi_import_cua_host_khong_nhac_khoa_khoi():
    offenders = []
    for path in sorted(host_module_graph()):
        src = code(read(path))
        offenders += [f"{path.relative_to(SRC)}: {k}" for k in HOST_BUNDLE_FORBIDDEN if k in src]
    assert not offenders, "mã tải về máy người dẫn nhắc khoá khối:\n" + "\n".join(offenders)


def test_k4_doc_import_bat_duoc_api_ts_neu_ai_do_import_lai():
    """Tự kiểm của gate: trình đọc import phải thấy một import giá trị từ ./api."""
    fake = 'import { useEffect } from "react";\nimport {\n  getHostState,\n} from "./api";\n'
    specs = [m.group(2) for m in _IMPORT_RE.finditer(fake) if not m.group(1)]
    assert "./api" in specs
    typed = 'import type { HostState } from "./types";\n'
    assert all(m.group(1) for m in _IMPORT_RE.finditer(typed))


def test_k4_payload_host_qua_danh_sach_cho_phep(tmp_path):
    decls = [(USE_HOST, ["HOST_PAYLOAD_KEYS", "finiteOrNull", "toHostState"])]
    leaked = {
        "pinned_product": "Bình giữ nhiệt 500ml",
        "price": 95000.0,
        "stock": 80,
        "elapsed_s": 12.5,
        "extra_a": "x",
        "extra_b": 1,
    }
    legacy = {"pinned_product": {"name": "Áo", "price": 5, "stock": 2}}
    got = node_eval(
        tmp_path,
        decls,
        f"[toHostState({js(leaked)}), toHostState({js(legacy)}), toHostState({{}})]",
    )
    full, old_shape, empty = got
    assert full == {
        "product_name": "Bình giữ nhiệt 500ml",
        "price": 95000,
        "stock": 80,
        "elapsed_s": 12.5,
    }, "chỉ bốn trường HostState được đi tiếp — trường lạ bị bỏ"
    assert old_shape == {"product_name": "Áo", "price": 5, "stock": 2, "elapsed_s": 0}
    assert empty == {"product_name": None, "price": None, "stock": None, "elapsed_s": 0}
    assert "/state?role=host" in code(read(USE_HOST)), "màn người dẫn chỉ đọc payload role=host"


def test_k4_duong_mang_rieng_cua_host_khop_api_ts_va_mau_khop_mock_ts():
    host = read(USE_HOST)
    api_src = read(API_TS)
    expr = re.compile(r"\(process\.env\.NEXT_PUBLIC_API_URL \?\? \"([^\"]+)\"\)\.replace\(")
    api_m = expr.search(api_src[api_src.index("export const API_BASE") :])
    host_m = expr.search(host[host.index("const HOST_API_BASE") :])
    assert api_m, "không đọc được địa chỉ máy chủ của api.ts"
    assert host_m, "không đọc được địa chỉ máy chủ của useHost.ts"
    assert api_m.group(1) == host_m.group(1), "địa chỉ máy chủ mặc định của /host lệch api.ts"

    mock = read(MOCK_TS)
    start = mock.index("export const MOCK_PRODUCTS")
    block = mock[start : mock.index("];", start)]
    mock_products = re.findall(
        r'name: "([^"]+)", category: "[^"]+", price: (\d+), stock: (\d+)', block
    )
    host_start = host.index("const MOCK_HOST_PRODUCTS")
    host_block = host[host_start : host.index("];", host_start)]
    host_products = re.findall(r'name: "([^"]+)", price: (\d+), stock: (\d+)', host_block)
    assert mock_products, "không đọc được MOCK_PRODUCTS"
    assert host_products == mock_products, (
        "bản mô phỏng của màn người dẫn phải cùng hàng với bản ghi bàn trợ live đang chạy"
    )
    assert "t % 240 === 0" in mock
    assert "const MOCK_HOST_PIN_EVERY_S = 240;" in host
    live = mock[mock.index('session_id: "mock-live-01"') :]
    assert "planned_duration_min: 90," in live[:400]
    assert "const MOCK_HOST_DURATION_S = 90 * 60;" in host
    elapsed = function_body(mock, "export function mockElapsedS(")
    mock_host = function_body(host, "export function mockHostState(")
    for piece in ("Math.min(2100, Math.floor(", "* 0.4))", "Math.max(60, ", "* 6) % span)"):
        assert piece in elapsed, f"mockElapsedS đổi nhịp: {piece}"
        assert piece in mock_host, f"đồng hồ mô phỏng của /host lệch bàn trợ live: {piece}"


# ---------------------------------------------------------------------------
# K5 — khung đầu tự tua luôn có HAI điểm phút
# ---------------------------------------------------------------------------


def _tick(off: int) -> dict:
    return {
        "offset_s": off,
        "ts_bucket": None,
        "viewers": 50,
        "comment_rate": 1,
        "like_rate": 0,
        "click_count": 0,
        "pinned_product_id": None,
        "baseline_viewers": None,
        "baseline_clicks_per_min": None,
    }


K5_DECLS = [
    (USE_REPLAY, ["FIRST_FRAME_MAX_COMMENT_S", "firstFrameOffset"]),
    (RHYTHM_CHART, ["toMinutePoints"]),
]


def test_k5_khung_dau_co_hai_diem_phut_ke_ca_khi_bo_thu_bat_muon(tmp_path):
    cases = {
        "tu_dau": ([0, 30, 60, 90], []),
        "tick_dau_90": ([90, 120, 150], []),
        "bat_muon_10_phut": ([600, 630, 660, 690], [610]),
        "bat_muon_2_phut": ([120, 150, 180], [130]),
        "tick_lon_xon": ([630, 600, 690, 660], []),
    }
    recs = {
        k: {
            "ticks": [_tick(o) for o in offs],
            "comments": [{"offset_s": c} for c in cm],
            "duration_s": 3600,
        }
        for k, (offs, cm) in cases.items()
    }
    expr = (
        f"Object.fromEntries(Object.entries({js(recs)}).map(([k, r]) => {{"
        " const t = firstFrameOffset(r);"
        " return [k, [t, toMinutePoints(r.ticks.filter((x) => x.offset_s <= t)).length]];"
        " }))"
    )
    got = node_eval(tmp_path, K5_DECLS, expr)
    for name, (t, points) in got.items():
        assert points >= 2, f"{name}: tự tua tới {t}s mà biểu đồ chỉ có {points} điểm phút"
    assert got["bat_muon_10_phut"][0] == 660
    assert got["tu_dau"][0] == 60


def test_k5_mot_phut_so_lieu_thi_khong_tu_tua(tmp_path):
    rec = {"ticks": [_tick(600), _tick(630)], "comments": [], "duration_s": 3600}
    assert node_eval(tmp_path, K5_DECLS, f"firstFrameOffset({js(rec)})") == 0


def test_k5_cau_nhac_khong_noi_qua_so_lieu():
    prompt = function_body(code(read(REPLAY_PAGE)), "function playPrompt(")
    assert "phút đầu có số liệu" not in prompt, (
        "tick đầu ở phút 10 thì 'phút đầu có số liệu' không đúng — nói đúng là đủ hai phút"
    )
    assert "đủ hai phút số liệu" in prompt


def test_k5_cau_nhac_chi_noi_du_hai_phut_khi_bieu_do_that_su_co_hai_phut(tmp_path):
    """Khung đầu còn có thể được tua tới BÌNH LUẬN đầu tiên khi bản ghi chưa có
    phút số liệu thứ hai (tick chỉ ở phút 10, bình luận ở 01:40) — lúc đó biểu
    đồ trống, nên câu nhắc không được khẳng định "đủ hai phút số liệu"."""
    decls = [
        (FORMAT_TS, ["fmtClock", "fmtMinSec", "fmtElapsed"]),
        (USE_REPLAY, ["FIRST_FRAME_MAX_COMMENT_S", "firstFrameOffset"]),
        (RHYTHM_CHART, ["toMinutePoints"]),
        (REPLAY_PAGE, ["minutesWithData", "playPrompt"]),
    ]
    cases = {
        "chi_binh_luan_truoc_tick": ([600, 630], [100]),
        "mot_phut_tick_va_binh_luan": ([0, 30], [200]),
        "bat_muon_du_hai_phut": ([600, 630, 660], [610]),
        "tu_dau": ([0, 30, 60, 90], []),
    }
    recs = {
        k: {
            "ticks": [_tick(o) for o in offs],
            "comments": [{"offset_s": c} for c in cm],
            "duration_s": 3600,
        }
        for k, (offs, cm) in cases.items()
    }
    expr = (
        f"Object.fromEntries(Object.entries({js(recs)}).map(([k, r]) => {{"
        " const t = firstFrameOffset(r);"
        " const visibleTicks = r.ticks.filter((x) => x.offset_s <= t);"
        " const rp = { recording: r, playing: false, speed: 30, t, firstFrameS: t, visibleTicks };"
        " return [k, [t, toMinutePoints(visibleTicks).length, playPrompt(rp)]];"
        " }))"
    )
    got = node_eval(tmp_path, decls, expr)
    for name, (t, points, prompt) in got.items():
        assert t > 0, f"{name}: tiền đề là khung đầu đã được tự tua"
        assert prompt.startswith("Đã tua sẵn tới"), f"{name}: {prompt!r}"
        if points >= 2:
            assert "đủ hai phút số liệu" in prompt, f"{name}: {prompt!r}"
        else:
            assert "đủ hai phút" not in prompt, (
                f"{name}: biểu đồ có {points} điểm phút mà câu nhắc nói đủ hai phút: {prompt!r}"
            )
            assert "bình luận đầu tiên" in prompt
    assert got["chi_binh_luan_truoc_tick"][:2] == [100, 0]
    assert got["mot_phut_tick_va_binh_luan"][:2] == [200, 1]
    assert got["bat_muon_du_hai_phut"][1] >= 2


# ---------------------------------------------------------------------------
# K6 — "Bắt đầu xem thử" luôn là bản mô phỏng ngoại tuyến
# ---------------------------------------------------------------------------


def test_k6_ma_mock_trong_link_buoc_che_do_mo_phong(tmp_path):
    got = node_eval(
        tmp_path,
        [(USE_REPLAY, ["SAMPLE_ID_PREFIX", "isSampleSessionId"])],
        "['mock-ended-01', 'mock-analysis-01', '3fa85f64-5717-4562-b3fc-2c963f66afa6', null, '']"
        ".map(isSampleSessionId)",
    )
    assert got == [True, True, False, False, False]
    home = read(SRC / "app" / "page.tsx")
    for sid in re.findall(r"/replay\?session=([\w-]+)", home):
        assert sid.startswith("mock-"), f"trang chủ mở bản xem thử bằng mã {sid} không có tiền tố"

    hook = code(read(USE_REPLAY))
    i_sample = hook.index("if (wantSample) {")
    i_list = hook.index("listSessions(2500)")
    assert i_sample < i_list, "mã mock phải được xét TRƯỚC khi hỏi máy chủ"
    between = hook[i_sample:i_list]
    assert re.search(
        r"const reason = sampleLinkMockReason\(connectionRef\.current\);\s*"
        r"if \(reason\) switchToMock\(reason\);\s*return;",
        between,
    ), "link xin bản xem thử thì KHÔNG gọi máy chủ — máy chủ sống sẽ mở một buổi thật"
    assert "connectionRef.current = connection;" in hook
    assert "}, [switchToMock, wantSample]);" in hook


def test_k6_xem_thu_khi_may_chu_song_va_co_buoi_that_da_ket_thuc(api, tmp_path):
    """Kịch bản E2E: máy chủ SỐNG, đã có một buổi THẬT kết thúc, bấm "Bắt đầu
    xem thử" → /replay?session=mock-ended-01. Trước khi sửa, hook hỏi máy chủ,
    pickReplaySession bỏ qua mã mock và mở buổi thật kèm nhãn "DỮ LIỆU THẬT"."""
    client, store = api
    real = _real_live_session(client, store, minutes_ago=30)
    assert client.post(f"/sessions/{real}/end").status_code == 200
    rows = client.get("/sessions").json()
    assert any(r["session_id"] == real and r["status"] == "ended" for r in rows)
    decls = [
        (FORMAT_TS, ["TZ", "dateFmt", "fmtDateHCM"]),
        (
            USE_REPLAY,
            [
                "SAMPLE_ID_PREFIX",
                "isSampleSessionId",
                "sampleLinkMockReason",
                "finishedAt",
                "endedNewestFirst",
                "pickReplaySession",
            ],
        ),
        (REPLAY_PAGE, ["provenanceText"]),
    ]
    sid = "mock-ended-01"
    expr = (
        "(() => {"
        f" const rows = {js(rows)};"
        f" const oldPick = pickReplaySession(endedNewestFirst(rows), {js(sid)});"
        f" const want = isSampleSessionId({js(sid)});"
        " const reason = want ? sampleLinkMockReason('connecting') : null;"
        " const rp = { connection: reason ? 'mock' : 'live', mockReason: reason };"
        " return [oldPick && oldPick.session_id, want, reason, provenanceText(rp, oldPick),"
        "  provenanceText({ connection: 'live', mockReason: null }, oldPick)];"
        "})()"
    )
    old_pick, want, reason, banner, old_banner = node_eval(tmp_path, decls, expr)
    assert old_pick == real, "tiền đề: đường cũ (hỏi máy chủ) mở nhầm buổi thật"
    assert old_banner.startswith("PHÁT LẠI DỮ LIỆU THẬT"), "tiền đề: đường cũ in nhãn THẬT"
    assert want is True
    assert reason == "sample", "máy chủ sống vẫn phải buộc chạy bản mô phỏng"
    assert banner.startswith("PHÁT LẠI DỮ LIỆU MÔ PHỎNG")
    assert "THẬT" not in banner
    page = code(read(REPLAY_PAGE))
    assert "const isSample = isMock || shown?.is_demo === true;" in page, (
        "chế độ mô phỏng phải kèm huy hiệu DEMO — dữ liệu mẫu"
    )


def test_k6_chon_ban_mo_phong_khac_khi_mat_may_chu_giu_ly_do_cu(tmp_path):
    """Đang mô phỏng vì mất máy chủ, chọn bản khác trong ô chọn phiên →
    `selectSession` ghi `?session=mock-…` vào link. Lý do "chưa kết nối được
    máy chủ" không được bị thay bằng "bản xem thử"."""
    got = node_eval(
        tmp_path,
        [(USE_REPLAY, ["sampleLinkMockReason"])],
        "['connecting', 'live', 'mock'].map(sampleLinkMockReason)",
    )
    assert got == ["sample", "sample", None]
    page = code(read(REPLAY_PAGE))
    assert "router.replace(`/replay?session=${encodeURIComponent(id)}`" in page, (
        "tiền đề: chọn phiên ghi mã vào link — mã mock làm hiệu ứng tải danh sách chạy lại"
    )


def test_k6_nhan_ban_xem_thu_la_mo_phong_khong_phai_that(tmp_path):
    decls = [
        (FORMAT_TS, ["TZ", "dateFmt", "fmtDateHCM"]),
        (REPLAY_PAGE, ["provenanceText", "requestNotice"]),
    ]
    rp = {"connection": "mock", "mockReason": "sample", "requestedStatus": "ok"}
    missing = {**rp, "requestedStatus": "not_found"}
    got = node_eval(
        tmp_path,
        decls,
        f"[provenanceText({js(rp)}, null), requestNotice({js(missing)})]",
    )
    banner, notice = got
    assert banner.startswith("PHÁT LẠI DỮ LIỆU MÔ PHỎNG")
    assert "ngoại tuyến" in banner
    assert "máy chủ" not in notice, "bản xem thử không phải vì mất máy chủ — đừng nói sai lý do"


# ---------------------------------------------------------------------------
# K7 — buổi chạy thử (dry_run) không bao giờ là "DỮ LIỆU THẬT"
# ---------------------------------------------------------------------------


def test_k7_phien_chay_thu_nap_nguon_mo_phong_khong_in_du_lieu_that(api, tmp_path):
    """Kịch bản đã tái hiện: dry_run → nguồn mô phỏng được phép → kết thúc →
    /replay. Payload bình luận không mang nền tảng nên web chỉ dựa vào cờ phiên."""
    from livelift.api.ingest_jobs import cho_phep_mo_phong

    client, _store = api
    body = {"platform": "youtube", "mode": "suggest", "planned_duration_min": 30, "dry_run": True}
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]
    row = next(x for x in client.get("/sessions").json() if x["session_id"] == sid)
    assert row["is_demo"] is False
    assert row["dry_run"] is True
    assert cho_phep_mo_phong(row), "tiền đề: phiên chạy thử được nạp bình luận mô phỏng"
    assert not cho_phep_mo_phong({**row, "dry_run": False}), (
        "tiền đề: phiên THẬT không bao giờ mang bình luận mô phỏng — nên chữ 'THẬT' chỉ an "
        "toàn khi cả is_demo lẫn dry_run đều tắt"
    )
    ended = {**row, "status": "ended", "start_ts": "2026-09-17T09:00:00Z"}
    real = {**ended, "dry_run": False}
    decls = [
        (FORMAT_TS, ["TZ", "dateFmt", "fmtDateHCM"]),
        (REPLAY_PAGE, ["provenanceText"]),
        (REPLAY_CONTROLS, ["sessionLabel"]),
    ]
    live_rp = {"connection": "live", "mockReason": None}
    got = node_eval(
        tmp_path,
        decls,
        f"[provenanceText({js(live_rp)}, {js(ended)}), provenanceText({js(live_rp)}, {js(real)}),"
        f" sessionLabel({js(ended)})]",
    )
    dry, real_text, label = got
    assert "THẬT" not in dry, f"phiên chạy thử bị in là dữ liệu thật: {dry!r}"
    assert "CHẠY THỬ" in dry
    assert "mô phỏng" in dry
    assert real_text.startswith("PHÁT LẠI DỮ LIỆU THẬT"), "phiên thật vẫn được gọi đúng tên"
    assert "chạy thử" in label

    page = code(read(REPLAY_PAGE))
    assert "const isDryRun = !isSample && shown?.dry_run === true;" in page
    i = page.index("{isDryRun ?")
    assert "CHẠY THỬ" in page[i : i + 120], "phiên chạy thử cần huy hiệu riêng cạnh dải băng"
