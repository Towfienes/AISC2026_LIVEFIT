"""``scripts/xoa_ban_tho_16_buoi.py``: mặc định CHỈ liệt kê; xoá chỉ khi có cờ và câu xác nhận.

Hồ sơ mục 3.3 (phương án A, 27/09/2026) cam kết xoá an toàn bản sao lưu còn tên tài khoản
người bình luận. Xoá là không đảo ngược nên cổng này canh ba điều: chạy thường không đụng
tệp nào và không in nội dung; gõ sai câu xác nhận thì không xoá; khi xoá thì giữ đúng bảng
băm và không bao giờ đụng mục "che" hay tệp băm tên đã biết. Mọi thứ chạy trên thư mục tạm.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "xoa_ban_tho_16_buoi.py"
BI_MAT = "NOI-DUNG-BINH-LUAN-GIA-@ten_that_gia"  # chuỗi giả; không được lọt ra màn hình


@pytest.fixture(scope="module")
def xb():
    spec = importlib.util.spec_from_file_location("xoa_ban_tho_16_buoi", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture
def goc(tmp_path: Path) -> Path:
    bk = tmp_path / "backup-labeling-2509"
    (bk / "lot1").mkdir(parents=True)
    (bk / "lot1" / "comments.jsonl").write_text(BI_MAT * 50, encoding="utf-8")
    (bk / "README.md").write_text(BI_MAT, encoding="utf-8")
    (bk / "_SHA256SUMS.txt").write_text("abc  lot1/comments.jsonl\n", encoding="utf-8")
    for ngay in ("2026-09-15", "2026-09-25"):
        pl = tmp_path / "prompt-log-goc" / ngay
        pl.mkdir(parents=True)
        (pl / "phien.jsonl").write_text(BI_MAT, encoding="utf-8")
    (tmp_path / "dinh-danh-da-biet.sha256").write_text("băm\n", encoding="utf-8")
    return tmp_path


def _anh(goc: Path) -> dict[str, bytes]:
    return {p.relative_to(goc).as_posix(): p.read_bytes() for p in goc.rglob("*") if p.is_file()}


def test_mac_dinh_chi_liet_ke_khong_dung_tep_khong_in_noi_dung(xb, goc, capsys):
    truoc = _anh(goc)

    def khong_duoc_hoi(_: str) -> str:
        raise AssertionError("chế độ liệt kê không được hỏi xác nhận")

    assert xb.main(["--goc", str(goc)], hoi=khong_duoc_hoi) == 0
    ra = capsys.readouterr().out
    assert _anh(goc) == truoc
    assert "CHỈ LIỆT KÊ: 2 tệp" in ra  # comments.jsonl + README.md; bảng băm được giữ
    assert "giữ lại: _SHA256SUMS.txt" in ra
    assert "CHE (không xoá ở đây)" in ra
    assert BI_MAT not in ra
    assert "ten_that_gia" not in ra


def test_sai_cau_xac_nhan_thi_khong_xoa(xb, goc, capsys):
    truoc = _anh(goc)
    assert xb.main(["--goc", str(goc), "--thuc-hien"], hoi=lambda _: "xoa ban tho") == 1
    assert _anh(goc) == truoc
    assert "không xoá gì" in capsys.readouterr().out


def test_thuc_hien_xoa_dung_pham_vi_giu_bang_bam_va_muc_che(xb, goc, capsys):
    ma = xb.main(["--goc", str(goc), "--thuc-hien"], hoi=lambda _: xb.CAU_XAC_NHAN)
    ra = capsys.readouterr().out
    assert ma == 0, ra
    con = _anh(goc)
    assert not (goc / "backup-labeling-2509" / "lot1").exists()
    assert "backup-labeling-2509/README.md" not in con
    assert "backup-labeling-2509/_SHA256SUMS.txt" in con
    assert "prompt-log-goc/2026-09-15/phien.jsonl" in con
    assert "prompt-log-goc/2026-09-25/phien.jsonl" in con
    assert "dinh-danh-da-biet.sha256" in con
    nhat_ky = [k for k in con if k.startswith("nhat-ky-xoa-ban-tho-")]
    assert len(nhat_ky) == 1
    dong = con[nhat_ky[0]].decode("utf-8").splitlines()[1:]
    assert sorted(d.split("\t")[0] for d in dong) == [
        "backup-labeling-2509/README.md",
        "backup-labeling-2509/lot1/comments.jsonl",
    ]
    assert all(len(d.split("\t")[2]) == 64 for d in dong)  # SHA-256, không có nội dung
    assert BI_MAT not in con[nhat_ky[0]].decode("utf-8")
    assert BI_MAT not in ra


def test_tu_choi_khi_muc_xoa_chua_tep_bam_ten_da_biet(xb, goc, capsys):
    (goc / "backup-labeling-2509" / "dinh-danh-da-biet.sha256").write_text("x", encoding="utf-8")
    truoc = _anh(goc)
    assert xb.main(["--goc", str(goc), "--thuc-hien"], hoi=lambda _: xb.CAU_XAC_NHAN) == 1
    assert _anh(goc) == truoc
    assert "TỪ CHỐI XOÁ" in capsys.readouterr().out


def test_muc_tieu_khop_ho_so_va_khong_tro_vao_kho_ma(xb):
    """Danh mục phải đúng như hồ sơ mục 3.3: xoá bản sao lưu, che (không xoá) nhật ký gốc."""
    xoa = {m.duong_dan for m in xb.MUC_TIEU if m.hanh_dong == "xoa"}
    che = {m.duong_dan for m in xb.MUC_TIEU if m.hanh_dong == "che"}
    assert xoa == {"backup-labeling-2509"}
    assert che == {"prompt-log-goc/2026-09-15", "prompt-log-goc/2026-09-25"}
    assert "dinh-danh-da-biet.sha256" in xb.KHONG_BAO_GIO_XOA
    assert not any("livelift" in m.duong_dan for m in xb.MUC_TIEU)
