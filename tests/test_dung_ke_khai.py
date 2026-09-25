"""Đưa bộ test của bộ dựng BẢN KÊ KHAI AI vào lần chạy ``pytest`` mặc định.

Bộ test thật nằm cạnh bộ dựng, ở
``docs/competition/sang-tao-tre-2026/ke_khai/test_dung_ke_khai.py`` (chạy riêng
được bằng ``pytest docs/competition/sang-tao-tre-2026/ke_khai``). Nhưng
``testpaths = ["tests"]`` nên ``pytest`` mặc định — và CI — không bao giờ thu thập
nó: bản kê khai (Điều 5 thể lệ) có thể lọt ký hiệu Markdown hay khẳng định sai cũ
mà không cổng nào đỏ (phản biện làn kê khai 25/09/2026).

Tệp này nạp module đó theo đường dẫn (không chuyển tệp, không đổi cách nó import
``doc_md``/``dung_ke_khai``) rồi đưa các hàm ``test_*`` vào không gian tên của
mình để pytest thu thập. Không có hàm test nào ⇒ đỏ, để việc đổi tên/chuyển chỗ
không lặng lẽ làm cổng rỗng.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

KE_KHAI = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "competition"
    / "sang-tao-tre-2026"
    / "ke_khai"
    / "test_dung_ke_khai.py"
)


def _nap():
    ten = "livelift_ho_so_ke_khai_test_dung_ke_khai"
    spec = importlib.util.spec_from_file_location(ten, KE_KHAI)
    assert spec is not None, KE_KHAI
    assert spec.loader is not None, KE_KHAI
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ten] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _nap()
_TESTS = {k: v for k, v in vars(_mod).items() if k.startswith("test_") and callable(v)}
globals().update(_TESTS)


def test_cau_noi_thu_thap_du_bo_test_ke_khai():
    assert len(_TESTS) >= 7, sorted(_TESTS)
    assert "test_ban_ke_khai_that_sach_va_du_muc" in _TESTS
