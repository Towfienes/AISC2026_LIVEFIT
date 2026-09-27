"""``hoan_tat_ho_so.py``: thay dấu giữ chỗ mục 13 và CHẶN bản nộp khi chưa đủ điều kiện.

Thêm 27/09/2026. Link Drive và mã commit nộp chỉ có sau khi hợp nhất, đẩy lên và tải gói
Drive; hồ sơ mang dấu giữ chỗ ``[[LINK_DRIVE]]``, ``[[COMMIT_NOP]]``. Cổng này canh: nội
dung thật có đúng hai dấu đó và không còn ô ⬜; thay xong thì câu mục 13 khớp mẫu dò của bộ
dựng kê khai; link sai dạng, mã commit sai, thiếu một tham số, kê khai còn tả kho trước
khi hợp nhất, PDF còn ``[[``/⬜/Markdown — đều không chép gì vào thư mục nộp. Không cần Word
hay python-docx: bộ dựng và bộ đọc PDF được thay bằng bản giả.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

DAY = Path(__file__).resolve().parents[1] / "docs" / "competition" / "sang-tao-tre-2026"
LINK = "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv_-wx?usp=sharing"
LINK_CHUAN = "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv_-wx"
MA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"


def _nap(ten: str, tep: Path):
    spec = importlib.util.spec_from_file_location(ten, tep)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ht():
    try:
        yield _nap("hoan_tat_ho_so", DAY / "hoan_tat_ho_so.py")
    finally:
        sys.modules.pop("hoan_tat_ho_so", None)


@pytest.fixture(scope="module")
def ke_khai():
    sys.path.insert(0, str(DAY / "ke_khai"))
    try:
        yield _nap("dung_ke_khai_cho_hoan_tat", DAY / "ke_khai" / "dung_ke_khai.py")
    finally:
        sys.path.remove(str(DAY / "ke_khai"))
        sys.modules.pop("dung_ke_khai_cho_hoan_tat", None)


def _than(md: str) -> str:
    """Nội dung sẽ in (bỏ chú thích <!-- … --> dành cho người viết)."""
    return re.sub(r"<!--.*?-->", "", md, flags=re.S)


def test_noi_dung_that_co_dung_hai_dau_giu_cho_va_khong_con_o_trong(ht):
    than = _than((DAY / "noi-dung.md").read_text(encoding="utf-8"))
    assert than.count(ht.LINK_DRIVE) == 1
    assert than.count(ht.COMMIT_NOP) == 1
    assert ht.giu_cho_con_lai(than) == sorted({ht.LINK_DRIVE, ht.COMMIT_NOP})
    assert "⬜" not in than, "còn ô ⬜: bản chờ link không dựng được"


def test_cau_bat_buoc_muc_1_nguyen_van_va_ten_san_pham_thong_nhat():
    """Trưởng nhóm yêu cầu câu kết mục 1 nguyên văn (chỉ đổi '-' thành '–' sau LiveLift)."""
    md = (DAY / "noi-dung.md").read_text(encoding="utf-8")
    ten = (
        "LiveLift – Nền tảng thí nghiệm vận hành và hỗ trợ ra quyết định cho livestream thương mại"
    )
    cau = (
        "Xuất phát từ những lý do trên, nhóm nghiên cứu quyết định lựa chọn và tiến hành nghiên "
        f"cứu, phát triển giải pháp “{ten}”, hướng tới việc hỗ trợ đội ngũ vận hành đánh giá có "
        "hệ thống tác động của các quyết định trong phiên live và từng bước chuyển từ ra quyết "
        "định chủ yếu dựa trên kinh nghiệm sang ra quyết định dựa trên bằng chứng."
    )
    dau_1 = re.search(r"^# 1\. ", md, re.M).start()
    dau_2 = re.search(r"^# 2\. ", md, re.M).start()
    muc_1 = md[dau_1:dau_2]
    assert muc_1.rstrip().endswith(cau), "câu bắt buộc phải là đoạn KẾT của mục 1"
    assert f"**Tên sản phẩm: {ten}.**" in muc_1
    tom_tat = md[md.index("# Tóm tắt dự án") : dau_1]
    assert ten in tom_tat, "Tóm tắt phải nêu đúng tên sản phẩm"
    for tep in ("05-BAN-KE-KHAI.md", "07-KICH-BAN-2-VIDEO.md"):
        assert ten in (DAY / tep).read_text(encoding="utf-8"), tep
    for tep in ("noi-dung.md", "05-BAN-KE-KHAI.md"):
        assert "hạ tầng đo lường nhân quả" not in (DAY / tep).read_text(encoding="utf-8"), tep


def test_thay_giu_cho_ra_cau_ma_ke_khai_do_duoc(ht, ke_khai):
    md = (DAY / "noi-dung.md").read_text(encoding="utf-8")
    moi = ht.thay_giu_cho(md, LINK_CHUAN, MA)
    assert ht.giu_cho_con_lai(_than(moi)) == []
    m = ke_khai._MA_COMMIT_MUC_13.search(moi)
    assert m, "câu mục 13 đổi chữ — sửa mẫu dò _MA_COMMIT_MUC_13"
    assert m.group(1) == MA[:7]
    assert LINK_CHUAN in moi


def test_chuan_hoa_link_drive(ht):
    assert ht.chuan_hoa_link_drive(LINK) == (LINK_CHUAN, [])
    u0 = "https://drive.google.com/drive/u/0/folders/1AbCdEfGhIjKlMnOpQrStUv_-wx"
    assert ht.chuan_hoa_link_drive(u0) == (LINK_CHUAN, [])
    for sai in (
        "",
        "http://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp",
        "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view",
        "https://docs.google.com/document/d/1AbCdEfGhIjKlMnOp/edit",
        "https://drive.google.com/drive/folders/[[LINK_DRIVE]]",
        "https://drive.google.com/drive/folders/ngan",
        "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp xem",
        "https://evil.example/drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp",
    ):
        link, loi = ht.chuan_hoa_link_drive(sai)
        assert link is None, sai
        assert loi, sai


def test_kiem_ma_commit(ht):
    assert ht.kiem_ma_commit("bcdd1fc") == []
    assert ht.kiem_ma_commit(MA) == []
    for sai in ("", "abc12", "xyz1234", "BCDD1FC", "[[COMMIT_NOP]]"):
        assert ht.kiem_ma_commit(sai), sai


def test_quet_chu_pdf(ht):
    sach = "Trang 1\f" * 20 + f"link {LINK_CHUAN[:30]}\n{LINK_CHUAN[30:]} commit {MA[:7]}"
    assert ht.quet_chu_pdf(sach, cho_phep_giu_cho=False, phai_co=(LINK_CHUAN, MA[:7])) == []
    for ban, ky_hieu in (("[[LINK_DRIVE]]", "[["), ("⬜", "⬜"), ("**đậm**", "**"), ("`x`", "`")):
        loi = ht.quet_chu_pdf(sach + ban, cho_phep_giu_cho=False)
        assert any(ky_hieu in x for x in loi), (ban, loi)
    assert ht.quet_chu_pdf("[[LINK_DRIVE]]", cho_phep_giu_cho=True) == []
    assert ht.quet_chu_pdf("x\f" * 21, cho_phep_giu_cho=True), "quá 20 trang phải bị chặn"
    assert ht.quet_chu_pdf("không có link", cho_phep_giu_cho=False, phai_co=(LINK_CHUAN,))


def _dung_gia(ghi_nhan: dict):
    def dung(noi_dung_tam: Path, ra: Path, *, cho_link: bool) -> int:
        ghi_nhan["noi_dung"] = noi_dung_tam.read_text(encoding="utf-8")
        ghi_nhan["cho_link"] = cho_link
        ra.mkdir(parents=True, exist_ok=True)
        hau_to = "_CHO_LINK" if cho_link else ""
        for duoi in (".docx", ".pdf"):
            (ra / f"AI2026_Ho_So_Du_An_LiveLift_BangC{hau_to}{duoi}").write_bytes(b"GIA")
        return 0

    return dung


def _cam_goi(*_a, **_k):
    raise AssertionError("không được dựng khi chưa đủ điều kiện")


def test_thieu_mot_tham_so_thi_khong_dung(ht, monkeypatch, tmp_path):
    monkeypatch.setattr(ht, "dung", _cam_goi)
    nop = tmp_path / "nop"
    assert ht.main(["--link-drive", LINK, "--nop", str(nop), "--dung", str(tmp_path)]) == 2
    assert ht.main(["--commit", MA, "--nop", str(nop), "--dung", str(tmp_path)]) == 2
    assert not nop.exists()


def test_ke_khai_con_ta_kho_truoc_hop_nhat_thi_chan_ban_nop(ht, monkeypatch, tmp_path):
    """05-BAN-KE-KHAI.md hiện tả `main` = 390027b, nhánh hoàn thiện chưa hợp nhất: điền mã
    commit sau hợp nhất vào hồ sơ mà không sửa kê khai thì hai văn bản nộp mâu thuẫn."""
    monkeypatch.setattr(ht, "kiem_commit_tren_main", lambda _ma: [])
    monkeypatch.setattr(ht, "dung", _cam_goi)
    nop = tmp_path / "nop"
    argv = ["--link-drive", LINK, "--commit", MA, "--nop", str(nop), "--dung", str(tmp_path)]
    assert ht.main(argv) == 1
    assert not nop.exists()


def test_commit_chua_tren_origin_main_thi_chan(ht, monkeypatch, tmp_path):
    monkeypatch.setattr(ht, "kiem_commit_tren_main", lambda _ma: ["chưa nằm trên origin/main"])
    monkeypatch.setattr(ht, "dung", _cam_goi)
    argv = ["--link-drive", LINK, "--commit", MA, "--nop", str(tmp_path / "nop")]
    assert ht.main([*argv, "--dung", str(tmp_path)]) == 1


def _chuan_bi_ban_nop(ht, monkeypatch, tmp_path, chu: str):
    ghi_nhan: dict = {}
    monkeypatch.setattr(ht, "kiem_commit_tren_main", lambda _ma: [])
    monkeypatch.setattr(ht, "lech_ke_khai", lambda _v: [])
    monkeypatch.setattr(ht, "dung", _dung_gia(ghi_nhan))
    monkeypatch.setattr(ht, "chu_pdf", lambda _pdf: chu)
    nop, giu = tmp_path / "nop", tmp_path / "giu"
    nop.mkdir()
    (nop / "AI2026_Ho_So_Du_An_LiveLift_BangC_CHO_LINK.pdf").write_bytes(b"CU")
    argv = ["--link-drive", LINK, "--commit", MA, "--nop", str(nop), "--dung", str(giu)]
    return ghi_nhan, nop, argv


def test_ban_nop_thay_giu_cho_chep_va_xoa_ban_cho_link(ht, monkeypatch, tmp_path):
    chu = "x\f" * 20 + f" {LINK_CHUAN} {MA[:7]}"
    ghi_nhan, nop, argv = _chuan_bi_ban_nop(ht, monkeypatch, tmp_path, chu)
    assert ht.main(argv) == 0
    assert ghi_nhan["cho_link"] is False
    assert LINK_CHUAN in ghi_nhan["noi_dung"]
    assert f"`{MA[:7]}`" in ghi_nhan["noi_dung"]
    assert "[[" not in _than(ghi_nhan["noi_dung"])
    assert sorted(p.name for p in nop.iterdir()) == [
        "AI2026_Ho_So_Du_An_LiveLift_BangC.docx",
        "AI2026_Ho_So_Du_An_LiveLift_BangC.pdf",
    ]
    assert (tmp_path / "giu" / "AI2026_Ho_So_Du_An_LiveLift_BangC.pdf").exists()
    # noi-dung.md trong kho KHÔNG bị sửa: vẫn mang dấu giữ chỗ
    assert ht.LINK_DRIVE in (DAY / "noi-dung.md").read_text(encoding="utf-8")


def test_pdf_con_dau_giu_cho_thi_khong_chep(ht, monkeypatch, tmp_path):
    chu = "x\f" * 20 + f" {LINK_CHUAN} {MA[:7]} [[COMMIT_NOP]]"
    _ghi_nhan, nop, argv = _chuan_bi_ban_nop(ht, monkeypatch, tmp_path, chu)
    assert ht.main(argv) == 1
    assert sorted(p.name for p in nop.iterdir()) == [
        "AI2026_Ho_So_Du_An_LiveLift_BangC_CHO_LINK.pdf"
    ]


def test_ban_cho_link_can_dai_do(ht, monkeypatch, tmp_path):
    ghi_nhan: dict = {}
    monkeypatch.setattr(ht, "dung", _dung_gia(ghi_nhan))
    nop = tmp_path / "nop"
    argv = ["--nop", str(nop), "--dung", str(tmp_path / "giu")]
    monkeypatch.setattr(ht, "chu_pdf", lambda _pdf: "x\f[[LINK_DRIVE]] [[COMMIT_NOP]]")
    assert ht.main(argv) == 1, "thiếu dải CHƯA ĐIỀN LINK DRIVE phải bị chặn"
    assert not nop.exists()
    monkeypatch.setattr(
        ht, "chu_pdf", lambda _pdf: "x\f[[LINK_DRIVE]] BẢN CHỜ LINK – CHƯA ĐIỀN LINK DRIVE"
    )
    assert ht.main(argv) == 0
    assert ghi_nhan["cho_link"] is True
    assert sorted(p.name for p in nop.iterdir()) == [
        "AI2026_Ho_So_Du_An_LiveLift_BangC_CHO_LINK.docx",
        "AI2026_Ho_So_Du_An_LiveLift_BangC_CHO_LINK.pdf",
    ]
