"""Design-system gate for the web client (gói UI-1).

An audit of the running code found the desk typeset at 11 px in 20 places and
10 px in 7 more. Per ISO 9241-303 a cap height should subtend 16–22 arcmin at
the design viewing distance; at 70 cm and 96 dpi one CSS pixel is ≈ 0.975
arcmin, so 11 px ≈ 10.7 arcmin — about a third BELOW the minimum. Operators
said it plainly: "chữ còn quá nhỏ".

Nothing in the suite could see that: the backend tests test the backend and
`tsc --noEmit` type-checks types, not sizes. These tests read the design
tokens and the components straight off disk and assert the four rules that
package UI-1 exists to hold:

1. the named type scale is declared, and nothing renders below its 13 px floor;
2. status is never colour-alone — every state also carries a SHAPE, and every
   status ink clears WCAG 1.4.3 AA (4.5:1) on every plane the desk paints
   (the ratios are recomputed here, not read from a comment);
3. motion runs on the Material 3 duration tokens and collapses completely
   under `prefers-reduced-motion: reduce`;
4. every focusable element shows a focus ring, and controls meet the WCAG 2.2
   SC 2.5.8 24x24 px target-size floor.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
TAILWIND = WEB / "tailwind.config.ts"
GLOBALS = WEB / "src" / "app" / "globals.css"
SRC = WEB / "src"

TSX = sorted(SRC.rglob("*.tsx"))

# Planes the dark desk paints, from tailwind.config.ts.
DARK_PLANES = {
    "page": "#0d0d0d",
    "surface": "#1a1a19",
    "raised": "#232322",
    "axis": "#383835",
}
LIGHT_PLANES = {"white": "#ffffff", "surface": "#f5f5f4"}

# Every status that carries text needs an ink on both planes.
STATUS_INKS = {"on", "off", "drift", "good", "warn", "crit", "info"}

# The scale handed down in the ISO 9241-303 derivation: name -> (px, line, weight).
TYPE_SCALE = {
    "meta": (13, 18, 400),
    "label": (15, 20, 600),
    "body": (16, 22, 400),
    "strong": (18, 24, 600),
    "title": (20, 26, 600),
    "num-s": (28, 30, 650),
    "num-m": (40, 42, 650),
    "num-l": (56, 54, 700),
    "num-xl": (72, 68, 700),
}
NUM_STEPS = [name for name in TYPE_SCALE if name.startswith("num-")]

# Material 3 duration tokens (ms).
M3_DURATIONS = {
    "short2": 100,
    "short4": 200,
    "medium1": 250,
    "medium2": 300,
    "medium3": 350,
}
M3_EMPHASIZED = "cubic-bezier(0.2, 0, 0, 1)"

# Smallest step of the scale — nothing may render below it.
FLOOR_PX = 13


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _rel_luminance(hex_color: str) -> float:
    """WCAG 2.x relative luminance of an #rrggbb colour."""
    h = hex_color.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two #rrggbb colours."""
    la, lb = _rel_luminance(a), _rel_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _css() -> str:
    return GLOBALS.read_text(encoding="utf-8")


def _block(css: str, header: str) -> str:
    """The text of an at-rule block that ends with a `}` on its own line."""
    m = re.search(re.escape(header) + r".*?\n\}\n", css, re.S)
    assert m, f"không tìm thấy khối {header!r} trong globals.css"
    return m.group(0)


def _tokens(css_part: str, suffix: str = "-ink") -> dict[str, str]:
    """`--st-<name><suffix>: #rrggbb;` declarations inside a chunk of CSS."""
    pat = re.compile(r"--st-([a-z0-9-]+?)" + re.escape(suffix) + r":\s*(#[0-9a-fA-F]{6})\s*;")
    return {m.group(1): m.group(2).lower() for m in pat.finditer(css_part)}


def _font_size_block() -> str:
    src = TAILWIND.read_text(encoding="utf-8")
    m = re.search(r"fontSize:\s*\{(.*?)\n      \},", src, re.S)
    assert m, "không tìm thấy theme.extend.fontSize trong tailwind.config.ts"
    return m.group(1)


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


def test_web_sources_are_readable():
    assert TAILWIND.exists(), f"không tìm thấy {TAILWIND}"
    assert GLOBALS.exists(), f"không tìm thấy {GLOBALS}"
    assert TSX, "không đọc được file .tsx nào — cấu trúc web/src đã đổi?"


# --------------------------------------------------------------------------
# 1. type scale
# --------------------------------------------------------------------------
def test_type_scale_is_declared_with_size_line_height_and_weight():
    block = _font_size_block()
    pat = re.compile(r'\n\s*"?([a-z0-9-]+)"?:\s*\["(\d+)px",\s*\{([^}]*)\}\]')
    entries = {m.group(1): (m.group(2), m.group(3)) for m in pat.finditer(block)}
    missing = sorted(set(TYPE_SCALE) - set(entries))
    assert not missing, f"thang chữ thiếu bậc: {missing}"

    for name, (px, line, weight) in TYPE_SCALE.items():
        got_px, opts = entries[name]
        assert int(got_px) == px, f"bậc {name}: cỡ {got_px}px, cần {px}px"
        assert f'lineHeight: "{line}px"' in opts, f"bậc {name} thiếu lineHeight {line}px"
        assert f'fontWeight: "{weight}"' in opts, f"bậc {name} thiếu fontWeight {weight}"

    # The display figures must line up in a column.
    css = _css()
    for name in NUM_STEPS:
        assert f".text-{name}" in css, f"bậc {name} chưa được gắn tabular-nums trong globals.css"
    assert "font-variant-numeric: tabular-nums" in css


def test_display_steps_exist_for_headline_figures():
    """The audit found no display size anywhere; num-* now covers 28-72px."""
    sizes = {TYPE_SCALE[n][0] for n in NUM_STEPS}
    assert max(sizes) >= 56, "chưa có cỡ chữ hiển thị (display) cho con số tiêu điểm"


def test_nothing_renders_below_the_iso_floor():
    """No type under 13px anywhere in the client — the reason UI-1 exists."""
    offenders: list[str] = []
    for path in TSX:
        src = path.read_text(encoding="utf-8")
        rel = path.relative_to(WEB).as_posix()
        for m in re.finditer(r"text-\[(\d+)px\]", src):
            if int(m.group(1)) < FLOOR_PX:
                line = src[: m.start()].count("\n") + 1
                offenders.append(f"{rel}:{line} {m.group(0)}")
        # Tailwind's text-xs is 12px — below the floor by name rather than value.
        for m in re.finditer(r"\btext-xs\b", src):
            line = src[: m.start()].count("\n") + 1
            offenders.append(f"{rel}:{line} text-xs (12px)")
        # Recharts tick labels are typeset in JS, not CSS.
        for m in re.finditer(r"fontSize:\s*(\d+)", src):
            if int(m.group(1)) < FLOOR_PX:
                line = src[: m.start()].count("\n") + 1
                offenders.append(f"{rel}:{line} {m.group(0)}")
    assert not offenders, (
        "Chữ nhỏ hơn bậc meta (13px) — dưới ngưỡng ISO 9241-303 ở 70cm:\n" + "\n".join(offenders)
    )


# --------------------------------------------------------------------------
# 2. status: shape + colour, and colour that actually passes AA
# --------------------------------------------------------------------------
def test_status_is_encoded_by_shape_not_colour_alone():
    css = _css()
    shapes = {"on": None, "off": None, "drift": None}
    for name in shapes:
        m = re.search(r"\.status-mark--" + name + r"\s*\{([^}]*)\}", css)
        assert m, f"thiếu ký hiệu hình dạng cho trạng thái {name!r}"
        shapes[name] = " ".join(m.group(1).split())
    assert len(set(shapes.values())) == 3, (
        "ba trạng thái BẬT/TẮT/trôi phải có ba hình khác nhau (chấm đặc, "
        f"vòng rỗng, nửa đặc) — hiện có: {shapes}"
    )
    assert ".status-mark {" in css, "thiếu hình cơ sở .status-mark"


def test_every_status_ink_clears_aa_on_every_dark_plane():
    inks = _tokens(_css())
    assert set(inks) == STATUS_INKS, f"thiếu/thừa mực trạng thái: {sorted(inks)}"
    failures = [
        f"--st-{name}-ink {hexv} trên {plane} = {contrast(hexv, bg):.2f}:1"
        for name, hexv in inks.items()
        for plane, bg in DARK_PLANES.items()
        if contrast(hexv, bg) < 4.5
    ]
    assert not failures, "Mực trạng thái dưới 4.5:1 (WCAG 1.4.3 AA):\n" + "\n".join(failures)


def test_every_status_ink_has_a_light_plane_twin_that_also_clears_aa():
    """A printed /ket-qua lands on white paper — the pair needs both halves."""
    css = _css()
    inks = _tokens(css, "-ink-light")
    assert set(inks) == STATUS_INKS, f"thiếu mực trạng thái cho nền sáng: {sorted(inks)}"
    failures = [
        f"--st-{name}-ink-light {hexv} trên {plane} = {contrast(hexv, bg):.2f}:1"
        for name, hexv in inks.items()
        for plane, bg in LIGHT_PLANES.items()
        if contrast(hexv, bg) < 4.5
    ]
    assert not failures, "Mực trạng thái nền sáng dưới 4.5:1:\n" + "\n".join(failures)

    # ... and the light half has to actually be reachable.
    printed = _block(css, "@media print {")
    for name in STATUS_INKS:
        assert f"--st-{name}-ink: var(--st-{name}-ink-light)" in printed, (
            f"bản in chưa đổi sang mực nền sáng cho trạng thái {name!r}"
        )
    assert "background: #ffffff" in printed, "bản in phải vẽ lại nền sáng trước khi đổi mực"


def test_light_inks_are_not_wired_to_the_os_colour_preference():
    """The desk paints dark unconditionally: dark ink on a dark plane would
    be the exact bug this token pair exists to prevent."""
    assert "@media (prefers-color-scheme: light)" not in _css()


def test_the_fill_tones_are_never_used_as_status_text():
    """#d03b3b reaches 4.05:1 on the page plane; it may fill, never letter."""
    assert contrast("#d03b3b", DARK_PLANES["page"]) < 4.5  # the reason -crit-ink exists
    offenders: list[str] = []
    for path in TSX:
        src = path.read_text(encoding="utf-8")
        rel = path.relative_to(WEB).as_posix()
        for m in re.finditer(r"text-critical\b(?!-)", src):
            line = src[: m.start()].count("\n") + 1
            offenders.append(f"{rel}:{line} text-critical")
    assert not offenders, (
        "text-critical (#d03b3b) chỉ đạt 4.05:1 trên nền trang — dùng "
        "text-crit-ink cho chữ:\n" + "\n".join(offenders)
    )


# --------------------------------------------------------------------------
# 3. motion
# --------------------------------------------------------------------------
def test_motion_uses_the_material3_duration_tokens():
    css = _css()
    for name, ms in M3_DURATIONS.items():
        assert re.search(rf"--dur-{name}:\s*{ms}ms\s*;", css), (
            f"thiếu token thời lượng M3 --dur-{name}: {ms}ms"
        )
    assert f"--ease-emphasized: {M3_EMPHASIZED}" in css, "thiếu easing emphasized của M3"

    config = TAILWIND.read_text(encoding="utf-8")
    for name in M3_DURATIONS:
        assert f'{name}: "var(--dur-{name})"' in config, (
            f"tiện ích Tailwind duration-{name} chưa nối vào biến CSS"
        )
    assert 'emphasized: "var(--ease-emphasized)"' in config


def test_reduced_motion_collapses_every_duration_token():
    block = _block(_css(), "@media (prefers-reduced-motion: reduce)")
    for name in M3_DURATIONS:
        assert re.search(rf"--dur-{name}:\s*(0|1)m?s\s*;", block), (
            f"--dur-{name} không được rút gọn khi người dùng chọn giảm chuyển động"
        )
    assert "animation-duration: 0.01ms !important" in block
    assert "transition-duration: 0.01ms !important" in block


def test_components_do_not_hardcode_transition_durations():
    offenders: list[str] = []
    for path in TSX:
        src = path.read_text(encoding="utf-8")
        rel = path.relative_to(WEB).as_posix()
        for m in re.finditer(r"duration-(\d+|\[[^\]]+\])", src):
            line = src[: m.start()].count("\n") + 1
            offenders.append(f"{rel}:{line} {m.group(0)}")
    assert not offenders, (
        "Thời lượng chuyển động phải dùng token M3 (duration-short2 …):\n" + "\n".join(offenders)
    )


# --------------------------------------------------------------------------
# 4. focus + target size
# --------------------------------------------------------------------------
def test_focus_ring_is_defined_for_keyboard_only():
    css = _css()
    assert ".focus-ring:focus-visible" in css
    m = re.search(r"\.focus-ring:focus-visible\s*\{([^}]*)\}", css)
    assert m, "không đọc được luật .focus-ring:focus-visible"
    assert "outline:" in m.group(1), "vòng focus phải vẽ outline thật"
    assert ".focus-ring-inset:focus-visible" in css, (
        "thiếu biến thể inset cho control nằm trong nhóm overflow-hidden"
    )
    ring = re.search(r"--focus-ring:\s*(#[0-9a-fA-F]{6})", css)
    assert ring, "thiếu token màu --focus-ring"
    # SC 1.4.11: a non-text indicator needs 3:1 against what surrounds it.
    assert contrast(ring.group(1), DARK_PLANES["page"]) >= 3.0


def test_every_focusable_element_shows_a_focus_ring():
    """Term had tabIndex + outline-none: a focus stop nobody could see."""
    shared = ("focus-ring", "fieldCls", "inputCls", "buttonCls")
    offenders: list[str] = []
    for path in TSX:
        src = path.read_text(encoding="utf-8")
        rel = path.relative_to(WEB).as_posix()
        for m in re.finditer(r"<(button|select|input|summary|textarea|Link)[\s\n]", src):
            tag = _opening_tag(src, m.start())
            if not any(token in tag for token in shared):
                line = src[: m.start()].count("\n") + 1
                offenders.append(f"{rel}:{line} <{m.group(1)}>")
        for m in re.finditer(r"tabIndex=\{0\}", src):
            start = src.rfind("<", 0, m.start())
            tag = _opening_tag(src, start)
            if "focus-ring" not in tag:
                line = src[: m.start()].count("\n") + 1
                offenders.append(f"{rel}:{line} tabIndex={{0}}")
    assert not offenders, (
        "Phần tử nhận được focus nhưng không có vòng focus (WCAG 2.4.7):\n" + "\n".join(offenders)
    )


def test_buttons_meet_the_wcag_target_size_minimum():
    """SC 2.5.8: 24x24 CSS px. `sm` used to render ~22.6px tall."""
    config = TAILWIND.read_text(encoding="utf-8")
    tap = re.search(r'tap:\s*"(\d+)px"', config)
    ctl = re.search(r'ctl:\s*"(\d+)px"', config)
    assert tap, "thiếu token mật độ `tap`"
    assert ctl, "thiếu token mật độ `ctl`"
    assert int(tap.group(1)) >= 24, "token `tap` phải ≥ 24px (WCAG 2.2 SC 2.5.8)"
    assert int(ctl.group(1)) >= 36, "token `ctl` (control chính trên desk) phải ≥ 36px"

    button = (SRC / "components" / "ui" / "Button.tsx").read_text(encoding="utf-8")
    size = re.search(r"const SIZE[^{]*\{(.*?)\n\};", button, re.S)
    assert size, "không đọc được bảng cỡ của Button"
    sm = re.search(r"sm:\s*\"([^\"]*)\"", size.group(1))
    md = re.search(r"md:\s*\"([^\"]*)\"", size.group(1))
    assert sm, "không đọc được cỡ sm"
    assert md, "không đọc được cỡ md"
    assert "min-h-tap" in sm.group(1), "cỡ sm chưa ghim sàn 24px"
    assert "min-h-ctl" in md.group(1), "cỡ md chưa ghim chiều cao 36px"
    assert 'size = "md"' in button, "cỡ md phải là mặc định cho hành động chính"


def test_segmented_controls_are_big_enough_to_hit():
    for name in ("StatusBar.tsx", "ReplayControls.tsx"):
        src = (SRC / "components" / name).read_text(encoding="utf-8")
        assert "min-h-tap" in src, f"{name}: nút trong nhóm phân đoạn chưa đạt sàn 24px"
        assert "focus-ring-inset" in src, (
            f"{name}: nhóm overflow-hidden cần vòng focus inset, nếu không sẽ bị cắt mất"
        )
