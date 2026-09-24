"""Bộ đọc Markdown tối giản cho bản kê khai — chỉ thư viện chuẩn, không phụ thuộc Word.

Tách riêng khỏi ``dung_ke_khai.py`` để kiểm thử được bằng venv chính (không cần
python-docx). Hỗ trợ đúng phần Markdown mà ``05-BAN-KE-KHAI.md`` dùng:

- tiêu đề ``#``, ``##``, ``###``; đoạn văn; dòng kẻ ``---``
- danh sách gạch đầu dòng ``- `` (thụt 2 dấu cách = cấp 2) và đánh số ``1. ``
- bảng ``| a | b |`` với dòng căn cột ``|---|:--:|---:|``; ``\\|`` là dấu gạch đứng trong ô
- khối trích ``> ``; khối mã ```` ``` ````
- chỉ thị dạng chú thích HTML: ``<!-- QUOC-HIEU -->``, ``<!-- BANG-KY -->``,
  ``<!-- NGAT-TRANG -->`` (trình xem Markdown bỏ qua, bộ dựng Word dùng)

Định dạng trong dòng: ``**đậm**``, ``*nghiêng*``, `` `mã` ``, ``[chữ](liên-kết)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Khoi:
    loai: str  # tieu_de | doan | ds_cham | ds_so | bang | ma | trich | ke | chi_thi
    cap: int = 0
    chu: str = ""
    muc: list = field(default_factory=list)  # ds: [(cap, chu)]; bang: [[ô]]
    canh: list = field(default_factory=list)  # bang: "trai" | "giua" | "phai"


_CHI_THI = re.compile(r"^<!--\s*([A-Z0-9\-]+)\s*-->$")
_DS_CHAM = re.compile(r"^(\s*)[-*] (.*)$")
_DS_SO = re.compile(r"^(\s*)(\d+)[.)] (.*)$")
_DONG_KE_BANG = re.compile(r"^\|?[\s:|\-]+\|?$")


def _o_bang(dong: str) -> list[str]:
    dong = dong.strip()
    if dong.startswith("|"):
        dong = dong[1:]
    if dong.endswith("|") and not dong.endswith("\\|"):
        dong = dong[:-1]
    tam = dong.replace("\\|", "\x00")
    return [o.strip().replace("\x00", "|") for o in tam.split("|")]


def _canh(dong: str) -> list[str]:
    ra = []
    for o in _o_bang(dong):
        o = o.strip()
        if o.startswith(":") and o.endswith(":"):
            ra.append("giua")
        elif o.endswith(":"):
            ra.append("phai")
        else:
            ra.append("trai")
    return ra


def phan_tich(md: str) -> list[Khoi]:
    dong = md.replace("\r\n", "\n").split("\n")
    ra: list[Khoi] = []
    i = 0
    doan: list[str] = []

    def xa_doan() -> None:
        if doan:
            ra.append(Khoi("doan", chu=" ".join(s.strip() for s in doan)))
            doan.clear()

    while i < len(dong):
        d = dong[i]
        s = d.strip()
        if not s:
            xa_doan()
            i += 1
            continue
        m = _CHI_THI.match(s)
        if m:
            xa_doan()
            ra.append(Khoi("chi_thi", chu=m.group(1)))
            i += 1
            continue
        if s.startswith("<!--"):  # chú thích thường: bỏ qua tới -->
            xa_doan()
            while i < len(dong) and "-->" not in dong[i]:
                i += 1
            i += 1
            continue
        if s.startswith("```"):
            xa_doan()
            i += 1
            ma = []
            while i < len(dong) and not dong[i].strip().startswith("```"):
                ma.append(dong[i].rstrip())
                i += 1
            i += 1
            ra.append(Khoi("ma", muc=ma))
            continue
        m = re.match(r"^(#{1,4}) (.*)$", s)
        if m:
            xa_doan()
            ra.append(Khoi("tieu_de", cap=len(m.group(1)), chu=m.group(2).strip()))
            i += 1
            continue
        if re.fullmatch(r"-{3,}|\*{3,}", s):
            xa_doan()
            ra.append(Khoi("ke"))
            i += 1
            continue
        if s.startswith("|"):
            xa_doan()
            hang, canh = [], []
            while i < len(dong) and dong[i].strip().startswith("|"):
                cur = dong[i].strip()
                if _DONG_KE_BANG.fullmatch(cur) and "-" in cur:
                    canh = _canh(cur)
                else:
                    hang.append(_o_bang(cur))
                i += 1
            ra.append(Khoi("bang", muc=hang, canh=canh))
            continue
        if s.startswith(">"):
            xa_doan()
            trich = []
            while i < len(dong) and dong[i].strip().startswith(">"):
                trich.append(dong[i].strip()[1:].strip())
                i += 1
            ra.append(Khoi("trich", chu=" ".join(t for t in trich if t)))
            continue
        m_c, m_s = _DS_CHAM.match(d), _DS_SO.match(d)
        if m_c or m_s:
            xa_doan()
            loai = "ds_cham" if m_c else "ds_so"
            muc: list[tuple[int, str]] = []
            while i < len(dong):
                dd = dong[i]
                mc, ms = _DS_CHAM.match(dd), _DS_SO.match(dd)
                m2 = mc if loai == "ds_cham" else ms
                if m2 is None:
                    # dòng tiếp nối của mục trước (thụt vào, không phải mục mới)
                    la_muc = mc is not None or ms is not None
                    if not la_muc and dd.startswith("  ") and dd.strip() and muc:
                        cap, chu = muc[-1]
                        muc[-1] = (cap, chu + " " + dd.strip())
                        i += 1
                        continue
                    break  # dòng trống, đoạn mới hoặc danh sách khác loại
                thut = len(m2.group(1))
                chu = m2.group(2) if loai == "ds_cham" else m2.group(3)
                muc.append((1 if thut >= 2 else 0, chu.strip()))
                i += 1
            ra.append(Khoi(loai, muc=muc))
            continue
        doan.append(d)
        i += 1
    xa_doan()
    return ra


# ------------------------------------------------------------------ trong dòng
_TRONG_DONG = re.compile(r"(`[^`\n]+`|\*\*.+?\*\*|\*[^*\n]+?\*|\[[^\]\n]+\]\([^)\s]+\))")


@dataclass(frozen=True)
class Doan:
    chu: str
    dam: bool = False
    nghieng: bool = False
    ma: bool = False


def tach_trong_dong(chu: str, *, dam: bool = False, nghieng: bool = False) -> list[Doan]:
    """Dịch **đậm**, *nghiêng*, `mã`, [chữ](link) thành các đoạn có định dạng — kể cả lồng nhau."""
    ra: list[Doan] = []
    for phan in _TRONG_DONG.split(chu):
        if not phan:
            continue
        if phan.startswith("`") and phan.endswith("`") and len(phan) > 2:
            ra.append(Doan(phan[1:-1], dam=dam, nghieng=nghieng, ma=True))
        elif phan.startswith("**") and phan.endswith("**") and len(phan) > 4:
            ra.extend(tach_trong_dong(phan[2:-2], dam=True, nghieng=nghieng))
        elif phan.startswith("*") and phan.endswith("*") and len(phan) > 2:
            ra.extend(tach_trong_dong(phan[1:-1], dam=dam, nghieng=True))
        elif phan.startswith("[") and "](" in phan and phan.endswith(")"):
            nhan, lk = phan[1:].split("](", 1)
            lk = lk[:-1]
            ra.extend(tach_trong_dong(nhan, dam=dam, nghieng=nghieng))
            if lk.startswith("http") and lk not in nhan:
                ra.append(Doan(f" ({lk})", dam=dam, nghieng=nghieng))
        else:
            ra.append(Doan(phan, dam=dam, nghieng=nghieng))
    return ra


def chu_tron(chu: str) -> str:
    """Chữ thuần sau khi bỏ định dạng — để kiểm không còn ký hiệu Markdown lọt ra."""
    return "".join(d.chu for d in tach_trong_dong(chu))
