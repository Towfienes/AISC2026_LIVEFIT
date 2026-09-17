"""Bàn trợ live chạy THẬT trong trình duyệt — hai lỗi kiểm toán 17/09 mà đọc mã
nguồn không bắt được.

1. **P1 — bấm đúp vượt qua xác nhận "Kết thúc phiên".** Cú bấm đầu mở bước xác
   nhận, React vẽ lại ngay trong sự kiện; cú thứ hai rơi đúng vào "Kết thúc
   ngay" (ở 1920px nút này nằm dưới nửa trái của nút cũ) và buổi live kết thúc
   không thể hoàn tác. Đo được bằng Chrome headless: nhấp đúp ở 10–45% bề ngang
   nút ⇒ 36/36 lần phiên bị kết thúc.
2. **P2 — đổi phiên lúc lệnh Thực hiện đang chờ.** Phản hồi của phiên A về sau
   khi đã chuyển sang phiên B từng ghi sản phẩm A vừa ghim lên hero phiên B.

Cách dựng: KHÔNG chép lại component. Mã nguồn THẬT (`StatusBar.tsx`,
`ui/Button.tsx`, `useDesk.ts`…) được TypeScript của dự án dịch sang JS, gói bằng
một bộ nạp module tí hon, chạy trên React 18 UMD của `web/node_modules`, với
CSS Tailwind biên dịch từ đúng `tailwind.config.ts` + `globals.css`. Chỉ tầng
mạng (`lib/api.ts`, `lib/useLiveSocket.ts`) được thay bằng bản giả để test tự
điều khiển thời điểm máy chủ trả lời. Chuột là chuột thật của Playwright
(mousedown/mouseup, click_count=2).

Bỏ qua (không giả vờ xanh) khi máy thiếu node, `npm install` hoặc Playwright.

CHẠY RIÊNG, CÓ HẠN GIỜ. Cả tệp mang dấu ``slow`` (bộ nhanh ``-m "not slow"``
không gọi tới trình duyệt). Từng thao tác Playwright có hạn giờ cứng
(``PW_TIMEOUT_MS``), từng tiến trình con có ``timeout=``, trang và trình duyệt
luôn được đóng trong ``finally``. Bản đầu của tệp từng TREO bộ test hơn 10 phút:
``page.evaluate("window.pending = window.desk.execute(...)")`` trả về chính
promise đang chờ máy chủ giả, mà ``evaluate`` thì CHỜ promise trả về — không có
hạn giờ nào cắt được. Mọi lệnh ``evaluate`` giờ trả ``undefined`` hoặc tự đua
với một hẹn giờ phía trình duyệt.

    timeout 900 .venv/Scripts/python -m pytest tests/test_web_desk_trinh_duyet.py -m slow
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

# `browser` tách test trình duyệt khỏi con số "cổng Monte-Carlo" mà README công bố
# (scripts/dong_bo_so_test.py đếm `slow and not browser`).
pytestmark = [pytest.mark.slow, pytest.mark.browser]

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SRC = WEB / "src"
NODE_MODULES = WEB / "node_modules"

#: Hạn giờ cứng cho MỌI thao tác Playwright (chờ phần tử, bấm, điều hướng). Đủ
#: rộng cho máy đang bận (17/09: với hạn 10 giây, test bấm đúp từng dính
#: TimeoutError khi nhiều bộ test chạy song song) mà vẫn cắt được thao tác treo.
PW_TIMEOUT_MS = 30_000
#: Hạn giờ cho một lần dịch TypeScript / biên dịch Tailwind.
BUNDLE_TIMEOUT_S = 120
TAILWIND_TIMEOUT_S = 180

BUNDLER = r"""
const path = require("path");
const fs = require("fs");
const [WEB, OUT, ENTRY, OVERRIDES] = process.argv.slice(2);
const ts = require(path.join(WEB, "node_modules", "typescript"));
const SRC = path.join(WEB, "src");
const overrides = JSON.parse(OVERRIDES);
const norm = (p) => path.resolve(p).toLowerCase();
const mods = new Map();

function resolve(from, spec) {
  let base;
  if (spec.startsWith("@/")) base = path.join(SRC, spec.slice(2));
  else if (spec.startsWith(".")) base = path.resolve(path.dirname(from), spec);
  else return null;
  for (const ext of ["", ".ts", ".tsx"]) {
    const p = base + ext;
    if (fs.existsSync(p) && fs.statSync(p).isFile()) {
      return overrides[norm(p)] ? path.resolve(overrides[norm(p)]) : path.resolve(p);
    }
  }
  throw new Error("không phân giải được " + spec + " từ " + from);
}

function add(file) {
  if (mods.has(file)) return;
  const src = fs.readFileSync(file, "utf8");
  const out = ts.transpileModule(src, {
    fileName: file,
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      jsx: ts.JsxEmit.React,
      esModuleInterop: true,
    },
  }).outputText;
  const deps = {};
  mods.set(file, { out, deps });
  for (const m of out.matchAll(/require\("([^"]+)"\)/g)) {
    const r = resolve(file, m[1]);
    if (r) {
      deps[m[1]] = r;
      add(r);
    } else if (m[1] !== "react") {
      throw new Error("module ngoài không có trong trình duyệt: " + m[1]);
    }
  }
}

const entry = path.resolve(ENTRY);
add(entry);
let js = "(function(){\nconst defs = {};\n";
for (const [file, { out, deps }] of mods) {
  js += "defs[" + JSON.stringify(file) + "] = { deps: " + JSON.stringify(deps) +
    ", fn: function(require, module, exports, React){\n" + out + "\n} };\n";
}
js += "const cache = {};\n" +
  "function load(file){ if (cache[file]) return cache[file].exports;" +
  " const d = defs[file]; const module = { exports: {} }; cache[file] = module;" +
  " d.fn(function(spec){ return spec === 'react' ? window.React : load(d.deps[spec]); }," +
  " module, module.exports, window.React); return module.exports; }\n" +
  "window.__entry = load(" + JSON.stringify(entry) + ");\n})();\n";
fs.writeFileSync(OUT, js);
"""

SESSIONS = [
    {
        "session_id": "A",
        "platform": "youtube",
        "title": "Live tối 17/09 — Son kem",
        "mode": "suggest",
        "status": "live",
        "planned_duration_min": 90,
        "start_ts": "2026-09-17T12:00:00Z",
        "end_ts": None,
        "is_demo": False,
    },
    {
        "session_id": "B",
        "platform": "shopee",
        "title": "Live trưa Shopee",
        "mode": "suggest",
        "status": "live",
        "planned_duration_min": 60,
        "start_ts": "2026-09-17T05:00:00Z",
        "end_ts": None,
        "is_demo": False,
    },
]

PRODUCTS = [
    {"product_id": pid, "name": name, "category": "my-pham", "price": 99000, "stock": 50}
    for pid, name in (("P1", "Son kem lì"), ("P2", "Kem chống nắng"), ("P3", "Phấn phủ"))
]

STATUS_BAR_HARNESS = """<!doctype html>
<html><head><meta charset="utf-8"><link rel="stylesheet" href="app.css"></head>
<body class="bg-page"><div id="root"></div>
<script>window.process = { env: {} };</script>
<script src="react.production.min.js"></script>
<script src="react-dom.production.min.js"></script>
<script src="statusbar.bundle.js"></script>
<script>
const h = React.createElement;
const StatusBar = window.__entry.default;
const SESSIONS = __SESSIONS__;
window.ended = [];
function App() {
  const [sid, setSid] = React.useState("A");
  return h("main", { className: "flex min-h-screen flex-col bg-page p-3" },
    h("div", {
      className: "sticky top-0 z-20 -mx-3 -mt-3 mb-3 flex flex-col gap-3 bg-page px-3 pb-3 pt-3",
    },
      h(StatusBar, {
        connection: "live", wsStatus: "open", sessions: SESSIONS, sessionId: sid,
        onSelectSession: setSid, elapsedS: 754, durationS: 5400, mode: "suggest",
        onSetMode: () => {}, canToggleMode: false,
        onEndSession: () => window.ended.push(sid), canEndSession: true, endBusy: false,
        alert: null,
      })));
}
ReactDOM.createRoot(document.getElementById("root")).render(h(App));
</script></body></html>
"""

FAKE_API = """
const SESSIONS = __SESSIONS__;
const PRODUCTS = __PRODUCTS__;
const PINNED: Record<string, string> = { A: "P1", B: "P2" };
const w = window as any;
w.executeCalls = [];
export const wsUrl = (sid: string) => "ws://invalid/" + sid;
export const sanitizeCards = (cards: any[]) => cards;
export const listSessions = (_t?: number) => Promise.resolve(SESSIONS);
export const listProducts = () => Promise.resolve(PRODUCTS);
export const getState = (sid: string) =>
  Promise.resolve({
    session_id: sid, elapsed_s: 120, mode: "suggest", status: "live",
    pinned_product: PRODUCTS.find((p: any) => p.product_id === PINNED[sid]) ?? null,
    current_block: null, design_hash: null, autopilot: null, cards_note: null, cards: [],
  });
export const getTicks = () => Promise.resolve([]);
export const getCards = () => Promise.resolve([]);
export const getComments = () => Promise.resolve([]);
export const getSchedule = () => Promise.resolve([]);
export const postOverride = () => Promise.resolve({});
export const endSession = (sid: string) =>
  Promise.resolve(SESSIONS.find((s: any) => s.session_id === sid));
export function executeCard(sid: string, cardId: string, productId: string) {
  return new Promise((resolve, reject) => {
    w.executeCalls.push({ sid, cardId, productId, resolve, reject });
  });
}
"""

FAKE_SOCKET = """
export type SocketStatus = "idle" | "connecting" | "open" | "closed";
export function useLiveSocket(_sid: string | null, _on: unknown, _enabled = true): SocketStatus {
  return "closed";
}
"""

USE_DESK_ENTRY = """
import { createElement } from "react";
import { useDesk } from "@/lib/useDesk";

export default function Probe() {
  const desk = useDesk({ preferredSessionId: "A" });
  (window as any).desk = desk;
  return createElement(
    "pre",
    { id: "probe" },
    JSON.stringify({
      connection: desk.connection,
      sessionId: desk.sessionId,
      pinned: desk.pinned ? desk.pinned.product_id : null,
    }),
  );
}
"""

USE_DESK_HARNESS = """<!doctype html>
<html><head><meta charset="utf-8"></head><body><div id="root"></div>
<script>window.process = { env: {} };</script>
<script src="react.production.min.js"></script>
<script src="react-dom.production.min.js"></script>
<script src="usedesk.bundle.js"></script>
<script>
ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(window.__entry.default));
</script></body></html>
"""


def _need(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"thiếu {path.relative_to(ROOT)} — chạy 'npm install' trong web/")


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("không có node")
    for rel in (
        "typescript/package.json",
        "tailwindcss/lib/cli.js",
        "react/umd/react.production.min.js",
        "react-dom/umd/react-dom.production.min.js",
    ):
        _need(NODE_MODULES / rel)
    pytest.importorskip("playwright.sync_api")

    out = tmp_path_factory.mktemp("desk_browser")
    for name in ("react/umd/react.production.min.js", "react-dom/umd/react-dom.production.min.js"):
        shutil.copy(NODE_MODULES / name, out / Path(name).name)

    sessions = json.dumps(SESSIONS, ensure_ascii=False)
    (out / "statusbar.html").write_text(
        STATUS_BAR_HARNESS.replace("__SESSIONS__", sessions), encoding="utf-8"
    )
    (out / "usedesk.html").write_text(USE_DESK_HARNESS, encoding="utf-8")
    fake_api = out / "fake_api.ts"
    fake_api.write_text(
        FAKE_API.replace("__SESSIONS__", sessions).replace(
            "__PRODUCTS__", json.dumps(PRODUCTS, ensure_ascii=False)
        ),
        encoding="utf-8",
    )
    fake_socket = out / "fake_socket.ts"
    fake_socket.write_text(FAKE_SOCKET, encoding="utf-8")
    # Điểm vào nằm NGOÀI web/src (không để lại tệp lạ trong mã nguồn khi
    # tsc/next của người khác đang chạy): nó chỉ import "@/lib/useDesk", mà
    # bộ nạp phân giải "@/" về web/src giống hệt app.
    entry = out / "probe.tsx"
    bundler = out / "bundle.cjs"
    bundler.write_text(BUNDLER, encoding="utf-8")

    def bundle(entry_file: Path, target: Path, overrides: dict[str, str]) -> None:
        norm = {str(Path(k).resolve()).lower(): str(v) for k, v in overrides.items()}
        r = subprocess.run(
            [node, str(bundler), str(WEB), str(target), str(entry_file), json.dumps(norm)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=BUNDLE_TIMEOUT_S,
        )
        assert r.returncode == 0, r.stderr

    bundle(SRC / "components" / "StatusBar.tsx", out / "statusbar.bundle.js", {})
    entry.write_text(USE_DESK_ENTRY, encoding="utf-8")
    bundle(
        entry,
        out / "usedesk.bundle.js",
        {
            str(SRC / "lib" / "api.ts"): str(fake_api),
            str(SRC / "lib" / "useLiveSocket.ts"): str(fake_socket),
        },
    )

    content = ",".join(
        p.as_posix()
        for p in (
            SRC / "components" / "StatusBar.tsx",
            SRC / "components" / "ui" / "Button.tsx",
            SRC / "components" / "ui" / "Badge.tsx",
            SRC / "components" / "ui" / "Callout.tsx",
            SRC / "components" / "ui" / "StatusMark.tsx",
            SRC / "components" / "ui" / "field.ts",
            out / "statusbar.html",
        )
    )
    r = subprocess.run(
        [
            node,
            str(NODE_MODULES / "tailwindcss" / "lib" / "cli.js"),
            "-c",
            "tailwind.config.ts",
            "-i",
            "src/app/globals.css",
            "-o",
            str(out / "app.css"),
            "--content",
            content,
        ],
        cwd=WEB,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=TAILWIND_TIMEOUT_S,
    )
    assert r.returncode == 0, r.stderr
    css = (out / "app.css").read_text(encoding="utf-8")
    for cls in (".ml-auto", ".min-h-ctl", ".invisible", ".col-start-1"):
        assert cls in css, f"CSS biên dịch thiếu {cls}"
    return out


@pytest.fixture(scope="module")
def browser() -> Iterator:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = None
        try:
            try:
                b = p.chromium.launch(headless=True, timeout=60_000)
            except Exception:  # chưa tải trình duyệt riêng của Playwright
                try:
                    b = p.chromium.launch(channel="chrome", headless=True, timeout=60_000)
                except Exception as e:
                    pytest.skip(f"không mở được Chromium headless: {e}")
            yield b
        finally:
            # Luôn đóng — kể cả khi một test ở giữa ném lỗi: không để lại
            # chrome.exe mồ côi giữ bộ test treo.
            if b is not None:
                b.close()


@contextmanager
def _page(browser, harness: Path, page_name: str, width: int, height: int = 1080) -> Iterator:
    """Một trang trong ngữ cảnh riêng, có hạn giờ cứng, LUÔN đóng khi xong."""
    context = browser.new_context(viewport={"width": width, "height": height})
    try:
        context.set_default_timeout(PW_TIMEOUT_MS)
        context.set_default_navigation_timeout(PW_TIMEOUT_MS)
        page = context.new_page()
        page.set_default_timeout(PW_TIMEOUT_MS)
        page.set_default_navigation_timeout(PW_TIMEOUT_MS)
        # Chặn mọi thứ ngoài tệp cục bộ (Google Fonts trong globals.css): test
        # không được phụ thuộc mạng; phông dự phòng không đổi bất biến hình học.
        page.route(
            "**/*",
            lambda route: (
                route.continue_() if route.request.url.startswith("file:") else route.abort()
            ),
        )
        page.goto((harness / page_name).as_uri())
        yield page
    finally:
        context.close()


def _bar_ready(page) -> None:
    page.get_by_role("button", name="Kết thúc phiên").wait_for()


@contextmanager
def _bar(browser, harness: Path, width: int) -> Iterator:
    with _page(browser, harness, "statusbar.html", width) as page:
        _bar_ready(page)
        yield page


def _box(page, name: str) -> dict:
    box = page.get_by_role("button", name=name, exact=True).bounding_box()
    assert box, f"không thấy nút {name}"
    return box


# ===========================================================================
# P1 — bấm đúp không bao giờ kết thúc phiên
# ===========================================================================
#: Chỗ bấm trên nút cũ: 10% và 30% nằm trong dải từng đo được là "phiên bị kết
#: thúc 36/36 lần" (10–45% bề ngang ở 1920px); 85% rơi vào chỗ nút "Huỷ" mới.
DOUBLE_CLICK_SPOTS = (0.1, 0.3, 0.85)
#: 0ms = nhấp đúp thật; 400ms = nhấp đúp chậm, dưới ngưỡng 500ms mặc định của Windows.
DOUBLE_CLICK_GAPS_MS = (0, 400)


# Bề ngang: 1920 và 1600 là hai bề ngang mà bản CHƯA SỬA (bỏ khoá thời gian +
# bỏ bề ngang của "Huỷ") thật sự bị kết thúc phiên — đã thử đột biến 17/09. Ở
# 1366 bản đột biến đó KHÔNG làm test này đỏ (không chứng minh được gì), nên
# bề ngang ấy được canh bằng test hình học ngay dưới (đột biến làm nó đỏ).
# 2 bề ngang × 3 chỗ × 2 nhịp = 12 lần thử (bản đầu 36 lần, mỗi lần một trang mới).
@pytest.mark.parametrize("width", [1920, 1600])
def test_bam_dup_nut_ket_thuc_phien_khong_ket_thuc_buoi_live(browser, harness, width):
    # Một trang cho mỗi bề ngang, TẢI LẠI giữa các lần thử (trạng thái React và
    # window.ended về gốc) — rẻ hơn nhiều so với mở trang mới mỗi lần.
    with _bar(browser, harness, width) as page:
        first = True
        for frac in DOUBLE_CLICK_SPOTS:
            for gap_ms in DOUBLE_CLICK_GAPS_MS:
                if not first:
                    page.reload()
                    _bar_ready(page)
                first = False
                trig = _box(page, "Kết thúc phiên")
                x = trig["x"] + trig["width"] * frac
                y = trig["y"] + trig["height"] / 2
                page.mouse.move(x, y)
                page.mouse.down(click_count=1)
                page.mouse.up(click_count=1)
                if gap_ms:
                    page.wait_for_timeout(gap_ms)
                page.mouse.down(click_count=2)
                page.mouse.up(click_count=2)
                page.wait_for_timeout(60)
                ended = page.evaluate("window.ended")
                visible = page.get_by_role(
                    "group", name="Xác nhận kết thúc Live tối 17/09 — Son kem"
                ).is_visible()
                assert ended == [], (
                    f"{width}px, bấm đúp ở {frac:.0%} bề ngang, cách {gap_ms}ms: phiên bị kết thúc"
                )
                assert visible, (
                    f"{width}px, {frac:.0%}, {gap_ms}ms: cú bấm thứ hai không được âm thầm "
                    "đóng bước xác nhận — người vận hành phải thấy câu hỏi"
                )


@pytest.mark.parametrize("width", [1920, 1366, 1024, 800])
def test_nut_ket_thuc_ngay_khong_bao_gio_nam_duoi_cho_nut_cu(browser, harness, width):
    with _bar(browser, harness, width) as page:
        trig = _box(page, "Kết thúc phiên")
        page.mouse.click(trig["x"] + trig["width"] / 2, trig["y"] + trig["height"] / 2)
        now = _box(page, "Kết thúc ngay")
        cancel = _box(page, "Huỷ")
        hits = page.evaluate(
            """(b) => {
              const out = [];
              for (let i = 0; i <= 20; i++) {
                for (const fy of [0.15, 0.5, 0.85]) {
                  const el = document.elementFromPoint(
                    b.x + (b.width * i) / 20, b.y + b.height * fy);
                  const btn = el && el.closest("button");
                  out.push(btn ? btn.textContent : null);
                }
              }
              return out;
            }""",
            trig,
        )
    assert "Kết thúc ngay" not in hits, f"{width}px: điểm trên chỗ nút cũ trúng 'Kết thúc ngay'"
    assert now["x"] + now["width"] <= trig["x"] + 0.5, (
        f"{width}px: 'Kết thúc ngay' ({now}) lấn vào dải ngang của nút cũ ({trig})"
    )
    assert abs(cancel["width"] - trig["width"]) <= 1, "'Huỷ' phải rộng đúng bằng nút cũ"
    assert abs((cancel["x"] + cancel["width"]) - (trig["x"] + trig["width"])) <= 1, (
        "'Huỷ' phải giữ mép phải — đúng chỗ nút cũ"
    )


def test_ket_thuc_ngay_bi_khoa_ngay_sau_khi_mo_roi_moi_nhan_bam(browser, harness):
    with _bar(browser, harness, 1920) as page:
        trig = _box(page, "Kết thúc phiên")
        page.mouse.click(trig["x"] + trig["width"] / 2, trig["y"] + trig["height"] / 2)
        now_btn = page.get_by_role("button", name="Kết thúc ngay", exact=True)
        now = now_btn.bounding_box()
        assert now, "không thấy nút Kết thúc ngay"
        assert now_btn.is_disabled(), "vừa mở bước xác nhận thì 'Kết thúc ngay' phải đang khoá"
        focused = page.evaluate("document.activeElement && document.activeElement.textContent")
        assert focused is not None
        assert focused.endswith("Huỷ"), "focus phải nằm ở lựa chọn AN TOÀN"
        page.mouse.click(now["x"] + now["width"] / 2, now["y"] + now["height"] / 2)
        assert page.evaluate("window.ended") == []
        page.wait_for_timeout(750)
        assert now_btn.is_enabled()
        page.mouse.click(now["x"] + now["width"] / 2, now["y"] + now["height"] / 2)
        ended = page.evaluate("window.ended")
    assert ended == ["A"], "bấm có chủ ý sau khoảng khoá phải kết thúc đúng phiên đang xem"


def test_doi_phien_xoa_buoc_xac_nhan_dang_mo(browser, harness):
    with _bar(browser, harness, 1920) as page:
        page.get_by_role("button", name="Kết thúc phiên").click()
        group = page.get_by_role("group", name="Xác nhận kết thúc Live tối 17/09 — Son kem")
        assert group.is_visible()
        assert "Live tối 17/09 — Son kem" in group.inner_text(), "câu xác nhận phải in tên phiên"
        page.get_by_role("combobox", name="Phiên đang xem").select_option("B")
        page.get_by_role("button", name="Kết thúc phiên").wait_for()
        assert page.get_by_role("button", name="Kết thúc ngay", exact=True).count() == 0, (
            "bước xác nhận của phiên A còn mở sau khi đổi sang phiên B"
        )
        page.get_by_role("button", name="Kết thúc phiên").click()
        page.wait_for_timeout(750)
        assert "Live trưa Shopee" in page.get_by_role("group").inner_text()
        page.get_by_role("button", name="Kết thúc ngay", exact=True).click()
        ended = page.evaluate("window.ended")
    assert ended == ["B"]


# ===========================================================================
# P2 — phản hồi Thực hiện về muộn không sửa state của phiên vừa chuyển sang
# ===========================================================================
def _probe(page) -> dict:
    return json.loads(page.locator("#probe").inner_text())


def _wait_probe(page, **want) -> dict:
    deadline = time.monotonic() + PW_TIMEOUT_MS / 1000
    while time.monotonic() < deadline:
        got = _probe(page)
        if all(got.get(k) == v for k, v in want.items()):
            return got
        page.wait_for_timeout(50)
    raise AssertionError(f"hook không tới trạng thái {want}: {_probe(page)}")


CARD_P3 = {
    "card_id": "card-1-P3",
    "rank": 1,
    "product_id": "P3",
    "product_name": "Phấn phủ",
    "headline": "Ghim Phấn phủ",
    "rationale": "",
    "estimate": 1.0,
    "ci_low": None,
    "ci_high": None,
    "source": "forecast",
    "auto_execute_in_s": None,
}

#: Gửi lệnh Thực hiện mà KHÔNG trả promise về Python: `evaluate` chờ mọi promise
#: nó nhận được, và promise này chỉ xong khi test tự trả lời máy chủ giả — trả
#: nó về là treo vĩnh viễn (nguyên nhân bộ test từng treo quá 10 phút).
SEND_EXECUTE = "(card) => { window.pending = window.desk.execute(card); }"

#: Máy chủ giả trả lời lệnh đầu tiên, rồi chờ `execute` xong — có hạn giờ phía
#: trình duyệt để lệnh evaluate không bao giờ treo.
ANSWER_EXECUTE = """async ([body, ms]) => {
  window.executeCalls[0].resolve(body);
  await Promise.race([
    window.pending,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("execute không xong sau " + ms + "ms")), ms)),
  ]);
}"""


def test_phan_hoi_thuc_hien_ve_muon_khong_ghim_len_phien_moi(browser, harness):
    with _page(browser, harness, "usedesk.html", 1280, 800) as page:
        _wait_probe(page, connection="live", sessionId="A", pinned="P1")

        page.evaluate(SEND_EXECUTE, CARD_P3)
        page.wait_for_function("window.executeCalls.length === 1")
        page.evaluate("() => { window.desk.setSessionId('B'); }")
        _wait_probe(page, sessionId="B", pinned="P2")

        body = {
            "action_id": "x",
            "product_id": "P3",
            "randomized": True,
            "overlap_set": ["P1", "P2", "P3"],
        }
        page.evaluate(ANSWER_EXECUTE, [body, PW_TIMEOUT_MS // 2])
        page.wait_for_timeout(150)
        after = _probe(page)
    assert after["pinned"] == "P2", (
        "sản phẩm vừa ghim ở phiên A hiện trên hero phiên B sau khi đổi phiên"
    )


def test_phan_hoi_thuc_hien_cung_phien_van_hien_ngay_san_pham_da_ghim(browser, harness):
    """Đối chứng: không đổi phiên thì bàn vẫn hiện ngay sản phẩm máy chủ ghim."""
    with _page(browser, harness, "usedesk.html", 1280, 800) as page:
        _wait_probe(page, connection="live", sessionId="A", pinned="P1")
        page.evaluate(SEND_EXECUTE, CARD_P3)
        page.wait_for_function("window.executeCalls.length === 1")
        body = {"action_id": "x", "product_id": "P3", "randomized": False}
        page.evaluate(ANSWER_EXECUTE, [body, PW_TIMEOUT_MS // 2])
        got = _wait_probe(page, pinned="P3")
    assert got["sessionId"] == "A"
