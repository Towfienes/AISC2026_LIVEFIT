"""PII filter quality gate (plan §8.2, HARNESS §2).

Recall gates on the labeled comment set:
- phone / email / order / address / social / bank: >= 95% each (hard project
  rule; luật 91/2025/QH15)
- name: >= 70% (honest rule-based ceiling for Vietnamese names —
  docs/research/2026-08-24-vietnamese-nlp.md; NER hook raises it later)
Precision guard: clean comments must stay essentially untouched.

The dataset includes the adversarial probe set from the 09/2026 red-team run
(multi-separator/fullwidth/keycap phones, out-of-gazetteer cities, q7/p5
abbreviations, lowercase names, social links, bank accounts).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from livelift.ingest.pii import scrub

DATA = Path(__file__).parent / "data" / "pii_comments.jsonl"
HARD_KINDS = ("phone", "email", "order", "address", "social", "bank")


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
        if case["labels"].get("phone", 0) == 0:
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


# --- probe đối kháng 09/2026: SĐT nguỵ trang ---------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "0901,234,567",  # separator dấu phẩy
        "0901/234/567",  # separator gạch chéo
        "0901 - 234 - 567",  # cụm " - "
        "０９０１２３４５６７",  # chữ số fullwidth (NFKC)
        "0️⃣9️⃣0️⃣1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣",  # emoji keycap
        "sdt0901234567",  # số dính tiền tố chữ
        "zalo0901234567",
        "09012345 sáu bảy",  # trộn chữ số + số viết chữ
    ],
)
def test_obfuscated_phone_scrubbed(text):
    res = scrub(text)
    assert res.counts.get("phone", 0) >= 1, f"lọt SĐT nguỵ trang: {text!r} -> {res.text!r}"
    assert len(re.sub(r"\D", "", res.text)) < 8, f"còn sót chữ số: {res.text!r}"


# --- probe đối kháng 09/2026: địa chỉ ---------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "ship về Nha Trang",  # thành phố khác tên tỉnh (gazetteer mở rộng)
        "giao về Đà Lạt",
        "ship về Buôn Ma Thuột",
        "q7 có ship không",  # viết tắt quận đứng một mình
        "giao về q.7 nha",
        "ship về p5 giúp em",  # viết tắt phường cần ngữ cảnh
        "mình ở bên Gò Vấp",  # từ ngữ cảnh "ở bên"
        "về tận Gò Vấp luôn",  # từ ngữ cảnh "về tận"
    ],
)
def test_adversarial_address_scrubbed(text):
    res = scrub(text)
    assert res.counts.get("address", 0) >= 1, f"lọt địa chỉ: {text!r} -> {res.text!r}"


def test_p_abbreviation_needs_context():
    """ "p5" đứng một mình dễ trùng tên model sản phẩm — chỉ bắt khi có ngữ cảnh."""
    assert scrub("điện thoại p5 còn hàng không").counts.get("address", 0) == 0
    assert scrub("ship về p5 giúp em").counts.get("address", 0) == 1


# --- probe đối kháng 09/2026: tên viết thường --------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "chị hương ơi chốt cho em màu đen",  # hô ngữ + tên thường
        "tên em là hoa",  # tự giới thiệu viết thường
        "nguyễn thị hoa đặt 2 hộp",  # họ tên đầy đủ viết thường
    ],
)
def test_lowercase_name_scrubbed(text):
    res = scrub(text)
    assert res.counts.get("name", 0) >= 1, f"lọt tên viết thường: {text!r} -> {res.text!r}"


@pytest.mark.parametrize(
    "text",
    [
        "chị ơi chốt giúp em",  # hô ngữ không kèm tên
        "em lấy 1 cái màu đỏ",
        "shop ơi hàng về chưa",
        "tên gì vậy shop",
    ],
)
def test_honorific_without_name_untouched(text):
    assert scrub(text).text == text


# --- pattern mới: MXH + số tài khoản ----------------------------------------


def test_social_links_and_handles_scrubbed():
    for text in (
        "fb.com/nguyenvana",
        "facebook.com/hoa.nguyen.123",
        "zalo.me/0901234567",
        "tiktok.com/@shopcuahoa",
        "ib em @hoa_nguyen nha",
    ):
        res = scrub(text)
        assert res.counts.get("social", 0) >= 1, f"lọt link MXH: {text!r} -> {res.text!r}"
        assert "[MXH]" in res.text


def test_email_not_double_counted_as_handle():
    res = scrub("gửi bill qua mail hoa.nguyen89@gmail.com giúp em")
    assert res.counts == {"email": 1}
    assert "[EMAIL]" in res.text


def test_bank_account_with_context_scrubbed():
    for text in (
        "stk 19036512345678 vietcombank",
        "số tk: 0071000123456",
        "số tài khoản 9704229912345678",
        "tk: 106868686868",
    ):
        res = scrub(text)
        assert res.counts.get("bank", 0) >= 1, f"lọt số tài khoản: {text!r} -> {res.text!r}"
        assert "[STK]" in res.text
        assert len(re.sub(r"\D", "", res.text)) < 6


def test_bare_tai_khoan_with_amount_untouched():
    """ "tài khoản" không có "số"/"stk" thường đi với số tiền — không được bắt."""
    text = "nạp vào tài khoản 500000 là được nha"
    assert scrub(text).counts.get("bank", 0) == 0


def test_new_tokens_idempotent():
    once = scrub("stk 19036512345678, fb.com/nguyenvana, chị hương ơi q7 nha").text
    assert scrub(once).text == once
