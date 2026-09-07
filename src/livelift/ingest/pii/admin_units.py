"""Vietnamese administrative-unit vocabulary for address detection.

Includes BOTH the pre-2025 63-province names and the post-merger names, because
viewers keep using old names in comments ("ship về Bình Dương nha shop" long
after Bình Dương merged into TP.HCM). District-level names cover the largest
metro areas where most e-commerce buyers are, and CITIES adds well-known
cities/towns whose names differ from their province ("ship về Nha Trang",
"giao về Đà Lạt" — 09/2026 red-team leaks); the address detector combines
this vocabulary with shipping-context words, so coverage does not need to be
exhaustive — street-level patterns are caught by the keyword rules in
``patterns.py``.

Matching is done on lowercased text WITH diacritics; a no-diacritics variant is
generated for each name because comments frequently drop diacritics
("ship ve go vap").
"""

from __future__ import annotations

import re
import unicodedata

PROVINCES: tuple[str, ...] = (
    # post-merger (2025) and pre-merger names, deduplicated
    "an giang",
    "bà rịa - vũng tàu",
    "bà rịa vũng tàu",
    "vũng tàu",
    "bạc liêu",
    "bắc giang",
    "bắc kạn",
    "bắc ninh",
    "bến tre",
    "bình dương",
    "bình định",
    "bình phước",
    "bình thuận",
    "cà mau",
    "cao bằng",
    "cần thơ",
    "đà nẵng",
    "đắk lắk",
    "đắk nông",
    "điện biên",
    "đồng nai",
    "đồng tháp",
    "gia lai",
    "hà giang",
    "hà nam",
    "hà nội",
    "hà tĩnh",
    "hải dương",
    "hải phòng",
    "hậu giang",
    "hòa bình",
    "hưng yên",
    "khánh hòa",
    "kiên giang",
    "kon tum",
    "lai châu",
    "lạng sơn",
    "lào cai",
    "lâm đồng",
    "long an",
    "nam định",
    "nghệ an",
    "ninh bình",
    "ninh thuận",
    "phú thọ",
    "phú yên",
    "quảng bình",
    "quảng nam",
    "quảng ngãi",
    "quảng ninh",
    "quảng trị",
    "sóc trăng",
    "sơn la",
    "tây ninh",
    "thái bình",
    "thái nguyên",
    "thanh hóa",
    "thừa thiên huế",
    "huế",
    "tiền giang",
    "trà vinh",
    "tuyên quang",
    "vĩnh long",
    "vĩnh phúc",
    "yên bái",
    "sài gòn",
    "tphcm",
    "tp hcm",
    "hồ chí minh",
)

DISTRICTS: tuple[str, ...] = (
    # TP.HCM
    "gò vấp",
    "bình thạnh",
    "tân bình",
    "tân phú",
    "phú nhuận",
    "bình tân",
    "thủ đức",
    "củ chi",
    "hóc môn",
    "bình chánh",
    "nhà bè",
    "cần giờ",
    "quận 1",
    "quận 2",
    "quận 3",
    "quận 4",
    "quận 5",
    "quận 6",
    "quận 7",
    "quận 8",
    "quận 9",
    "quận 10",
    "quận 11",
    "quận 12",
    "thủ dầu một",
    "dĩ an",
    "thuận an",
    "biên hòa",
    # Hà Nội
    "hoàn kiếm",
    "ba đình",
    "đống đa",
    "hai bà trưng",
    "cầu giấy",
    "thanh xuân",
    "hoàng mai",
    "long biên",
    "tây hồ",
    "nam từ liêm",
    "bắc từ liêm",
    "hà đông",
    "gia lâm",
    "đông anh",
    "sơn tây",
    "thanh trì",
    "hoài đức",
    # other metros
    "hải châu",
    "thanh khê",
    "sơn trà",
    "ngũ hành sơn",
    "liên chiểu",
    "cẩm lệ",
    "ninh kiều",
    "bình thủy",
    "cái răng",
)


CITIES: tuple[str, ...] = (
    # well-known cities/towns whose names differ from their province — viewers
    # say "ship về Nha Trang", not "ship về Khánh Hòa". Not exhaustive: every
    # match still requires a shipping-context word right before it.
    "nha trang",
    "cam ranh",
    "ninh hòa",
    "đà lạt",
    "bảo lộc",
    "phan thiết",
    "mũi né",
    "phan rang",
    "tháp chàm",
    "buôn ma thuột",
    "buôn hồ",
    "pleiku",
    "an khê",
    "ayun pa",
    "kon tum",
    "gia nghĩa",
    "quy nhơn",
    "an nhơn",
    "hoài nhơn",
    "tuy hòa",
    "sông cầu",
    "tam kỳ",
    "hội an",
    "điện bàn",
    "hạ long",
    "cẩm phả",
    "uông bí",
    "móng cái",
    "đông triều",
    "quảng yên",
    "sa pa",
    "mộc châu",
    "tam đảo",
    "điện biên phủ",
    "việt trì",
    "vĩnh yên",
    "phúc yên",
    "sông công",
    "phổ yên",
    "chí linh",
    "kinh môn",
    "tam điệp",
    "phủ lý",
    "sầm sơn",
    "bỉm sơn",
    "nghi sơn",
    "vinh",
    "cửa lò",
    "hồng lĩnh",
    "kỳ anh",
    "đồng hới",
    "ba đồn",
    "đông hà",
    "đồ sơn",
    "cát bà",
    "thủy nguyên",
    "đồng xoài",
    "chơn thành",
    "bình long",
    "phước long",
    "long khánh",
    "nhơn trạch",
    "long thành",
    "trảng bom",
    "bến cát",
    "tân uyên",
    "bà rịa",
    "phú mỹ",
    "tân an",
    "kiến tường",
    "đức hòa",
    "cần giuộc",
    "mỹ tho",
    "gò công",
    "cai lậy",
    "cao lãnh",
    "sa đéc",
    "hồng ngự",
    "long xuyên",
    "châu đốc",
    "tân châu",
    "rạch giá",
    "hà tiên",
    "phú quốc",
    "vị thanh",
    "ngã bảy",
    "thốt nốt",
    "ô môn",
    "bình minh",
    "giá rai",
    "năm căn",
    # Hà Nội outer districts not yet in DISTRICTS
    "mê linh",
    "sóc sơn",
    "thường tín",
    "thanh oai",
    "quốc oai",
    "chương mỹ",
    "đan phượng",
    "phú xuyên",
    "ứng hòa",
    "mỹ đức",
    "ba vì",
    "phúc thọ",
    "thạch thất",
)


def _strip_diacritics(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _variants(names: tuple[str, ...]) -> set[str]:
    out: set[str] = set()
    for n in names:
        out.add(n)
        out.add(_strip_diacritics(n))
    return out


ALL_UNIT_VARIANTS: frozenset[str] = frozenset(
    _variants(PROVINCES) | _variants(DISTRICTS) | _variants(CITIES)
)

# One alternation regex over all unit names, longest first so "bà rịa vũng tàu"
# wins over "vũng tàu". Word-ish boundaries: names are letters/digits/spaces.
_UNIT_ALTERNATION = "|".join(
    re.escape(name) for name in sorted(ALL_UNIT_VARIANTS, key=len, reverse=True)
)
_VN_WORD_CHARS = "\\wàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
UNIT_RE = re.compile(
    rf"(?<![{_VN_WORD_CHARS}])({_UNIT_ALTERNATION})(?![{_VN_WORD_CHARS}])",
    re.IGNORECASE,
)
