"""TikTok Shop LIVE analytics — API CHÍNH THỨC, hậu kiểm số liệu theo phút.

Đường này đi qua **TikTok Shop Open Platform** (Partner Center) bằng token do
CHÍNH người bán ủy quyền cho app — đúng quyết định của chủ dự án ngày
17/09/2026 (chỉ API chính thức, tài khoản của nhóm hoặc đối tác đồng ý). Nó
KHÔNG đọc bình luận và KHÔNG thay thế bộ đo không chính thức cũ trong
``collectors/tiktok_public`` (giữ nguyên, không dùng cho live thật).

Mô-đun này CHƯA được nối vào bộ thu nền hay giao diện web.

Nguồn đã tự đọc (tài liệu chính thức, truy cập 17/09/2026)
----------------------------------------------------------
Ngày trong ngoặc là ``update_time`` của trang.

- Ký yêu cầu — https://partner.tiktokshop.com/docv2/page/sign-your-api-request
  (06/07/2026): bỏ ``sign`` và ``access_token`` khỏi query → sắp khóa theo thứ
  tự chữ cái (có ``shop_cipher`` nếu endpoint cần) → nối ``{key}{value}`` →
  đặt **đường dẫn lên trước** → nếu content-type không phải
  ``multipart/form-data`` thì nối **đúng từng byte** thân yêu cầu → bọc
  ``app_secret`` ở hai đầu → HMAC-SHA256 với khóa ``app_secret``, xuất hex chữ
  thường. Nguyên văn: *"For API version 202309 and later, send the access
  token in the x-tts-access-token request header instead of the query string.
  The access token is not included when generating the signature."* Ví dụ
  chính thức (``app_secret=e59af819cc`` → ``b596b73e…82dc8``) được khóa trong
  ``tests/test_ingest_tiktok_shop.py``.
- Tham số chung — https://partner.tiktokshop.com/docv2/page/common-parameters
  (15/09/2026): ``app_key``, ``sign``, ``timestamp`` (*"A 10-digit Unix
  timestamp in seconds … Valid range: [current time - 5 mins, current time + 30
  secs]"*), header ``x-tts-access-token`` và ``content-type: application/json``.
- Mã lỗi chung — https://partner.tiktokshop.com/docv2/page/common-errors
  (06/07/2026): ``36009004`` bị dùng lại cho nhiều lỗi (*"Do not use the numeric
  code alone for programmatic branching. Combine it with the response message
  keyword"*); ``105005`` thiếu scope; ``105002`` token hết hạn; ``106001`` chữ
  ký sai; ``101000`` token sai ``user_type`` hoặc không khớp shop;
  ``106013`` thiếu ``shop_cipher``; ``36009002`` giới hạn nhịp.
- Hạn mức — https://partner.tiktokshop.com/docv2/page/64f1991d64ed2e0295f3d2c0
  (03/09/2026): QPS cấp động; điểm khởi đầu cho *"complex analytics: 0.2-1
  request/second"*, *"Start from the low end"*; HTTP ``429`` hoặc mã
  ``36009002`` là bị bóp nhịp → backoff mũ + jitter, tôn trọng ``Retry-After``.
  Shop thử (sandbox): ``429``/``36009037``; shop/người bán ngừng hoạt động:
  ``401``/``36009043``/``36009044``
  (https://partner.tiktokshop.com/docv2/page/6a2fcefe4dcf9be6fd930820, 15/06/2026).
- Ba endpoint dùng ở đây (cả ba: token NGƯỜI BÁN ``user_type = 0``, scope
  ``data.shop_analytics.public.read`` gói "TikTok Shop Analytics", query
  ``shop_cipher`` bắt buộc; tên miền trong mọi mẫu yêu cầu:
  ``https://open-api.tiktokglobalshop.com`` — tài liệu không nêu tên miền API
  theo vùng nên không có biến cấu hình vùng):

  * ``GET /analytics/202509/shop_lives/performance`` —
    https://partner.tiktokshop.com/docv2/page/get-shop-live-performance-list-202509
    (14/07/2026): danh sách phiên theo khoảng ngày ``start_date_ge`` (gồm) /
    ``end_date_lt`` (không gồm) *"in shop registered timezone"*, ``page_size``
    tối đa 100, ``page_token``/``next_page_token``, ``account_type``.
  * ``GET /analytics/202510/shop_lives/{live_id}/performance_per_minutes`` —
    https://partner.tiktokshop.com/docv2/page/get-shop-live-minute-performance-202510
    (14/07/2026): *"Returns minute-level performance for a LIVE session after
    the session is finished. This API only returns data for live streams hosted
    by the shop official account or marketing account."* Phân trang bằng
    ``page_token`` (tài liệu không có ``page_size``). ``intervals[]`` có
    ``start_time``/``end_time`` (*"unix timestamp GMT (UTC+00:00)"*).
  * ``GET /analytics/202512/shop/{live_id}/products_performance`` —
    https://partner.tiktokshop.com/docv2/page/get-shop-live-products-performance-list-202512
    (26/08/2026): số liệu theo sản phẩm, không phân trang. Tài liệu viết sai
    chính tả ``produt_clicks`` (cả ở ``sort_field`` lẫn phản hồi) — giữ
    nguyên, không "sửa hộ".

  Nhóm ``analytics/202502/live_rooms/*`` (``core_stats``…) cần token CREATOR
  (``user_type = 1``, scope ``creator.data.live.read.public``) nên KHÔNG có ở
  đây. Mã ``66009315 No permission for the action`` được tài liệu ghi cho nhóm
  đó; ba endpoint trên có bảng mã lỗi riêng để trống, nên gặp mã này ở đây vẫn
  hiểu là "không có quyền với phiên này".

Kiểm chứng thật 17/09/2026 (danh tính GIẢ, không đọc dữ liệu của ai)
-------------------------------------------------------------------
Ba đường dẫn trên, ký bằng app_key/app_secret/token bịa, đều trả **HTTP 400**
``{"code": 36009004, "data": null, "message": "Invalid credentials. Invalid
'app_key' query parameter. For more details: …", "request_id": "…"}``; một
đường dẫn bịa cùng tiền tố trả **HTTP 404** mã ``36009009 Invalid path``. Đối
chứng này chứng minh cả ba endpoint TỒN TẠI ở cổng API và cho thấy phong bì lỗi
thật (``data: null``, thông điệp dùng nháy đơn). Cổng từ chối ``app_key``
TRƯỚC khi kiểm chữ ký, nên phép thử **không** chứng minh được thuật toán ký —
phần đó dựa vào ví dụ chính thức đã tái lập. Nhóm chưa có app/shop thật: chưa có
live-fire với dữ liệu. Phản hồi lưu ở
``tests/data/tiktok_shop/loi_tham_do_that_17092026.json``.

Những gì tài liệu KHÔNG nói (đừng giả định)
-------------------------------------------
- Số liệu theo phút có sau khi phiên kết thúc **bao lâu** — không trang nào nêu.
  Phải tự đo.
- ``end_time`` của một phút là mốc mở (``start + 60``) hay đóng (``start + 59``)
  — mẫu phản hồi chính thức còn để ``start_time == end_time``.
  :func:`gop_theo_khoi` vì vậy coi mỗi interval phủ ít nhất
  ``[start_time, start_time + 60)`` khi xét ranh giới khối, và đếm số phút dựa
  vào giả định này.
- Kích thước trang mặc định của ``performance_per_minutes``.
- Theo thông báo "Analytics Open API Metric Consistency Adjustment"
  (https://partner.tiktokshop.com/docv2/page/698d74de3a0ca3049812e044,
  12/02/2026), GMV/đơn theo phút là số **quy đổi (attributed)**; ``gmv`` theo
  phút *"including returns and refunds"*. Đây là số do nền tảng tính, chỉ dùng
  làm biến phụ/đối chứng chéo — biến kết quả chính vẫn là click ``/r/{code}``.

Bí mật (quy tắc cứng)
---------------------
``app_secret`` không bao giờ rời máy (chỉ làm khóa HMAC); ``access_token`` đi
trong HEADER, không nằm trong URL. Mọi lỗi được gói thành
:class:`TikTokShopApiError` — thông điệp không chứa URL, và mọi chuỗi trùng
token/secret trong thông điệp của máy chủ đều bị che. Nhập
:mod:`livelift.ingest.base` để cài bộ lọc che ``sign=`` trong log của httpx.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import random
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from itertools import pairwise
from typing import Any, Literal

import httpx

import livelift.ingest.base  # noqa: F401 — cài bộ lọc che bí mật trong log httpx
from livelift.config import get_settings

logger = logging.getLogger(__name__)

#: Tên miền API trong mọi mẫu yêu cầu của tài liệu (không có biến thể theo vùng).
BASE_URL = "https://open-api.tiktokglobalshop.com"

PATH_LIVE_LIST = "/analytics/202509/shop_lives/performance"
PATH_LIVE_MINUTES = "/analytics/202510/shop_lives/{live_id}/performance_per_minutes"
PATH_LIVE_PRODUCTS = "/analytics/202512/shop/{live_id}/products_performance"

#: Tham số không bao giờ được đưa vào chuỗi ký (tài liệu "Sign your API request").
KHOA_KHONG_KY = frozenset({"sign", "access_token"})

#: Biến môi trường bắt buộc cho cả ba endpoint (đều cần shop_cipher).
REQUIRED_ENV: tuple[str, ...] = (
    "TIKTOK_SHOP_APP_KEY",
    "TIKTOK_SHOP_APP_SECRET",
    "TIKTOK_SHOP_ACCESS_TOKEN",
    "TIKTOK_SHOP_SHOP_CIPHER",
)

#: Giá trị hợp lệ theo tài liệu endpoint.
ACCOUNT_TYPES = ("ALL", "OFFICIAL_ACCOUNTS", "MARKETING_ACCOUNTS", "AFFILIATE_ACCOUNTS")
#: performance_per_minutes chỉ có dữ liệu cho hai loại tài khoản này.
ACCOUNT_TYPES_CO_THEO_PHUT = ("OFFICIAL_ACCOUNTS", "MARKETING_ACCOUNTS")
CURRENCIES = ("USD", "LOCAL")
SORT_ORDERS = ("ASC", "DESC")
PAGE_SIZE_MAX = 100

#: 0,2 request/giây — đầu thấp của khoảng "complex analytics: 0.2-1
#: request/second" mà trang Rate limits bảo bắt đầu từ đó.
DEFAULT_MIN_INTERVAL_S = 5.0
#: Trang Rate limits: base 1 s, gấp đôi mỗi lần, jitter 0–500 ms, trần 60 s,
#: thử tối đa 5 lần.
RATE_LIMIT_BASE_S = 1.0
RATE_LIMIT_CAP_S = 60.0
RATE_LIMIT_JITTER_S = 0.5
RATE_LIMIT_MAX_RETRIES = 5
#: Retry-After dài hơn mức này thì báo lỗi ngay thay vì treo tiến trình.
RETRY_AFTER_MAX_S = 300.0
#: 5xx / mạng / 36009007: thử lại ít lần hơn — không phải lỗi hạn mức.
TRANSIENT_MAX_RETRIES = 3
#: Chặn trên số trang để vòng phân trang không bao giờ chạy mãi.
MAX_PAGES = 500

#: Ký tự an toàn cho ``live_id`` — nó nằm trong ĐƯỜNG DẪN được ký, nên ``/``,
#: ``?`` hay ``#`` sẽ đổi endpoint thật sự được gọi.
_LIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

LoaiLoi = Literal["auth", "permission", "rate_limit", "config", "transient", "other"]

MA_SANDBOX_THEO_GIO = "36009037"
MA_RATE_LIMIT = frozenset({"36009002", MA_SANDBOX_THEO_GIO})
#: ``36009007`` "Request timeout" (Common errors) và ``36009003`` *"Internal error.
#: Please try again. If the issue persists after multiple attempts, please contact
#: platform support."* — bảng lỗi của Get Shop LIVE Performance Overview
#: (``/analytics/202509/shop_lives/overview_performance``,
#: https://partner.tiktokshop.com/docv2/page/6960bc30ea9d0304fa4027f7, cập nhật
#: 10/09/2026) và Get Authorized Shops
#: (https://partner.tiktokshop.com/docv2/page/6507ead7b99d5302be949ba9); truy cập
#: 17/09/2026. Tài liệu bảo thử lại và không nêu HTTP status của mã này.
MA_TRANSIENT = frozenset({"36009007", "36009003"})


# ---------------------------------------------------------------------------
# Ký yêu cầu
# ---------------------------------------------------------------------------


def _gia_tri_query(value: Any) -> str:
    """Chuẩn hóa giá trị query thành đúng chuỗi sẽ gửi (và sẽ ký)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def chuoi_can_ky(
    path: str,
    query: Mapping[str, Any],
    body: bytes = b"",
    content_type: str = "application/json",
) -> bytes:
    """Chuỗi trước khi bọc ``app_secret`` (bước 2–4 của tài liệu ký).

    ``path`` + ``{key}{value}`` của các khóa query (trừ ``sign``,
    ``access_token``) sắp theo thứ tự chữ cái + thân yêu cầu nếu content-type
    không phải ``multipart/form-data``. Giá trị query là giá trị ĐÃ GIẢI MÃ
    (như ``queries.Get`` của mẫu Go), còn thân yêu cầu được nối đúng từng byte.
    """
    keys = sorted(k for k in query if k not in KHOA_KHONG_KY)
    parts = [path.encode("utf-8")]
    parts.extend(f"{k}{_gia_tri_query(query[k])}".encode() for k in keys)
    media_type = content_type.split(";", 1)[0].strip().lower()
    if body and media_type != "multipart/form-data":
        parts.append(body)
    return b"".join(parts)


def tao_chu_ky(
    path: str,
    query: Mapping[str, Any],
    app_secret: str,
    body: bytes = b"",
    content_type: str = "application/json",
) -> str:
    """HMAC-SHA256 (khóa ``app_secret``) của ``app_secret + chuỗi cần ký + app_secret``, hex."""
    secret = app_secret.encode("utf-8")
    message = secret + chuoi_can_ky(path, query, body, content_type) + secret
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def build_signed_query(
    path: str,
    query: Mapping[str, Any],
    app_key: str,
    app_secret: str,
    shop_cipher: str,
    timestamp: int,
) -> dict[str, str]:
    """Bộ tham số query đã ký cho một lời gọi GET có ``shop_cipher``.

    ``access_token`` KHÔNG có ở đây — nó đi trong header ``x-tts-access-token``.
    Tham số có giá trị ``None`` hoặc chuỗi rỗng bị bỏ hẳn (gửi gì thì ký nấy).
    """
    ts = int(timestamp)
    if len(str(ts)) != 10:
        raise ValueError(
            f"timestamp={ts} không phải Unix timestamp 10 chữ số (giây) như tài liệu yêu cầu."
        )
    params: dict[str, str] = {}
    for key, value in query.items():
        if value is None:
            continue
        text = _gia_tri_query(value)
        if text == "":
            continue
        params[str(key)] = text
    params.update({"app_key": app_key, "shop_cipher": shop_cipher, "timestamp": str(ts)})
    params.pop("sign", None)
    params.pop("access_token", None)
    params["sign"] = tao_chu_ky(path, params, app_secret)
    return params


# ---------------------------------------------------------------------------
# Lỗi
# ---------------------------------------------------------------------------


class TikTokShopApiError(Exception):
    """Lỗi từ TikTok Shop Open Platform, **không chứa URL hay bí mật**.

    Câu tiếng Việt (có cách sửa) đứng TRƯỚC chi tiết kỹ thuật để vẫn còn khi
    thông điệp bị cắt ngắn.
    """

    loai: LoaiLoi = "other"

    def __init__(
        self,
        code: str,
        message: str = "",
        status: int | None = None,
        request_id: str | None = None,
        giai_thich: str = "",
    ) -> None:
        self.code = str(code)
        self.api_message = message
        self.status = status
        self.request_id = request_id
        self.giai_thich = giai_thich
        detail = f"TikTok Shop API lỗi {self.code}"
        if status is not None:
            detail += f" (HTTP {status})"
        if message:
            detail += f": {message}"
        if request_id:
            detail += f" [request_id={request_id}]"
        super().__init__(f"{giai_thich} [{detail}]" if giai_thich else detail)


class TikTokShopAuthError(TikTokShopApiError, ValueError):
    """Sai danh tính: token hết hạn/sai, chữ ký sai, app_key sai, đồng hồ lệch.

    Kế thừa ``ValueError``: là lỗi cấu hình, thử lại ngay không sửa được.
    """

    loai: LoaiLoi = "auth"


class TikTokShopPermissionError(TikTokShopApiError, ValueError):
    """Danh tính đúng nhưng KHÔNG có quyền: thiếu scope, không có quyền với
    phiên, IP không được phép, shop/người bán ngừng hoạt động."""

    loai: LoaiLoi = "permission"


class TikTokShopRateLimitError(TikTokShopApiError, RuntimeError):
    """Bị bóp nhịp gọi (HTTP 429 / 36009002 / 36009037) sau khi đã tự thử lại.
    Token vẫn tốt."""

    loai: LoaiLoi = "rate_limit"


class TikTokShopConfigError(TikTokShopApiError, ValueError):
    """Sai định danh hoặc đường dẫn: thiếu/thừa ``shop_cipher``, phiên bản API
    hay đường dẫn không còn hợp lệ."""

    loai: LoaiLoi = "config"


_LOP_THEO_LOAI: dict[LoaiLoi, type[TikTokShopApiError]] = {
    "auth": TikTokShopAuthError,
    "permission": TikTokShopPermissionError,
    "rate_limit": TikTokShopRateLimitError,
    "config": TikTokShopConfigError,
    "transient": TikTokShopApiError,
    "other": TikTokShopApiError,
}

_CACH_TRA_MA = (
    "Tra mã ở https://partner.tiktokshop.com/docv2/page/common-errors và gửi kèm "
    "request_id khi hỏi hỗ trợ TikTok."
)


#: Mọi kiểu dấu nháy quanh tên tham số: backtick (bảng lỗi của tài liệu), nháy đơn
#: (phản hồi THẬT của cổng 17/09/2026: ``Invalid 'app_key' query parameter``),
#: nháy kép và nháy cong.
_DAU_NHAY_RE = re.compile("[`'\"‘’“”]")


def _ly_do_36009004(message: str) -> str:
    """Lý do cụ thể của mã ``36009004`` theo bảng từ khóa của trang Common errors.

    Bỏ MỌI dấu nháy trước khi so: bảng lỗi của tài liệu viết ``The `access_token`
    header is invalid`` (backtick), bảng từ khóa viết ``access_token header is
    invalid`` (không dấu), còn cổng API thật dùng nháy đơn (``'app_key'``).
    """
    text = _DAU_NHAY_RE.sub("", (message or "").lower())
    if "timestamp" in text:
        return "timestamp"
    if "x-tts-access-token" in text or "access_token header" in text:
        return "token"
    if "app_key" in text:
        return "app_key"
    if "category_asset_cipher" in text:
        return "cipher_thua"
    if "shop_cipher" in text:
        return "cipher_thua" if ("not required" in text or "unexpected" in text) else "cipher"
    if "shop_id" in text:
        return "shop_id"
    if "api version" in text:
        return "version"
    if "signature" in text or "missing credentials" in text:
        return "sign"
    return "khac"


_LOAI_THEO_LY_DO: dict[str, LoaiLoi] = {
    "timestamp": "auth",
    "token": "auth",
    "app_key": "auth",
    "sign": "auth",
    "cipher": "config",
    "cipher_thua": "config",
    "shop_id": "config",
    "version": "config",
    "khac": "other",
}


def phan_loai_loi(code: str, message: str = "", status: int | None = None) -> LoaiLoi:
    """Phân loại theo mã + TỪ KHÓA thông điệp, đúng khuyến nghị của Common errors."""
    ma = str(code).strip()
    if status == 429 or ma in MA_RATE_LIMIT:
        return "rate_limit"
    if ma == "36009004":
        return _LOAI_THEO_LY_DO[_ly_do_36009004(message)]
    if ma in {"105002", "106001", "101000"}:
        return "auth"
    if ma in {"105005", "66009315", "36009033", "36009043", "36009044"}:
        return "permission"
    if ma in {"106013", "36009009", "36009010", "36009014"}:
        return "config"
    if "invalid api version" in (message or "").lower():
        return "config"
    if ma in MA_TRANSIENT or ma == "network" or (status is not None and status >= 500):
        return "transient"
    if status == 401:
        return "auth"
    if status == 403:
        return "permission"
    return "other"


_GIAI_THICH_THEO_MA: dict[str, str] = {
    "36009037": (
        "Shop THỬ (sandbox) đã vượt hạn mức lượt gọi mỗi giờ của TikTok. Chờ sang giờ sau "
        "rồi chạy lại; không dùng shop thử để kéo dữ liệu hàng loạt."
    ),
    "105002": (
        "access_token TikTok Shop đã HẾT HẠN (mặc định sống 7 ngày). Làm mới bằng "
        "refresh_token qua https://auth.tiktok-shops.com/api/v2/token/refresh, dán giá trị "
        "mới vào TIKTOK_SHOP_ACCESS_TOKEN trong .env rồi chạy lại."
    ),
    "106001": (
        "Chữ ký (sign) bị TikTok Shop từ chối. Kiểm tra TIKTOK_SHOP_APP_SECRET đúng cặp với "
        "TIKTOK_SHOP_APP_KEY (Partner Center → App & Service → app → App Secret) và không có "
        "dấu cách thừa."
    ),
    "101000": (
        "Token không đúng loại hoặc không khớp shop: số liệu LIVE của shop cần token NGƯỜI "
        "BÁN (user_type = 0) và TIKTOK_SHOP_SHOP_CIPHER phải là shop mà token này được ủy "
        "quyền. Token creator (user_type = 1) không dùng được ở đây. Lấy lại shop_cipher bằng "
        "GET /authorization/202309/shops (Get Authorized Shops)."
    ),
    "105005": (
        "App hoặc token CHƯA có quyền 'TikTok Shop Analytics' "
        "(data.shop_analytics.public.read). Bật gói đó ở Partner Center → App & Service → "
        "Manage API, rồi cho shop ỦY QUYỀN LẠI để token mới mang quyền này (xem trường "
        "granted_scopes khi đổi token)."
    ),
    "66009315": (
        "TikTok Shop báo không có quyền với phiên LIVE này. Kiểm tra live_id thuộc đúng shop "
        "đã ủy quyền và phiên được phát bằng tài khoản CHÍNH THỨC hoặc tài khoản MARKETING "
        "của shop — số liệu theo phút không có cho live của creator liên kết."
    ),
    "36009033": (
        "Địa chỉ IP của máy chạy LiveLift không nằm trong danh sách IP cho phép của app. Thêm "
        "IP này ở Partner Center → App & Service (hoặc bỏ danh sách IP) rồi chạy lại."
    ),
    "36009043": (
        "Shop đã bị vô hiệu hóa hoặc đang đóng — TikTok chặn mọi lời gọi API cho shop này. "
        "Chủ shop phải xử lý trạng thái tài khoản trong Seller Center; thử lại không sửa được."
    ),
    "36009044": (
        "Tài khoản người bán đã bị vô hiệu hóa — TikTok chặn mọi lời gọi API. Chủ shop phải "
        "xử lý trạng thái tài khoản trong Seller Center; thử lại không sửa được."
    ),
    "106013": (
        "Thiếu hoặc sai shop_cipher. Lấy giá trị bằng GET /authorization/202309/shops (Get "
        "Authorized Shops) rồi đặt TIKTOK_SHOP_SHOP_CIPHER trong .env."
    ),
    "36009003": (
        "TikTok Shop báo lỗi nội bộ phía họ (36009003); client đã tự thử lại vài lần nhưng "
        "vẫn lỗi. Chạy lại sau ít phút; nếu lặp lại nhiều lần, gửi ticket hỗ trợ ở "
        "https://partner.tiktokshop.com/ticket/center kèm request_id."
    ),
}

_GIAI_THICH_THEO_LY_DO: dict[str, str] = {
    "timestamp": (
        "Đồng hồ máy chạy LiveLift lệch so với TikTok (timestamp phải nằm trong khoảng 5 phút "
        "trước đến 30 giây sau giờ máy chủ TikTok). Bật đồng bộ giờ tự động của hệ điều hành "
        "rồi chạy lại."
    ),
    "token": (
        "TIKTOK_SHOP_ACCESS_TOKEN không hợp lệ. Lấy token mới qua luồng ủy quyền người bán "
        "(đổi auth_code ở https://auth.tiktok-shops.com/api/v2/token/get với "
        "grant_type=authorized_code) rồi dán lại vào .env."
    ),
    "app_key": (
        "TIKTOK_SHOP_APP_KEY không hợp lệ (sai, app bị tắt hoặc đã xóa). Chép lại App Key từ "
        "trang chi tiết app trong Partner Center."
    ),
    "sign": _GIAI_THICH_THEO_MA["106001"],
    "cipher": _GIAI_THICH_THEO_MA["106013"],
    "cipher_thua": (
        "Yêu cầu gửi THỪA một định danh (shop_cipher/category_asset_cipher) cho endpoint "
        "không cần nó — lỗi mã nguồn LiveLift, báo người giữ mã đối chiếu tài liệu endpoint."
    ),
    "shop_id": _GIAI_THICH_THEO_MA["106013"],
}

_GIAI_THICH_THEO_LOAI: dict[LoaiLoi, str] = {
    "rate_limit": (
        "TikTok Shop đang giới hạn nhịp gọi (HTTP 429 / 36009002) — token VẪN TỐT, không cần "
        "đổi. Client đã tự chờ rồi thử lại nhưng vẫn bị chặn: đợi vài phút rồi chạy lại, và "
        "không chạy song song nhiều tiến trình trên cùng một shop."
    ),
    "config": (
        "Đường dẫn, phương thức hoặc phiên bản API không còn hợp lệ — TikTok có thể đã ngừng "
        "phiên bản này. Đối chiếu tài liệu endpoint trên partner.tiktokshop.com rồi cập nhật "
        "hằng số PATH_* trong src/livelift/ingest/tiktok_shop.py."
    ),
    "auth": (
        "TikTok Shop từ chối danh tính. Kiểm tra TIKTOK_SHOP_APP_KEY, TIKTOK_SHOP_APP_SECRET, "
        "TIKTOK_SHOP_ACCESS_TOKEN (token sống 7 ngày). " + _CACH_TRA_MA
    ),
    "permission": (
        "TikTok Shop từ chối quyền truy cập. Kiểm tra app đã bật gói 'TikTok Shop Analytics' "
        "và shop đã ủy quyền lại sau khi bật. " + _CACH_TRA_MA
    ),
    "transient": (
        "Lỗi tạm thời phía TikTok hoặc đường mạng; client đã thử lại vài lần. Chạy lại sau ít phút."
    ),
    "other": "TikTok Shop trả lỗi chưa phân loại. " + _CACH_TRA_MA,
}


def giai_thich_loi(code: str, message: str = "", status: int | None = None) -> str:
    """Câu tiếng Việt cho người vận hành: chuyện gì xảy ra và sửa thế nào."""
    ma = str(code).strip()
    if ma in _GIAI_THICH_THEO_MA:
        return _GIAI_THICH_THEO_MA[ma]
    if ma == "36009004":
        ly_do = _ly_do_36009004(message)
        if ly_do in _GIAI_THICH_THEO_LY_DO:
            return _GIAI_THICH_THEO_LY_DO[ly_do]
    return _GIAI_THICH_THEO_LOAI[phan_loai_loi(ma, message, status)]


def tao_loi(
    code: str,
    message: str = "",
    status: int | None = None,
    request_id: str | None = None,
) -> TikTokShopApiError:
    """Dựng lỗi đúng lớp kèm câu tiếng Việt."""
    loai = phan_loai_loi(code, message, status)
    lop = _LOP_THEO_LOAI[loai]
    err = lop(
        code=str(code),
        message=message,
        status=status,
        request_id=request_id,
        giai_thich=giai_thich_loi(code, message, status),
    )
    if lop is TikTokShopApiError:
        err.loai = loai
    return err


def che_bi_mat(text: str, bi_mat: Iterable[str]) -> str:
    """Thay mọi lần xuất hiện của token/secret trong ``text`` bằng ``***``."""
    out = text
    for value in bi_mat:
        if value and len(value) >= 4:
            out = out.replace(value, "***")
    return out


def credential_problem(
    values: Mapping[str, str], required: Iterable[str] = REQUIRED_ENV
) -> str | None:
    """Câu tiếng Việt nếu thiếu biến, None nếu đủ. Chỉ nêu TÊN biến, không bao giờ nêu giá trị."""
    missing = [name for name in required if not (values.get(name) or "").strip()]
    if not missing:
        return None
    return (
        "Thiếu danh tính TikTok Shop trong .env: "
        + ", ".join(missing)
        + ". Lấy App Key/App Secret ở Partner Center, access_token qua luồng ủy quyền "
        "người bán, shop_cipher bằng Get Authorized Shops — xem "
        "docs/HUONG-DAN-LAY-KHOA-API.md mục 5."
    )


def _retry_after_s(value: str | None, now: datetime | None = None) -> float | None:
    """``Retry-After`` dạng giây hoặc ngày HTTP → số giây; không đọc được thì None."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    ref = now or datetime.now(UTC)
    return max(0.0, (when - ref).total_seconds())


def _ma_hop_le_live_id(live_id: str) -> str:
    text = str(live_id).strip()
    if not _LIVE_ID_RE.match(text):
        raise ValueError(
            f"live_id không hợp lệ ({len(text)} ký tự): chỉ nhận chữ, số, '_' và '-'. "
            "Lấy live_id từ danh sách phiên (trường id)."
        )
    return text


def _ngay_iso(name: str, value: date | str) -> str:
    if isinstance(value, datetime):
        raise ValueError(f"{name} phải là ngày (YYYY-MM-DD), không phải thời điểm.")
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value).strip()).isoformat()
    except ValueError:
        raise ValueError(f"{name}={value!r} không đúng định dạng ngày YYYY-MM-DD.") from None


def _int_hoac_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Kết quả
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DanhSachPhienLive:
    """Mọi trang của ``shop_lives/performance`` cho một khoảng ngày."""

    phien: list[dict[str, Any]]
    total_count: int | None
    latest_available_date: str | None
    so_trang: int
    request_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HieuSuatTheoPhut:
    """Mọi trang của ``performance_per_minutes`` cho một ``live_id``."""

    live_id: str
    overall: dict[str, Any]
    intervals: list[dict[str, Any]]
    total_count: int | None
    so_trang: int
    request_ids: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)


def phien_moi_nhat(phien: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Phiên có ``start_time`` lớn nhất; phiên thiếu/hỏng ``start_time`` bị bỏ qua."""
    tot: dict[str, Any] | None = None
    tot_ts: int | None = None
    for item in phien:
        ts = _int_hoac_none(item.get("start_time"))
        if ts is None:
            continue
        if tot_ts is None or ts > tot_ts:
            tot, tot_ts = dict(item), ts
    return tot


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TikTokShopLiveAnalyticsClient:
    """Client bất đồng bộ, CHỈ ĐỌC, cho số liệu LIVE của một shop đã ủy quyền.

    Danh tính lấy từ :func:`get_settings` nếu không truyền tường minh. Truyền
    ``client`` (``httpx.AsyncClient`` với ``MockTransport``) để test không cần
    mạng; ``clock`` để cố định ``timestamp``; ``min_interval_s=0`` để bỏ giãn nhịp.
    """

    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
        access_token: str | None = None,
        shop_cipher: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = BASE_URL,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        clock: Callable[[], float] = time.time,
    ) -> None:
        settings = get_settings()
        self._app_key = (app_key if app_key is not None else settings.tiktok_shop_app_key).strip()
        self._app_secret = (
            app_secret if app_secret is not None else settings.tiktok_shop_app_secret
        ).strip()
        self._access_token = (
            access_token if access_token is not None else settings.tiktok_shop_access_token
        ).strip()
        self._shop_cipher = (
            shop_cipher if shop_cipher is not None else settings.tiktok_shop_shop_cipher
        ).strip()
        self._base = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None
        self._min_interval_s = max(0.0, float(min_interval_s))
        self._clock = clock
        self._lan_goi_truoc: float | None = None

    # -- danh tính ---------------------------------------------------------

    def _credential_values(self) -> dict[str, str]:
        return {
            "TIKTOK_SHOP_APP_KEY": self._app_key,
            "TIKTOK_SHOP_APP_SECRET": self._app_secret,
            "TIKTOK_SHOP_ACCESS_TOKEN": self._access_token,
            "TIKTOK_SHOP_SHOP_CIPHER": self._shop_cipher,
        }

    def require_credentials(self) -> None:
        """Báo lỗi tiếng Việt NGAY nếu thiếu biến, trước mọi vòng mạng."""
        problem = credential_problem(self._credential_values())
        if problem:
            raise ValueError(problem)

    def _che(self, text: str) -> str:
        return che_bi_mat(text, (self._access_token, self._app_secret))

    # -- vận chuyển --------------------------------------------------------

    async def _giu_nhip(self) -> None:
        if self._min_interval_s <= 0:
            return
        if self._lan_goi_truoc is not None:
            cho = self._min_interval_s - (time.monotonic() - self._lan_goi_truoc)
            if cho > 0:
                await asyncio.sleep(cho)
        self._lan_goi_truoc = time.monotonic()

    async def _goi(
        self, ten: str, path: str, query: Mapping[str, Any]
    ) -> tuple[dict[str, Any], str | None]:
        """GET một endpoint đã ký; trả ``(data, request_id)``.

        Tự thử lại khi bị bóp nhịp (tối đa :data:`RATE_LIMIT_MAX_RETRIES`, tôn
        trọng ``Retry-After``) và khi lỗi tạm thời (tối đa
        :data:`TRANSIENT_MAX_RETRIES`). Lỗi danh tính/quyền/cấu hình nổi lên ngay.
        """
        self.require_credentials()
        lan_rate = 0
        lan_tam_thoi = 0
        while True:
            await self._giu_nhip()
            params = build_signed_query(
                path,
                query,
                app_key=self._app_key,
                app_secret=self._app_secret,
                shop_cipher=self._shop_cipher,
                timestamp=int(self._clock()),
            )
            headers = {
                "x-tts-access-token": self._access_token,
                "content-type": "application/json",
            }
            retry_after: float | None = None
            try:
                resp = await self._client.get(self._base + path, params=params, headers=headers)
            except httpx.HTTPError as exc:
                # str(exc) của httpx có thể chứa URL — chỉ giữ tên lớp.
                err = tao_loi("network", type(exc).__name__)
            else:
                loi_phan_hoi, data, request_id = self._doc_phan_hoi(resp)
                if loi_phan_hoi is None:
                    return data, request_id
                err = loi_phan_hoi
                retry_after = _retry_after_s(resp.headers.get("Retry-After"))

            if isinstance(err, TikTokShopRateLimitError):
                # 36009037 = hạn mức THEO GIỜ của shop thử: thử lại sau vài giây chỉ
                # đốt thêm hạn mức; tài liệu bảo chờ sang giờ sau.
                if lan_rate >= RATE_LIMIT_MAX_RETRIES or err.code == MA_SANDBOX_THEO_GIO:
                    raise err
                cho = min(RATE_LIMIT_BASE_S * (2**lan_rate), RATE_LIMIT_CAP_S)
                cho += random.uniform(0.0, RATE_LIMIT_JITTER_S)
                if retry_after is not None:
                    if retry_after > RETRY_AFTER_MAX_S:
                        raise err
                    cho = max(cho, retry_after)
                lan_rate += 1
                logger.warning(
                    "TikTok Shop %s: bị giới hạn nhịp (%s) — chờ %.1fs rồi thử lại (%d/%d).",
                    ten,
                    err.code,
                    cho,
                    lan_rate,
                    RATE_LIMIT_MAX_RETRIES,
                )
                await asyncio.sleep(cho)
                continue
            if err.loai == "transient" and lan_tam_thoi < TRANSIENT_MAX_RETRIES:
                cho = min(RATE_LIMIT_BASE_S * (2**lan_tam_thoi), RATE_LIMIT_CAP_S)
                lan_tam_thoi += 1
                logger.warning(
                    "TikTok Shop %s: lỗi tạm thời (%s) — chờ %.1fs rồi thử lại (%d/%d).",
                    ten,
                    err.code,
                    cho,
                    lan_tam_thoi,
                    TRANSIENT_MAX_RETRIES,
                )
                await asyncio.sleep(cho)
                continue
            raise err

    def _doc_phan_hoi(
        self, resp: httpx.Response
    ) -> tuple[TikTokShopApiError | None, dict[str, Any], str | None]:
        status = resp.status_code
        try:
            payload = resp.json()
        except ValueError:
            code = "http_error" if status >= 400 else "bad_json"
            return (
                tao_loi(code, f"phản hồi không phải JSON ({len(resp.content)} byte)", status),
                {},
                None,
            )
        if not isinstance(payload, dict):
            return tao_loi("bad_json", "envelope không phải object", status), {}, None
        request_id = str(payload.get("request_id") or "") or None
        raw_code = payload.get("code")
        code = "" if raw_code is None else str(raw_code).strip()
        message = self._che(str(payload.get("message") or ""))
        if code not in ("", "0"):
            return tao_loi(code, message, status, request_id), {}, None
        if status >= 400:
            return tao_loi("http_error", message, status, request_id), {}, None
        if code == "":
            return tao_loi("bad_json", "envelope thiếu trường code", status, request_id), {}, None
        data = payload.get("data")
        return None, data if isinstance(data, dict) else {}, request_id

    async def _cac_trang(
        self,
        ten: str,
        path: str,
        query: Mapping[str, Any],
        lay_muc: Callable[[dict[str, Any]], list[Any]],
        max_pages: int,
    ) -> list[tuple[dict[str, Any], str | None]]:
        """Theo ``next_page_token`` tới hết; từ chối vòng lặp và trần số trang.

        Dừng khi: không còn token; trang rỗng; hoặc đã đủ ``total_count``. Một
        token lặp lại hay vượt ``max_pages`` là LỖI (không cắt âm thầm dữ liệu
        của một thí nghiệm).
        """
        if max_pages < 1:
            raise ValueError("max_pages phải ≥ 1.")
        trang: list[tuple[dict[str, Any], str | None]] = []
        token: str | None = None
        da_thay: set[str] = set()
        so_muc = 0
        for _ in range(max_pages):
            q = dict(query)
            if token:
                q["page_token"] = token
            data, request_id = await self._goi(ten, path, q)
            trang.append((data, request_id))
            muc = lay_muc(data)
            so_muc += len(muc)
            nxt = str(data.get("next_page_token") or "")
            total = _int_hoac_none(data.get("total_count"))
            if not nxt or not muc or (total is not None and so_muc >= total):
                return trang
            if nxt in da_thay:
                raise TikTokShopApiError(
                    code="phan_trang_lap",
                    giai_thich=(
                        f"TikTok Shop {ten} trả lại một page_token đã dùng — dừng để không lặp "
                        "vô hạn. Chạy lại sau ít phút; nếu lặp lại, báo người giữ mã."
                    ),
                )
            da_thay.add(nxt)
            token = nxt
        raise TikTokShopApiError(
            code="qua_so_trang",
            giai_thich=(
                f"TikTok Shop {ten}: đã đọc {max_pages} trang mà vẫn còn trang sau — dừng thay "
                "vì cắt bớt dữ liệu âm thầm. Tăng max_pages rồi chạy lại."
            ),
        )

    # -- endpoint ----------------------------------------------------------

    async def list_live_sessions(
        self,
        start_date_ge: date | str,
        end_date_lt: date | str,
        *,
        account_type: str | None = "OFFICIAL_ACCOUNTS",
        page_size: int = PAGE_SIZE_MAX,
        currency: str = "LOCAL",
        sort_field: str | None = None,
        sort_order: str | None = None,
        max_pages: int = MAX_PAGES,
    ) -> DanhSachPhienLive:
        """Mọi phiên LIVE trong ``[start_date_ge, end_date_lt)`` (ngày theo múi giờ
        đăng ký của shop — Việt Nam là UTC+7).

        Mặc định ``account_type="OFFICIAL_ACCOUNTS"`` vì chỉ phiên của tài khoản
        chính thức/marketing mới có số liệu theo phút. Truyền ``None`` để dùng
        mặc định của API (``ALL``).
        """
        start = _ngay_iso("start_date_ge", start_date_ge)
        end = _ngay_iso("end_date_lt", end_date_lt)
        if end <= start:
            raise ValueError(
                f"end_date_lt ({end}) phải SAU start_date_ge ({start}) — end_date_lt không "
                "tính ngày đó."
            )
        if not 1 <= int(page_size) <= PAGE_SIZE_MAX:
            raise ValueError(f"page_size phải trong 1..{PAGE_SIZE_MAX} (tài liệu: tối đa 100).")
        if account_type is not None and account_type not in ACCOUNT_TYPES:
            raise ValueError(
                f"account_type={account_type!r} không hợp lệ — chỉ nhận {ACCOUNT_TYPES}."
            )
        if currency not in CURRENCIES:
            raise ValueError(f"currency={currency!r} không hợp lệ — chỉ nhận {CURRENCIES}.")
        if sort_order is not None and sort_order not in SORT_ORDERS:
            raise ValueError(f"sort_order={sort_order!r} không hợp lệ — chỉ nhận {SORT_ORDERS}.")
        query = {
            "start_date_ge": start,
            "end_date_lt": end,
            "page_size": int(page_size),
            "currency": currency,
            "account_type": account_type,
            "sort_field": sort_field,
            "sort_order": sort_order,
        }

        def lay_phien(data: dict[str, Any]) -> list[Any]:
            items = data.get("live_stream_sessions")
            return items if isinstance(items, list) else []

        trang = await self._cac_trang(
            "shop_lives/performance", PATH_LIVE_LIST, query, lay_phien, max_pages
        )
        phien: list[dict[str, Any]] = []
        for data, _ in trang:
            phien.extend(item for item in lay_phien(data) if isinstance(item, dict))
        cuoi = trang[-1][0]
        return DanhSachPhienLive(
            phien=phien,
            total_count=_int_hoac_none(cuoi.get("total_count")),
            latest_available_date=(
                str(cuoi["latest_available_date"]) if cuoi.get("latest_available_date") else None
            ),
            so_trang=len(trang),
            request_ids=[rid for _, rid in trang if rid],
        )

    async def performance_per_minutes(
        self,
        live_id: str,
        *,
        currency: str = "LOCAL",
        max_pages: int = MAX_PAGES,
    ) -> HieuSuatTheoPhut:
        """Chuỗi số liệu theo phút của một phiên ĐÃ KẾT THÚC, gộp mọi trang.

        ``intervals`` giữ nguyên thứ tự và cấu trúc TikTok trả; ``overall`` lấy từ
        trang đầu có ``overall``. Lệch giữa số phút đọc được và ``total_count`` được
        ghi vào ``canh_bao`` (không tự sửa).
        """
        ma = _ma_hop_le_live_id(live_id)
        if currency not in CURRENCIES:
            raise ValueError(f"currency={currency!r} không hợp lệ — chỉ nhận {CURRENCIES}.")
        path = PATH_LIVE_MINUTES.format(live_id=ma)

        def lay_phut(data: dict[str, Any]) -> list[Any]:
            perf = data.get("performance")
            items = perf.get("intervals") if isinstance(perf, dict) else None
            return items if isinstance(items, list) else []

        trang = await self._cac_trang(
            "performance_per_minutes", path, {"currency": currency}, lay_phut, max_pages
        )
        intervals: list[dict[str, Any]] = []
        overall: dict[str, Any] = {}
        for data, _ in trang:
            perf = data.get("performance")
            if not overall and isinstance(perf, dict) and isinstance(perf.get("overall"), dict):
                overall = dict(perf["overall"])
            intervals.extend(item for item in lay_phut(data) if isinstance(item, dict))
        total = _int_hoac_none(trang[-1][0].get("total_count"))
        canh_bao: list[str] = []
        if total is not None and total != len(intervals):
            canh_bao.append(
                f"TikTok báo total_count={total} nhưng đọc được {len(intervals)} phút — ghi nhận "
                "vào nhật ký phiên và kéo lại sau."
            )
            logger.info("performance_per_minutes: %s", canh_bao[-1])
        return HieuSuatTheoPhut(
            live_id=ma,
            overall=overall,
            intervals=intervals,
            total_count=total,
            so_trang=len(trang),
            request_ids=[rid for _, rid in trang if rid],
            canh_bao=canh_bao,
        )

    async def products_performance(
        self,
        live_id: str,
        *,
        currency: str = "LOCAL",
        sort_field: str | None = None,
        sort_order: str | None = None,
    ) -> list[dict[str, Any]]:
        """Số liệu theo sản phẩm của một phiên (một lời gọi — tài liệu không có phân trang).

        Trường số lượt bấm được tài liệu viết là ``produt_clicks``; giữ nguyên.
        """
        ma = _ma_hop_le_live_id(live_id)
        if currency not in CURRENCIES:
            raise ValueError(f"currency={currency!r} không hợp lệ — chỉ nhận {CURRENCIES}.")
        if sort_order is not None and sort_order not in SORT_ORDERS:
            raise ValueError(f"sort_order={sort_order!r} không hợp lệ — chỉ nhận {SORT_ORDERS}.")
        data, _ = await self._goi(
            "products_performance",
            PATH_LIVE_PRODUCTS.format(live_id=ma),
            {"currency": currency, "sort_field": sort_field, "sort_order": sort_order},
        )
        items = data.get("products")
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


# ---------------------------------------------------------------------------
# Quy chuỗi theo phút về khối switchback (hàm thuần)
# ---------------------------------------------------------------------------

#: Độ dài tối thiểu của một interval "minute-level" khi xét ranh giới khối.
GIAY_MOT_PHUT = 60

#: Trường CỘNG ĐƯỢC giữa các phút: tên trong kết quả → (nhóm, trường) trong interval.
#: Không có ``customers`` (một khách đặt ở hai phút bị đếm hai lần) và không có
#: trường tỷ lệ (``ctr``, ``*_rate``, ``gpm``…) — tỷ lệ phải tính lại từ tổng.
TRUONG_CONG_DON: dict[str, tuple[str, str]] = {
    "sku_orders": ("sales", "sku_orders"),
    "main_orders": ("sales", "main_orders"),
    "items_sold": ("sales", "items_sold"),
    "created_sku_orders": ("conversion", "created_sku_orders"),
    "views": ("traffic", "views"),
    "impressions": ("traffic", "impressions"),
    "product_impressions": ("traffic", "product_impressions"),
    "product_clicks": ("traffic", "product_clicks"),
    "comments": ("interactions", "comments"),
    "likes": ("interactions", "likes"),
    "shares": ("interactions", "shares"),
    "new_followers": ("interactions", "new_followers"),
    # "The number of viewers within this interval" cộng qua các phút KHÔNG phải
    # số người xem duy nhất; nó xấp xỉ người·phút (diễn giải của nhóm — tài liệu
    # không định nghĩa). Tên trường nói rõ điều đó.
    "viewers_cong_moi_phut": ("traffic", "viewers"),
}


@dataclass(frozen=True)
class SoLieuKhoi:
    """Tổng các phút nằm TRỌN trong một khối."""

    block_index: int | None
    assignment: str | None
    is_washout: bool
    start_offset_s: float
    end_offset_s: float
    so_phut: int
    so_phut_bo_burn_in: int
    tong: dict[str, int | None]
    gmv: Decimal | None
    tien_te: str | None
    so_phut_thieu: dict[str, int]


@dataclass(frozen=True)
class KetQuaGopKhoi:
    """Kết quả :func:`gop_theo_khoi`, kèm sổ các phút KHÔNG được tính."""

    khoi: list[SoLieuKhoi]
    so_phut_cat_ngang: int
    phut_cat_ngang: list[tuple[int, int]]
    so_phut_ngoai_lich: int
    so_phut_hong: int
    so_phut_trung_lap: int
    #: Số interval hợp lệ có ``end_time - start_time < 60`` (kể cả bằng nhau như mẫu
    #: chính thức) nên được coi là ``[start_time, start_time + 60)`` khi xét ranh giới.
    so_phut_gia_dinh_60s: int = 0


def _thuoc_tinh(block: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(block, Mapping):
            if name in block:
                return block[name]
        elif hasattr(block, name):
            return getattr(block, name)
    return default


def _moc_giay(start_ts: datetime | float | int) -> float:
    if isinstance(start_ts, datetime):
        if start_ts.tzinfo is None:
            raise ValueError(
                "start_ts không có múi giờ — không biết là giờ Việt Nam hay UTC. Truyền "
                "datetime có tzinfo (ví dụ start_ts của phiên LiveLift, lưu theo UTC)."
            )
        return start_ts.timestamp()
    if isinstance(start_ts, bool) or not isinstance(start_ts, int | float):
        raise ValueError("start_ts phải là datetime có múi giờ hoặc Unix timestamp (giây).")
    return float(start_ts)


def gop_theo_khoi(
    intervals: Iterable[Mapping[str, Any]],
    blocks: Sequence[Any],
    start_ts: datetime | float | int,
    *,
    burn_in_s: float = 0.0,
) -> KetQuaGopKhoi:
    """Quy ``intervals[]`` của ``performance_per_minutes`` về các khối switchback.

    ``blocks``: dict hoặc đối tượng có ``start_offset_s``/``end_offset_s`` (giây
    tính từ ``start_ts`` — đúng quy ước của lịch LiveLift), tùy chọn
    ``block_index``/``index``, ``assignment``, ``is_washout``. Khối là nửa
    khoảng ``[start, end)``, không được chồng lên nhau. ``start_ts``: thời điểm
    phiên LiveLift lên sóng (datetime có múi giờ hoặc Unix giây). ``start_time``/
    ``end_time`` của TikTok là Unix giây UTC.

    Quy tắc phút cắt ngang ranh giới (CÓ CHỦ ĐÍCH)
    ---------------------------------------------
    Mỗi phút là một con số gộp, không tách được theo giây. Chia tỷ lệ sẽ bịa
    ra phần lẻ của lượt bấm/đơn hàng; gán cả phút cho khối chứa ``start_time``
    sẽ trộn điều kiện BẬT của khối sau vào khối TẮT trước (hoặc ngược lại). Vì
    vậy một phút chỉ được tính cho khối ``k`` khi nó nằm **trọn** trong khối::

        start_k + burn_in_s <= start_time - start_ts
        max(end_time, start_time + 60) - start_ts <= end_k

    Vì sao ``max(end_time, start_time + 60)``: tài liệu không nói ``end_time`` là
    mốc mở (``start + 60``) hay đóng (``start + 59``), và mẫu phản hồi chính thức
    (https://partner.tiktokshop.com/docv2/page/get-shop-live-minute-performance-202510,
    truy cập 17/09/2026) còn để ``start_time == end_time``. Endpoint trả số liệu
    *"minute-level"*, nên mỗi interval được coi là phủ ÍT NHẤT một phút kể từ
    ``start_time``. Nếu chỉ so ``end_time``, phút có ``end_time == start_time``
    bắt đầu ở 600 s với ranh giới khối lệch giây ở 630 s sẽ bị cộng trọn vào khối
    trước, dù 30 giây cuối thuộc điều kiện của khối sau. Số interval dựa vào giả
    định này được đếm ở ``so_phut_gia_dinh_60s``. Mọi phút khác bị LOẠI và được
    ĐẾM, không bao giờ biến mất âm thầm:

    - ``so_phut_cat_ngang`` / ``phut_cat_ngang``: phút chạm hai khối, hoặc chạm
      mép lịch (bắt đầu trước giờ lên sóng / trong khoảng trống giữa hai khối
      nhưng kéo sang một khối). Với ranh giới khối có jitter theo giây, thường mất
      khoảng một phút ở mỗi ranh giới — hãy báo con số này trong phương pháp.
    - ``so_phut_bo_burn_in`` (theo từng khối): phút bắt đầu trong ``burn_in_s``
      giây đầu khối (cùng ý nghĩa với ``burn_in_s`` của
      :func:`livelift.core.features.block_frame`; mặc định 0 ở hàm thuần này).
    - ``so_phut_ngoai_lich``: phút không chạm khối nào.
    - ``so_phut_hong``: thiếu/sai ``start_time``/``end_time`` hoặc ``end < start``.
    - ``so_phut_trung_lap``: cùng ``start_time`` xuất hiện lần nữa (giữ lần đầu).

    Độ lệch đồng hồ giữa máy chủ LiveLift và TikTok chưa được đo; nếu lệch vài
    giây, một phút sát ranh giới vẫn có thể bị xếp sai — dùng ``burn_in_s`` làm
    đệm.

    Tổng (``tong``) chỉ gồm các trường cộng được (:data:`TRUONG_CONG_DON`);
    ``None`` nghĩa là không phút nào trong khối có trường đó. ``gmv`` cộng bằng
    ``Decimal``; hai tiền tệ khác nhau trong cùng lời gọi là ``ValueError``.
    """
    t0 = _moc_giay(start_ts)
    if burn_in_s < 0:
        raise ValueError("burn_in_s không được âm.")

    khoi_vao: list[tuple[float, float, Any]] = []
    for block in blocks:
        start = _thuoc_tinh(block, "start_offset_s")
        end = _thuoc_tinh(block, "end_offset_s")
        if start is None or end is None:
            raise ValueError("Mỗi khối phải có start_offset_s và end_offset_s (giây).")
        start_f, end_f = float(start), float(end)
        if end_f <= start_f:
            raise ValueError(f"Khối [{start_f:g}, {end_f:g}) rỗng hoặc ngược chiều.")
        khoi_vao.append((start_f, end_f, block))
    khoi_vao.sort(key=lambda item: item[0])
    for (_, end_truoc, _), (start_sau, _, _) in pairwise(khoi_vao):
        if start_sau < end_truoc:
            raise ValueError("Các khối chồng lên nhau — một phút không thể thuộc hai khối.")

    so_phut = [0] * len(khoi_vao)
    so_burn_in = [0] * len(khoi_vao)
    tong: list[dict[str, int | None]] = [dict.fromkeys(TRUONG_CONG_DON) for _ in khoi_vao]
    thieu: list[dict[str, int]] = [{} for _ in khoi_vao]
    gmv: list[Decimal | None] = [None] * len(khoi_vao)
    tien_te_chung: str | None = None

    cat_ngang: list[tuple[int, int]] = []
    ngoai_lich = hong = trung_lap = gia_dinh_60s = 0
    da_thay: set[int] = set()

    for interval in intervals:
        st = _int_hoac_none(interval.get("start_time"))
        et = _int_hoac_none(interval.get("end_time"))
        if st is None or et is None or et < st:
            hong += 1
            continue
        if st in da_thay:
            trung_lap += 1
            continue
        da_thay.add(st)
        if et - st < GIAY_MOT_PHUT:
            gia_dinh_60s += 1
        # Mỗi interval phủ ít nhất [start_time, start_time + 60): xem docstring.
        a, b = st - t0, max(et, st + GIAY_MOT_PHUT) - t0

        vi_tri = next((i for i, (s, e, _) in enumerate(khoi_vao) if s <= a < e), None)
        if vi_tri is None:
            if any(s < b and a < e for s, e, _ in khoi_vao):
                cat_ngang.append((st, et))
            else:
                ngoai_lich += 1
            continue
        start_k, end_k, _ = khoi_vao[vi_tri]
        if b > end_k:
            cat_ngang.append((st, et))
            continue
        if a < start_k + burn_in_s:
            so_burn_in[vi_tri] += 1
            continue

        so_phut[vi_tri] += 1
        for ten, (nhom, truong) in TRUONG_CONG_DON.items():
            obj = interval.get(nhom)
            value = _int_hoac_none(obj.get(truong)) if isinstance(obj, Mapping) else None
            if value is None:
                thieu[vi_tri][ten] = thieu[vi_tri].get(ten, 0) + 1
                continue
            tong[vi_tri][ten] = (tong[vi_tri][ten] or 0) + value
        sales = interval.get("sales")
        gmv_obj = sales.get("gmv") if isinstance(sales, Mapping) else None
        amount = gmv_obj.get("amount") if isinstance(gmv_obj, Mapping) else None
        try:
            so_tien = Decimal(str(amount)) if amount is not None else None
        except InvalidOperation:
            so_tien = None
        if so_tien is None or not so_tien.is_finite():
            thieu[vi_tri]["gmv"] = thieu[vi_tri].get("gmv", 0) + 1
            continue
        tien_te = gmv_obj.get("currency") if isinstance(gmv_obj, Mapping) else None
        if tien_te:
            if tien_te_chung is not None and tien_te != tien_te_chung:
                raise ValueError(
                    f"GMV trộn hai tiền tệ ({tien_te_chung} và {tien_te}) — kéo lại cùng "
                    "currency (LOCAL hoặc USD) cho cả phiên."
                )
            tien_te_chung = str(tien_te)
        gmv[vi_tri] = (gmv[vi_tri] or Decimal(0)) + so_tien

    ket_qua = []
    for i, (start_k, end_k, block) in enumerate(khoi_vao):
        index = _thuoc_tinh(block, "block_index", "index")
        ket_qua.append(
            SoLieuKhoi(
                block_index=None if index is None else int(index),
                assignment=_thuoc_tinh(block, "assignment"),
                is_washout=bool(_thuoc_tinh(block, "is_washout", default=False)),
                start_offset_s=start_k,
                end_offset_s=end_k,
                so_phut=so_phut[i],
                so_phut_bo_burn_in=so_burn_in[i],
                tong=tong[i],
                gmv=gmv[i],
                tien_te=tien_te_chung if gmv[i] is not None else None,
                so_phut_thieu=thieu[i],
            )
        )
    return KetQuaGopKhoi(
        khoi=ket_qua,
        so_phut_cat_ngang=len(cat_ngang),
        phut_cat_ngang=cat_ngang,
        so_phut_ngoai_lich=ngoai_lich,
        so_phut_hong=hong,
        so_phut_trung_lap=trung_lap,
        so_phut_gia_dinh_60s=gia_dinh_60s,
    )
