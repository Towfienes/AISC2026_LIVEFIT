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
"""

from __future__ import annotations

import re
from pathlib import Path

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
    assert "offset_s >= 60" in first, "biểu đồ cần hai điểm phút — khung đầu phải qua phút 1"
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
    assert "listSessions(" in pull, "danh sách phiên phải được đọc lại TRONG vòng poll"
    assert "pickCurrentSession(" in pull, "phiên đang live phải được chọn lại TRONG vòng poll"
    loop = src[src.index("const loop = async () => {") :]
    assert "await pull()" in loop, "vòng poll phải gọi hàm chọn phiên"
    assert "setTimeout(loop" in loop, "vòng poll phải tự nối đuôi"
    assert not re.search(r"listSessions\(2500\)\s*\.then", src), (
        "chọn phiên bằng một lời gọi .then lúc tải chính là lỗi khoá nhầm phiên"
    )
    assert 'pickCurrentSession(list.filter((s) => s.status === "live"))' in pull, (
        "không có tham số thì chỉ chiếu phiên ĐANG live — hàng ghim của buổi đã kết thúc "
        "có thể khiến người dẫn giới thiệu nhầm"
    )


def test_d7_ma_trong_link_uu_tien_tuyet_doi():
    src = code(read(USE_HOST))
    pull = pull_body(src)
    i_req = pull.index("if (requested) {")
    assert i_req < pull.index("pickCurrentSession("), (
        "nhánh ?session= phải được xét trước việc tự chọn phiên"
    )
    req_block = pull[i_req : pull.index("if (!list) {")]
    assert "getHostState(requested)" in req_block
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
    assert fields == {"host", "connection", "degraded", "sessionNotFound", "sampleData"}, (
        f"useHost chỉ được trả HostState + cờ đường truyền/nhãn, thấy: {sorted(fields)}"
    )
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
