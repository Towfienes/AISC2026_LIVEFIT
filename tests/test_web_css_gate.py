"""CỔNG CHẬM: trang chủ phải có CSS THẬT — dựng bản build thật rồi cân tệp.

Ngày 13/09/2026 chủ dự án mở sản phẩm lên và thấy trang chủ hiện **HTML thô,
không có CSS**: ``/_next/static/css/app/layout.css`` trả 404. Trong lúc đó
894 test nhanh, 13 gate chậm, ``tsc --noEmit`` và ``ruff`` đều XANH — không
một cái nào mở trang lên xem nó có mặc quần áo hay không. Nguyên nhân gốc:
nhiều tiến trình ``next dev``/``next build`` chạy song song cùng ghi một thư
mục ``.next`` (``.next/static/css`` rỗng), cộng một tiến trình ``next`` cũ vẫn
giữ cổng 3000 và phục vụ từ thư mục đã bị xoá.

Tệp này là cổng chặn tái diễn, và cố ý đắt (~60-90 giây) vì mọi phép thử rẻ
hơn đều đã trượt:

* ``next build`` THẬT vào thư mục riêng ``LIVELIFT_DIST_DIR`` (không đụng
  ``.next`` của máy chủ dev đang chạy — dùng chung chính là nguyên nhân gốc);
* ``next start``, ``GET /`` phải 200;
* HTML phải có ``<link rel="stylesheet">`` (``rel=preload`` không tính);
* **tải tệp CSS đó về**: 200, > 10 KB, có token ``--canvas`` và ``--brand``.

Và một test nữa chứng minh cổng CÓ RĂNG: cùng bản build ấy, xoá tệp CSS khỏi
thư mục build rồi phục vụ lại — trang chủ vẫn 200, thẻ ``<link>`` vẫn nguyên,
và cổng PHẢI đỏ. Đó chính xác là hình dạng của sự cố 13/09.

Chạy:

    .venv/Scripts/python -m pytest tests/test_web_css_gate.py -q
    .venv/Scripts/python scripts/gate_css_web.py      # cùng mã, chạy tay

Bỏ qua (chứ không giả vờ xanh) khi máy không có node hoặc chưa ``npm install``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WEB = REPO / "web"

_spec = importlib.util.spec_from_file_location(
    "livelift_gate_css_slow", REPO / "scripts" / "gate_css_web.py"
)
assert _spec is not None
assert _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gate
_spec.loader.exec_module(gate)

# Thư mục build riêng của cổng chậm: không đụng `.next` (máy chủ dev), không
# đụng `.next-chay-local` (lệnh chạy hằng ngày), không đụng `.next-gate-css`
# (bản chạy tay) — ba tiến trình có thể cùng chạy mà không giẫm lên nhau.
DIST_TEST = ".next-gate-css-pytest"

thieu_node = not (WEB / "node_modules" / "next").is_dir()
can_node = pytest.mark.skipif(
    thieu_node, reason="web/node_modules/next chưa có — chạy 'npm install' trong web/"
)


@pytest.fixture(scope="module")
def ban_build():
    """Dựng MỘT lần, hai test cùng dùng (build là phần đắt nhất, ~50 giây)."""
    xong, loi, giay, duoi = gate.dung_ban_build(DIST_TEST)
    if not xong:
        gate.don_thu_muc(DIST_TEST)
        pytest.fail(f"'next build' hỏng sau {giay:.1f}s: {'; '.join(loi)}\n{duoi}")
    yield DIST_TEST
    gate.don_thu_muc(DIST_TEST)


@pytest.mark.slow
@can_node
def test_thu_muc_build_co_tep_css(ban_build):
    """Bằng chứng trên đĩa: ngày 13/09 `.next/static/css` RỖNG mà không ai kêu."""
    thu_muc_css = WEB / ban_build / "static" / "css"
    assert thu_muc_css.is_dir(), f"{thu_muc_css} không tồn tại sau khi build xong"
    tep = list(thu_muc_css.rglob("*.css"))
    assert tep, f"{thu_muc_css} không có tệp .css nào"
    assert max(t.stat().st_size for t in tep) > gate.chay_local.CSS_TOI_THIEU_BYTE


@pytest.mark.slow
@can_node
def test_trang_chu_cua_ban_build_that_co_css_that(ban_build):
    """Phép thử đầy đủ: 200 → có thẻ stylesheet → TẢI tệp về → cân và soi token."""
    with gate.may_chu_ban_build(ban_build) as (goc, log):
        len_duoc, ly_do = gate.chay_local.doi_http_200(goc, gate.CHO_START_GIAY, nhip=0.5)
        assert len_duoc, f"trang chủ không trả 200 ({ly_do})\n{gate.chay_local._duoi_log(log)}"
        css = gate.chay_local.kiem_tra_css_cua_trang(goc, timeout=30.0)
    assert css.dat, "TRANG VỠ VÌ THIẾU CSS:\n  - " + "\n  - ".join(css.loi)
    assert css.href is not None
    assert css.so_byte > gate.chay_local.CSS_TOI_THIEU_BYTE


@pytest.mark.slow
@can_node
def test_cong_nay_co_rang_xoa_css_khoi_ban_build_thi_phai_do(ban_build):
    """Kiểm chứng ngược — tái hiện ĐÚNG hình dạng sự cố 13/09.

    Xoá tệp CSS khỏi thư mục build, giữ nguyên mọi thứ khác. Máy chủ vẫn trả
    trang chủ 200 kèm thẻ ``<link>`` trỏ vào tệp đã biến mất — y hệt hôm ấy.
    Đo lại ngày 13/09/2026: trang lỗi 404 của Next dài 7.083 byte, nên cổng
    đỏ vì bốn lẽ độc lập (mã 404, Content-Type là HTML, dưới 10 KB, thiếu
    token). Một cổng không tự chứng minh được là nó bắt được lỗi thì chỉ là
    một dòng xanh vô nghĩa.
    """
    tep_css = sorted((WEB / ban_build / "static" / "css").rglob("*.css"))
    assert tep_css, "không có gì để xoá — bản build đã hỏng từ trước"
    da_luu = {t: t.read_bytes() for t in tep_css}
    try:
        for t in tep_css:
            t.unlink()
        with gate.may_chu_ban_build(ban_build) as (goc, log):
            len_duoc, ly_do = gate.chay_local.doi_http_200(goc, gate.CHO_START_GIAY, nhip=0.5)
            assert len_duoc, f"máy chủ không lên ({ly_do})\n{gate.chay_local._duoi_log(log)}"
            html_200 = True
            css = gate.chay_local.kiem_tra_css_cua_trang(goc, timeout=30.0)
    finally:
        for t, noi_dung in da_luu.items():
            t.write_bytes(noi_dung)

    assert html_200, "trang chủ vẫn phải 200 — đó mới là cái bẫy"
    assert not css.dat, "CỔNG KHÔNG CÓ RĂNG: xoá sạch CSS mà cổng vẫn xanh"
    assert css.href is not None, "thẻ <link> vẫn phải còn — sự cố nằm ở tệp phía sau nó"
    assert any("404" in x or "byte" in x for x in css.loi)
