"""Keyword-baseline intent classifier for Vietnamese livestream comments.

This is the PRE-REGISTERED ABLATION BASELINE: a transparent keyword matcher
whose numbers anchor the comparison against the ViSoBERT fine-tune that
replaces it later behind the same ``classify`` signature
(docs/research/2026-08-24-vietnamese-nlp.md). Do not "improve" it silently —
its simplicity is the point.

Matching is case- and diacritics-insensitive: both the comment and the keyword
sets are lowercased and stripped of diacritics before matching, so "GIÁ", "gia"
and "giá" all hit the same keyword. Labels are checked in a fixed priority
order (closing a sale beats asking about it); the first label whose keyword set
matches wins, otherwise ``khac``.

Only scrubbed text should ever reach this function in the ingest path — the
classifier itself never stores or logs its input.
"""

from __future__ import annotations

import re
import unicodedata

INTENT_LABELS = ("hoi_gia", "hoi_size", "che_dat", "chot_don", "van_chuyen", "khac")


def strip_diacritics(text: str) -> str:
    """Lowercase and remove Vietnamese diacritics ("Gò Vấp" -> "go vap")."""
    text = text.lower().replace("đ", "d")  # đ has no combining-mark decomposition
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


# Keyword phrases per label, written with diacritics for readability; they are
# diacritics-stripped at compile time so matching is accent-insensitive on both
# sides. Phrases (not single risky tokens) are used where stripping collides:
# "đắt" (expensive) and "đặt" (to order) both strip to "dat", so ``che_dat``
# only uses phrases like "đắt quá" while ``chot_don`` uses "đặt hàng".
_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "chot_don",
        (
            "chốt",
            "chốt đơn",
            "lấy 1",
            "lấy một",
            "em lấy",
            "order",
            "mua",
            "đặt hàng",
            "đặt mua",
            "cho em 1",
            "cho mình 1",
        ),
    ),
    (
        "hoi_size",
        (
            "size",
            "sz",
            "bao ký",
            "bao nhiêu ký",
            "mấy ký",
            "bao kg",
            "cân nặng",
            "chiều cao",
            "form",
            "mặc vừa",
            "xl",
            "xxl",
        ),
    ),
    (
        "van_chuyen",
        (
            "ship",
            "giao",
            "giao hàng",
            "vận chuyển",
            "phí ship",
            "freeship",
            "cod",
            "bao lâu tới",
            "bao lâu nhận",
            "khi nào nhận",
            "khi nào tới",
        ),
    ),
    (
        "hoi_gia",
        (
            "bao nhiêu",
            "bn",
            "giá",
            "nhiêu tiền",
            "bao tiền",
            "giá nhiêu",
            "nhiu tiền",
        ),
    ),
    (
        "che_dat",
        (
            "đắt quá",
            "đắt thế",
            "đắt vậy",
            "mắc quá",
            "mắc thế",
            "mắc vậy",
            "quá đắt",
            "quá mắc",
            "cao thế",
            "cao vậy",
            "hố quá",
            "chát quá",
        ),
    ),
)


def _compile(phrases: tuple[str, ...]) -> re.Pattern[str]:
    stripped = sorted({strip_diacritics(p) for p in phrases}, key=len, reverse=True)
    alternation = "|".join(re.escape(p) for p in stripped)
    return re.compile(rf"\b(?:{alternation})\b")


_MATCHERS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (label, _compile(phrases)) for label, phrases in _KEYWORDS
)


def classify(text: str) -> str:
    """Classify one comment into an intent label.

    Returns the first matching label in priority order
    (chot_don > hoi_size > van_chuyen > hoi_gia > che_dat), else ``khac``.
    """
    normalized = strip_diacritics(text)
    for label, pattern in _MATCHERS:
        if pattern.search(normalized):
            return label
    return "khac"
