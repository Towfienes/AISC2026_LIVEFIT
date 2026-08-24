"""Regex patterns for Vietnamese PII in livestream comments.

Design bias: RECALL over precision. Over-redacting a fragment of harmless text
costs a little signal; leaking one phone number breaks a hard project rule and
the law (Luật 91/2025/QH15 — online-behavior data is sensitive personal data).

Patterns cover the messy reality of shopping-live comments:
- phones split by spaces/dots ("0 9 0 1 2 3 4 5 6 7", "09.01.23.45.67"),
  letter-O-for-zero ("O9O1234567"), +84 / 84 prefixes;
- order/tracking codes announced with context words or carrier prefixes;
- addresses as street patterns ("số 12/3 đường Lê Lợi") or shipping context +
  administrative unit ("ship về Gò Vấp nha shop");
- names after context words ("tên chị là Nguyễn Thị Hoa") or surname-led
  capitalized sequences.
"""

from __future__ import annotations

import re

# --- Phone -----------------------------------------------------------------
# Candidate: 0 / O / +84 / 84 head, then 9-11 more digit-ish chars, each
# optionally preceded by one separator. Validated later by digit count.
PHONE_RE = re.compile(
    r"""
    (?<![\dA-Za-z])                 # not inside a longer number/word
    (?:\+\s?84|84|[0oO])            # head
    (?:[\s.\-·]?[0-9oO]){8,11}      # body, separators allowed between digits
    (?![0-9oO])
    """,
    re.VERBOSE,
)


def phone_digit_count(candidate: str) -> int:
    """Digits in the candidate after o/O→0 normalization (obfuscation)."""
    return sum(1 for ch in candidate if ch.isdigit() or ch in "oO")


def is_valid_phone(candidate: str) -> bool:
    n = phone_digit_count(candidate)
    # VN mobile: 10 digits (0x) / 11 with +84; landline up to 11; old 11-digit ok.
    return 10 <= n <= 12


# --- Email -----------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# --- Order / tracking codes ------------------------------------------------
# 1) context-triggered: "mã đơn ... ABC123", "vận đơn: SPXVN012..."
ORDER_CONTEXT_RE = re.compile(
    r"""
    (?:mã\s*đơn(?:\s*hàng)?|ma\s*don(?:\s*hang)?|đơn\s*hàng|don\s*hang|
       mã\s*vận\s*đơn|vận\s*đơn|van\s*don|mvđ|mvd|tracking|order|mã\s*kiện|ma\s*kien)
    \s*(?:là|la|số|so|:|\#)?\s*
    (?P<code>[A-Za-z0-9][A-Za-z0-9\-]{4,24})
    """,
    re.VERBOSE | re.IGNORECASE,
)
# 2) carrier-prefixed codes that identify a shipment on their own
ORDER_CARRIER_RE = re.compile(
    r"\b(?:SPXVN|SPX|GHN|GHTK|VTP|VNPOST|J&?T|NJV)[A-Z0-9\-]{6,20}\b", re.IGNORECASE
)
# 3) Shopee-style order ids: yymmdd + uppercase alnum tail
ORDER_SHOPEE_RE = re.compile(r"\b\d{6}[A-Z0-9]{6,12}\b")

# --- Address ---------------------------------------------------------------
_ADDR_TAIL = r"[^,.;!?\n]{0,45}"
# "số 12/3 đường Lê Lợi", "12 Nguyễn Trãi", "số nhà 5 ngõ 12"
STREET_NUM_RE = re.compile(
    rf"""
    (?:số\s*(?:nhà)?\s*)?
    \b\d{{1,4}}(?:\s*/\s*\d{{1,4}}){{0,3}}\s*
    (?:đường|duong|phố|pho|ngõ|ngo|hẻm|hem|tổ|ấp|thôn|khu\s*phố|kp|lô|block|
       tòa|toà|chung\s*cư)\b{_ADDR_TAIL}
    """,
    re.VERBOSE | re.IGNORECASE,
)
# keyword-led span: "đường Lê Văn Sỹ", "phường 5", "chung cư Sky Garden"
_ADDR_KEYWORD = (
    r"đường|duong|phố|ngõ|ngo|hẻm|hem|thôn|ấp|khu\s*phố|khu\s*đô\s*thị|kđt|"
    r"chung\s*cư|chung\s*cu|tòa\s*nhà|toà\s*nhà|phường|phuong|xã|quận|quan|"
    r"huyện|huyen|thị\s*trấn|thị\s*xã|t[pt]\.|thành\s*phố|thanh\s*pho|tỉnh|tinh"
)
_ADDR_STOPWORDS = r"nào|gì|gi|này|nay|đó|do|kia|đấy|mình|minh|bạn|ban|ai|đông|vắng"
ADDR_KEYWORD_RE = re.compile(
    rf"""
    \b(?:{_ADDR_KEYWORD})\s+
    (?!(?:{_ADDR_STOPWORDS})\b)
    [^\s,.;!?\n]{{1,25}}(?:\s+[^\s,.;!?\n]{{1,25}}){{0,3}}
    """,
    re.VERBOSE | re.IGNORECASE,
)
# shipping context immediately before an admin-unit name is built in filter.py
ADDR_CONTEXT_WORDS_RE = re.compile(
    r"(?:ship|giao|gửi|gui|chuyển|chuyen|về|ve\b|ở|tại|tai\b|đến|den\b|quê|que\b|từ|tu\b)\s*$",
    re.IGNORECASE,
)
# explicit address announcement: "địa chỉ: 45 Nguyễn Trãi Thanh Xuân".
# Guards: (a) negative lookbehind for "[" so the [ĐỊA CHỈ] replacement token
# never re-triggers (idempotency); (b) the captured tail excludes brackets;
# (c) short triggers (đc, add) require a colon to avoid "đc" ≈ "được" slang.
ADDR_ANNOUNCE_RE = re.compile(
    r"(?<!\[)(?:(?:địa\s*chỉ|dia\s*chi)\s*:?|(?:đ\/?c|add)\s*:)\s*[^,.;!?\n\[\]]{4,60}",
    re.IGNORECASE,
)

# --- Person names ----------------------------------------------------------
_VN_SURNAMES = (
    "Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô|Dương|Lý|"
    "Đinh|Đào|Trịnh|Trương|Lâm|Mai|Tô|Hà|Tạ|Châu|Lưu|Cao|Thái|Quách"
)
_CAP_WORD = r"[A-ZĐÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zà-ỹ]+"
NAME_SURNAME_RE = re.compile(rf"\b(?:{_VN_SURNAMES})\s+{_CAP_WORD}(?:\s+{_CAP_WORD}){{0,3}}")
NAME_CONTEXT_RE = re.compile(
    rf"""
    (?:tên|ten)\s*(?:là|la|em|chị|chi|anh|mình|minh|tôi|toi|khách|khach)?\s*(?:là|la)?\s+
    (?P<name>{_CAP_WORD}(?:\s+{_CAP_WORD}){{0,3}})
    """,
    re.VERBOSE,
)
# honorific + capitalized given name: "chị Hương", "anh Tuấn" (research: ~0.7
# recall on names is the honest ceiling for rule-based Vietnamese name PII;
# NER hook can raise it later)
HONORIFIC_NAME_RE = re.compile(
    rf"\b(?:chị|chi|anh|cô|co|chú|chu|bác|bac|bạn|ban|em)\s+(?P<name>{_CAP_WORD}(?:\s+{_CAP_WORD}){{0,2}})"
)
