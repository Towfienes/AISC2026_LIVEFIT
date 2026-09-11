"""Gate cho ``docs/HUONG-DAN-SU-DUNG.md`` — hướng dẫn bấm từng nút có ảnh thật.

Tài liệu này là thứ người dùng (chủ shop, giám khảo) mở đầu tiên, và nó dựa vào
**27 ảnh chụp màn hình** nằm trong ``docs/img/``. Ảnh bị đổi tên hoặc bị dọn đi
sẽ biến cả trang thành một dãy ô vỡ — mà không một test nào khác của kho mã nhìn
thấy, vì không có dòng mã Python/TypeScript nào tham chiếu tới chúng.

Bốn kiểm tra, không cần mạng và không cần server:

1. mọi ``![...](img/...)`` trỏ tới một file CÓ THẬT (và không rỗng);
2. mọi liên kết tương đối trong tài liệu giải được về một file có thật;
3. không có ảnh mồ côi trong ``docs/img/`` — ảnh đã chụp thì phải được dùng,
   nếu không lần dọn kho sau sẽ không ai dám xoá;
4. README trỏ tới hướng dẫn (đường vào của người dùng mới).

Ngoài ra, gate nội dung: các nhãn nút được trích dẫn trong hướng dẫn phải khớp
CHUỖI THẬT trong mã nguồn web — cùng tinh thần contract test web↔API. Hướng dẫn
ghi sai tên nút còn tệ hơn không có hướng dẫn.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GUIDE = DOCS / "HUONG-DAN-SU-DUNG.md"
IMG_DIR = DOCS / "img"
README = ROOT / "README.md"

IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


@pytest.fixture(scope="module")
def guide_text() -> str:
    assert GUIDE.is_file(), f"thiếu hướng dẫn sử dụng: {GUIDE}"
    return GUIDE.read_text(encoding="utf-8")


def _referenced_images(text: str) -> list[str]:
    return IMAGE_RE.findall(text)


def test_moi_anh_duoc_tham_chieu_deu_ton_tai(guide_text: str) -> None:
    refs = _referenced_images(guide_text)
    assert refs, "hướng dẫn phải có ảnh chụp từng bước"
    missing = [r for r in refs if not (DOCS / r).is_file()]
    assert not missing, f"ảnh được tham chiếu nhưng không tồn tại: {missing}"


def test_khong_co_anh_rong(guide_text: str) -> None:
    """Một file PNG 0 byte vẫn 'tồn tại' nhưng hiện ra ô vỡ y hệt file thiếu."""
    empty = [r for r in _referenced_images(guide_text) if (DOCS / r).stat().st_size < 1024]
    assert not empty, f"ảnh rỗng hoặc hỏng (<1KB): {empty}"


def test_moi_lien_ket_tuong_doi_giai_duoc(guide_text: str) -> None:
    broken: list[str] = []
    for link in LINK_RE.findall(guide_text):
        if link.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = (DOCS / link.split("#", 1)[0]).resolve()
        if not target.exists():
            broken.append(link)
    assert not broken, f"liên kết tương đối hỏng trong hướng dẫn: {broken}"


def test_khong_co_anh_mo_coi(guide_text: str) -> None:
    """Ảnh nằm trong docs/img/ mà không tài liệu nào dùng là rác chờ mục nát."""
    used = {Path(r).name for r in _referenced_images(guide_text)}
    # Tài liệu khác cũng được phép dùng chung thư mục ảnh.
    for md in DOCS.rglob("*.md"):
        if md == GUIDE:
            continue
        used |= {Path(r).name for r in _referenced_images(md.read_text(encoding="utf-8"))}
    on_disk = {p.name for p in IMG_DIR.glob("*") if p.is_file()}
    orphans = sorted(on_disk - used)
    assert not orphans, f"ảnh không được tài liệu nào dùng: {orphans}"


def test_readme_tro_toi_huong_dan() -> None:
    text = README.read_text(encoding="utf-8")
    assert "docs/HUONG-DAN-SU-DUNG.md" in text, "README phải trỏ tới hướng dẫn sử dụng"


# ---------------------------------------------------------------------------
# Gate nội dung: nhãn nút trong hướng dẫn phải khớp chuỗi thật trong mã web
# ---------------------------------------------------------------------------

WEB_SRC = ROOT / "web" / "src"

#: (nhãn được trích trong hướng dẫn, file khai báo nhãn đó)
QUOTED_LABELS = [
    ("Bắt đầu xem thử", "app/page.tsx"),
    ("Phân tích", "app/page.tsx"),
    ("Thêm sản phẩm", "app/chay-phien/page.tsx"),
    ("Xong, sang bước 2", "app/chay-phien/page.tsx"),
    ("Tạo phiên", "app/chay-phien/page.tsx"),
    ("Bốc thăm lịch", "app/chay-phien/page.tsx"),
    ("Bắt đầu phát sóng", "app/chay-phien/page.tsx"),
    ("Mở bàn điều khiển", "app/chay-phien/page.tsx"),
    ("Mở màn hình host", "app/chay-phien/page.tsx"),
    ("Chép link", "app/chay-phien/page.tsx"),
    ("Kết thúc phiên", "components/StatusBar.tsx"),
    ("Phiên đang xem", "components/StatusBar.tsx"),
    ("Thực hiện", "components/ActionCard.tsx"),
    ("Bỏ qua", "components/ActionCard.tsx"),
    ("Đã thực hiện", "components/ActionCard.tsx"),
    ("Tạm dừng cuộn", "components/CommentFeed.tsx"),
    ("Sản phẩm đang ghim", "components/HostView.tsx"),
    ("Chưa ghim sản phẩm", "components/HostView.tsx"),
    ("Chưa có phiên nào đang chạy", "app/desk/page.tsx"),
    ("Vẫn mở bàn điều khiển với phiên đã kết thúc", "app/desk/page.tsx"),
    ("THIẾU nguồn", "components/SignalTiles.tsx"),
    ("Báo cáo phiên", "app/ket-qua/page.tsx"),
    ("In / lưu PDF", "app/bao-cao/[id]/page.tsx"),
]


@pytest.mark.parametrize(("label", "rel_path"), QUOTED_LABELS)
def test_nhan_nut_trich_trong_huong_dan_khop_ma_nguon(
    guide_text: str, label: str, rel_path: str
) -> None:
    assert label in guide_text, f"hướng dẫn không còn nhắc nhãn “{label}”"
    source = (WEB_SRC / rel_path).read_text(encoding="utf-8")
    assert label in source, (
        f"hướng dẫn trích nhãn “{label}” nhưng {rel_path} không còn chuỗi đó — "
        "đổi nhãn trên giao diện thì phải cập nhật docs/HUONG-DAN-SU-DUNG.md"
    )


def test_huong_dan_noi_ro_day_la_web_app(guide_text: str) -> None:
    """Câu trả lời đầu tiên người dùng cần: web hay app điện thoại."""
    head = guide_text[:2500]
    assert "WEB APP" in head
    assert "Không phải app điện thoại" in head
    assert "localhost:3000" in head


def test_huong_dan_co_muc_gioi_han_va_muc_ai_dung_man_nao(guide_text: str) -> None:
    assert "Giới hạn hiện tại" in guide_text
    assert "Ai dùng màn nào" in guide_text
    # Ba giới hạn BẮT BUỘC phải được nói thẳng (yêu cầu của gói HUONG-DAN).
    assert "Chưa có đăng nhập" in guide_text
    assert "chưa có bộ thực thi" in guide_text
    assert "Điện thoại chưa dùng được" in guide_text
