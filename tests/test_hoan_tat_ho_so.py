"""``hoan_tat_ho_so.py``: dựng bản nộp chính thức và CHẶN khi chưa đủ điều kiện.

27/09/2026, trưởng nhóm chốt: hồ sơ nộp ngay, không chờ link, không nhắc Google Drive ở đâu cả;
câu kết mục 1 phải đúng nguyên văn; tên sản phẩm viết "LiveLift - …" ở mọi tệp nộp. Cổng này
canh: nguồn thật không còn ``[[…]]``, ô ⬜, chữ "Drive"; câu bắt buộc là đoạn KẾT mục 1; bản
kê khai tả kho sau khi hợp nhất; PDF còn ``[[``/⬜/Markdown/Drive, vượt 20 trang, trang cuối
trống quá nửa, thiếu câu bắt buộc: đều không chép gì vào thư mục nộp. Không cần Word hay
python-docx: bộ dựng và bộ đọc PDF được thay bằng bản giả.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

DAY = Path(__file__).resolve().parents[1] / "docs" / "competition" / "sang-tao-tre-2026"
TEN = "LiveLift - Nền tảng thí nghiệm vận hành và hỗ trợ ra quyết định cho livestream thương mại"
CAU = (
    "Xuất phát từ những lý do trên, nhóm nghiên cứu quyết định lựa chọn và tiến hành nghiên "
    f"cứu, phát triển giải pháp “{TEN}”, hướng tới việc hỗ trợ đội ngũ vận hành đánh giá có "
    "hệ thống tác động của các quyết định trong phiên live và từng bước chuyển từ ra quyết "
    "định chủ yếu dựa trên kinh nghiệm sang ra quyết định dựa trên bằng chứng."
)


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


def _than(md: str) -> str:
    """Nội dung sẽ in (bỏ chú thích <!-- … --> dành cho người viết)."""
    return re.sub(r"<!--.*?-->", "", md, flags=re.S)


def test_hang_so_khop_yeu_cau_truong_nhom(ht):
    assert ht.TEN_SAN_PHAM == TEN
    assert ht.CAU_BAT_BUOC == CAU


def test_nguon_that_khong_con_giu_cho_o_trong_va_drive(ht):
    for tep in ("noi-dung.md", "05-BAN-KE-KHAI.md"):
        md = (DAY / tep).read_text(encoding="utf-8")
        assert ht.loi_nguon(tep, md) == [], tep


def test_cau_bat_buoc_muc_1_nguyen_van_va_ten_san_pham_thong_nhat():
    md = (DAY / "noi-dung.md").read_text(encoding="utf-8")
    dau_1 = re.search(r"^# 1\. ", md, re.M).start()
    dau_2 = re.search(r"^# 2\. ", md, re.M).start()
    muc_1 = md[dau_1:dau_2]
    assert muc_1.rstrip().endswith(CAU), "câu bắt buộc phải là đoạn KẾT của mục 1, nguyên văn"
    assert f"**Tên sản phẩm: {TEN}.**" in muc_1
    tom_tat = md[md.index("# Tóm tắt dự án") : dau_1]
    assert TEN in tom_tat, "Tóm tắt phải nêu đúng tên sản phẩm"
    ten_cu = TEN.replace(" - ", " – ")
    for tep in ("noi-dung.md", "05-BAN-KE-KHAI.md", "07-KICH-BAN-2-VIDEO.md"):
        t = (DAY / tep).read_text(encoding="utf-8")
        assert TEN in t, tep
        assert ten_cu not in t, f"{tep} còn tên sản phẩm kiểu cũ (gạch ngắn '–')"
        assert "hạ tầng đo lường nhân quả" not in t, tep


def test_ho_so_han_che_gach_ngang_va_ky_hieu_trong_van_ban():
    """Trưởng nhóm 27/09/2026: văn phong tự nhiên, hạn chế gạch ngang và ký hiệu dồn nén."""
    t = _than((DAY / "noi-dung.md").read_text(encoding="utf-8"))
    for ky_hieu in ("—", "–", "→", "·", "×", "≥", "≤"):
        assert ky_hieu not in t, f"hồ sơ còn ký hiệu {ky_hieu!r}"


def test_muc_13_tro_kho_ma_cong_khai(ht):
    md = (DAY / "noi-dung.md").read_text(encoding="utf-8")
    muc_13 = md[re.search(r"^# 13\. ", md, re.M).start() :]
    assert ht.KHO_MA in muc_13
    assert "24/08/2026" in muc_13, "mục 13 phải nêu lịch sử commit từ 24/08/2026"


def test_quet_chu_pdf(ht):
    sach = "Trang 1\f" * 20 + f"{CAU[:50]}\n{CAU[50:]} {TEN}"
    assert ht.quet_chu_pdf(sach, phai_co=(CAU, TEN), gioi_han_trang=20) == []
    for ban, ky_hieu in (
        ("[[LINK_DRIVE]]", "[["),
        ("⬜", "⬜"),
        ("**đậm**", "**"),
        ("`x`", "`"),
        ("thư mục Google Drive", "Drive"),
    ):
        loi = ht.quet_chu_pdf(sach + ban, gioi_han_trang=20)
        assert any(ky_hieu in x for x in loi), (ban, loi)
    assert ht.quet_chu_pdf("x\f" * 21, gioi_han_trang=20), "quá 20 trang phải bị chặn"
    assert ht.quet_chu_pdf("x\f" * 21, gioi_han_trang=None) == []
    thieu = ht.quet_chu_pdf(
        sach.replace("bằng chứng.", "bằng chứng"), phai_co=(CAU,), gioi_han_trang=20
    )
    assert thieu, "câu bắt buộc thiếu dấu chấm cuối vẫn phải bị bắt"


def test_ty_le_lap_day_trang_cuoi(ht):
    html = (
        '<page width="595.3" height="841.9">'
        '<word xMin="70" yMin="40" xMax="90" yMax="52.0">20</word>'
        '<word xMin="70" yMin="300" xMax="90" yMax="421.0">cuối</word></page>'
    )
    assert ht.ty_le_lap_day(html) == pytest.approx(421.0 / 841.9)
    assert ht.ty_le_lap_day('<page width="1" height="2"></page>') is None
    assert ht.dem_gach("a — b – c – d") == {"—": 1, "–": 2}


def _gia(ht, monkeypatch, tmp_path, *, chu_hs: str, chu_kk: str, lap_day: float = 0.9):
    goi = {"ho_so": 0, "ke_khai": 0}

    def dung_ho_so(ra: Path, _ngay):
        goi["ho_so"] += 1
        for duoi in (".docx", ".pdf"):
            (ra / f"{ht.TEN_HO_SO}{duoi}").write_bytes(b"GIA")
        return 0

    def dung_ke_khai(ra_docx: Path):
        goi["ke_khai"] += 1
        for duoi in (".docx", ".pdf"):
            ra_docx.with_suffix(duoi).write_bytes(b"GIA")
        return 0

    monkeypatch.setattr(ht, "dung_ho_so", dung_ho_so)
    monkeypatch.setattr(ht, "dung_ke_khai", dung_ke_khai)
    monkeypatch.setattr(ht, "lech_ke_khai", lambda _v: [])
    monkeypatch.setattr(ht, "chu_pdf", lambda pdf: chu_hs if pdf.stem == ht.TEN_HO_SO else chu_kk)
    monkeypatch.setattr(ht, "lap_day_trang_cuoi", lambda _pdf, _n: lap_day)
    nop = tmp_path / "nop"
    return goi, nop, ["--nop", str(nop)]


CHU_HS_SACH = "x\f" * 19 + f"{CAU} {TEN} https://github.com/bminhnemhoi/AISC2026_LIVEFIT\f"
CHU_KK_SACH = f"Bản kê khai {TEN}\f" * 12


def test_ban_nop_dung_ca_hai_va_chep_dung_thu_muc(ht, monkeypatch, tmp_path):
    goi, nop, argv = _gia(ht, monkeypatch, tmp_path, chu_hs=CHU_HS_SACH, chu_kk=CHU_KK_SACH)
    assert ht.main(argv) == 0
    assert goi == {"ho_so": 1, "ke_khai": 1}
    assert sorted(p.name for p in (nop / "01-Tai-lieu-du-an").iterdir()) == [
        "AI2026_BangC_LiveLift_HoSoDuAn.docx",
        "AI2026_BangC_LiveLift_HoSoDuAn.pdf",
    ]
    assert sorted(p.name for p in (nop / "05-Ban-ke-khai").iterdir()) == [
        "AI2026_BangC_LiveLift_BanKeKhai.docx",
        "AI2026_BangC_LiveLift_BanKeKhai.pdf",
    ]


@pytest.mark.parametrize(
    ("chu_hs", "chu_kk", "lap_day"),
    [
        (CHU_HS_SACH + "thư mục Google Drive", CHU_KK_SACH, 0.9),
        (CHU_HS_SACH, CHU_KK_SACH + " Drive", 0.9),
        (CHU_HS_SACH + "[[COMMIT_NOP]]", CHU_KK_SACH, 0.9),
        (CHU_HS_SACH.replace(CAU, CAU.replace(" - ", " – ")), CHU_KK_SACH, 0.9),
        ("x\f" * 21 + CHU_HS_SACH, CHU_KK_SACH, 0.9),
        (CHU_HS_SACH, CHU_KK_SACH, 0.3),
        (CHU_HS_SACH, CHU_KK_SACH.replace(TEN, "LiveLift"), 0.9),
    ],
    ids=["ho-so-drive", "ke-khai-drive", "giu-cho", "sai-cau", "21-trang", "trang-cuoi", "ten"],
)
def test_pdf_chua_dat_thi_khong_chep_gi(ht, monkeypatch, tmp_path, chu_hs, chu_kk, lap_day):
    _goi, nop, argv = _gia(ht, monkeypatch, tmp_path, chu_hs=chu_hs, chu_kk=chu_kk, lap_day=lap_day)
    assert ht.main(argv) == 1
    assert not nop.exists()


def test_nguon_con_loi_thi_khong_dung(ht, monkeypatch, tmp_path):
    def cam(*_a, **_k):
        raise AssertionError("không được dựng khi nguồn còn lỗi")

    monkeypatch.setattr(ht, "dung_ho_so", cam)
    monkeypatch.setattr(ht, "dung_ke_khai", cam)
    monkeypatch.setattr(ht, "lech_ke_khai", lambda _v: ["bản kê khai còn ghi 390027b"])
    assert ht.main(["--nop", str(tmp_path / "nop")]) == 1
    assert not (tmp_path / "nop").exists()
    assert ht.loi_nguon("x.md", "a [[LINK_DRIVE]] ⬜ Google Drive <!-- Drive -->") == [
        "x.md: còn dấu giữ chỗ [[LINK_DRIVE]]",
        "x.md: còn 1 ô ⬜",
        "x.md: còn 2 chỗ nhắc Drive",
    ]
    assert ht.loi_nguon("x.md", "sạch <!-- [[GHI_CHU]] Drive ⬜ -->") == []
