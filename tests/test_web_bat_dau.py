"""Gate cho gói WIZARD — trang /bat-dau ("tôi có một buổi live, dùng được gì?").

Trang này tồn tại để trả lời câu hỏi chủ dự án hỏi đi hỏi lại: *"Tôi mở phiên
live bất kỳ của nền tảng nào cũng được và sử dụng sản phẩm — có làm được không?
Hiện tại nếu dùng thì dùng như nào?"* Câu trả lời vốn nằm trong
`docs/nen-tang-ho-tro.md` và `docs/mo-hinh-van-hanh-kol.md`, còn sản phẩm thì
không nói gì — người dùng mở trang chủ ra không biết mình làm được gì.

Rủi ro của một trang như thế KHÔNG phải lỗi kiểu dữ liệu: `tsc --noEmit` đã lo
phần đó, và `Record<ComboKey, Outcome>` còn cưỡng chế đủ 20 ô ngay lúc biên dịch
(thiếu một tổ hợp là lỗi TS2740 — đã kiểm chứng). Rủi ro thật là **nội dung trôi
dần thành lời hứa hão**: một người sửa sau thấy cột TikTok toàn màu đỏ, thấy
"xấu", rồi nới thành "sắp hỗ trợ"; hoặc thêm nền tảng mà bỏ trống phần "không
làm được gì"; hoặc dán cùng một câu trả lời cho hai tổ hợp khác nhau — đúng thứ
trang này sinh ra để xoá bỏ.

Bốn bất biến dưới đây đọc thẳng nguồn trên đĩa, như các gate UI khác:

1. ĐỦ 20 TỔ HỢP, MỖI TỔ HỢP MỘT CÂU TRẢ LỜI RIÊNG — không câu nào trùng câu nào.
2. MỌI TỔ HỢP ĐỀU PHẢI NÓI "KHÔNG LÀM ĐƯỢC GÌ, VÌ SAO" — kể cả ô tốt nhất bảng.
3. HAI RANH GIỚI KHÔNG ĐƯỢC NỚI: TikTok không bao giờ được hứa (hôm nay
   WebSocket 400 10/10 lần, WAF chặn nội dung đã kết thúc, yt-dlp không có bộ
   đọc bình luận TikTok, Research API không mở cho tổ chức Việt Nam); và buổi
   live CỦA NGƯỜI KHÁC không bao giờ chạm tới ĐỀ XUẤT hay THÍ NGHIỆM — không
   điều khiển được buổi phát thì không bốc thăm được, đó là ràng buộc của thiết
   kế thí nghiệm chứ không phải của phần mềm.
4. TRANG PHẢI NẰM TRONG LUỒNG — có lối vào từ trang chủ và từ TopNav, nếu không
   nó chỉ là một tệp không ai tìm thấy, tức chưa lấp được khoảng trống nào.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
SRC = WEB / "src"
DATA = SRC / "lib" / "batdau.ts"
PAGE = SRC / "app" / "bat-dau" / "page.tsx"
VOD = SRC / "components" / "BatDauVod.tsx"
HOME = SRC / "app" / "page.tsx"
TOPNAV = SRC / "components" / "TopNav.tsx"

PLATFORMS = ("youtube", "facebook", "tiktok", "shopee", "khac")
OWNERS = ("toi", "nguoi-khac")
WHENS = ("dang-phat", "da-ket-thuc")
COMBOS = {f"{p}|{o}|{w}" for p in PLATFORMS for o in OWNERS for w in WHENS}

# Mức can thiệp: chỉ đạt được trên buổi live do chính mình vận hành.
INTERVENTION_LEVELS = {"de-xuat", "thi-nghiem"}

# Ba khối cố định của mỗi câu trả lời — thứ tự này là hợp đồng với người đọc.
RESULT_BLOCKS = (
    "Làm được gì ngay bây giờ",
    "Cần gì để lên mức cao hơn",
    "Không làm được gì, và vì sao",
)


def code(src: str) -> str:
    """Nguồn đã bỏ chú thích.

    Cùng lý do với các gate UI khác: `batdau.ts` giải thích chính những phản-mẫu
    bị cấm ("KHÔNG HỨA HÃO", "TikTok không được tô hồng"), nên tìm chuỗi thô sẽ
    bắt nhầm phần giải thích.
    """
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


def _match_brace(src: str, open_at: int) -> int:
    """Vị trí dấu `}` đóng cho dấu `{` tại `open_at`, bỏ qua dấu trong chuỗi."""
    depth = 0
    quote: str | None = None
    i = open_at
    while i < len(src):
        ch = src[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'`":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise AssertionError("không tìm được dấu đóng của khối")


def outcomes() -> dict[str, str]:
    """`{tổ hợp: thân của Outcome}` đọc thẳng từ bảng MATRIX."""
    src = code(DATA.read_text(encoding="utf-8"))
    start = src.index("const MATRIX")
    body = src[start : _match_brace(src, src.index("{", start)) + 1]
    out: dict[str, str] = {}
    for m in re.finditer(r'"([a-z-]+\|[a-z-]+\|[a-z-]+)":\s*\{', body):
        open_at = m.end() - 1
        out[m.group(1)] = body[open_at : _match_brace(body, open_at) + 1]
    return out


def field(block: str, name: str) -> str:
    """Giá trị của một khoá cấp cao nhất trong khối Outcome."""
    m = re.search(rf'(?m)^    {name}:\s*"([a-z-]+)"', block)
    return m.group(1) if m else ""


def test_wizard_sources_are_readable():
    for path in (DATA, PAGE, VOD, HOME, TOPNAV):
        assert path.exists(), f"không tìm thấy {path} — gói WIZARD đã bị đổi cấu trúc?"
    assert "Record<ComboKey, Outcome>" in DATA.read_text(encoding="utf-8"), (
        "bảng phải giữ kiểu Record<ComboKey, Outcome> — đây là thứ bắt TypeScript "
        "cưỡng chế đủ 20 tổ hợp ngay lúc biên dịch"
    )


# ---------------------------------------------------------------------------
# 1. đủ 20 tổ hợp, mỗi tổ hợp một câu trả lời riêng
# ---------------------------------------------------------------------------
def test_the_matrix_covers_every_combination_exactly_once():
    got = outcomes()
    missing = sorted(COMBOS - set(got))
    extra = sorted(set(got) - COMBOS)
    assert not missing, f"thiếu câu trả lời cho tổ hợp: {missing}"
    assert not extra, f"tổ hợp lạ trong bảng: {extra}"
    assert len(got) == 20


def test_every_combination_has_its_own_answer():
    """20 tổ hợp, 20 câu trả lời KHÁC NHAU.

    Đây là lời hứa in ngay trên trang ("Mỗi tổ hợp có một câu trả lời riêng —
    20 tổ hợp, 20 câu trả lời khác nhau"). Hai tổ hợp dùng chung một câu là dấu
    hiệu ai đó vừa gộp hai tình huống khác nhau vào một lời khuyên chung chung.
    """
    seen: dict[str, str] = {}
    clashes: list[str] = []
    for combo, block in outcomes().items():
        m = re.search(r"headline:\s*(.*?)\n\s*now:", block, re.S)
        assert m, f"{combo}: không đọc được headline"
        text = " ".join(m.group(1).split())
        if text in seen:
            clashes.append(f"{seen[text]} và {combo}")
        seen[text] = combo
    assert not clashes, "Hai tổ hợp trở lên dùng chung một câu trả lời:\n" + "\n".join(clashes)


def test_every_outcome_carries_the_full_shape():
    for combo, block in outcomes().items():
        for key in ("level:", "ceiling:", "headline:", "now:", "upgrade:", "blocked:"):
            assert re.search(rf"(?m)^    {re.escape(key)}", block), f"{combo}: thiếu khoá {key!r}"
        assert field(block, "level"), f"{combo}: không đọc được level"
        assert field(block, "ceiling"), f"{combo}: không đọc được ceiling"


def test_no_outcome_claims_a_ceiling_below_what_it_already_does():
    order = {"khong": 0, "quan-sat": 1, "de-xuat": 2, "thi-nghiem": 3}
    bad = [
        f"{combo}: level={field(b, 'level')} > ceiling={field(b, 'ceiling')}"
        for combo, b in outcomes().items()
        if order[field(b, "level")] > order[field(b, "ceiling")]
    ]
    assert not bad, "Trần thấp hơn mức đang đạt:\n" + "\n".join(bad)


# ---------------------------------------------------------------------------
# 2. mọi tổ hợp đều phải nói "không làm được gì, vì sao"
# ---------------------------------------------------------------------------
def test_no_outcome_ships_with_an_empty_blocked_list():
    """Kể cả tổ hợp tốt nhất cũng có thứ nó KHÔNG làm được.

    YouTube/của tôi/đang phát là ô mạnh nhất bảng, và nó vẫn không có tín hiệu
    đơn hàng, vẫn không ghim hộ được. Một ô `blocked` rỗng nghĩa là ai đó đã
    ngừng nói phần khó nghe.
    """
    for combo, block in outcomes().items():
        m = re.search(r"(?m)^    blocked:\s*(.*)$", block)
        assert m, f"{combo}: không đọc được blocked"
        assert not re.match(r"\[\s*\]", m.group(1).strip()), (
            f"{combo}: `blocked` rỗng — mọi tổ hợp đều phải nêu ít nhất một thứ "
            "không làm được kèm lý do"
        )


def test_every_blocked_item_gives_a_reason():
    src = code(DATA.read_text(encoding="utf-8"))
    labels = len(re.findall(r"(?m)^\s+label:\s*\"", src))
    whys = len(re.findall(r"(?m)^\s+why:", src))
    assert labels == whys, (
        f"{labels} mục 'không làm được' nhưng chỉ {whys} lý do — mỗi mục phải trả "
        "lời được câu VÌ SAO"
    )


def test_the_page_always_renders_all_three_result_blocks():
    """Ba khối là hợp đồng, không phải tuỳ chọn."""
    src = PAGE.read_text(encoding="utf-8")
    for title in RESULT_BLOCKS:
        assert title in src, f"trang /bat-dau thiếu khối kết quả {title!r}"
    assert code(src).count("<ResultBlock") == 3, (
        "phải dựng đúng ba khối kết quả — thêm/bớt khối là đổi hợp đồng với người đọc"
    )


def test_a_dead_end_still_points_at_the_nearest_alternative():
    """Tổ hợp không làm được thì khối đầu KHÔNG đeo dấu ✓ xanh, và phải đổi tiêu
    đề sang đường thay thế: một dấu tích xanh trên câu "không gì cả" là tín hiệu
    sai, đúng loại hứa hão gói này tồn tại để chặn."""
    raw = PAGE.read_text(encoding="utf-8")
    assert 'outcome.level === "khong"' in code(raw), (
        "khối 'làm được gì ngay' phải phân nhánh theo tổ hợp không làm được"
    )
    assert "đường thay thế gần nhất" in raw, (
        "tổ hợp bế tắc phải chỉ đường thay thế, không được bỏ người dùng ở đó"
    )


def test_an_upgrade_path_always_says_how_long_it_takes():
    """`time: null` nghĩa là KHÔNG có đường lên, và trang phải nói thẳng như vậy.
    Có đường lên thì phải kèm thời gian ước tính — "cần thêm vài thứ" mà không
    nói mất bao lâu là câu trả lời vô dụng."""
    for combo, block in outcomes().items():
        m = re.search(r"(?m)^      time:\s*(null|\"(.*?)\")", block)
        assert m, f"{combo}: phần 'cần gì để lên mức cao hơn' chưa khai `time`"
        if m.group(1) != "null":
            assert m.group(2).strip(), f"{combo}: `time` rỗng — dùng null nếu không có đường lên"
    assert "Không có đường lên từ tổ hợp này" in PAGE.read_text(encoding="utf-8"), (
        "khi `time: null` trang phải in thẳng là không có đường lên"
    )


# ---------------------------------------------------------------------------
# 3. hai ranh giới không được nới
# ---------------------------------------------------------------------------
def test_tiktok_is_never_promised_a_capability():
    bad = [
        f"{combo}: level={field(b, 'level')} ceiling={field(b, 'ceiling')}"
        for combo, b in outcomes().items()
        if combo.startswith("tiktok|") and {field(b, "level"), field(b, "ceiling")} != {"khong"}
    ]
    assert not bad, (
        "TikTok được khai một mức khác 'khong':\n"
        + "\n".join(bad)
        + "\n\nHôm nay không có đường nào: WebSocket 400 10/10 lần, WAF chặn nội "
        "dung đã kết thúc, yt-dlp không có bộ đọc bình luận TikTok, Research API "
        "không mở cho tổ chức Việt Nam. Chỉ nới ô này khi có bằng chứng chạy thật."
    )


def test_someone_elses_live_never_reaches_an_intervention_level():
    """Không điều khiển được buổi phát thì không bốc thăm được.

    Ràng buộc này đến từ thiết kế thí nghiệm, không từ phần mềm: bốc thăm
    BẬT/TẮT phải xảy ra TRƯỚC khi phát sóng và phải can thiệp được vào buổi
    live. Không bản cập nhật nào được nới nó.
    """
    bad = [
        f"{combo}: level={field(b, 'level')} ceiling={field(b, 'ceiling')}"
        for combo, b in outcomes().items()
        if "|nguoi-khac|" in combo
        and INTERVENTION_LEVELS & {field(b, "level"), field(b, "ceiling")}
    ]
    assert not bad, "Buổi live của người khác được khai mức can thiệp:\n" + "\n".join(bad)


def test_a_finished_live_is_never_promised_an_intervention_level():
    """Buổi đã phát xong không bốc thăm ngược lại được.

    Ô "của tôi / đã kết thúc" được phép chỉ đường chuẩn bị cho buổi SAU, nhưng
    trần của CHÍNH buổi này không bao giờ vượt quá QUAN SÁT.
    """
    bad = [
        f"{combo}: level={field(b, 'level')} ceiling={field(b, 'ceiling')}"
        for combo, b in outcomes().items()
        if combo.endswith("|da-ket-thuc")
        and INTERVENTION_LEVELS & {field(b, "level"), field(b, "ceiling")}
    ]
    assert not bad, (
        "Buổi đã kết thúc được khai mức can thiệp — không có cách bốc thăm ngược "
        "về quá khứ:\n" + "\n".join(bad)
    )


# ---------------------------------------------------------------------------
# 4. trang phải nằm trong luồng
# ---------------------------------------------------------------------------
def test_the_wizard_is_reachable_from_the_home_page_and_the_nav():
    # CẬP NHẬT CÓ CHỦ ĐÍCH (gói SKIN, 09/2026 — spec UX-FLOW mục a): nav gộp
    # 7 mục về 5 mục theo pha TRƯỚC/TRONG/SAU live; /bat-dau RỜI KHỎI NAV vì
    # nó là công cụ tra cứu MỘT LẦN, không phải điểm đến hằng ngày. Lối vào
    # của nó bây giờ là CỬA SỐ 1 (nổi bật nhất) trên trang chủ — bất biến
    # "người mới phải thấy được /bat-dau ngay" vẫn giữ, chỉ đổi chỗ đứng.
    assert '"/bat-dau"' in code(HOME.read_text(encoding="utf-8")), (
        "trang chủ phải có lối vào /bat-dau — đây là câu hỏi đầu tiên của mọi "
        "người dùng mới; khi rời nav thì cửa trên trang chủ là lối vào duy nhất"
    )
    topnav = code(TOPNAV.read_text(encoding="utf-8"))
    assert '"/bat-dau"' not in topnav, (
        "nav v2 chỉ còn 5 mục theo pha (spec UX-FLOW a) — /bat-dau đã rời nav "
        "một cách CÓ CHỦ ĐÍCH; nếu muốn đưa lại phải sửa spec trước"
    )
    # Năm mục theo việc — đúng cấu trúc pha TRƯỚC/TRONG/SAU của spec.
    for href in ('"/"', '"/chay-phien"', '"/desk"', '"/replay"', '"/ket-qua"'):
        assert href in topnav, f"nav v2 thiếu mục {href}"
    assert '"/host"' not in topnav, (
        "màn hình người dẫn (bị làm mù) không được nằm trên nav — lối vào là "
        "nút 'Mở màn hình người dẫn' từ Chuẩn bị phiên / Bàn trợ live"
    )


def test_the_wizard_asks_exactly_three_questions_and_takes_no_typing():
    src = code(PAGE.read_text(encoding="utf-8"))
    assert src.count("<Question") == 3, (
        "đúng ba câu hỏi: của ai / nền tảng nào / đang phát hay đã kết thúc"
    )
    # Mọi lựa chọn là một nút bấm. Ô dán link YouTube nằm trong BatDauVod và chỉ
    # hiện ở tổ hợp cần tới nó, nên chính trang wizard không có ô gõ chữ nào.
    assert "<input" not in src, "ba câu hỏi phải bấm là xong — không ô gõ chữ nào trên wizard"
    assert "aria-pressed" in src, "nút lựa chọn phải công bố trạng thái chọn cho trình đọc màn hình"


def test_the_answer_is_a_shareable_link():
    """Mỗi tổ hợp là một URL: gửi câu trả lời cho đồng đội là gửi một cái link,
    không phải một đoạn 'bấm cái này rồi bấm cái kia'."""
    src = code(PAGE.read_text(encoding="utf-8"))
    assert "history.replaceState" in src, "lựa chọn phải được ghi lên URL"
    assert "parseQuery(" in src, "trang phải đọc lại lựa chọn từ URL khi mở bằng link"
    data = code(DATA.read_text(encoding="utf-8"))
    for key in ('"cua"', '"nen"', '"khi"'):
        assert key in data, f"thiếu tham số URL {key}"


def test_the_vod_box_reuses_the_existing_api_contract():
    """Ô dán link nạp qua đúng hợp đồng sẵn có (POST /replays/youtube →
    GET /replays/jobs/{id}); gói này không mở đường API mới nào."""
    src = code(VOD.read_text(encoding="utf-8"))
    for fn in ("submitYoutubeReplay", "getReplayJob"):
        assert fn in src, f"ô dán link phải dùng lại {fn}() của api.ts"
    assert "mode=analysis" in src, "phiên nạp từ VOD là phiên QUAN SÁT — phải mở ở chế độ phân tích"
