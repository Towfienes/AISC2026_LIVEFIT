"""Gate tài liệu sau đợt kiểm toán 17/09/2026 — chữ phải khớp mã đang chạy.

Sáu lỗi tài liệu được hai người phản biện xác nhận ngày 17/09. Mỗi lỗi là một
câu từng đúng rồi lỗi thời khi mã đổi, và không test nào nhìn thấy vì không dòng
mã nào đọc tài liệu. Các gate dưới đây lấy **sự thật từ mã** (hằng số, bảng định
tuyến, cấu hình mặc định, tên test có thật) rồi đối chiếu câu chữ, nên khi mã
đổi lần nữa thì test đỏ thay vì tài liệu âm thầm nói sai:

1. ``nen-tang-ho-tro.md`` §4.3 phải kể đủ danh tính bắt buộc của API livestream
   Shopee (có ``user_id``), không tự ghi số test (một nguồn số duy nhất ở §4.4),
   và không còn câu nào nói chữ ký dùng ``shop_id``.
2. ``nen-tang-ho-tro.md`` §0 dòng 1: khi lệnh bật bộ thu luôn đòi token mà web
   không gửi token, câu "người bán tự bật được" phải kèm giới hạn ``INGEST_TOKEN``.
3. ``HUONG-DAN-TEST.md`` §5 và ``TONG-KET-DU-AN.md``: có đường ghi đơn thì không
   được còn "chưa/không có API ghi".
4. ``research/2026-09-17-danh-gia-toan-dien-va-lo-trinh-tu-dong.md``: bảng trạng
   thái chỉ dùng quy ước của chính tài liệu (không "⏳" treo), và mọi tên test
   được viện dẫn làm bằng chứng phải là test có thật.
5. ``06-KHO-MA-VA-MINH-CHUNG.md``: ảnh chụp kho memory bật mặc định thì không
   được nói chế độ memory "mất sạch dữ liệu khi khởi động lại".
"""

from __future__ import annotations

import inspect
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from livelift.api.auth import MUC_DEMO, MUC_TOKEN, liet_ke_route_ghi
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import Settings
from livelift.ingest import shopee

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TESTS = ROOT / "tests"
WEB = ROOT / "web" / "src"

NEN_TANG = DOCS / "nen-tang-ho-tro.md"
HUONG_DAN_TEST = DOCS / "HUONG-DAN-TEST.md"
TONG_KET = DOCS / "TONG-KET-DU-AN.md"
DANH_GIA = DOCS / "research" / "2026-09-17-danh-gia-toan-dien-va-lo-trinh-tu-dong.md"
KHO_MA = DOCS / "competition" / "sang-tao-tre-2026" / "06-KHO-MA-VA-MINH-CHUNG.md"
ENV_EXAMPLE = ROOT / ".env.example"
API_TS = WEB / "lib" / "api.ts"
BAO_CAO_PAGE = WEB / "app" / "bao-cao" / "[id]" / "page.tsx"

INGEST_PATH = "/sessions/{session_id}/ingest"
ORDERS_IMPORT_PATH = "/sessions/{session_id}/orders/import"
ORDERS_PATH = "/sessions/{session_id}/orders"


def read(path: Path) -> str:
    assert path.is_file(), f"thiếu tệp: {path}"
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def section(text: str, start: str, end: str) -> str:
    """Đoạn từ tiêu đề ``start`` tới trước tiêu đề ``end`` (cả hai phải có thật)."""
    i = text.find(start)
    assert i >= 0, f"không tìm thấy mục {start!r}"
    j = text.find(end, i + len(start))
    assert j >= 0, f"không tìm thấy mục {end!r} sau {start!r}"
    return text[i:j]


def code(src: str) -> str:
    """Nguồn TypeScript đã bỏ chú thích — chú thích hay kể lại phản-mẫu."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


@pytest.fixture(scope="module")
def routes_ghi() -> dict[tuple[str, str], str | None]:
    app = create_app(store=InMemoryStore())
    return {(m, r["path"]): r["muc"] for r in liet_ke_route_ghi(app) for m in r["methods"]}


# ---------------------------------------------------------------------------
# 1. Shopee §4.3 — danh tính bắt buộc lấy từ mã, không phải trí nhớ người viết
# ---------------------------------------------------------------------------


def _muc_43() -> str:
    return section(read(NEN_TANG), "### 4.3 Ba câu trả lời cho Shopee", "### 4.4 ")


def test_43_ke_du_danh_tinh_bat_buoc_cua_api_livestream_shopee():
    """Lỗi 17/09: §4.3 (b) chỉ bảo lấy ``shop_id`` + ``access_token``; người làm
    theo bị bộ thu dừng với "Thiếu danh tính Shopee trong .env: SHOPEE_USER_ID"."""
    muc = _muc_43()
    assert "SHOPEE_USER_ID" in shopee.REQUIRED_ENV_LIVESTREAM, "tiền đề test đã đổi — đọc lại §4.3"
    for bien in shopee.REQUIRED_ENV_LIVESTREAM:
        tham_so = bien.removeprefix("SHOPEE_").lower()
        assert f"`{tham_so}`" in muc or f"`{bien}`" in muc, (
            f"§4.3 (b) không nhắc {bien} — mã đòi biến này cho MỌI lời gọi livestream"
        )


def test_43_shop_id_chi_duoc_nhac_nhu_tham_so_ghim():
    muc = _muc_43()
    assert "SHOPEE_SHOP_ID" not in shopee.REQUIRED_ENV_LIVESTREAM
    assert "SHOPEE_SHOP_ID" in shopee.REQUIRED_ENV_SHOW_ITEM
    buoc = re.split(r"\n\s*\d\.\s", muc)
    oauth = [b for b in buoc if "OAuth" in b]
    assert oauth, "§4.3 (b) phải còn bước ủy quyền OAuth"
    for b in oauth:
        assert "`user_id`" in b, "bước OAuth phải nói nó trả về user_id (user_id_list)"
        if "`shop_id`" in b:
            assert "ghim" in b, "bước OAuth nhắc shop_id thì phải nói rõ nó chỉ để ghim sản phẩm"


def test_43_khong_tu_ghi_so_test_mot_nguon_so_o_44():
    """§4.3 từng ghi "26 test xanh" trong khi §4.4 đã là 57: hai chỗ ghi cùng
    một con số thì một chỗ sẽ lỗi thời. Số test chỉ nằm ở bảng §4.4, kèm ngày đếm."""
    muc = _muc_43()
    assert not re.search(r"\d+\s+test", muc), "§4.3 không được tự ghi số test — trỏ sang §4.4"
    muc_44 = section(read(NEN_TANG), "### 4.4 ", "**Danh tính cần có trong `.env`:**")
    m = re.search(
        r"`tests/test_ingest_shopee\.py` \| \*\*\d+ test\*\* "
        r"\(đếm \d{2}/\d{2}/\d{4} tại commit `(?P<commit>[0-9a-f]{7,40})`\)",
        muc_44,
    )
    assert m, (
        "số test Shopee ở §4.4 phải ghi kèm ngày đếm VÀ commit: chỉ ghi ngày thì số đã "
        "cũ ngay khi có bản vá cùng ngày thêm test"
    )
    assert "--collect-only" in muc_44, "§4.4 phải chỉ lệnh đếm số test hiện tại"
    _commit_co_that(m.group("commit"))


def _commit_co_that(commit: str) -> None:
    """Commit được viện dẫn phải có thật trong kho (bỏ qua khi không có git/.git)."""
    git = shutil.which("git")
    if git is None or not (ROOT / ".git").exists():
        pytest.skip("không có git để đối chiếu commit")
    kq = subprocess.run(
        [git, "-C", str(ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        check=False,
        timeout=20,
    )
    if kq.returncode != 0 and (ROOT / ".git" / "shallow").exists():
        pytest.skip("bản clone nông không có commit cũ")
    assert kq.returncode == 0, f"tài liệu viện dẫn commit {commit} không có trong kho"


def test_khong_con_cau_noi_chu_ky_shopee_dung_shop_id():
    """Chữ ký loại "User" không có ``shop_id`` — mọi câu nhắc ký/HMAC cùng
    ``shop_id`` phải là câu lịch sử hoặc phủ định."""
    tham_so_ky = inspect.signature(shopee.sign_request).parameters
    assert "user_id" in tham_so_ky, "tiền đề test đã đổi"
    assert "shop_id" not in tham_so_ky, "tiền đề test đã đổi"
    sai = [
        dong
        for dong in read(NEN_TANG).splitlines()
        if "`shop_id`" in dong
        and re.search(r"HMAC|\bký\b", dong)
        and not re.search(r"không phải|\bcũ\b|trước đó", dong)
    ]
    assert not sai, "câu nói chữ ký Shopee dùng shop_id (sai từ 17/09):\n" + "\n".join(sai)


# ---------------------------------------------------------------------------
# 2. §0 dòng 1 — "người bán tự bật được" phải kèm giới hạn INGEST_TOKEN
# ---------------------------------------------------------------------------


def _web_gui_token() -> bool:
    return "Authorization" in code(read(API_TS))


def test_0_dong_bo_thu_noi_gioi_han_ingest_token(routes_ghi):
    assert routes_ghi.get(("POST", INGEST_PATH)) == MUC_TOKEN, "tiền đề test đã đổi"
    bang = section(read(NEN_TANG), "## 0. Cập nhật 17/09/2026", "\n---\n")
    dong = [d for d in bang.splitlines() if d.startswith("| 1 |")]
    assert len(dong) == 1, "§0 phải còn đúng một dòng #1 về bộ thu chạy nền"
    if _web_gui_token():
        return  # web đã gửi token: giới hạn không còn, câu chữ tự do
    assert "INGEST_TOKEN" in dong[0], (
        "lệnh bật bộ thu luôn đòi token mà web không gửi token — bản công khai trả 401; "
        "§0 dòng 1 phải nói người bán chỉ tự bật được khi máy chủ chưa đặt INGEST_TOKEN"
    )
    assert "401" in dong[0] or "Thiếu hoặc sai token ingest" in dong[0]


# ---------------------------------------------------------------------------
# 3. Đơn hàng — có đường ghi thì không tài liệu sống nào còn nói "chưa có API ghi"
# ---------------------------------------------------------------------------

CHUA_CO_API_GHI = re.compile(r"(chưa|không)\s+có\s+API\s+ghi", re.I)


def _co_duong_ghi_don(routes_ghi) -> bool:
    return ("POST", ORDERS_IMPORT_PATH) in routes_ghi and ("POST", ORDERS_PATH) in routes_ghi


def test_huong_dan_test_dua_nhap_don_csv_vao_muc_dung_duoc(routes_ghi):
    assert _co_duong_ghi_don(routes_ghi), "tiền đề test đã đổi"
    assert routes_ghi[("POST", ORDERS_IMPORT_PATH)] in (MUC_TOKEN, MUC_DEMO)
    assert "<OrdersPanel" in code(read(BAO_CAO_PAGE)), "tiền đề: ô nhập CSV nằm ở trang báo cáo"
    muc5 = section(read(HUONG_DAN_TEST), "## 5. Bảng khả năng", "## 6. ")
    dung_duoc = section(muc5, "### Dùng được ngay trên giao diện", "### Chỉ dùng được bằng lệnh")
    chua_co = muc5[muc5.index("### Chưa có") :]
    assert not CHUA_CO_API_GHI.search(muc5), "§5 vẫn nói đơn hàng chưa có API ghi"
    assert "order_event" not in chua_co
    loi = "nhập đơn CSV ở trang Báo cáo phiên phải nằm trong 'Dùng được ngay trên giao diện'"
    assert "Nhập đơn" in dung_duoc, loi
    assert "orders/import" in dung_duoc, loi
    if not _web_gui_token():
        assert "INGEST_TOKEN" in muc5, "§5 phải nói giới hạn của bản có INGEST_TOKEN"


def test_tong_ket_khong_con_viec_ghi_don_chua_co_api(routes_ghi):
    assert _co_duong_ghi_don(routes_ghi), "tiền đề test đã đổi"
    text = read(TONG_KET)
    sai = [d for d in text.splitlines() if CHUA_CO_API_GHI.search(d)]
    assert not sai, "TONG-KET vẫn ghi đơn hàng chưa có API ghi:\n" + "\n".join(sai)
    dong = [d for d in text.splitlines() if d.startswith("| Ghi đơn hàng vào hệ thống")]
    assert len(dong) == 1, "TONG-KET phải còn đúng một việc P1 về ghi đơn hàng"
    assert "ĐÃ CÓ" in dong[0]
    assert "Còn thiếu" in dong[0]


# ---------------------------------------------------------------------------
# 4. Bản đánh giá 17/09 — trạng thái theo quy ước, bằng chứng là test có thật
# ---------------------------------------------------------------------------

NHAN_TRANG_THAI = ("ĐÃ SỬA", "MỘT PHẦN", "CÒN MỞ", "GIỚI HẠN NỀN TẢNG")


def _o_trang_thai(muc: str) -> list[tuple[str, str]]:
    """(tên lỗi, ô trạng thái) của mọi hàng bảng có cột trạng thái cuối."""
    hang: list[tuple[str, str]] = []
    for d in muc.splitlines():
        if not d.startswith("| ") or set(d) <= set("|- "):
            continue
        o = [c.strip() for c in d.strip().strip("|").split("|")]
        if o[0] in ("#", "Lỗi", "Vấn đề"):
            continue
        hang.append((o[1] if o[0].isdigit() else o[0], o[2] if o[0].isdigit() else o[-1]))
    return hang


def test_danh_gia_1709_khong_con_trang_thai_treo():
    """ "⏳ đang sửa trong đợt này" lỗi thời ngay khi đợt kết thúc — và nó không
    nằm trong quy ước trạng thái mà chính mục 2 của tài liệu khai."""
    text = read(DANH_GIA)
    for nhan in NHAN_TRANG_THAI:
        assert f"**{nhan}**" in text, f"quy ước trạng thái phải khai {nhan}"
    for start, end in (
        ("### 2.1 ", "### 2.2 "),
        ("### 2.2 ", "### 2.3 "),
        ("### 2.4 ", "### 2.5 "),
    ):
        hang = _o_trang_thai(section(text, start, end))
        assert hang, f"bảng {start.strip()} rỗng"
        sai = [f"{ten} → {o}" for ten, o in hang if not o.lstrip("*").startswith(NHAN_TRANG_THAI)]
        assert not sai, f"{start.strip()}: ô trạng thái ngoài quy ước:\n" + "\n".join(sai)


def test_danh_gia_1709_moi_test_duoc_vien_dan_deu_co_that():
    text = read(DANH_GIA)
    vien_dan = set(re.findall(r"`(test_\w+)`", text))
    assert vien_dan, "bảng trạng thái ĐÃ SỬA phải viện dẫn test hồi quy"
    co_that = set()
    for f in TESTS.glob("test_*.py"):
        co_that |= set(re.findall(r"(?m)^def (test_\w+)\(", f.read_text(encoding="utf-8")))
    thieu = sorted(vien_dan - co_that)
    assert not thieu, "tài liệu viện dẫn test không tồn tại:\n" + "\n".join(thieu)


# ---------------------------------------------------------------------------
# 5. Kho memory có ảnh chụp mặc định — không được gọi là "mất sạch"
# ---------------------------------------------------------------------------


def test_kho_ma_noi_dung_muc_mat_cua_che_do_memory():
    mac_dinh = Settings.model_fields
    assert mac_dinh["store_snapshot_enabled"].default is True, "tiền đề test đã đổi"
    chu_ky = mac_dinh["store_snapshot_interval_s"].default
    assert re.search(r"(?m)^STORE_SNAPSHOT_ENABLED=true\s*$", read(ENV_EXAMPLE)), (
        "tiền đề: .env.example bật ảnh chụp"
    )
    dong = [d for d in read(KHO_MA).splitlines() if "STORE_BACKEND=memory" in d]
    assert dong, "mục A.8 phải còn dòng về chạy ngoài Docker với STORE_BACKEND=memory"
    for d in dong:
        loi = "câu về chế độ memory phải nói có ảnh chụp và mức mất tối đa một chu kỳ"
        assert "ảnh chụp" in d, loi
        assert f"{chu_ky:g} giây" in d, loi
        if "mất sạch" in d:
            assert "đính chính" in d.lower() or "sai" in d, (
                "chỉ được nhắc 'mất sạch' như câu cũ đã đính chính"
            )


def test_kho_ma_khong_con_xep_muc_3_la_viec_chan_mat_du_lieu():
    """Đính chính bảng A.8 phải đi tới mọi chỗ trích lại thứ tự ưu tiên của nó.

    Sót 17/09: dòng A.8 #3 và câu **Ưu tiên** đã sửa, nhưng việc C.3 #1 vẫn ghi
    "ưu tiên #3 mất-dữ-liệu, #2 fail-khởi-động" — người đọc mục việc cần làm vẫn
    sửa README như thể chế độ memory mất sạch dữ liệu.
    """
    assert Settings.model_fields["store_snapshot_enabled"].default is True, "tiền đề test đã đổi"
    text = read(KHO_MA)
    sai = [
        d
        for d in text.splitlines()
        if re.search(r"#3\s*(\(|—|-|:)?\s*mất[- ]dữ[- ]liệu", d) and "đính chính" not in d.lower()
    ]
    assert not sai, "vẫn gọi A.8 #3 là việc mất dữ liệu:\n" + "\n".join(sai)
    trich_uu_tien = [
        d
        for d in text.splitlines()
        if "#2" in d and "#3" in d and re.search(r"ưu tiên", d, re.I) and "A.8" in d
    ]
    trich_uu_tien += [d for d in text.splitlines() if d.startswith("**Ưu tiên:**")]
    assert trich_uu_tien, "tiền đề: phải còn câu ưu tiên của bảng A.8"
    for d in trich_uu_tien:
        assert d.index("#2") < d.index("#3"), f"#3 không còn đứng trước #2: {d}"
