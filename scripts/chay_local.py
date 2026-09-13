#!/usr/bin/env python3
"""Khởi động LiveLift trên máy mình bằng MỘT lệnh — và không nói dối về kho.

Vì sao có tệp này (sự cố 13/09/2026, ba lỗi cùng một buổi):

1. **Trang chủ render thành HTML thô, không CSS.** ``/_next/static/css/app/
   layout.css`` trả 404. Gốc rễ: NHIỀU tiến trình ``next dev``/``next build``
   cùng ghi một thư mục ``.next``, thư mục build hỏng (``.next/static/css``
   rỗng), lại còn một tiến trình ``next`` CŨ vẫn giữ cổng 3000 và phục vụ từ
   thư mục ``.next`` đã bị xoá. Sửa tay được, nhưng không có gì chặn tái diễn.
2. **Kho chết mà không ai biết.** PostgreSQL tắt hẳn, không ai nghe cổng 5432,
   nhưng người vận hành vẫn tưởng dữ liệu đang được lưu bền vững.
3. **Cổng bị chiếm im lặng.** Tiến trình cũ không chết, tiến trình mới không
   lên, và thông báo lỗi không nói PID nào đang giữ cổng.

Tệp này làm TRỌN một vòng và **đo** thay vì tin:

  (a) tìm và báo tiến trình đang giữ cổng 3000/8000 (in PID + tên, hỏi trước
      khi dừng, hoặc dùng ``--force``);
  (b) dọn các thư mục build rác ``.next-*`` thừa do các phiên chạy song song
      bỏ lại;
  (c) hỏi kho: PostgreSQL có THẬT SỰ trả lời không — không thì tự chọn
      ``memory + ảnh chụp`` và NÓI RÕ dữ liệu nằm trong RAM;
  (d) bật API rồi đợi ``/health`` xanh;
  (e) bật web rồi đợi trang chủ 200 **và kiểm tra tệp CSS tải được** — đúng
      phép thử mà sự cố (1) đã trượt; hỏng thì tự dọn thư mục build và thử
      lại MỘT lần;
  (f) in bảng tóm tắt: địa chỉ mở, chế độ kho, số phiên đang có.

Chạy (PowerShell — môi trường thật của chủ dự án):

    .venv/Scripts/python scripts/chay_local.py

Mã thoát: 0 = mọi thứ xanh · 1 = không khởi động được · 2 = cổng bị chiếm mà
không được phép dừng · 3 = web lên nhưng CSS hỏng (chính sự cố 13/09).

Thư mục build: mặc định ``web/.next-chay-local`` — CỐ Ý khác ``.next`` để một
``npm run dev`` gõ tay ở terminal khác không giẫm lên thư mục của lệnh này.
Mọi tiến trình dev/build song song PHẢI đặt ``LIVELIFT_DIST_DIR`` riêng (xem
``web/next.config.mjs``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.config import get_settings  # noqa: E402
from livelift.console import configure  # noqa: E402

# --- Hằng số của phép thử CSS ----------------------------------------------
#
# 10 KB là ngưỡng "có thật hay không", không phải ngưỡng thẩm mỹ: bản CSS thật
# của bàn điều khiển đo được ~62 KB (13/09/2026), còn mọi dạng hỏng đã gặp đều
# nhỏ hơn 10 KB — 404 rỗng (0 byte), trang lỗi HTML của Next (~2 KB), hoặc tệp
# CSS cụt do build dở dang. Hai token là bằng chứng CSS ĐÚNG của dự án chứ
# không phải reset của trình duyệt: `--canvas` (nền tối) và `--brand` (màu
# thương hiệu) đều được khai báo trong web/src/app/globals.css.
CSS_TOI_THIEU_BYTE = 10 * 1024
CSS_TOKEN_BAT_BUOC = ("--canvas", "--brand")

DIST_DIR_MAC_DINH = ".next-chay-local"
CONG_API_MAC_DINH = 8000
CONG_WEB_MAC_DINH = 3000

CHO_API_GIAY = 90.0
CHO_WEB_GIAY = 240.0  # `next dev` biên dịch lần đầu rất lâu trên Windows


# ===========================================================================
# Hàm thuần — phần được khoá bằng test nhanh (tests/test_khoi_dong_sach.py)
# ===========================================================================


@dataclass(frozen=True)
class TienTrinh:
    """Một tiến trình đang nghe một cổng TCP."""

    pid: int
    ten: str = "?"

    def __str__(self) -> str:  # pragma: no cover - chỉ để in
        return f"PID {self.pid} ({self.ten})"


def phan_tich_netstat(ket_xuat: str, cong: int) -> list[int]:
    """Rút PID của các tiến trình ĐANG NGHE ``cong`` từ đầu ra ``netstat -ano``.

    Phải phân biệt được cổng 3000 với 30000 và với cổng phía đối tác
    (cột Foreign Address) — nhầm một trong hai là giết nhầm tiến trình.
    """
    pids: list[int] = []
    for dong in ket_xuat.splitlines():
        phan = dong.split()
        # Proto, Local Address, Foreign Address, State, PID
        if len(phan) < 5 or phan[0].upper() not in {"TCP", "TCPV6"}:
            continue
        if phan[3].upper() not in {"LISTENING", "LISTEN"}:
            continue
        if _cong_cua_dia_chi(phan[1]) != cong:
            continue
        try:
            pid = int(phan[4])
        except ValueError:
            continue
        if pid > 0 and pid not in pids:
            pids.append(pid)
    return pids


def _cong_cua_dia_chi(dia_chi: str) -> int | None:
    """``0.0.0.0:3000`` / ``[::]:3000`` / ``127.0.0.1:8000`` -> số cổng."""
    if ":" not in dia_chi:
        return None
    try:
        return int(dia_chi.rsplit(":", 1)[1])
    except ValueError:
        return None


def phan_tich_dong_pid(ket_xuat: str) -> list[TienTrinh]:
    """Đọc các dòng ``<pid>\\t<tên>`` do PowerShell in ra."""
    ra: list[TienTrinh] = []
    for dong in ket_xuat.splitlines():
        if not dong.strip():
            continue
        phan = dong.split("\t")
        try:
            pid = int(phan[0].strip())
        except (ValueError, IndexError):
            continue
        ten = phan[1].strip() if len(phan) > 1 and phan[1].strip() else "?"
        if all(t.pid != pid for t in ra):
            ra.append(TienTrinh(pid=pid, ten=ten))
    return ra


TUOI_COI_LA_RAC_GIAY = 300.0


def chon_thu_muc_rac(
    ten_thu_muc: Iterable[str],
    dang_dung: str,
    tuoi_giay: dict[str, float] | None = None,
    nguong_tuoi_giay: float = TUOI_COI_LA_RAC_GIAY,
) -> list[str]:
    """Thư mục build ``.next-*`` nào là RÁC và xoá được.

    Giữ lại ba loại:

    * ``.next`` — của người gõ ``npm run dev`` bằng tay;
    * thư mục lệnh này sắp dùng;
    * thư mục **vừa được ghi** (mới hơn ``nguong_tuoi_giay``) — nhiều khả năng
      đang có một tiến trình khác dùng nó. Xoá thư mục build của một tiến
      trình đang sống là tái tạo ĐÚNG sự cố 13/09 cho người khác, chỉ đổi vai.

    Xoá: mọi ``.next-<gì đó>`` còn lại — dấu vết của các tiến trình song song
    đã chết.
    """
    tuoi = tuoi_giay or {}
    return sorted(
        ten
        for ten in ten_thu_muc
        if ten.startswith(".next-")
        and ten not in {dang_dung, ".next"}
        and tuoi.get(ten, nguong_tuoi_giay + 1.0) > nguong_tuoi_giay
    )


@dataclass(frozen=True)
class KetQuaKho:
    """Trả lời câu hỏi 'kho nào, và ta BIẾT hay ta ĐOÁN?'."""

    backend: str  # "postgres" | "memory"
    ben_vung: bool
    # "truy-van"  đã chạy SELECT 1, biết chắc kho sống
    # "cong-mo"   cổng mở nhưng không hỏi sâu được (máy thiếu psycopg)
    # "ep-buoc"   người dùng ép bằng --kho, KHÔNG đo gì cả
    # "tat-cong" / "khong-noi-duoc"  kho chết
    muc_do: str
    thong_diep: str


def chon_che_do_kho(
    song: bool,
    muc_do: str,
    chi_tiet: str,
    duong_dan_anh_chup: str,
    chu_ky_giay: float,
) -> KetQuaKho:
    """Chọn kho từ kết quả ĐO được, và viết ra câu nói thật tương ứng.

    Nguyên tắc cốt lõi của dự án: thiếu nguồn thì TUYÊN BỐ thiếu. Nếu Postgres
    không trả lời, lệnh này không được im lặng rơi về RAM — nó phải nói thẳng
    dữ liệu sẽ nằm trong RAM và mất gì khi tiến trình chết.
    """
    if song and muc_do == "truy-van":
        return KetQuaKho(
            backend="postgres",
            ben_vung=True,
            muc_do=muc_do,
            thong_diep=(
                f"PostgreSQL trả lời truy vấn thật ({chi_tiet}) — dùng kho BỀN VỮNG. "
                "Khởi động lại không mất gì."
            ),
        )
    if song and muc_do in {"cong-mo", "ep-buoc"}:
        vi_sao = (
            f"Cổng PostgreSQL đang mở nhưng CHƯA kiểm được bằng truy vấn ({chi_tiet})."
            if muc_do == "cong-mo"
            else f"Chạy kho postgres vì BỊ ÉP ({chi_tiet}) — lệnh này KHÔNG đo gì cả."
        )
        return KetQuaKho(
            backend="postgres",
            ben_vung=True,
            muc_do=muc_do,
            thong_diep=(
                f"{vi_sao} Dùng kho postgres theo cấu hình — hãy xem lại /health sau khi API lên."
            ),
        )
    if muc_do == "ep-buoc":
        return KetQuaKho(
            backend="memory",
            ben_vung=False,
            muc_do=muc_do,
            thong_diep=(
                f"Chạy kho memory + ảnh chụp vì BỊ ÉP ({chi_tiet}). DỮ LIỆU NẰM TRONG "
                f"RAM, chỉ được chụp lại mỗi {chu_ky_giay:.0f} giây vào "
                f"{duong_dan_anh_chup}."
            ),
        )
    return KetQuaKho(
        backend="memory",
        ben_vung=False,
        muc_do=muc_do,
        thong_diep=(
            f"KHÔNG có PostgreSQL ({chi_tiet}). Tự chọn kho memory + ảnh chụp: "
            f"DỮ LIỆU NẰM TRONG RAM, chỉ được chụp lại mỗi {chu_ky_giay:.0f} giây "
            f"vào {duong_dan_anh_chup}. Tiến trình chết đột ngột thì mất tối đa "
            f"{chu_ky_giay:.0f} giây sự kiện cuối. ĐỦ cho demo và thi đấu; phiên "
            "live thật hãy bật Postgres trước."
        ),
    )


_LINK_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r"""(\w[\w-]*)\s*=\s*("([^"]*)"|'([^']*)')""")


def tim_link_css(html: str) -> list[str]:
    """Mọi ``href`` của thẻ ``<link rel="stylesheet">`` trong HTML.

    Thứ tự thuộc tính của Next thay đổi giữa dev và bản build, nên không được
    khớp bằng một chuỗi cứng. ``rel="preload" as="style"`` KHÔNG tính: nó chỉ
    là gợi ý tải trước, trang vẫn trắng nếu thiếu thẻ stylesheet thật.
    """
    ra: list[str] = []
    for the in _LINK_RE.findall(html):
        thuoc_tinh = {
            m.group(1).lower(): (m.group(3) if m.group(3) is not None else m.group(4))
            for m in _ATTR_RE.finditer(the)
        }
        rel = (thuoc_tinh.get("rel") or "").lower().split()
        href = thuoc_tinh.get("href")
        if "stylesheet" in rel and href and href not in ra:
            ra.append(href)
    return ra


@dataclass
class KetQuaCss:
    """Phán quyết của phép thử CSS — rỗng ``loi`` nghĩa là đạt."""

    dat: bool
    loi: list[str] = field(default_factory=list)
    href: str | None = None
    so_byte: int = 0


def kiem_tra_noi_dung_css(
    noi_dung: bytes,
    ma_http: int = 200,
    kieu_noi_dung: str = "",
) -> list[str]:
    """Liệt kê MỌI lý do tệp CSS này không dùng được. Rỗng = đạt.

    Đây là hạt nhân của cổng chống tái diễn sự cố 13/09: ngày hôm đó thẻ
    ``<link>`` vẫn nằm đúng chỗ trong HTML, chỉ có tệp phía sau nó trả 404 —
    nên kiểm "có thẻ link" là chưa đủ, phải TẢI tệp về và cân.
    """
    loi: list[str] = []
    if ma_http != 200:
        loi.append(f"tệp CSS trả HTTP {ma_http} (mong đợi 200) — đúng dạng sự cố 13/09")
    if kieu_noi_dung and "css" not in kieu_noi_dung.lower():
        loi.append(f"Content-Type là {kieu_noi_dung!r}, không phải text/css")
    dau = noi_dung[:200].lstrip().lower()
    if dau.startswith((b"<!doctype", b"<html")):
        loi.append("nội dung trả về là HTML (trang lỗi), không phải CSS")
    if len(noi_dung) < CSS_TOI_THIEU_BYTE:
        loi.append(
            f"tệp CSS chỉ {len(noi_dung)} byte, dưới ngưỡng {CSS_TOI_THIEU_BYTE} byte "
            "— bản dựng đầy đủ của bàn điều khiển lớn hơn nhiều"
        )
    van_ban = noi_dung.decode("utf-8", errors="replace")
    thieu = [t for t in CSS_TOKEN_BAT_BUOC if t not in van_ban]
    if thieu:
        loi.append(f"thiếu token thiết kế {', '.join(thieu)} — đây không phải CSS của LiveLift")
    return loi


def tach_host_cong(database_url: str) -> tuple[str, int]:
    """``postgresql://u:p@127.0.0.1:5432/db`` -> ``("127.0.0.1", 5432)``."""
    phan = urllib.parse.urlsplit(database_url)
    return (phan.hostname or "127.0.0.1", phan.port or 5432)


# ===========================================================================
# Đo thật — socket, tiến trình, HTTP
# ===========================================================================


def cong_dang_mo(host: str, cong: int, timeout: float = 1.0) -> bool:
    """Có ai đang nghe ``host:cong`` không? (chỉ bắt tay TCP, không gửi gì)"""
    try:
        with socket.create_connection((host, cong), timeout=timeout):
            return True
    except OSError:
        return False


def _chay(cmd: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - lệnh cố định trong tệp này
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def tien_trinh_giu_cong(cong: int) -> list[TienTrinh]:
    """PID + tên của mọi tiến trình đang NGHE cổng này."""
    if os.name == "nt":
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps:
            lenh = (
                f"Get-NetTCPConnection -State Listen -LocalPort {cong} "
                "-ErrorAction SilentlyContinue | ForEach-Object { "
                "$p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
                '"$($_.OwningProcess)`t$($p.ProcessName)" }'
            )
            ra = _chay([ps, "-NoProfile", "-NonInteractive", "-Command", lenh], timeout=45)
            if ra.returncode == 0 and ra.stdout.strip():
                return phan_tich_dong_pid(ra.stdout)
        netstat = _chay(["netstat", "-ano", "-p", "TCP"], timeout=45)
        return [
            TienTrinh(pid=p, ten=_ten_tien_trinh(p))
            for p in phan_tich_netstat(netstat.stdout, cong)
        ]
    lsof = shutil.which("lsof")
    if lsof:
        ra = _chay([lsof, "-nP", f"-iTCP:{cong}", "-sTCP:LISTEN", "-t"], timeout=30)
        pids = [int(d) for d in ra.stdout.split() if d.strip().isdigit()]
        return [TienTrinh(pid=p, ten=_ten_tien_trinh(p)) for p in dict.fromkeys(pids)]
    return []


def _ten_tien_trinh(pid: int) -> str:
    if os.name == "nt":
        ra = _chay(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], timeout=30)
        dong = ra.stdout.strip().splitlines()
        if dong and dong[0].startswith('"'):
            return dong[0].split('","')[0].strip('"')
        return "?"
    ra = _chay(["ps", "-p", str(pid), "-o", "comm="], timeout=15)
    return ra.stdout.strip() or "?"


def dung_tien_trinh(tt: TienTrinh) -> bool:
    """Dừng một tiến trình (kể cả cây con của nó trên Windows)."""
    if os.name == "nt":
        ra = _chay(["taskkill", "/PID", str(tt.pid), "/T", "/F"], timeout=45)
        return ra.returncode == 0
    try:
        os.kill(tt.pid, 15)
        time.sleep(1.5)
        os.kill(tt.pid, 9)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return True


def _http_get(url: str, timeout: float = 10.0) -> tuple[int, bytes, str]:
    req = urllib.request.Request(  # noqa: S310 - luôn là http://127.0.0.1 do tệp này dựng
        url, headers={"User-Agent": "livelift-chay-local"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("Content-Type", "")


def doi_http_200(url: str, han_giay: float, nhip: float = 0.5) -> tuple[bool, str]:
    """Đợi tới khi ``url`` trả 200, hoặc hết hạn. Trả (đạt, lý do cuối)."""
    het = time.monotonic() + han_giay
    ly_do = "chưa thử lần nào"
    while time.monotonic() < het:
        try:
            ma, _, _ = _http_get(url, timeout=10.0)
            if ma == 200:
                return True, "200"
            ly_do = f"HTTP {ma}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            ly_do = f"{type(exc).__name__}: {exc}"
        time.sleep(nhip)
    return False, ly_do


def kiem_tra_css_cua_trang(goc: str, timeout: float = 30.0) -> KetQuaCss:
    """Tải trang chủ, tìm thẻ stylesheet, TẢI tệp CSS về và cân nó."""
    try:
        ma, than, _ = _http_get(goc, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return KetQuaCss(dat=False, loi=[f"không mở được {goc}: {exc}"])
    if ma != 200:
        return KetQuaCss(dat=False, loi=[f"trang chủ trả HTTP {ma}, mong đợi 200"])
    html = than.decode("utf-8", errors="replace")
    hrefs = tim_link_css(html)
    if not hrefs:
        return KetQuaCss(
            dat=False,
            loi=['trang chủ KHÔNG có thẻ <link rel="stylesheet"> nào — trang sẽ hiện HTML thô'],
        )
    href = hrefs[0]
    url_css = urllib.parse.urljoin(goc, href)
    try:
        ma_css, noi_dung, kieu = _http_get(url_css, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return KetQuaCss(dat=False, loi=[f"không tải được {url_css}: {exc}"], href=href)
    loi = kiem_tra_noi_dung_css(noi_dung, ma_http=ma_css, kieu_noi_dung=kieu)
    return KetQuaCss(dat=not loi, loi=loi, href=href, so_byte=len(noi_dung))


def kiem_tra_postgres(database_url: str) -> tuple[bool, str, str]:
    """(sống, mức độ, chi tiết) — ĐO chứ không đoán.

    Ba mức, nói thẳng ta biết tới đâu: ``truy-van`` (đã chạy ``SELECT 1``),
    ``cong-mo`` (cổng mở nhưng không có psycopg để hỏi sâu hơn), ``tat-cong``
    (không ai nghe cổng).
    """
    host, cong = tach_host_cong(database_url)
    if not cong_dang_mo(host, cong, timeout=1.5):
        return False, "tat-cong", f"không ai nghe {host}:{cong}"
    try:
        import psycopg
    except ImportError:
        return True, "cong-mo", f"{host}:{cong} mở, nhưng máy này chưa cài psycopg"
    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as exc:  # mọi lỗi đều có nghĩa là kho KHÔNG dùng được
        loai = type(exc).__name__
        return False, "khong-noi-duoc", f"{host}:{cong} mở nhưng truy vấn hỏng ({loai})"
    return True, "truy-van", f"{host}:{cong}"


# ===========================================================================
# In ấn
# ===========================================================================


def _tieu_de(chu: str) -> None:
    print()
    print(f"== {chu} ==")


def _duoi_log(duong_dan: Path, so_dong: int = 25) -> str:
    try:
        dong = duong_dan.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "(không đọc được nhật ký)"
    return "\n".join(f"      | {d}" for d in dong[-so_dong:]) or "      | (nhật ký rỗng)"


def _hoi_dong_y(cau_hoi: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        return input(f"{cau_hoi} [c/K] ").strip().lower() in {"c", "co", "có", "y", "yes"}
    except (EOFError, KeyboardInterrupt):
        return False


# ===========================================================================
# Các bước
# ===========================================================================


def buoc_don_cong(cong: int, nhan: str, force: bool) -> bool:
    """(a) Báo cáo và (nếu được phép) dừng tiến trình đang giữ cổng."""
    giu = tien_trinh_giu_cong(cong)
    if not giu:
        print(f"  ✓ Cổng {cong} ({nhan}) đang trống")
        return True
    for tt in giu:
        print(f"  ! Cổng {cong} ({nhan}) đang bị giữ bởi PID {tt.pid} — {tt.ten}")
    print("    Đây chính là cái bẫy ngày 13/09: một tiến trình 'next' cũ vẫn giữ cổng")
    print("    3000 và phục vụ từ thư mục build ĐÃ BỊ XOÁ, nên trang hiện HTML thô.")
    if not force and not _hoi_dong_y(f"    Dừng {len(giu)} tiến trình trên?"):
        print("    → Không dừng. Chạy lại với --force, hoặc tự dừng rồi chạy lại.")
        return False
    ok = True
    for tt in giu:
        if dung_tien_trinh(tt):
            print(f"    ✓ Đã dừng PID {tt.pid}")
        else:
            print(f"    ✗ KHÔNG dừng được PID {tt.pid} (thiếu quyền?)")
            ok = False
    time.sleep(1.0)
    con = tien_trinh_giu_cong(cong)
    if con:
        print(f"    ✗ Cổng {cong} vẫn bị giữ: {', '.join(str(t) for t in con)}")
        return False
    return ok


def buoc_don_rac(dist_dir: str, xoa_ca_dist: bool) -> list[str]:
    """(b) Xoá các thư mục build ``.next-*`` thừa (bỏ qua thư mục vừa được ghi)."""
    if not WEB_DIR.is_dir():
        return []
    bay_gio = time.time()
    ten = [p.name for p in WEB_DIR.iterdir() if p.is_dir()]
    tuoi = {}
    for p in WEB_DIR.iterdir():
        if p.is_dir():
            try:
                tuoi[p.name] = bay_gio - p.stat().st_mtime
            except OSError:
                tuoi[p.name] = TUOI_COI_LA_RAC_GIAY + 1.0
    rac = chon_thu_muc_rac(ten, dang_dung=dist_dir, tuoi_giay=tuoi)
    giu_vi_moi = [
        t
        for t in ten
        if t.startswith(".next-")
        and t not in {dist_dir, ".next", *rac}
        and tuoi.get(t, 0.0) <= TUOI_COI_LA_RAC_GIAY
    ]
    for t in giu_vi_moi:
        print(f"  · Giữ web/{t} — vừa được ghi, có thể đang có tiến trình khác dùng")
    if xoa_ca_dist and dist_dir in ten:
        rac.append(dist_dir)
    for r in rac:
        shutil.rmtree(WEB_DIR / r, ignore_errors=True)
        print(f"  ✓ Đã xoá thư mục build thừa: web/{r}")
    if not rac:
        print("  ✓ Không có thư mục build rác nào")
    return rac


def _spawn(cmd: list[str], cwd: Path, env: dict[str, str], log: Path) -> subprocess.Popen:
    log.parent.mkdir(parents=True, exist_ok=True)
    handle = log.open("w", encoding="utf-8")
    return subprocess.Popen(  # noqa: S603 - lệnh do chính tệp này dựng
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )


def _lenh_next(web_dir: Path) -> list[str] | None:
    """Gọi thẳng ``node next`` — không qua npx: ít biến số, không cần mạng."""
    binary = web_dir / "node_modules" / "next" / "dist" / "bin" / "next"
    node = shutil.which("node")
    if binary.is_file() and node:
        return [node, str(binary)]
    npx = shutil.which("npx")
    return [npx, "next"] if npx else None


def _dung_popen(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        _chay(["taskkill", "/PID", str(proc.pid), "/T", "/F"], timeout=45)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:  # pragma: no cover - đường hiếm
        proc.kill()


# ===========================================================================
# main
# ===========================================================================


def main(argv: list[str] | None = None) -> int:
    configure()
    parser = argparse.ArgumentParser(
        description="Khởi động sạch LiveLift (API + web) bằng một lệnh",
    )
    parser.add_argument("--cong-api", type=int, default=CONG_API_MAC_DINH)
    parser.add_argument("--cong-web", type=int, default=CONG_WEB_MAC_DINH)
    parser.add_argument(
        "--force", action="store_true", help="dừng tiến trình giữ cổng mà không hỏi"
    )
    parser.add_argument(
        "--sach", action="store_true", help="xoá cả thư mục build đang dùng trước khi chạy"
    )
    parser.add_argument(
        "--kho",
        choices=["tu-dong", "memory", "postgres"],
        default="tu-dong",
        help="ép chế độ kho; mặc định tự đo Postgres rồi chọn",
    )
    parser.add_argument("--bo-qua-web", action="store_true", help="chỉ bật API")
    ket_thuc = parser.add_mutually_exclusive_group()
    ket_thuc.add_argument(
        "--tach",
        action="store_true",
        help="kiểm tra xong thì thoát, để API và web chạy tiếp",
    )
    ket_thuc.add_argument(
        "--thu-roi-thoat",
        action="store_true",
        help="chạy trọn vòng kiểm tra rồi TỰ TẮT cả hai tiến trình và thoát (CI / kiểm nhanh)",
    )
    parser.add_argument("--dist-dir", default=DIST_DIR_MAC_DINH)
    args = parser.parse_args(argv)

    settings = get_settings()
    thu_muc_log = Path(tempfile.gettempdir()) / "livelift-chay-local"
    log_api = thu_muc_log / "api.log"
    log_web = thu_muc_log / "web.log"
    api: subprocess.Popen | None = None
    web: subprocess.Popen | None = None
    giu_lai = False  # chỉ True ở đúng một đường: --tach và mọi thứ đã xanh

    print("== LiveLift — khởi động sạch ==")
    print(f"   Kho mã:    {REPO_ROOT}")
    print(f"   Nhật ký:   {thu_muc_log}")

    try:
        # (a) cổng ------------------------------------------------------
        _tieu_de("(a) Cổng đang bị ai giữ?")
        can = [(args.cong_api, "API")]
        if not args.bo_qua_web:
            can.append((args.cong_web, "web"))
        for cong, nhan in can:
            if not buoc_don_cong(cong, nhan, args.force):
                return 2

        # (b) rác build --------------------------------------------------
        _tieu_de("(b) Thư mục build rác")
        buoc_don_rac(args.dist_dir, xoa_ca_dist=args.sach)

        # (c) kho --------------------------------------------------------
        _tieu_de("(c) Kho dữ liệu — đo, không đoán")
        if args.kho == "tu-dong":
            song, muc_do, chi_tiet = kiem_tra_postgres(settings.database_url)
        else:
            song = args.kho == "postgres"
            muc_do = "ep-buoc"
            chi_tiet = f"do người dùng ép bằng --kho {args.kho}"
        kho = chon_che_do_kho(
            song,
            muc_do,
            chi_tiet,
            settings.store_snapshot_path,
            settings.store_snapshot_interval_s,
        )
        dau = "✓" if kho.ben_vung else "!"
        print(f"  {dau} {kho.thong_diep}")

        # (d) API --------------------------------------------------------
        _tieu_de("(d) API")
        env_api = {**os.environ, "STORE_BACKEND": kho.backend}
        if kho.backend == "postgres":
            env_api["DATABASE_URL"] = settings.database_url
        api = _spawn(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "livelift.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.cong_api),
                "--log-level",
                "info",
            ],
            REPO_ROOT,
            env_api,
            log_api,
        )
        goc_api = f"http://127.0.0.1:{args.cong_api}"
        dat, ly_do = doi_http_200(f"{goc_api}/health", CHO_API_GIAY)
        if not dat:
            print(f"  ✗ /health không xanh sau {CHO_API_GIAY:.0f}s ({ly_do})")
            print(_duoi_log(log_api))
            return 1
        _, than, _ = _http_get(f"{goc_api}/health", timeout=10.0)
        health = json.loads(than.decode("utf-8"))
        print(
            f"  ✓ /health xanh — storage_mode={health.get('storage_mode')} "
            f"durable={health.get('durable')}"
        )
        if health.get("storage_mode", "").startswith("memory"):
            print("    NHẮC LẠI: dữ liệu nằm trong RAM. Khởi động lại tiến trình này là")
            print("    mất mọi thứ chưa kịp vào ảnh chụp.")

        # (e) web + CỔNG CSS ---------------------------------------------
        css = KetQuaCss(dat=True, loi=[])
        goc_web = f"http://127.0.0.1:{args.cong_web}"
        if not args.bo_qua_web:
            _tieu_de("(e) Web + phép thử CSS (sự cố 13/09)")
            lenh_next = _lenh_next(WEB_DIR)
            if lenh_next is None:
                print("  ✗ Không tìm thấy Next (thiếu node hoặc chưa 'npm install' trong web/)")
                return 1
            for lan in (1, 2):
                env_web = {
                    **os.environ,
                    "LIVELIFT_DIST_DIR": args.dist_dir,
                    "NEXT_PUBLIC_API_URL": goc_api,
                }
                web = _spawn(
                    [*lenh_next, "dev", "-p", str(args.cong_web)], WEB_DIR, env_web, log_web
                )
                dat, ly_do = doi_http_200(goc_web, CHO_WEB_GIAY, nhip=1.0)
                if not dat:
                    print(f"  ✗ Trang chủ không trả 200 sau {CHO_WEB_GIAY:.0f}s ({ly_do})")
                    print(_duoi_log(log_web))
                    return 1
                print(f"  ✓ Trang chủ trả 200 (thư mục build web/{args.dist_dir})")
                css = kiem_tra_css_cua_trang(goc_web)
                if css.dat:
                    print(
                        f"  ✓ CSS tải được: {css.href} — {css.so_byte:,} byte, "
                        f"có {', '.join(CSS_TOKEN_BAT_BUOC)}"
                    )
                    break
                for loi in css.loi:
                    print(f"  ✗ CSS HỎNG: {loi}")
                if lan == 1:
                    print("    → Dọn sạch thư mục build rồi dựng lại MỘT lần...")
                    _dung_popen(web)
                    web = None
                    shutil.rmtree(WEB_DIR / args.dist_dir, ignore_errors=True)
            if not css.dat:
                print("    Vẫn hỏng sau khi dựng lại sạch. Xem nhật ký:")
                print(_duoi_log(log_web))
                return 3

        # (f) tóm tắt ----------------------------------------------------
        dem = health.get("mode_counts") or {}
        tong = sum(v for v in dem.values() if isinstance(v, int))
        _tieu_de("(f) Tóm tắt")
        rong = 62
        print("  " + "-" * rong)
        print(f"  {'Bàn điều khiển (web)':<26}{goc_web if not args.bo_qua_web else '(tắt)'}")
        print(f"  {'API':<26}{goc_api}")
        print(f"  {'Health':<26}{goc_api}/health")
        print(
            f"  {'Chế độ kho':<26}{health.get('storage_mode')} "
            f"(bền vững: {'CÓ' if health.get('durable') else 'KHÔNG'})"
        )
        print(
            f"  {'Số phiên đang có':<26}{tong}  (thật {dem.get('real', 0)} · "
            f"demo {dem.get('demo', 0)})"
        )
        if not args.bo_qua_web:
            print(f"  {'CSS':<26}{css.so_byte:,} byte — ĐẠT")
        print(f"  {'Nhật ký':<26}{thu_muc_log}")
        print("  " + "-" * rong)

        if args.thu_roi_thoat:
            print()
            print("  Mọi phép thử ĐẠT. Đang tắt cả hai tiến trình (--thu-roi-thoat).")
            return 0

        if args.tach:
            pid_web = f" và {web.pid}" if web is not None else ""
            print()
            print("  Đã bật xong và để chạy tiếp (--tach). Dừng bằng:")
            print(f"    taskkill /PID {api.pid} /T /F{pid_web}")
            giu_lai = True
            return 0

        print()
        print("  Đang chạy. Nhấn Ctrl+C để dừng CẢ HAI tiến trình gọn gàng.")
        try:
            while True:
                if api.poll() is not None:
                    print("  ✗ Tiến trình API đã chết:")
                    print(_duoi_log(log_api))
                    return 1
                if web is not None and web.poll() is not None:
                    print("  ✗ Tiến trình web đã chết:")
                    print(_duoi_log(log_web))
                    return 1
                time.sleep(1.0)
        except KeyboardInterrupt:
            print()
            print("  Đang dừng...")
            return 0
    finally:
        # Mặc định KHÔNG để lại tiến trình mồ côi: một tiến trình 'next' mồ côi
        # giữ cổng 3000 chính là nửa sau của sự cố 13/09.
        if not giu_lai:
            _dung_popen(web)
            _dung_popen(api)


if __name__ == "__main__":
    raise SystemExit(main())
