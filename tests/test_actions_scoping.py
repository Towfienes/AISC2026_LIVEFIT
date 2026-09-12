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

from livelift.api.routes.actions import (
    product_id_from_card,
    refusal_for_unpinnable_product,
    scope_candidates_to_product,
)
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


# -- refusal_for_unpinnable_product -----------------------------------------
#
# Sự cố 12/09 (kiem-chung-van-hanh.md §2.4b): ba tình huống khác hẳn nhau cùng
# nhận MỘT câu "Thẻ không còn hợp lệ — sản phẩm đã hết hàng hoặc danh sách gợi ý
# vừa thay đổi. Chờ thẻ mới rồi thử lại." Trên tình huống thật sự xảy ra (sản
# phẩm vừa tạo, tồn kho 50, chỉ nằm ngoài ba thẻ gợi ý) CẢ HAI lý do đều sai và
# lời khuyên "chờ" là không bao giờ thực hiện được.


def _kho(**stocks: int) -> dict[str, dict]:
    return {
        pid: {"product_id": pid, "name": f"Sản phẩm {pid}", "stock": stock}
        for pid, stock in stocks.items()
    }


def _ranked(*pids: str) -> list[Candidate]:
    return [cand(pid, 5.0 - i, 4.0 - i, 6.0 - i) for i, pid in enumerate(pids)]


def test_refusal_for_product_that_is_not_in_the_catalogue_says_so():
    exc = refusal_for_unpinnable_product("KHONG-CO", _kho(A=10), _ranked("A"), from_card=False)
    assert exc.status_code == 404
    assert "KHONG-CO" in exc.detail
    assert "hết hàng" not in exc.detail


def test_refusal_for_out_of_stock_product_quotes_the_real_stock():
    exc = refusal_for_unpinnable_product("B", _kho(A=10, B=0), _ranked("A"), from_card=False)
    assert exc.status_code == 409
    assert "HẾT HÀNG" in exc.detail
    assert "tồn kho 0" in exc.detail


def test_refusal_for_in_stock_product_outside_the_suggestion_set_never_claims_stock():
    """Đúng trường hợp đã xảy ra: còn 50 cái, chỉ là xếp ngoài top-3.

    Thông báo phải (a) KHÔNG nói hết hàng, (b) KHÔNG khuyên chờ thẻ mới —
    danh sách gợi ý sẽ không bao giờ tự đổi thành sản phẩm này — và (c) nói
    được vị trí thật của nó cùng một đường đi thật sự dùng được.
    """
    kho = _kho(A=10, B=10, C=10, MOI=50)
    exc = refusal_for_unpinnable_product("MOI", kho, _ranked("A", "B", "C", "MOI"), from_card=False)
    assert exc.status_code == 409
    assert "hết hàng" not in exc.detail
    assert "Chờ thẻ mới rồi thử lại" not in exc.detail
    assert "50" in exc.detail  # tồn kho thật
    assert "4/4" in exc.detail  # vị trí thật trong bảng xếp hạng
    assert "override" in exc.detail  # đường đi thật sự tồn tại


def test_refusal_for_a_stale_card_tells_the_desk_to_refresh():
    """Bàn điều khiển bấm một thẻ ĐÃ RENDER: ở đây "tải lại danh sách" là lời
    khuyên thật sự làm được, khác hẳn trường hợp gõ thẳng product_id."""
    kho = _kho(A=10, B=10, C=10, CU=10)
    exc = refusal_for_unpinnable_product("CU", kho, _ranked("A", "B", "C", "CU"), from_card=True)
    assert exc.status_code == 409
    assert "hết hàng" not in exc.detail
    assert "Thẻ đã cũ" in exc.detail
    assert "state" in exc.detail


def test_every_refusal_names_a_different_cause():
    """Ba tình huống, ba câu — không được rơi về cùng một câu chung chung."""
    kho = _kho(A=10, B=0, MOI=50)
    ranked = _ranked("A", "B", "MOI")
    details = {
        refusal_for_unpinnable_product(pid, kho, ranked, from_card=False).detail
        for pid in ("KHONG-CO", "B", "MOI")
    }
    assert len(details) == 3
