"""Tên tài khoản DÍNH LIỀN chữ đứng trước (``chữ@tên8106``) — lỗ hổng tìm ra 25/09/2026.

Tới 25/09/2026 bộ lọc để lọt dạng này ở cả hai mẫu:

- ``EMAIL_RE`` đòi phần sau ``@`` có ``.tld``;
- ``SOCIAL_HANDLE_RE`` có lookbehind ``(?<![\\w.@])`` (để nhường phần tên của email
  cho ``EMAIL_RE``), nên ``@`` đứng ngay sau một chữ thì không bao giờ được xét.

Hậu quả thật: 8 tên tài khoản người bình luận (16 dòng) còn trong ``data/labeling`` —
6 dạng ``chữ@tên`` (4 ở dòng huấn luyện, đã gửi cho LLM gán nhãn) và 2 dạng ``@@tên`` — và
2 tên thật lọt vào Prompt Log "đã làm sạch" trong gói Drive, trong khi
``xuat_prompt_log.py --quet`` vẫn báo 0 (cùng bộ lọc).

Hình dạng thật (kiểm 25/09, chỉ đếm): với 6 tên dạng ``chữ@tên``, chữ ASCII đứng ngay
trước ``@``; 2/6 tên có chữ số, 4/6 chỉ gồm chữ (dài 9–19). Mọi tên dưới đây là BỊA,
dựng theo đúng hình dạng đó.

Đối chứng âm: cách viết giá, cỡ, mốc giờ dùng ``@`` với nghĩa "giá/lúc" không được che.
"""

from __future__ import annotations

import pytest

from livelift.ingest.pii import scrub

# (văn bản, phần tên KHÔNG được còn lại sau khi lọc)
DINH_LIEN = [
    # chữ không dấu ngay trước @, tên có chữ số (dạng thật 2/6)
    ("cảm ơn bạn@minhthu8106 nhiều", "minhthu8106"),
    ("xinh quá shop@hoalan2k3 ơi", "hoalan2k3"),
    # chữ CÓ dấu ngay trước @
    ("chốt đơn ạ@lan.anh99 nha", "lan.anh99"),
    ("hay quá@thu_trang giúp em", "thu_trang"),
    ("đẹp lắm@TrầnThịMai-k3x", "TrầnThịMai"),
    ("dạ vâng@ngocanh.99", "ngocanh"),
    # tên chỉ gồm chữ, dài (dạng thật 4/6)
    ("cho em hỏi@hoangyenchibi", "hoangyenchibi"),
    ("mua rồi nha@phuongthaodangyeu", "phuongthaodangyeu"),
    # chữ số đứng trước @ (vd. "2 cái@tên") và dấu chấm đứng trước @
    ("lấy 2@kimchi_88 nhé", "kimchi_88"),
    ("tuyệt vời.@bichngoc1999", "bichngoc1999"),
]

# Không được che: giá, số lượng, cỡ, mốc giờ, phiên bản gói — đều dùng "@" = "giá/lúc".
KHONG_PHAI_TEN = [
    "3 cái@50k",
    "2@99k",
    "@50k",
    "size@M",
    "8h@live",
    "combo 2 hộp@199.000đ",
    "áo thun@1tr5 free ship",
    "hẹn@7h30 tối nay",
    "size@XXL còn không",
    "size@2XL",
    "npm i next@14.2.3",
]


@pytest.mark.parametrize(("text", "ten"), DINH_LIEN)
def test_ten_tai_khoan_dinh_lien_bi_che(text: str, ten: str) -> None:
    res = scrub(text)
    assert res.counts.get("social", 0) == 1, f"lọt tên tài khoản dính liền: {res.counts}"
    assert "[MXH]" in res.text
    assert ten.lower() not in res.text.lower(), "còn sót phần tên tài khoản"
    assert "@" not in res.text


# "@@tên": "@" thứ hai đứng sau "@" nên lookbehind cũ bỏ qua; 2/8 tên thật ở data/labeling có
# dạng này và regex kiểm kê ``(?<=\w)@`` cũng bỏ sót. Kèm ca biên: tên chỉ gồm chữ, đúng
# ``GLUED_LETTERS_MIN`` = 5 chữ (4 chữ như ``8h@live`` được giữ — xem KHONG_PHAI_TEN).
HAI_A_CONG_VA_BIEN = [
    ("@@minhthu8106 xinh quá", "minhthu8106"),
    ("đẹp quá@@hoangyenchibi", "hoangyenchibi"),
    ("cảm ơn bạn@minha", "minha"),
]


@pytest.mark.parametrize(("text", "ten"), HAI_A_CONG_VA_BIEN)
def test_hai_a_cong_va_ten_dung_nguong_bi_che(text: str, ten: str) -> None:
    res = scrub(text)
    assert res.counts.get("social", 0) == 1, f"lọt tên tài khoản: {res.counts}"
    assert ten.lower() not in res.text.lower(), "còn sót phần tên tài khoản"
    assert scrub(res.text).text == res.text


@pytest.mark.parametrize("text", [t for t, _ in DINH_LIEN])
def test_dinh_lien_luy_dang(text: str) -> None:
    once = scrub(text).text
    assert scrub(once).text == once


@pytest.mark.parametrize("text", KHONG_PHAI_TEN)
def test_gia_co_gio_khong_bi_che(text: str) -> None:
    res = scrub(text)
    assert res.counts.get("social", 0) == 0, f"che oan thành [MXH]: {text!r} -> {res.text!r}"
    assert res.text == text


def test_email_hop_le_van_la_email() -> None:
    """Luật dính liền không được tranh span của email: vẫn đúng một [EMAIL]."""
    for text in (
        "gửi bill qua mail hoa.nguyen89@gmail.com giúp em",
        "mail em là thu_trang99@yahoo.com.vn",
        "liên hệ abc@shop.vn nha",
    ):
        res = scrub(text)
        assert res.counts == {"email": 1}, f"{text!r} -> {res.text!r}"
        assert "@" not in res.text


def test_dinh_lien_dang_ten_mien_van_mat_ten() -> None:
    """``vâng@ngocanh.shop`` trông như email (".shop" là tên miền) nên thành [EMAIL] —
    loại nào cũng được, miễn tên tài khoản không còn và chỉ che MỘT lần."""
    res = scrub("dạ vâng@ngocanh.shop")
    assert sum(res.counts.values()) == 1
    assert "ngocanh" not in res.text
    assert "@" not in res.text


def test_handle_dung_rieng_van_bi_che_nhu_cu() -> None:
    """Handle đứng sau khoảng trắng (luật cũ) không đổi hành vi."""
    for text in ("ib em @hoa_nguyen nha", "@TrầnThịMai-k3x chốt 2 cái", "cảm ơn @ThuHà."):
        assert scrub(text).counts.get("social", 0) == 1, text
    assert scrub("cảm ơn @ThuHà.").text.endswith("[MXH].")
