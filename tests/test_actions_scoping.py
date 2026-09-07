"""Inner-tier scoping when the desk clicks a specific card.

Defect 09/2026: the web client sent only ``card_id`` while the server filtered
on ``product_id`` (always ``None``) — so the server randomized over the WHOLE
candidate set and clicking card A could pin product B. The fix scopes the
candidate set to the clicked card's overlap set, keeping the §6.2 exploration
contract (see ``scope_candidates_to_product``); these tests pin down the pure
scoping logic on crafted intervals.
"""

from __future__ import annotations

import random

from livelift.api.routes.actions import product_id_from_card, scope_candidates_to_product
from livelift.core.assigner import Candidate, choose_action


def cand(pid: str, mu: float, lo: float, hi: float) -> Candidate:
    return Candidate(product_id=pid, estimate=mu, ci_low=lo, ci_high=hi)


# -- product_id_from_card ----------------------------------------------------


def test_product_id_extracted_from_card_id():
    """card_id dạng ``card-{rank}-{product_id}`` (build_cards) — client cũ chỉ
    gửi card_id vẫn phải được scope đúng thẻ."""
    assert product_id_from_card("card-0-P1") == "P1"
    # product_id có thể chứa dấu gạch: chỉ tách 2 dấu đầu
    assert product_id_from_card("card-2-ao-thun-den") == "ao-thun-den"


def test_product_id_from_card_rejects_garbage():
    assert product_id_from_card(None) is None
    assert product_id_from_card("") is None
    assert product_id_from_card("tuy-tien") is None
    assert product_id_from_card("card-0-") is None


# -- scope_candidates_to_product --------------------------------------------


def test_separated_intervals_pin_exactly_the_clicked_card():
    """Khi khoảng ước lượng đã tách bạch, bấm thẻ B phải ghim ĐÚNG B với
    propensity 1 — không bao giờ là sản phẩm khác."""
    candidates = [
        cand("A", 5.0, 4.5, 5.5),
        cand("B", 3.0, 2.5, 3.5),
        cand("C", 1.0, 0.5, 1.5),
    ]
    scoped = scope_candidates_to_product(candidates, "B")
    assert scoped is not None
    assert [c.product_id for c in scoped] == ["B"]
    decision = choose_action(scoped, random.Random(0))
    assert decision.product_id == "B"
    assert decision.inner_propensity == 1.0
    assert decision.randomized is False


def test_overlapping_intervals_keep_exploration_with_logged_propensity():
    """Thẻ được bấm là mốc: mọi ứng viên chồng lấn với nó vẫn được ngẫu nhiên
    hoá (hợp đồng khám phá §6.2), ứng viên tách hẳn bị loại."""
    candidates = [
        cand("A", 5.0, 4.0, 6.0),
        cand("B", 4.5, 3.8, 5.2),
        cand("C", 1.0, 0.5, 1.5),
    ]
    scoped = scope_candidates_to_product(candidates, "B")
    assert scoped is not None
    assert {c.product_id for c in scoped} == {"A", "B"}
    decision = choose_action(scoped, random.Random(0))
    assert decision.product_id in {"A", "B"}
    assert decision.inner_propensity == 0.5
    assert decision.randomized is True


def test_cold_start_full_overlap_keeps_uniform_exploration():
    """Cold start: mọi ứng viên mang đúng prior (khoảng trùng nhau hoàn toàn)
    — scope theo thẻ nào cũng giữ nguyên tập, propensity 1/k."""
    candidates = [cand(pid, 1.0, 0.5, 1.5) for pid in ("A", "B", "C")]
    scoped = scope_candidates_to_product(candidates, "C")
    assert scoped is not None
    assert {c.product_id for c in scoped} == {"A", "B", "C"}
    decision = choose_action(scoped, random.Random(3))
    assert decision.inner_propensity == 1.0 / 3.0


def test_unknown_product_returns_none_instead_of_falling_back():
    """Sản phẩm không còn trong tập ứng viên (hết hàng / danh sách đổi) phải
    trả None — rơi lặng về toàn bộ tập chính là lỗi 'bấm thẻ A ghim B'."""
    candidates = [cand("A", 5.0, 4.0, 6.0)]
    assert scope_candidates_to_product(candidates, "X") is None
