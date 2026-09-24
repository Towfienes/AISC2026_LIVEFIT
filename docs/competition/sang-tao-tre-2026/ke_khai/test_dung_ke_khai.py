"""Bộ dựng bản kê khai: đọc Markdown đúng, không lọt ký hiệu, nội dung đủ mục và trung thực.

Chạy (tại thư mục kho mã)::

    .venv/Scripts/python -m pytest docs/competition/sang-tao-tre-2026/ke_khai -q

Phần dựng .docx chỉ chạy khi môi trường có python-docx (``.venv-docx``); còn lại chỉ cần
thư viện chuẩn.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

DAY = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY))
import doc_md  # noqa: E402
import dung_ke_khai  # noqa: E402

NGUON = DAY.parent / "05-BAN-KE-KHAI.md"


def test_phan_tich_tieu_de_bang_danh_sach_chi_thi():
    md = "\n".join(
        [
            "<!-- QUOC-HIEU -->",
            "# Tiêu đề",
            "",
            "Đoạn một dòng một",
            "dòng hai.",
            "",
            "| A | B có \\| gạch | C |",
            "|---|:---:|---:|",
            "| 1 | **đậm** | `mã` |",
            "",
            "- mục một",
            "  tiếp nối",
            "  - mục con",
            "1. số một",
            "",
            "```",
            "lệnh",
            "```",
        ]
    )
    k = doc_md.phan_tich(md)
    loai = [x.loai for x in k]
    assert loai == ["chi_thi", "tieu_de", "doan", "bang", "ds_cham", "ds_so", "ma"]
    assert k[2].chu == "Đoạn một dòng một dòng hai."
    assert k[3].muc[0] == ["A", "B có | gạch", "C"]
    assert k[3].canh == ["trai", "giua", "phai"]
    assert k[4].muc == [(0, "mục một tiếp nối"), (1, "mục con")]
    assert k[6].muc == ["lệnh"]


def test_dinh_dang_long_nhau_khong_lot_ky_hieu():
    doan = doc_md.tach_trong_dong("**đậm có `mã` trong** và *nghiêng* [kho](https://x.y/z)")
    chu = "".join(d.chu for d in doan)
    assert "`" not in chu
    assert "*" not in chu
    assert "](" not in chu
    assert "https://x.y/z" in chu
    assert any(d.ma and d.dam for d in doan)


def test_kiem_md_bat_o_trong_va_so_cho_dien():
    k = doc_md.phan_tich("Số: ⟦CHUA_DIEN⟧\n\nÔ: ⬜")
    loi = dung_ke_khai.kiem_md(k)
    assert len(loi) == 2


def _nguon() -> str:
    return NGUON.read_text(encoding="utf-8")


def test_ban_ke_khai_that_sach_va_du_muc():
    md = _nguon()
    assert dung_ke_khai.kiem_md(doc_md.phan_tich(md)) == []
    for muc in (
        "## I.",
        "## II.",
        "## III.",
        "## IV.",
        "## V.",
        "## VI.",
        "## VII.",
        "## VIII.",
        "## IX.",
        "## X.",
    ):
        assert muc in md, muc
    for cong_cu in ("Claude Code", "Google Antigravity", "OpenAI Codex", "GitHub Copilot"):
        assert cong_cu in md, cong_cu
    for luat in ("91/2025/QH15", "356/2025/NĐ-CP", "134/2025/QH15"):
        assert luat in md, luat


def test_bang_ky_co_du_ba_thanh_vien():
    k = doc_md.phan_tich(_nguon())
    i = next(j for j, x in enumerate(k) if x.loai == "chi_thi" and x.chu == "BANG-KY")
    bang = next(x for x in k[i:] if x.loai == "bang")
    ten = [h[0] for h in bang.muc[1:]]
    assert ten == ["Ngô Bình Minh", "Lê Xuân Khánh", "Ngô Lâm Tiến"]
    assert all(h[-1] == "" for h in bang.muc[1:]), "cột chữ ký phải để trống để ký tay"


def test_khang_dinh_sai_cu_chi_con_trong_muc_dinh_chinh():
    md = _nguon()
    dau = md.index("## Đính chính")
    cuoi = md.index("## I.")
    for cum in ("1.297", "0,271", "4,5%", "tự viết", "gán tay", "lợi ích chính đáng"):
        for m in re.finditer(re.escape(cum), md):
            assert dau <= m.start() < cuoi, f"{cum!r} xuất hiện ngoài mục đính chính"
    can_cu = md.index("## Căn cứ")
    for m in re.finditer("13/2023", md):
        assert can_cu <= m.start() < cuoi, "Nghị định 13/2023 chỉ được nhắc là đã bị thay"


def test_dung_docx_khong_lot_ky_hieu(tmp_path):
    pytest.importorskip("docx")
    ra = tmp_path / "ke-khai.docx"
    dung_ke_khai.dung_docx(doc_md.phan_tich(_nguon()), ra)
    assert dung_ke_khai.kiem_docx(ra) == []
