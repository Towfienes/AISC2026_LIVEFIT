"""``pyproject.toml`` khai đủ phụ thuộc của ``scripts/ve_hinh_ho_so.py`` (extra ``hinh``).

Phản biện làn hình 25/09/2026: script vẽ hình hồ sơ cần matplotlib, Pillow và
Playwright nhưng pyproject không khai gói nào, nên máy sạch (và ``.venv`` của
chính nhóm) không dựng lại được hình; ``--chi h2`` trên ``.venv`` từng ghi đè
PNG rồi mới chết vì thiếu Pillow. Hồ sơ hứa "mọi con số sinh lại được bằng một
lệnh" — lệnh đó phải cài được bằng ``pip install -e ".[hinh]"``.

Test đọc chính các câu ``import`` của script (bằng ``ast``), nên thêm một thư
viện vẽ mới mà quên khai là đỏ.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "ve_hinh_ho_so.py"

#: Tên module import → tên gói trên PyPI.
GOI_CUA_MODULE = {"matplotlib": "matplotlib", "PIL": "pillow", "playwright": "playwright"}


def _extras() -> dict[str, list[str]]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["optional-dependencies"]


def _ten_goi(rang_buoc: str) -> str:
    return re.split(r"[\s\[<>=!~;]", rang_buoc, maxsplit=1)[0].lower()


def _module_ngoai_duoc_import() -> set[str]:
    """Module gốc mà script import, trừ thư viện chuẩn, livelift và gói bắt buộc."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    goc: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            goc |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            goc.add(node.module.split(".")[0])
    bat_buoc = {"numpy", "scipy", "pandas", "pydantic", "livelift"}
    return {m for m in goc if m not in sys.stdlib_module_names and m not in bat_buoc}


def test_extra_hinh_ton_tai_va_co_rang_buoc_toi_thieu():
    extras = _extras()
    assert "hinh" in extras, 'pyproject thiếu extra "hinh" cho scripts/ve_hinh_ho_so.py'
    for rb in extras["hinh"]:
        assert ">=" in rb, f"{rb!r}: cần phiên bản tối thiểu (>=), không để trống"


def test_extra_hinh_phu_moi_thu_vien_ve_ma_script_import():
    ngoai = _module_ngoai_duoc_import()
    assert ngoai == set(GOI_CUA_MODULE), (
        f"script import thư viện ngoài chưa có trong bảng ánh xạ: {sorted(ngoai)}"
    )
    khai = {_ten_goi(rb) for rb in _extras()["hinh"]}
    thieu = sorted(GOI_CUA_MODULE[m] for m in ngoai if GOI_CUA_MODULE[m] not in khai)
    assert not thieu, f'extra "hinh" thiếu: {thieu}'


def test_matplotlib_toi_thieu_chay_duoc_voi_numpy_2():
    """numpy ≥ 2 (lõi, ``numpy>=1.26`` cho phép 2.x) cần matplotlib ≥ 3.9 — bản cũ
    hơn build theo ABI numpy 1 và vỡ lúc import."""
    rb = next(r for r in _extras()["hinh"] if _ten_goi(r) == "matplotlib")
    m = re.search(r">=\s*(\d+)\.(\d+)", rb)
    assert m, rb
    assert (int(m.group(1)), int(m.group(2))) >= (3, 9), rb
