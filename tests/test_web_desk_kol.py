"""Gate cho gói UI-KOL: khung xem live + dải thẻ tín hiệu trung thực + /bao-cao.

Ba bất biến mà gói này tồn tại để giữ, đọc thẳng từ nguồn như các gate UI khác
(`tsc --noEmit` không thấy được chúng):

1. VIDEO LÀ NGỮ CẢNH PHỤ TRỢ — đồng hồ khối giữ nguyên vị trí sticky ưu tiên 1
   (gate UI-2 đã khoá); khung video KHÔNG autoplay, thu gọn được, và một phiên
   không có video phải hiện trạng thái tiếng Việt thay vì khung đen câm.
2. KHÔNG BỊA SỐ trên dải thẻ tín hiệu — mỗi ô có đúng 3 trạng thái
   (GIÁ TRỊ / SUY GIẢM / THIẾU); trạng thái THIẾU in chữ "THIẾU nguồn" kèm
   lý do lấy từ ma trận tín hiệu của máy chủ, tuyệt đối không render số 0
   thay cho nguồn không tồn tại.
3. /bao-cao/[id] hiển thị caveat BẮT BUỘC của phân bố ý định, không gắn số
   nhân quả cho phiên quan sát, và ô thiếu in "THIẾU" + lý do.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
SRC = WEB / "src"
DESK_PAGE = SRC / "app" / "desk" / "page.tsx"
LIVE_VIDEO = SRC / "components" / "LiveVideo.tsx"
SIGNAL_TILES = SRC / "components" / "SignalTiles.tsx"
BAO_CAO_PAGE = SRC / "app" / "bao-cao" / "[id]" / "page.tsx"
KET_QUA_PAGE = SRC / "app" / "ket-qua" / "page.tsx"
REPLAY_PAGE = SRC / "app" / "replay" / "page.tsx"
RHYTHM_CHART = SRC / "components" / "RhythmChart.tsx"
USE_DESK = SRC / "lib" / "useDesk.ts"
API_TS = SRC / "lib" / "api.ts"


def code(src: str) -> str:
    """Nguồn đã bỏ chú thích — cùng lý do với các gate UI khác: file giải thích
    chính những phản-mẫu bị cấm, tìm chuỗi thô sẽ bắt nhầm phần giải thích."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


# ---------------------------------------------------------------------------
# 1. khung xem live
# ---------------------------------------------------------------------------


def test_the_video_frame_never_autoplays_and_uses_the_privacy_embed():
    src = code(LIVE_VIDEO.read_text(encoding="utf-8"))
    assert "youtube-nocookie.com/embed/" in src, (
        "khung video phải nhúng qua youtube-nocookie.com — bàn trợ live không "
        "cần cookie theo dõi của YouTube"
    )
    assert "autoplay=1" not in src, (
        "KHÔNG autoplay: tiếng/hình do người vận hành tự bật, video là ngữ "
        "cảnh phụ trợ chứ không phải nội dung chính của bàn"
    )
    m = re.search(r"<iframe[\s\S]*?/>", src)
    assert m, "không đọc được thẻ iframe của khung video"
    assert "title=" in m.group(0), "iframe phải có title tiếng Việt cho trình đọc màn hình"


def test_the_video_frame_collapses_and_remembers_the_choice():
    src = code(LIVE_VIDEO.read_text(encoding="utf-8"))
    for label in ("Mở khung xem live", "Thu gọn"):
        assert label in src, f"thiếu nút {label!r} — video phải nhường chỗ được cho dữ liệu"
    assert "localStorage" in src, "lựa chọn thu gọn phải được nhớ giữa các lần mở bàn"
    assert re.search(r"try\s*\{[^}]*localStorage", src), (
        "localStorage phải nằm trong try/catch — chế độ riêng tư ném lỗi khi truy cập"
    )
    assert "matchMedia" in src, (
        "mặc định phải theo bề rộng màn hình: mở trên màn ≥ xl, thu gọn dưới đó (spec B)"
    )


def test_a_session_without_video_gets_a_reason_not_a_black_frame():
    src = LIVE_VIDEO.read_text(encoding="utf-8")
    assert "Phiên này không có video để nhúng" in src, (
        "session không có video_id phải hiện trạng thái tiếng Việt nói rõ vì sao"
    )


def test_the_desk_wires_the_video_from_the_session_design():
    page = code(DESK_PAGE.read_text(encoding="utf-8"))
    assert "<LiveVideo" in page, "trang /desk không còn dựng khung xem live"
    assert "youtubeVideoId(" in page, (
        "video id phải đi qua youtubeVideoId() — design.video_id trước, "
        "parse source_url sau, null thì tuyên bố thiếu"
    )
    # Đồng hồ khối vẫn đứng trước video trong thứ tự nguồn (ưu tiên 1 tuyệt đối).
    assert page.index("<BlockClock") < page.index("<LiveVideo"), (
        "video là ngữ cảnh phụ trợ — không được đứng trước đồng hồ khối"
    )
    api = code(API_TS.read_text(encoding="utf-8"))
    assert re.search(r"\{11\}", api), (
        "youtubeVideoId phải parse id đúng 11 ký tự — id sai độ dài là video của người khác"
    )


# ---------------------------------------------------------------------------
# 2. dải thẻ tín hiệu — không bịa số
# ---------------------------------------------------------------------------


def test_signal_tiles_declare_the_three_states_and_the_missing_words():
    src = code(SIGNAL_TILES.read_text(encoding="utf-8"))
    m = re.search(r"type TileState = ([^;]+);", src)
    assert m, "SignalTiles phải khai báo kiểu 3 trạng thái"
    for state in ("value", "degraded", "missing"):
        assert f'"{state}"' in m.group(1), f"thiếu trạng thái {state!r}"
    assert "THIẾU nguồn" in SIGNAL_TILES.read_text(encoding="utf-8"), (
        "ô thiếu phải in đúng chữ 'THIẾU nguồn' — đây là điểm khác biệt trung thực"
    )


def test_a_missing_tile_never_renders_a_zero():
    """Ô THIẾU không render số: nhánh missing chỉ in chữ + lý do."""
    src = code(SIGNAL_TILES.read_text(encoding="utf-8"))
    m = re.search(r"tile\.state === \"missing\" \? \(([\s\S]*?)\) : \(", src)
    assert m, "không đọc được nhánh render trạng thái missing"
    branch = m.group(1)
    assert "tile.reason" in branch, "nhánh THIẾU phải in lý do từ ma trận tín hiệu"
    assert "tile.value" not in branch, "nhánh THIẾU không được render giá trị số"
    assert not re.search(r"\?\?\s*0\b", src), (
        "không được thay nguồn thiếu bằng `?? 0` — số 0 giả chính là thứ gói này cấm"
    )


def test_the_tiles_take_their_reasons_from_the_server_matrix():
    src = code(SIGNAL_TILES.read_text(encoding="utf-8"))
    # Lý do của ô người xem / lượt bấm / tim-quà phải lấy từ detail của ma trận
    # (signals.py), không tự bịa chuỗi trong client cho nguồn mà server đã grade.
    assert src.count(".detail") >= 3, (
        "các ô phải dùng nguyên văn lý do tiếng Việt từ GET /sessions/{id}/signals"
    )
    page = code(DESK_PAGE.read_text(encoding="utf-8"))
    assert "getSignalCoverage(" in page, "trang /desk phải tải ma trận tín hiệu từ API"


def test_the_replay_desk_does_not_show_a_fake_viewer_zero_on_the_clock():
    """Phiên replay: CCU quá khứ không tồn tại — đồng hồ khối nhận null (hiện
    '—'), không nhận số 0 giả từ tick placeholder."""
    page = code(DESK_PAGE.read_text(encoding="utf-8"))
    m = re.search(r"viewers=\{([^}]+)\}", page)
    assert m, "không đọc được prop viewers của BlockClock"
    assert "null" in m.group(1), (
        "BlockClock phải nhận viewers=null cho phiên không có nguồn đo người xem"
    )
    clock = (SRC / "components" / "BlockClock.tsx").read_text(encoding="utf-8")
    assert re.search(r"viewers:\s*number \| null", clock), (
        "BlockClock.viewers phải là number | null — Vital hiện '—' cho null"
    )


def test_the_clock_does_not_show_a_fake_clicks_zero_when_no_link_exists():
    """Cùng luật cho lượt bấm/phút: ma trận nói clicks = missing (phiên không
    có link đo) thì đồng hồ khối phải nhận null (hiện '—') — tổng click_count
    của tick chỉ là chỗ trống, hiện 0 sẽ mâu thuẫn với ô THIẾU ngay bên dưới
    (bắt gặp trên desk buổi Achan 11/09)."""
    page = code(DESK_PAGE.read_text(encoding="utf-8"))
    m = re.search(r"clicksPerMin=\{([^}]+)\}", page)
    assert m, "không đọc được prop clicksPerMin của BlockClock"
    assert "honestClicksPerMin" in m.group(1), (
        "BlockClock phải nhận bản đã đối chiếu ma trận (null khi clicks missing)"
    )
    assert re.search(r'"clicks"\s*&&\s*s\.status\s*===\s*"missing"', page), (
        "điều kiện phải đọc từ ma trận tín hiệu của máy chủ, không đoán theo platform"
    )


def test_the_rhythm_chart_draws_no_line_for_a_source_that_does_not_exist():
    """Khung LỚN NHẤT của bàn cũng phải theo luật không-bịa-số.

    Bắt gặp trên desk buổi Achan 11/09: dải thẻ tín hiệu in 'THIẾU nguồn' cho
    người xem và lượt bấm, còn biểu đồ ngay dưới vẫn vẽ hai đường phẳng ở mức
    0 từ chính các tick placeholder đó — hai phát biểu trái ngược nhau trên
    cùng một màn hình. Panel nào không có nguồn thì không được vẽ gì cả.
    """
    raw = RHYTHM_CHART.read_text(encoding="utf-8")
    src = code(raw)
    for prop in ("viewersMissing", "clicksMissing"):
        assert prop in src, f"RhythmChart phải nhận lý do thiếu nguồn qua {prop}"
    for prop, label in (("viewersMissing", "người xem"), ("clicksMissing", "lượt bấm")):
        assert re.search(rf"\{{{prop} \?[\s\S]{{0,200}}?<MissingRow", src), (
            f"panel {label} phải đổi sang dải THIẾU khi ma trận nói nguồn không có"
        )
    assert "THIẾU nguồn" in raw, "dải thiếu phải dùng đúng chữ của thẻ tín hiệu"
    # Nhịp bình luận là tín hiệu THẬT của mọi phiên có chat — luôn được vẽ.
    assert re.search(r'key:\s*"comments"', src), (
        "biểu đồ phải vẽ nhịp bình luận: trên phiên replay đó là đường DUY NHẤT "
        "có số liệu thật, thiếu nó thì khung lớn nhất của bàn trống trơn"
    )


def test_switching_session_resets_the_comment_high_water_mark():
    """Đổi phiên phải trả mốc bình luận về 0.

    Poll chỉ nhận bình luận có offset LỚN HƠN mốc đã thấy. Mốc là ref sống qua
    các lần đổi phiên, nên sau khi xem một buổi DÀI rồi chuyển sang buổi NGẮN
    hơn, không bình luận nào vượt mốc: radar và feed đứng im ở 'Chưa có bình
    luận nào' trên một buổi có hàng nghìn bình luận (bắt gặp trên bàn 11/09 khi
    đổi Trang sức 138 phút → Achan 117 phút). Panel nói SAI còn tệ hơn panel
    trống, nên khoá bằng gate.
    """
    src = code(USE_DESK.read_text(encoding="utf-8"))
    m = re.search(r"useEffect\(\(\) => \{([\s\S]*?)\}, \[sessionId\]\);", src)
    assert m, "không tìm thấy effect reset trạng thái khi đổi phiên"
    body = m.group(1)
    assert "setComments([])" in body, "đổi phiên phải xoá bình luận của phiên cũ"
    assert "lastCommentOffset.current = 0" in body, (
        "đổi phiên phải trả mốc nước cao của bình luận về 0 — nếu không, phiên "
        "ngắn hơn phiên trước sẽ không bao giờ nhận được bình luận nào"
    )


def test_the_desk_feeds_the_chart_from_the_server_signal_matrix():
    page = code(DESK_PAGE.read_text(encoding="utf-8"))
    m = re.search(r"<RhythmChart([\s\S]{0,400}?)/>", page)
    assert m, "không đọc được lời gọi <RhythmChart>"
    for prop in ("viewersMissing=", "clicksMissing="):
        assert prop in m.group(1), f"trang /desk phải truyền {prop} cho biểu đồ nhịp"
    assert re.search(r'missingReason\("ticks"\)', page), (
        "lý do phải lấy từ ma trận tín hiệu của máy chủ, không đoán theo nền tảng"
    )


# ---------------------------------------------------------------------------
# 3. trang /bao-cao/[id]
# ---------------------------------------------------------------------------


def test_bao_cao_page_always_shows_the_intent_caveat():
    src = code(BAO_CAO_PAGE.read_text(encoding="utf-8"))
    assert "phan_bo_y_dinh.caveat" in src, (
        "caveat của phân bố ý định là BẮT BUỘC — precision phụ thuộc tỷ lệ nền "
        "từng lớp (live-fire 19.126 bình luận)"
    )
    i = src.index("phan_bo_y_dinh.caveat")
    region = src[max(0, i - 400) : i]
    assert "<Callout" in region, "caveat phải nằm trong Callout nổi bật, không phải chú thích chìm"


def test_bao_cao_page_renders_gaps_as_thieu_with_reasons():
    src = code(BAO_CAO_PAGE.read_text(encoding="utf-8"))
    assert "THIẾU" in BAO_CAO_PAGE.read_text(encoding="utf-8"), (
        "ô tổng quan thiếu nguồn phải in chữ THIẾU"
    )
    assert "missingReason" in src, "mỗi ô thiếu phải kèm lý do từ tong_quan.thieu"
    assert "tq.thieu" in src, "lý do phải lấy từ chính payload máy chủ, không tự bịa"


def test_bao_cao_page_never_invents_causal_numbers_for_observational_sessions():
    src = code(BAO_CAO_PAGE.read_text(encoding="utf-8"))
    assert '"quan_sat"' in src, "trang phải phân nhánh theo loai_phien"
    assert "không có số nhân quả" in BAO_CAO_PAGE.read_text(encoding="utf-8"), (
        "phiên quan sát phải nói thẳng: không có lịch gán ngẫu nhiên thì không "
        "có số nhân quả nào để hiển thị"
    )
    # Ước lượng chỉ render từ ket_qua_thi_nghiem (đường analyze_outer + khóa §7).
    m = re.search(r"kq\.estimable && kq\.estimate != null", src)
    assert m, "phần nhân quả phải kiểm estimable trước khi render con số"


def test_the_report_is_reachable_from_desk_replay_and_results():
    """Báo cáo phải mở được từ cả ba đường người bán thật sự đi: bàn trợ live
    (đang chạy), phát lại (xem lại buổi cũ) và trang kết quả (danh sách phiên).
    Đường /replay là đường hay dùng nhất cho buổi đã kết thúc."""
    pages = {
        "desk": DESK_PAGE,
        "replay": REPLAY_PAGE,
        "ket-qua": KET_QUA_PAGE,
    }
    for name, path in pages.items():
        raw = path.read_text(encoding="utf-8")
        assert "/bao-cao/" in code(raw), f"trang {name} phải có nút mở /bao-cao/[id]"
        assert "Báo cáo phiên" in raw, f"trang {name} phải gọi nút đó là 'Báo cáo phiên'"


def test_the_replay_report_button_points_at_the_session_being_replayed():
    """Nút trên /replay phải trỏ vào ĐÚNG phiên đang tua (không phải một id
    cứng), và không được hiện khi chưa có phiên — dẫn người bán tới 404 còn
    tệ hơn không có nút."""
    src = code(REPLAY_PAGE.read_text(encoding="utf-8"))
    assert re.search(r"/bao-cao/\$\{rp\.sessionId\}", src), (
        "nút báo cáo trên /replay phải dùng chính rp.sessionId của bản ghi đang phát lại"
    )
    assert re.search(r"rp\.sessionId\s*&&[\s\S]{0,80}?\?", src), (
        "nút phải bị ẩn khi chưa chọn được phiên (mock/đang tải)"
    )
