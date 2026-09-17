"""Gate cho gói WIZARD — /chay-phien thành wizard từng-bước-một.

Trang này là CỔNG VÀO của toàn bộ giá trị thí nghiệm và từng bị người thật chê
"quá khó sử dụng": bắt tự nghĩ "Mã SP", 5 ô nhập chỉ có placeholder, chữ
seed/độ dài khối phơi mặc định, và kết thúc phiên bằng một LỆNH TERMINAL in
ngay trên UI. Gói WIZARD (spec UX-FLOW e1 + critic sản phẩm ưu tiên #5) đập lại
thành 4 bước mỗi-lần-một-màn.

Rủi ro thật của một wizard không phải lỗi kiểu dữ liệu (tsc lo rồi) mà là TRÔI
DẦN VỀ LỐI CŨ: ai đó "tiện tay" thêm lại ô Mã SP, in lại một lệnh terminal cho
nhanh, hay bỏ khối giải thích để màn gọn hơn. Các bất biến dưới đây đọc thẳng
nguồn trên đĩa như mọi gate UI khác, mỗi bất biến gắn với một lý do sản phẩm
cụ thể — sửa chúng thì phải sửa spec trước.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
SRC = WEB / "src"
PAGE = SRC / "app" / "chay-phien" / "page.tsx"
API_TS = SRC / "lib" / "api.ts"
COPY_TS = SRC / "lib" / "copy.ts"
DESK_PAGE = SRC / "app" / "desk" / "page.tsx"
USE_DESK = SRC / "lib" / "useDesk.ts"


def code(src: str) -> str:
    """Nguồn đã bỏ chú thích — comment được phép nhắc phản-mẫu bị cấm."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


def page_src() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_wizard_sources_are_readable():
    for p in (PAGE, API_TS, COPY_TS, DESK_PAGE, USE_DESK):
        assert p.exists(), f"không tìm thấy {p} — gói WIZARD đã bị đổi cấu trúc?"


# ---------------------------------------------------------------------------
# 1. mỗi lần một bước — không đổ 4 thẻ cùng lúc
# ---------------------------------------------------------------------------
def test_the_wizard_renders_one_step_at_a_time():
    """4 bước phải nằm sau điều kiện `step === n` — người mới chỉ thấy MỘT
    việc mỗi lúc (progressive disclosure, spec UX-FLOW N3). Quay lại kiểu trải
    cả 4 khối là quay lại đúng màn hình bị chê "quá khó sử dụng"."""
    src = code(page_src())
    for n in (1, 2, 3, 4):
        assert f"step === {n} ?" in src, (
            f"bước {n} không còn được render theo điều kiện `step === {n}` — "
            "wizard phải hiện đúng một bước mỗi lúc"
        )
    for label in ('"Sản phẩm"', '"Bốc thăm"', '"Lên sóng"'):
        assert label in src, (
            f"thanh tiến độ 4 bước mất nhãn {label} (Sản phẩm/Buổi live/Bốc thăm/Lên sóng)"
        )


def test_every_step_explains_why_it_exists():
    """Mỗi bước một dòng "Vì sao cần bước này?" (yêu cầu #2 của gói) — đây là
    lớp tự-giải-thích thay cho tài liệu rời."""
    src = code(page_src())
    assert src.count("<WhyStep>") == 4, (
        "phải có đúng 4 khối <WhyStep> — mỗi bước một lời giải thích, "
        f"hiện đếm được {src.count('<WhyStep>')}"
    )
    assert "Vì sao cần bước này?" in page_src()


# ---------------------------------------------------------------------------
# 2. không bắt người bán nghĩ mã, không bắt gõ lệnh terminal
# ---------------------------------------------------------------------------
def test_the_seller_never_types_a_product_code():
    """Mã sản phẩm TỰ SINH từ tên (slug) — ô "Mã SP" là thứ đầu tiên bị người
    thật chê và đã bị bỏ CÓ CHỦ ĐÍCH; thêm lại là đổi spec."""
    # code(): comment đầu file ĐƯỢC PHÉP nhắc tên phản-mẫu bị cấm ("Mã SP")
    # để giải thích vì sao nó bị bỏ — chỉ phần render mới bị soi.
    src = code(page_src())
    assert "Mã SP" not in src, "ô 'Mã SP' đã quay lại — người bán không phải nghĩ mã"
    assert "function slugify" in src, "thiếu hàm slugify — mã sản phẩm phải tự sinh từ tên"
    assert "uniqueSlug(" in src, "createProduct phải dùng uniqueSlug(name) làm product_id"
    assert not re.search(r"product_id:\s*newProduct", src), (
        "product_id không được lấy từ ô nhập của người dùng"
    )


def test_no_terminal_command_or_endpoint_ever_reaches_the_seller():
    """Gate G3 của spec UX-FLOW cho trang này: không lệnh CLI, không tên
    endpoint, không hướng dẫn docker trên màn hình người bán. QC chạy phía máy
    chủ khi đọc báo cáo — người bán chỉ bấm nút."""
    raw = page_src()
    for bad in ("livelift-qc", "docker compose", "curl", "POST /", "NEXT_PUBLIC"):
        assert bad not in raw, (
            f"chuỗi kỹ thuật {bad!r} xuất hiện trên /chay-phien — "
            "ngôn ngữ terminal/endpoint bị cấm trên màn người bán (spec d4/G3)"
        )


def test_sample_product_button_exists_for_demo():
    """Nút "Dùng sản phẩm mẫu" — người xem thử không có gì để gõ vẫn đi hết
    wizard được (yêu cầu #1 của gói)."""
    assert "Dùng sản phẩm mẫu" in page_src()
    assert "fillSample" in code(page_src())


# ---------------------------------------------------------------------------
# 3. minh bạch bốc thăm: dải khối + mã bằng chứng, seed là tuỳ chọn nâng cao
# ---------------------------------------------------------------------------
def test_the_draw_step_shows_the_schedule_and_the_design_hash():
    """Bốc thăm phải TRỰC QUAN (dải khối BlockStrip) và KIỂM CHỨNG ĐƯỢC (mã
    bằng chứng design_hash kèm giải thích 'không ai sửa lịch giữa chừng') —
    đây là chỗ sản phẩm chứng minh nó là thí nghiệm thật chứ không phải đèn
    nhấp nháy."""
    raw = page_src()
    src = code(raw)
    assert "<BlockStrip" in src, "bước 3 phải vẽ dải khối bằng BlockStrip"
    assert "designHash" in src, "mã bằng chứng (design_hash) không còn được hiển thị"
    assert "design_hash" in src, "trang không còn đọc design_hash từ máy chủ"
    assert "Mã bằng chứng" in raw, "khối 'Mã bằng chứng' đã mất tên tiếng người"
    assert "không ai sửa lịch giữa chừng" in raw, (
        "mã bằng chứng phải kèm giải thích vì sao nó đáng tin"
    )


def test_seed_and_block_length_hide_behind_advanced_options():
    """Seed/độ dài khối là tuỳ chọn NÂNG CAO (spec N3): mặc định là đủ, không
    phơi thuật ngữ trần ra màn chính."""
    raw = page_src()
    assert "Tuỳ chọn nâng cao" in raw, "seed/độ dài khối phải nằm sau 'Tuỳ chọn nâng cao'"
    # seed chỉ được xuất hiện có giải thích (Term) — không bao giờ là nhãn trần.
    assert "Mã bốc thăm (seed)" in raw or "mã kiểm chứng lịch" in raw.lower()


# ---------------------------------------------------------------------------
# 4. trạng thái sống sót qua refresh; phiên planned mở lại đúng bước
# ---------------------------------------------------------------------------
def test_wizard_state_survives_a_refresh():
    src = code(page_src())
    assert "ll.chayphien.v1" in src, "khoá localStorage của wizard đã đổi tên?"
    assert "localStorage.setItem" in src, "wizard không còn ghi trạng thái xuống localStorage"
    assert "localStorage.getItem" in src, "wizard không còn đọc lại trạng thái từ localStorage"
    assert "history.replaceState" in src, "bước hiện tại phải được ghi lên URL (?buoc=)"


def test_a_saved_session_resumes_at_the_right_step_from_server_truth():
    """Máy chủ là nguồn sự thật khi khôi phục: planned → bước 3 (chưa bốc),
    scheduled → bước 3/4, live → bước 4, ended/cancelled → làm lại từ đầu.
    Thiếu nhánh nào là người dùng refresh xong rơi vào bước sai."""
    src = code(page_src())
    for status in ('"planned"', '"ended"', '"cancelled"', '"live"'):
        assert f"=== {status}" in src or f"status === {status}" in src, (
            f"logic khôi phục thiếu nhánh trạng thái {status}"
        )
    assert "getSchedule(" in src, "khôi phục phiên scheduled phải tải lại lịch từ máy chủ"


# ---------------------------------------------------------------------------
# 5. lỗi máy chủ đến tay người bán NGUYÊN VĂN tiếng Việt, không lỗi kỹ thuật
# ---------------------------------------------------------------------------
def test_api_client_extracts_the_servers_vietnamese_detail():
    """Backend trả 400 kèm `detail` tiếng Việt CÓ GỢI Ý SỬA (vd cấu hình lịch
    không khả thi). api.ts phải đọc detail đó thay vì ném 'API 400 Bad
    Request' — nuốt câu gợi ý của máy chủ là vứt câu trả lời tốt nhất người
    dùng có thể nhận."""
    src = code(API_TS.read_text(encoding="utf-8"))
    m = re.search(r"async function request<", src)
    assert m, "api.ts không còn hàm request()"
    body = src[m.start() : src.index("\n}\n", m.start()) + 3]
    assert "detail" in body, "request() không còn đọc `detail` từ body lỗi"
    assert "res.json()" in body


def test_the_wizard_translates_technical_errors_into_actions():
    """Chuỗi 'API 400…' hay 'Failed to fetch' không bao giờ được hiện trần —
    viError() dịch chúng thành câu hành động được; thông báo tiếng Việt của
    máy chủ thì hiện nguyên văn."""
    src = code(page_src())
    assert "function viError" in src, "thiếu viError() — lỗi kỹ thuật sẽ hiện trần"
    assert "viError(e)" in src, "khung run() phải đưa mọi lỗi qua viError()"


# ---------------------------------------------------------------------------
# 6. đường đi khép kín: lên sóng xong dẫn thẳng tới ĐÚNG phiên trên desk
# ---------------------------------------------------------------------------
def test_going_live_deep_links_to_the_desk_session():
    src = code(page_src())
    assert "/desk?session=" in src, (
        "bấm 'Bắt đầu phát sóng' phải chuyển tới /desk?session=ID — "
        "không được thả người dùng vào desk rồi bắt tự tìm phiên"
    )
    desk = code(DESK_PAGE.read_text(encoding="utf-8"))
    assert '"session"' in desk, "desk không còn đọc tham số ?session= từ URL"
    use_desk = code(USE_DESK.read_text(encoding="utf-8"))
    assert "preferredSessionId" in use_desk, (
        "useDesk mất tuỳ chọn preferredSessionId — deep link sẽ bị bỏ qua"
    )


# ---------------------------------------------------------------------------
# 7. checklist trước giờ G: trung thực theo ma trận tín hiệu, không hứa hão
# ---------------------------------------------------------------------------
def test_the_preflight_checklist_uses_the_signal_matrix():
    """Checklist bước 4 đọc GET /sessions/{id}/signals — trạng thái THIẾU lấy
    từ máy chủ, không bao giờ tự đoán là có (luật không-bịa-số), kèm câu trấn
    an rằng trước giờ phát nguồn chưa chảy là bình thường.

    CẬP NHẬT CÓ CHỦ ĐÍCH (gói H4, đánh giá UI 17/09): bản trước in lý do
    NGUYÊN VĂN của máy chủ, và nguyên văn đó lộ ghi chú nội bộ ("parser đã
    có, vòng ingest chưa nối", "GIVT-lite", "§4.1") lên màn người bán. Nay lý
    do đi qua lyDoThuong(): nguồn THIẾU đã biết nói bằng câu thường (vẫn nói
    là thiếu), trường hợp khác giữ lời máy chủ, chỉ bỏ phần ngoặc kỹ thuật.
    Hành vi này được chạy thử với lý do THẬT của signals.assess trong
    tests/test_web_wizard_v3.py."""
    raw = page_src()
    src = code(raw)
    assert "getSignalCoverage(" in src, "checklist phải đọc tình trạng tín hiệu thật"
    assert "s.detail" in src, "trường hợp chưa có câu thường phải dùng lý do của máy chủ"
    assert "lyDoThuong(s)" in src, "lý do của máy chủ phải qua lời thường trước khi hiện"
    assert "Màn hình người dẫn" in raw, "checklist thiếu mục màn hình người dẫn"
    assert "bình luận ghim" in raw, "checklist thiếu mục dán link đo vào bình luận ghim"
    assert "<IngestPanel" in src, "checklist thiếu mục nguồn bình luận (bộ thu)"


def test_every_field_on_the_wizard_carries_a_label():
    """5 ô placeholder-không-nhãn là lỗi bị điểm mặt trong spec — mọi ô nhập
    của wizard phải có nhãn nhìn thấy được (label bọc ngoài)."""
    src = code(page_src())
    inputs = len(re.findall(r"<input", src))
    labels = len(re.findall(r"<label", src))
    # checkbox + các ô text đều nằm trong <label>; cho phép chênh lệch 0.
    assert labels >= inputs, (
        f"{inputs} ô nhập nhưng chỉ {labels} nhãn <label> — có ô placeholder trần quay lại?"
    )
    for must in ("Tên sản phẩm", "Giá bán", "Link trang sản phẩm"):
        assert must in page_src(), f"mất nhãn {must!r} trên form sản phẩm"


def test_the_one_line_sentences_come_from_the_shared_copy_file():
    """Câu-một-dòng BẬT/TẮT + link đo + màn người dẫn phải import từ
    lib/copy.ts (single source of truth, spec UX-FLOW mục 0) — không trang nào
    tự viết dị bản."""
    src = code(page_src())
    assert "CAU_MOT_DONG" in src, "/chay-phien không còn dùng câu chuẩn từ copy.ts"
    copy_src = COPY_TS.read_text(encoding="utf-8")
    for key in ("batTat", "linkDo", "manNguoiDan"):
        assert key in copy_src, f"copy.ts thiếu câu chuẩn {key!r}"
