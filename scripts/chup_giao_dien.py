"""Chụp giao diện thật, dựng Hình 7 và quay video demo thô của LiveLift — tái lập bằng một lệnh.

Vì sao tệp này tồn tại
----------------------
Hồ sơ Sáng tạo trẻ AI 2026 (Bảng C) cần ảnh giao diện cho Hình 7 và một video demo
≤ 5 phút. Ảnh chụp tay thì không ai biết chụp từ bản nào, với dữ liệu gì, có sửa
gì không; kiểm toán 25/09/2026 còn tìm ra một lỗi giao diện (feed bình luận trên
bàn trợ live chỉ cao 1,7 dòng) mà mọi ảnh cũ đều mang theo. Tệp này đi ĐÚNG luồng
người bán trên bản build production đang chạy, đo lại các điểm từng hỏng, và ghi
kèm mỗi lần chụp: bản git, dữ liệu dùng, số đo.

Ba việc
-------
``chup``  Đi trọn luồng trên API + web ĐANG CHẠY: gieo bộ Demo Vàng
          (``POST /demo/seed-vang``), tạo một phiên CHẠY THỬ qua wizard ``/chay-phien``,
          bật bộ thu nguồn Mô phỏng ×10 SAU khi bấm "Bắt đầu phát sóng", chờ bình luận
          về, rồi chụp trang chủ, ``/bat-dau``, wizard bước 3–4, ``/desk``, ``/host``,
          ``/ket-qua`` (mặc định và một phiên Demo Vàng), ``/replay``, ``/bao-cao``.
          Ảnh vào ``docs/img/v2/`` (mỗi ảnh ≤ 400 KB, nén bằng Pillow nếu cần), kèm
          ``chup.json`` (số đo) và ``README.md``. Đo chiều cao feed bình luận
          (``clientHeight``) và đếm số dòng thấy trọn — dưới 8 dòng thì in LỖI.
``ghep``  Dựng ``docs/competition/sang-tao-tre-2026/hinh/h7-giao-dien.png`` từ bốn ảnh
          cắt ``docs/img/v2/h7-*.png``: lưới 2×2, rộng 16 cm, 300 dpi, nhãn ≥ 8 pt,
          cao ≤ 10 cm.
``quay``  Quay màn hình TỰ ĐỘNG theo trình tự cảnh của video 2 trong
          ``docs/competition/sang-tao-tre-2026/07-KICH-BAN-2-VIDEO.md`` (1920×1080), rồi
          dùng ffmpeg ghép MP4 H.264, sinh phụ đề tiếng Việt ``.srt`` (lời dẫn lấy từ kịch
          bản) và bản đã ghi cứng phụ đề. Mọi cảnh đeo nhãn "QUAY TỰ ĐỘNG · DỮ LIỆU MẪU /
          CHẠY THỬ"; đầu ra KHÔNG phải bản nộp — đội phải lồng tiếng và ghi hình cả ba
          thành viên (xem README.md sinh kèm).

Chạy (từ gốc kho; API và web phải đang chạy — tệp này không tự bật server)::

    # API kho bộ nhớ, trạng thái ghi ra thư mục tạm (không chạm data/ của kho mã)
    STORE_BACKEND=memory STORE_SNAPSHOT_PATH=<tạm>/store.json \\
    INGEST_STATE_PATH=<tạm>/ingest.json CORS_ORIGINS=http://127.0.0.1:3765 \\
      .venv/Scripts/python -m uvicorn livelift.api.main:app --host 127.0.0.1 --port 8765
    # web production, API nhúng lúc build
    cd web && LIVELIFT_DIST_DIR=.next-chup NEXT_PUBLIC_API_URL=http://127.0.0.1:8765 npx next build
    LIVELIFT_DIST_DIR=.next-chup npx next start -p 3765

    .venv/Scripts/python scripts/chup_giao_dien.py chup
    .venv/Scripts/python scripts/chup_giao_dien.py ghep
    .venv/Scripts/python scripts/chup_giao_dien.py quay --ra ../VIDEO-2509   # nên dùng kho sạch

Cần Playwright + Chromium (``pip install -e ".[hinh]"`` rồi ``playwright install chromium``),
Pillow, và ``ffmpeg``/``ffprobe`` trên PATH (có libass thì có thêm bản ghi cứng phụ đề).

Luật trung thực (không thương lượng)
------------------------------------
* Chỉ dữ liệu MẪU (``is_demo``) và CHẠY THỬ (``dry_run``); bình luận là kịch bản Mô
  phỏng tổng hợp 100% (số điện thoại trong đó là số giả). Không mở VOD của ai, không
  đọc ``.env``, không đọc ``data/labeling/``.
* Không sửa DOM của sản phẩm. Nhãn cảnh/nhãn "QUAY TỰ ĐỘNG" là lớp phủ của Playwright
  (``page.screencast.show_overlay``); cảnh chia đôi desk/host và các "thẻ terminal" là
  trang khung do chính tệp này dựng, có ghi rõ trên hình.
* Đầu ra lệnh trên thẻ terminal là đầu ra THẬT, chạy ngay trước lúc quay, có giờ chạy.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "src"))

from livelift.console import configure  # noqa: E402

API_MAC_DINH = "http://127.0.0.1:8765"
WEB_MAC_DINH = "http://127.0.0.1:3765"
RA_ANH = GOC / "docs" / "img" / "v2"
HINH = GOC / "docs" / "competition" / "sang-tao-tre-2026" / "hinh"
H7 = HINH / "h7-giao-dien.png"
KICH_BAN = "docs/competition/sang-tao-tre-2026/07-KICH-BAN-2-VIDEO.md"
LENH = "python scripts/chup_giao_dien.py"

TRAN_BYTE_ANH = 400 * 1024
"""Trần dung lượng mỗi ảnh trong docs/img/v2 — ảnh đi vào kho mã và gói Drive."""

KHUNG_CHUP = {"width": 1366, "height": 768}
"""Khung laptop phổ thông mà bàn trợ live được thiết kế cho (kiểm toán 25/09 đo ở đây)."""
KHUNG_HEP = {"width": 640, "height": 900}
"""Khung hẹp cho ảnh cắt của Hình 7: chữ xuống dòng, ô 8 cm in ra vẫn đọc được."""
KHUNG_HOST_H7 = {"width": 1100, "height": 560}
"""Màn người dẫn cho Hình 7c: tỉ lệ gần đúng ô ảnh (~1,95:1), chữ to vẫn đọc được khi in."""
KHUNG_QUAY = {"width": 1920, "height": 1080}

CAO_TOI_DA_TOAN_TRANG = 2800
"""Ảnh toàn trang dài hơn mức này (px CSS) mà ép không xuống 400 KB thì chỉ giữ phần đầu."""

FEED_DONG_TOI_THIEU = 8
"""Feed bình luận phải thấy trọn ít nhất 8 dòng (sự cố 25/09: 55 px = 1,7 dòng)."""

PII_GOC = (
    r"0900[ .]?000",
    r"Thử Nghiệm",
    r"Giả Định",
    r"Không Tên",
    r"khach\.mau",
    r"Mẫu Thử",
    r"phường Mẫu",
    r"thị trấn Mẫu",
)
"""Chuỗi PII GIẢ trong ``mo_phong_kich_ban.jsonl`` — không được còn nguyên trên màn hình."""
PII_DA_CHE = re.compile(r"\[(?:SĐT|ĐỊA CHỈ|EMAIL|TÊN)\]")
CHU_KHOI = re.compile(r"\bBẬT\b|\bTẮT\b|\bON\b|\bOFF\b|[Kk]hối")

# Hình 7 — khổ in
H7_RONG_PX = 1889
"""16 cm ở 300 dpi = 1889,76 px; lấy 1889 để không vượt 16,0 cm (cổng test_ve_hinh_ho_so)."""
H7_CAO_TOI_DA_PX = 1181
"""10 cm ở 300 dpi."""
H7_DPI = 300
H7_CHU_PX = 36
"""36 px ở 300 dpi = 8,64 pt; chèn 15 cm như noi-dung.md thì còn 8,1 pt — vẫn ≥ 8 pt."""
H7_NEN_O = (7, 8, 13)
"""Màu --canvas của giao diện, để ô ảnh cắt và phần đệm liền một mảng."""
H7_O = (
    ("h7-a-lich-khoi.png", "(a) Lịch khối BẬT/TẮT bốc trước giờ phát"),
    ("h7-b-desk-pii-da-che.png", "(b) Bàn trợ live: dữ liệu cá nhân đã che"),
    ("h7-c-host-lam-mu.png", "(c) Màn người dẫn: không thấy khối"),
    ("h7-d-ket-qua-demo-vang.png", "(d) Kết quả Demo Vàng, nhãn DEMO"),
)


# ============================================================ tiện ích chung
def goi_api(base: str, duong: str, body: Any = None, method: str | None = None) -> Any:
    """Gọi API LiveLift (JSON). ``base`` do người chạy truyền vào — chỉ là địa chỉ máy mình."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 — địa chỉ http cục bộ do người chạy truyền
        base + duong,
        data=data,
        method=method or ("GET" if body is None else "POST"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
        raw = r.read().decode("utf-8")
    return json.loads(raw) if raw else None


def kiem_server(api: str, web: str) -> dict:
    """Dừng sớm, nói rõ, nếu API hay web chưa chạy."""
    try:
        suc_khoe = goi_api(api, "/health")
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"LỖI: không gọi được API {api}/health ({e}). Bật API trước (xem --help).")
    try:
        with urllib.request.urlopen(web + "/", timeout=60) as r:  # noqa: S310
            ma = r.status
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"LỖI: không mở được web {web}/ ({e}). Bật web production trước (xem --help).")
    if suc_khoe.get("status") != "ok" or ma != 200:
        sys.exit(f"LỖI: API status={suc_khoe.get('status')}, web HTTP {ma}.")
    return suc_khoe


def chay_lenh(lenh: list[str], cwd: Path | None = None, timeout: int = 900) -> tuple[int, str]:
    """Chạy một lệnh (không qua shell), trả (mã thoát, stdout+stderr)."""
    p = subprocess.run(  # noqa: S603 — danh sách đối số cố định trong tệp này
        lenh,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        env=_env_utf8(),
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _env_utf8() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def ban_git() -> dict:
    """Bản git đang chụp — HEAD và các tệp chưa commit (ảnh phải nói nó chụp từ đâu)."""
    _, head = chay_lenh(["git", "rev-parse", "--short", "HEAD"], cwd=GOC)
    _, nhanh = chay_lenh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=GOC)
    _, st = chay_lenh(["git", "status", "--porcelain", "--untracked-files=no"], cwd=GOC)
    return {
        "head": head.strip(),
        "nhanh": nhanh.strip(),
        "chua_commit": [d[3:] for d in st.splitlines() if d.strip()],
    }


def bay_gio() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def nen_png(duong: Path, tran: int = TRAN_BYTE_ANH) -> dict:
    """Ép PNG xuống ≤ ``tran`` byte: bảng 256/192/128 màu (không dither — mặt phẳng UI
    phẳng), rồi mới thu nhỏ từng nấc 10% (tới 40%). Không ép được thì giữ bản nhỏ nhất và
    trả ``vuot_tran`` — người gọi quyết định (cắt bớt chiều cao trang)."""
    from PIL import Image

    goc = duong.stat().st_size
    if goc <= tran:
        return {"byte": goc, "cach": "giữ nguyên"}
    anh = Image.open(duong).convert("RGB")
    ti_le = 1.0
    while ti_le >= 0.4:
        a = (
            anh
            if ti_le == 1.0
            else anh.resize(
                (round(anh.width * ti_le), round(anh.height * ti_le)), Image.Resampling.LANCZOS
            )
        )
        for mau in (256, 192, 128):
            q = a.quantize(colors=mau, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            tam = duong.with_suffix(".tam.png")
            q.save(tam, optimize=True)
            if tam.stat().st_size <= tran:
                tam.replace(duong)
                return {
                    "byte": duong.stat().st_size,
                    "byte_goc": goc,
                    "cach": f"bảng {mau} màu" + (f", thu {ti_le:.0%}" if ti_le < 1 else ""),
                    "kich_thuoc": [a.width, a.height],
                }
            tam.unlink()
        ti_le = round(ti_le - 0.1, 2)
    q.save(duong, optimize=True)
    return {
        "byte": duong.stat().st_size,
        "byte_goc": goc,
        "cach": "bảng 128 màu, thu 40%",
        "vuot_tran": True,
    }


# ---------------------------------------------------------------- JS dùng chung
JS_DO_FEED = """
() => {
  const ul = document.querySelector('ul[aria-label="Danh sách bình luận"]');
  if (!ul) return null;
  const hop = ul.parentElement;
  const r = hop.getBoundingClientRect();
  const dong = [...ul.children];
  const tron = dong.filter(li => {
    const q = li.getBoundingClientRect();
    return q.top >= r.top - 0.5 && q.bottom <= r.bottom + 0.5;
  });
  const cao = dong.slice(0, 40).map(li => li.getBoundingClientRect().height).sort((a, b) => a - b);
  const buoc = dong.slice(1, 41).map((li, i) => li.getBoundingClientRect().top
                                     - dong[i].getBoundingClientRect().top).sort((a, b) => a - b);
  return {
    buoc_dong_trung_vi: buoc.length ? buoc[Math.floor(buoc.length / 2)] : null,
    client_height: hop.clientHeight,
    scroll_height: hop.scrollHeight,
    so_dong: dong.length,
    dong_thay_tron: tron.length,
    cao_dong_trung_vi: cao.length ? cao[Math.floor(cao.length / 2)] : null,
    chu_thay: tron.map(li => li.innerText.replace(/\\s+/g, ' ').trim()),
  };
}
"""

JS_CUON_FEED_TOI_DONG_CHE = r"""
(mau) => {
  const ul = document.querySelector('ul[aria-label="Danh sách bình luận"]');
  if (!ul) return null;
  const hop = ul.parentElement;
  const dong = [...ul.children];
  const re = new RegExp(mau);
  const che = dong.map(li => re.test(li.innerText));
  const cao = dong[0]?.getBoundingClientRect().height || 32;
  const vua = Math.max(1, Math.floor(hop.clientHeight / cao));
  let tot = -1, dem_tot = -1;
  for (let i = 0; i < dong.length; i++) {
    let d = 0;
    for (let j = i; j < Math.min(dong.length, i + vua); j++) if (che[j]) d++;
    if (d > dem_tot) { dem_tot = d; tot = i; }
  }
  if (tot < 0) return null;
  const dau = Math.max(0, tot - 1);
  hop.scrollTop = dong[dau].offsetTop - 2;
  return {dong_dau: dau, so_dong_che_trong_khung: dem_tot, vua_khung: vua};
}
"""

JS_KHUNG_CAT = r"""
(spec) => {
  // innerText mang cả text-transform (tiêu đề mục in HOA bằng CSS) — so không phân biệt hoa/thường
  const sau = (chu) => {
    const can = chu.toLocaleLowerCase('vi');
    let tot = null;
    for (const e of document.querySelectorAll('body *')) {
      if (!e.getClientRects().length) continue;
      const t = (e.innerText || '').toLocaleLowerCase('vi');
      if (t.includes(can) && (!tot || tot.contains(e))) tot = e;
    }
    return tot;
  };
  // "Thẻ" chứa một mốc: tổ tiên gần nhất là <section> hoặc khung bo góc RỘNG hơn nửa
  // màn hình — không lấy nhầm chính cái huy hiệu bo tròn chứa chữ mốc.
  const the = (e) => {
    for (let x = e; x && x !== document.body; x = x.parentElement) {
      const lop = x.getAttribute('class') || '';
      if ((x.tagName === 'SECTION' || /rounded/.test(lop))
          && x.getBoundingClientRect().width > innerWidth * (spec.rong_toi_thieu || 0.5))
        return x;
    }
    return document.querySelector('main') || document.body;
  };
  const len = (e, n) => { for (let i = 0; e && i < (n || 0); i++) e = e.parentElement; return e; };
  const hcn = (e) => {
    const r = e.getBoundingClientRect();
    return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height};
  };
  const tim_tren = sau(spec.tren), tim_duoi = sau(spec.duoi), tim_ngang = sau(spec.ngang);
  if (!tim_tren || !tim_duoi || !tim_ngang)
    return {thieu: [!tim_tren && spec.tren, !tim_duoi && spec.duoi,
                    !tim_ngang && spec.ngang].filter(Boolean)};
  const tren = tim_tren, duoi = len(tim_duoi, spec.duoi_cha), ngang = the(tim_ngang);
  const a = hcn(tren), b = hcn(duoi), c = hcn(ngang);
  const p = spec.dem || 10;
  const y0 = Math.max(0, a.y - p);
  const y1 = spec.duoi_lay_mep_tren ? b.y - 2 : b.y + b.h + p;
  const x0 = Math.max(0, c.x - p);
  const x1 = Math.min(document.documentElement.scrollWidth, c.x + c.w + p);
  return {x: x0, y: y0, width: x1 - x0, height: Math.min(y1 - y0, spec.cao_toi_da || 1e9)};
}
"""


def cho_on_dinh(page: Any, ms: int = 1500) -> None:
    """Chờ font tải xong và giao diện thôi nhảy (khung xương → số thật)."""
    page.wait_for_load_state("domcontentloaded")
    page.evaluate("document.fonts.ready.then(() => true)")
    page.wait_for_timeout(ms)


def mo_trang(page: Any, url: str, cho_chu: str | None = None, ms: int = 1500) -> None:
    page.goto(url, wait_until="domcontentloaded")
    if cho_chu:
        page.get_by_text(cho_chu).first.wait_for(timeout=30_000)
    cho_on_dinh(page, ms)


def khung_cat(page: Any, spec: dict) -> dict:
    kq = page.evaluate(JS_KHUNG_CAT, spec)
    if "thieu" in kq:
        raise RuntimeError(f"không tìm thấy mốc cắt {kq['thieu']} trên {page.url}")
    return kq


def id_tu_url(url: str, khoa: str) -> str | None:
    m = re.search(khoa + r"=([0-9a-f-]{36})", url)
    return m.group(1) if m else None


def chon_phien_vang(vang: dict, nhom: str, duoi: str = "#1") -> str:
    """Lấy session_id của một phiên Demo Vàng theo nhóm (duong/null/thieu) và đuôi tên."""
    ung_vien = list(vang["nhom"][nhom])
    for sid in ung_vien:
        if str(vang["ket_qua"][sid].get("title", "")).endswith(duoi):
            return sid
    return ung_vien[0]


def pii_tho_trong(chu: str) -> list[str]:
    return [m for m in PII_GOC if re.search(m, chu)]


# ============================================================ wizard (dùng chung)
@dataclass
class PhienChayThu:
    session_id: str = ""
    url_buoc3: str = ""
    host_url: str = ""
    ma_link: list[str] = field(default_factory=list)


def wizard_den_buoc3(page: Any, web: str, cham: Callable[[int], None]) -> PhienChayThu:
    """Bước 1–3 của /chay-phien như người bán lần đầu: sản phẩm mẫu, link mẫu, CHẠY THỬ,
    tạo phiên, bốc thăm. ``cham(ms)`` là nhịp dừng giữa các thao tác (quay chậm, chụp nhanh)."""
    mo_trang(page, web + "/chay-phien", cho_chu="Chuẩn bị buổi live", ms=800)
    cham(900)
    page.get_by_role("button", name="Dùng sản phẩm mẫu").click()
    cham(900)
    page.get_by_role("button", name="+ Thêm sản phẩm").click()
    page.get_by_text("Áo khoác dù 2 lớp").first.wait_for(timeout=20_000)
    page.wait_for_timeout(600)
    cham(700)
    nut_link = page.get_by_role("button", name="Điền link mẫu để chạy thử").first
    try:
        nut_link.wait_for(timeout=5_000)
        nut_link.click()
        cham(900)
    except Exception:  # noqa: BLE001 — mọi sản phẩm đã có link thì nút không hiện
        print("  (không có nút Điền link mẫu — mọi sản phẩm đã có link)")
    page.get_by_role("button", name=re.compile("Xong, sang bước 2")).click()
    page.get_by_text("Chạy thử (không tính vào kết quả)").first.wait_for(timeout=20_000)
    cham(1400)
    page.get_by_text("Chạy thử (không tính vào kết quả)").first.click()
    cham(1100)
    page.get_by_role("button", name=re.compile("Tạo phiên, sang bước 3")).click()
    page.get_by_role("button", name="Bốc thăm lịch BẬT/TẮT").wait_for(timeout=30_000)
    cham(1400)
    page.get_by_role("button", name="Bốc thăm lịch BẬT/TẮT").click()
    page.get_by_role("button", name=re.compile("Xong, sang bước 4")).wait_for(timeout=30_000)
    page.wait_for_timeout(600)
    sid = id_tu_url(page.url, "phien")
    if not sid:
        raise RuntimeError(f"wizard không ghi phiên lên URL: {page.url}")
    return PhienChayThu(session_id=sid, url_buoc3=page.url)


def wizard_buoc4_len_song(
    page: Any, phien: PhienChayThu, cham: Callable[[int], None], giu_host: bool
) -> Any:
    """Bước 4: tick đã dán link, mở màn người dẫn, bấm Bắt đầu phát sóng. Bộ thu KHÔNG
    bật ở đây: nguồn Mô phỏng phát ngay khi bật, nên bật sau khi lên sóng (làn backend,
    kiểm toán 25/09 mục 3.5). Trả trang host (hoặc None nếu đã đóng)."""
    page.get_by_role("button", name=re.compile("Xong, sang bước 4")).click()
    page.get_by_role("button", name=re.compile("Bắt đầu phát sóng")).wait_for(timeout=30_000)
    cho_on_dinh(page, 1200)
    try:  # link đo được tạo khi vào bước 4 — chờ tối đa 8 s, thiếu thì quay tiếp
        page.get_by_text(re.compile(r"/r/[A-Za-z0-9_-]{4,}")).first.wait_for(timeout=8_000)
    except Exception:  # noqa: BLE001
        print("  (bước 4 chưa hiện link đo nào)")
    chu = page.evaluate("() => document.body.innerText")
    phien.ma_link = sorted(set(re.findall(r"/r/([A-Za-z0-9_-]{4,})", chu)))
    cham(800)
    o_tick = page.get_by_label(re.compile("Tôi đã dán"))
    if o_tick.count():
        o_tick.first.check()
    cham(900)
    with page.context.expect_page() as moi:
        page.get_by_role("link", name=re.compile("Mở màn hình người dẫn")).first.click()
    host = moi.value
    phien.host_url = host.url
    if not giu_host:
        host.close()
        host = None
    page.bring_to_front()
    cham(900)
    return host


def bam_bat_dau_phat(page: Any) -> None:
    page.get_by_role("button", name=re.compile("Bắt đầu phát sóng")).click()
    page.wait_for_url(re.compile(r"/desk\?session="), timeout=30_000)
    page.get_by_text("Bộ thu bình luận").first.wait_for(timeout=30_000)


def bat_bo_thu_mo_phong(page: Any, cham: Callable[[int], None]) -> None:
    """Trên /desk: chọn nguồn Mô phỏng, gõ "x10", bấm Bật bộ thu (đúng nút người bán bấm)."""
    khung = page.locator('section[aria-label="Bộ thu bình luận"]').first
    khung.locator("select").first.wait_for(timeout=30_000)
    page.wait_for_function(
        """() => [...document.querySelectorAll('section[aria-label="Bộ thu bình luận"] option')]
                 .some(o => o.value === 'mo_phong')""",
        timeout=30_000,
    )
    khung.locator("select").first.select_option("mo_phong")
    cham(700)
    o_nhap = khung.locator("input").first
    o_nhap.click()
    o_nhap.press_sequentially("x10", delay=90)
    cham(600)
    khung.get_by_role("button", name="Bật bộ thu").click()
    page.get_by_text("Tắt bộ thu").first.wait_for(timeout=30_000)


def ket_thuc_phien(page: Any, cham: Callable[[int], None]) -> None:
    page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
    cham(700)
    page.get_by_role("button", name="Kết thúc phiên").first.click()
    cham(1100)
    page.get_by_role("button", name=re.compile("Kết thúc ngay")).first.click()
    page.get_by_text("Xem báo cáo phiên").first.wait_for(timeout=30_000)


# ============================================================ việc 1: chụp
@dataclass
class NhatKy:
    anh: list[dict] = field(default_factory=list)
    kiem: dict = field(default_factory=dict)
    loi_console: list[str] = field(default_factory=list)
    loi: list[str] = field(default_factory=list)


def chup(api: str, web: str, ra: Path, ban_sao: Path | None) -> int:
    from playwright.sync_api import sync_playwright

    suc_khoe = kiem_server(api, web)
    ra.mkdir(parents=True, exist_ok=True)
    nk = NhatKy()
    git = ban_git()
    bat_dau = bay_gio()
    vang = goi_api(api, "/demo/seed-vang", body={})
    duong1 = chon_phien_vang(vang, "duong", "#1")
    null1 = chon_phien_vang(vang, "null", "#1")
    thieu = chon_phien_vang(vang, "thieu", "")
    print(f"Demo Vàng: DƯƠNG #1 {duong1[:8]} · NULL #1 {null1[:8]} · CHƯA ĐỦ {thieu[:8]}")

    def luu(page: Any, ten: str, mo_ta: str, full: bool = False, clip: dict | None = None) -> None:
        duong = ra / f"{ten}.png"
        if clip is not None:
            page.screenshot(path=str(duong), clip=clip, full_page=True, animations="disabled")
        else:
            page.screenshot(path=str(duong), full_page=full, animations="disabled")
        nen = nen_png(duong)
        cao = CAO_TOI_DA_TOAN_TRANG
        while nen.get("vuot_tran") and full and cao >= 1200:
            # trang quá dài: giữ phần đầu (nói rõ trong chup.json), thay vì thu ảnh tới nhòe
            rong = page.evaluate("() => document.documentElement.clientWidth")
            page.screenshot(
                path=str(duong),
                clip={"x": 0, "y": 0, "width": rong, "height": cao},
                full_page=True,
                animations="disabled",
            )
            nen = nen_png(duong) | {"cat_cao_css": cao}
            cao -= 400
        if nen.get("vuot_tran"):
            nk.loi.append(f"{duong.name} vẫn > {TRAN_BYTE_ANH // 1024} KB sau khi ép")
        nk.anh.append({"tep": duong.name, "mo_ta": mo_ta, "url": page.url, **nen})
        print(f"  {duong.name:42s} {nen['byte'] / 1024:6.0f} KB · {nen['cach']}")

    def ghi_loi_console(tag: str, page: Any) -> None:
        page.on(
            "console",
            lambda m: (
                nk.loi_console.append(f"{tag} {m.type}: {m.text[:200]}")
                if m.type == "error"
                else None
            ),
        )
        page.on("pageerror", lambda e: nk.loi_console.append(f"{tag} pageerror: {str(e)[:200]}"))

    def khong_cham(_ms: int) -> None:
        return None

    def cat_h7(trang: Any, ten: str, mo_ta: str, cac_spec: list[dict], them: Any = None) -> None:
        """Ảnh cắt cho Hình 7: thử lần lượt các bộ mốc; hỏng hết thì ghi LỖI, chụp tiếp."""
        ly_do = ""
        for spec in cac_spec:
            try:
                clip = khung_cat(trang, spec)
            except RuntimeError as e:
                ly_do = str(e)
                continue
            luu(trang, ten, mo_ta, clip=clip | (them(trang) if them else {}))
            return
        nk.loi.append(f"không cắt được {ten}: {ly_do}")

    with sync_playwright() as pw:
        trinh = pw.chromium.launch(headless=True)
        chung = {
            "device_scale_factor": 2,
            "locale": "vi-VN",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "reduced_motion": "reduce",
        }
        ctx = trinh.new_context(viewport=KHUNG_CHUP, **chung)
        hep = trinh.new_context(viewport=KHUNG_HEP, **chung)
        trang_host_h7 = trinh.new_context(viewport=KHUNG_HOST_H7, **chung).new_page()
        page = ctx.new_page()
        page.set_default_timeout(30_000)
        ghi_loi_console("chinh", page)
        trang_hep = hep.new_page()
        trang_hep.set_default_timeout(30_000)

        print("Chụp:")
        mo_trang(page, web + "/", cho_chu="LiveLift")
        luu(page, "01-trang-chu", "Trang chủ: ba lối vào và chip KHO nói rõ dữ liệu mẫu hay thật")

        mo_trang(page, web + "/bat-dau", cho_chu="Buổi live của tôi dùng được gì?")
        for chon in ("Của tôi", "YouTube", "Đang phát"):
            page.get_by_role("button", name=re.compile("^" + chon)).first.click()
            page.wait_for_timeout(300)
        cho_on_dinh(page, 1500)
        luu(
            page,
            "02-bat-dau-ket-qua",
            "/bat-dau sau 3 câu (Của tôi · YouTube · Đang phát): làm được gì ngay, thiếu khoá gì",
            full=True,
        )

        phien = wizard_den_buoc3(page, web, khong_cham)
        sid = phien.session_id
        luu(page, "03-chay-phien-buoc3-lich-khoi", "Wizard bước 3: lịch 16 khối BẬT/TẮT đã bốc")
        mo_trang(trang_hep, phien.url_buoc3, cho_chu="Bốc thăm lịch BẬT/TẮT", ms=2000)
        trang_hep.get_by_role("button", name=re.compile("Xong, sang bước 4")).wait_for()
        cat_h7(
            trang_hep,
            "h7-a-lich-khoi",
            "Hình 7a: lịch khối của phiên chạy thử (khung hẹp 640 px)",
            [
                {
                    "tren": "Bước 3/4",
                    "duoi": "Chỉ hiện trên bàn trợ live",
                    "dem": 12,
                    "ngang": "Bốc thăm lịch BẬT/TẮT",
                },
                {
                    "tren": "Bốc thăm lịch BẬT/TẮT",
                    "duoi": "Khối TẮT",
                    "dem": 12,
                    "ngang": "Bốc thăm lịch BẬT/TẮT",
                },
            ],
        )

        host = wizard_buoc4_len_song(page, phien, khong_cham, giu_host=True)
        ghi_loi_console("host", host)
        page.wait_for_timeout(800)
        luu(
            page, "04-chay-phien-buoc4-checklist", "Wizard bước 4: checklist trước giờ G", full=True
        )
        thong_tin = goi_api(api, f"/sessions/{sid}")
        nk.kiem["phien_chay_thu"] = {
            k: thong_tin.get(k)
            for k in (
                "session_id",
                "status",
                "dry_run",
                "is_demo",
                "platform",
                "planned_duration_min",
                "title",
            )
        }
        nk.kiem["so_link_do"] = len(phien.ma_link)

        bam_bat_dau_phat(page)
        cho_on_dinh(page, 1500)
        bat_bo_thu_mo_phong(page, khong_cham)
        t_bat = time.time()
        print(f"  phiên {sid[:8]} lên sóng, bộ thu Mô phỏng ×10 đã bật; chờ bình luận…")
        page.wait_for_timeout(20_000)
        luu(page, "05-desk-dang-live", "Bàn trợ live đang phát: khối hiện tại, đồng hồ khối, lịch")
        host.bring_to_front()
        host.wait_for_timeout(1000)
        luu(
            host,
            "06-host-lam-mu",
            "Màn người dẫn cùng phiên: chỉ thời gian, sản phẩm, giá, tồn kho",
        )
        page.bring_to_front()

        # chờ đủ kịch bản (200 câu ×10 ≈ 131 s) để feed có mọi câu PII giả
        so_bl = 0
        while time.time() - t_bat < 170:
            trang_thai = goi_api(api, f"/sessions/{sid}/ingest")
            so_bl = int(trang_thai.get("comments_posted") or 0)
            if so_bl >= 200:
                break
            page.wait_for_timeout(5000)
        page.wait_for_timeout(3000)
        nk.kiem["bo_thu_da_ghi"] = so_bl

        # feed: cuộn trang tới khung bình luận, cuộn feed tới dòng có câu đã che
        page.locator('ul[aria-label="Danh sách bình luận"]').first.scroll_into_view_if_needed()
        page.evaluate(
            """() => { const ul = document.querySelector('ul[aria-label="Danh sách bình luận"]');
                       const r = ul.parentElement.getBoundingClientRect();
                       window.scrollBy(0, r.bottom - innerHeight + 24); }"""
        )
        page.wait_for_timeout(600)
        cuon = page.evaluate(JS_CUON_FEED_TOI_DONG_CHE, PII_DA_CHE.pattern)
        page.wait_for_timeout(1200)
        do = page.evaluate(JS_DO_FEED)
        nk.kiem["feed_1366x768"] = {**(do or {}), "cuon": cuon}
        if not do or do["dong_thay_tron"] < FEED_DONG_TOI_THIEU:
            nk.loi.append(
                f"feed bình luận chỉ thấy trọn {do and do['dong_thay_tron']} dòng "
                f"(clientHeight {do and do['client_height']} px) — dưới {FEED_DONG_TOI_THIEU}"
            )
        chu_desk = page.evaluate("() => document.body.innerText")
        nk.kiem["pii_goc_tren_desk"] = pii_tho_trong(chu_desk)
        nk.kiem["nhan_che_tren_desk"] = sorted(set(PII_DA_CHE.findall(chu_desk)))
        luu(
            page,
            "05b-desk-binh-luan-da-che",
            "Feed bình luận trên desk: câu có SĐT giả đã thành [SĐT]",
        )
        cat_h7(
            page,
            "h7-b-desk-pii-da-che",
            "Hình 7b: feed bình luận desk (1366×768), dòng có dữ liệu cá nhân giả đã che",
            [
                {
                    "tren": "Bình luận trực tiếp",
                    "duoi": "Bình luận trực tiếp",
                    "dem": 8,
                    "ngang": "Radar bình luận",
                    "rong_toi_thieu": 0.3,
                },
            ],
            them=_cao_feed,
        )

        binh_luan = goi_api(api, f"/sessions/{sid}/comments")
        nk.kiem["pii_goc_trong_api"] = [
            c["text"] for c in binh_luan if pii_tho_trong(c.get("text") or "")
        ]
        da_che = [c["text"] for c in binh_luan if PII_DA_CHE.search(c["text"])]
        nk.kiem["vi_du_da_che"] = da_che[:10]
        nk.kiem["so_binh_luan_api"] = len(binh_luan)

        tt_host = goi_api(api, f"/sessions/{sid}/state?role=host")
        nk.kiem["khoa_payload_host"] = sorted(tt_host.keys())
        chu_host = host.evaluate("() => document.body.innerText")
        nk.kiem["host_co_chu_khoi"] = bool(CHU_KHOI.search(chu_host))
        mo_trang(trang_host_h7, phien.host_url, cho_chu="Màn người dẫn", ms=2500)
        cat_h7(
            trang_host_h7,
            "h7-c-host-lam-mu",
            f"Hình 7c: màn người dẫn cùng phiên (khung {KHUNG_HOST_H7['width']}×"
            f"{KHUNG_HOST_H7['height']})",
            [
                {
                    "tren": "Màn người dẫn",
                    "duoi": "Kéo cửa sổ này sang màn phụ",
                    "dem": 16,
                    "ngang": "Màn người dẫn",
                    "duoi_lay_mep_tren": True,
                },
                {
                    "tren": "Màn người dẫn",
                    "duoi": "Màn người dẫn",
                    "dem": 16,
                    "ngang": "Màn người dẫn",
                    "cao_toi_da": KHUNG_HOST_H7["height"],
                },
            ],
            them=_toan_ngang,
        )
        host.close()

        ket_thuc_phien(page, khong_cham)
        cho_on_dinh(page, 1500)
        nk.kiem["trang_thai_sau_ket_thuc"] = goi_api(api, f"/sessions/{sid}").get("status")

        mo_trang(page, f"{web}/bao-cao/{sid}", cho_chu="Tổng quan", ms=3500)
        luu(
            page,
            "10-bao-cao-chay-thu",
            "Báo cáo sau phiên chạy thử: nhãn CHẠY THỬ, THIẾU trung thực",
            full=True,
        )

        mo_trang(page, web + "/ket-qua", cho_chu="Kết quả & chiến lược", ms=3000)
        luu(
            page,
            "07-ket-qua-mac-dinh-that-chua-du",
            "/ket-qua mặc định = dữ liệu thật: 0 phiên thật, CHƯA ĐỦ ĐIỀU KIỆN",
            full=True,
        )
        tom = goi_api(api, "/experiment/summary?env=real")
        nk.kiem["ket_qua_that"] = {k: tom.get(k) for k in ("n_sessions", "estimable")}

        mo_trang(page, f"{web}/ket-qua?phien={duong1}", cho_chu="PHIÊN DEMO", ms=2500)
        luu(page, "08-ket-qua-demo-vang-duong", "Kết quả một phiên Demo Vàng DƯƠNG (dữ liệu mẫu)")
        mo_trang(page, f"{web}/ket-qua?phien={null1}", cho_chu="PHIÊN DEMO", ms=2500)
        luu(page, "08b-ket-qua-demo-vang-null", "Demo Vàng NULL: KTC chứa 0, hệ thống nói không rõ")
        mo_trang(page, f"{web}/ket-qua?phien={thieu}", cho_chu="PHIÊN DEMO", ms=2500)
        luu(page, "08c-ket-qua-demo-vang-chua-du", "Demo Vàng CHƯA ĐỦ: 3 khối, không trả số")
        mo_trang(trang_hep, f"{web}/ket-qua?phien={duong1}", cho_chu="PHIÊN DEMO", ms=2500)
        cat_h7(
            trang_hep,
            "h7-d-ket-qua-demo-vang",
            "Hình 7d: kết quả phiên Demo Vàng DƯƠNG #1 (khung hẹp 640 px)",
            [
                {
                    "tren": "HIỆU ỨNG RÕ",
                    "duoi": "độ tin cậy 95%",
                    "dem": 14,
                    "ngang": "HIỆU ỨNG RÕ",
                },
                {
                    "tren": "HIỆU ỨNG RÕ",
                    "duoi": "MỨC Ý NGHĨA",
                    "dem": 14,
                    "ngang": "HIỆU ỨNG RÕ",
                    "duoi_lay_mep_tren": True,
                },
                {
                    "tren": "DEMO — dữ liệu mẫu",
                    "duoi": "KTC 95%",
                    "dem": 14,
                    "ngang": "DEMO — dữ liệu mẫu",
                },
            ],
        )

        mo_trang(page, f"{web}/replay?session={duong1}", cho_chu="Xem lại", ms=3500)
        luu(page, "09-replay", "Xem lại phiên Demo Vàng: tua, radar theo vị trí phát (DỮ LIỆU MẪU)")
        trinh.close()

    ket = {
        "lenh": f"{LENH} chup",
        "bat_dau": bat_dau,
        "xong": bay_gio(),
        "git": git,
        "api": api,
        "web": web,
        "kho": {k: suc_khoe.get(k) for k in ("storage_mode", "durable")},
        "khung": {
            "chinh": KHUNG_CHUP,
            "hep": KHUNG_HEP,
            "host_h7": KHUNG_HOST_H7,
            "device_scale_factor": 2,
        },
        "demo_vang": {"duong_1": duong1, "null_1": null1, "chua_du": thieu},
        "phien_chay_thu": sid,
        "anh": nk.anh,
        "kiem": nk.kiem,
        "loi_console": nk.loi_console,
        "loi": nk.loi,
    }
    (ra / "chup.json").write_text(json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    ghi_readme_anh(ra, ket)
    if ban_sao is not None:
        sao_chep_goi_drive(ra, ban_sao, ket)
    for dong in _tom_tat_kiem(ket):
        print(dong)
    return 1 if nk.loi or ket["kiem"].get("pii_goc_tren_desk") else 0


def _cao_feed(page: Any) -> dict:
    """Khung cắt đúng khối "Bình luận trực tiếp": từ tiêu đề tới đáy vùng cuộn."""
    return page.evaluate(
        """() => {
          const ul = document.querySelector('ul[aria-label="Danh sách bình luận"]');
          const hop = ul.parentElement.getBoundingClientRect();
          let tieu_de = ul.parentElement;
          while (tieu_de && !(tieu_de.innerText || '').startsWith('Bình luận trực tiếp'))
            tieu_de = tieu_de.parentElement;
          const t = (tieu_de || ul.parentElement).getBoundingClientRect();
          return {y: t.top + scrollY - 8, height: hop.bottom - t.top + 16};
        }"""
    )


def _toan_ngang(page: Any) -> dict:
    """Mở khung cắt ra hết bề ngang trang (màn host căn giữa, chữ to)."""
    return page.evaluate("() => ({x: 0, width: document.documentElement.clientWidth})")


def _tom_tat_kiem(ket: dict) -> list[str]:
    k = ket["kiem"]
    feed = k.get("feed_1366x768") or {}
    dong = [
        "",
        "Kiểm:",
        f"  feed desk 1366×768: clientHeight {feed.get('client_height')} px, thấy trọn "
        f"{feed.get('dong_thay_tron')} dòng (cao dòng {feed.get('cao_dong_trung_vi')} px, bước "
        f"{feed.get('buoc_dong_trung_vi')} px), "
        f"{feed.get('so_dong')} bình luận",
        f"  PII gốc trên desk: {k.get('pii_goc_tren_desk')} · trong API: "
        f"{len(k.get('pii_goc_trong_api') or [])} · nhãn che thấy: {k.get('nhan_che_tren_desk')}",
        f"  payload host: {k.get('khoa_payload_host')} · chữ khối trên host: "
        f"{k.get('host_co_chu_khoi')}",
        f"  phiên chạy thử: {k.get('phien_chay_thu')} → {k.get('trang_thai_sau_ket_thuc')}",
        f"  /experiment/summary?env=real: {k.get('ket_qua_that')}",
        f"  lỗi console: {len(ket['loi_console'])}",
    ]
    dong += [f"  LỖI: {x}" for x in ket["loi"]]
    return dong


def ghi_readme_anh(ra: Path, ket: dict) -> None:
    git = ket["git"]
    chua = ", ".join(f"`{p}`" for p in git["chua_commit"]) or "không có"
    k = ket["kiem"]
    feed = k.get("feed_1366x768") or {}
    dong = [
        f"# Ảnh giao diện v2 — chụp tự động {ket['bat_dau'][8:10]}/{ket['bat_dau'][5:7]}/"
        f"{ket['bat_dau'][:4]}",
        "",
        f"*Sinh bằng* `{LENH} chup` *— không sửa tay; chụp lại bằng lệnh.* Số đo đầy đủ: "
        "`chup.json`.",
        "",
        f"- Bản build: nhánh `{git['nhanh']}`, HEAD `{git['head']}`; tệp chưa commit lúc chụp: "
        f"{chua}.",
        f"- Chụp lúc {ket['bat_dau']} → {ket['xong']}; Chromium headless (Playwright), khung "
        f"{KHUNG_CHUP['width']}×{KHUNG_CHUP['height']}, device scale 2 (ảnh cắt `h7-*` ghi "
        "khung riêng ở cột Nội dung); ảnh > "
        f"{TRAN_BYTE_ANH // 1024} KB được ép bằng bảng màu Pillow (không dither).",
        f"- Kho API: `{ket['kho'].get('storage_mode')}` (bộ nhớ, không bền) — dữ liệu chỉ gồm "
        "bộ Demo Vàng (`is_demo`, dữ liệu MẪU) và một phiên CHẠY THỬ (`dry_run`) tạo qua "
        "wizard; bình luận là kịch bản Mô phỏng tổng hợp ×10 (số điện thoại, địa chỉ, email "
        'đều GIẢ), bật SAU khi bấm "Bắt đầu phát sóng".',
        f"- Feed bình luận trên desk (1366×768): `clientHeight` {feed.get('client_height')} px, "
        f"thấy trọn {feed.get('dong_thay_tron')} dòng (ngưỡng {FEED_DONG_TOI_THIEU}).",
        f"- Chuỗi PII giả còn nguyên trên desk: {len(k.get('pii_goc_tren_desk') or [])}; "
        f"trong `GET /sessions/{{id}}/comments`: {len(k.get('pii_goc_trong_api') or [])}. "
        f"Payload `state?role=host` chỉ có khoá {', '.join(k.get('khoa_payload_host') or [])}.",
        f"- `/experiment/summary?env=real` sau phiên chạy thử: "
        f"`n_sessions={(k.get('ket_qua_that') or {}).get('n_sessions')}` — dự án có 0 phiên thí "
        "nghiệm ngẫu nhiên thật.",
        "",
        "| Ảnh | Nội dung |",
        "|---|---|",
    ]
    dong += [f"| ![{a['mo_ta']}]({a['tep']}) | `{a['tep']}` — {a['mo_ta']} |" for a in ket["anh"]]
    dong += [
        "",
        "Ảnh `h7-*` là ảnh cắt đầu vào của Hình 7 hồ sơ "
        "(`docs/competition/sang-tao-tre-2026/hinh/h7-giao-dien.png`, dựng bằng "
        f"`{LENH} ghep`).",
        "",
    ]
    (ra / "README.md").write_text("\n".join(dong), encoding="utf-8")


def sao_chep_goi_drive(ra: Path, dich: Path, ket: dict) -> None:
    """Bản sao cho gói Drive, tên theo quy ước ``YYYY-MM-DD_<commit>_<man-hinh>.png``."""
    dich.mkdir(parents=True, exist_ok=True)
    ngay = ket["bat_dau"][:10]
    head = ket["git"]["head"]
    da_chep = []
    for a in ket["anh"]:
        if a["tep"].startswith("h7-"):
            continue
        ten = f"{ngay}_{head}_{a['tep'][:-4]}.png"
        shutil.copy2(ra / a["tep"], dich / ten)
        da_chep.append((ten, a["mo_ta"]))
    chu = [
        f"# Ảnh giao diện chụp {ngay[8:10]}/{ngay[5:7]}/{ngay[:4]} (bản `{head}`)",
        "",
        f"Chụp tự động bằng `{LENH} chup` trên bản build production của nhánh "
        f"`{ket['git']['nhanh']}` (HEAD `{head}`"
        + (
            f"; kèm {len(ket['git']['chua_commit'])} tệp chưa commit: "
            + ", ".join(ket["git"]["chua_commit"])
            if ket["git"]["chua_commit"]
            else ""
        )
        + "). Dữ liệu: Demo Vàng (MẪU) và một phiên CHẠY THỬ, bình luận Mô phỏng tổng hợp; "
        "không có dữ liệu cá nhân thật. Bản gốc và số đo: `docs/img/v2/` trong kho mã.",
        "",
        *[f"- `{t}` — {m}" for t, m in da_chep],
        "",
    ]
    (dich / f"{ngay}_{head}_GHI-CHU.md").write_text("\n".join(chu), encoding="utf-8")
    print(f"  đã chép {len(da_chep)} ảnh sang {dich}")


# ============================================================ việc 2: ghép Hình 7
def _phong(co: int, dam: bool = False) -> Any:
    from PIL import ImageFont

    ung_vien = (
        ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf"]
        if dam
        else ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"]
    )
    try:
        import matplotlib

        ung_vien.append(
            str(
                Path(matplotlib.__file__).parent
                / "mpl-data/fonts/ttf"
                / ("DejaVuSans-Bold.ttf" if dam else "DejaVuSans.ttf")
            )
        )
    except ImportError:
        pass
    for p in ung_vien:
        if Path(p).is_file():
            return ImageFont.truetype(p, co)
    sys.exit("LỖI: không tìm thấy phông Arial/DejaVu có dấu tiếng Việt.")


def _xuong_dong(chu: str, phong: Any, rong: int) -> list[str]:
    tu, dong, hien = chu.split(), [], ""
    for t in tu:
        thu = f"{hien} {t}".strip()
        if phong.getlength(thu) <= rong or not hien:
            hien = thu
        else:
            dong.append(hien)
            hien = t
    if hien:
        dong.append(hien)
    return dong


def _tuong_doi(duong: Path) -> str:
    try:
        return str(duong.relative_to(GOC))
    except ValueError:
        return str(duong)


def ghep(ra_anh: Path, dich: Path) -> int:
    from PIL import Image, ImageDraw

    thieu = [t for t, _ in H7_O if not (ra_anh / t).is_file()]
    if thieu:
        sys.exit(f"LỖI: thiếu ảnh cắt {thieu} — chạy `{LENH} chup` trước.")
    ket = json.loads((ra_anh / "chup.json").read_text(encoding="utf-8"))
    khe = 24
    o_rong = (H7_RONG_PX - khe) // 2
    phong_nhan = _phong(H7_CHU_PX, dam=True)
    phong_chan = _phong(H7_CHU_PX)
    dong_cao = round(H7_CHU_PX * 1.22)
    nhan = [_xuong_dong(c, phong_nhan, o_rong) for _, c in H7_O]
    so_dong_nhan = [max(len(nhan[0]), len(nhan[1])), max(len(nhan[2]), len(nhan[3]))]
    head = ket["git"]["head"]
    chan = (
        f"Chụp tự động bản build {head} ngày "
        f"{ket['bat_dau'][8:10]}/{ket['bat_dau'][5:7]}/{ket['bat_dau'][:4]} "
        "(scripts/chup_giao_dien.py). (a)–(c): phiên CHẠY THỬ, bình luận mô phỏng tổng hợp; "
        "(d): Demo Vàng — dữ liệu mẫu, không phải kết quả thật."
    )
    dong_chan = _xuong_dong(chan, phong_chan, H7_RONG_PX)
    cao_chu = (sum(so_dong_nhan) + len(dong_chan)) * dong_cao
    dem_nhan, dem_hang, dem_chan = 8, 18, 14
    dem_dau = 6  # dấu chồng tiếng Việt (Ể, Ẫ) cao hơn đường ascent của phông
    o_cao = (H7_CAO_TOI_DA_PX - dem_dau - cao_chu - 2 * dem_nhan - dem_hang - dem_chan) // 2
    cao = dem_dau + cao_chu + 2 * dem_nhan + 2 * o_cao + dem_hang + dem_chan
    nen = Image.new("RGB", (H7_RONG_PX, cao), "white")
    ve = ImageDraw.Draw(nen)
    y = dem_dau
    bao_cao = []
    for hang in range(2):
        for cot in range(2):
            i = hang * 2 + cot
            x = cot * (o_rong + khe)
            for j, d in enumerate(nhan[i]):
                ve.text((x, y + j * dong_cao), d, font=phong_nhan, fill=(20, 20, 20))
            y_anh = y + so_dong_nhan[hang] * dong_cao + dem_nhan
            anh = Image.open(ra_anh / H7_O[i][0]).convert("RGB")
            ti = min(o_rong / anh.width, o_cao / anh.height)
            nho = anh.resize(
                (round(anh.width * ti), round(anh.height * ti)), Image.Resampling.LANCZOS
            )
            o = Image.new("RGB", (o_rong, o_cao), H7_NEN_O)
            o.paste(nho, ((o_rong - nho.width) // 2, (o_cao - nho.height) // 2))
            nen.paste(o, (x, y_anh))
            bao_cao.append(
                {"o": H7_O[i][0], "ti_le": round(ti, 3), "anh_px": [anh.width, anh.height]}
            )
        y = y + so_dong_nhan[hang] * dong_cao + dem_nhan + o_cao + dem_hang
    y += dem_chan - dem_hang
    for j, d in enumerate(dong_chan):
        ve.text((0, y + j * dong_cao), d, font=phong_chan, fill=(70, 70, 70))
    dich.parent.mkdir(parents=True, exist_ok=True)
    nen.save(dich, dpi=(H7_DPI, H7_DPI), optimize=True)
    rong_cm = H7_RONG_PX / H7_DPI * 2.54
    cao_cm = cao / H7_DPI * 2.54
    print(
        f"Hình 7: {_tuong_doi(dich)} — {H7_RONG_PX}×{cao} px = {rong_cm:.2f}×{cao_cm:.2f} cm "
        f"ở {H7_DPI} dpi; chữ {H7_CHU_PX} px = {H7_CHU_PX * 72 / H7_DPI:.2f} pt; "
        f"{dich.stat().st_size / 1024:.0f} KB"
    )
    for b in bao_cao:
        print(f"  {b['o']:30s} ảnh {b['anh_px'][0]}×{b['anh_px'][1]} px, thu {b['ti_le']}")
    if cao > H7_CAO_TOI_DA_PX:
        print(f"LỖI: Hình 7 cao {cao_cm:.2f} cm > 10 cm")
        return 1
    return 0


# ============================================================ việc 3: quay video
@dataclass
class Canh:
    ma: str
    ten: str
    loi_dan: str
    giay: float
    so: int | None = None
    mo_ta: str = ""


CANH = (
    Canh("mo_dau", "Bản quay tự động", "", 7),
    Canh(
        "mo",
        "Mở",
        "Mọi màn hình thầy cô sắp xem đều ghi rõ đâu là dữ liệu mẫu, đâu là dữ liệu thật. "
        "Hôm nay mọi bình luận là dữ liệu mô phỏng.",
        11,
        1,
        "chip dữ liệu mẫu / dữ liệu thật",
    ),
    Canh(
        "chuan_bi",
        "Vận hành (1): chuẩn bị phiên",
        "Lịch bốc thăm sinh ở đây, trước giờ phát, kèm mã băm của tham số và hạt giống. "
        "Ai giữ tệp thiết kế cũng tính lại được mã này để thấy lịch không bị sửa.",
        42,
        2,
        "sản phẩm mẫu, link mẫu, Chạy thử, bốc thăm lịch 16 khối",
    ),
    Canh(
        "cong_chan",
        "Vận hành (2): cổng chặn",
        "Phiên chưa có lịch thì chính người tạo ra nó cũng không cho lên sóng được.",
        21,
        3,
        "POST /sessions/{id}/start với phiên nháp chưa bốc lịch → 409",
    ),
    Canh(
        "len_song",
        "Vận hành (3): lên sóng",
        "Bộ thu bình luận chạy nền trong máy chủ, bật bằng một nút. Nguồn Mô phỏng chỉ dùng "
        "được cho phiên chạy thử — phiên thật bị máy chủ từ chối.",
        22,
        4,
        "checklist bước 4, Bắt đầu phát sóng, bật bộ thu Mô phỏng ×10",
    ),
    Canh(
        "desk",
        "Chức năng chính (1): bàn trợ live",
        "Đây là một số điện thoại giả trong kịch bản mô phỏng — và đây là thứ được ghi xuống: "
        "[SĐT]. Bộ lọc chạy trước khi ghi đĩa. Radar ý định cho người trợ live thấy khách "
        "đang hỏi gì; bản đang chạy mặc định là bản cũ, và nhãn này không dùng để tính tác động.",
        46,
        5,
        "đồng hồ khối, bình luận đã che, radar ý định",
    ),
    Canh(
        "lam_mu",
        "Chức năng chính (2): làm mù người dẫn",
        "Cùng một phiên. Màn người dẫn chỉ có thời gian, sản phẩm đang ghim, giá, tồn kho — "
        "không có khối, không có nhánh.",
        18,
        6,
        "desk và host cùng phiên, chia đôi",
    ),
    Canh(
        "ket_qua",
        "Kết quả xử lý",
        "Phiên chạy thử không lọt vào kết quả thật. Không đủ dữ liệu thì hệ thống nói chưa "
        "đủ, không ép ra một con số. Còn kết quả thật hôm nay là 0 phiên — đúng như hồ sơ.",
        52,
        7,
        "kết thúc phiên, báo cáo chạy thử, ba trạng thái Demo Vàng, kết quả thật",
    ),
    Canh(
        "tich_hop",
        "Khả năng tích hợp",
        "Mỗi nền tảng là một bộ nối riêng qua API chính thức; lõi phân tích không đổi. Đơn "
        "hàng nhập từ tệp xuất của Seller Center, không đọc thông tin người mua. Hôm nay chúng "
        "em chưa có khóa nền tảng nào, nên luồng thầy cô vừa xem chạy bằng nguồn mô phỏng.",
        34,
        8,
        "/bat-dau, ô nhập đơn CSV, link đo, kiểm tra khoá YouTube",
    ),
    Canh(
        "ung_dung",
        "Khả năng ứng dụng",
        "Mỗi con số trong hồ sơ có lệnh chạy lại trong kho mã công khai này. Sản phẩm dùng "
        "được cho nhà bán tự phát sóng có lượng xem ổn định, và cho mọi nơi có một kênh phát, "
        "nhiều người xem.",
        18,
        9,
        "chạy test bộ lọc dữ liệu cá nhân",
    ),
    Canh("chot", "Chốt", "Cảm ơn thầy cô đã theo dõi.", 7),
)
CANH_THEO_MA = {c.ma: c for c in CANH}
TRAN_GIAY_VIDEO = 285.0
NHIP_QUAY = 1.5
"""Nhân mọi khoảng dừng giữa hai thao tác khi quay — đủ chậm để người xem đọc kịp."""
"""Trần tự đặt (4:45) — thể lệ cho 5:00; chừa 15 giây cho đội ghép lời dẫn/webcam."""

PHONG_GOOGLE = (
    "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700"
    "&family=JetBrains+Mono:wght@400;700&display=swap"
)
CSS_THE = """
<meta charset="utf-8">
<link href="__PHONG__" rel="stylesheet">
<style>
 html,body{margin:0;height:100%;background:#07080d;color:#e8e9ef;
   font-family:'Be Vietnam Pro',Arial,sans-serif}
 .khung{box-sizing:border-box;height:100%;padding:110px 150px;display:flex;flex-direction:column;
   justify-content:center;gap:26px}
 h1{font-size:54px;margin:0;letter-spacing:-.02em}
 .nho{font-size:26px;line-height:1.5;color:#b9bccb;margin:0}
 .vang{color:#fbbf24;font-weight:700}
 .the{display:inline-block;border:1px solid rgba(251,191,36,.6);color:#fbbf24;border-radius:999px;
   padding:6px 16px;font-weight:700;font-size:20px;letter-spacing:.06em}
 pre{font-family:'JetBrains Mono',Consolas,monospace;font-size:17px;line-height:1.45;margin:0;
   white-space:pre-wrap;word-break:break-word;color:#d7dae3}
 .tm{box-sizing:border-box;height:100%;padding:92px 60px 40px;display:flex;flex-direction:column;
   gap:14px}
 .tm .dau{font-size:19px;color:#b9bccb}
 .tm .hop{flex:1;overflow:auto;background:#0d0f16;border:1px solid rgba(255,255,255,.11);
   border-radius:10px;padding:18px 22px}
 .lenh{color:#7ee787;font-weight:700}
</style>
""".replace("__PHONG__", PHONG_GOOGLE)


def _lop_phu(canh: Canh) -> str:
    return (
        '<div style="position:fixed;top:46px;right:14px;z-index:2147483647;max-width:520px;'
        "background:rgba(7,8,13,.9);border:1px solid rgba(251,191,36,.55);border-radius:8px;"
        "padding:6px 12px;font:600 13px/1.4 'Be Vietnam Pro',Arial,sans-serif;color:#f5f5f4;"
        'pointer-events:none">'
        '<div style="color:#fbbf24;font-size:11px;letter-spacing:.05em">'
        "QUAY TỰ ĐỘNG · SẢN PHẨM THẬT · DỮ LIỆU MẪU / CHẠY THỬ</div>"
        f'<div style="font-size:15px">{canh.so}/9 · {html.escape(canh.ten)}</div></div>'
    )


def the_terminal(
    lenh: str, ra_lenh: str, ma: int, luc: str, ghi_chu: str, canh: Canh | None = None
) -> str:
    # che mọi chuỗi trông như khoá/token (≥ 32 ký tự liền) — phòng khi máy quay có khoá thật
    sach = re.sub(r"(?=[A-Za-z0-9_\-]*[A-Za-z0-9])[A-Za-z0-9_\-]{32,}", "[đã che]", ra_lenh)
    return (
        f"<html><head>{CSS_THE}</head><body>{_lop_phu(canh) if canh else ''}<div class='tm'>"
        f"<div class='dau'>Đầu ra THẬT của lệnh, chạy lúc {html.escape(luc)} trên máy quay "
        f"(mã thoát {ma}) · trình quay tự động hiển thị lại · {html.escape(ghi_chu)}</div>"
        f"<div class='hop' id='hop'><pre><span class='lenh'>$ {html.escape(lenh)}</span>\n"
        f"{html.escape(sach.rstrip())}</pre></div></div></body></html>"
    )


def the_mo_dau(git: dict) -> str:
    return (
        f"<html><head>{CSS_THE}</head><body><div class='khung'>"
        "<span class='the'>BẢN QUAY THÔ · KHÔNG PHẢI BẢN NỘP</span>"
        "<h1>LiveLift — video demo sản phẩm</h1>"
        "<p class='nho'>Quay màn hình <span class='vang'>tự động</span> (Playwright, Chromium "
        f"1920×1080) trên sản phẩm thật chạy tại máy nhóm, bản build <b>{html.escape(git['head'])}"
        f"</b>, {datetime.now().strftime('%d/%m/%Y')}.</p>"
        "<p class='nho'>Dữ liệu: bộ Demo Vàng (dữ liệu <span class='vang'>MẪU</span>) và một "
        "phiên <span class='vang'>CHẠY THỬ</span>; mọi bình luận là dữ liệu mô phỏng tổng hợp, "
        "số điện thoại là số giả. Chưa có lời dẫn — phụ đề là lời dẫn theo kịch bản.</p>"
        "</div></body></html>"
    )


def the_chot() -> str:
    return (
        f"<html><head>{CSS_THE}</head><body><div class='khung'>"
        "<span class='the'>HẾT BẢN QUAY TỰ ĐỘNG</span>"
        "<h1>Cảm ơn thầy cô đã theo dõi.</h1>"
        "<p class='nho'>Trước khi nộp, đội phải: lồng tiếng theo kịch bản; ghi hình cả ba "
        "thành viên (ô webcam); quay thêm cảnh trang GitHub của kho mã; kê khai rằng phần quay "
        "màn hình được thực hiện tự động.</p>"
        "</div></body></html>"
    )


def the_chia_doi(web: str, sid: str) -> str:
    ti = 958 / 1366
    cao_iframe = round((1080 - 64) / ti)
    return (
        f"<html><head>{CSS_THE}<style>"
        "body{overflow:hidden}.dau{position:absolute;top:0;left:0;right:0;height:64px;"
        "display:flex;align-items:center;justify-content:space-between;padding:0 16px;"
        "box-sizing:border-box;background:#13161f;border-bottom:1px solid rgba(255,255,255,.11);"
        "font-size:15px}.dau b{color:#fbbf24}"
        ".cot{position:absolute;top:64px;width:958px;height:1016px;overflow:hidden}"
        ".trai{left:0}.phai{left:962px;border-left:4px solid #fbbf24;box-sizing:border-box}"
        f"iframe{{border:0;width:1366px;height:{cao_iframe}px;transform:scale({ti:.4f});"
        "transform-origin:0 0}"
        "</style></head><body><div class='dau'>"
        "<span><b>QUAY TỰ ĐỘNG · 6/9 · Chức năng chính (2): làm mù người dẫn</b></span>"
        "<span>Khung chia đôi do trình quay dựng: 2 khung nhúng, CÙNG MỘT PHIÊN đang phát · "
        "trái /desk (người trợ live) · phải /host (người dẫn)</span></div>"
        f"<div class='cot trai'><iframe src='{web}/desk?session={sid}'></iframe></div>"
        f"<div class='cot phai'><iframe src='{web}/host?session={sid}'></iframe></div>"
        "</body></html>"
    )


@dataclass
class BanGhi:
    """Khung hình JPEG của screencast + mốc cảnh, theo giờ đồng hồ (giây epoch).

    Mốc của khung là giờ NHẬN khung (``time.time()``), không phải ``timestamp`` do
    Chromium gửi: lần quay 25/09 dùng ``timestamp`` thì hình trôi chậm dần so với mốc
    cảnh (tới ~24 s ở phút thứ 4) — ``timestamp`` có lúc lùi (đổi tiến trình trang khi
    điều hướng, khung nhúng), mỗi lần lùi bị kẹp về 0 là cộng thêm độ trễ. Giờ nhận luôn
    tăng và cùng đồng hồ với mốc cảnh; ``timestamp`` vẫn được ghi để chẩn đoán."""

    thu_muc: Path
    khung: list[tuple[str, float]] = field(default_factory=list)
    ts_goc: list[float] = field(default_factory=list)
    moc: list[dict] = field(default_factory=list)
    loi: list[str] = field(default_factory=list)
    kiem: dict = field(default_factory=dict)

    def nhan(self, f: dict) -> None:
        nhan_luc = time.time()
        ts = float(f["timestamp"])
        self.ts_goc.append(ts / 1000.0 if ts > 1e11 else ts)
        ten = f"k{len(self.khung):06d}.jpg"
        (self.thu_muc / ten).write_bytes(f["data"])
        self.khung.append((ten, nhan_luc))

    def chan_doan(self) -> dict:
        """Độ lệch giữa giờ nhận và timestamp Chromium; số lần timestamp lùi."""
        lech = [n - t for (_, n), t in zip(self.khung, self.ts_goc, strict=True)]
        lui = [a - b for a, b in zip(self.ts_goc, self.ts_goc[1:], strict=False) if b < a]
        return {
            "lech_nhan_tru_ts_giay": [round(min(lech), 3), round(max(lech), 3)] if lech else None,
            "so_lan_ts_lui": len(lui),
            "ts_lui_lon_nhat_giay": round(max(lui), 3) if lui else 0.0,
        }


def quay(api: str, web: str, ra: Path, tam: Path | None, giu_khung: bool) -> int:
    from playwright.sync_api import sync_playwright

    kiem_server(api, web)
    ra.mkdir(parents=True, exist_ok=True)
    tam = tam or (ra / "_khung")
    if tam.exists():
        shutil.rmtree(tam)
    tam.mkdir(parents=True)
    bg = BanGhi(thu_muc=tam)
    git = ban_git()
    vang = goi_api(api, "/demo/seed-vang", body={})
    duong1 = chon_phien_vang(vang, "duong", "#1")
    null1 = chon_phien_vang(vang, "null", "#1")
    thieu = chon_phien_vang(vang, "thieu", "")
    nhap = goi_api(
        api,
        "/sessions",
        body={
            "platform": "youtube",
            "title": "Phiên nháp chưa bốc lịch (thử cổng 409)",
            "planned_duration_min": 90,
            "dry_run": True,
        },
    )
    sid_nhap = nhap["session_id"]
    # Đầu ra thật của hai lệnh terminal — chạy NGAY trước khi quay, ghi giờ chạy
    lenh_yt = [sys.executable, "scripts/kiem_tra_youtube.py"]
    luc_yt = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    ma_yt, ra_yt = chay_lenh(lenh_yt, cwd=GOC, timeout=120)
    lenh_pii = [sys.executable, "-m", "pytest", "tests/test_pii_filter.py"]
    lenh_pii += ["-p", "no:cacheprovider"]
    luc_pii = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    ma_pii, ra_pii = chay_lenh(lenh_pii, cwd=GOC, timeout=300)
    bg.kiem["lenh"] = {
        "kiem_tra_youtube": {"ma": ma_yt, "luc": luc_yt},
        "pytest_pii": {"ma": ma_pii, "luc": luc_pii, "dong_cuoi": ra_pii.strip().splitlines()[-1:]},
    }
    trang_thai: dict[str, Any] = {"phien": None}

    with sync_playwright() as pw:
        trinh = pw.chromium.launch(headless=True)
        ctx = trinh.new_context(
            viewport=KHUNG_QUAY,
            device_scale_factor=1,
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
        )
        page = ctx.new_page()
        page.set_default_timeout(30_000)
        page.on("pageerror", lambda e: bg.loi.append(f"pageerror {page.url}: {str(e)[:160]}"))
        # làm nóng: tải trang chủ và font trước khi bấm ghi (không quay đoạn chờ máy nguội)
        mo_trang(page, web + "/", cho_chu="LiveLift", ms=1500)
        page.set_content(the_mo_dau(git))
        cho_on_dinh(page, 800)

        page.screencast.start(on_frame=bg.nhan, size=KHUNG_QUAY, quality=92)
        # con trỏ chuột cho người xem theo kịp cú bấm; chữ mô tả thao tác thu về 1 px
        hanh_dong = page.screencast.show_actions(
            cursor="pointer", font_size=1, duration=450, position="bottom-left"
        )
        t0 = time.time()
        lop_phu: list[Any] = []

        def cham(ms: int) -> None:
            page.wait_for_timeout(int(ms * NHIP_QUAY))

        def bo_lop_phu() -> None:
            while lop_phu:
                lop_phu.pop().__exit__(None, None, None)

        def canh(c: Canh, viec: Callable[[], None], lop: bool = True) -> None:
            bat = time.time()
            bo_lop_phu()
            if c.so is not None and lop:
                lop_phu.append(page.screencast.show_overlay(_lop_phu(c)))
            if c.so is not None:
                page.screencast.show_chapter(
                    f"{c.so}/9 · {c.ten}", description=c.mo_ta, duration=1500
                )
                page.wait_for_timeout(1300)
            try:
                viec()
            except Exception as e:  # noqa: BLE001 — ghi lỗi, quay tiếp các cảnh sau
                bg.loi.append(f"{c.ma}: {type(e).__name__}: {str(e)[:300]}")
                print(f"  LỖI cảnh {c.ma}: {e}")
            con = c.giay - (time.time() - bat)
            if con > 0:
                page.wait_for_timeout(int(con * 1000))
            moc = {"ma": c.ma, "bat_dau": bat - t0, "ket_thuc": time.time() - t0}
            if trang_thai.get("loi_tu") is not None:
                moc["loi_dan_tu"] = trang_thai.pop("loi_tu")
            bg.moc.append(moc)
            print(
                f"  {c.ma:10s} {bat - t0:6.1f} → {time.time() - t0:6.1f} s"
                + (f"  (vượt {-con:.1f} s)" if con < 0 else "")
            )

        def v_mo_dau() -> None:
            page.wait_for_timeout(500)

        def v_mo() -> None:
            mo_trang(page, web + "/", cho_chu="LiveLift", ms=600)
            chip = page.locator("header, nav").get_by_text(re.compile("KHO:")).first
            if chip.count():
                chip.hover()
            cham(3500)

        def v_chuan_bi() -> None:
            phien = wizard_den_buoc3(page, web, cham)
            trang_thai["phien"] = phien
            cham(2500)
            chi_tiet = page.get_by_text("Chi tiết kỹ thuật").first
            if chi_tiet.count():
                chi_tiet.click()
                cham(700)
                chi_tiet.scroll_into_view_if_needed()
            cham(3000)

        def v_cong_chan() -> None:
            mo_trang(page, api + "/docs", cho_chu="LiveLift API", ms=1200)
            khoi = page.locator(
                '.opblock-post:has(.opblock-summary-path[data-path="/sessions/{session_id}/start"])'
            ).first
            khoi.scroll_into_view_if_needed()
            cham(800)
            khoi.locator(".opblock-summary").first.click()
            cham(900)
            khoi.get_by_role("button", name="Try it out").click()
            cham(700)
            o = khoi.locator('input[placeholder="session_id"]').first
            o.click()
            o.press_sequentially(sid_nhap, delay=18)
            cham(600)
            khoi.get_by_role("button", name="Execute").click()
            bang = khoi.locator(".live-responses-table").first
            bang.wait_for(timeout=15_000)
            khoi.get_by_text("Error: Conflict").first.wait_for(timeout=15_000)
            m = re.search(r"\b([1-5]\d\d)\b", bang.inner_text())
            bg.kiem["cong_chan_ma_http"] = m.group(1) if m else None
            khoi.locator(".live-responses-table").first.scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, 160)")

        def v_len_song() -> None:
            phien: PhienChayThu = trang_thai["phien"]
            mo_trang(page, phien.url_buoc3, cho_chu="Bốc thăm lịch BẬT/TẮT", ms=900)
            wizard_buoc4_len_song(page, phien, cham, giu_host=False)
            cham(800)
            bam_bat_dau_phat(page)
            cho_on_dinh(page, 1500)
            bat_bo_thu_mo_phong(page, cham)
            bg.kiem["bo_thu_bat_luc_giay"] = round(time.time() - t0, 1)

        def v_desk() -> None:
            cham(2500)
            # cuộn trang xuống đáy: khung bình luận lên cao nhất có thể, tránh vùng phụ đề
            page.evaluate(
                "window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'smooth'})"
            )
            page.wait_for_function(
                r"""() => [...document.querySelectorAll('ul[aria-label="Danh sách bình luận"] li')]
                         .some(li => /\[SĐT\]/.test(li.innerText))""",
                timeout=40_000,
            )
            cham(1500)
            # đúng thao tác người trợ live: bấm "Tạm dừng cuộn" để đọc một dòng
            dung = page.get_by_role("button", name="Tạm dừng cuộn").first
            if dung.count():
                dung.click()
                cham(600)
            dong = (
                page.locator('ul[aria-label="Danh sách bình luận"] li')
                .filter(has_text=re.compile(r"\[SĐT\]"))
                .first
            )
            dong.evaluate(
                "li => { const h = li.parentElement.parentElement;"
                " h.scrollTo({top: li.offsetTop - 4, behavior: 'smooth'}); }"
            )
            cham(900)
            dong.hover()
            trang_thai["loi_tu"] = time.time() - t0 - 0.3
            bg.kiem["feed_1920x1080"] = page.evaluate(JS_DO_FEED)
            bg.kiem["pii_goc_tren_desk"] = pii_tho_trong(
                page.evaluate("() => document.body.innerText")
            )
            cham(7000)
            radar = page.get_by_text("Radar bình luận").first
            if radar.count():
                radar.hover()
            cham(3000)

        def v_lam_mu() -> None:
            phien: PhienChayThu = trang_thai["phien"]
            page.set_content(the_chia_doi(web, phien.session_id))
            cho_on_dinh(page, 1000)

        def v_ket_qua() -> None:
            phien: PhienChayThu = trang_thai["phien"]
            # gỡ hai khung nhúng trước khi rời trang khung (đóng WebSocket/poll của chúng)
            page.evaluate("document.querySelectorAll('iframe').forEach(f => f.remove())")
            sid = phien.session_id
            mo_trang(page, f"{web}/desk?session={sid}", cho_chu="Kết thúc phiên", ms=1200)
            ket_thuc_phien(page, cham)
            cham(1200)
            page.get_by_text("Xem báo cáo phiên").first.click()
            page.get_by_text("Tổng quan").first.wait_for(timeout=30_000)
            cho_on_dinh(page, 2500)
            for chu in ("Ma trận tín hiệu", "Kết quả thí nghiệm"):
                muc = page.get_by_text(chu, exact=True).first
                if muc.count():
                    muc.evaluate("e => e.scrollIntoView({block: 'start', behavior: 'smooth'})")
                    cham(3200)
            mo_trang(page, f"{web}/ket-qua?env=demo", cho_chu="Kết quả & chiến lược", ms=300)
            try:
                page.get_by_text(re.compile("KTC 95%|CHƯA ĐỦ ĐIỀU KIỆN")).first.wait_for(
                    timeout=25_000
                )
            except Exception:  # noqa: BLE001 — chậm thì vẫn quay tiếp, ghi lại
                bg.loi.append("ket_qua: bản gộp demo chưa hiện kết luận sau 25 s")
            cham(2400)
            for sid_vang in (duong1, null1, thieu):
                mo_trang(page, f"{web}/ket-qua?phien={sid_vang}", cho_chu="PHIÊN DEMO", ms=4200)
            mo_trang(page, f"{web}/ket-qua", cho_chu="Kết quả & chiến lược", ms=3000)
            muc = page.get_by_text("Phiên chạy thử", exact=True).first
            if muc.count():
                muc.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'smooth'})")
            cham(2200)

        def v_tich_hop() -> None:
            phien: PhienChayThu = trang_thai["phien"]
            mo_trang(page, web + "/bat-dau", cho_chu="Buổi live của tôi dùng được gì?", ms=700)
            for chon in ("Của tôi", "YouTube", "Đang phát"):
                page.get_by_role("button", name=re.compile("^" + chon)).first.click()
                cham(650)
            cham(900)
            page.evaluate("window.scrollBy({top: 520, behavior: 'smooth'})")
            cham(2400)
            mo_trang(page, f"{web}/bao-cao/{phien.session_id}", cho_chu="Tổng quan", ms=1200)
            don = page.get_by_text("Nhập đơn từ tệp CSV").first
            if don.count():
                don.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'smooth'})")
            cham(2400)
            if phien.ma_link:
                try:
                    page.goto(
                        f"{api}/r/{phien.ma_link[0]}", wait_until="domcontentloaded", timeout=10_000
                    )
                    bg.kiem["link_do_mo_toi"] = page.url
                except Exception as e:  # noqa: BLE001 — mạng ngoài có thể chậm, quay tiếp
                    bg.kiem["link_do_mo_toi"] = f"lỗi: {e}"
                cham(1800)
            page.set_content(
                the_terminal(
                    "python scripts/kiem_tra_youtube.py",
                    ra_yt,
                    ma_yt,
                    luc_yt,
                    "kiểm khoá YouTube Data API, không in khoá",
                    CANH_THEO_MA["tich_hop"],
                )
            )
            cho_on_dinh(page, 2500)
            page.evaluate("document.getElementById('hop').scrollTo({top: 1e6, behavior: 'smooth'})")

        def v_ung_dung() -> None:
            page.set_content(
                the_terminal(
                    "python -m pytest tests/test_pii_filter.py",
                    ra_pii,
                    ma_pii,
                    luc_pii,
                    "40 ca kiểm bộ lọc dữ liệu cá nhân",
                    CANH_THEO_MA["ung_dung"],
                )
            )
            cho_on_dinh(page, 500)

        def v_chot() -> None:
            page.set_content(the_chot())
            cho_on_dinh(page, 300)

        viec = {
            "mo_dau": v_mo_dau,
            "mo": v_mo,
            "chuan_bi": v_chuan_bi,
            "cong_chan": v_cong_chan,
            "len_song": v_len_song,
            "desk": v_desk,
            "lam_mu": v_lam_mu,
            "ket_qua": v_ket_qua,
            "tich_hop": v_tich_hop,
            "ung_dung": v_ung_dung,
            "chot": v_chot,
        }
        print("Quay:")
        for x in CANH:
            canh(x, viec[x.ma], lop=x.ma != "lam_mu")
        bo_lop_phu()
        hanh_dong.__exit__(None, None, None)
        t_ket = time.time()
        page.wait_for_timeout(300)
        page.screencast.stop()
        trinh.close()

    phien = trang_thai["phien"]
    bg.kiem["chan_doan_khung"] = bg.chan_doan()
    bg.kiem["phien_chay_thu"] = phien.session_id if phien else None
    bg.kiem["phien_nhap_409"] = sid_nhap
    bg.kiem["demo_vang"] = {"duong_1": duong1, "null_1": null1, "chua_du": thieu}
    return dung_video(bg, t0, t_ket, ra, git, giu_khung)


# ------------------------------------------------------------ ffmpeg + phụ đề
def _gio_srt(s: float) -> str:
    ms = max(0, round(s * 1000))
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _tach_cau(chu: str, toi_da: int = 96) -> list[str]:
    """Tách lời dẫn thành câu phụ đề ≤ ``toi_da`` ký tự, cắt ở dấu câu rồi mới ở khoảng trắng."""
    manh = [m.strip() for m in re.split(r"(?<=[.;:?!])\s+|\s+(?=—)", chu) if m.strip()]
    ra: list[str] = []
    for m in manh:
        while len(m) > toi_da:
            phay = m.rfind(", ", 0, toi_da)
            cat = phay + 1 if phay > toi_da * 0.4 else m.rfind(" ", 0, toi_da)
            ra.append(m[:cat].strip())
            m = m[cat + 1 :].strip()
        if ra and len(ra[-1]) + len(m) + 1 <= toi_da * 0.6:
            ra[-1] = f"{ra[-1]} {m}"
        else:
            ra.append(m)
    return ra


def _hai_dong(cau: str, toi_da: int = 52) -> str:
    if len(cau) <= toi_da:
        return cau
    giua = len(cau) // 2
    trai, phai = cau.rfind(" ", 0, giua + 1), cau.find(" ", giua)
    cat = trai if phai < 0 or (trai >= 0 and giua - trai <= phai - giua) else phai
    return cau[:cat] + "\n" + cau[cat + 1 :]


def phu_de(moc: list[dict]) -> list[tuple[float, float, str]]:
    """Mốc phụ đề theo mốc cảnh THẬT của lần quay, lời dẫn chia theo độ dài câu."""
    theo_ma = {c.ma: c for c in CANH}
    cue: list[tuple[float, float, str]] = []
    for m in moc:
        c = theo_ma[m["ma"]]
        if c.ma == "mo_dau":
            cue.append(
                (
                    m["bat_dau"] + 0.4,
                    m["ket_thuc"] - 0.3,
                    "[Bản quay màn hình tự động — chưa có lời dẫn.\n"
                    "Phụ đề là lời dẫn theo kịch bản video 2.]",
                )
            )
            continue
        cau = _tach_cau(c.loi_dan)
        dau = m.get("loi_dan_tu", m["bat_dau"] + (1.4 if c.so else 0.4))
        cuoi = m["ket_thuc"] - 0.25
        tong = sum(len(x) for x in cau)
        t = dau
        for x in cau:
            dai = (cuoi - dau) * len(x) / tong
            cue.append((t, t + dai - 0.08, _hai_dong(x)))
            t += dai
    return cue


def ghi_srt(cue: list[tuple[float, float, str]], duong: Path) -> None:
    khoi = [f"{i}\n{_gio_srt(a)} --> {_gio_srt(b)}\n{t}\n" for i, (a, b, t) in enumerate(cue, 1)]
    duong.write_text("\n".join(khoi), encoding="utf-8")


def _ds(chuoi: str) -> list[str]:
    """Đối số dòng lệnh viết liền một chuỗi (không có khoảng trắng bên trong đối số)."""
    return chuoi.split()


def _ffprobe_giay(duong: Path) -> float:
    lenh = "ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1"
    ma, ra = chay_lenh([*_ds(lenh), str(duong)], timeout=60)
    if ma != 0:
        sys.exit(f"LỖI ffprobe {duong.name}: {ra[-400:]}")
    return float(ra.strip().splitlines()[-1])


def dung_video(bg: BanGhi, t0: float, t_ket: float, ra: Path, git: dict, giu_khung: bool) -> int:
    if not bg.khung:
        sys.exit("LỖI: screencast không trả khung hình nào.")
    if not shutil.which("ffmpeg"):
        sys.exit("LỖI: không thấy ffmpeg trên PATH.")
    # ffconcat: mỗi khung giữ tới khung sau (screencast chỉ gửi khi màn hình đổi)
    khung = [(t, max(ts, t0)) for t, ts in bg.khung if ts <= t_ket + 1]
    dong = ["ffconcat version 1.0"]
    for (ten, ts), (_, ts_sau) in zip(khung, [*khung[1:], ("", t_ket)], strict=True):
        dong += [f"file '{ten}'", f"duration {max(ts_sau - ts, 0.001):.4f}"]
    dong.append(f"file '{khung[-1][0]}'")
    (bg.thu_muc / "khung.ffconcat").write_text("\n".join(dong) + "\n", encoding="utf-8")
    # khung đầu tiên có thể tới trễ vài chục ms sau t0 — bù bằng chính khung đó
    lech_dau = max(0.0, khung[0][1] - t0)
    tong = t_ket - t0
    srt = ra / "demo-tho.srt"
    ghi_srt(phu_de(bg.moc), srt)
    mp4 = ra / "demo-tho.mp4"
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x07080d,format=yuv420p"
    )
    if lech_dau > 0:
        vf = f"tpad=start_duration={lech_dau:.3f}:start_mode=clone," + vf
    lenh = [
        *_ds("ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i khung.ffconcat"),
        *_ds("-f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000"),
        *["-i", str(srt), *_ds("-map 0:v -map 1:a -map 2:s")],
        *["-vf", vf, *_ds("-fps_mode cfr -r 30")],
        *_ds("-c:v libx264 -preset medium -crf 18 -profile:v high -c:a aac -b:a 96k"),
        *_ds("-c:s mov_text -metadata:s:s:0 language=vie"),
        *["-t", f"{tong:.3f}", "-movflags", "+faststart", str(mp4)],
    ]
    print("ffmpeg: ghép MP4 H.264…")
    ma, ket = chay_lenh(lenh, cwd=bg.thu_muc, timeout=1800)
    if ma != 0:
        sys.exit(f"LỖI ffmpeg: {ket[-1500:]}")
    giay = _ffprobe_giay(mp4)
    ban_phu_de = None
    ma_f, bo_loc = chay_lenh(["ffmpeg", "-hide_banner", "-filters"], timeout=60)
    if ma_f == 0 and re.search(r"\bsubtitles\b", bo_loc):
        phong = bg.thu_muc / "phong"
        phong.mkdir(exist_ok=True)
        for p in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"):
            if Path(p).is_file():
                shutil.copy2(p, phong / Path(p).name)
        shutil.copy2(srt, bg.thu_muc / "pd.srt")
        kieu = (
            "FontName=Arial,FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
            "BorderStyle=3,Outline=5,Shadow=0,MarginV=12,Alignment=2"
        )
        ban_phu_de = ra / "demo-tho-phu-de.mp4"
        lenh = [
            *["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp4)],
            "-vf",
            f"subtitles=pd.srt:charenc=UTF-8:fontsdir=phong:force_style='{kieu}'",
            *_ds("-map 0:v -map 0:a -c:v libx264 -preset medium -crf 18 -c:a copy"),
            *["-movflags", "+faststart", str(ban_phu_de)],
        ]
        print("ffmpeg: ghi cứng phụ đề (libass)…")
        ma, ket = chay_lenh(lenh, cwd=bg.thu_muc, timeout=1800)
        if ma != 0:
            bg.loi.append(f"ghi cứng phụ đề hỏng: {ket[-600:]}")
            ban_phu_de = None
    giay_pd = _ffprobe_giay(ban_phu_de) if ban_phu_de else None
    ket_qua = {
        "lenh": f"{LENH} quay --ra {ra}",
        "luc": bay_gio(),
        "git": git,
        "khung_hinh": len(khung),
        "thoi_luong_giay": round(giay, 2),
        "thoi_luong_phu_de_giay": round(giay_pd, 2) if giay_pd else None,
        "tran_giay": TRAN_GIAY_VIDEO,
        "canh": [
            {
                **m,
                "ten": next(c.ten for c in CANH if c.ma == m["ma"]),
                "du_kien_giay": next(c.giay for c in CANH if c.ma == m["ma"]),
            }
            for m in bg.moc
        ],
        "kiem": bg.kiem,
        "loi": bg.loi,
    }
    (ra / "demo-tho.json").write_text(
        json.dumps(ket_qua, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    ghi_readme_video(ra, ket_qua, ban_phu_de is not None)
    if not giu_khung:
        shutil.rmtree(bg.thu_muc, ignore_errors=True)
    print(f"Video: {mp4} — {giay:.1f} s ({len(khung)} khung hình)")
    if ban_phu_de:
        print(f"       {ban_phu_de} — {giay_pd:.1f} s")
    print(f"Phụ đề: {srt}")
    loi = list(bg.loi)
    if giay > 300 or (giay_pd or 0) > 300:
        loi.append(f"video dài {giay:.1f} s > 300 s")
    elif giay > TRAN_GIAY_VIDEO:
        print(f"CẢNH BÁO: {giay:.1f} s > trần tự đặt {TRAN_GIAY_VIDEO:.0f} s (thể lệ: 300 s)")
    for x in loi:
        print(f"LỖI: {x}")
    return 1 if loi else 0


def ghi_readme_video(ra: Path, kq: dict, co_phu_de: bool) -> None:
    def mmss(s: float) -> str:
        return f"{int(s) // 60}:{int(s) % 60:02d}"

    k = kq["kiem"]
    feed = k.get("feed_1920x1080") or {}
    bang = [
        f"| {mmss(m['bat_dau'])}–{mmss(m['ket_thuc'])} | {m['ten']} | "
        f"{next((c.mo_ta for c in CANH if c.ma == m['ma']), '')} |"
        for m in kq["canh"]
    ]
    dong = [
        "# Video demo THÔ — bản quay màn hình tự động (25/09/2026)",
        "",
        "> **Đây KHÔNG phải bản nộp.** Là bản quay màn hình **tự động** (Playwright điều khiển "
        "Chromium, không có người bấm) của **sản phẩm thật** LiveLift chạy tại máy nhóm, trên "
        "dữ liệu **MẪU** (bộ Demo Vàng, `is_demo`) và một phiên **CHẠY THỬ** (`dry_run`) tạo "
        "ngay lúc quay; mọi bình luận là kịch bản **Mô phỏng** tổng hợp (số điện thoại, địa "
        'chỉ, email trong đó là GIẢ). Mọi cảnh đeo nhãn "QUAY TỰ ĐỘNG · SẢN PHẨM THẬT · DỮ '
        'LIỆU MẪU / CHẠY THỬ" trên hình.',
        "",
        "## Tệp",
        "",
        f"- `demo-tho.mp4` — H.264 1920×1080, 30 khung/giây, {kq['thoi_luong_giay']:.1f} giây "
        f"(ffprobe; trần thể lệ 300 giây), tiếng câm, kèm phụ đề mềm tiếng Việt.",
        "- `demo-tho.srt` — phụ đề tiếng Việt theo mốc cảnh THẬT của lần quay; lời dẫn lấy "
        f'nguyên từ cột "Lời thoại" của video 2 trong `{KICH_BAN}`.',
        (
            f"- `demo-tho-phu-de.mp4` — cùng video, phụ đề ghi cứng (libass), "
            f"{kq['thoi_luong_phu_de_giay']:.1f} giây."
            if co_phu_de
            else "- (không có bản ghi cứng phụ đề: ffmpeg máy này thiếu libass)"
        ),
        "- `demo-tho.json` — mốc từng cảnh, số đo, lỗi (nếu có).",
        "",
        "## Đội PHẢI làm trước khi nộp (thể lệ + kịch bản)",
        "",
        "1. **Lồng tiếng** theo lời thoại của kịch bản (phụ đề chính là lời thoại đó, đặt đúng "
        "mốc cảnh) — video này câm.",
        '2. **Ghi hình cả 3 thành viên** (ô webcam góc phải dưới, đổi người theo cột "Ai" '
        "của kịch bản). Bản quay tự động không thay được phần này.",
        "3. Quay thêm cảnh **trang GitHub của kho mã** (cảnh 9 của kịch bản) sau khi đẩy "
        "nhánh nộp — bản này KHÔNG quay GitHub để không lộ README cũ trên nhánh chính.",
        "4. **Kê khai** trong bản kê khai AI: phần quay màn hình được thực hiện TỰ ĐỘNG bằng "
        "`scripts/chup_giao_dien.py quay` (Playwright), kịch bản bấm do tác tử AI viết.",
        '5. Nếu dùng lại hình của bản này: giữ nhãn "QUAY TỰ ĐỘNG"; đoạn nào cắt/ghép thì '
        'ghi "chuyển cảnh" (luật 3 của kịch bản).',
        "",
        "## Trình tự cảnh (mốc thật)",
        "",
        "| Mốc | Phần | Trên màn hình |",
        "|---|---|---|",
        *bang,
        "",
        "## Khác kịch bản ở đâu (và vì sao)",
        "",
        "- Cảnh cổng chặn 409 dùng một **phiên nháp tạo sẵn qua `POST /sessions`** "
        f"(`{k.get('phien_nhap_409', '')[:8]}…`, chạy thử, chưa bốc lịch) trong Swagger `/docs`; "
        f"mã trả về đo được: {k.get('cong_chan_ma_http')}.",
        "- Cảnh làm mù là **trang khung chia đôi do trình quay dựng** (2 khung nhúng /desk và "
        "/host của CÙNG một phiên đang phát) — tương đương chia đôi màn hình; trên hình có ghi.",
        '- Ba trạng thái Demo Vàng mở bằng nút "Kết quả" (`/ket-qua?phien=`) thay vì '
        '"Báo cáo" — thấy ngay kết luận ở đầu trang.',
        "- Hai lệnh terminal (`kiem_tra_youtube.py`, `pytest tests/test_pii_filter.py`) chạy "
        "THẬT ngay trước lúc quay; trình quay hiển thị lại đầu ra, có giờ chạy và mã thoát "
        "trên hình.",
        "",
        "## Số đo của lần quay",
        "",
        f"- Bản build: HEAD `{kq['git']['head']}` (nhánh `{kq['git']['nhanh']}`), tệp chưa "
        f"commit: {', '.join(kq['git']['chua_commit']) or 'không'}.",
        # Kịch bản 07 đã theo thứ tự này (cảnh "Vận hành (3)"); câu cũ "Kịch bản ghi bật ở
        # bước 4" sai sau khi kịch bản được sửa 25/09 — ghi số đo thay vì nói hộ kịch bản.
        f"- Bộ thu Mô phỏng ×10 bật ở giây {k.get('bo_thu_bat_luc_giay')}, trên /desk SAU khi "
        'bấm "Bắt đầu phát sóng" — nguồn Mô phỏng phát ngay khi bật, bật ở bước 4 thì bình '
        "luận bị ghi trước giờ phát (kiểm toán 25/09, mục 3.5).",
        f"- Feed bình luận trên /desk 1920×1080: `clientHeight` {feed.get('client_height')} px, "
        f"thấy trọn {feed.get('dong_thay_tron')} dòng.",
        f"- Chuỗi PII giả còn nguyên trên /desk: {len(k.get('pii_goc_tren_desk') or [])}.",
        f"- Link đo mở tới: {k.get('link_do_mo_toi', '—')}.",
        f"- Lỗi trong lúc quay: {len(kq['loi'])}" + (f" — {kq['loi']}" if kq["loi"] else "") + ".",
        "",
        "## Quay lại",
        "",
        "Bật API (kho bộ nhớ, **kho sạch**) và web production như docstring của "
        "`scripts/chup_giao_dien.py`, rồi:",
        "",
        "```",
        f"{LENH} quay --ra <thư mục ra>",
        "```",
        "",
    ]
    (ra / "README.md").write_text("\n".join(dong), encoding="utf-8")


# ==================================================================== main
def main() -> int:
    configure()
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--api", default=API_MAC_DINH, help=f"địa chỉ API (mặc định {API_MAC_DINH})")
    ap.add_argument("--web", default=WEB_MAC_DINH, help=f"địa chỉ web (mặc định {WEB_MAC_DINH})")
    con = ap.add_subparsers(dest="viec", required=True)
    p = con.add_parser("chup", help="chụp giao diện vào docs/img/v2/")
    p.add_argument("--ra", type=Path, default=RA_ANH)
    p.add_argument(
        "--ban-sao",
        type=Path,
        default=None,
        help="thư mục chép thêm ảnh cho gói Drive (tên YYYY-MM-DD_<commit>_...)",
    )
    p = con.add_parser("ghep", help="dựng Hình 7 từ docs/img/v2/h7-*.png")
    p.add_argument("--anh", type=Path, default=RA_ANH)
    p.add_argument("--ra", type=Path, default=H7)
    p = con.add_parser("quay", help="quay video demo thô + phụ đề")
    p.add_argument("--ra", type=Path, required=True, help="thư mục ra (ngoài kho mã)")
    p.add_argument("--tam", type=Path, default=None, help="thư mục khung hình tạm")
    p.add_argument("--giu-khung", action="store_true", help="không xoá khung hình tạm")
    a = ap.parse_args()
    api, web = a.api.rstrip("/"), a.web.rstrip("/")
    if a.viec == "chup":
        return chup(api, web, a.ra.resolve(), a.ban_sao.resolve() if a.ban_sao else None)
    if a.viec == "ghep":
        return ghep(a.anh.resolve(), a.ra.resolve())
    return quay(api, web, a.ra.resolve(), a.tam.resolve() if a.tam else None, a.giu_khung)


if __name__ == "__main__":
    sys.exit(main())
