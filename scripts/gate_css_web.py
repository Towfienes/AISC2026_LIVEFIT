#!/usr/bin/env python3
"""CỔNG: trang chủ phải có CSS thật — dựng BẢN BUILD THẬT rồi đo.

Sự cố 13/09/2026: chủ dự án mở sản phẩm lên và thấy trang chủ hiện **HTML thô
không có CSS** — ``/_next/static/css/app/layout.css`` trả 404. Toàn bộ 894 test
nhanh, 13 gate chậm, ``tsc --noEmit`` và ``ruff`` đều XANH trong lúc đó, vì
không có cái nào mở trình duyệt lên xem trang có mặc quần áo hay không.

Cổng này lấp đúng khoảng trống ấy, và cố ý làm theo cách đắt nhất — tốn ~1-3
phút — vì mọi cách rẻ hơn đều đã không bắt được lỗi:

1. ``next build`` THẬT, vào một thư mục build riêng (``LIVELIFT_DIST_DIR``) để
   không giẫm lên ``.next`` của máy chủ dev đang chạy — chính việc dùng chung
   thư mục là nguyên nhân gốc;
2. ``next start`` phục vụ bản build đó trên một cổng rảnh;
3. ``GET /`` phải trả **200**;
4. HTML phải có thẻ ``<link rel="stylesheet">`` (không tính ``rel=preload``);
5. **TẢI tệp CSS đó về**: phải 200, phải > 10 KB, và phải chứa token thiết kế
   ``--canvas`` và ``--brand``. Bước 5 mới là bước bắt được sự cố — hôm ấy thẻ
   ``<link>`` vẫn ở đúng chỗ, chỉ có tệp phía sau nó biến mất.

Chạy tay trước khi demo cho giám khảo:

    .venv/Scripts/python scripts/gate_css_web.py

Chạy trong bộ test (cùng một mã, có đánh dấu ``slow``):

    .venv/Scripts/python -m pytest tests/test_web_css_gate.py -q -m slow

Mã thoát: 0 = trang chủ có CSS thật · 1 = hỏng (in rõ hỏng ở bước nào).
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
sys.path.insert(0, str(REPO_ROOT / "src"))

# scripts/ không phải package — nạp phần dùng chung theo đường dẫn. Cố ý DÙNG
# LẠI đúng các hàm mà lệnh khởi động hằng ngày dùng, để cổng và lệnh chạy tay
# không bao giờ đo hai thứ khác nhau.
_spec = importlib.util.spec_from_file_location(
    "livelift_chay_local", Path(__file__).resolve().parent / "chay_local.py"
)
assert _spec is not None
assert _spec.loader is not None
chay_local = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = chay_local
_spec.loader.exec_module(chay_local)

from livelift.console import configure  # noqa: E402

DIST_DIR_GATE = ".next-gate-css"
CHO_START_GIAY = 120.0
BUILD_TIMEOUT_GIAY = 900.0


@dataclass
class KetQuaGate:
    """Phán quyết đầy đủ của cổng — đủ để in ra hoặc assert trong pytest."""

    dat: bool
    buoc: str  # bước hỏng đầu tiên, "" nếu đạt
    loi: list[str] = field(default_factory=list)
    href_css: str | None = None
    so_byte_css: int = 0
    giay_build: float = 0.0
    duoi_log: str = ""

    def bao_cao(self) -> str:
        if self.dat:
            return (
                f"ĐẠT — trang chủ 200, {self.href_css} tải được "
                f"({self.so_byte_css:,} byte, có {', '.join(chay_local.CSS_TOKEN_BAT_BUOC)})"
            )
        dong = [f"HỎNG ở bước: {self.buoc}", *(f"  - {x}" for x in self.loi)]
        if self.duoi_log:
            dong.append(self.duoi_log)
        return "\n".join(dong)


def cong_ranh() -> int:
    """Xin hệ điều hành một cổng TCP không ai dùng."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _lenh_next() -> list[str] | None:
    return chay_local._lenh_next(WEB_DIR)


def _moi_truong(dist_dir: str) -> dict[str, str]:
    return {
        **os.environ,
        # Thư mục build RIÊNG: cổng này không bao giờ được đụng vào `.next`
        # của máy chủ dev đang phục vụ cổng 3000 — dùng chung thư mục chính
        # là nguyên nhân gốc của sự cố 13/09.
        "LIVELIFT_DIST_DIR": dist_dir,
        "NEXT_TELEMETRY_DISABLED": "1",
        # Bản build phải độc lập với máy chủ API: cổng này đo CSS, không đo
        # dữ liệu. Thiếu dòng này thì cổng đỏ mỗi khi API tắt — một cổng hay
        # báo động giả là một cổng sẽ bị tắt.
        "NEXT_PUBLIC_MOCK": "1",
    }


def _thu_muc_log() -> Path:
    # Nhật ký nằm NGOÀI kho mã: không có tệp lạ nào rơi vào web/ để rồi lọt
    # qua .gitignore (vốn chỉ bỏ qua THƯ MỤC `.next-*/`).
    duong_dan = Path(tempfile.gettempdir()) / "livelift-gate-css"
    duong_dan.mkdir(parents=True, exist_ok=True)
    return duong_dan


def dung_ban_build(dist_dir: str = DIST_DIR_GATE) -> tuple[bool, list[str], float, str]:
    """``next build`` thật vào ``web/<dist_dir>``. Trả (đạt, lỗi, giây, đuôi log)."""
    lenh_next = _lenh_next()
    if lenh_next is None:
        return False, ["không tìm thấy node/npx"], 0.0, ""
    shutil.rmtree(WEB_DIR / dist_dir, ignore_errors=True)
    t0 = time.monotonic()
    try:
        build = subprocess.run(  # noqa: S603 - lệnh do chính tệp này dựng
            [*lenh_next, "build"],
            cwd=str(WEB_DIR),
            env=_moi_truong(dist_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=BUILD_TIMEOUT_GIAY,
            check=False,
        )
    except subprocess.TimeoutExpired:
        giay = time.monotonic() - t0
        return False, [f"'next build' quá {BUILD_TIMEOUT_GIAY:.0f}s vẫn chưa xong"], giay, ""
    giay = time.monotonic() - t0
    if build.returncode != 0:
        duoi = "\n".join(f"      | {d}" for d in (build.stdout + build.stderr).splitlines()[-30:])
        return False, [f"'next build' thoát mã {build.returncode}"], giay, duoi
    return True, [], giay, ""


@contextlib.contextmanager
def may_chu_ban_build(dist_dir: str = DIST_DIR_GATE, cong: int | None = None):
    """Phục vụ bản build SẴN CÓ bằng ``next start``; trả ``(gốc URL, nhật ký)``.

    Tách riêng khỏi :func:`dung_ban_build` để test kiểm chứng cổng có thể dựng
    MỘT lần rồi phục vụ HAI lần — lần hai sau khi đã cố tình xoá tệp CSS khỏi
    thư mục build, để chứng minh cổng thật sự có răng.
    """
    lenh_next = _lenh_next()
    if lenh_next is None:  # pragma: no cover - đã chặn ở chay_gate
        raise RuntimeError("không tìm thấy node/npx")
    cong_dung = cong or cong_ranh()
    log = _thu_muc_log() / f"{dist_dir}-start.log"
    handle = log.open("w", encoding="utf-8")
    server = subprocess.Popen(  # noqa: S603 - lệnh do chính tệp này dựng
        [*lenh_next, "start", "-p", str(cong_dung)],
        cwd=str(WEB_DIR),
        env=_moi_truong(dist_dir),
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    try:
        yield f"http://127.0.0.1:{cong_dung}", log
    finally:
        chay_local._dung_popen(server)
        handle.close()


def don_thu_muc(dist_dir: str = DIST_DIR_GATE) -> None:
    """Xoá thư mục build của cổng và nhật ký của nó."""
    shutil.rmtree(WEB_DIR / dist_dir, ignore_errors=True)
    for log in _thu_muc_log().glob(f"{dist_dir}*.log"):
        with contextlib.suppress(OSError):
            log.unlink()


def chay_gate(
    dist_dir: str = DIST_DIR_GATE,
    cong: int | None = None,
    giu_thu_muc: bool = False,
) -> KetQuaGate:
    """Dựng bản build thật rồi đo trang chủ. Không đụng tới ``.next``."""
    if not (WEB_DIR / "node_modules" / "next").is_dir():
        return KetQuaGate(
            dat=False,
            buoc="chuẩn bị",
            loi=["web/node_modules/next không có — chạy 'npm install' trong web/ trước"],
        )
    if _lenh_next() is None:
        return KetQuaGate(dat=False, buoc="chuẩn bị", loi=["không tìm thấy node/npx"])

    try:
        # --- (1) build thật -------------------------------------------------
        xong, loi, giay, duoi = dung_ban_build(dist_dir)
        if not xong:
            return KetQuaGate(dat=False, buoc="next build", loi=loi, giay_build=giay, duoi_log=duoi)

        # Bằng chứng trên đĩa TRƯỚC khi mở cổng: ngày 13/09 thư mục
        # .next/static/css RỖNG mà không lệnh nào kêu ca.
        thu_muc_css = WEB_DIR / dist_dir / "static" / "css"
        if not (thu_muc_css.is_dir() and any(thu_muc_css.rglob("*.css"))):
            return KetQuaGate(
                dat=False,
                buoc="thư mục build",
                loi=[f"{thu_muc_css} không có tệp .css nào sau khi build xong"],
                giay_build=giay,
            )

        # --- (2) next start -------------------------------------------------
        with may_chu_ban_build(dist_dir, cong) as (goc, log):
            len_duoc, ly_do = chay_local.doi_http_200(goc, CHO_START_GIAY, nhip=0.5)
            if not len_duoc:
                return KetQuaGate(
                    dat=False,
                    buoc="next start",
                    loi=[f"trang chủ không trả 200 sau {CHO_START_GIAY:.0f}s ({ly_do})"],
                    giay_build=giay,
                    duoi_log=chay_local._duoi_log(log),
                )

            # --- (3)(4)(5) trang chủ + thẻ link + TẢI tệp CSS ---------------
            css = chay_local.kiem_tra_css_cua_trang(goc, timeout=30.0)
            if not css.dat:
                return KetQuaGate(
                    dat=False,
                    buoc="CSS của trang chủ",
                    loi=css.loi,
                    href_css=css.href,
                    so_byte_css=css.so_byte,
                    giay_build=giay,
                    duoi_log=chay_local._duoi_log(log),
                )
        return KetQuaGate(
            dat=True,
            buoc="",
            href_css=css.href,
            so_byte_css=css.so_byte,
            giay_build=giay,
        )
    finally:
        if not giu_thu_muc:
            don_thu_muc(dist_dir)


def main(argv: list[str] | None = None) -> int:
    configure()
    parser = argparse.ArgumentParser(description="Cổng CSS: build thật rồi đo trang chủ")
    parser.add_argument("--dist-dir", default=DIST_DIR_GATE)
    parser.add_argument("--cong", type=int, default=None)
    parser.add_argument(
        "--giu-thu-muc", action="store_true", help="không xoá thư mục build sau khi đo"
    )
    args = parser.parse_args(argv)

    print("== CỔNG CSS — dựng bản build thật rồi đo trang chủ ==")
    print(f"   Thư mục build riêng: web/{args.dist_dir} (KHÔNG đụng .next)")
    print("   Đang chạy 'next build', mất khoảng 1-3 phút...")
    kq = chay_gate(dist_dir=args.dist_dir, cong=args.cong, giu_thu_muc=args.giu_thu_muc)
    if kq.giay_build:
        print(f"   next build: {kq.giay_build:.1f}s")
    print(kq.bao_cao())
    return 0 if kq.dat else 1


if __name__ == "__main__":
    raise SystemExit(main())
