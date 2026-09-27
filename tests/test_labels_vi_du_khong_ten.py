"""Ví dụ THẬT trong ``labels.LABEL_EXAMPLES_REAL`` không mang tên người.

Sự cố 25/09/2026: một ví dụ ``chao_hoi`` dạng ``<TÊN HIỂN THỊ> : HELLO`` mang tên
hiển thị của một người bình luận thật, chép nguyên văn vào mã và đi thẳng vào
prompt của LLM gán nhãn (``label_llm.build_prompt``). Bộ lọc PII của sản phẩm
không bắt được nó — tên VIẾT HOA TOÀN BỘ, không dấu, đứng trước dấu ":" kiểu dòng
chat chuyển tiếp — nên cổng này kiểm cả dạng đó chứ không chỉ gọi ``scrub``. Rà
cả tệp cùng đợt: gỡ thêm một tên riêng sau từ xưng hô ("cháu …"), một chữ viết
tắt có thể là tên người thứ ba (thay phòng ngừa) và một địa danh cấp huyện của
người bình luận (thay bằng ``[TÊN]`` / ``[ĐỊA CHỈ]`` như bộ lọc làm với các ví
dụ khác). Tệp này KHÔNG chép lại tên nào — chỉ giữ băm.

Thông báo lỗi không in lại ví dụ (chính ví dụ có thể là dữ liệu cá nhân), chỉ in
lớp, số thứ tự hoặc băm.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from livelift.ingest.pii import scrub
from livelift.nlp.label_llm import build_prompt
from livelift.nlp.labels import LABEL_EXAMPLES_REAL

DISPLAY_NAME_PREFIX_RE = re.compile(r"^\s*(?P<ten>[^:]{2,40}?)\s*:\s")
"""``<tên hiển thị> : <nội dung>`` — dạng dòng chat chuyển tiếp kèm tên người gửi."""

DA_GO_SHA12: frozenset[str] = frozenset(
    {
        # sha256[:12] (NFC, chữ thường) của tên/địa danh đã gỡ khỏi ví dụ 25/09/2026.
        # Chỉ lưu băm — test kiểm chúng không quay lại dưới dạng từ hay cặp từ.
        "d148bfa1bbe1",
        "7695ca14d6fa",
        "549450cb4642",
        "f6fe25575108",
        "3843b46c0cb6",
    }
)


def _sha12(s: str) -> str:
    return hashlib.sha256(unicodedata.normalize("NFC", s).encode("utf-8")).hexdigest()[:12]


def _vi_du() -> list[tuple[str, int, str]]:
    return [(lb, i, t) for lb, ex in LABEL_EXAMPLES_REAL.items() for i, t in enumerate(ex)]


def _tu_va_cap_tu(text: str) -> set[str]:
    words = re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", text).lower())
    return set(words) | {f"{a} {b}" for a, b in zip(words, words[1:], strict=False)}


def test_vi_du_that_khong_bat_dau_bang_ten_hien_thi_nguoi_gui():
    """Tiền tố ``TÊN : `` chỉ được phép là placeholder ``[TÊN]``."""
    vi_pham = [
        (lb, i)
        for lb, i, t in _vi_du()
        if (m := DISPLAY_NAME_PREFIX_RE.match(t)) and m.group("ten").strip() != "[TÊN]"
    ]
    assert vi_pham == [], f"ví dụ thật mở đầu bằng tên hiển thị người gửi (lớp, stt): {vi_pham}"


def test_vi_du_that_qua_bo_loc_pii_khong_doi():
    """Mọi ví dụ đã đi qua bộ lọc của sản phẩm: lọc lại không được đổi chữ nào."""
    vi_pham = [(lb, i) for lb, i, t in _vi_du() if scrub(t).text != t]
    assert vi_pham == [], f"ví dụ thật còn PII theo bộ lọc sản phẩm (lớp, stt): {vi_pham}"


def test_ten_va_dia_danh_da_go_khong_quay_lai():
    lai = sorted(
        {
            (lb, i)
            for lb, i, t in _vi_du()
            if any(_sha12(w) in DA_GO_SHA12 for w in _tu_va_cap_tu(t))
        }
    )
    assert lai == [], f"tên/địa danh đã gỡ 25/09 quay lại (lớp, stt): {lai}"


def test_doi_chung_am_cong_bat_dung_dang_ten_hien_thi():
    """Cổng phải đỏ trên đúng dạng của sự cố, và không báo oan placeholder."""
    assert DISPLAY_NAME_PREFIX_RE.match("NGUYEN VAN BIA : HELLO")
    assert DISPLAY_NAME_PREFIX_RE.match("[TÊN] : HELLO").group("ten") == "[TÊN]"
    assert not DISPLAY_NAME_PREFIX_RE.match("0h ngày 22/05 đến 0h ngày 24")
    # Băm tính trên chữ thường NFC: "TÊN BỊA" viết hoa hay dựng sẵn/tổ hợp đều ra một băm.
    assert _sha12("tên bịa") in {_sha12(w) for w in _tu_va_cap_tu("CHÀO TÊN BỊA")}
    assert _sha12(unicodedata.normalize("NFD", "bịa")) == _sha12("bịa")


def test_prompt_gan_nhan_dung_placeholder_thay_ten():
    """Đầu ra cuối cùng — prompt gửi cho LLM — mang ``[TÊN] : HELLO``."""
    prompt = build_prompt()
    assert "[TÊN] : HELLO" in prompt
    assert not any(_sha12(w) in DA_GO_SHA12 for w in _tu_va_cap_tu(prompt))
