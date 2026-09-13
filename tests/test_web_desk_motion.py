"""Chuyển động có mục đích trên bàn điều khiển (gói UI-3).

Gói UI-1 sửa thang chữ, UI-2 sửa bố cục. Lần rà soát sau đó tìm ra một lớp lỗi
mà cả `tsc --noEmit` lẫn hai bộ gate kia đều không thấy: CHUYỂN ĐỘNG.

1. `animate-pulse` chạy trên chấm TRỰC TIẾP — một nhịp đập không bao giờ dừng
   suốt 90 phút phát sóng, ngay cạnh vùng số liệu người vận hành phải đọc. Nó
   không báo điều gì mới; nó chỉ là nhiễu nền.
2. Playhead trên dải khối chạy bằng `left` và thanh tiến trình bằng `width`:
   hai thuộc tính buộc trình duyệt bố trí lại toàn trang mỗi giây, ngay cạnh
   một biểu đồ đang vẽ.
3. Feed bình luận TỰ CUỘN mà không có nút dừng — vi phạm WCAG 2.2.2, và cách
   duy nhất để dừng là "cuộn lên rồi đừng đụng vào".
4. Bộ chọn chế độ Gợi ý / Tự động dùng hai `aria-pressed` rời rạc: trình đọc
   màn hình hiểu là hai công tắc độc lập, có thể bật cả hai hoặc không bật cái
   nào — trong khi đúng một chế độ luôn được chọn.
5. Không có gì ngăn một `<Tooltip>` Recharts thiếu `isAnimationActive={false}`
   len vào và cho cả biểu đồ vẽ lại 12 lần mỗi phút.

Các gate dưới đây đọc thẳng nguồn của đường render /desk và giữ đúng những luật
mà gói UI-3 tồn tại để giữ.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
SRC = WEB / "src"
GLOBALS = SRC / "app" / "globals.css"
TAILWIND = WEB / "tailwind.config.ts"
DESK_PAGE = SRC / "app" / "desk" / "page.tsx"
MOTION_LIB = SRC / "lib" / "motion.ts"
BLOCK_CLOCK = SRC / "components" / "BlockClock.tsx"
BLOCK_STRIP = SRC / "components" / "BlockStrip.tsx"
STATUS_BAR = SRC / "components" / "StatusBar.tsx"
COMMENT_FEED = SRC / "components" / "CommentFeed.tsx"
ACTION_CARD = SRC / "components" / "ActionCard.tsx"
RHYTHM_CHART = SRC / "components" / "RhythmChart.tsx"
COMMENT_RADAR = SRC / "components" / "CommentRadar.tsx"

# Mọi thành phần /desk thực sự dựng (giống danh sách của gate bố cục).
# Gói UI-KOL thêm LiveVideo + SignalTiles vào đường render — quét cùng luật.
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

# Thời lượng riêng của gói UI-3 (ms) — ngoài thang M3 mà UI-1 đã khoá.
UI3_DURATIONS = {
    "tick": 1000,  # playhead + thanh tiến trình, khớp nhịp tick 1 giây
    "enter": 180,  # dòng bình luận / thẻ mới
    "switch": 280,  # chuyển khối BẬT ↔ TẮT (khoảng cho phép: 250–300ms)
    "flash-in": 120,
    "flash-out": 400,
}


def code(src: str) -> str:
    """`src` đã bỏ chú thích.

    Các file này giải thích chính những phản-mẫu bị cấm (và trích dẫn tên lớp
    của chúng) để người sửa sau biết chuyện gì đã xảy ra — tìm chuỗi thô sẽ bắt
    nhầm phần giải thích.
    """
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


def desk_render_path() -> dict[str, str]:
    """`{đường dẫn tương đối: mã nguồn}` cho mọi file /desk dựng."""
    files = [DESK_PAGE] + [SRC / "components" / name for name in DESK_COMPONENTS]
    files += sorted((SRC / "components" / "ui").glob("*.tsx"))
    out: dict[str, str] = {}
    for path in files:
        assert path.exists(), f"không tìm thấy {path} — đường render /desk đã đổi?"
        out[path.relative_to(WEB).as_posix()] = path.read_text(encoding="utf-8")
    return out


def _opening_tag(src: str, start: int) -> str:
    """Văn bản của thẻ JSX bắt đầu tại `start`, tới dấu `>` không nằm trong ngoặc."""
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


def _element_around(src: str, needle: str) -> str:
    """Thẻ mở của phần tử chứa `needle` (ví dụ một thuộc tính role)."""
    i = src.index(needle)
    start = src.rfind("<", 0, i)
    return _opening_tag(src, start)


def _keyframes(css: str, name: str) -> str:
    m = re.search(rf"@keyframes\s+{re.escape(name)}\s*\{{(.*?)\n\}}", css, re.S)
    assert m, f"thiếu @keyframes {name}"
    return m.group(1)


# --------------------------------------------------------------------------
# 1. đồng hồ và đếm ngược KHÔNG được có hiệu ứng
# --------------------------------------------------------------------------
# Số nhảy mỗi giây mà có transition thì không bao giờ đứng yên đủ lâu để đọc.
MOVING_TRANSITION = re.compile(
    r"transition-transform|transition-all|transition-\[|animate-|motion-(?:enter|switch|flash)"
)


def test_the_countdown_is_never_animated():
    src = code(BLOCK_CLOCK.read_text(encoding="utf-8"))
    timer = _element_around(src, 'role="timer"')
    offenders = MOVING_TRANSITION.findall(timer)
    assert not offenders, (
        "Đếm ngược tới ranh giới khối nhảy mỗi giây: gắn chuyển động vào nó là "
        f"làm nó không bao giờ đứng yên đủ lâu để đọc. Tìm thấy: {offenders}"
    )
    # Chỉ được phép đổi MÀU (báo sắp tới ranh giới), không đổi hình/kích thước.
    assert "transition-colors" in timer, (
        "đếm ngược phải đổi mực mượt khi bước vào ngưỡng cảnh báo ranh giới"
    )


def test_the_session_clock_is_never_animated():
    src = code(STATUS_BAR.read_text(encoding="utf-8"))
    i = src.index("fmtClock(elapsedS)")
    span = _opening_tag(src, src.rfind("<", 0, i))
    assert not MOVING_TRANSITION.search(span), "đồng hồ phiên không được có hiệu ứng"
    assert "tnum" in span, (
        "đồng hồ phải dùng chữ số bảng (tabular-nums), nếu không mỗi giây bề "
        "ngang lại đổi và con số tự rung"
    )


def test_no_permanent_ambient_motion_on_the_desk():
    """`animate-pulse` trên chấm TRỰC TIẾP chạy suốt 90 phút — đã gỡ.

    NGOẠI LỆ CÓ CHỦ ĐÍCH (gói DESK-HOST v2, spec UI-VISUAL c1): đèn ĐANG PHÁT
    (`.live-dot`, keyframes ll-pulse trong globals.css) là chuyển động lặp
    DUY NHẤT được phép trên màn vận hành — quy ước phát sóng toàn cầu, gắn
    trên ĐÈN 8px chứ không phải trên chữ/card, và prefers-reduced-motion tắt
    nó. Gate dưới khoá ngoại lệ ở đúng một chỗ: chỉ StatusBar, chỉ trong nhánh
    status === "live".
    """
    bar = code(STATUS_BAR.read_text(encoding="utf-8"))
    assert "animate-pulse" not in bar, (
        "Chấm TRỰC TIẾP không được nhấp nháy vĩnh viễn: nó không báo điều gì "
        "mới, nhưng nằm ngay cạnh vùng số liệu và bắt mắt vài nghìn lần mỗi "
        "phiên. Trạng thái kết nối đã có ba kênh TĨNH: hình dạng, màu và chữ."
    )
    # Đèn ĐANG PHÁT: đúng một lần trong StatusBar, và phải nằm sau guard live.
    assert bar.count("live-dot") == 1, (
        "`.live-dot` (pulse vô hạn) chỉ được gắn trên MỘT đèn ĐANG PHÁT của "
        "thanh trạng thái — mọc thêm ở chỗ khác là quay lại nhiễu nền"
    )
    guard = bar[: bar.index("live-dot")]
    assert 'status === "live"' in guard[-400:], (
        "đèn ĐANG PHÁT chỉ được sáng khi phiên thật sự đang live — không phải "
        "đèn trang trí thường trực"
    )
    for rel, raw in desk_render_path().items():
        if rel.endswith("StatusBar.tsx"):
            continue
        assert "live-dot" not in code(raw), f"{rel}: `.live-dot` lọt ra ngoài đèn ĐANG PHÁT"
    # Chỉ khung xương chờ tải mới được lặp — nó biến mất ngay khi có dữ liệu.
    offenders: list[str] = []
    for rel, raw in desk_render_path().items():
        if rel.endswith("ui/Skeleton.tsx"):
            continue
        for m in re.finditer(r"animate-(pulse|spin|bounce|ping)", code(raw)):
            offenders.append(f"{rel}:{raw[: m.start()].count(chr(10)) + 1} {m.group(0)}")
    assert not offenders, "Chuyển động lặp vô hạn trên màn vận hành 90 phút:\n" + "\n".join(
        offenders
    )


# --------------------------------------------------------------------------
# 2. count-up cho KPI — có ngưỡng, viết bằng rAF, tôn trọng giảm chuyển động
# --------------------------------------------------------------------------
def test_the_kpi_count_up_has_a_threshold_and_uses_raf():
    src = MOTION_LIB.read_text(encoding="utf-8")
    assert "requestAnimationFrame" in src, "count-up phải chạy bằng rAF, không thêm thư viện"
    assert "cancelAnimationFrame" in src, "phải huỷ rAF khi tháo/ngắt tween, nếu không rò frame"
    tween = re.search(r"tweenMs:\s*(\d+)", code(src))
    assert tween, "không đọc được thời lượng tween KPI"
    assert tween.group(1) == "350", "tween KPI phải là 350ms (token M3 medium3)"
    thr = re.search(r"tweenThreshold:\s*([\d.]+)", code(src))
    assert thr, "không đọc được ngưỡng đáng tween"
    assert abs(float(thr.group(1)) - 0.05) < 1e-9, (
        "phải có ngưỡng 5%: tween 350ms cho '1.204 → 1.207' chỉ làm con số rung"
    )
    body = code(src)
    assert "digitCount" in body, (
        "đổi số chữ số (999 → 1.000) là một sự kiện, phải tween kể cả khi lệch < 5%"
    )
    reduced_motion = "tween chạy bằng JS nên CSS không rút gọn hộ — hook phải tự khoá khi "
    reduced_motion += "người dùng chọn giảm chuyển động"
    assert "usePrefersReducedMotion" in body, reduced_motion
    assert "reduced" in body, reduced_motion


def test_the_kpi_figures_actually_use_the_count_up():
    # CẬP NHẬT CÓ CHỦ ĐÍCH (gói DESK-HOST v2): các con số KPI chuyển từ đồng hồ
    # khối sang cột KPI (SignalTiles) theo mockup mock_desk — bất biến motion
    # giữ nguyên, chỉ đổi chỗ ở: số vẫn phải qua count-up có ngưỡng + nháy nền.
    tiles = code((SRC / "components" / "SignalTiles.tsx").read_text(encoding="utf-8"))
    assert "useCountUp" in tiles, "số KPI phải đi qua count-up"
    assert "<Flash" in tiles, "giá trị vừa đổi phải có nháy nền xác nhận"
    # Đồng hồ khối giữ nháy nền một-lần cho khoảnh khắc chuyển khối (S2).
    clock = code(BLOCK_CLOCK.read_text(encoding="utf-8"))
    assert "<Flash" in clock, "thẻ khối phải nháy nền MỘT lần đúng lúc chuyển khối"


# --------------------------------------------------------------------------
# 3. nháy xác nhận: chỉ đổi nền, alpha ≤ 12%, không đẩy bố cục
# --------------------------------------------------------------------------
def test_the_confirm_flash_only_paints_and_never_moves_layout():
    css = GLOBALS.read_text(encoding="utf-8")
    frames = _keyframes(css, "ll-flash")
    props = set(re.findall(r"(?m)^\s*([a-z-]+):", frames))
    assert props == {"background-color"}, (
        f"nháy xác nhận chỉ được đổi NỀN, không đổi kích thước/vị trí — hiện đổi: {props}"
    )
    alphas = [float(a) for a in re.findall(r"rgba\([^)]*?,\s*([\d.]+)\)", frames)]
    var_alpha = re.search(r"--flash-alpha:\s*([\d.]+)", css)
    assert var_alpha, "thiếu token --flash-alpha"
    alphas.append(float(var_alpha.group(1)))
    assert max(alphas) <= 0.12 + 1e-9, f"alpha nháy vượt trần 12%: {max(alphas)}"

    flash = (SRC / "components" / "ui" / "Flash.tsx").read_text(encoding="utf-8")
    body = code(flash)
    assert "absolute" in body, (
        "lớp nháy phải định vị tuyệt đối — nằm trong luồng bố cục thì nó đẩy "
        "đúng con số mà nó đang xác nhận"
    )
    assert "pointer-events-none" in body, "lớp nháy không được chặn chuột"
    assert "aria-hidden" in body, "lớp nháy là trang trí, không được vào cây trợ năng"
    assert re.search(r"if \(key === 0\) return null", body), (
        "lần gắn đầu tiên không được nháy: mở màn hình lên mà cả bàn nháy một "
        "loạt thì không xác nhận điều gì cả"
    )


# --------------------------------------------------------------------------
# 4. chuyển khối BẬT ↔ TẮT — hiệu ứng "to" DUY NHẤT, 250–300ms, emphasized
# --------------------------------------------------------------------------
def test_the_block_switch_is_a_crossfade_and_a_wipe():
    css = GLOBALS.read_text(encoding="utf-8")
    frames = _keyframes(css, "ll-switch")
    assert "opacity" in frames, "nửa crossfade: trạng thái mới phải mờ dần hiện lên"
    assert "clip-path" in frames, "nửa wipe: chữ trạng thái mới phải quét từ trái sang"
    dur = re.search(r"--dur-switch:\s*(\d+)ms", css)
    assert dur, "thiếu token --dur-switch"
    assert 250 <= int(dur.group(1)) <= 300, (
        f"chuyển khối phải trong khoảng 250–300ms, hiện {dur.group(1)}ms"
    )
    rule = re.search(r"\.motion-switch\s*\{([^}]*)\}", css)
    assert rule, "không đọc được luật .motion-switch"
    assert "--ease-emphasized" in rule.group(1), (
        "chuyển khối dùng easing emphasized cubic-bezier(0.2, 0, 0, 1)"
    )

    src = code(BLOCK_CLOCK.read_text(encoding="utf-8"))
    assert "motion-switch" in src, "đồng hồ khối chưa dùng hiệu ứng chuyển khối"
    assert re.search(r"key=\{switchKey\}", src), (
        "hiệu ứng phải khoá theo trạng thái khối, nếu không nó chạy lại mỗi lần render"
    )
    assert "duration-switch" in src, "mặt chip phải crossfade cùng thời lượng với chữ"


def test_the_boundary_warning_signals_without_blinking():
    src = code(BLOCK_CLOCK.read_text(encoding="utf-8"))
    warn = re.search(r"BOUNDARY_WARN_S\s*=\s*(\d+)", src)
    assert warn, "thiếu ngưỡng cảnh báo sắp tới ranh giới khối"
    assert 15 <= int(warn.group(1)) <= 60, "ngưỡng cảnh báo nên trong khoảng 15–60 giây"
    assert "nearBoundary" in src, "chưa nối ngưỡng cảnh báo vào giao diện"
    assert "text-warn-ink" in src, "cảnh báo phải đổi mực sang hổ phách (kênh tĩnh)"
    # Tín hiệu vào một lần rồi ĐỨNG YÊN — không nhấp nháy đúng lúc cần tập trung.
    i = src.index("Sắp đổi khối")
    chip = src[max(0, i - 500) : i]
    assert "animate-" not in chip, "cảnh báo ranh giới không được nhấp nháy liên tục"


# --------------------------------------------------------------------------
# 5. playhead + thanh tiến trình: transform/GPU, 1000ms linear khớp nhịp tick
# --------------------------------------------------------------------------
def test_the_playhead_moves_by_transform_not_by_left():
    src = code(BLOCK_STRIP.read_text(encoding="utf-8"))
    playhead = src[src.index("positionS != null &&") :][:600]
    assert "translate3d" in playhead or "translateX" in playhead, (
        "playhead phải chạy bằng transform (tổng hợp trên GPU); `left` buộc "
        "trình duyệt bố trí lại cả trang mỗi giây, ngay cạnh biểu đồ đang vẽ"
    )
    assert "transition-transform" in playhead, "playhead phải trôi, không nhảy nấc"
    tick_linear = "playhead phải chạy 1000ms LINEAR để khớp đúng nhịp tick 1 giây"
    assert "duration-tick" in playhead, tick_linear
    assert "ease-linear" in playhead, tick_linear
    assert not re.search(r"transition-\[left\]|transition-all", playhead)


def test_the_block_progress_bar_scales_instead_of_resizing():
    src = code(BLOCK_CLOCK.read_text(encoding="utf-8"))
    i = src.index('role="progressbar"')
    bar = src[i : i + 800]
    assert "scaleX(" in bar, "thanh tiến trình phải dùng scaleX, không animate width"
    same_beat = "thanh tiến trình chạy cùng nhịp 1000ms linear với playhead"
    for token in ("transition-transform", "duration-tick", "ease-linear"):
        assert token in bar, f"{same_beat} (thiếu {token})"
    assert "transition-[width]" not in bar, (
        "animate `width` buộc bố trí lại mỗi giây — đúng thứ transform tránh được"
    )


def test_the_motion_tokens_are_declared_and_collapse_under_reduced_motion():
    css = GLOBALS.read_text(encoding="utf-8")
    for name, ms in UI3_DURATIONS.items():
        assert re.search(rf"--dur-{name}:\s*{ms}ms\s*;", css), f"thiếu token --dur-{name}: {ms}ms"
    block = re.search(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}\n", css, re.S)
    assert block, "không đọc được khối prefers-reduced-motion"
    for name in UI3_DURATIONS:
        assert re.search(rf"--dur-{name}:\s*(0|1)m?s\s*;", block.group(1)), (
            f"--dur-{name} không được rút gọn khi người dùng chọn giảm chuyển động"
        )
    config = TAILWIND.read_text(encoding="utf-8")
    for name in ("tick", "enter", "switch"):
        assert f'{name}: "var(--dur-{name})"' in config, (
            f"tiện ích Tailwind duration-{name} chưa nối vào biến CSS"
        )


# --------------------------------------------------------------------------
# 6. dòng mới vào: fade + 6px, so le ≤ 3 bậc, KHÔNG animate chiều cao
# --------------------------------------------------------------------------
def test_new_rows_enter_without_animating_height():
    css = GLOBALS.read_text(encoding="utf-8")
    frames = _keyframes(css, "ll-enter")
    props = set(re.findall(r"(?m)^\s*([a-z-]+):", frames))
    assert props <= {"opacity", "transform"}, (
        f"dòng mới chỉ được fade + dịch; animate height/max-height sẽ đẩy cả "
        f"danh sách trôi trong lúc người ta đang đọc — hiện đổi: {props}"
    )
    assert "translateY(6px)" in frames, "quãng dịch phải là 6px, đủ thấy mà không nhảy"
    dur = re.search(r"--dur-enter:\s*(\d+)ms", css)
    assert dur, "thiếu token --dur-enter"
    assert int(dur.group(1)) == 180, "dòng mới vào trong 180ms"


def test_the_comment_stagger_is_capped_at_three_rows():
    lib = code(MOTION_LIB.read_text(encoding="utf-8"))
    cap = re.search(r"staggerMax:\s*(\d+)", lib)
    assert cap, "không đọc được trần bậc so le"
    assert int(cap.group(1)) <= 3, (
        "so le tối đa 3 bậc: 20 bình luận vào cùng lúc mà xếp hàng đủ 20 bậc "
        "thì dòng cuối vào sau hơn một giây"
    )
    assert "Math.min(i, MOTION.staggerMax - 1)" in lib, "bậc so le phải bị chặn trần"
    feed = code(COMMENT_FEED.read_text(encoding="utf-8"))
    wired = "feed bình luận chưa nối hiệu ứng vào dòng mới"
    assert "useEnterStagger" in feed, wired
    assert "animationDelay" in feed, wired
    assert "motion-enter" in feed


# --------------------------------------------------------------------------
# 7. WCAG 2.2.2 — nội dung tự cuộn phải có nút dừng
# --------------------------------------------------------------------------
def test_the_auto_scrolling_feed_can_be_paused():
    src = code(COMMENT_FEED.read_text(encoding="utf-8"))
    assert "scrollTo(" in src, "gate này chỉ có nghĩa khi feed thực sự tự cuộn"
    pause_rule = "WCAG 2.2.2: nội dung tự động cuộn phải có cách dừng lại có nhãn rõ ràng "
    pause_rule += "— 'cuộn lên rồi đừng đụng vào' là mẹo ngầm, không phải điều khiển"
    for label in ("Tạm dừng cuộn", "Tiếp tục cuộn"):
        assert label in src, f"{pause_rule} (thiếu {label!r})"
    assert "paused" in src, "thiếu trạng thái tạm dừng"
    assert "bình luận mới" in src, (
        "tạm dừng không được đồng nghĩa với bỏ lỡ: phải đếm và cho nhảy tới dòng mới"
    )


# --------------------------------------------------------------------------
# 8. biểu đồ không được vẽ lại có hiệu ứng sau mỗi lần poll
# --------------------------------------------------------------------------
def test_charts_never_replay_their_draw_animation_on_a_poll():
    animated = ("Line", "Bar", "Area", "Pie", "Tooltip", "Scatter", "RadialBar")
    offenders: list[str] = []
    for path in (RHYTHM_CHART, COMMENT_RADAR):
        raw = path.read_text(encoding="utf-8")
        src = code(raw)
        for name in animated:
            for m in re.finditer(rf"<{name}[\s\n]", src):
                tag = _opening_tag(src, m.start())
                if "isAnimationActive={false}" not in tag:
                    line = src[: m.start()].count("\n") + 1
                    offenders.append(f"{path.name}:{line} <{name}>")
    assert not offenders, (
        "Bàn poll số liệu 5 giây một lần; thiếu `isAnimationActive={false}` là "
        "cho cả biểu đồ tự vẽ lại 12 lần mỗi phút, suốt 90 phút:\n" + "\n".join(offenders)
    )


# --------------------------------------------------------------------------
# 9. trợ năng: vai trò ARIA thật cho bộ chọn chế độ + điều hướng bàn phím
# --------------------------------------------------------------------------
def test_the_mode_segmented_control_uses_a_real_radio_group():
    src = code(STATUS_BAR.read_text(encoding="utf-8"))
    assert 'role="radiogroup"' in src, (
        "hai nút `aria-pressed` rời rạc nói rằng có thể bật cả hai hoặc không "
        "bật cái nào; ở đây đúng một chế độ luôn được chọn — đó là radiogroup"
    )
    assert 'role="radio"' in src, "mỗi lựa chọn chế độ phải là một radio"
    assert "aria-checked" in src, "radio phải nói rõ cái nào đang được chọn"
    assert not re.search(r"aria-pressed=\{mode ===", src), (
        "bỏ hẳn aria-pressed trên bộ chọn chế độ, không dùng lẫn với radio"
    )
    for key in ("ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Home", "End"):
        assert key in src, f"radiogroup thiếu điều hướng bàn phím phím {key}"
    assert "tabIndex={selected ? 0 : -1}" in src, (
        "roving tabindex: Tab phải đi qua cả nhóm bằng một lần bấm, không phải hai"
    )
    assert "focus-ring-inset" in src, "nhóm overflow-hidden cần vòng focus inset"


def test_live_regions_do_not_chatter():
    """`aria-live` chỉ đặt ở chỗ nói ÍT — vùng đọc liên tục sẽ bị người dùng tắt."""
    offenders: list[str] = []
    for rel, raw in desk_render_path().items():
        src = code(raw)
        for m in re.finditer(r'aria-live="(\w+)"', src):
            if m.group(1) not in ("polite", "off"):
                line = src[: m.start()].count("\n") + 1
                offenders.append(f"{rel}:{line} aria-live={m.group(1)}")
    assert not offenders, (
        "Trên bàn vận hành không có gì gấp tới mức cắt lời trình đọc màn hình "
        "(aria-live=assertive):\n" + "\n".join(offenders)
    )

    clock = code(BLOCK_CLOCK.read_text(encoding="utf-8"))
    # Vùng polite của đồng hồ khối chỉ được đổi khi CHUYỂN khối, nên câu thông
    # báo không được chứa đồng hồ đếm ngược (đổi mỗi giây).
    assert "useAnnounceOnChange" in clock, (
        "thông báo chuyển khối phải đi qua hook chỉ phát khi trạng thái đổi"
    )
    ann = re.search(r"const announcement = useAnnounceOnChange\((.*?)\n  \);", clock, re.S)
    assert ann, "không đọc được câu thông báo chuyển khối"
    chatter = "câu thông báo chứa đồng hồ đếm ngược sẽ khiến vùng aria-live đọc lại "
    chatter += "mỗi giây — người dùng sẽ tắt nó và mất luôn thông báo chuyển khối"
    for token in ("fmtMinSec", "remainingS"):
        assert token not in ann.group(1), f"{chatter} (thấy {token})"
    # Feed bình luận là vùng nói NHIỀU nhất: phải tắt hẳn, và tắt có chủ ý.
    feed = code(COMMENT_FEED.read_text(encoding="utf-8"))
    assert 'aria-live="off"' in feed, (
        "feed trực tiếp đọc lên liên tục sẽ che mất mọi thông báo khác của bàn"
    )


def test_every_focusable_element_on_the_desk_keeps_a_visible_focus_ring():
    """Term từng có tabIndex + outline-none: một điểm dừng focus không ai thấy."""
    shared = ("focus-ring", "fieldCls", "buttonCls")
    offenders: list[str] = []
    for rel, raw in desk_render_path().items():
        src = code(raw)
        for m in re.finditer(r"<(button|select|input|summary|textarea|Link)[\s\n]", src):
            tag = _opening_tag(src, m.start())
            if not any(token in tag for token in shared):
                offenders.append(f"{rel}:{src[: m.start()].count(chr(10)) + 1} <{m.group(1)}>")
        for m in re.finditer(r"tabIndex=\{0\}", src):
            tag = _opening_tag(src, src.rfind("<", 0, m.start()))
            if "focus-ring" not in tag:
                offenders.append(f"{rel}:{src[: m.start()].count(chr(10)) + 1} tabIndex")
    assert not offenders, "Phần tử nhận focus mà không thấy vòng focus (WCAG 2.4.7):\n" + "\n".join(
        offenders
    )
    term = (SRC / "components" / "Term.tsx").read_text(encoding="utf-8")
    term_rule = "Term nhận focus bằng tabIndex nên phải mang vòng focus dùng chung"
    assert "focus-ring" in term, term_rule
    assert "outline-none" not in code(term), term_rule


# --------------------------------------------------------------------------
# 10. trạng thái RỖNG và ĐANG TẢI — nói rõ người dùng nên làm gì
# --------------------------------------------------------------------------
def test_the_loading_state_says_what_is_happening():
    src = code(DESK_PAGE.read_text(encoding="utf-8"))
    i = src.index("function DeskSkeleton")
    # Chuỗi JSX bị prettier ngắt dòng giữa câu, nên gom khoảng trắng trước khi tìm.
    skeleton = re.sub(r"\s+", " ", src[i : i + 1200])
    assert 'role="status"' in skeleton, (
        "khung xám không nói được là đang TẢI hay đã HỎNG — cần một dòng "
        "role=status cho cả mắt lẫn trình đọc màn hình"
    )
    assert "Đang kết nối" in skeleton, "thiếu câu tiếng Việt mô tả việc đang diễn ra"
    assert "không cần tải lại trang" in skeleton, "trạng thái tải phải nói rõ đừng làm gì"


def test_every_empty_panel_tells_the_operator_what_to_do():
    checks = {
        "desk/page.tsx (thẻ hành động)": (DESK_PAGE, "Chưa có gợi ý cho thời điểm này"),
        "RhythmChart.tsx": (RHYTHM_CHART, "Chưa có phút số liệu nào"),
        "CommentRadar.tsx": (COMMENT_RADAR, "Chưa có bình luận nào trong 5 phút gần nhất"),
        "CommentFeed.tsx": (COMMENT_FEED, "Chưa có bình luận nào"),
        "BlockStrip.tsx": (BLOCK_STRIP, "Chưa nhận được lịch khối"),
    }
    for label, (path, phrase) in checks.items():
        src = path.read_text(encoding="utf-8")
        assert phrase in src, f"{label}: thiếu trạng thái rỗng tiếng Việt {phrase!r}"

    # …và trạng thái rỗng phải nói bước tiếp theo, không chỉ báo "trống".
    for path in (RHYTHM_CHART, COMMENT_RADAR):
        src = path.read_text(encoding="utf-8")
        assert "sẽ tự" in src or "tự vẽ" in src, (
            f"{path.name}: trạng thái rỗng phải nói khi nào dữ liệu sẽ tới"
        )

    # Thang chữ: trạng thái rỗng là chỗ người mới đọc đầu tiên, không dùng cỡ
    # metadata cho câu chính.
    for path in (RHYTHM_CHART, COMMENT_RADAR, COMMENT_FEED):
        src = code(path.read_text(encoding="utf-8"))
        assert "text-body" in src, f"{path.name}: câu chính của trạng thái rỗng phải ở bậc body"


def test_the_executed_card_confirms_the_command_reached_the_server():
    src = code(ACTION_CARD.read_text(encoding="utf-8"))
    confirm = "bấm Thực hiện là gửi một lệnh đi máy chủ — thẻ phải xác nhận cú bấm đã "
    confirm += "tới, trước cả khi thấy sản phẩm được ghim trên luồng phát"
    assert "<Flash" in src, confirm
    assert "executed" in src, confirm
    assert "motion-enter" in src, "thẻ mới phải vào bằng hiệu ứng, không nhảy phịch ra"
    assert "Đã thực hiện" in src
