"""PII filter quality gate (plan §8.2, HARNESS §2).

Recall gates on the labeled comment set:
- phone / email / order / address: >= 95% each (hard project rule)
- name: >= 70% (honest rule-based ceiling for Vietnamese names —
  docs/research/2026-08-24-vietnamese-nlp.md; NER hook raises it later)
Precision guard: clean comments must stay essentially untouched.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from livelift.ingest.pii import scrub

DATA = Path(__file__).parent / "data" / "pii_comments.jsonl"
HARD_KINDS = ("phone", "email", "order", "address")


def load_cases() -> list[dict]:
    with open(DATA, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_recall_gates():
    cases = load_cases()
    labeled = dict.fromkeys((*HARD_KINDS, "name"), 0)
    caught = dict.fromkeys((*HARD_KINDS, "name"), 0)
    misses: list[str] = []
    for case in cases:
        counts = scrub(case["text"]).counts
        for kind in labeled:
            want = case["labels"].get(kind, 0)
            got = counts.get(kind, 0)
            labeled[kind] += want
            caught[kind] += min(got, want)
            if got < want:
                misses.append(f"{kind}: {case['text']!r} (got {got}, want {want})")

    report = "; ".join(misses) if misses else "none"
    for kind in HARD_KINDS:
        recall = caught[kind] / labeled[kind]
        assert recall >= 0.95, f"{kind} recall {recall:.2%} < 95% — misses: {report}"
    name_recall = caught["name"] / labeled["name"]
    assert name_recall >= 0.70, f"name recall {name_recall:.2%} < 70% — misses: {report}"


def test_no_digits_survive_phone_scrub():
    """After scrubbing, no 10+ digit runs may remain in any labeled-phone text."""
    for case in load_cases():
        if case["labels"]["phone"] == 0:
            continue
        out = scrub(case["text"]).text
        digits = re.sub(r"\D", "", out)
        assert len(digits) < 8, f"digit residue in {out!r}"


def test_clean_comments_mostly_untouched():
    """Precision guard: at most 1 of the clean comments may be altered."""
    altered = []
    for case in load_cases():
        if any(case["labels"].values()):
            continue
        res = scrub(case["text"])
        if res.text != case["text"]:
            altered.append(case["text"])
    assert len(altered) <= 1, f"over-redaction of clean comments: {altered}"


def test_replacement_tokens_used():
    res = scrub("0901234567 ship về Gò Vấp, mail a@b.vn, mã đơn ABC123XYZ")
    assert "[SĐT]" in res.text
    assert "[ĐỊA CHỈ]" in res.text
    assert "[EMAIL]" in res.text
    assert "[MÃ ĐƠN]" in res.text


def test_scrub_is_idempotent():
    once = scrub("0901234567 ship về Gò Vấp nha shop").text
    twice = scrub(once).text
    assert once == twice


def test_result_never_carries_original_text():
    """ScrubResult must not expose the raw content of a match (only spans)."""
    res = scrub("0901234567")
    for m in res.matches:
        assert not hasattr(m, "snippet")
        assert set(vars(m)) <= {"kind", "start", "end"}


@pytest.mark.parametrize(
    "text",
    [
        "giá 199k freeship toàn quốc",
        "mua 1 tặng 1 hôm nay thôi",
        "size L với XL còn hàng không",
    ],
)
def test_marketing_text_untouched(text):
    assert scrub(text).text == text
