"""Phép soát trước buổi chấm phải CHẶN khi bộ phân loại ý định đang rơi về từ khoá.

Kiểm toán 25/09/2026: với scikit-learn lệch bản, ``joblib.load`` vẫn thành công
nhưng ``predict_proba`` vỡ, và 393/393 bình luận âm thầm bị gán nhãn bằng từ khoá
trong khi ``/health`` khai mô hình. Máy chủ nay nói thật —
``intent_backend="keyword_fallback"`` kèm ``intent_fallback_reason``, hoặc
``"dang_nap"`` trong cửa sổ nạp — nhưng ``scripts/kiem_tra_truoc_demo.py`` không
đọc trường đó, nên vẫn in "SẴN SÀNG LÊN SÓNG". Từ nay:

* ``keyword_fallback`` ⇒ TRƯỢT (chặn), kèm lời khuyên sửa;
* ``dang_nap`` ⇒ hỏi lại ``/health`` tới 30 giây; còn ``dang_nap`` ⇒ TRƯỢT;
* ``keyword_baseline`` (cài không kèm [ml] — cấu hình hợp lệ) ⇒ CẢNH BÁO;
* ``tfidf_logreg`` ⇒ ĐẠT.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "kiem_tra_truoc_demo.py"


def _nap():
    ten = "livelift_kiem_tra_truoc_demo_bo_phan_loai_test"
    spec = importlib.util.spec_from_file_location(ten, SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ten] = mod
    spec.loader.exec_module(mod)
    return mod


kt = _nap()
TEN = "Bộ phân loại ý định"


class _DongHoGia:
    """Đồng hồ giả: ``ngu(x)`` chỉ cộng thời gian, không ngủ thật."""

    def __init__(self) -> None:
        self.t = 1000.0
        self.lan_ngu = 0

    def dong_ho(self) -> float:
        return self.t

    def ngu(self, s: float) -> None:
        self.lan_ngu += 1
        self.t += s


def _chuoi_health(*backends: str | None, ly_do: str | None = None):
    """Hàm hỏi lại /health trả lần lượt từng backend (backend cuối lặp mãi)."""
    ds = list(backends)
    dem = {"n": 0}

    def hoi_lai() -> dict:
        dem["n"] += 1
        b = ds[min(dem["n"] - 1, len(ds) - 1)]
        return {"intent_backend": b, "intent_fallback_reason": ly_do}

    return hoi_lai, dem


def _chay(doc: dict, hoi_lai=None, *, khat_khe: bool = False):
    s = kt.Soat(khat_khe=khat_khe)
    dh = _DongHoGia()
    kt.thu_bo_phan_loai(s, doc, hoi_lai, dong_ho=dh.dong_ho, ngu=dh.ngu)
    dong = [k for k in s.ket_qua if k.ten == TEN]
    assert len(dong) == 1, [k.ten for k in s.ket_qua]
    return s, dong[0], dh


def test_keyword_fallback_la_truot_chan_kem_loi_khuyen_sua():
    s, kq, dh = _chay(
        {"intent_backend": "keyword_fallback", "intent_fallback_reason": "AttributeError"}
    )
    assert kq.trang_thai == kt.TRUOT
    assert kq.chan is True
    assert "AttributeError" in kq.chi_tiet, "phải in lý do máy chủ khai"
    assert "từ khoá" in kq.chi_tiet.lower()
    assert "scikit-learn" in kq.cach_sua
    assert "khởi động lại" in kq.cach_sua
    assert kq in s.hong(), "trượt-và-chặn phải làm phán quyết thành CHƯA SẴN SÀNG"
    assert dh.lan_ngu == 0


def test_dang_nap_qua_30_giay_la_truot():
    hoi_lai, dem = _chuoi_health("dang_nap")
    s, kq, dh = _chay({"intent_backend": "dang_nap"}, hoi_lai)
    assert kq.trang_thai == kt.TRUOT
    assert kq.chan is True
    assert "dang_nap" in kq.chi_tiet
    assert dh.t - 1000.0 >= kt.CHO_NAP_MO_HINH_S, "phải chờ đủ ngưỡng trước khi kết luận"
    assert dh.t - 1000.0 <= kt.CHO_NAP_MO_HINH_S + kt.NHIP_HOI_LAI_S, "không chờ quá ngưỡng"
    assert dem["n"] >= 2, "phải hỏi lại /health trong lúc chờ"
    assert kq.cach_sua
    assert kq in s.hong()


def test_dang_nap_roi_nap_xong_la_dat():
    hoi_lai, dem = _chuoi_health("dang_nap", "tfidf_logreg")
    _, kq, dh = _chay({"intent_backend": "dang_nap"}, hoi_lai)
    assert kq.trang_thai == kt.DAT, kq.chi_tiet
    assert dem["n"] == 2
    assert dh.t - 1000.0 < kt.CHO_NAP_MO_HINH_S


def test_dang_nap_roi_roi_ve_tu_khoa_la_truot():
    hoi_lai, _ = _chuoi_health("dang_nap", "keyword_fallback", ly_do="UnpicklingError")
    _, kq, _ = _chay({"intent_backend": "dang_nap"}, hoi_lai)
    assert kq.trang_thai == kt.TRUOT
    assert kq.chan is True
    assert "UnpicklingError" in kq.chi_tiet


def test_hoi_lai_loi_mang_van_cho_toi_nguong_roi_truot():
    def hoi_lai() -> dict:
        raise ConnectionError("mất mạng giữa chừng (test)")

    _, kq, dh = _chay({"intent_backend": "dang_nap"}, hoi_lai)
    assert kq.trang_thai == kt.TRUOT
    assert dh.t - 1000.0 >= kt.CHO_NAP_MO_HINH_S


def test_mo_hinh_dang_chay_la_dat_khong_cho():
    _, kq, dh = _chay({"intent_backend": "tfidf_logreg", "intent_fallback_reason": None})
    assert kq.trang_thai == kt.DAT
    assert "tfidf_logreg" in kq.chi_tiet
    assert dh.lan_ngu == 0


def test_khong_co_mo_hinh_theo_cau_hinh_la_canh_bao_khong_chan():
    s, kq, _ = _chay({"intent_backend": "keyword_baseline"})
    assert kq.trang_thai == kt.CANH_BAO
    assert kq.chan is False
    assert "[server,ml]" in kq.cach_sua, "lời khuyên phải nói cài extra ml"
    assert kq not in s.hong()
    s2, kq2, _ = _chay({"intent_backend": "keyword_baseline"}, khat_khe=True)
    assert kq2 in s2.hong(), "chế độ khắt khe: cảnh báo cũng chặn"


def test_api_cu_khong_khai_backend_la_khong_do_duoc():
    _, kq, _ = _chay({})
    assert kq.trang_thai == kt.KHONG_DO
    assert kq.chan is False


def test_main_goi_phep_soat_bo_phan_loai_voi_ham_hoi_lai():
    src = SCRIPT.read_text(encoding="utf-8")
    ham_main = src.split("def main(")[1]
    assert "thu_bo_phan_loai(s, doc," in ham_main, "main phải chạy phép soát bộ phân loại"
