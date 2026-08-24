"""PII scrub engine: detect → resolve overlaps → replace in one pass.

Usage:
    from livelift.ingest.pii import scrub
    result = scrub("09O1 234 567 gửi giúp em size M, ship về Gò Vấp")
    result.text   # "[SĐT] gửi giúp em size M, ship về [ĐỊA CHỈ]"

The engine returns spans and kinds only — never persist the original text or
any substring of it. The gate in tests/test_pii_filter.py requires ≥95% recall
per category on the labeled comment set (HARD project rule, plan §8.2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from livelift.ingest.pii import patterns as P  # noqa: N812 — conventional alias
from livelift.ingest.pii.admin_units import UNIT_RE

# Lower number = higher priority when spans overlap.
KIND_PRIORITY = {"email": 0, "order": 1, "phone": 2, "address": 3, "name": 4}
REPLACEMENT = {
    "phone": "[SĐT]",
    "email": "[EMAIL]",
    "order": "[MÃ ĐƠN]",
    "address": "[ĐỊA CHỈ]",
    "name": "[TÊN]",
}

# Spelled-out digits: "không chín không một hai ba bốn năm sáu bảy"
_SPELLED_DIGIT = (
    r"(?:không|khong|một|mot|mốt|hai|ba|bốn|bon|tư|tu|năm|nam|lăm|lam"
    r"|sáu|sau|bảy|bay|bẩy|tám|tam|chín|chin)"
)
SPELLED_PHONE_RE = re.compile(
    rf"(?:\b{_SPELLED_DIGIT}\b[\s.,\-]*){{9,12}}",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PIIMatch:
    kind: str
    start: int
    end: int


@dataclass(frozen=True)
class ScrubResult:
    text: str
    matches: tuple[PIIMatch, ...]

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for m in self.matches:
            out[m.kind] = out.get(m.kind, 0) + 1
        return out

    @property
    def has_pii(self) -> bool:
        return bool(self.matches)


def _find_spans(text: str) -> list[PIIMatch]:
    spans: list[PIIMatch] = []

    for m in P.EMAIL_RE.finditer(text):
        spans.append(PIIMatch("email", m.start(), m.end()))

    for m in P.ORDER_CONTEXT_RE.finditer(text):
        spans.append(PIIMatch("order", m.start("code"), m.end("code")))
    for m in P.ORDER_CARRIER_RE.finditer(text):
        spans.append(PIIMatch("order", m.start(), m.end()))
    for m in P.ORDER_SHOPEE_RE.finditer(text):
        spans.append(PIIMatch("order", m.start(), m.end()))

    for m in P.PHONE_RE.finditer(text):
        if P.is_valid_phone(m.group()):
            spans.append(PIIMatch("phone", m.start(), m.end()))
    for m in SPELLED_PHONE_RE.finditer(text):
        spans.append(PIIMatch("phone", m.start(), m.end()))

    for m in P.STREET_NUM_RE.finditer(text):
        spans.append(PIIMatch("address", m.start(), m.end()))
    for m in P.ADDR_KEYWORD_RE.finditer(text):
        spans.append(PIIMatch("address", m.start(), m.end()))
    for m in P.ADDR_ANNOUNCE_RE.finditer(text):
        spans.append(PIIMatch("address", m.start(), m.end()))
    # administrative unit preceded by a shipping-context word ("ship về Gò Vấp")
    for m in UNIT_RE.finditer(text):
        prefix = text[max(0, m.start() - 16) : m.start()]
        if P.ADDR_CONTEXT_WORDS_RE.search(prefix):
            spans.append(PIIMatch("address", m.start(), m.end()))

    for m in P.NAME_CONTEXT_RE.finditer(text):
        spans.append(PIIMatch("name", m.start("name"), m.end("name")))
    for m in P.NAME_SURNAME_RE.finditer(text):
        spans.append(PIIMatch("name", m.start(), m.end()))
    for m in P.HONORIFIC_NAME_RE.finditer(text):
        spans.append(PIIMatch("name", m.start("name"), m.end("name")))

    return spans


def _resolve_overlaps(spans: list[PIIMatch]) -> list[PIIMatch]:
    """Keep the highest-priority span in any overlapping group; merge
    same-kind overlaps into one span."""
    ordered = sorted(spans, key=lambda s: (KIND_PRIORITY[s.kind], s.start, -(s.end - s.start)))
    kept: list[PIIMatch] = []
    for s in ordered:
        clashing = [k for k in kept if not (s.end <= k.start or s.start >= k.end)]
        if not clashing:
            kept.append(s)
            continue
        same = [k for k in clashing if k.kind == s.kind]
        if len(same) == len(clashing):
            # merge with same-kind overlaps into one covering span
            for k in same:
                kept.remove(k)
            start = min([s.start] + [k.start for k in same])
            end = max([s.end] + [k.end for k in same])
            kept.append(PIIMatch(s.kind, start, end))
        # else: a higher-priority span already covers this — drop s
    return sorted(kept, key=lambda s: s.start)


def scrub(text: str) -> ScrubResult:
    """Scrub PII from a comment. Pure function; safe for concurrent use."""
    spans = _resolve_overlaps(_find_spans(text))
    if not spans:
        return ScrubResult(text=text, matches=())

    parts: list[str] = []
    cursor = 0
    for s in spans:
        parts.append(text[cursor : s.start])
        parts.append(REPLACEMENT[s.kind])
        cursor = s.end
    parts.append(text[cursor:])
    return ScrubResult(text="".join(parts), matches=tuple(spans))
