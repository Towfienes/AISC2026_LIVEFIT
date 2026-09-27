"""Dựng BẢN NỘP CHÍNH THỨC: hồ sơ dự án Bảng C và bản kê khai, quét PDF, chép vào thư mục nộp.

Vì sao có tệp này. Hai văn bản nộp (hồ sơ dự án theo MẪU 3 và bản kê khai công cụ AI) dựng
bằng hai bộ dựng khác nhau; mỗi bộ tự kiểm phần của mình, nhưng không bộ nào đọc lại CHỮ của
PDF cuối cùng. Tệp này dựng cả hai vào thư mục tạm, đọc chữ của từng PDF, và chỉ chép vào thư
mục nộp khi mọi cổng đều đạt. Hỏng ở bất kỳ bước nào thì không chép gì, thoát mã 1.

27/09/2026, trưởng nhóm chốt: hồ sơ nộp NGAY, không chờ link nào, không nhắc Google Drive ở
đâu cả; mục 13 trỏ kho mã công khai. Bản trước của tệp này (thay dấu giữ chỗ ``[[LINK_DRIVE]]``,
``[[COMMIT_NOP]]`` bằng ``--link-drive``, ``--commit``; "bản chờ link" có dải đỏ) đã bỏ.

    .venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/hoan_tat_ho_so.py
    # ngày in ở khối ký tên (mặc định hôm nay):  --ngay-ky 28/09/2026

Cổng của bản nộp:
  * nguồn ``noi-dung.md`` và ``05-BAN-KE-KHAI.md`` không còn ``[[…]]``, ô ⬜, chữ "Drive";
    bản kê khai tả kho SAU khi hợp nhất (``dung_ke_khai.lech_trang_thai_kho`` rỗng);
  * bộ dựng hồ sơ đạt mọi cổng của nó (≤ 20 trang do Word đếm, không lọt Markdown…);
  * chữ của PDF hồ sơ: không còn ``[[``, ⬜, ký hiệu Markdown, chữ "Drive"; có NGUYÊN VĂN câu
    bắt buộc cuối mục 1, tên sản phẩm và link kho mã; ≤ 20 trang; trang cuối không trống
    quá nửa;
  * chữ của PDF kê khai: như trên (trừ giới hạn trang và câu bắt buộc), có tên sản phẩm.

In ra màn hình chỉ số liệu và đường dẫn, không in nội dung hồ sơ (trang 1 có dữ liệu cá nhân
của thí sinh).
"""

from __future__ import annotations

import argparse
import contextlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DAY = Path(__file__).resolve().parent
NOI_DUNG = DAY / "noi-dung.md"
KE_KHAI_MD = DAY / "05-BAN-KE-KHAI.md"
THU_MUC_NOP = Path("D:/AISC2026/NOP-HO-SO-SANG-TAO-TRE-2026")
THU_MUC_HO_SO = "01-Tai-lieu-du-an"
THU_MUC_KE_KHAI = "05-Ban-ke-khai"
TEN_HO_SO = "AI2026_BangC_LiveLift_HoSoDuAn"
TEN_KE_KHAI = "AI2026_BangC_LiveLift_BanKeKhai"
GIOI_HAN_TRANG = 20
#: Trang cuối phải có chữ tới ít nhất nửa trang (tính theo chiều cao trang).
LAP_DAY_TOI_THIEU = 0.5

TEN_SAN_PHAM = (
    "LiveLift - Nền tảng thí nghiệm vận hành và hỗ trợ ra quyết định cho livestream thương mại"
)
#: Câu trưởng nhóm yêu cầu NGUYÊN VĂN làm đoạn kết mục 1 (27/09/2026).
CAU_BAT_BUOC = (
    "Xuất phát từ những lý do trên, nhóm nghiên cứu quyết định lựa chọn và tiến hành nghiên "
    f"cứu, phát triển giải pháp “{TEN_SAN_PHAM}”, hướng tới việc hỗ trợ đội ngũ vận hành đánh "
    "giá có hệ thống tác động của các quyết định trong phiên live và từng bước chuyển từ ra "
    "quyết định chủ yếu dựa trên kinh nghiệm sang ra quyết định dựa trên bằng chứng."
)
KHO_MA = "https://github.com/bminhnemhoi/AISC2026_LIVEFIT"

_GIU_CHO = re.compile(r"\[\[[^\]\n]*\]\]")
_DRIVE = re.compile(r"drive", re.I)
#: Poppler (MiKTeX) đứng trước: chỉ nó có ``-bbox`` để đo trang cuối; bản xpdf 4.00 của Git
#: for Windows đọc chữ được nhưng không có ``-bbox``.
_DUONG_PDFTOTEXT = (
    Path.home() / r"AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftotext.exe",
    Path(r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"),
)


# ------------------------------------------------------------------ logic thuần
def than(md: str) -> str:
    """Phần sẽ in của một tệp nguồn (bỏ chú thích ``<!-- … -->`` dành cho người viết)."""
    return re.sub(r"<!--.*?-->", "", md, flags=re.S)


def loi_nguon(ten: str, md: str) -> list[str]:
    """Lỗi tìm thấy trong phần sẽ in của một tệp nguồn .md."""
    t = than(md)
    loi = []
    giu_cho = sorted(set(_GIU_CHO.findall(t)))
    if giu_cho:
        loi.append(f"{ten}: còn dấu giữ chỗ {', '.join(giu_cho)}")
    if "⬜" in t:
        loi.append(f"{ten}: còn {t.count('⬜')} ô ⬜")
    n = len(_DRIVE.findall(t))
    if n:
        loi.append(f"{ten}: còn {n} chỗ nhắc Drive")
    return loi


def phang(chu: str) -> str:
    """Bỏ mọi khoảng trắng: chữ trích từ PDF ngắt dòng tùy chỗ, không so được nguyên dạng."""
    return re.sub(r"\s+", "", chu)


def quet_chu_pdf(
    chu: str, *, phai_co: tuple[str, ...] = (), gioi_han_trang: int | None
) -> list[str]:
    """Lỗi tìm thấy trong chữ trích từ PDF. Không trả nội dung quanh chỗ lỗi (trang 1 của
    hồ sơ có dữ liệu cá nhân), chỉ trả số lần."""
    loi = []
    for ky_hieu, ten in (
        ("⬜", "ô ⬜"),
        ("[[", "dấu giữ chỗ [["),
        ("**", "dấu **"),
        ("`", "dấu `"),
        ("](", "cú pháp liên kết ]("),
        ("<!--", "chú thích <!--"),
    ):
        n = chu.count(ky_hieu)
        if n:
            loi.append(f"PDF còn {n} {ten}")
    n = len(_DRIVE.findall(chu))
    if n:
        loi.append(f"PDF còn {n} chỗ nhắc Drive")
    p = phang(chu)
    for x in phai_co:
        if phang(x) not in p:
            loi.append(f"PDF không chứa nguyên văn {x[:60]!r}…")
    so_trang = chu.count("\f")
    if gioi_han_trang is not None and so_trang > gioi_han_trang:
        loi.append(f"PDF có {so_trang} trang (> {gioi_han_trang})")
    return loi


_TRANG = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">')
_TU = re.compile(r'<word xMin="[\d.]+" yMin="[\d.]+" xMax="[\d.]+" yMax="([\d.]+)">')


def ty_le_lap_day(bbox_html: str) -> float | None:
    """Tỷ lệ chiều cao trang có chữ, tính tới từ thấp nhất (0..1), từ ``pdftotext -bbox``
    của MỘT trang. Không đọc được thì None."""
    m = _TRANG.search(bbox_html)
    y = [float(v) for v in _TU.findall(bbox_html)]
    if not m or not y:
        return None
    return max(y) / float(m.group(2))


def dem_gach(chu: str) -> dict[str, int]:
    """Số gạch dài (—) và gạch ngắn (–) trong chữ của PDF: trưởng nhóm yêu cầu hạn chế tối đa."""
    return {"—": chu.count("—"), "–": chu.count("–")}


# ------------------------------------------------------------------ bên ngoài (thay được khi test)
def tim_pdftotext() -> str | None:
    return next((str(p) for p in _DUONG_PDFTOTEXT if p.is_file()), None) or shutil.which(
        "pdftotext"
    )


def _pdftotext(*doi: str) -> str:
    exe = tim_pdftotext()
    if exe is None:
        raise RuntimeError("không tìm thấy pdftotext (Git for Windows hoặc MiKTeX có sẵn)")
    kq = subprocess.run(  # noqa: S603 — tệp chạy tìm ở đường dẫn cố định
        [exe, "-enc", "UTF-8", *doi, "-"], capture_output=True, check=True
    )
    return kq.stdout.decode("utf-8", errors="replace")


def chu_pdf(pdf: Path) -> str:
    """Chữ của PDF (mỗi trang kết thúc bằng \\f). Không có pdftotext thì lỗi, không đoán."""
    return _pdftotext(str(pdf))


def lap_day_trang_cuoi(pdf: Path, so_trang: int) -> float | None:
    return ty_le_lap_day(_pdftotext("-bbox", "-f", str(so_trang), "-l", str(so_trang), str(pdf)))


def dung_ho_so(ra: Path, ngay_ky: str | None) -> int:
    """Gọi bộ dựng hồ sơ (cần python-docx và Word) vào thư mục ``ra``."""
    sys.path.insert(0, str(DAY))
    try:
        import dung_ho_so as bo  # noqa: PLC0415 — cần python-docx, chỉ nạp khi thật sự dựng
    finally:
        sys.path.remove(str(DAY))
    argv = ["--out-dir", str(ra), "--noi-dung", str(NOI_DUNG)]
    return bo.main([*argv, "--ngay-ky", ngay_ky] if ngay_ky else argv)


def dung_ke_khai(ra_docx: Path) -> int:
    """Gọi bộ dựng bản kê khai (cần python-docx và Word), ghi ``ra_docx`` và PDF cùng tên."""
    sys.path.insert(0, str(DAY / "ke_khai"))
    try:
        import dung_ke_khai as bo  # noqa: PLC0415
    finally:
        sys.path.remove(str(DAY / "ke_khai"))
    return bo.main(["--ra", str(ra_docx)])


def lech_ke_khai(ke_khai: str) -> list[str]:
    sys.path.insert(0, str(DAY / "ke_khai"))
    try:
        import dung_ke_khai as bo  # noqa: PLC0415
    finally:
        sys.path.remove(str(DAY / "ke_khai"))
    return bo.lech_trang_thai_kho(ke_khai)


# ------------------------------------------------------------------ luồng chính
def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--nop", type=Path, default=THU_MUC_NOP, help="thư mục gốc hồ sơ nộp")
    ap.add_argument("--ngay-ky", default=None, help="ngày ký DD/MM/YYYY (mặc định hôm nay)")
    a = ap.parse_args(argv)

    ho_so_md = NOI_DUNG.read_text(encoding="utf-8")
    ke_khai_md = KE_KHAI_MD.read_text(encoding="utf-8")
    loi = loi_nguon(NOI_DUNG.name, ho_so_md) + loi_nguon(KE_KHAI_MD.name, ke_khai_md)
    if phang(CAU_BAT_BUOC) not in phang(than(ho_so_md)):
        loi.append(f"{NOI_DUNG.name}: thiếu nguyên văn câu bắt buộc cuối mục 1")
    loi += lech_ke_khai(ke_khai_md)
    if loi:
        print("CHƯA DỰNG, nguồn còn lỗi:")
        for x in loi:
            print("   -", x)
        return 1

    with tempfile.TemporaryDirectory(prefix="hoan-tat-ho-so-") as td:
        td = Path(td)
        ra_hs, ra_kk = td / "ho-so", td / "ke-khai"
        ra_hs.mkdir()
        ra_kk.mkdir()
        ma = dung_ho_so(ra_hs, a.ngay_ky)
        hs_docx = ra_hs / f"{TEN_HO_SO}.docx"
        if ma != 0 or not hs_docx.exists() or not hs_docx.with_suffix(".pdf").exists():
            print(f"CHƯA XONG: bộ dựng hồ sơ thoát mã {ma}, không chép gì vào thư mục nộp.")
            return 1
        kk_docx = ra_kk / f"{TEN_KE_KHAI}.docx"
        ma = dung_ke_khai(kk_docx)
        if ma != 0 or not kk_docx.exists() or not kk_docx.with_suffix(".pdf").exists():
            print(f"CHƯA XONG: bộ dựng kê khai thoát mã {ma}, không chép gì vào thư mục nộp.")
            return 1

        loi = []
        try:
            chu_hs = chu_pdf(hs_docx.with_suffix(".pdf"))
            chu_kk = chu_pdf(kk_docx.with_suffix(".pdf"))
            trang_hs = chu_hs.count("\f")
            lap_day = lap_day_trang_cuoi(hs_docx.with_suffix(".pdf"), trang_hs)
        except (RuntimeError, OSError, subprocess.CalledProcessError) as e:
            print(f"CHƯA XONG: không đọc được chữ của PDF ({e}), không chép gì.")
            return 1
        loi += [
            f"hồ sơ: {x}"
            for x in quet_chu_pdf(
                chu_hs,
                phai_co=(CAU_BAT_BUOC, TEN_SAN_PHAM, KHO_MA),
                gioi_han_trang=GIOI_HAN_TRANG,
            )
        ]
        if lap_day is None or lap_day < LAP_DAY_TOI_THIEU:
            loi.append(
                f"hồ sơ: trang cuối (trang {trang_hs}) chỉ có chữ tới "
                f"{0 if lap_day is None else round(lap_day * 100)}% chiều cao, trống quá nửa"
            )
        loi += [
            f"kê khai: {x}"
            for x in quet_chu_pdf(chu_kk, phai_co=(TEN_SAN_PHAM,), gioi_han_trang=None)
        ]
        if loi:
            print("CHƯA XONG, quét PDF:")
            for x in loi:
                print("   -", x)
            return 1
        g_hs, g_kk = dem_gach(chu_hs), dem_gach(chu_kk)
        print(
            f"  Quét PDF đạt. Hồ sơ: {trang_hs} trang, trang cuối có chữ tới "
            f"{round(lap_day * 100)}% chiều cao, {g_hs['—']} gạch dài và {g_hs['–']} gạch "
            f"ngắn. Kê khai: {chu_kk.count(chr(12))} trang, {g_kk['—']} gạch dài và "
            f"{g_kk['–']} gạch ngắn."
        )
        for thu_muc, docx in ((THU_MUC_HO_SO, hs_docx), (THU_MUC_KE_KHAI, kk_docx)):
            dich = a.nop / thu_muc
            dich.mkdir(parents=True, exist_ok=True)
            for tep in (docx, docx.with_suffix(".pdf")):
                shutil.copy2(tep, dich / tep.name)
            print(f"Đã chép {docx.stem}.docx và .pdf vào {dich}")
    print("  BẢN NỘP sẵn sàng. Mở PDF kiểm lại trang 1 (thông tin thí sinh) và trang cuối.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
