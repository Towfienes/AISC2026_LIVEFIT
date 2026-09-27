"""Bộ dựng bản kê khai: đọc Markdown đúng, không lọt ký hiệu, nội dung đủ mục và trung thực.

Chạy (tại thư mục kho mã)::

    .venv/Scripts/python -m pytest docs/competition/sang-tao-tre-2026/ke_khai -q

``pytest`` mặc định (``testpaths = ["tests"]``, cả CI) thu thập bộ này qua cầu nối
``tests/test_dung_ke_khai.py`` (25/09/2026) — đổi tên/chuyển tệp này thì sửa cả cầu nối.

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
    # Số Prompt Log (phần việc 3, tối 25/09/2026): kê khai và hồ sơ mục 13 ghi 78 câu / 567 nhật
    # ký trong khi bản xuất trên đĩa đã là 83 / 598 — không gì so hai bên. dung_goi_drive.py
    # trích MỌI chỗ ghi số và so với SO-DEM.json của lần xuất; ở đây: các chỗ ghi phải khớp nhau,
    # mỗi khoá quan trọng phải trích được, và lệch một số thì bị báo ở cả hai tệp.
    import dung_goi_drive as goi

    ho_so = (DAY.parent / "noi-dung.md").read_text(encoding="utf-8")
    trich = goi.trich_so_prompt_log(md)
    for khoa in ("cau_lenh_nguoi", "lenh_gach_cheo", "goi_cong_cu", "tac_tu_con", "so_phien"):
        assert khoa in trich, f"kê khai không còn chỗ ghi {khoa} mà bộ so trích được"
    so_phien = trich["so_phien"][0]
    assert sum(k.endswith(":cau_lenh_nguoi") for k in trich) == so_phien, "bảng I.3 thiếu phiên"
    kv = {khoa: cac_so[0] for khoa, cac_so in trich.items()}
    van_ban = [("05-BAN-KE-KHAI.md", md), ("noi-dung.md", ho_so)]
    assert goi.lech_so_prompt_log(kv, van_ban) == []
    # Phần việc 2 (wf6): 06-KHO-MA-VA-MINH-CHUNG.md còn 78 / 567 khi hai tệp kia đã là 83 / 598 —
    # cổng của dung_goi_drive.py phải quét cả 06, và 06 phải khớp hai tệp kia.
    assert DAY.parent / "06-KHO-MA-VA-MINH-CHUNG.md" in goi.TEP_SO_PROMPT_LOG
    tat_ca = [(p.name, p.read_text(encoding="utf-8")) for p in goi.TEP_SO_PROMPT_LOG]
    assert goi.lech_so_prompt_log(kv, tat_ca) == []
    # Khoá của bộ trích và của SO-DEM.json phải là một: SO-DEM tối thiểu dựng từ chính bảng I.3.
    so_dem = {
        "tong": {
            **{k: kv[k] for k in goi._COT_PHIEN},
            "so_phien_chinh": so_phien,
            "so_kich_ban_dieu_phoi": kv["kich_ban_dieu_phoi"],
            "mo_hinh": {k[8:]: v for k, v in kv.items() if k.startswith("mo_hinh:")},
        },
        "phien": {
            k[:8] + "-0000": {c: kv[f"{k[:8]}:{c}"] for c in goi._COT_PHIEN}
            | {"system_prompt": i < kv["system_prompt"]}
            for i, k in enumerate(k for k in kv if k.endswith(":cau_lenh_nguoi"))
        },
        "tong_ke_ca_tac_tu_con": {
            "goi_cong_cu": kv["goi_cong_cu_ca_tac_tu_con"],
            "cong_cu:Write": kv["ghi_sua_tep"],
            "cong_cu:WebSearch": kv["tim_web"],
            "cong_cu:WebFetch": kv["doc_trang_web"],
        },
    }
    assert goi.lech_so_prompt_log(goi.gia_tri_tu_so_dem(so_dem), van_ban) == []
    so_dem["tong"]["cau_lenh_nguoi"] += 1  # lần xuất sau có thêm một câu người gõ
    lech = goi.lech_so_prompt_log(goi.gia_tri_tu_so_dem(so_dem), van_ban)
    assert any(x.startswith("noi-dung.md") for x in lech), lech
    assert sum(x.startswith("05-BAN-KE-KHAI.md") for x in lech) >= 4, lech


def test_bang_ky_co_du_ba_thanh_vien():
    k = doc_md.phan_tich(_nguon())
    i = next(j for j, x in enumerate(k) if x.loai == "chi_thi" and x.chu == "BANG-KY")
    bang = next(x for x in k[i:] if x.loai == "bang")
    ten = [h[0] for h in bang.muc[1:]]
    assert ten == ["Ngô Bình Minh", "Lê Xuân Khánh", "Ngô Lâm Tiến"]
    assert all(h[-1] == "" for h in bang.muc[1:]), "cột chữ ký phải để trống để ký tay"


def test_khang_dinh_sai_cu_chi_con_trong_muc_dinh_chinh():
    md = _nguon()
    # Phần việc 2 (wf6): câu "N commit ngày 25/09, commit cuối là commit dựng bản kê khai này"
    # sai ngay khi nhánh có thêm commit (9 → 22 → 23 → 24; một lần phải amend để giữ câu đúng).
    # Bản kê khai không được ghi số commit của nhánh đang sống; chỉ trỏ lệnh git log.
    phang = re.sub(r"\s+", " ", md)
    for mau in (r"\d+ commit ngày 25/09", r"\d+/\d+ commit của nhánh", r"cả \d+ mang dòng"):
        assert not re.search(mau, phang), f"05 còn ghi số commit của nhánh hoàn thiện: {mau}"
    dau = md.index("## Đính chính")
    cuoi = md.index("## I.")
    for cum in ("1.297", "0,271", "4,5%", "tự viết", "gán tay", "lợi ích chính đáng"):
        for m in re.finditer(re.escape(cum), md):
            assert dau <= m.start() < cuoi, f"{cum!r} xuất hiện ngoài mục đính chính"
    can_cu = md.index("## Căn cứ")
    for m in re.finditer("13/2023", md):
        assert can_cu <= m.start() < cuoi, "Nghị định 13/2023 chỉ được nhắc là đã bị thay"
    # Kiểm độc lập 25/09/2026 (wf6-5, P0): hồ sơ mục 13 sẽ trỏ `main` SAU khi hợp nhất, còn
    # 05 tả `main` = 390027b, 56/56 commit, nhánh hoàn thiện "chưa hợp nhất". Điền mã commit ở
    # mục 13 mà không sửa 05 thì hai văn bản nộp cùng nhau mâu thuẫn — bộ dựng phải chặn.
    ho_so = (DAY.parent / "noi-dung.md").read_text(encoding="utf-8")
    assert dung_ke_khai.lech_trang_thai_kho(ho_so, md) == [], "mục 13 chưa điền mã commit"
    # 27/09/2026: ô ⬜ của mục 13 thành dấu giữ chỗ [[COMMIT_NOP]]; hoan_tat_ho_so.py thay nó
    # bằng `mã` (7 ký tự, trong dấu mã) — đúng dạng mẫu dò _MA_COMMIT_MUC_13 bắt được.
    sau_hop_nhat = ho_so.replace("commit [[COMMIT_NOP]]", "commit `a1b2c3d`")
    assert sau_hop_nhat != ho_so, "câu mục 13 đổi chữ — sửa mẫu dò _MA_COMMIT_MUC_13"
    lech = dung_ke_khai.lech_trang_thai_kho(sau_hop_nhat, md)
    assert any("390027b" in x for x in lech), lech
    assert any("a1b2c3d" in x for x in lech), lech
    assert len(lech) >= 5, lech  # dòng 11, I.1, I.2, II, VII.1
    # 05 đã viết lại theo trạng thái sau hợp nhất thì sạch — kể cả câu PR số 1 "chưa hợp nhất".
    da_sua = (
        "| Trạng thái mã nguồn khi kê khai | Nhánh `main` tại commit `a1b2c3d` (đã hợp nhất "
        "`hoan-thien/ho-so-2509`; trước đó `main` ở 390027b, 56 commit). Nhánh "
        "`tien/aisc-round2` (PR số 1) chưa hợp nhất |"
    )
    assert dung_ke_khai.lech_trang_thai_kho(sau_hop_nhat, da_sua) == []


def test_dung_docx_khong_lot_ky_hieu(tmp_path):
    pytest.importorskip("docx")
    ra = tmp_path / "ke-khai.docx"
    dung_ke_khai.dung_docx(doc_md.phan_tich(_nguon()), ra)
    assert dung_ke_khai.kiem_docx(ra) == []


def test_anh_moc_cu_bo_anh_co_du_lieu_that_cua_kenh_ben_thu_ba(tmp_path):
    """Gói Drive mở công khai (27/09/2026): ảnh 11/09 phân tích buổi live của kênh bên thứ ba
    (``l2-*`` có bình luận nguyên văn, một ảnh còn tên tài khoản; ``l4-02..04`` có tên shop)
    không được chép vào ``anh-moc-cu/`` — hồ sơ mục 3.3 cam kết không công bố nguyên văn."""
    import dung_goi_drive as goi

    kho = tmp_path / "kho"
    (kho / "docs" / "img" / "v2").mkdir(parents=True)
    for ten in ("l1-01-a.png", "l2-05-b.png", "l4-01-c.png", "l4-03-d.png", "ghi-chu.txt"):
        (kho / "docs" / "img" / ten).write_bytes(b"x")
    for ten in ("01-a.png", "README.md", "chup.json"):
        (kho / "docs" / "img" / "v2" / ten).write_bytes(b"x")
    dich = tmp_path / "anh-moc-cu"
    cu = dich / "2026-09-11_ban-nhap_04b3f52"
    cu.mkdir(parents=True)
    (cu / "l2-05-b.png").write_bytes(b"lan-dung-cu")
    ra = goi.chep_anh_moc_cu(dich, kho)
    assert sorted(p.name for p in cu.iterdir()) == ["l1-01-a.png", "l4-01-c.png"]
    assert sorted(ra["bo"]) == ["docs/img/l2-05-b.png", "docs/img/l4-03-d.png"]
    moi = dich / "2026-09-25_hoan-thien_af11a93"
    assert sorted(p.name for p in moi.iterdir()) == ["01-a.png", "README.md", "chup.json"]
    assert "Cố ý không chép 2 ảnh" in (dich / "DOC-TRUOC.md").read_text(encoding="utf-8")
    # Kho thật: mọi ảnh l2-* và l4-02..04 bị loại, ảnh mô phỏng/demo thì giữ.
    that = sorted(p.name for p in (goi.REPO / "docs" / "img").glob("*.png"))
    bo = [t for t in that if goi.BO_ANH.match(t)]
    assert bo, "không còn ảnh nào bị loại — kiểm lại BO_ANH"
    assert all(t.startswith(("l2-", "l4-02", "l4-03", "l4-04")) for t in bo)
    assert any(t.startswith("l3-") for t in that if t not in bo)
