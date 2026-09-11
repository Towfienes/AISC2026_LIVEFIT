"""Shopee Live ingestion via the OFFICIAL Shopee Open Platform API v2.

Đây là đường **chính thức, hợp Điều khoản dịch vụ** — khác hẳn TikTok
(dịch ngược, đã bị chặn) và yt-dlp (trái ToS của YouTube). Nó đọc buổi live của
**chính shop mình** bằng token do chủ shop tự cấp qua OAuth của Shopee.

Kiểm chứng thật ngày 11/09/2026 (xem ``docs/nen-tang-ho-tro.md`` §4):

- ``GET https://partner.shopeemobile.com/api/v2/livestream/get_latest_comment_list``
  TỒN TẠI: gọi không tham số trả ``{"error":"error_param","message":"There is no
  partner_id in query."}``, trong khi một đường dẫn bịa
  (``/api/v2/livestream/khong_ton_tai_abc``) trả **HTTP 404
  ``error_not_found``**. Đối chứng này là bằng chứng endpoint có thật, không
  phải suy đoán.
- Ký thử đúng lược đồ (partner_id/partner_key giả) → ``HTTP 403
  invalid_partner_id`` — tức cổng API **chấp nhận dạng yêu cầu** và chỉ từ chối
  vì danh tính giả. Nhóm chưa có ``SHOPEE_PARTNER_ID`` nên **chưa đọc được
  bình luận thật**; mọi hành vi dưới đây có test ngoại tuyến, chưa có live-fire.
- Tài liệu endpoint ghi rõ ``(For TW, ID, TH, PH, MY, SG, VN)`` — **có Việt Nam**.

Ba đặc tính của API này định hình toàn bộ thiết kế dưới đây:

1. **Cửa sổ 10 giây.** ``get_latest_comment_list`` chỉ trả bình luận *trong 10
   giây gần nhất*. Poll chậm hơn 10 s là **mất dữ liệu vĩnh viễn** — không có
   con trỏ ``since`` để quay lại như Facebook. Vì vậy :data:`MAX_SAFE_POLL_S`
   được ép cứng: truyền ``poll_s`` lớn hơn sẽ **báo lỗi ngay**, chứ không âm
   thầm bỏ sót bình luận trong một thí nghiệm nhân quả.
2. **Chữ ký nằm trong query string.** Lược đồ ký của Shopee bắt buộc
   ``access_token`` và ``shop_id`` phải là *tham số query* (chúng nằm trong
   chuỗi cơ sở của HMAC). Không thể đẩy token sang header như Facebook. Nên
   mọi lỗi ở đây được gói lại thành :class:`ShopeeApiError` — thông điệp
   **không bao giờ chứa URL**, vì ``httpx`` nhét URL đầy đủ vào mọi
   ``HTTPStatusError`` và token sẽ lọt vào traceback/log.
3. **Có tín hiệu chuyển đổi thật.** ``get_session_metric`` trả ``gmv``,
   ``orders``, ``atc``, ``ctr``, ``ccu``, ``peak_ccu`` — thứ mà YouTube và
   TikTok **không** có. Đây là lý do Shopee đáng đầu tư: nó là nền tảng duy
   nhất khảo sát được hôm nay vừa cho bình luận vừa cho kết quả thương mại
   qua một API chính thức.

Quyền riêng tư (hard rule 1): phản hồi bình luận **có** ``user_id`` và
``username``. :func:`parse_comment` chỉ đọc ``comment_id``/``content``/
``timestamp`` — hai trường định danh **không bao giờ** ra khỏi hàm này, kể cả
vào log. Văn bản thô được :class:`livelift.ingest.base.ApiSink` lọc PII trước
khi truyền đi.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from collections import deque
from collections.abc import AsyncIterator, Iterable
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

from livelift.config import get_settings
from livelift.ingest.base import Backoff, RawComment, RawTick

logger = logging.getLogger(__name__)

#: Cổng API theo vùng (src/schemas/region.ts của SDK Shopee, tra 11/09/2026).
#: Việt Nam dùng cổng GLOBAL — Shopee **không** có host riêng cho .vn.
REGION_BASE_URLS: dict[str, str] = {
    "global": "https://partner.shopeemobile.com/api/v2",
    "china": "https://openplatform.shopee.cn/api/v2",
    "brazil": "https://openplatform.shopee.com.br/api/v2",
    "sandbox": "https://openplatform.sandbox.test-stable.shopee.sg/api/v2",
}
DEFAULT_REGION = "global"

PATH_COMMENTS = "/livestream/get_latest_comment_list"
PATH_METRIC = "/livestream/get_session_metric"
PATH_DETAIL = "/livestream/get_session_detail"

#: Cửa sổ dữ liệu của ``get_latest_comment_list`` theo tài liệu Shopee.
COMMENT_WINDOW_S = 10.0
#: Nhịp poll tối đa còn an toàn. Vượt ngưỡng này là chắc chắn mất bình luận
#: (cửa sổ 10 s trôi qua giữa hai lần gọi), nên client **từ chối chạy**.
MAX_SAFE_POLL_S = 8.0
DEFAULT_POLL_S = 5.0
DEFAULT_TICK_S = 30.0

#: Số trang ``next_offset`` theo trong MỘT lần poll. Cửa sổ chỉ 10 s nên một
#: phòng rất đông vẫn hiếm khi vượt vài trang; chặn trên để không kẹt vòng lặp.
MAX_PAGES_PER_POLL = 20
_SEEN_IDS_MAX = 2048

AUTH_BACKOFF_S = 60.0
RATE_LIMIT_BACKOFF_S = 300.0
RETRY_CAP_S = 60.0

#: ``status`` của ``get_session_detail``: 0 = chưa bắt đầu, 1 = đang phát,
#: 2 = đã kết thúc.
STATUS_INIT = 0
STATUS_ONGOING = 1
STATUS_ENDED = 2

#: Mảnh chuỗi trong trường ``error`` của Shopee nghĩa là "người vận hành phải
#: sửa danh tính" — thử lại nhanh không cứu được.
#: CHƯA KIỂM CHỨNG TRÊN TÀI KHOẢN THẬT: nhóm chưa có partner_id, nên danh sách
#: này dựng từ quy ước đặt tên mã lỗi của Shopee chứ không phải từ lỗi đã gặp.
#: Nhánh mặc định là "transient" (thử lại) nên phân loại sai chỉ làm chậm chứ
#: không làm hỏng dữ liệu.
AUTH_ERROR_MARKERS = (
    "auth",
    "token",
    "sign",
    "permission",
    "partner_id",
    "shop_id",
    "forbid",
)
#: Mảnh chuỗi nghĩa là "đang bị bóp nhịp gọi" — token vẫn tốt, chỉ cần nghỉ.
RATE_LIMIT_MARKERS = ("rate", "limit", "too many", "frequen", "busy")

ErrorKind = Literal["auth", "rate_limit", "transient"]


class ShopeeApiError(Exception):
    """Lỗi từ Shopee Open Platform, **đã bỏ URL**.

    Lý do tồn tại: lược đồ ký của Shopee bắt buộc ``access_token`` nằm trong
    query string. ``httpx.HTTPStatusError`` in nguyên URL vào thông điệp, nên
    nếu để nó nổi lên thì token của shop sẽ nằm trong traceback và trong mọi
    dòng log ``logger.exception``. Lớp này chỉ mang mã trạng thái, mã lỗi và
    ``request_id`` — đủ để gỡ rối, không đủ để lộ khóa.
    """

    def __init__(
        self,
        code: str,
        message: str = "",
        status: int | None = None,
        request_id: str | None = None,
    ) -> None:
        self.code = code
        self.api_message = message
        self.status = status
        self.request_id = request_id
        detail = f"Shopee API lỗi {code!r}"
        if status is not None:
            detail += f" (HTTP {status})"
        if message:
            detail += f": {message}"
        if request_id:
            detail += f" [request_id={request_id}]"
        super().__init__(detail)


def sign_request(
    partner_id: str,
    partner_key: str,
    path: str,
    timestamp: int,
    access_token: str,
    shop_id: str,
) -> str:
    """HMAC-SHA256 hex của ``partner_id + path + timestamp + access_token + shop_id``.

    ``path`` là đường dẫn ĐẦY ĐỦ tính từ gốc host (``/api/v2/livestream/...``),
    không phải phần đuôi — ký sai phần này là lỗi hay gặp nhất khi tích hợp
    Shopee. Lược đồ đọc từ ``src/fetch.ts`` của SDK Shopee, tra 11/09/2026.
    """
    base_string = f"{partner_id}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        partner_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def build_signed_params(
    partner_id: str,
    partner_key: str,
    path: str,
    access_token: str,
    shop_id: str,
    extra: dict[str, Any] | None = None,
    timestamp: int | None = None,
) -> dict[str, str]:
    """Bộ tham số query đã ký cho một lời gọi cấp shop."""
    ts = int(time.time()) if timestamp is None else timestamp
    params: dict[str, str] = {str(k): str(v) for k, v in (extra or {}).items()}
    params.update(
        {
            "partner_id": partner_id,
            "timestamp": str(ts),
            "access_token": access_token,
            "shop_id": shop_id,
            "sign": sign_request(partner_id, partner_key, path, ts, access_token, shop_id),
        }
    )
    return params


def classify_error(exc: Exception) -> ErrorKind:
    """auth / rate_limit / transient — quyết định nghỉ bao lâu rồi thử lại."""
    if isinstance(exc, ShopeeApiError):
        haystack = f"{exc.code} {exc.api_message}".lower()
        if exc.status in (401, 403) or any(m in haystack for m in AUTH_ERROR_MARKERS):
            # Rate limit đôi khi cũng trả 403; ưu tiên nhận diện rate limit
            # để không bảo người vận hành đi xoay token đang còn tốt.
            if any(m in haystack for m in RATE_LIMIT_MARKERS):
                return "rate_limit"
            return "auth"
        if exc.status == 429 or any(m in haystack for m in RATE_LIMIT_MARKERS):
            return "rate_limit"
    return "transient"


def auth_error_message(exc: ShopeeApiError) -> str:
    return (
        f"XÁC THỰC Shopee THẤT BẠI ({exc.code}). Việc cần làm: chạy "
        "`python scripts/kiem_tra_shopee.py` để xem token còn hạn không — "
        "access_token của Shopee chỉ sống 4 giờ và phải làm mới bằng "
        "refresh_token. Kiểm tra cả SHOPEE_PARTNER_ID / SHOPEE_PARTNER_KEY / "
        "SHOPEE_SHOP_ID. Xem docs/nen-tang-ho-tro.md §4."
    )


def rate_limit_message(exc: ShopeeApiError) -> str:
    return (
        f"GIỚI HẠN nhịp gọi Shopee ({exc.code}) — token VẪN TỐT, KHÔNG cần đổi "
        f"token. Tự nghỉ {RATE_LIMIT_BACKOFF_S:.0f}s rồi chạy tiếp. Nếu lặp lại, "
        "giảm nhịp poll (nhưng KHÔNG được quá "
        f"{MAX_SAFE_POLL_S:.0f}s — cửa sổ bình luận chỉ {COMMENT_WINDOW_S:.0f}s) "
        "hoặc tắt bớt tiến trình ingest trên cùng một shop."
    )


def parse_comment(item: dict[str, Any]) -> RawComment | None:
    """Một phần tử ``response.list`` → :class:`RawComment`, hoặc None nếu hỏng.

    **Bỏ ``user_id`` và ``username``** ngay tại đây (hard rule 1 + §11.2): hai
    trường đó có trong phản hồi của Shopee nhưng không bao giờ được ra khỏi
    hàm này. ``author_ext_id`` để None chứ không phải ``user_id``, nên kể cả
    một lỗi nối dây sau này cũng không làm lộ danh tính người bình luận.
    """
    comment_id = item.get("comment_id")
    content = item.get("content")
    ts = item.get("timestamp")
    if comment_id is None or content is None or ts is None:
        return None
    try:
        ts_utc = datetime.fromtimestamp(float(ts), tz=UTC)
    except (TypeError, ValueError, OSError, OverflowError):
        return None
    return RawComment(
        platform="shopee",
        ext_id=str(comment_id),
        ts_utc=ts_utc,
        text=str(content),
        author_ext_id=None,
    )


def next_offset(data: dict[str, Any]) -> int | None:
    """``next_offset`` khi còn trang sau, None khi hết.

    Shopee trả ``next_offset`` cả khi đã hết dữ liệu, nên trang rỗng mới là
    dấu chấm hết thật; hàm này chỉ chuẩn hóa kiểu, vòng lặp quyết định dừng.
    """
    value = data.get("next_offset")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ShopeeLiveClient:
    """Client bất đồng bộ đọc bình luận + người xem của một phiên Shopee Live.

    Danh tính lấy từ :func:`get_settings` nếu không truyền tường minh. Truyền
    ``client`` (``httpx.AsyncClient`` với ``MockTransport``) để test không cần
    mạng.
    """

    def __init__(
        self,
        partner_id: str | None = None,
        partner_key: str | None = None,
        shop_id: str | None = None,
        access_token: str | None = None,
        region: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._partner_id = partner_id if partner_id is not None else settings.shopee_partner_id
        self._partner_key = partner_key if partner_key is not None else settings.shopee_partner_key
        self._shop_id = shop_id if shop_id is not None else settings.shopee_shop_id
        self._access_token = (
            access_token if access_token is not None else settings.shopee_access_token
        )
        region_name = (region if region is not None else settings.shopee_region).strip().lower()
        if region_name not in REGION_BASE_URLS:
            raise ValueError(
                f"SHOPEE_REGION không hợp lệ: {region_name!r} — chỉ nhận "
                f"{', '.join(sorted(REGION_BASE_URLS))}"
            )
        self._region = region_name
        self._base = REGION_BASE_URLS[region_name]
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None
        #: Lỗi gần nhất (None = khỏe) — runner in ra trong mỗi heartbeat.
        self.last_error: str | None = None
        #: Shopee KHÔNG trả header hạn mức như Facebook, nên luôn None. Giữ
        #: thuộc tính để runner dùng chung một giao diện heartbeat.
        self.last_usage_pct: float | None = None

    def _missing_credentials(self) -> list[str]:
        pairs = {
            "SHOPEE_PARTNER_ID": self._partner_id,
            "SHOPEE_PARTNER_KEY": self._partner_key,
            "SHOPEE_SHOP_ID": self._shop_id,
            "SHOPEE_ACCESS_TOKEN": self._access_token,
        }
        return [name for name, value in pairs.items() if not value]

    def require_credentials(self) -> None:
        """Báo lỗi tiếng Việt NGAY nếu thiếu danh tính, thay vì để Shopee trả
        ``invalid_partner_id`` sau một vòng mạng."""
        missing = self._missing_credentials()
        if missing:
            raise RuntimeError(
                "Thiếu danh tính Shopee trong .env: "
                + ", ".join(missing)
                + ". Xem docs/nen-tang-ho-tro.md §4 để biết cách xin "
                "partner_id/partner_key và ủy quyền shop."
            )

    # -- transport ---------------------------------------------------------

    async def _get(self, path: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Gọi một endpoint đã ký, trả về ``response`` của envelope.

        Mọi lỗi được gói thành :class:`ShopeeApiError` — **không có URL** trong
        thông điệp, vì access_token bắt buộc phải nằm trong query string.
        """
        params = build_signed_params(
            partner_id=self._partner_id,
            partner_key=self._partner_key,
            path=path,
            access_token=self._access_token,
            shop_id=self._shop_id,
            extra=extra,
        )
        try:
            resp = await self._client.get(self._base + path, params=params)
        except httpx.HTTPError as exc:
            # str(exc) của httpx có thể chứa URL (kèm token) — chỉ giữ tên lớp.
            raise ShopeeApiError(code="network", message=type(exc).__name__) from None
        try:
            body = resp.json()
        except ValueError:
            raise ShopeeApiError(
                code="bad_json",
                message=f"phản hồi không phải JSON ({len(resp.content)} byte)",
                status=resp.status_code,
            ) from None
        if not isinstance(body, dict):
            raise ShopeeApiError(
                code="bad_json", message="envelope không phải object", status=resp.status_code
            )
        error = str(body.get("error") or "")
        if error:
            raise ShopeeApiError(
                code=error,
                message=str(body.get("message") or ""),
                status=resp.status_code,
                request_id=str(body.get("request_id") or "") or None,
            )
        if resp.status_code >= 400:
            # Envelope sạch nhưng HTTP hỏng (cổng chặn trước khi vào API).
            raise ShopeeApiError(code="http_error", status=resp.status_code)
        response = body.get("response")
        return response if isinstance(response, dict) else {}

    async def _handle_poll_error(self, what: str, exc: Exception, backoff: Backoff) -> None:
        kind = classify_error(exc)
        if kind == "auth" and isinstance(exc, ShopeeApiError):
            self.last_error = auth_error_message(exc)
            logger.error("%s — tạm dừng %.0fs rồi thử lại.", self.last_error, AUTH_BACKOFF_S)
            await asyncio.sleep(AUTH_BACKOFF_S)
            return
        if kind == "rate_limit" and isinstance(exc, ShopeeApiError):
            self.last_error = rate_limit_message(exc)
            logger.error("%s", self.last_error)
            await asyncio.sleep(RATE_LIMIT_BACKOFF_S)
            return
        delay = backoff.next_delay()
        detail = exc.code if isinstance(exc, ShopeeApiError) else type(exc).__name__
        self.last_error = f"{what}: {detail}"
        logger.warning("%s thất bại: %s; thử lại sau %.1fs", what, detail, delay)
        await asyncio.sleep(delay)

    # -- comments ----------------------------------------------------------

    @staticmethod
    def _new_comments(
        items: Iterable[dict[str, Any]], seen: deque[str], seen_set: set[str]
    ) -> list[RawComment]:
        """Parse một trang, bỏ bình luận đã trả ở lần poll trước.

        Khử trùng lặp là **bắt buộc**, không phải tối ưu: cửa sổ 10 s và nhịp
        poll 5 s cố ý chồng lấn, nên mỗi bình luận được Shopee trả ~2 lần.
        """
        fresh: list[RawComment] = []
        for item in items:
            comment = parse_comment(item)
            if comment is None or comment.ext_id in seen_set:
                continue
            if len(seen) == seen.maxlen:
                seen_set.discard(seen[0])
            seen.append(comment.ext_id)
            seen_set.add(comment.ext_id)
            fresh.append(comment)
        return fresh

    async def iter_comments(
        self, session_id: str, poll_s: float = DEFAULT_POLL_S
    ) -> AsyncIterator[RawComment]:
        """Yield bình luận bằng cách poll cửa sổ 10 giây của Shopee.

        Không có con trỏ ``since``: mỗi lần poll lấy lại cả cửa sổ và lọc trùng
        theo ``comment_id``. Vì vậy nhịp poll **phải** nhỏ hơn cửa sổ — quá
        :data:`MAX_SAFE_POLL_S` thì hàm này ném ``ValueError`` ngay lập tức chứ
        không chạy rồi mất dữ liệu âm thầm.
        """
        if poll_s > MAX_SAFE_POLL_S:
            raise ValueError(
                f"poll_s={poll_s:.1f}s vượt ngưỡng an toàn {MAX_SAFE_POLL_S:.0f}s: "
                f"get_latest_comment_list CHỈ trả bình luận trong "
                f"{COMMENT_WINDOW_S:.0f}s gần nhất, poll chậm hơn là MẤT bình luận "
                "vĩnh viễn (không có con trỏ để lấy lại). Giảm poll_s xuống."
            )
        self.require_credentials()
        seen: deque[str] = deque(maxlen=_SEEN_IDS_MAX)
        seen_set: set[str] = set()
        backoff = Backoff(base_s=poll_s, cap_s=max(poll_s, RETRY_CAP_S))
        while True:
            offset = 0
            batch: list[RawComment] = []
            failed = False
            for _page in range(MAX_PAGES_PER_POLL):
                try:
                    data = await self._get(
                        PATH_COMMENTS, {"session_id": session_id, "offset": offset}
                    )
                except ShopeeApiError as exc:
                    await self._handle_poll_error("poll bình luận", exc, backoff)
                    failed = True
                    break
                items = data.get("list") or []
                batch.extend(self._new_comments(items, seen, seen_set))
                nxt = next_offset(data)
                if not items or nxt is None or nxt == offset:
                    break
                offset = nxt
            else:
                logger.warning(
                    "poll bình luận: dừng ở %d trang trong một lần poll — phòng live "
                    "quá đông; dữ liệu vẫn đủ nhưng hãy ghi nhận vào nhật ký phiên.",
                    MAX_PAGES_PER_POLL,
                )
            if failed:
                continue
            self.last_error = None
            backoff.reset()
            for comment in sorted(batch, key=lambda c: c.ts_utc):
                yield comment
            await asyncio.sleep(poll_s)

    # -- viewers -----------------------------------------------------------

    async def iter_viewers(
        self, session_id: str, every_s: float = DEFAULT_TICK_S
    ) -> AsyncIterator[RawTick]:
        """Yield số người xem đồng thời (``ccu``) mỗi ``every_s`` giây.

        Dừng khi ``get_session_detail`` báo ``status == 2`` (đã kết thúc).
        Trạng thái được hỏi TRƯỚC: ``get_session_metric`` vẫn trả số sau khi
        phiên đóng, nên kiểm tra ngược lại sẽ poll mãi một phiên đã chết.
        """
        self.require_credentials()
        backoff = Backoff(base_s=every_s, cap_s=max(every_s, RETRY_CAP_S))
        while True:
            try:
                detail = await self._get(PATH_DETAIL, {"session_id": session_id})
                status = detail.get("status")
                if status is not None and int(status) == STATUS_ENDED:
                    logger.info("phiên Shopee Live đã kết thúc (status=2) — dừng đếm người xem")
                    return
                metric = await self._get(PATH_METRIC, {"session_id": session_id})
            except ShopeeApiError as exc:
                await self._handle_poll_error("poll người xem", exc, backoff)
                continue
            self.last_error = None
            backoff.reset()
            ccu = metric.get("ccu")
            if ccu is not None:
                yield RawTick(
                    platform="shopee",
                    ts_utc=datetime.now(UTC),
                    viewers=float(ccu),
                )
            await asyncio.sleep(every_s)

    # -- conversion signals ------------------------------------------------

    async def get_session_metric(self, session_id: str) -> dict[str, Any]:
        """Chỉ số thời gian thực của phiên: ``gmv``, ``orders``, ``atc``,
        ``ctr``, ``ccu``, ``peak_ccu``, ``likes``, ``comments``, ``shares``,
        ``views``, ``avg_viewing_duration``.

        Đây là các số **cộng dồn từ đầu phiên**, không phải theo khối. Muốn số
        theo khối switchback thì lấy **hiệu** giữa hai mốc đầu/cuối khối — và
        phải ghi rõ trong phương pháp rằng biến kết quả là sai phân của một
        bộ đếm cộng dồn, chứ không phải sự kiện đơn lẻ có dấu thời gian.
        """
        self.require_credentials()
        return await self._get(PATH_METRIC, {"session_id": session_id})

    async def get_session_detail(self, session_id: str) -> dict[str, Any]:
        """Metadata phiên: ``title``, ``status``, ``start_time``, ``end_time``."""
        self.require_credentials()
        return await self._get(PATH_DETAIL, {"session_id": session_id})

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
