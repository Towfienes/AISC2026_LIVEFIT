"""Dựng hồ sơ dự án Bảng C (.docx + .pdf) cho Cuộc thi Sáng tạo trẻ Quốc gia về AI 2026.

Vì sao có tệp này: bản nộp phải DỰNG LẠI ĐƯỢC. Nội dung nằm ở ``noi-dung.md``,
định dạng nằm ở đây, còn khung MẪU 3 lấy NGUYÊN XI từ file mẫu của ban tổ chức
— kể cả bảng thông tin thí sinh và khối ký tên. Sửa chữ thì sửa Markdown rồi
chạy lại; sửa thẳng .docx là lần dựng sau mất hết.

Mẫu của cuộc thi gộp cả ba bảng A, B, C vào MỘT file. Tệp này cắt lấy đúng đoạn
MẪU 3 (Bảng C) rồi mới điền, nên nếu ban tổ chức phát hành lại mẫu thì chỉ cần
thay file mẫu, không phải sửa mã.

Chạy (cần ``python-docx``, cố ý KHÔNG nằm trong phụ thuộc dự án)::

    python -m venv .venv-docx
    .venv-docx/Scripts/pip install python-docx
    .venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/dung_ho_so.py
    # bản nháp khi còn ô ⬜ / thiếu hình, ra thư mục khác:
    .venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/dung_ho_so.py \
        --out-dir <thư mục> --cho-phep-o-trong
    # tự kiểm bộ dựng (không cần Word):
    .venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/dung_ho_so.py --tu-kiem

Luật an toàn của bản nộp (sửa 25/09/2026, sau kiểm toán hồ sơ):

1. **Không bao giờ ghi đè bản nộp bằng một bản hỏng.** Mọi thứ dựng ra tệp tạm
   trong thư mục đích; chỉ khi đạt HẾT điều kiện (không ô ⬜, không thiếu hình,
   ô "3 người" đã tích, không lọt ký tự Markdown, ≤ 20 trang do Word đếm) thì
   tệp tạm mới được đổi tên thành ``AI2026_Ho_So_Du_An_LiveLift_BangC.docx/.pdf``.
   Trước đây bộ dựng ghi .docx + .pdf RỒI mới báo lỗi và thoát mã 1.
2. Còn ô ⬜ mà không có ``--cho-phep-o-trong`` → thoát mã 1 ngay, không tạo
   tệp nào. Có cờ đó → dựng BẢN NHÁP mang hậu tố ``_NHAP``, không bao giờ trùng
   tên bản nộp.
3. Giới hạn cứng **20 trang**, đếm bằng Word (COM) — chỉ Word ngắt trang giống
   thứ ban tổ chức sẽ mở. Mẫu để giãn dòng 1,15 nên bộ dựng giữ đúng 1,15.

Cú pháp Markdown được hỗ trợ — xem đầu ``noi-dung.md`` (khối chú thích).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph

DAY = Path(__file__).resolve().parent
NOI_DUNG = DAY / "noi-dung.md"

# Mẫu của ban tổ chức nằm ngoài kho mã (tài sản của BTC, không đưa vào git).
MAU = Path(
    r"D:\AISC2026\sang tạo trẻ quốc gia\drive-download-20260914T062853Z-1-001"
    r"\AI2026_Mẫu hồ sơ.docx"
)
OUT_DIR_MAC_DINH = Path(r"D:\AISC2026")
TEN_TEP = "AI2026_Ho_So_Du_An_LiveLift_BangC"
HAU_TO_NHAP = "_NHAP"

CHO_TRONG = "⬜"
GIOI_HAN_TRANG = 20
SO_MUC_MAU_3 = 13

FONT = "Times New Roman"
FONT_MA = "Consolas"
CO = Pt(13)
CO_BANG = Pt(10.5)
CO_KHOI_MA = Pt(9)
CO_TLTK = Pt(11)  # danh mục tài liệu tham khảo
GIAN_DONG = 1.15  # đúng như mẫu MẪU 3 đặt cho phần nội dung

NEN_TIEU_DE_BANG = "D5DCE4"  # đúng màu nền hàng tiêu đề trong bảng của mẫu BTC
NEN_KHUNG = "EEF2F7"  # nền khung "> " (tóm tắt dự án)
NEN_MA = "F0F0F0"  # nền chữ mã nội dòng

RONG_HINH_MAC_DINH_CM = 15.0
RONG_CHU_CM = 16.0  # A4 11907 twip − lề trái 1701 − lề phải 1134 = 9072 twip = 16,0 cm

TAC_GIA = "Đội LiveLift"
TIEU_DE_TEP = (
    "LiveLift — Hồ sơ dự án Bảng C, Cuộc thi Sáng tạo trẻ Quốc gia về Trí tuệ nhân tạo 2026"
)

# MẪU 3 hỏi "Lớp hành chính, ngành, khoa, trường" — KHÔNG hỏi MSSV. Bản PDF còn
# lên thư mục minh chứng, nên mặc định không in MSSV (tối thiểu hóa dữ liệu cá
# nhân). Đổi thành True nếu ban tổ chức yêu cầu.
GHI_MSSV = False

W14 = "http://schemas.microsoft.com/office/word/2010/wordml"

# ---------------------------------------------------------------- thông tin đội
# Đọc từ docs/competition/thong-tin-doi.local.json (đã gitignore) — ngày sinh,
# MSSV, số điện thoại không được nằm trong kho mã công khai. Xem thong_tin_doi.py.
sys.path.insert(0, str(DAY.parent))
import thong_tin_doi  # noqa: E402


def thanh_vien_tu(doi: dict) -> list[dict[str, str]]:
    """Chuyển JSON thông tin đội thành đúng 6 ô mà MẪU 3 hỏi cho mỗi thí sinh."""
    ra = []
    for tv in doi["thanh_vien"]:
        lop = (tv.get("lop_hanh_chinh") or CHO_TRONG).strip() or CHO_TRONG
        phan = [
            f"Lớp {lop}",
            f"Ngành {tv['nganh']}",
            f"Khoa {tv['khoa']}",
            f"Trường {tv['truong']}",
        ]
        if GHI_MSSV:
            phan.append(f"MSSV {tv['mssv']}")
        ra.append(
            {
                "ho_ten": tv["ho_ten"],
                "ngay_sinh": tv["ngay_sinh"],
                "lop": ", ".join(phan),
                "noi_o": tv["noi_o"],
                "dien_thoai": tv["dien_thoai"],
                "email": tv["email"],
            }
        )
    return ra


# ------------------------------------------------------------------ tiện ích Word
def _dat_font(run, name: str) -> None:
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)


def _to_nen(run, mau: str) -> None:
    rpr = run._element.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), mau)
    rpr.append(shd)


def set_font(run, *, bold=False, size=CO, italic=False, mono=False):
    """Định dạng một run. ``mono`` = chữ mã: Consolas, nhỏ hơn chữ quanh nó ~15%."""
    name = FONT_MA if mono else FONT
    run.font.name = name
    run.font.size = Pt(round(size.pt * 0.85 * 2) / 2) if mono else size
    run.font.bold = bold
    run.font.italic = italic
    _dat_font(run, name)
    return run


# Mã trước, rồi đậm, rồi nghiêng: ở cùng một vị trí, phép chọn của regex theo thứ
# tự nhánh — nên `a**b` là mã, không phải mở đầu chữ đậm.
_INLINE = re.compile(r"(`[^`\n]+`|\*\*.+?\*\*|\*[^*\n]+?\*)")


def emit_runs(p, text, *, size=CO, bold=False, italic=False):
    """Dịch **đậm**, *nghiêng* và `mã` thành run Word — kể cả LỒNG nhau.

    Lỗi cũ (kiểm toán 25/09/2026): regex tách ``**…**`` nuốt nguyên cụm, in cả cặp
    dấu backtick bên trong ra bản PDF ("Phiên không có `design_hash`"). Nay phần
    trong ``**…**`` và ``*…*`` được dịch đệ quy; mã thành run Consolas có nền nhạt.
    """
    for chunk in _INLINE.split(text):
        if not chunk:
            continue
        if chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:
            r = set_font(p.add_run(chunk[1:-1]), bold=bold, italic=italic, size=size, mono=True)
            _to_nen(r, NEN_MA)
        elif chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
            emit_runs(p, chunk[2:-2], size=size, bold=True, italic=italic)
        elif chunk.startswith("*") and chunk.endswith("*") and len(chunk) > 2:
            emit_runs(p, chunk[1:-1], size=size, bold=bold, italic=True)
        else:
            set_font(p.add_run(chunk), bold=bold, italic=italic, size=size)


def para(
    doc,
    text="",
    *,
    bold=False,
    size=CO,
    italic=False,
    align=None,
    space_before=0,
    space_after=4,
    indent=None,
    mono=False,
    giu_voi_doan_sau=False,
    dinh_dang=True,
):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.0 if mono else GIAN_DONG
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.first_line_indent = Pt(0)
    if align is not None:
        p.alignment = align
    if indent is not None:
        pf.left_indent = Pt(indent)
    if giu_voi_doan_sau:
        pf.keep_with_next = True
    if text:
        if mono:
            r = p.add_run(text)
            r.font.name = FONT_MA
            r.font.size = CO_KHOI_MA
            _dat_font(r, FONT_MA)
        elif dinh_dang:
            emit_runs(p, text, size=size, bold=bold, italic=italic)
        else:
            set_font(p.add_run(text), bold=bold, size=size, italic=italic)
    return p


def rich_para(doc_or_cell, text, *, indent=None, space_after=3, hanging=False, size=CO):
    p = doc_or_cell.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = GIAN_DONG
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    pf.first_line_indent = Pt(0)
    # Văn xuôi canh đều; gạch đầu dòng canh trái, vì canh đều trên dòng có
    # thụt treo làm chữ giãn thành khoảng trắng loang lổ.
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT if hanging else WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent is not None:
        pf.left_indent = Pt(indent)
        if hanging:
            pf.first_line_indent = Pt(-11)
    emit_runs(p, text, size=size)
    return p


def _chu_thich(doc, nhan: str, noi_dung: str, *, giu_voi_doan_sau: bool, space_after=6):
    """'Hình N.' / 'Bảng N.' in đậm, phần còn lại in nghiêng, canh giữa."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.0
    pf.space_before = Pt(2)
    pf.space_after = Pt(space_after)
    pf.first_line_indent = Pt(0)
    pf.keep_with_next = giu_voi_doan_sau
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(nhan + " "), bold=True, size=Pt(11.5))
    emit_runs(p, noi_dung, size=Pt(11.5), italic=True)
    return p


def _nen_o(cell, mau: str) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), mau)
    tcpr.append(shd)


def _do_rong_cot(rows: list[list[str]], ncol: int) -> list[float]:
    """Chia 16 cm theo độ dài chữ của từng cột (mũ 0,7 để cột dài không nuốt hết).

    Word tự co giãn thì cột đầu ngắn chữ bị ép hẹp, nhãn dòng xuống 3 dòng
    (bảng baseline bản 15/09) — đặt độ rộng tường minh tiết kiệm được dòng.
    """
    trong_so = []
    for j in range(ncol):
        dai = max((len(r[j]) if j < len(r) else 0) for r in rows)
        trong_so.append(max(min(dai, 60), 5) ** 0.7)
    tong = sum(trong_so)
    return [RONG_CHU_CM * w / tong for w in trong_so]


def add_table(doc, rows, canh=None):
    ncol = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=ncol)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    rong = _do_rong_cot(rows, ncol)
    grid = t._tbl.tblGrid
    for j, gc in enumerate(grid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(int(rong[j] / 2.54 * 1440)))
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j in range(ncol):
            txt = row[j] if j < len(row) else ""
            cells[j].width = Cm(rong[j])
            cp = cells[j].paragraphs[0]
            cp.paragraph_format.line_spacing = 1.0
            cp.paragraph_format.space_after = Pt(1)
            cp.paragraph_format.space_before = Pt(1)
            if i == 0:
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _nen_o(cells[j], NEN_TIEU_DE_BANG)
            elif canh and j < len(canh) and canh[j]:
                cp.alignment = canh[j]
            else:
                cp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # Mẫu đặt thụt dòng đầu ở docDefaults; trong ô bảng nó đẩy dòng đầu
            # vào trong còn dòng xuống hàng sát mép trái, trông như lỗi in.
            cp.paragraph_format.first_line_indent = Pt(0)
            emit_runs(cp, txt, size=CO_BANG, bold=(i == 0))
            if i == 0:
                cp.paragraph_format.keep_with_next = True

        trpr = cells[0]._tc.getparent().get_or_add_trPr()
        if i == 0:
            trpr.append(OxmlElement("w:tblHeader"))  # lặp tiêu đề mỗi trang
        trpr.append(OxmlElement("w:cantSplit"))  # không xẻ đôi hàng
    return t


def add_khung(doc, dong: list[str]):
    """Khung nền nhạt một ô cho các dòng ``> …`` (dùng cho Tóm tắt dự án)."""
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.rows[0].cells[0]
    cell.width = Cm(RONG_CHU_CM)
    _nen_o(cell, NEN_KHUNG)
    cell._tc.remove(cell.paragraphs[0]._p)
    for d in dong:
        m = re.match(r"^[-•]\s+(.*)$", d)
        if m:
            rich_para(cell, "• " + m.group(1), indent=12, space_after=1, hanging=True, size=Pt(12))
        elif d.strip():
            rich_para(cell, d, space_after=2, size=Pt(12))
    if not cell.paragraphs:
        cell.add_paragraph()
    trpr = t.rows[0]._tr.get_or_add_trPr()
    trpr.append(OxmlElement("w:cantSplit"))
    return t


# ------------------------------------------------------------------ dựng thân bài
@dataclass
class NguCanh:
    """Thứ bộ dựng ghi lại trong lúc đổ nội dung, để kiểm sau."""

    goc: Path  # thư mục chứa noi-dung.md — đường dẫn hình tính từ đây
    hinh: list[int] = field(default_factory=list)
    bang: list[int] = field(default_factory=list)
    thieu_hinh: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)


_HINH = re.compile(r"^!\[(.*?)\]\((.+?)\)(\{[^}]*\})?\s*$")
_CHU_THICH_HINH = re.compile(r"^Hình\s+(\d+)\.\s+(.+)$")
_CHU_THICH_BANG = re.compile(r"^:\s*Bảng\s+(\d+)\.\s+(.+)$")


def _rong_hinh(thuoc_tinh: str | None, chu_thich: str) -> tuple[float, str]:
    rong = RONG_HINH_MAC_DINH_CM
    if thuoc_tinh:
        m = re.search(r"width\s*=\s*([\d.,]+)\s*cm", thuoc_tinh)
        if m:
            rong = float(m.group(1).replace(",", "."))
    elif "|" in chu_thich:  # cú pháp cũ ![chú thích|10.5](…)
        truoc, _, so = chu_thich.rpartition("|")
        if re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", so):
            rong, chu_thich = float(so.strip().replace(",", ".")), truoc
    return min(rong, RONG_CHU_CM), chu_thich


def _them_hinh(doc, ctx: NguCanh, alt: str, duong_dan: str, thuoc_tinh: str | None) -> None:
    rong, alt = _rong_hinh(thuoc_tinh, alt)
    m = _CHU_THICH_HINH.match(alt.strip())
    if m:
        so, noi_dung = int(m.group(1)), m.group(2)
        ctx.hinh.append(so)
        nhan = f"Hình {so}."
    else:
        ctx.canh_bao.append(f"chú thích hình phải bắt đầu bằng 'Hình N.': {alt[:50]!r}")
        nhan, noi_dung = "Hình ?.", alt
    anh = Path(duong_dan) if Path(duong_dan).is_absolute() else ctx.goc / duong_dan
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(4)
    pf.space_after = Pt(0)
    pf.first_line_indent = Pt(0)
    pf.keep_with_next = True  # hình không rời chú thích
    if anh.is_file():
        try:
            p.add_run().add_picture(str(anh), width=Cm(rong))
        except Exception as e:  # noqa: BLE001 — ảnh hỏng thì báo, không sập
            ctx.thieu_hinh.append(f"{duong_dan} (không đọc được: {type(e).__name__})")
            set_font(p.add_run(f"[HÌNH HỎNG: {duong_dan}]"), bold=True)
    else:
        # Thiếu hình phải THẤY được trong bản nháp và CHẶN bản nộp.
        ctx.thieu_hinh.append(duong_dan)
        set_font(p.add_run(f"[THIẾU HÌNH: {duong_dan}]"), bold=True)
    _chu_thich(doc, nhan, noi_dung, giu_voi_doan_sau=False)


def _canh_cot(dong_ke: str) -> list:
    ra = []
    for o in dong_ke.strip().strip("|").split("|"):
        o = o.strip()
        if o.startswith(":") and o.endswith(":"):
            ra.append(WD_ALIGN_PARAGRAPH.CENTER)
        elif o.endswith(":"):
            ra.append(WD_ALIGN_PARAGRAPH.RIGHT)
        else:
            ra.append(None)
    return ra


def render_body(doc, body: str, ctx: NguCanh, co=CO) -> None:
    """Đổ thân một mục. ``co`` = cỡ chữ văn xuôi/danh sách (danh mục tài liệu dùng nhỏ hơn)."""
    lines = body.split("\n")
    i = 0
    chu_thich_bang = None  # (số, nội dung) đang chờ bảng kế tiếp
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        # khối mã / sơ đồ ký tự — giữ liền một khối, không xẻ qua trang
        if stripped.startswith("```"):
            i += 1
            khoi = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                khoi.append(lines[i].rstrip() or " ")
                i += 1
            i += 1
            for k, bl in enumerate(khoi):
                para(
                    doc, bl, mono=True, space_after=0, indent=6, giu_voi_doan_sau=k < len(khoi) - 1
                )
            para(doc, "", space_after=2)
            continue

        m = _HINH.match(stripped)
        if m:
            _them_hinh(doc, ctx, m.group(1), m.group(2), m.group(3))
            i += 1
            continue

        m = _CHU_THICH_BANG.match(stripped)
        if m:
            chu_thich_bang = (int(m.group(1)), m.group(2))
            i += 1
            continue

        if stripped.startswith("|"):
            rows, canh = [], None
            while i < len(lines) and lines[i].strip().startswith("|"):
                cur = lines[i].strip()
                if re.fullmatch(r"[\s|:\-]+", cur):
                    canh = _canh_cot(cur)
                else:
                    rows.append([c.strip() for c in cur.strip("|").split("|")])
                i += 1
            if rows:
                if chu_thich_bang:
                    so, nd = chu_thich_bang
                    ctx.bang.append(so)
                    _chu_thich(doc, f"Bảng {so}.", nd, giu_voi_doan_sau=True, space_after=2)
                    chu_thich_bang = None
                add_table(doc, rows, canh)
                para(doc, "", space_after=2)
            continue

        if chu_thich_bang and stripped:
            ctx.canh_bao.append(
                f"chú thích 'Bảng {chu_thich_bang[0]}.' không đứng ngay trên một bảng"
            )
            chu_thich_bang = None

        if stripped.startswith(">"):
            dong = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                dong.append(lines[i].strip()[1:].strip())
                i += 1
            add_khung(doc, dong)
            para(doc, "", space_after=2)
            continue

        if not stripped:
            i += 1
            continue

        m = re.match(r"^(\s*)[-•]\s+(.*)$", line)
        if m:
            depth = min(len(m.group(1)) // 2, 2)
            rich_para(
                doc, "• " + m.group(2), indent=14 + depth * 14, space_after=2, hanging=True, size=co
            )
            i += 1
            continue

        if re.match(r"^\s*\d+[.)]\s", line):
            rich_para(doc, stripped, indent=14, space_after=2, hanging=True, size=co)
            i += 1
            continue

        rich_para(doc, stripped, size=co)
        i += 1


# ------------------------------------------------------------- cắt và điền mẫu
def _chu_cua(el) -> str:
    return "".join(n.text or "" for n in el.iter(qn("w:t")))


def cat_lay_mau_3(doc):
    """Xoá mọi thứ không thuộc MẪU 3, giữ nguyên sectPr ở cuối."""
    body = doc.element.body
    con = list(body)
    dau = None
    for idx, c in enumerate(con):
        if c.tag == qn("w:p") and "MẪU HỒ SƠ DỰ ÁN DỰ THI BẢNG C" in _chu_cua(c):
            dau = idx
            break
    if dau is None:
        sys.exit("Không tìm thấy MẪU 3 (Bảng C) trong file mẫu của ban tổ chức")
    for c in con[:dau]:
        body.remove(c)
    return dau


def diem_moc_noi_dung(doc):
    """Vị trí đoạn 'NỘI DUNG HỒ SƠ DỰ ÁN' và bảng ký tên cuối mẫu."""
    con = list(doc.element.body)
    moc = None
    for idx, c in enumerate(con):
        if c.tag == qn("w:p") and "NỘI DUNG HỒ SƠ DỰ ÁN" in _chu_cua(c):
            moc = idx
            break
    if moc is None:
        sys.exit("Không tìm thấy mốc 'NỘI DUNG HỒ SƠ DỰ ÁN'")
    ky_ten = None
    for c in con[moc:]:
        if c.tag == qn("w:tbl") and "Đại diện đội thi" in _chu_cua(c):
            ky_ten = c
            break
    return moc, ky_ten


def _bang_thi_sinh(doc):
    return next(
        (t for t in doc.tables if "Số lượng thí sinh" in "".join(c.text for c in t.rows[0].cells)),
        None,
    )


def _o_duy_nhat(row):
    """row.cells lặp lại cùng một ô khi ô gộp; lọc theo phần tử XML."""
    thay, ra = set(), []
    for c in row.cells:
        if id(c._tc) not in thay:
            thay.add(id(c._tc))
            ra.append(c)
    return ra


def tich_o_so_luong(tbl, so: int) -> int:
    """Tích ô "<so> người" ở hàng 'Số lượng thí sinh'. Trả số ô đã tích.

    Lỗi cũ (bản dựng 15/09 và 25/09): ký tự ☐ nằm trong ``w:sdt/w:sdtContent/w:r``
    (điều khiển nội dung do Google Docs sinh), mà ``cell.paragraphs[].runs`` của
    python-docx chỉ thấy run con TRỰC TIẾP của ``w:p`` — nên ô không bao giờ được
    tích. Nay đi qua MỌI ``w:t`` của ô. Nếu điều khiển là hộp kiểm thật của Word
    (``w14:checkbox``) thì đặt cả ``w14:checked`` để Word không vẽ lại ☐.
    """
    for row in tbl.rows:
        o = _o_duy_nhat(row)
        if not o[0].text.strip().lower().startswith("số lượng thí sinh"):
            continue
        da_tich = 0
        for cell in o[1:]:
            tc = cell._tc
            if not re.match(rf"\s*{so}\s*người", _chu_cua(tc)):
                continue
            for sdt in tc.iter(qn("w:sdt")):
                sdt_pr = sdt.find(qn("w:sdtPr"))
                cb = sdt_pr.find(f"{{{W14}}}checkbox") if sdt_pr is not None else None
                if cb is not None:
                    chk = cb.find(f"{{{W14}}}checked")
                    if chk is None:
                        chk = OxmlElement("w14:checked")
                        cb.insert(0, chk)
                    chk.set(f"{{{W14}}}val", "1")
            for t in tc.iter(qn("w:t")):
                if t.text and "☐" in t.text:
                    t.text = t.text.replace("☐", "☒", 1)
                    da_tich += 1
                    break
        return da_tich
    return 0


def dem_o_tich(doc, so: int) -> tuple[int, int]:
    """Đọc lại XML: (số ☒ trong ô "<so> người", tổng số ☒ ở hàng số lượng)."""
    tbl = _bang_thi_sinh(doc)
    if tbl is None:
        return 0, 0
    for row in tbl.rows:
        o = _o_duy_nhat(row)
        if not o[0].text.strip().lower().startswith("số lượng thí sinh"):
            continue
        dung, tong = 0, 0
        for cell in o[1:]:
            chu = _chu_cua(cell._tc)
            n = chu.count("☒")
            tong += n
            if re.match(rf"\s*{so}\s*người", chu):
                dung += n
        return dung, tong
    return 0, 0


def dien_thong_tin_thi_sinh(doc, thanh_vien: list[dict[str, str]]) -> int:
    """Điền bảng thông tin thí sinh của MẪU 3; tích ô số lượng.

    Mẫu là MỘT bảng dọc: hàng đầu là 'Số lượng thí sinh', rồi mỗi thí sinh 6
    hàng nhãn-giá trị. Điền theo NHÃN chứ không theo chỉ số hàng, vì ban tổ
    chức có thể phát hành lại mẫu với số hàng khác.
    """
    tbl = _bang_thi_sinh(doc)
    if tbl is None:
        sys.exit("Không tìm thấy bảng thông tin thí sinh trong MẪU 3")
    tich_o_so_luong(tbl, len(thanh_vien))

    khoa = {
        "họ và tên": "ho_ten",
        "ngày/tháng/năm sinh": "ngay_sinh",
        "lớp hành chính, ngành, khoa, trường": "lop",
        "xã/phường/đặc khu, tỉnh/thành phố": "noi_o",
        "điện thoại": "dien_thoai",
        "email": "email",
    }
    chi_so = -1  # -1 = chưa tới thí sinh nào
    da_dien = 0
    for row in tbl.rows:
        o = _o_duy_nhat(row)
        nhan = re.sub(r"\s+", " ", o[0].text.strip().lower())
        if nhan.startswith("số lượng thí sinh"):
            continue
        if nhan.startswith("thí sinh thứ"):
            chi_so += 1
            continue
        if chi_so < 0 or chi_so >= len(thanh_vien) or len(o) < 2:
            continue
        for k, truong in khoa.items():
            dau = k.split(",")[0]
            if nhan.startswith(dau):
                cell = o[1]
                cell.text = ""
                cp = cell.paragraphs[0]
                cp.paragraph_format.line_spacing = 1.0
                cp.paragraph_format.first_line_indent = Pt(0)
                set_font(cp.add_run(thanh_vien[chi_so][truong]), size=CO_BANG)
                da_dien += 1
                break
    return da_dien


def dat_thuoc_tinh(doc) -> None:
    """Tác giả/tiêu đề của tệp = đội LiveLift, không thừa hưởng 'TuanKhai' của mẫu."""
    cp = doc.core_properties
    now = dt.datetime.now(dt.UTC).replace(microsecond=0, tzinfo=None)
    cp.author = TAC_GIA
    cp.last_modified_by = TAC_GIA
    cp.title = TIEU_DE_TEP
    cp.subject = "Hồ sơ dự án dự thi Bảng C"
    cp.keywords = "LiveLift; switchback; livestream; suy luận nhân quả"
    cp.comments = ""
    cp.category = ""
    cp.created = now
    cp.modified = now
    cp.revision = 1


# ------------------------------------------------------------------ đọc Markdown
def doc_muc(duong_dan: Path) -> list[dict]:
    """Tách Markdown thành [{heading, level, body}].

    Bỏ mọi chú thích ``<!-- … -->`` (kể cả nhiều dòng): ghi chú cho người viết,
    không ra bản nộp.
    """
    secs: list[dict] = []
    cur = None
    trong_chu_thich = False
    for line in duong_dan.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if trong_chu_thich:
            if "-->" in s:
                trong_chu_thich = False
            continue
        if s.startswith("<!--"):
            trong_chu_thich = "-->" not in s
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            cur = {"heading": m.group(2).strip(), "level": len(m.group(1)), "body": []}
            secs.append(cur)
            continue
        if cur is not None:
            cur["body"].append(line)
    for s in secs:
        s["body"] = "\n".join(s["body"]).strip("\n")
    if not secs:
        sys.exit(f"{duong_dan.name} không có mục nào (cần dòng bắt đầu bằng '# ')")
    return secs


def _so_muc(heading: str) -> str | None:
    m = re.match(r"^(\d+(?:\.\d+)*)\.?\s", heading)
    return m.group(1) if m else None


def kiem_dau_vao(thanh_vien, secs, goc: Path, doi: dict) -> list[str]:
    """Mọi lý do CHƯA NỘP ĐƯỢC tìm thấy trước khi dựng (không cần Word)."""
    chan: list[str] = []
    chua_dien = sum(1 for tv in thanh_vien for v in tv.values() if CHO_TRONG in v)
    if chua_dien:
        chan.append(
            f"{chua_dien} ô thông tin thí sinh còn dấu {CHO_TRONG} "
            "(điền docs/competition/thong-tin-doi.local.json)"
        )
    if doi.get("thieu_tep_that"):
        chan.append("chưa có docs/competition/thong-tin-doi.local.json — đang dùng tệp mẫu")
    con_trong = [
        s["heading"][:40] for s in secs if CHO_TRONG in s["body"] or CHO_TRONG in s["heading"]
    ]
    if con_trong:
        chan.append(
            f"{len(con_trong)} mục còn dấu {CHO_TRONG} trong noi-dung.md: " + "; ".join(con_trong)
        )

    # Cấu trúc MẪU 3: đúng 13 mục cấp 1 đánh số 1..13 theo thứ tự; không trùng số mục.
    cap1 = [_so_muc(s["heading"]) for s in secs if s["level"] == 1 and _so_muc(s["heading"])]
    if cap1 != [str(k) for k in range(1, SO_MUC_MAU_3 + 1)]:
        chan.append(f"mục cấp 1 phải là 1..{SO_MUC_MAU_3} đúng thứ tự, đang có: {', '.join(cap1)}")
    so = [_so_muc(s["heading"]) for s in secs if _so_muc(s["heading"])]
    trung = sorted({x for x in so if so.count(x) > 1})
    if trung:
        chan.append("trùng số mục: " + ", ".join(trung))

    # Tham chiếu chéo: "mục X.Y", "Hình N", "Bảng N" phải trỏ tới thứ có thật.
    toan_van = "\n".join(s["body"] for s in secs)
    co_muc = set(so)
    sai_muc = sorted({m for m in re.findall(r"mục (\d+(?:\.\d+)*)", toan_van) if m not in co_muc})
    if sai_muc:
        chan.append("tham chiếu tới mục không tồn tại: " + ", ".join(sai_muc))
    so_hinh = [int(m) for m in re.findall(r"^!\[Hình (\d+)\.", toan_van, re.M)]
    so_bang = [int(m) for m in re.findall(r"^:\s*Bảng (\d+)\.", toan_van, re.M)]
    dong_van = [
        d
        for d in toan_van.splitlines()
        if not _HINH.match(d.strip()) and not _CHU_THICH_BANG.match(d.strip())
    ]
    for ten, ds in (("Hình", so_hinh), ("Bảng", so_bang)):
        if ds != list(range(1, len(ds) + 1)):
            chan.append(f"{ten} phải đánh số liên tiếp 1..n theo thứ tự xuất hiện, đang có: {ds}")
        nhac = {int(m) for d in dong_van for m in re.findall(rf"\b{ten} (\d+)", d)}
        sai = sorted(n for n in nhac if n not in ds)
        if sai:
            chan.append(f"nhắc tới {ten} không tồn tại: {sai}")

    # Hình thiếu tệp
    for _alt, duong_dan in re.findall(r"^!\[(.*?)\]\((.+?)\)", toan_van, re.M):
        anh = Path(duong_dan) if Path(duong_dan).is_absolute() else goc / duong_dan
        if not anh.is_file():
            chan.append(f"thiếu tệp hình: {duong_dan}")
    return chan


def kiem_sau_khi_dung(tep: Path, so_thanh_vien: int) -> list[str]:
    """Đọc lại chính tệp .docx vừa ghi: thứ gì lọt ra bản in thì chặn ở đây."""
    doc = Document(str(tep))
    chan = []
    lot = []
    for t in doc.element.body.iter(qn("w:t")):
        s = t.text or ""
        if "`" in s or "**" in s:
            lot.append(s.strip()[:40])
    if lot:
        chan.append(f"lọt ký tự Markdown vào bản in ({len(lot)} chỗ): " + " | ".join(lot[:3]))
    dung, tong = dem_o_tich(doc, so_thanh_vien)
    if dung != 1 or tong != 1:
        chan.append(
            f"ô '{so_thanh_vien} người' chưa được tích đúng (☒ đúng ô: {dung}, cả hàng: {tong})"
        )
    if doc.core_properties.author != TAC_GIA:
        chan.append(f"tác giả tệp là {doc.core_properties.author!r}, không phải {TAC_GIA!r}")
    return chan


# ------------------------------------------------------------------ Word COM
def xuat_pdf_va_dem_trang(docx: Path):
    """Nhờ Word đếm trang rồi xuất PDF. Trả (số trang, số từ, đường dẫn PDF).

    Vì sao phải là Word: giới hạn 20 trang là giới hạn CỨNG, và chỉ Word mới
    ngắt trang giống thứ ban tổ chức sẽ mở ra. LibreOffice và các thư viện
    Python ngắt khác, lệch một hai trang là chuyện thường.

    Lệnh chạy thẳng qua -Command chứ không qua tệp .ps1: Windows PowerShell 5.1
    đọc tệp .ps1 theo bảng mã ANSI nếu tệp không có BOM, nên mọi chú thích
    tiếng Việt trong .ps1 làm hỏng bộ phân tích cú pháp. Đã dính một lần rồi.
    """
    pdf = docx.with_suffix(".pdf")
    d_ps = str(docx).replace("'", "''")
    p_ps = str(pdf).replace("'", "''")
    ps = (
        "$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
        "$w.DisplayAlerts = 0; "
        f"$d = $w.Documents.Open('{d_ps}', $false, $true); $d.Repaginate(); "
        "$t = $d.ComputeStatistics(2); $u = $d.ComputeStatistics(0); "
        f"$d.SaveAs([ref]'{p_ps}', [ref]17); $d.Close($false); $w.Quit(); "
        'Write-Output "$t $u"'
    )
    try:
        # noqa S603/S607: lệnh dựng từ hằng số trong tệp này cộng đường dẫn
        # tệp do chính script sinh ra — không có đầu vào từ người dùng.
        out = subprocess.run(  # noqa: S603
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=240,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"  Không đếm trang được ({e}) — mở Word xem thanh trạng thái")
        return None, None, None
    so = out.stdout.split()
    if len(so) < 2 or not so[0].isdigit() or not pdf.exists():
        print("  Không đếm trang được. Word có đang mở chính tệp này không?")
        if out.stderr.strip():
            print("  ", out.stderr.strip().splitlines()[0])
        return None, None, None
    return int(so[0]), int(so[1]), pdf


# ------------------------------------------------------------------ dựng toàn bộ
def dung(secs, thanh_vien, goc: Path):
    """Dựng Document từ mẫu + nội dung. Trả (doc, ngữ cảnh, số ô thí sinh đã điền)."""
    if not MAU.exists():
        sys.exit(f"Không thấy file mẫu của ban tổ chức: {MAU}")
    doc = Document(str(MAU))
    cat_lay_mau_3(doc)
    so_o = dien_thong_tin_thi_sinh(doc, thanh_vien)

    moc, ky_ten = diem_moc_noi_dung(doc)
    body = doc.element.body
    # Tiêu đề "NỘI DUNG HỒ SƠ DỰ ÁN" không được nằm một mình ở đáy trang 1.
    Paragraph(list(body)[moc], doc._body).paragraph_format.keep_with_next = True
    if ky_ten is not None:
        body.remove(ky_ten)  # đặt lại ở cuối sau khi đổ nội dung
    for c in list(body)[moc + 1 :]:
        if c.tag != qn("w:sectPr"):
            body.remove(c)

    ctx = NguCanh(goc=goc)
    for s in secs:
        lv = s.get("level", 1)
        para(
            doc,
            s["heading"],
            bold=True,
            size=Pt(13.5) if lv == 1 else Pt(13),
            italic=(lv >= 3),
            space_before=9 if lv == 1 else 6,
            space_after=3,
            giu_voi_doan_sau=True,
        )
        # Danh mục tài liệu tham khảo in cỡ 11 như chú thích — tiết kiệm ~0,2 trang
        # mà vẫn trên ngưỡng đọc được khi in.
        la_tltk = s["heading"].strip().lower().startswith("tài liệu tham khảo")
        render_body(doc, s["body"], ctx, co=CO_TLTK if la_tltk else CO)

    if ky_ten is not None:
        para(doc, "", space_before=8, space_after=0)
        sect = body.find(qn("w:sectPr"))
        if sect is not None:
            sect.addprevious(ky_ten)
        else:
            body.append(ky_ten)
    dat_thuoc_tinh(doc)
    return doc, ctx, so_o


def _doc_doi(duong_dan: str | None) -> dict:
    if duong_dan:
        d = json.loads(Path(duong_dan).read_text(encoding="utf-8"))
        d["thieu_tep_that"] = False
        return d
    return thong_tin_doi.doc()


def _xoa(*tep):
    for t in tep:
        if t is not None and Path(t).exists():
            Path(t).unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Dựng hồ sơ dự án Bảng C (MẪU 3) từ noi-dung.md")
    ap.add_argument("--out-dir", default=str(OUT_DIR_MAC_DINH), help="thư mục ghi .docx/.pdf")
    ap.add_argument(
        "--cho-phep-o-trong",
        action="store_true",
        help="dựng BẢN NHÁP (hậu tố _NHAP) dù còn ô ⬜ hoặc thiếu hình",
    )
    ap.add_argument("--khong-pdf", action="store_true", help="bỏ bước Word (không đếm trang)")
    ap.add_argument("--noi-dung", default=str(NOI_DUNG), help=argparse.SUPPRESS)
    ap.add_argument("--thong-tin", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--tu-kiem", action="store_true", help="tự kiểm bộ dựng rồi thoát")
    args = ap.parse_args(argv)
    if args.tu_kiem:
        return tu_kiem()

    out_dir = Path(args.out_dir)
    noi_dung = Path(args.noi_dung).resolve()
    doi = _doc_doi(args.thong_tin)
    thanh_vien = thanh_vien_tu(doi)
    secs = doc_muc(noi_dung)

    chan = kiem_dau_vao(thanh_vien, secs, noi_dung.parent, doi)
    if chan and not args.cho_phep_o_trong:
        print("CHƯA NỘP ĐƯỢC — không tạo và không ghi đè tệp nào:")
        for c in chan:
            print("   -", c)
        print("  (dựng bản nháp: thêm --cho-phep-o-trong)")
        return 1

    doc, ctx, so_o = dung(secs, thanh_vien, noi_dung.parent)
    for c in ctx.canh_bao:
        chan.append(c)
    if so_o < 6 * len(thanh_vien):
        chan.append(f"chỉ điền được {so_o}/{6 * len(thanh_vien)} ô thí sinh — mẫu BTC đổi nhãn?")

    out_dir.mkdir(parents=True, exist_ok=True)
    tam = out_dir / f"{TEN_TEP}.tam-{os.getpid()}.docx"
    doc.save(str(tam))
    chan += kiem_sau_khi_dung(tam, len(thanh_vien))

    trang = tu = pdf_tam = None
    # Word có thể đã ghi PDF tạm rồi mới hỏng ở bước đọc số trang; khi đó
    # xuat_pdf_va_dem_trang trả None nên phải dọn theo tên dự kiến.
    pdf_tam_du_kien = tam.with_suffix(".pdf")
    if args.khong_pdf:
        chan.append("chưa đếm trang (chạy với --khong-pdf)")
    else:
        trang, tu, pdf_tam = xuat_pdf_va_dem_trang(tam)
        if trang is None:
            chan.append("Word không đếm được trang")
        elif trang > GIOI_HAN_TRANG:
            chan.append(f"VƯỢT GIỚI HẠN: {trang}/{GIOI_HAN_TRANG} trang — phải cắt bớt")

    print(
        f"  {len(secs)} mục · {len(doc.paragraphs)} đoạn · {len(doc.tables)} bảng · "
        f"{len(ctx.hinh)} hình · {len(ctx.bang)} bảng có chú thích · {so_o} ô thí sinh"
    )
    if trang is not None:
        print(f"  {trang}/{GIOI_HAN_TRANG} trang · {tu} từ (Word đếm)")
    for h in ctx.thieu_hinh:
        print(f"  THIẾU HÌNH: {h}")

    if not chan:
        dich = out_dir / f"{TEN_TEP}.docx"
        os.replace(tam, dich)
        os.replace(pdf_tam, dich.with_suffix(".pdf"))
        print("Đã ghi:", dich, "và", dich.with_suffix(".pdf"))
        print("  Sẵn sàng nộp.")
        return 0

    print("  CHƯA NỘP ĐƯỢC:")
    for c in chan:
        print("   -", c)
    if not args.cho_phep_o_trong:
        _xoa(tam, pdf_tam, pdf_tam_du_kien)
        print("  Giữ nguyên bản cũ — không ghi đè .docx/.pdf nào.")
        return 1
    dich = out_dir / f"{TEN_TEP}{HAU_TO_NHAP}.docx"
    os.replace(tam, dich)
    if pdf_tam is not None:
        os.replace(pdf_tam, dich.with_suffix(".pdf"))
    else:
        # PDF nháp của lần dựng trước không còn khớp .docx nháp vừa ghi.
        _xoa(pdf_tam_du_kien, dich.with_suffix(".pdf"))
    print("BẢN NHÁP:", dich, "(không phải bản nộp)")
    vuot = trang is not None and trang > GIOI_HAN_TRANG
    return 1 if vuot or (trang is None and not args.khong_pdf) else 0


# ------------------------------------------------------------------ tự kiểm
def _png_1x1() -> bytes:
    """Một ảnh PNG 1×1 hợp lệ, tự sinh — để tự kiểm không phụ thuộc tệp hình nào."""
    import struct
    import zlib

    def khoi(loai: bytes, du_lieu: bytes) -> bytes:
        return (
            struct.pack(">I", len(du_lieu))
            + loai
            + du_lieu
            + struct.pack(">I", zlib.crc32(loai + du_lieu) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + khoi(b"IHDR", ihdr)
        + khoi(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
        + khoi(b"IEND", b"")
    )


def tu_kiem() -> int:
    """Nghiệm thu bộ dựng trên dữ liệu tổng hợp — không cần Word, không đọc dữ liệu đội.

    Mỗi kiểm tra ứng với một lỗi thật đã gặp (kiểm toán hồ sơ 25/09/2026).
    """
    if not MAU.exists():
        print(f"BỎ QUA: không có file mẫu BTC ({MAU})")
        return 0
    loi = 0

    def kq(ten, dat, chi_tiet=""):
        nonlocal loi
        loi += 0 if dat else 1
        print(f"  [{'ĐẠT' if dat else 'HỎNG'}] {ten}{(' — ' + chi_tiet) if chi_tiet else ''}")

    tv = {
        "ho_ten": "Nguyễn Văn A",
        "ngay_sinh": "01/01/2006",
        "mssv": "000",
        "lop_hanh_chinh": "24050301",
        "nganh": "Công nghệ thông tin",
        "khoa": "Công nghệ thông tin",
        "truong": "Đại học Tôn Đức Thắng",
        "noi_o": "Phường X, TP. Hồ Chí Minh",
        "dien_thoai": "0000000000",
        "email": "a@example.com",
    }
    doi = {"thanh_vien": [dict(tv), dict(tv), dict(tv)]}
    md = "\n".join(
        [
            "<!-- chú thích\nnhiều dòng -->",
            "# Tóm tắt dự án",
            "> Dòng tóm tắt có `mã` và **đậm `mã trong đậm`**.",
            *[f"# {k}. Mục {k}\n\nĐoạn văn mục {k}, xem mục 1." for k in range(1, 14)],
            ": Bảng 1. Bảng thử",
            "| A | B |",
            "|---|---:|",
            "| **`x`** | 1 |",
            "",
            "Như Hình 1 cho thấy.",
            "![Hình 1. Hình thử](khong-ton-tai.png){width=12cm}",
        ]
    )
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "nd.md").write_text(md, encoding="utf-8")
        (td / "doi.json").write_text(json.dumps(doi, ensure_ascii=False), encoding="utf-8")

        # (1) Tích ô "3 người" nằm trong w:sdt — đọc lại XML sau khi lưu.
        secs = doc_muc(td / "nd.md")
        doc, ctx, so_o = dung(secs, thanh_vien_tu(doi), td)
        doc.save(str(td / "a.docx"))
        dung_o, tong = dem_o_tich(Document(str(td / "a.docx")), 3)
        kq(
            "tích đúng một ô '3 người' (ký tự trong w:sdt)",
            dung_o == 1 and tong == 1,
            f"{dung_o}/{tong}",
        )
        kq("điền đủ 18 ô thí sinh, có 'Lớp …'", so_o == 18, str(so_o))

        # (2) Không lọt dấu backtick / ** vào bản in; mã là run Consolas.
        lot = kiem_sau_khi_dung(td / "a.docx", 3)
        kq("không lọt ký tự Markdown, tác giả = đội", not lot, "; ".join(lot))
        font_ma = {}  # chữ của run → font, kể cả run trong ô bảng và khung tóm tắt
        for r in Document(str(td / "a.docx")).element.body.iter(qn("w:r")):
            chu = "".join(t.text or "" for t in r.iter(qn("w:t")))
            rf = r.find(f"{qn('w:rPr')}/{qn('w:rFonts')}")
            if chu in ("mã", "mã trong đậm", "x"):
                font_ma[chu] = rf.get(qn("w:ascii")) if rf is not None else None
        kq(
            "chữ mã (cả trong đậm, trong ô bảng) là Consolas",
            len(font_ma) == 3 and set(font_ma.values()) == {FONT_MA},
            str(font_ma),
        )
        kq("thiếu hình được ghi nhận, không sập", ctx.thieu_hinh == ["khong-ton-tai.png"])

        # (3) Còn ⬜ → mã 1, KHÔNG đụng bản nộp cũ.
        doi_o = {"thanh_vien": [dict(tv, noi_o="⬜"), dict(tv), dict(tv)]}
        (td / "doi_o.json").write_text(json.dumps(doi_o, ensure_ascii=False), encoding="utf-8")
        cu = td / "ra"
        cu.mkdir()
        for duoi in (".docx", ".pdf"):
            (cu / f"{TEN_TEP}{duoi}").write_bytes(b"BAN-CU")
        truoc = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in cu.iterdir()}
        ma_thoat = main(
            [
                "--out-dir",
                str(cu),
                "--noi-dung",
                str(td / "nd.md"),
                "--thong-tin",
                str(td / "doi_o.json"),
            ]
        )
        sau = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in cu.iterdir()}
        kq("còn ⬜ → thoát mã 1, bản cũ nguyên vẹn", ma_thoat == 1 and truoc == sau)

        # (4) Bản nháp: ra tệp _NHAP, vẫn không đụng bản nộp.
        ma_thoat = main(
            [
                "--out-dir",
                str(cu),
                "--noi-dung",
                str(td / "nd.md"),
                "--thong-tin",
                str(td / "doi_o.json"),
                "--cho-phep-o-trong",
                "--khong-pdf",
            ]
        )
        sau = {
            p.name: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in cu.iterdir()
            if "NHAP" not in p.name
        }
        kq(
            "bản nháp ra _NHAP, bản nộp nguyên vẹn, không sót tệp tạm",
            ma_thoat == 0
            and (cu / f"{TEN_TEP}{HAU_TO_NHAP}.docx").exists()
            and truoc == sau
            and not list(cu.glob("*.tam-*")),
        )

        # (5) Trùng số mục và tham chiếu sai bị chặn trước khi dựng.
        (td / "sai.md").write_text(
            md.replace("# 9. Mục 9", "# 8. Mục 9") + "\nxem mục 42, Hình 9 và Bảng 7.",
            encoding="utf-8",
        )
        chan = kiem_dau_vao(thanh_vien_tu(doi), doc_muc(td / "sai.md"), td, {})
        kq(
            "chặn trùng số mục và tham chiếu tới mục, Hình, Bảng không có",
            any("trùng số mục" in c for c in chan)
            and any("42" in c for c in chan)
            and any("Hình không tồn tại: [9]" in c for c in chan)
            and any("Bảng không tồn tại: [7]" in c for c in chan),
            "; ".join(chan),
        )
        # Lỗi 25/09: một lần sửa qua heredoc biến "\b" của regex thành ký tự 0x08,
        # tắt âm thầm kiểm tra "nhắc tới Hình/Bảng". Chặn mọi ký tự điều khiển.
        dieu_khien = [
            i
            for i, ch in enumerate(Path(__file__).read_text(encoding="utf-8"))
            if ord(ch) < 32 and ch not in "\n\t"
        ]
        kq("mã bộ dựng không chứa ký tự điều khiển lạ", not dieu_khien, str(dieu_khien[:3]))

        # (6) Hình có thật: ảnh nhúng + chú thích "Hình 1." NGAY dưới, cùng khối trang;
        #     bảng có chú thích "Bảng 1." dính với bảng, hàng tiêu đề tô nền; tiêu đề
        #     và khối mã không mồ côi (keep_with_next).
        (td / "a.png").write_bytes(_png_1x1())
        md6 = "\n".join(
            [
                "# 1. Mục một",
                "Đoạn dẫn, xem Hình 1 và Bảng 1.",
                "![Hình 1. Hình có thật](a.png){width=4cm}",
                ": Bảng 1. Bảng có chú thích",
                "| Cột A | Cột B |",
                "|---|---|",
                "| x | y |",
                "```",
                "dòng mã 1",
                "dòng mã 2",
                "```",
                *[f"# {k}. Mục {k}\n\nĐoạn {k}." for k in range(2, 14)],
            ]
        )
        (td / "hinh.md").write_text(md6, encoding="utf-8")
        secs6 = doc_muc(td / "hinh.md")
        chan6 = kiem_dau_vao(thanh_vien_tu(doi), secs6, td, {})
        doc6, ctx6, _ = dung(secs6, thanh_vien_tu(doi), td)
        doc6.save(str(td / "h.docx"))
        d6 = Document(str(td / "h.docx"))
        ps = d6.paragraphs
        # Mẫu BTC có sẵn ảnh (quốc hiệu/logo) ở trang 1 — tìm từ CHÚ THÍCH ngược lên.
        i_cap = next((i for i, p in enumerate(ps) if p.text.startswith("Hình 1.")), None)
        i_anh = i_cap - 1 if i_cap else None
        co_anh = i_anh is not None and bool(ps[i_anh]._p.xpath(".//pic:pic"))
        kq(
            "hình có thật được nhúng, chú thích 'Hình 1.' ngay dưới, ảnh dính chú thích",
            co_anh and bool(ps[i_anh].paragraph_format.keep_with_next) and ctx6.hinh == [1],
            f"vị trí ảnh {i_anh}, cảnh báo đầu vào: {chan6}",
        )
        cap_bang = next((p for p in ps if p.text.startswith("Bảng 1.")), None)
        bang = next((t for t in d6.tables if t.rows[0].cells[0].text == "Cột A"), None)
        nen = None
        if bang is not None:
            shd = bang.rows[0].cells[0]._tc.find(f"{qn('w:tcPr')}/{qn('w:shd')}")
            nen = shd.get(qn("w:fill")) if shd is not None else None
        kq(
            "chú thích 'Bảng 1.' dính bảng; hàng tiêu đề tô nền",
            cap_bang is not None
            and bool(cap_bang.paragraph_format.keep_with_next)
            and nen == NEN_TIEU_DE_BANG,
            f"nền {nen}",
        )
        tieu_de = next(p for p in ps if p.text == "1. Mục một")
        ma = [p for p in ps if p.text.startswith("dòng mã")]
        moc = next(p for p in ps if "NỘI DUNG HỒ SƠ DỰ ÁN" in p.text)
        kq(
            "tiêu đề, dòng mã (trừ dòng cuối) và 'NỘI DUNG HỒ SƠ DỰ ÁN' giữ với đoạn sau",
            bool(tieu_de.paragraph_format.keep_with_next)
            and bool(ma[0].paragraph_format.keep_with_next)
            and not ma[-1].paragraph_format.keep_with_next
            and bool(moc.paragraph_format.keep_with_next),
        )

        # (7) Word đã ghi PDF tạm rồi mới hỏng (không đọc được số trang): thoát mã 1,
        #     KHÔNG sót ``*.tam-*.pdf`` trong thư mục nộp (phản biện 25/09/2026).
        # (8) Bản nháp dựng lại với --khong-pdf: xoá PDF nháp CŨ, để .docx và .pdf
        #     nháp không bao giờ là hai phiên bản khác nhau.
        goc_word = globals()["xuat_pdf_va_dem_trang"]

        def word_hong(docx: Path):
            docx.with_suffix(".pdf").write_bytes(b"PDF-TAM")
            return None, None, None

        globals()["xuat_pdf_va_dem_trang"] = word_hong
        try:
            ra7 = td / "ra7"
            ra7.mkdir()
            doi_du = ["--noi-dung", str(td / "hinh.md"), "--thong-tin", str(td / "doi.json")]
            ma7 = main(["--out-dir", str(ra7), *doi_du])
        finally:
            globals()["xuat_pdf_va_dem_trang"] = goc_word
        kq(
            "Word hỏng sau khi ghi PDF tạm → thoát 1, không sót tệp tạm",
            ma7 == 1 and not list(ra7.iterdir()),
            str(sorted(p.name for p in ra7.iterdir())),
        )
        nhap_pdf = ra7 / f"{TEN_TEP}{HAU_TO_NHAP}.pdf"
        nhap_pdf.write_bytes(b"PDF-NHAP-CU")
        main(["--out-dir", str(ra7), *doi_du, "--cho-phep-o-trong", "--khong-pdf"])
        kq(
            "bản nháp --khong-pdf xoá PDF nháp cũ (không để .docx/.pdf lệch nhau)",
            not nhap_pdf.exists() and (ra7 / f"{TEN_TEP}{HAU_TO_NHAP}.docx").exists(),
        )
    print("TỰ KIỂM:", "ĐẠT" if not loi else f"{loi} HỎNG")
    return 0 if not loi else 1


if __name__ == "__main__":
    # Bảng mã cp1252 của console Windows không in được tiếng Việt.
    for _luong in (sys.stdout, sys.stderr):
        if hasattr(_luong, "reconfigure"):
            _luong.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
