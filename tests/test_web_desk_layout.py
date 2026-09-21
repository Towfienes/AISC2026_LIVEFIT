"""Layout + failure-visibility gate for the control desk (gói UI-2).

Gói UI-1 fixed the type scale; the audit that followed found the *structure*
still broken, and none of it was visible to any existing test:

1. the single most-glanced fact of a live session (khối hiện tại BẬT/TẮT and
   the countdown to the boundary) rode inside a paragraph of hint text at the
   same size and the same white as its own annotation;
2. the desk was fitted to 1920x1080 with two nested ``overflow-hidden`` planes
   and NOT ONE breakpoint — at 1366x768 the "lượt bấm/phút" panel (the primary
   outcome of the experiment) collapsed to ~4 px and the action-card column was
   cut to a third of a card with nothing to say so;
3. ``onExecute={() => void desk.execute(c)}`` threw the rejection of a failed
   command into an unhandled promise: the card silently rolled back and the
   operator was never told the pin had not happened.

`tsc --noEmit` cannot see any of that — it type-checks types, not layout or
promise handling. These tests read the desk render path off disk and hold the
four properties gói UI-2 exists to guarantee: a display-sized operating clock,
a responsive layout with real minimum heights, an error that reaches the
operator, and the blinding boundary (rule L6) still intact.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
SRC = WEB / "src"
DESK_PAGE = SRC / "app" / "desk" / "page.tsx"
BLOCK_CLOCK = SRC / "components" / "BlockClock.tsx"
STATUS_BAR = SRC / "components" / "StatusBar.tsx"
BLOCK_STRIP = SRC / "components" / "BlockStrip.tsx"
ACTION_CARD = SRC / "components" / "ActionCard.tsx"

# Every component the /desk route actually renders (plus the shared primitives
# it renders them with). Used by the sweeping gates below.
# Gói UI-KOL (09/2026) added LiveVideo (khung xem live) and SignalTiles (dải
# thẻ tín hiệu) to the render path — they are swept by the same gates.
DESK_COMPONENTS = [
    "BlockClock.tsx",
    "StatusBar.tsx",
    "BlockStrip.tsx",
    "ActionCard.tsx",
    "CommentFeed.tsx",
    "CommentRadar.tsx",
    "RhythmChart.tsx",
    "LiveVideo.tsx",
    "SignalTiles.tsx",
    "TopNav.tsx",
    "Term.tsx",
]

# Anything that belongs to the BLINDED host view. The desk is the operator
# screen and may see the assignment; the moment one of these names appears on
# the desk render path, the two models have been crossed (rule L6).
HOST_ONLY = ("HostView", "useHost", "HostState")


def desk_render_path() -> dict[str, str]:
    """`{relative path: source}` for every file the /desk route renders."""
    files = [DESK_PAGE] + [SRC / "components" / name for name in DESK_COMPONENTS]
    files += sorted((SRC / "components" / "ui").glob("*.tsx"))
    out: dict[str, str] = {}
    for path in files:
        assert path.exists(), f"không tìm thấy {path} — đường render /desk đã đổi?"
        out[path.relative_to(WEB).as_posix()] = path.read_text(encoding="utf-8")
    return out


def code(src: str) -> str:
    """`src` with comments removed.

    Every gate below asks "does the RENDERED desk do X". The files are heavily
    commented — with the very anti-patterns being banned, quoted so the next
    maintainer knows what went wrong — so a naive substring search would find
    `void desk.execute` in the paragraph explaining why it was removed.
    """
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


def _opening_tag(src: str, start: int) -> str:
    """Text of the JSX tag beginning at `start`, up to its unbraced `>`."""
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


def _before(src: str, needle: str, window: int = 400) -> str:
    """The `window` characters just before `needle` (the element's own tag)."""
    i = src.index(needle)
    return src[max(0, i - window) : i]


# --------------------------------------------------------------------------
# 1. the operating clock — the desk's hero, not a line of hint text
# --------------------------------------------------------------------------
def test_current_block_is_rendered_at_display_size():
    """Trạng thái khối + đếm ngược phải ở bậc hiển thị, không phải bậc chú thích.

    CẬP NHẬT CÓ CHỦ ĐÍCH (gói DESK-HOST v2, 09/2026 — mockup mock_desk.png):
    hai chỉ số vận hành (người xem, lượt bấm/phút) CHUYỂN từ đồng hồ khối sang
    cột KPI (SignalTiles) để hero chỉ còn đúng một việc — trạng thái khối; nhãn
    đếm ngược đổi "Còn đến ranh giới khối" → "Chuyển khối sau" (ngôn ngữ
    việc-cần-làm). BẤT BIẾN GIỮ NGUYÊN: mọi con số vẫn ở bậc hiển thị có nhãn
    thật — phần KPI được khẳng định ở nửa dưới của test, trên SignalTiles.
    """
    src = code(BLOCK_CLOCK.read_text(encoding="utf-8"))

    # v2: đếm ngược num-l (56px) ở màn thiết kế, num-m dự phòng — hạ một bậc so
    # với num-xl của UI-2 để tổng chiều cao hero ≤ ~300px và desk 1920×1080
    # KHÔNG cuộn (ràng buộc f4 của spec, đo lại bằng ảnh chụp); 56px mono vẫn
    # là bậc hiển thị, đọc được từ 2 mét.
    countdown = _before(src, 'role="timer"', 700) + src[src.index('role="timer"') :][:400]
    assert "xl:text-num-l" in countdown, (
        "đếm ngược tới ranh giới khối phải đạt bậc num-l (56px) trên màn thiết kế"
    )
    assert "text-num-m" in countdown, "đếm ngược thiếu bậc dự phòng num-m cho màn hẹp"
    assert "Chuyển khối sau" in src, "thiếu nhãn tiếng Việt cho đếm ngược ranh giới khối"

    # CẬP NHẬT CÓ CHỦ ĐÍCH (gói C5 — liếc 1 giây ở 1366×768): chữ trạng thái
    # BẬT/TẮT đứng CẠNH đếm ngược (hero hai cột) ở bậc num-m (40px) thay vì
    # chồng lên nó ở num-l — ảnh f06 đo được chữ ~40px đã đọc được ngay, còn
    # hero một cột cao ~285px đẩy nút Thực hiện của thẻ #1 xuống dưới mép màn.
    # Bất biến giữ nguyên: chữ trạng thái vẫn ở bậc HIỂN THỊ (num-*), không
    # phải bậc chữ thường.
    word = _before(src, "{heroWord}", 300)
    assert "text-num-m" in word, "chữ trạng thái khối phải ở bậc hiển thị num-m (40px)"
    assert "font-display" in word, "chữ trạng thái là CHỮ — font display, không phải mono số"
    assert "text-label" in src, "nhãn của thẻ khối phải ở bậc label"

    # Hero v2 phải GIẢI THÍCH trạng thái bằng một câu người thường (spec UX-FLOW
    # e2: "hệ thống đang điều khiển" vs "vận hành như thường lệ").
    assert "Hệ thống đang điều khiển việc ghim sản phẩm" in src
    assert "Khối đối chứng — hệ thống cố ý không đưa gợi ý" in src
    assert "hãy vận hành như bình thường để đo mức nền" in src

    # ... and the vitals — now KPI tiles — keep display figures with a real
    # label, not a bare number glued to a sentence.
    tiles = code((SRC / "components" / "SignalTiles.tsx").read_text(encoding="utf-8"))
    assert "text-num-s" in tiles, "số KPI phải ở bậc hiển thị (num-s trở lên) trên cột KPI"
    assert "text-label" in tiles, "ô KPI phải có nhãn ở bậc label"
    for label in ("Người xem", "Lượt bấm / phút", "Bình luận / phút"):
        assert label in tiles, f"thiếu nhãn tiếng Việt {label!r} trên cột KPI"


def test_block_status_carries_a_shape_and_a_word_not_only_a_colour():
    """BẬT và TẮT từng in cùng một màu trắng, không nền, không ký hiệu."""
    src = code(BLOCK_CLOCK.read_text(encoding="utf-8"))
    assert "StatusMark" in src, "chip trạng thái khối thiếu kênh HÌNH DẠNG"
    assert re.search(r"<StatusMark[^>]*size=\{\d+\}", src), (
        "ký hiệu trạng thái phải được phóng to theo chữ 56px, nếu không kênh "
        "hình dạng biến mất bên cạnh con chữ hiển thị"
    )
    assert "STATUS_TEXT" in src, "chip trạng thái phải lấy CHỮ từ bảng STATUS_TEXT dùng chung"

    chip = re.search(r"const CHIP: Record<StatusShape, string> = \{(.*?)\n\};", src, re.S)
    assert chip, "không đọc được bảng nền/mực của chip trạng thái"
    body = chip.group(1)
    for shape in ("on", "off", "drift"):
        assert re.search(rf"\n\s+{shape}:", body), f"chip thiếu nền riêng cho trạng thái {shape!r}"
    fills = re.findall(r"\n\s+\w+:\s*\"([^\"]*)\"", body)
    assert len(set(fills)) == 3, f"ba trạng thái phải có ba nền khác nhau — hiện có: {fills}"


def test_the_operating_clock_is_pinned_and_comes_first():
    """Ưu tiên 1: đồng hồ khối không được cuộn mất khỏi tầm mắt."""
    src = code(DESK_PAGE.read_text(encoding="utf-8"))
    assert "<BlockClock" in src, "trang /desk không còn dựng đồng hồ khối"
    assert "sticky top-0" in src, "khối tiêu điểm phải dính đầu màn hình khi trang cuộn"
    # It has to sit inside that sticky wrapper, before the analysis panels.
    assert src.index("sticky top-0") < src.index("<BlockClock"), (
        "đồng hồ khối phải nằm trong vùng dính đầu màn hình"
    )
    assert src.index("<BlockClock") < src.index("<RhythmChart"), (
        "đồng hồ khối phải đứng trước biểu đồ trong thứ tự ưu tiên"
    )


# --------------------------------------------------------------------------
# 2. responsive: no 1920x1080 assumption, real minimum heights
# --------------------------------------------------------------------------
def test_desk_layout_is_not_fitted_to_one_screen_size():
    src = code(DESK_PAGE.read_text(encoding="utf-8"))
    assert "overflow-hidden" not in src, (
        "hai tầng overflow-hidden là cách nội dung bị CẮT ở 1366x768 — bỏ hẳn "
        "trên mặt phẳng bố cục của /desk"
    )
    assert not re.search(r"(?<![-\w])h-screen\b", src), (
        "chiều cao khoá cứng theo màn hình là giả định 1920x1080 — dùng min-h-screen"
    )
    assert "min-h-screen" in src, "trang phải cao tối thiểu bằng màn hình rồi cuộn tiếp"
    assert not re.search(r"basis-\[\d+%\]", src), (
        "chia tỉ lệ cứng (basis-[40%]) không sống được ở 768px chiều cao"
    )


def test_desk_layout_declares_breakpoints():
    """Bố cục cũ không có MỘT breakpoint nào."""
    src = code(DESK_PAGE.read_text(encoding="utf-8"))
    breakpoints = set(re.findall(r"\b(sm|md|lg|xl|2xl):", src))
    assert breakpoints, "đường render /desk không khai báo breakpoint nào"
    grid = re.findall(r"(?:sm|md|lg|xl|2xl):grid-(?:cols|rows)-\[[^\]]+\]", src)
    assert grid, "lưới chính phải đổi hình theo breakpoint, không phải grid-cols-2 cố định"
    assert not re.search(r'className="[^"]*\bgrid-cols-2\b', src), (
        "grid-cols-2 cố định là lý do cột thẻ hành động bị bóp ở 1366px"
    )


def test_every_panel_declares_a_minimum_height():
    """Biểu đồ 'lượt bấm/phút' từng sập còn ~4px vì không có sàn chiều cao."""
    src = code(DESK_PAGE.read_text(encoding="utf-8"))
    floors = re.findall(r"min-h-\[([\d.]+)rem\]", src)
    assert len(floors) >= 3, (
        f"mỗi vùng (thẻ hành động, biểu đồ, radar+feed) cần một sàn chiều cao — mới có {floors}"
    )
    assert min(float(f) for f in floors) >= 6, "sàn chiều cao dưới 6rem thì vùng vẫn coi như sập"

    # The chart's own container, not just the card around it.
    chart_tag = _before(src, "<RhythmChart")
    assert "min-h-[" in chart_tag, (
        "khung chứa biểu đồ nhịp phiên phải có sàn chiều cao riêng — đây là chỗ "
        "chỉ số đầu ra chính của thí nghiệm bị sập về 4px"
    )

    # ... and the grid tracks themselves carry floors rather than pure fractions.
    tracks = re.findall(r"(?:sm|md|lg|xl|2xl):grid-rows-\[([^\]]+)\]", src)
    assert tracks, "lưới chính chưa khai báo hàng theo breakpoint"
    bare = [t for t in tracks if "minmax(" not in t]
    assert not bare, f"hàng của lưới phải dùng minmax(sàn, tỉ lệ) thay vì tỉ lệ trần: {bare}"


def test_overflow_is_scrollable_with_a_visible_cue():
    """Cắt nội dung im lặng là lỗi; cuộn có chỉ báo thì không."""
    src = code(DESK_PAGE.read_text(encoding="utf-8"))
    assert "overflow-y-auto" in src, "danh sách thẻ hành động phải cuộn được"
    assert "useIsOverflowing" in src, "thiếu phát hiện tràn khung cho danh sách thẻ"
    assert "cuộn để xem hết" in src, (
        "khi danh sách dài hơn khung phải có dòng chữ tiếng Việt nói rõ là cuộn được"
    )


def test_status_bar_wraps_instead_of_squeezing():
    src = code(STATUS_BAR.read_text(encoding="utf-8"))
    assert "flex-wrap" in src, (
        "thanh trạng thái cố định một dòng sẽ đẩy nút Kết thúc phiên ra ngoài ở 1366px"
    )
    assert "min-h-bar" in src, "thanh trạng thái phải cao TỐI THIỂU 44px, không phải đúng 44px"
    assert not re.search(r"(?<![-\w])h-bar\b", src), (
        "h-bar khoá cứng chiều cao nên hàng thứ hai không có chỗ"
    )


def test_block_strip_legend_wraps_instead_of_truncating():
    """CẬP NHẬT CÓ CHỦ ĐÍCH (gói C — Bàn trợ live v3): câu ranh giới làm mù đổi
    sang THUẬT NGỮ THỐNG NHẤT của dự án ("Bàn trợ live", "Màn người dẫn") thay
    cho "bàn điều khiển"/"màn hình host" (lẫn tiếng Anh). Bất biến giữ nguyên:
    câu phải có và không bao giờ bị `truncate`."""
    src = code(BLOCK_STRIP.read_text(encoding="utf-8"))
    assert "flex-wrap" in src, "chú giải dải khối phải xuống dòng thay vì bị cắt"
    marker = "Chỉ hiện trên bàn trợ live — màn người dẫn không thấy khối"
    assert marker in src, "mất cảnh báo ranh giới làm mù"
    assert "màn hình host" not in src, "câu làm mù còn lẫn chữ 'host' — dùng 'màn người dẫn'"
    note = _before(src, marker, 200)
    assert "truncate" not in note, (
        "câu cảnh báo làm mù bị `truncate` cắt còn một nửa trên màn hẹp — "
        "đúng dòng không bao giờ được đọc dở"
    )


# --------------------------------------------------------------------------
# 3. a failed command has to reach the operator
# --------------------------------------------------------------------------
def test_execute_rejection_is_not_swallowed():
    src = code(DESK_PAGE.read_text(encoding="utf-8"))
    assert not re.search(r"void\s+desk\.execute", src), (
        "`void desk.execute(...)` ném lỗi vào promise không ai bắt: thẻ tự lùi "
        "lại còn người vận hành không biết lệnh đã trượt"
    )
    call = src.index("desk.execute(")
    assert ".catch(" in src[call : call + 400], "lời gọi desk.execute phải có .catch"
    assert "setAlert(" in src[call : call + 800], "lỗi phải được đưa lên ô thông báo của thanh"


def test_the_error_lands_in_a_reserved_slot_not_on_top_of_the_figures():
    page = code(DESK_PAGE.read_text(encoding="utf-8"))
    bar = code(STATUS_BAR.read_text(encoding="utf-8"))
    assert "alert={" in page, "trang /desk chưa truyền lỗi vào ô dành sẵn của StatusBar"
    for name, src in (("desk/page.tsx", page), ("StatusBar.tsx", bar)):
        assert "onDismissAlert" in src, (
            f"{name}: thông báo lỗi phải do người vận hành tự đóng, không tự biến mất"
        )
    assert re.search(r"\balert\??:", bar), "StatusBar chưa có prop cho ô thông báo"
    # Not a toast, not a modal, not an overlay over the numbers.
    for name, src in (("desk/page.tsx", page), ("StatusBar.tsx", bar)):
        assert not re.search(r"\btoast\b", src, re.I), f"{name}: không dùng toast cho lỗi vận hành"
        assert not re.search(r"\bmodal\b|\bdialog\b", src, re.I), f"{name}: không dùng modal/dialog"
        assert not re.search(r'className="[^"]*\bfixed\b', src), (
            f"{name}: lớp phủ `fixed` sẽ đè lên vùng số liệu"
        )


def test_the_error_message_explains_what_happened_in_vietnamese():
    src = code(DESK_PAGE.read_text(encoding="utf-8"))
    msg = re.search(r"Không thực hiện được thẻ[^;]*?;", src, re.S)
    assert msg, "thiếu chuỗi tiếng Việt giải thích khi lệnh Thực hiện trượt"
    text = msg.group(0)
    assert "trả lại danh sách" in text, (
        "thông báo phải nói rõ thẻ đã được hoàn tác — useDesk.execute lùi thẻ ra "
        "khỏi tập đã thực hiện khi API từ chối"
    )
    assert "thử lại" in text or "lại" in text, "thông báo phải nói bước tiếp theo"


# --------------------------------------------------------------------------
# 4. target sizes on the desk
# --------------------------------------------------------------------------
def test_the_primary_action_keeps_the_36px_control_height():
    src = code(ACTION_CARD.read_text(encoding="utf-8"))
    assert 'size="sm"' not in src, (
        "Thực hiện / Bỏ qua là hành động chính của bàn — phải giữ cỡ md (36px), "
        "không rơi về cỡ dày đặc 24px"
    )
    for label in ("Thực hiện", "Bỏ qua"):
        assert label in src, f"mất nút {label!r} trên thẻ hành động"


def test_every_raw_button_on_the_desk_meets_the_24px_target_floor():
    """SC 2.5.8: 24x24 CSS px. `<Button>` lo phần của nó; `<button>` trần thì không."""
    ok = ("min-h-tap", "min-h-ctl", "h-ctl", "h-bar", "buttonCls")
    offenders: list[str] = []
    for rel, src in desk_render_path().items():
        for m in re.finditer(r"<button[\s\n]", src):
            tag = _opening_tag(src, m.start())
            if not any(token in tag for token in ok):
                offenders.append(f"{rel}:{src[: m.start()].count(chr(10)) + 1}")
    assert not offenders, "Nút không ghim được sàn 24x24px (WCAG 2.2 SC 2.5.8):\n" + "\n".join(
        offenders
    )


# --------------------------------------------------------------------------
# 5. the type scale still holds on the desk, and the blinding boundary too
# --------------------------------------------------------------------------
def test_no_sub_scale_type_returns_to_the_desk():
    offenders: list[str] = []
    for rel, raw in desk_render_path().items():
        for m in re.finditer(r"text-\[(\d+)px\]|text-xs\b", code(raw)):
            offenders.append(f"{rel}:{raw[: m.start()].count(chr(10)) + 1} {m.group(0)}")
    assert not offenders, (
        "Đường render /desk quay lại cỡ chữ ngoài thang (10/11/12px):\n" + "\n".join(offenders)
    )


def test_the_desk_never_touches_the_blinded_host_model():
    """Rule L6: /desk là màn OPERATOR, /host bị làm mù — hai model không được chạm nhau."""
    offenders: list[str] = []
    for rel, raw in desk_render_path().items():
        # Comments are stripped on purpose: naming the forbidden model in a
        # "do not import this" note is exactly what the boundary needs.
        src = code(raw)
        for name in HOST_ONLY:
            if re.search(rf"\b{name}\b", src):
                offenders.append(f"{rel}: {name}")
    assert not offenders, (
        "Đường render /desk chạm vào model của màn hình host bị làm mù:\n" + "\n".join(offenders)
    )


def test_the_operating_clock_is_documented_as_operator_only():
    """Một người sửa sau phải đọc được ranh giới ngay trong file."""
    src = BLOCK_CLOCK.read_text(encoding="utf-8")
    head = src[: re.search(r"(?m)^import ", src).start()]
    assert "OPERATOR" in head, "BlockClock thiếu ghi chú ranh giới làm mù ở đầu file"
    assert "HostView" in head, "ghi chú phải nêu đích danh file không được import nó"
