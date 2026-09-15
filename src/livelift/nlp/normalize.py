"""Chuẩn hoá văn bản chat livestream tiếng Việt + đặc trưng phong cách.

Vì sao module này tồn tại — nói bằng số: bộ phân loại TF-IDF huấn luyện trên
320 câu **tự biên soạn** đạt macro-F1 0,870 trên chính bộ đó nhưng chỉ 0,271
trên chat bán hàng THẬT (``docs/benchmarks/live-fire-achan.md``). Một phần
khoảng cách đó là **hình thái bề mặt**: chat thật có ``CHỮ IN HOA CẢ CÂU``,
``kéeeeeo dàiii``, emoji xen chữ, dấu câu lặp, ký tự full-width, teencode
(``k``, ``bn``, ``dc``, ``j``), và bảng giá do shop tự dán. Bộ biên soạn có
teencode nhưng KHÔNG có phân phối hình thái của chat thật.

Hai nhóm hàm, tách bạch vì chúng phục vụ hai mục đích trái ngược nhau:

``normalize_text``
    Xoá nhiễu hình thái để TF-IDF nhìn thấy *nội dung*. Mất thông tin phong
    cách — đó là chủ ý.

``style_features``
    Giữ lại đúng thông tin phong cách vừa bị xoá, dưới dạng số. Đây là chỗ
    duy nhất trong pipeline có **mô hình về người nói**: bảng giá shop tự dán
    (``bao_gia_shop``) khác bình luận khách ở CHỮ IN HOA + nhiều mốc giá +
    dấu ``||``, chứ không khác ở từ ngữ — cơ chế sai (c) trong live-fire
    08/09 ("không có mô hình về người nói").

Mọi hàm ở đây là **hàm thuần** (HARNESS.md §1): vào chuỗi, ra chuỗi/số.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = [
    "PII_PLACEHOLDERS",
    "STYLE_FEATURE_NAMES",
    "TEENCODE",
    "collapse_elongation",
    "normalize_batch",
    "normalize_text",
    "style_features",
    "style_matrix",
]


# ---------------------------------------------------------------------------
# Từ điển teencode — CỐ TÌNH NHỎ VÀ BẢO THỦ
# ---------------------------------------------------------------------------
# Quy tắc chọn mục: chỉ thêm dạng viết tắt mà (1) xuất hiện thật trong lô
# `data/labeling/`, và (2) có một cách giãn DUY NHẤT trong ngữ cảnh mua bán.
# Những dạng đa nghĩa bị loại có chủ ý: `m` (mình/mày/mét), `e` (em/anh e),
# `s` (sao/sẽ), `t` (tao/tôi) — giãn sai một token cao tần còn hại hơn không
# giãn. Ablation ở `eval_intent.py` đo đúng phần đóng góp của bảng này.
TEENCODE: dict[str, str] = {
    "k": "không",
    "ko": "không",
    "kg": "không",
    "kh": "không",
    "khg": "không",
    "hok": "không",
    "hong": "không",
    "khong": "không",
    "bn": "bao nhiêu",
    "bnhieu": "bao nhiêu",
    "bnh": "bao nhiêu",
    "nhiu": "nhiêu",
    "nhiêu": "nhiêu",
    "j": "gì",
    "ji": "gì",
    "gi": "gì",
    "dc": "được",
    "đc": "được",
    "duoc": "được",
    "đk": "được không",
    "dk": "được không",
    "ntn": "như thế nào",
    "sp": "sản phẩm",
    "vs": "với",
    "vơi": "với",
    "wa": "quá",
    "qa": "quá",
    "qá": "quá",
    "z": "vậy",
    "zay": "vậy",
    "vay": "vậy",
    "ak": "ạ",
    "ah": "ạ",
    "ạk": "ạ",
    "hsd": "hạn sử dụng",
    "ib": "nhắn tin",
    "inbox": "nhắn tin",
    "cmt": "bình luận",
    "ctv": "cộng tác viên",
    "sdt": "số điện thoại",
    "sđt": "số điện thoại",
    "tks": "cảm ơn",
    "thks": "cảm ơn",
    "thanks": "cảm ơn",
    "thank": "cảm ơn",
    "ty": "cảm ơn",
    "hi": "chào",
    "hii": "chào",
    "hello": "chào",
    "halo": "chào",
    "alo": "chào",
    "sz": "size",
    "cs": "có",
    "ce": "chị",
    "chj": "chị",
    "cj": "chị",
    "shjp": "ship",
    "gja": "giá",
    "gía": "giá",
}

PII_PLACEHOLDERS: tuple[str, ...] = (
    "[SĐT]",
    "[ĐỊA CHỈ]",
    "[TÊN]",
    "[MÃ ĐƠN]",
    "[MXH]",
    "[EMAIL]",
)
"""Placeholder do bộ lọc PII ở tầng ingest chèn vào. Chúng phải sống sót qua
chuẩn hoá thành MỘT token nguyên khối: ``[ĐỊA CHỈ]`` là tín hiệu mạnh cho
``hoi_daily``/``van_chuyen``, nhưng nếu bị tách thành "địa" + "chỉ" thì char
n-gram sẽ trộn nó với chữ thường."""

_PII_TOKEN = {p: f" pii{p.strip('[]').replace(' ', '').lower()} " for p in PII_PLACEHOLDERS}

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_ELONG_RE = re.compile(r"(.)\1{2,}", flags=re.UNICODE)
_PUNCT_RUN_RE = re.compile(r"([!?.,~\-_*])\1{1,}")
_SPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[0-9a-zA-ZÀ-ỹ]+", flags=re.UNICODE)

# Mốc giá kiểu chat Việt: "400k", "55 K", "1tr2", "600.000đ", "120 nghìn".
_PRICE_RE = re.compile(
    r"\d[\d.,]*\s*(?:k\b|nghìn|ngàn|tr\b|triệu|củ\b|đ\b|d\b|vnd|₫)",
    flags=re.IGNORECASE | re.UNICODE,
)

# Khối emoji + ký hiệu trang trí hay gặp trong chat (Symbol-other là chính).
_EMOJI_CATEGORIES = frozenset({"So", "Sk"})


def collapse_elongation(text: str) -> str:
    """``kooooo`` -> ``koo``, ``!!!!!`` -> ``!!``.

    Giữ lại HAI ký tự chứ không phải một: độ dài kéo dài là tín hiệu cảm xúc
    thật (``đẹpppp`` khác ``đẹp``), chỉ phần đuôi vô hạn mới là nhiễu làm nổ
    từ vựng char n-gram.
    """
    return _PUNCT_RUN_RE.sub(r"\1\1", _ELONG_RE.sub(r"\1\1", text))


def _expand_teencode(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return TEENCODE.get(match.group(0), match.group(0))

    return _WORD_RE.sub(repl, text)


def normalize_text(
    text: str,
    *,
    nfkc: bool = True,
    lowercase: bool = True,
    elongation: bool = True,
    teencode: bool = True,
    emoji: bool = True,
) -> str:
    """Chuẩn hoá một bình luận về dạng TF-IDF đọc được.

    Từng bước bật/tắt được bằng tham số vì **bảng ablation** trong
    ``docs/competition/sang-tao-tre-2026/03-NLP-NANG-CAP.md`` đo đóng góp của
    từng bước — một hàm chuẩn hoá không tháo rời được là một hàm không kiểm
    chứng được.

    Thứ tự cố ý: NFKC (ký tự full-width ``ｇｉá`` -> ``giá``) → PII placeholder
    thành token nguyên khối → xoá URL → gom ký tự kéo dài → tách emoji ra khỏi
    chữ → hạ chữ thường → giãn teencode. Teencode phải chạy SAU khi hạ chữ
    thường, nếu không ``KO`` sẽ không khớp khoá ``ko``.
    """
    if nfkc:
        text = unicodedata.normalize("NFKC", text)
    for placeholder, token in _PII_TOKEN.items():
        if placeholder in text:
            text = text.replace(placeholder, token)
    text = _URL_RE.sub(" pii_url ", text)
    if elongation:
        text = collapse_elongation(text)
    if emoji:
        # Tách emoji khỏi chữ liền kề để char_wb không dính "ạ🙏" thành một từ.
        text = "".join(
            f" {ch} " if unicodedata.category(ch) in _EMOJI_CATEGORIES else ch for ch in text
        )
    if lowercase:
        text = text.lower()
    if teencode:
        text = _expand_teencode(text)
    return _SPACE_RE.sub(" ", text).strip()


STYLE_FEATURE_NAMES: tuple[str, ...] = (
    "caps_ratio",
    "digit_ratio",
    "emoji_ratio",
    "len_log",
    "n_price_marks",
    "has_pipe_sep",
    "is_shouted_pricesheet",
    "has_question_mark",
    "n_pii_placeholders",
)


def style_features(text: str) -> list[float]:
    """Đặc trưng PHONG CÁCH, tính trên văn bản THÔ (trước chuẩn hoá).

    Trả về vector theo đúng thứ tự :data:`STYLE_FEATURE_NAMES`.

    ``is_shouted_pricesheet`` là đặc trưng "mô hình người nói" rẻ nhất có thể
    làm mà không cần metadata tác giả (nền tảng không trả về vai trò mod cho
    replay): shop dán bảng giá thì viết HOA phần lớn câu **và** nhắc ≥ 2 mốc
    giá, hoặc dùng ``||`` để ngăn nhiều mặt hàng trên một dòng. Khách hỏi giá
    hầu như không bao giờ làm cả hai việc đó cùng lúc.
    """
    stripped = text.strip()
    n = max(len(stripped), 1)
    letters = [ch for ch in stripped if ch.isalpha()]
    caps = sum(1 for ch in letters if ch.isupper()) / max(len(letters), 1)
    digits = sum(1 for ch in stripped if ch.isdigit()) / n
    emoji = sum(1 for ch in stripped if unicodedata.category(ch) in _EMOJI_CATEGORIES) / n
    n_price = len(_PRICE_RE.findall(stripped))
    has_pipe = 1.0 if "||" in stripped or stripped.count("|") >= 2 else 0.0
    shouted_sheet = 1.0 if (caps >= 0.6 and n_price >= 2) or (has_pipe and n_price >= 1) else 0.0
    n_pii = sum(stripped.count(p) for p in PII_PLACEHOLDERS)
    return [
        round(caps, 4),
        round(digits, 4),
        round(emoji, 4),
        round(len(stripped) ** 0.5 / 10.0, 4),
        float(min(n_price, 6)),
        has_pipe,
        shouted_sheet,
        1.0 if "?" in stripped else 0.0,
        float(min(n_pii, 3)),
    ]


# ---------------------------------------------------------------------------
# Bộ chuyển đổi dùng trong sklearn Pipeline
# ---------------------------------------------------------------------------
# CHÚNG PHẢI SỐNG Ở ĐÂY, không phải trong ``eval_intent``. joblib pickle một
# ``FunctionTransformer`` bằng ``__module__`` + ``__qualname__`` của hàm. Khi
# script huấn luyện chạy bằng ``python -m livelift.nlp.eval_intent``, module đó
# mang tên ``__main__``, nên artifact lưu ra tham chiếu ``__main__._normalize_all``
# và **không tiến trình nào khác nạp lại được** — lỗi này đã xảy ra thật ngày
# 14/09 và chỉ lộ ra khi thử nạp artifact từ một tiến trình sạch. Đặt hàm ở một
# module không bao giờ là ``__main__`` là cách sửa tận gốc.


def normalize_batch(texts: list[str]) -> list[str]:
    """``FunctionTransformer`` bước chuẩn hoá — xem :func:`normalize_text`."""
    return [normalize_text(t) for t in texts]


def style_matrix(texts: list[str]):
    """``FunctionTransformer`` khối đặc trưng phong cách — trả mảng numpy."""
    import numpy as np

    return np.asarray([style_features(t) for t in texts], dtype=float)
