"""Facebook Live ingestion via the Graph API (own Page, Page access token).

Facts re-verified against the Graph API reference on **2026-09-09** (see
``docs/huong-dan-facebook-token.md`` for the operator-facing version):

- Comments are read by polling ``GET /{live-video-id}/comments``. Meta still
  documents a Server-Sent-Events stream (``/{id}/live_comments`` on
  ``streaming-graph.facebook.com``) but presents it as the *browser-client*
  option; polling is the documented server-side path and is what we use — it
  survives disconnects, needs no long-lived connection and resumes from a
  ``since`` cursor. (Earlier note in this file said the SSE stream "is gone";
  that overstated it — it is documented, we simply do not depend on it.)
- ``live_filter`` MUST be ``no_filter``: the default ``filter_low_quality``
  silently drops "low quality" comments, which for us is lost purchase intent.
- ``filter`` defaults to ``toplevel``, which hides replies. Live shoppers do
  reply to each other and to the shop, so we ask for ``stream`` (flat list
  including replies). Revert by setting :data:`COMMENT_FILTER` to ``toplevel``.
- ``order=reverse_chronological`` is a *hint*: the docs say "if the comments
  can be ranked, the order will always be ranked regardless of this modifier",
  so nothing here may assume an ordering — each batch is re-sorted by time and
  the cursor is taken from the max timestamp seen.
- **Pagination matters.** One page holds at most ``limit`` comments; a busy
  Vietnamese live room (or the first poll after a 60 s backoff) can exceed it.
  Without following ``paging.next`` those comments are lost forever, because
  the ``since`` cursor then jumps past them. We follow the ``after`` cursor up
  to :data:`MAX_PAGES_PER_POLL` pages per poll. ``paging.cursors.after`` is
  present even on the last page, so ``paging.next`` is what decides whether
  another page exists.
- Viewer count: ``GET /{live-video-id}?fields=live_views,status``. ``status``
  is checked FIRST — a broadcast walks LIVE → LIVE_STOPPED → PROCESSING → VOD
  and ``live_views`` can still be present after it stopped, which used to keep
  the tick loop running forever against a dead broadcast.
- Rate limits arrive as ``OAuthException`` with HTTP 400 as well (codes 4, 17,
  32, 613, often ``is_transient: true``). Classifying those as "expired token"
  told the operator to rotate a perfectly good token, so error classification
  is now three-way: auth / rate-limit / transient.
- ``X-App-Usage`` / ``X-Page-Usage`` / ``X-Business-Use-Case-Usage`` report
  quota consumption as percentages on *every* response. We surface the peak so
  an operator sees the wall coming instead of being cut off mid-session.
- Page-level quota is 4800 calls × engaged users per 24 h sliding window, which
  a small new Fanpage can exhaust: 5 s comment polling alone is ~17k calls per
  24 h. The usage warning above is the early-warning system for that.
- An app in Development Mode (Standard Access) reads its *own* Page with no App
  Review, using a Page access token (``pages_read_user_content`` for viewers'
  comments). Other people's Pages need Advanced Access = App Review + Business
  Verification.

The access token travels in an ``Authorization: Bearer`` header, never in the
query string: an httpx error message repeats the URL, so a token in the query
would end up in tracebacks and proxy logs.

Raw comment text stays in memory only; scrubbing happens in the sink
(see :mod:`livelift.ingest.base`). The commenter's id (``from``) is dropped
at normalization (description §11.2).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from collections.abc import AsyncIterator, Iterable, Mapping
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

from livelift.config import get_settings
from livelift.ingest.base import AUTH_STATUSES, Backoff, RawComment, RawTick, http_status

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com"
DEFAULT_POLL_S = 5.0
_SEEN_IDS_MAX = 2048
# Error handling: an expired/invalid Page token cannot be fixed by retrying —
# pause long and tell the operator what to do; a rate limit needs a longer,
# quieter pause; 429/5xx/transport errors get exponential backoff with a cap.
AUTH_BACKOFF_S = 60.0
RATE_LIMIT_BACKOFF_S = 300.0
RETRY_CAP_S = 60.0
#: Startup lookup of the live video id — a single network blip must not kill it.
LIVE_VIDEO_MAX_TRIES = 4

#: Comments per page. 100 is the practical Graph maximum for this edge.
COMMENT_PAGE_LIMIT = 100
#: Pages followed within ONE poll (100 × 10 = 1000 comments per 5 s poll).
MAX_PAGES_PER_POLL = 10
#: ``stream`` = flat list including replies; ``toplevel`` = replies dropped.
COMMENT_FILTER = "stream"

#: Warn once the peak Graph usage percentage crosses this (Meta throttles at 100).
USAGE_WARN_PCT = 75.0
#: Re-arm the warning only after usage falls this far below the threshold.
USAGE_WARN_HYSTERESIS_PCT = 10.0
_USAGE_HEADERS = ("x-app-usage", "x-page-usage", "x-business-use-case-usage")
_USAGE_PCT_KEYS = frozenset({"call_count", "total_cputime", "total_time"})

#: Graph error codes that mean "you are being rate limited", not "bad token".
RATE_LIMIT_CODES = frozenset({4, 17, 32, 613})
#: Graph error codes that mean "credentials/permissions", i.e. an operator must act.
AUTH_ERROR_CODES = frozenset({10, 102, 190, 200})
#: ``error_subcode`` hints for code 190 — the difference between "log in again"
#: and "someone removed the app" is the difference between 1 and 10 minutes of
#: panic at T−5 minutes.
TOKEN_SUBCODE_HINTS: dict[int, str] = {
    458: "người dùng đã gỡ ứng dụng khỏi tài khoản",
    459: "tài khoản đang bị Facebook yêu cầu xác minh (checkpoint)",
    460: "mật khẩu tài khoản đã đổi nên token cũ bị hủy",
    463: "token đã hết hạn",
    464: "tài khoản chưa được xác nhận",
    467: "token không còn hợp lệ (đã đăng xuất hoặc bị thu hồi)",
    492: "tài khoản không còn quyền quản trị Page này",
}

#: ``status`` values that mean the broadcast is over — stop polling.
#: (LiveVideo.BroadcastStatus: LIVE, LIVE_STOPPED, PROCESSING, VOD,
#: UNPUBLISHED, SCHEDULED_CANCELED, SCHEDULED_EXPIRED, SCHEDULED_LIVE,
#: SCHEDULED_UNPUBLISHED.)
ENDED_STATUSES = frozenset(
    {
        "VOD",
        "PROCESSING",
        "LIVE_STOPPED",
        "UNPUBLISHED",
        "SCHEDULED_CANCELED",
        "SCHEDULED_EXPIRED",
    }
)

ErrorKind = Literal["auth", "rate_limit", "transient"]


def _error_body(exc: httpx.HTTPError) -> dict[str, Any]:
    """The Graph ``error`` object of a failed response, ``{}`` when absent."""
    if not isinstance(exc, httpx.HTTPStatusError):
        return {}
    try:
        body = exc.response.json()
    except ValueError:
        return {}
    err = body.get("error") if isinstance(body, dict) else None
    return err if isinstance(err, dict) else {}


def classify_error(exc: httpx.HTTPError) -> ErrorKind:
    """Sort a Graph failure into auth / rate_limit / transient.

    The Graph API answers *everything* with HTTP 400 + ``OAuthException``, so
    the status code alone decides nothing: an expired token (code 190), a
    missing permission (code 200) and "application request limit reached"
    (code 4) all look the same from the outside. Order matters here — the
    rate-limit codes are checked before the OAuthException catch-all, and
    ``is_transient`` (Meta's own "this will pass" flag) before 401/403.
    """
    err = _error_body(exc)
    code = err.get("code")
    status = http_status(exc)
    if code in RATE_LIMIT_CODES or status == 429:
        return "rate_limit"
    if err.get("is_transient"):
        return "transient"
    if status in AUTH_STATUSES:
        return "auth"
    if code in AUTH_ERROR_CODES or err.get("type") == "OAuthException":
        return "auth"
    return "transient"


def _auth_error_message(exc: httpx.HTTPError) -> str:
    """Operator-facing (Vietnamese): what broke and what to do about it."""
    err = _error_body(exc)
    status = http_status(exc)
    code = err.get("code")
    subcode = err.get("error_subcode")
    hint = TOKEN_SUBCODE_HINTS.get(subcode) if isinstance(subcode, int) else None
    chi_tiet = f"HTTP {status}"
    if code is not None:
        chi_tiet += f", code {code}"
    if hint:
        chi_tiet += f" — {hint}"
    return (
        f"LỖI Facebook Graph API ({chi_tiet}): Page access token hết hạn hoặc thiếu quyền. "
        "Tạo token mới với quyền pages_read_engagement + pages_read_user_content, cập nhật "
        "FACEBOOK_PAGE_ACCESS_TOKEN trong .env, rồi chạy: python scripts/kiem_tra_facebook.py"
    )


def _rate_limit_message(exc: httpx.HTTPError) -> str:
    """Operator-facing (Vietnamese): quota, not credentials — do NOT rotate."""
    err = _error_body(exc)
    code = err.get("code")
    return (
        f"GIỚI HẠN nhịp gọi Facebook (code {code}): token VẪN TỐT, không cần đổi token. "
        f"Tạm dừng {RATE_LIMIT_BACKOFF_S:.0f}s. Nếu lặp lại, tăng khoảng poll "
        "(--poll-s) hoặc giảm số tiến trình ingest đang chạy trên cùng Page."
    )


def _collect_usage_pcts(node: Any, out: list[float]) -> None:
    """Walk a usage-header structure, collecting every percentage field.

    ``X-App-Usage`` is a flat object; ``X-Business-Use-Case-Usage`` nests
    lists of objects under business ids. Only the three documented percentage
    keys are collected — ``estimated_time_to_regain_access`` is minutes, not a
    percentage, and must never be compared against the warning threshold.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _USAGE_PCT_KEYS and isinstance(value, (int, float)):
                out.append(float(value))
            else:
                _collect_usage_pcts(value, out)
    elif isinstance(node, list):
        for value in node:
            _collect_usage_pcts(value, out)


def usage_percent(headers: Mapping[str, str]) -> float | None:
    """Peak Graph quota usage (0–100) across the usage headers, None if absent.

    Pure function over response headers so the warning logic is testable
    without a live quota.
    """
    found: list[float] = []
    for name in _USAGE_HEADERS:
        raw = headers.get(name)
        if not raw:
            continue
        try:
            _collect_usage_pcts(json.loads(raw), found)
        except ValueError:
            continue
    return max(found) if found else None


def _parse_graph_time(value: str) -> datetime:
    """Parse a Graph API timestamp like ``2026-08-24T13:05:42+0000`` to UTC."""
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        ts = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def parse_comment(item: dict[str, Any]) -> RawComment | None:
    """Parse one Graph comment object into a :class:`RawComment`.

    Pure function. Returns ``None`` for comments without a message (e.g.
    sticker-only). The ``from`` field is present in the raw object but
    deliberately ignored — the author id is dropped here, at normalization,
    and never reaches storage or transmission.
    """
    text = item.get("message")
    created = item.get("created_time")
    ext_id = item.get("id")
    if not text or not created or not ext_id:
        return None
    return RawComment(
        platform="facebook",
        ext_id=str(ext_id),
        ts_utc=_parse_graph_time(str(created)),
        text=str(text),
        author_ext_id=None,  # dropped at normalization — never transmitted
    )


def comment_params(
    since: int | None = None, after: str | None = None, limit: int = COMMENT_PAGE_LIMIT
) -> dict[str, str]:
    """Query parameters for one page of live-video comments.

    Module level (not a method) so the readiness checker in
    ``scripts/kiem_tra_facebook.py`` can exercise the EXACT request the
    ingest runner will make — a permission that is missing only for the real
    parameter set must fail in the checker, not at T−0.
    """
    params = {
        "order": "reverse_chronological",
        "live_filter": "no_filter",
        "filter": COMMENT_FILTER,
        "fields": "id,message,created_time",
        "limit": str(limit),
    }
    if since is not None:
        params["since"] = str(since)
    if after is not None:
        params["after"] = after
    return params


def next_page_cursor(data: Mapping[str, Any]) -> str | None:
    """The ``after`` cursor when another page exists, else ``None``.

    ``paging.cursors.after`` is returned even on the LAST page, so using it
    alone would make every poll walk to the page cap. ``paging.next`` is the
    field that actually says "there is more".
    """
    paging = data.get("paging") or {}
    if not isinstance(paging, dict) or not paging.get("next"):
        return None
    cursors = paging.get("cursors") or {}
    after = cursors.get("after") if isinstance(cursors, dict) else None
    return str(after) if after else None


class FacebookLiveClient:
    """Async client for live-video comments and viewer snapshots.

    Uses a Page access token and Graph version from :func:`get_settings`
    unless passed explicitly. An injected ``httpx.AsyncClient`` makes the
    class testable without network access.
    """

    def __init__(
        self,
        page_access_token: str | None = None,
        graph_version: str | None = None,
        client: httpx.AsyncClient | None = None,
        page_id: str | None = None,
    ) -> None:
        if page_access_token is None or graph_version is None:
            settings = get_settings()
            if page_access_token is None:
                page_access_token = settings.facebook_page_access_token
            if graph_version is None:
                graph_version = settings.facebook_graph_version
        self._token = page_access_token
        self._page_id = page_id
        self._base = f"{GRAPH_BASE}/{graph_version}"
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None
        #: Most recent error description (None = healthy); shown by the
        #: runner heartbeat so an operator sees a stuck loop without grepping.
        self.last_error: str | None = None
        #: Peak Graph quota usage seen so far (percent, None = unknown).
        self.last_usage_pct: float | None = None
        self._usage_warned = False

    # -- error handling ----------------------------------------------------

    async def _handle_poll_error(self, what: str, exc: httpx.HTTPError, backoff: Backoff) -> None:
        """Classify a polling failure, record it for the heartbeat, and sleep.

        Auth failures (expired token, missing permission): red Vietnamese
        error + long fixed pause — an operator must rotate the token, no
        amount of fast retrying helps. Rate limits: a longer pause and an
        explicit "your token is fine" so nobody rotates a good token at
        T−5 minutes. 429/5xx/transport: exponential backoff with a ceiling.
        """
        kind = classify_error(exc)
        if kind == "auth":
            self.last_error = _auth_error_message(exc)
            logger.error("%s — tạm dừng %.0fs rồi thử lại.", self.last_error, AUTH_BACKOFF_S)
            await asyncio.sleep(AUTH_BACKOFF_S)
            return
        if kind == "rate_limit":
            self.last_error = _rate_limit_message(exc)
            logger.error("%s", self.last_error)
            await asyncio.sleep(RATE_LIMIT_BACKOFF_S)
            return
        status = http_status(exc)
        delay = backoff.next_delay()
        detail = f"HTTP {status}" if status is not None else type(exc).__name__
        self.last_error = f"{what}: {detail}"
        logger.warning("%s failed: %s; retrying in %.1fs", what, detail, delay)
        await asyncio.sleep(delay)

    # -- discovery ---------------------------------------------------------

    async def get_active_live_video_id(self, page_id: str | None = None) -> str:
        """Resolve the Page's currently-LIVE video id.

        Saves the operator from digging the id out of a Facebook URL at
        T−2 minutes. Retries transient failures; an auth failure raises
        immediately with an actionable Vietnamese message (retrying cannot
        fix a bad token).
        """
        if page_id is None:
            page_id = self._page_id or get_settings().facebook_page_id
        if not page_id:
            raise RuntimeError(
                "Chưa có FACEBOOK_PAGE_ID trong .env — không biết đọc Page nào. "
                "Xem docs/huong-dan-facebook-token.md."
            )
        params = {
            "broadcast_status": '["LIVE"]',
            "fields": "id,status,broadcast_start_time,permalink_url",
            "limit": "5",
        }
        data: dict[str, Any] | None = None
        last_exc: Exception | None = None
        for attempt in range(1, LIVE_VIDEO_MAX_TRIES + 1):
            try:
                data = await self._get(f"/{page_id}/live_videos", params)
                break
            except httpx.HTTPError as exc:
                if classify_error(exc) == "auth":
                    raise RuntimeError(_auth_error_message(exc)) from exc
                last_exc = exc
                if attempt < LIVE_VIDEO_MAX_TRIES:
                    delay = 2.0 ** (attempt - 1)
                    logger.warning(
                        "live_videos lookup failed: %s (lần %d/%d); thử lại sau %.1fs",
                        type(exc).__name__,
                        attempt,
                        LIVE_VIDEO_MAX_TRIES,
                        delay,
                    )
                    await asyncio.sleep(delay)
        if data is None:
            raise RuntimeError(
                f"Không lấy được danh sách live video của Page {page_id} sau "
                f"{LIVE_VIDEO_MAX_TRIES} lần thử (lỗi mạng/API tạm thời) — chạy lại lệnh."
            ) from last_exc
        for item in data.get("data") or []:
            status = str(item.get("status") or "").upper()
            if item.get("id") and status in ("", "LIVE"):
                return str(item["id"])
        raise RuntimeError(
            f"Page {page_id} hiện KHÔNG có buổi live nào đang phát. Bấm phát live rồi "
            "chạy lại, hoặc truyền thẳng --source-id nếu đã biết live-video id."
        )

    # -- comments ----------------------------------------------------------

    @staticmethod
    def _new_comments(
        items: Iterable[dict[str, Any]], seen: deque[str], seen_set: set[str]
    ) -> list[RawComment]:
        """Parse a page, dropping comments already yielded in an earlier poll."""
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
        self, live_video_id: str, poll_s: float = DEFAULT_POLL_S
    ) -> AsyncIterator[RawComment]:
        """Yield comments by polling with a ``since`` cursor.

        ``live_filter=no_filter`` is non-negotiable (see module docstring).
        Each poll follows ``paging.next`` up to :data:`MAX_PAGES_PER_POLL`
        pages so a burst larger than one page is not silently dropped; the
        very first poll takes ONE page only, because a stream that has been
        running for an hour would otherwise be back-filled comment by comment
        before the first live one arrives. Ordering from Graph is a hint, so
        each poll's batch is re-sorted ascending before yielding.
        """
        since: int | None = None
        seen: deque[str] = deque(maxlen=_SEEN_IDS_MAX)
        seen_set: set[str] = set()
        backoff = Backoff(base_s=poll_s, cap_s=max(poll_s, RETRY_CAP_S))
        first_poll = True
        while True:
            after: str | None = None
            batch: list[RawComment] = []
            failed = False
            for _page in range(MAX_PAGES_PER_POLL):
                try:
                    data = await self._get(
                        f"/{live_video_id}/comments", comment_params(since, after)
                    )
                except httpx.HTTPError as exc:
                    await self._handle_poll_error("comment poll", exc, backoff)
                    failed = True
                    break
                items = data.get("data") or []
                fresh = self._new_comments(items, seen, seen_set)
                batch.extend(fresh)
                after = next_page_cursor(data)
                # Stop paging when the page was empty, Graph says there is no
                # next page, everything on it was already seen (we caught up
                # with the previous poll), or this is the bounded first poll.
                if not items or after is None or not fresh or first_poll:
                    break
            else:
                logger.warning(
                    "comment poll: dừng ở %d trang trong một lần poll — phòng live quá "
                    "đông, cân nhắc tăng poll_s hoặc chấp nhận trễ.",
                    MAX_PAGES_PER_POLL,
                )
            if failed:
                continue
            self.last_error = None
            backoff.reset()
            first_poll = False

            for comment in sorted(batch, key=lambda c: c.ts_utc):
                yield comment

            if batch:
                newest = max(c.ts_utc for c in batch)
                # 1s overlap on purpose: the seen-id set absorbs duplicates,
                # a forward-only cursor would drop same-second stragglers.
                since = int(newest.timestamp())
            await asyncio.sleep(poll_s)

    # -- viewers -----------------------------------------------------------

    async def iter_viewers(
        self, live_video_id: str, every_s: float = 30.0
    ) -> AsyncIterator[RawTick]:
        """Yield ``live_views`` snapshots every ``every_s`` seconds.

        ``status`` is inspected BEFORE ``live_views``: Graph keeps returning a
        viewer number for a short while after the broadcast stops, so a
        viewers-first check left the loop polling a dead broadcast forever.
        """
        backoff = Backoff(base_s=every_s, cap_s=max(every_s, RETRY_CAP_S))
        while True:
            try:
                data = await self._get(f"/{live_video_id}", {"fields": "live_views,status"})
            except httpx.HTTPError as exc:
                await self._handle_poll_error("viewer poll", exc, backoff)
                continue
            self.last_error = None
            backoff.reset()

            status = str(data.get("status") or "").upper()
            if status in ENDED_STATUSES:
                logger.info("live video đã kết thúc (status=%s) — dừng vòng đếm người xem", status)
                return
            viewers = data.get("live_views")
            if viewers is not None:
                yield RawTick(
                    platform="facebook",
                    ts_utc=datetime.now(UTC),
                    viewers=float(viewers),
                )
            await asyncio.sleep(every_s)

    # -- transport ---------------------------------------------------------

    def _note_usage(self, headers: Mapping[str, str]) -> None:
        """Record quota usage and warn once when it crosses the threshold."""
        pct = usage_percent(headers)
        if pct is None:
            return
        self.last_usage_pct = pct
        if pct >= USAGE_WARN_PCT and not self._usage_warned:
            self._usage_warned = True
            logger.warning(
                "CẢNH BÁO hạn mức Facebook: đã dùng %.0f%% quota (Facebook chặn ở 100%%). "
                "Giảm nhịp poll hoặc tắt bớt tiến trình ingest trên cùng Page.",
                pct,
            )
        elif pct < USAGE_WARN_PCT - USAGE_WARN_HYSTERESIS_PCT:
            self._usage_warned = False

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        # Token in a header, NOT in params: httpx puts the full URL in every
        # error message, so a query-string token leaks into tracebacks/logs.
        resp = await self._client.get(
            self._base + path,
            params=params,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        self._note_usage(resp.headers)  # read usage on failures too
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
