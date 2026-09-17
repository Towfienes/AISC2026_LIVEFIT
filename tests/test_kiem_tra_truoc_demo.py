"""Phép soát trước buổi chấm: kho chết không được báo thành "kho TRỐNG".

Hồi quy kiểm toán 17/09/2026. Khi kho dữ liệu không trả lời, ``/health`` trả
``mode='unknown'`` và ``mode_counts=null`` (xem ``api/main.py``). Trước khi sửa,
``thu_che_do_du_lieu`` cộng số phiên ra 0 rồi in TRƯỢT "kho TRỐNG — hội đồng mở
link sẽ thấy một trang không có gì" kèm lời khuyên nạp bộ demo vàng: chỉ sai
bệnh, trong khi vấn đề thật là kho chết.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _nap():
    ten = "livelift_kiem_tra_truoc_demo_test"
    spec = importlib.util.spec_from_file_location(ten, REPO / "scripts" / "kiem_tra_truoc_demo.py")
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ten] = mod
    spec.loader.exec_module(mod)
    return mod


kt = _nap()


def _dong(s, ten: str):
    return [kq for kq in s.ket_qua if kq.ten == ten]


def test_kho_khong_tra_loi_khong_bi_bao_la_kho_trong():
    s = kt.Soat()
    kt.thu_che_do_du_lieu(s, {"mode": "unknown", "mode_counts": None})

    du_lieu = _dong(s, "Trang có dữ liệu để xem")
    assert len(du_lieu) == 1
    kq = du_lieu[0]
    assert kq.trang_thai == kt.KHONG_DO, "không đếm được thì là KHÔNG ĐO ĐƯỢC, không phải TRƯỢT"
    assert "TRỐNG" not in kq.chi_tiet
    assert "seed-vang" not in kq.cach_sua, "không được khuyên nạp demo vào một kho đang chết"
    assert "không trả lời" in kq.chi_tiet
    assert not any(k.trang_thai == kt.TRUOT for k in s.ket_qua)


def test_kho_trong_that_van_bi_bao_truot():
    s = kt.Soat()
    kt.thu_che_do_du_lieu(s, {"mode": "real", "mode_counts": {"demo": 0, "real": 0}})
    kq = _dong(s, "Trang có dữ liệu để xem")[0]
    assert kq.trang_thai == kt.TRUOT
    assert "TRỐNG" in kq.chi_tiet


def test_kho_co_du_lieu_dat():
    s = kt.Soat()
    kt.thu_che_do_du_lieu(s, {"mode": "mixed", "mode_counts": {"demo": 3, "real": 2}})
    kq = _dong(s, "Trang có dữ liệu để xem")[0]
    assert kq.trang_thai == kt.DAT
    assert "5 phiên" in kq.chi_tiet


def test_kho_khong_tra_loi_nhan_che_do_la_canh_bao_khong_chan():
    """Kho không trả lời: dòng nhãn DEMO/THẬT không được tự nhận một chế độ nào,
    và không được chặn buổi chấm lần thứ hai (dòng "Kho đang trả lời" đã chặn)."""
    s = kt.Soat()
    kt.thu_che_do_du_lieu(s, {"mode": "unknown", "mode_counts": None})
    nhan = _dong(s, "Nhãn DEMO/THẬT")
    assert len(nhan) == 1
    assert nhan[0].trang_thai == kt.CANH_BAO
    assert nhan[0].chan is False
    assert "KHO: CHƯA ĐẾM ĐƯỢC" in nhan[0].cach_sua


def test_nhan_chip_duoc_trich_trong_phep_soat_khop_ma_web():
    """Phép soát kể lại chữ trên chip kho — chữ đó phải là chuỗi THẬT trong
    ``ModeChip.tsx``, nếu không người soát sẽ đi tìm một nhãn không tồn tại."""
    chip = (REPO / "web" / "src" / "components" / "ModeChip.tsx").read_text(encoding="utf-8")
    trich: set[str] = set()
    for doc in (
        {"mode": "demo", "mode_counts": {"demo": 2, "real": 0}},
        {"mode": "real", "mode_counts": {"demo": 0, "real": 2}},
        {"mode": "mixed", "mode_counts": {"demo": 1, "real": 1}},
        {"mode": "unknown", "mode_counts": None},
    ):
        s = kt.Soat()
        kt.thu_che_do_du_lieu(s, doc)
        for kq in _dong(s, "Nhãn DEMO/THẬT"):
            trich |= set(re.findall(r"'((?:KHO)[^']*)'", f"{kq.chi_tiet} {kq.cach_sua}"))
    assert trich, "tiền đề: phép soát phải trích nhãn chip"
    thieu = sorted(n for n in trich if f'"{n}"' not in chip)
    assert not thieu, f"phép soát trích nhãn chip không có trong ModeChip.tsx: {thieu}"
