"""Gate gói E (đánh giá UI 17/09/2026) — trang chủ, điều hướng, báo cáo phiên.

Mỗi bài dưới đây khoá một lỗi đã thấy tận mắt trên ảnh chụp của đợt đánh giá,
đọc thẳng mã nguồn web (tiền lệ ``test_web_probe.py``) và — ở những chỗ web
dựa vào một câu trả lời cụ thể của máy chủ — kiểm tra luôn đầu máy chủ, để hai
đầu không lệch nhau trong im lặng:

E1  mọi trang báo 404 ``/favicon.ico`` vì ``web/src/app`` không có biểu tượng;
E2  TopNav trên điện thoại 390px là dải cuộn ngang cắt chữ và đẩy chip chế độ
    ra ngoài màn hình;
E3  chip "● PHIÊN THẬT" chấm đỏ — trùng hình và màu đèn ĐANG PHÁT — hiện cả
    khi kho không có phiên nào;
E4  banner kho suy giảm là một khối 7 dòng có tên biến môi trường;
E5  thẻ "BẮT ĐẦU Ở ĐÂY" không có nút chính, tên hành động xem thử lệch giữa
    tiêu đề và nút, số trong dải hero lệch định dạng (19.126 nhưng 1157);
E6  ``/bao-cao/<mã sai>`` báo "kiểm tra máy chủ API đã chạy chưa" dù máy chủ
    đang trả 404, và vẫn hiện nút mở bàn / phát lại / in trên trang lỗi;
E7  báo cáo không có chỗ xem và nhập đơn hàng.
"""

from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SRC = WEB / "src"
APP = SRC / "app"
HOME = APP / "page.tsx"
LAYOUT = APP / "layout.tsx"
ICON = APP / "icon.svg"
NOT_FOUND = APP / "not-found.tsx"
TOPNAV = SRC / "components" / "TopNav.tsx"
MODECHIP = SRC / "components" / "ModeChip.tsx"
TOM_TAT = SRC / "components" / "TomTat3Cau.tsx"
BAO_CAO = APP / "bao-cao" / "[id]" / "page.tsx"
ORDERS = SRC / "components" / "OrdersPanel.tsx"
DONG_BO_SO_TEST = ROOT / "scripts" / "dong_bo_so_test.py"


def read(p: Path) -> str:
    assert p.exists(), f"không tìm thấy {p}"
    return p.read_text(encoding="utf-8")


def code(src: str) -> str:
    """Nguồn đã bỏ chú thích — chú thích giải thích chính các phản-mẫu bị cấm."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<![:\w])//.*$", " ", src)


def opening_tag(src: str, start: int) -> str:
    """Thẻ JSX mở bắt đầu tại ``start``, tới dấu ``>`` không nằm trong ngoặc."""
    depth = 0
    for j in range(start, len(src)):
        ch = src[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == ">" and depth == 0:
            return src[start : j + 1]
    return src[start:]


def flat(text: str) -> str:
    return " ".join(text.split())


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    with TestClient(create_app(store=InMemoryStore())) as c:
        yield c
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# E1 — biểu tượng trang
# ---------------------------------------------------------------------------


def test_e1_app_co_bieu_tuong_svg_mau_brand_tren_nen_toi():
    """Next 14 tự chèn ``<link rel="icon">`` cho ``app/icon.svg``; có thẻ đó thì
    trình duyệt thôi đòi ``/favicon.ico`` (lỗi 404 ở mọi trang lần đầu)."""
    root = ET.fromstring(read(ICON))
    assert root.tag.endswith("svg"), "icon.svg phải là một tệp SVG hợp lệ"
    assert root.get("viewBox"), "biểu tượng cần viewBox để co giãn đúng ở mọi cỡ tab"
    fills = {el.get("fill", "").lower() for el in root.iter()}
    assert "#7c6cff" in fills, "biểu tượng phải dùng màu brand #7c6cff"
    assert "#07080d" in fills, "biểu tượng phải đặt trên nền tối (plane page #07080d)"


def test_e1_layout_khong_de_bieu_tuong_bang_duong_dan_khong_ton_tai():
    """Khai ``icons`` trong metadata sẽ ĐÈ quy ước ``app/icon.svg``; nếu có ai
    khai tay thì tệp được khai phải thật sự tồn tại."""
    layout = code(read(LAYOUT))
    for href in re.findall(r'"/([^"?]+\.(?:ico|png|svg))', layout):
        assert (WEB / "public" / href).exists() or (APP / href).exists(), (
            f"layout trỏ biểu tượng tới /{href} nhưng tệp không tồn tại — lại 404"
        )


# ---------------------------------------------------------------------------
# E2 — TopNav trên điện thoại
# ---------------------------------------------------------------------------


def test_e2_topnav_khong_con_la_dai_cuon_ngang():
    src = code(read(TOPNAV))
    assert "overflow-x-auto" not in src, (
        "nav cuộn ngang cắt chữ 'Chuẩn bị ph…' và đẩy chip chế độ ra ngoài màn 390px"
    )


def test_e2_man_hep_co_nut_mo_dong_danh_sach_dung_chuan_aria():
    src = code(read(TOPNAV))
    m = re.search(r"<button[\s\n]", src)
    assert m, "màn hẹp phải có nút mở/đóng danh sách trang"
    tag = opening_tag(src, m.start())
    assert "aria-expanded={open}" in tag, "nút menu phải công bố trạng thái mở/đóng"
    assert "aria-controls={MENU_ID}" in tag, "nút menu phải trỏ tới danh sách nó điều khiển"
    assert "focus-ring" in tag, "nút menu phải có vòng focus"
    assert "min-h-ctl" in tag or "min-h-tap" in tag, "nút menu phải đạt kích thước bấm WCAG"
    assert "lg:hidden" in tag, "nút menu chỉ dành cho màn hẹp"
    assert "id={MENU_ID}" in src, "danh sách phải mang đúng id mà aria-controls trỏ tới"
    assert "hidden={!open}" in src, "danh sách phải thật sự ẩn khi đóng"
    assert '"Escape"' in src, "Esc phải đóng danh sách (thói quen bàn phím của mọi menu)"
    assert src.count("GROUPS.map") == 2, "đủ mục cho cả hai bố cục: ngang (lg) và danh sách dọc"


def test_e2_chip_che_do_luon_thay_tren_moi_do_rong():
    src = code(read(TOPNAV))
    assert src.count("<ModeChip") == 1, "chip chế độ render đúng một lần"
    i = src.index("<ModeChip")
    wrapper = opening_tag(src, src.rfind("<div", 0, i))
    assert not re.search(r"(?<![:\w-])hidden\b", wrapper), (
        "chip chế độ không được nằm trong khối bị ẩn ở màn hẹp — trang chủ dặn "
        "'chip ở góc phải thanh điều hướng', nên nó phải luôn thấy"
    )
    assert "flex-wrap" in wrapper, "cụm chip + nút phải được xuống dòng thay vì tràn ra ngoài"


# ---------------------------------------------------------------------------
# E3 — chip kho trung tính, nói đúng kho đang chứa gì
# ---------------------------------------------------------------------------


def test_e3_chip_khong_dung_hinh_va_mau_den_dang_phat():
    src = code(read(MODECHIP))
    assert "PHIÊN THẬT" not in src, "chip nói về KHO, không phải về một phiên đang phát"
    assert "bg-live" not in src, "màu đèn ĐANG PHÁT (live) không được dùng cho chip kho"
    assert "border-live" not in src
    assert not re.search(r"rounded-full bg-\w+\"\s*/>", src), (
        "chấm tròn đặc là hình của đèn ĐANG PHÁT — chip kho dùng ký hiệu riêng"
    )


def test_e3_moi_trang_thai_kho_co_chu_va_hinh_rieng():
    src = code(read(MODECHIP))
    block = src[src.index("const KHO_META") : src.index("function ChipGlyph")]
    texts = re.findall(r'text:\s*"([^"]+)"', block)
    glyphs = re.findall(r'glyph:\s*"([^"]+)"', block)
    assert len(texts) >= 4, "tối thiểu: trống / thật / mẫu / cả hai"
    assert len(texts) == len(glyphs), "mỗi trạng thái kho phải có cả CHỮ và HÌNH"
    assert len(set(glyphs)) == len(glyphs), f"hai trạng thái kho trùng hình: {glyphs}"
    assert all("KHO" in t for t in texts), f"chữ trên chip phải nói về kho: {texts}"
    do = "không trạng thái kho nào được tô đỏ — đỏ là đèn ĐANG PHÁT / lỗi"
    assert "text-crit-ink" not in block, do
    assert "critical" not in block, do


def test_e3_kho_rong_duoc_goi_la_trong_khong_phai_that(client):
    """Máy chủ gọi kho RỖNG là ``mode=real``; chip phải nhận ra kho rỗng qua
    ``mode_counts`` và nói TRỐNG. Kiểm hai đầu để hợp đồng không lệch."""
    body = client.get("/health").json()
    assert body["mode"] == "real"
    assert body["mode_counts"] == {"demo": 0, "real": 0}
    src = code(read(MODECHIP))
    assert "c.real === 0 && c.demo === 0" in src
    assert 'return "trong"' in src
    assert "KHO TRỐNG" in src


# ---------------------------------------------------------------------------
# E4 — banner kho suy giảm: một tiêu đề, một việc cần làm, chi tiết gập lại
# ---------------------------------------------------------------------------


def _degraded_banner(src: str) -> str:
    i = src.index('api === "degraded" && (')
    return src[i : src.index("</Callout>", i)]


def test_e4_banner_suy_giam_gon_va_chi_tiet_ky_thuat_nam_trong_details():
    banner = _degraded_banner(code(read(HOME)))
    assert "<details" in banner, "chi tiết kỹ thuật phải gập vào <details>"
    head, detail = banner.split("<details", 1)
    assert head.count("<p") == 2, "phần luôn hiện: đúng 1 dòng tiêu đề + 1 câu việc cần làm"
    assert "Việc cần làm" in head, "câu hành động phải đứng riêng, không chìm giữa đoạn"
    assert "SERVER_STATUS_MESSAGE.degraded" not in head, "câu kỹ thuật dài không được luôn hiện"
    assert "probe?.warning" not in head, "lý do nguyên văn (tên biến môi trường) phải gập lại"
    assert "SERVER_STATUS_MESSAGE.degraded" in detail, "câu chuẩn của máy chủ vẫn phải xem được"
    assert "probe?.warning" in detail, "lý do nguyên văn của máy chủ vẫn phải xem được"
    summary = opening_tag(detail, detail.index("<summary"))
    assert "focus-ring" in summary, "summary phải có vòng focus"
    assert "STORE_" not in head, "không tên biến môi trường nào trên dòng người bán đọc"


# ---------------------------------------------------------------------------
# E5 — phân cấp nút, tên hành động xem thử, định dạng số hero
# ---------------------------------------------------------------------------


def test_e5_the_bat_dau_o_day_mang_nut_chinh_duy_nhat():
    src = code(read(HOME))
    i = src.index('href="/bat-dau"')
    card_01 = src[i : src.index("</Link>", i)]
    assert "BẮT ĐẦU Ở ĐÂY" in card_01
    assert 'buttonCls("primary")' in card_01, "thẻ 'BẮT ĐẦU Ở ĐÂY' phải mang hình nút chính"
    assert src.count('buttonCls("primary")') == 1, "trang chỉ có MỘT nút chính"
    for m in re.finditer(r"<Button[\s\n]", src):
        tag = opening_tag(src, m.start())
        assert 'variant="ghost"' in tag, (
            "các nút còn lại phải là nút phụ — nút đặc ở thẻ demo kéo mắt khỏi thẻ 01"
        )


def test_e5_ten_hanh_dong_xem_thu_thong_nhat():
    render = code(read(HOME))
    assert "Xem thử 30 giây" in render, "tiêu đề thẻ 02 phải là 'Xem thử 30 giây'"
    assert "Bắt đầu xem thử" in render, "nút thẻ 02 cùng gốc 'xem thử' (HDSD bước 1.2 trích)"
    assert "Xem demo" not in render, "tiêu đề cũ 'Xem demo 30 giây' lệch tên với nút"
    assert "Xem thử với dữ liệu mô phỏng" not in render, (
        "một hành động hai tên: nút trang chủ không đổi nhãn theo trạng thái kho"
    )


def test_e5_so_hero_dinh_dang_vi_vn_ma_khong_doi_gia_tri():
    raw = read(HOME)
    render = code(raw)
    m = re.search(r'\{ value: "(\d+)", label: "kiểm thử tự động đang xanh" \}', raw)
    assert m, (
        "hằng PROOF phải giữ đúng mẫu mà scripts/dong_bo_so_test.py ghi đè — "
        "đổi cách HIỂN THỊ, không đổi dữ liệu"
    )
    assert '\\{ value: "' in read(DONG_BO_SO_TEST), "script đồng bộ số test vẫn dùng mẫu này"
    assert "{proofText(p.value)}" in render, "số hero phải đi qua bộ định dạng"
    assert "{p.value}" not in render, "in thô p.value cho ra '1157' cạnh '19.126'"
    fn = render[render.index("function proofText") :]
    fn = fn[: fn.index("\n}")]
    assert "fmtNumber" in fn, "định dạng phải dùng fmtNumber (vi-VN) chung của app"


# ---------------------------------------------------------------------------
# E6 — /bao-cao phân biệt KHÔNG CÓ PHIÊN với MẤT KẾT NỐI
# ---------------------------------------------------------------------------


def test_e6_may_chu_tra_404_tieng_viet_ma_web_nhan_dien(client):
    """Web nhận diện "không có phiên" bằng tiền tố câu 404 của máy chủ — hai đầu
    phải khớp, nếu không trang lại quay về câu nghi ngờ mạng."""
    r = client.get(f"/sessions/{uuid.uuid4()}/bao-cao")
    assert r.status_code == 404
    assert r.json()["detail"].startswith("Không tìm thấy phiên")
    r2 = client.get("/sessions/khong-ton-tai/bao-cao")
    assert r2.status_code == 404
    assert r2.json()["detail"].startswith("Không tìm thấy phiên")
    assert "không hợp lệ" in r2.json()["detail"]

    src = code(read(BAO_CAO))
    assert 'msg.startsWith("Không tìm thấy phiên")' in src
    assert 'msg.includes("không hợp lệ")' in src


def test_e6_chi_cau_404_tieng_viet_moi_la_khong_co_phien():
    """Một 404 TRẦN ("API 404 …" thân không phải JSON, "Not Found" mặc định của
    FastAPI) nghĩa là địa chỉ đó không phục vụ đường báo cáo — phiên có thể vẫn
    còn nguyên. Nói "không có phiên này, thử lại vô ích" lúc đó là nói sai. Còn
    502/503/504 là cổng trung gian không nối được tới máy chủ: mất kết nối."""
    src = code(read(BAO_CAO))
    fn = src[src.index("function phanLoaiLoi") :]
    fn = fn[: fn.index("\n}")]
    m = re.search(r"if \(([^\n]*Không tìm thấy phiên[^\n]*)\) \{", fn)
    assert m, "không đọc được điều kiện nhận diện 'không có phiên'"
    assert "||" not in m.group(1), "chỉ câu 404 tiếng Việt của máy chủ mới là 'không có phiên'"
    assert "404" not in fn, "404 trần không được đọc thành 'không có phiên'"
    gateway = re.search(
        r"if \(/\^API 50\[234\]\\b/\.test\(msg\)\) return \{ loai: \"(\S+)\" \}", fn
    )
    assert gateway, "502/503/504 phải được nhận diện"
    assert gateway.group(1) == "mat-ket-noi"
    assert fn.index("API 50") < fn.index("Không tìm thấy phiên")
    assert 'msg === "Not Found"' in fn, "câu tiếng Anh mặc định không được in lên trang"


def test_e6_ba_loai_loi_ba_cau_khac_nhau():
    src = code(read(BAO_CAO))
    assert "kiểm tra máy chủ API đã chạy chưa và phiên có tồn tại không" not in src, (
        "câu cũ gộp 'máy chủ chết' với 'mã phiên sai' thành một"
    )
    fn = src[src.index("function phanLoaiLoi") :]
    fn = fn[: fn.index("\n}")]
    assert "instanceof TypeError" in fn, "mất kết nối = không nối được…"
    assert '"AbortError"' in fn, "… HOẶC hết giờ"
    for loai in ("khong-co-phien", "mat-ket-noi", "may-chu-loi"):
        assert f'err?.loai === "{loai}"' in src, f"thiếu nhánh hiển thị cho lỗi {loai}"

    def branch(loai: str) -> str:
        i = src.index(f'err?.loai === "{loai}"')
        j = src.find("err?.loai ===", i + 10)
        return src[i : j if j != -1 else src.index("{data && tq", i)]

    khong = branch("khong-co-phien")
    vo_ich = "mã phiên sai thì thử lại vô ích — chỉ đường tới danh sách phiên"
    assert "Thử lại" not in khong, vo_ich
    assert "load()" not in khong, vo_ich
    assert 'href="/ket-qua"' in khong, "trang 'không có phiên' phải chỉ tới danh sách phiên"
    assert "Mất kết nối" in branch("mat-ket-noi")
    assert "load()" in branch("mat-ket-noi"), "mất kết nối thì phải thử lại được"
    assert "err.chiTiet" in branch("may-chu-loi"), "máy chủ báo lỗi thì in nguyên văn câu của nó"


def test_e6_nut_hanh_dong_bi_an_tren_trang_loi():
    src = code(read(BAO_CAO))
    header = src[src.index("<PageHeader") : src.index("</PageHeader>")]
    for label in ("Kết quả phiên này", "Mở bàn trợ live", "Xem phát lại", "In / lưu PDF"):
        assert header.count(label) == 1, f"nút '{label}' phải nằm trong header, đúng một lần"
        li = header.index(label)
        guard = header.rfind("{data ? (", 0, li)
        chi_khi_co = (
            f"nút '{label}' phải chỉ hiện khi đã có báo cáo — trên trang lỗi không có gì "
            "để mở bàn, phát lại hay in"
        )
        assert guard != -1, chi_khi_co
        assert ") : null}" not in header[guard:li], chi_khi_co


# ---------------------------------------------------------------------------
# E7 — OrdersPanel: xem tổng đơn, nhập CSV, trung thực
# ---------------------------------------------------------------------------


def test_e7_bao_cao_dat_orders_panel_theo_dung_phien():
    src = code(read(BAO_CAO))
    assert 'import OrdersPanel from "@/components/OrdersPanel"' in src
    m = re.search(r"<OrdersPanel[\s\n]", src)
    assert m, "trang báo cáo phải render OrdersPanel"
    tag = opening_tag(src, m.start())
    assert "sessionId={data.session_id}" in tag
    assert "isDemo={data.is_demo}" in tag, "phiên mẫu phải đeo nhãn DEMO cả trên khối đơn"


def test_e7_orders_panel_dung_hop_dong_api_va_khong_gui_tep():
    src = code(read(ORDERS))
    for fn in ("getOrders(sessionId)", "importOrdersCsv(sessionId"):
        assert fn in src, f"OrdersPanel phải gọi {fn}"
    for field in ("tong_don", "tong_san_pham", "tong_doanh_thu"):
        assert f"summary.{field}" in src, f"thiếu ô {field}"
    assert "new FileReader()" in src, "chọn tệp chỉ để ĐỌC CHỮ trên trình duyệt"
    # Phản biện 17/09: đọc BYTE rồi giải mã NGAY TRÊN TRÌNH DUYỆT (TextDecoder) —
    # readAsText(f, "utf-8") giải mã hỏng tệp CSV bảng mã 1258 của Excel mà không
    # báo lỗi. Vẫn là đọc chữ tại chỗ, không tải tệp lên (chạy thật ở
    # test_web_phan_bien_1709_khac.py::test_k2_*).
    assert "readAsArrayBuffer(" in src, "chọn tệp chỉ để ĐỌC CHỮ trên trình duyệt"
    assert "new TextDecoder(" in src, "chữ được giải mã trên trình duyệt, không gửi byte đi"
    assert "readAsText(" not in src, 'readAsText(f, "utf-8") nuốt lỗi bảng mã im lặng'
    assert "FormData" not in src, "không bao giờ tải tệp lên"
    assert "multipart" not in src, "không bao giờ tải tệp lên"
    assert re.search(r'<input[^>]{0,160}type="file"', src), "phải chọn được tệp"
    assert "<textarea" in src, "phải dán được nội dung CSV"


def test_e7_orders_panel_noi_that_va_khong_lo_nhanh():
    raw = read(ORDERS)
    src = code(raw)
    assert "Đơn hàng là chỉ số phụ; chỉ số chính là lượt nhấp link đo." in src
    text = flat(src)
    tu_hang = "gợi ý cột phải render từ COT_GOI_Y — tên cột đã đối chiếu với máy chủ, không gõ tay"
    assert "COT_GOI_Y.map(" in src, tu_hang
    assert "c.ten.map(" in src, tu_hang
    assert "THIẾU — không phải bằng 0" in text, "chưa có đơn thì doanh thu là THIẾU, không phải 0 ₫"
    for cam in ("block_id", "BẬT", "TẮT", "assignment"):
        assert cam not in src, f"khối đơn không được đọc/hiện nhánh thí nghiệm: {cam!r}"
    assert not re.search(r"\barm\b", src), "khối đơn không được đọc nhánh (arm) của đơn"
    for f in ("result.nhap_moi", "result.trung_bo_qua", "result.loi.map", "l.dong", "l.ly_do"):
        assert f in src, f"kết quả nhập phải hiện {f}"


def test_e7_hop_dong_nhap_don_hai_dau(client):
    """Tên trường web đọc phải là tên trường máy chủ trả — kiểm bằng một lần
    nhập thật: một đơn mới, một đơn trùng mã, một dòng lỗi có số dòng."""
    sid = client.post(
        "/sessions", json={"platform": "facebook", "planned_duration_min": 30}
    ).json()["session_id"]
    csv = (
        "ma_don,thoi_gian,tong_tien\n"
        "DH1,17/09/2026 20:05,125.000\n"
        "DH1,17/09/2026 20:05,125.000\n"
        "DH2,khong-phai-ngay,99000\n"
    )
    r = client.post(f"/sessions/{sid}/orders/import", json={"csv": csv})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nhap_moi"] == 1
    assert body["trung_bo_qua"] == 1
    assert [loi["dong"] for loi in body["loi"]] == [4]
    assert body["loi"][0]["ly_do"]
    tong = client.get(f"/sessions/{sid}/orders").json()
    assert (tong["tong_don"], tong["tong_san_pham"], tong["tong_doanh_thu"]) == (1, 1, 125000)

    thieu_cot = client.post(f"/sessions/{sid}/orders/import", json={"csv": "a,b\n1,2\n"})
    assert thieu_cot.status_code == 422
    assert "thiếu cột bắt buộc" in thieu_cot.json()["detail"], (
        "OrdersPanel in nguyên văn detail tiếng Việt khi thiếu cột"
    )


def _cot_goi_y(src: str) -> list[tuple[str, bool, list[str]]]:
    """(khoá máy chủ, bắt buộc?, [tên cột]) đọc từ hằng COT_GOI_Y của OrdersPanel."""
    body = src.split("const COT_GOI_Y")[1].split("];")[0]
    return [
        (m.group(1), m.group(2) == "true", re.findall(r'"([^"]+)"', m.group(3)))
        for m in re.finditer(
            r'khoa:\s*"([^"]+)",\s*batBuoc:\s*(true|false),\s*ten:\s*\[([^\]]*)\]', body
        )
    ]


def _phien(client) -> str:
    return client.post(
        "/sessions", json={"platform": "facebook", "planned_duration_min": 30}
    ).json()["session_id"]


def test_e7_goi_y_cot_dung_ten_may_chu_nhan(client):
    """Phản biện gói E: gợi ý cũ in đậm "thời gian đặt đơn" — tên máy chủ không
    nhận — nên người làm đúng theo màn hình bị 422 cả tệp. Mọi tên cột in trên
    màn hình (kể cả dòng mẫu trong ô dán) phải là bí danh trong ``_COT``, và một
    tệp dùng đúng các tên đó phải nhập được thật."""
    from livelift.api.routes.orders import _COT, _chuan_hoa_ten_cot

    src = code(read(ORDERS))
    cot = _cot_goi_y(src)
    assert cot, "không đọc được hằng COT_GOI_Y"
    assert {k for k, bat_buoc, _ in cot if bat_buoc} == {"ts", "gross"}, (
        "cột bắt buộc trên màn hình phải đúng hai cột máy chủ bắt buộc"
    )
    for khoa, _, ten in cot:
        assert ten, f"cột {khoa} phải có ít nhất một tên"
        for t in ten:
            assert _chuan_hoa_ten_cot(t) in _COT[khoa], (
                f"gợi ý in tên cột {t!r} cho {khoa} nhưng máy chủ không nhận tên đó"
            )

    m = re.search(r'placeholder=\{"([^"\\]+)\\n', src)
    assert m, "ô dán phải có dòng tiêu đề mẫu"
    tat_ca_bi_danh = {b for bi_danh in _COT.values() for b in bi_danh}
    for t in m.group(1).split(","):
        assert _chuan_hoa_ten_cot(t) in tat_ca_bi_danh, f"dòng mẫu dùng tên cột lạ {t!r}"

    # Chạy thật: MỖI tên của cột bắt buộc, ghép với tên đầu của các cột còn lại.
    ten_dau = {khoa: ten[0] for khoa, _, ten in cot}
    gia_tri = {"ts": "17/09/2026 20:05", "gross": "125000"}
    for khoa, bat_buoc, ten in cot:
        if not bat_buoc:
            continue
        for i, t in enumerate(ten):
            tieu_de = {**ten_dau, khoa: t}
            csv = (
                f"{tieu_de['order_id']},{tieu_de['ts']},{tieu_de['gross']}\n"
                f"DH-{khoa}-{i},{gia_tri['ts']},{gia_tri['gross']}\n"
            )
            r = client.post(f"/sessions/{_phien(client)}/orders/import", json={"csv": csv})
            assert r.status_code == 200, f"tiêu đề {tieu_de} bị từ chối: {r.text}"
            assert r.json()["nhap_moi"] == 1, r.text


def test_e7_so_dong_loi_khong_bia_khi_may_chu_cat_danh_sach(client):
    """Máy chủ chỉ trả ``loi[:50]``; từ 17/09/2026 nó trả thêm tổng thật ở
    ``tong_loi``. Tệp 60 dòng lỗi phải hiện "Lỗi 60 dòng" (số thật), và với
    máy chủ cũ không có ``tong_loi`` thì đủ trần chỉ được nói "ít nhất"."""
    src = code(read(ORDERS))
    m = re.search(r"const MAX_LOI_HIEN = (\d+);", src)
    assert m, "OrdersPanel phải khai trần danh sách lỗi của máy chủ"
    tran = int(m.group(1))

    csv = "mã đơn,thời gian,tổng tiền\n" + "".join(
        f"X{i},khong-phai-ngay,1\n" for i in range(tran + 10)
    )
    r = client.post(f"/sessions/{_phien(client)}/orders/import", json={"csv": csv})
    assert r.status_code == 200, r.text
    assert len(r.json()["loi"]) == tran, "trần phía web phải khớp đúng trần cắt của máy chủ"
    assert r.json()["tong_loi"] == tran + 10, "máy chủ phải trả tổng số dòng lỗi thật"

    text = flat(src)
    # Có tong_loi thì dùng số thật; thiếu (máy chủ cũ) thì đủ trần là "ít nhất".
    assert 'typeof result.tong_loi === "number"' in text
    assert "chiCanDuoi: result.loi.length >= MAX_LOI_HIEN" in text
    i = text.index("fmtNumber(soLoi(result).so)")
    assert 'soLoi(result).chiCanDuoi ? "Lỗi ít nhất" : "Lỗi"' in text[i - 200 : i], (
        "ô đếm lỗi phải nói 'ít nhất' khi chỉ biết cận dưới"
    )
    assert not re.search(r">\s*Lỗi\s*<span", src), "không còn nhãn 'Lỗi N dòng' vô điều kiện"
    j = text.index("soLoi(result).so > result.loi.length || soLoi(result).chiCanDuoi ? ( <p")
    assert "có thể còn" in text[j : j + 300], (
        "danh sách bị cắt thì nói rõ còn dòng lỗi chưa liệt kê"
    )


# ---------------------------------------------------------------------------
# Thuật ngữ thống nhất trên trang 404 và khối tóm tắt
# ---------------------------------------------------------------------------


def test_trang_404_dung_thuat_ngu_thong_nhat_va_token_chuyen_dong():
    src = code(read(NOT_FOUND))
    assert "Bàn điều khiển" not in src, "thuật ngữ thống nhất là 'Bàn trợ live'"
    assert "Bàn trợ live" in src
    assert "Chuẩn bị phiên" in src
    i = src.index('href: "/bat-dau"')
    assert "bốc thăm" not in src[i : src.index("}", i)].lower(), (
        "/bat-dau là ba câu hỏi, không phải nơi bốc thăm lịch (đó là /chay-phien)"
    )
    link = opening_tag(src, src.index("<Link"))
    assert re.search(r"\btransition\b(?!-)", link) is None, (
        "transition trần dùng thời lượng mặc định"
    )
    assert "duration-short" in link


def test_tom_tat_khong_lan_thuat_ngu_tieng_anh():
    assert "template" not in code(read(TOM_TAT))
