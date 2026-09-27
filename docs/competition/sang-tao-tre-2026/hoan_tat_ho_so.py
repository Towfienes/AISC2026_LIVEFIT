"""Hoàn tất hồ sơ dự án Bảng C: thay dấu giữ chỗ, dựng, kiểm, chép vào thư mục nộp.

Vì sao có tệp này (27/09/2026): hai thứ cuối cùng của mục 13 — link Google Drive minh
chứng và mã commit ``main`` sau khi hợp nhất — chỉ có SAU khi trưởng nhóm hợp nhất nhánh,
đẩy lên và tải gói Drive lên. Trước đây chúng là ô ⬜ nên không dựng được bản nào gần bản
nộp. Nay ``noi-dung.md`` mang dấu giữ chỗ ``[[LINK_DRIVE]]`` và ``[[COMMIT_NOP]]``; tệp này
thay chúng trên một BẢN SAO TẠM (không sửa ``noi-dung.md``), gọi ``dung_ho_so.py``, quét
chữ của PDF, rồi mới chép vào thư mục nộp.

    # BẢN CHỜ LINK (chưa có link Drive / mã commit): dải đỏ "CHƯA ĐIỀN LINK DRIVE"
    .venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/hoan_tat_ho_so.py
    # BẢN NỘP, sau khi hợp nhất + đẩy main và tải gói Drive lên (mở quyền xem):
    .venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/hoan_tat_ho_so.py \\
        --link-drive https://drive.google.com/drive/folders/<ID> --commit <mã commit main>

Bản nộp CHỈ ra khi đạt hết: link là thư mục Google Drive; mã commit có trên
``origin/main``; bản kê khai đã viết theo trạng thái sau hợp nhất (``dung_ke_khai
.lech_trang_thai_kho`` rỗng); ``dung_ho_so.py`` đạt mọi cổng (không ⬜, không thiếu hình,
≤ 20 trang do Word đếm…); chữ của PDF không còn ``[[``, ``⬜``, ký hiệu Markdown và có
đúng link, mã commit. Hỏng ở bước nào thì không chép gì vào thư mục nộp, thoát mã 1.
Bản nộp chép xong thì xoá bản chờ link trong thư mục nộp để không nộp nhầm.

In ra màn hình chỉ số liệu và đường dẫn — không in nội dung hồ sơ (trang 1 có dữ liệu
cá nhân của thí sinh).
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
REPO = DAY.parents[2]
NOI_DUNG = DAY / "noi-dung.md"
KE_KHAI_MD = DAY / "05-BAN-KE-KHAI.md"
THU_MUC_NOP = Path("D:/AISC2026/NOP-HO-SO-SANG-TAO-TRE-2026/01-Ho-so-du-an")
THU_MUC_DUNG = Path("D:/AISC2026")  # nơi bộ dựng vẫn ghi bản mới nhất (như trước 27/09)
TEN_TEP = "AI2026_Ho_So_Du_An_LiveLift_BangC"
HAU_TO_CHO_LINK = "_CHO_LINK"
GIOI_HAN_TRANG = 20

LINK_DRIVE = "[[LINK_DRIVE]]"
COMMIT_NOP = "[[COMMIT_NOP]]"
_GIU_CHO = re.compile(r"\[\[[^\]\n]*\]\]")
_LINK_THU_MUC = re.compile(
    r"^https://drive\.google\.com/drive/(?:u/\d+/)?folders/([A-Za-z0-9_-]{10,})"
    r"(?:[/?][^\s]*)?$"
)
_MA_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
_DUONG_PDFTOTEXT = (
    Path(r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"),
    Path.home() / r"AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftotext.exe",
)


# ------------------------------------------------------------------ logic thuần
def chuan_hoa_link_drive(url: str) -> tuple[str | None, list[str]]:
    """(link chuẩn, lỗi). Chỉ nhận THƯ MỤC Google Drive; bỏ ``?usp=…``, ``/u/0``.

    Bỏ tham số truy vấn vì link ngắn hơn thì dòng mục 13 không xuống thêm dòng (hồ sơ sát
    20 trang); thư mục mở quyền "bất kỳ ai có đường liên kết" mở được không cần tham số.
    """
    url = (url or "").strip()
    loi = []
    if not url:
        return None, ["thiếu --link-drive"]
    if any(c.isspace() for c in url) or "[[" in url or "⬜" in url:
        loi.append("link có khoảng trắng hoặc còn dấu giữ chỗ")
    m = _LINK_THU_MUC.match(url)
    if not m:
        loi.append(
            "link phải là THƯ MỤC Google Drive dạng https://drive.google.com/drive/folders/<ID> "
            "(không phải tệp, không phải docs.google.com)"
        )
        return None, loi
    return (f"https://drive.google.com/drive/folders/{m.group(1)}" if not loi else None), loi


def kiem_ma_commit(ma: str) -> list[str]:
    ma = (ma or "").strip()
    if not ma:
        return ["thiếu --commit"]
    if not _MA_COMMIT.match(ma):
        return [f"mã commit phải là 7–40 ký tự hex thường, nhận {ma[:12]!r}"]
    return []


def thay_giu_cho(van_ban: str, link: str, ma_commit: str) -> str:
    """Thay hai dấu giữ chỗ; mã commit in 7 ký tự trong dấu mã (khớp mẫu dò của kê khai)."""
    return van_ban.replace(LINK_DRIVE, link).replace(COMMIT_NOP, f"`{ma_commit[:7]}`")


def giu_cho_con_lai(van_ban: str) -> list[str]:
    return sorted(set(_GIU_CHO.findall(van_ban)))


def quet_chu_pdf(chu: str, *, cho_phep_giu_cho: bool, phai_co: tuple[str, ...] = ()) -> list[str]:
    """Lỗi tìm thấy trong chữ trích từ PDF. Không trả nội dung quanh chỗ lỗi (trang 1 có
    dữ liệu cá nhân), chỉ trả số lần."""
    loi = []
    kiem = [
        ("⬜", "ô ⬜"),
        ("**", "dấu **"),
        ("`", "dấu `"),
        ("](", "cú pháp liên kết ]("),
        ("<!--", "chú thích <!--"),
    ]
    if not cho_phep_giu_cho:
        kiem.append(("[[", "dấu giữ chỗ [["))
    for ky_hieu, ten in kiem:
        n = chu.count(ky_hieu)
        if n:
            loi.append(f"PDF còn {n} {ten}")
    phang = re.sub(r"\s+", "", chu)
    for x in phai_co:
        if re.sub(r"\s+", "", x) not in phang:
            loi.append(f"PDF không chứa {x[:60]!r}")
    so_trang = chu.count("\f")
    if so_trang > GIOI_HAN_TRANG:
        loi.append(f"PDF có {so_trang} trang (> {GIOI_HAN_TRANG})")
    return loi


# ------------------------------------------------------------------ bên ngoài (thay được khi test)
def tim_pdftotext() -> str | None:
    return shutil.which("pdftotext") or next(
        (str(p) for p in _DUONG_PDFTOTEXT if p.is_file()), None
    )


def chu_pdf(pdf: Path) -> str:
    """Chữ của PDF (mỗi trang kết thúc bằng \\f). Không có pdftotext thì lỗi, không đoán."""
    exe = tim_pdftotext()
    if exe is None:
        raise RuntimeError("không tìm thấy pdftotext (Git for Windows hoặc MiKTeX có sẵn)")
    kq = subprocess.run(  # noqa: S603 — tệp chạy tìm ở đường dẫn cố định
        [exe, "-enc", "UTF-8", str(pdf), "-"], capture_output=True, check=True
    )
    return kq.stdout.decode("utf-8", errors="replace")


def kiem_commit_tren_main(ma: str, repo: Path = REPO) -> list[str]:
    """Mã commit phải có trong kho và nằm trên ``origin/main`` (đã hợp nhất VÀ đẩy lên)."""

    def git(*a: str) -> int:
        lenh = ["git", "-C", str(repo), *a]
        return subprocess.run(lenh, capture_output=True, check=False).returncode  # noqa: S603

    if git("cat-file", "-e", f"{ma}^{{commit}}") != 0:
        return [f"kho không có commit {ma[:12]} (chưa fetch?)"]
    if git("merge-base", "--is-ancestor", ma, "origin/main") != 0:
        return [f"commit {ma[:12]} chưa nằm trên origin/main — hợp nhất và đẩy lên trước"]
    return []


def dung(noi_dung_tam: Path, ra: Path, *, cho_link: bool) -> int:
    """Gọi bộ dựng hồ sơ (cần python-docx) trên bản sao tạm; hình lấy từ thư mục gốc."""
    sys.path.insert(0, str(DAY))
    try:
        import dung_ho_so  # noqa: PLC0415 — cần python-docx, chỉ nạp khi thật sự dựng
    finally:
        sys.path.remove(str(DAY))
    argv = ["--noi-dung", str(noi_dung_tam), "--goc-hinh", str(DAY), "--out-dir", str(ra)]
    return dung_ho_so.main([*argv, "--ban-cho-link"] if cho_link else argv)


def lech_ke_khai(van_ban_ho_so: str) -> list[str]:
    sys.path.insert(0, str(DAY / "ke_khai"))
    try:
        import dung_ke_khai  # noqa: PLC0415
    finally:
        sys.path.remove(str(DAY / "ke_khai"))
    return dung_ke_khai.lech_trang_thai_kho(van_ban_ho_so, KE_KHAI_MD.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ luồng chính
def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--link-drive", default=None, help="link THƯ MỤC Google Drive đã mở quyền")
    ap.add_argument("--commit", default=None, help="mã commit main sau khi hợp nhất và đẩy lên")
    ap.add_argument("--nop", type=Path, default=THU_MUC_NOP, help="thư mục nộp (01-Ho-so-du-an)")
    ap.add_argument("--dung", type=Path, default=THU_MUC_DUNG, help="nơi giữ thêm một bản")
    ap.add_argument("--noi-dung", type=Path, default=NOI_DUNG, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    cho_link = a.link_drive is None and a.commit is None
    if not cho_link and (a.link_drive is None or a.commit is None):
        print("CHƯA DỰNG: bản nộp cần CẢ --link-drive lẫn --commit (thiếu cả hai = bản chờ link).")
        return 2

    van_ban = a.noi_dung.read_text(encoding="utf-8")
    phai_co: tuple[str, ...] = ()
    if cho_link:
        print("Dựng BẢN CHỜ LINK (chưa có link Drive, mã commit nộp).")
        moi = van_ban
    else:
        link, loi = chuan_hoa_link_drive(a.link_drive)
        ma = (a.commit or "").strip().lower()
        loi += kiem_ma_commit(ma)
        if not loi:
            loi += kiem_commit_tren_main(ma)
        if loi:
            print("CHƯA DỰNG BẢN NỘP:")
            for x in loi:
                print("   -", x)
            return 1
        moi = thay_giu_cho(van_ban, link, ma)
        con = giu_cho_con_lai(moi)
        if con:
            print("CHƯA DỰNG BẢN NỘP: còn dấu giữ chỗ lạ", ", ".join(con))
            return 1
        lech = lech_ke_khai(moi)
        if lech:
            print("CHƯA DỰNG BẢN NỘP — bản kê khai còn tả kho như TRƯỚC khi hợp nhất:")
            for x in lech:
                print("   -", x)
            print("  Sửa 05-BAN-KE-KHAI.md theo trạng thái sau hợp nhất, dựng lại kê khai.")
            return 1
        phai_co = (link, ma[:7])
        print(f"Dựng BẢN NỘP với link Drive đã chuẩn hóa và commit {ma[:7]}.")

    hau_to = HAU_TO_CHO_LINK if cho_link else ""
    with tempfile.TemporaryDirectory(prefix="hoan-tat-ho-so-") as td:
        td = Path(td)
        tam = td / "noi-dung.md"
        tam.write_text(moi, encoding="utf-8")
        ra = td / "ra"
        ma_dung = dung(tam, ra, cho_link=cho_link)
        docx = ra / f"{TEN_TEP}{hau_to}.docx"
        pdf = docx.with_suffix(".pdf")
        if ma_dung != 0 or not docx.exists() or not pdf.exists():
            print(f"CHƯA XONG: bộ dựng thoát mã {ma_dung} — không chép gì vào thư mục nộp.")
            return 1
        try:
            chu = chu_pdf(pdf)
        except (RuntimeError, OSError, subprocess.CalledProcessError) as e:
            print(f"CHƯA XONG: không đọc được chữ của PDF ({e}) — không chép gì.")
            return 1
        loi = quet_chu_pdf(chu, cho_phep_giu_cho=cho_link, phai_co=phai_co)
        if cho_link and "CHƯA ĐIỀN LINK DRIVE" not in chu:
            loi.append("bản chờ link thiếu dải CHƯA ĐIỀN LINK DRIVE")
        if loi:
            print("CHƯA XONG — quét PDF:")
            for x in loi:
                print("   -", x)
            return 1
        print(
            f"  Quét PDF đạt: {chu.count(chr(12))} trang, không còn ⬜/Markdown"
            + ("" if cho_link else ", không còn [[, có đúng link và mã commit")
            + "."
        )
        for dich in (a.nop, a.dung):
            dich.mkdir(parents=True, exist_ok=True)
            for tep in (docx, pdf):
                shutil.copy2(tep, dich / tep.name)
        if not cho_link:
            for cu in a.nop.glob(f"{TEN_TEP}{HAU_TO_CHO_LINK}.*"):
                cu.unlink()
        print(f"Đã chép {docx.name}, {pdf.name} vào {a.nop} và {a.dung}.")
    if cho_link:
        print(
            "  BẢN CHỜ LINK — KHÔNG NỘP. Có link Drive và mã commit thì chạy lại với "
            "--link-drive … --commit …."
        )
    else:
        print("  BẢN NỘP sẵn sàng. Mở PDF kiểm lại trang 1 (thông tin thí sinh) và trang cuối.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
