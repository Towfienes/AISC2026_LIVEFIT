"""Bộ thu bình luận chạy NỀN bên trong API — bấm nút là thu, không gõ lệnh.

Vì sao tệp này tồn tại (kiểm toán 17/09/2026)
---------------------------------------------
Trước ngày này, đưa bình luận của một buổi live vào LiveLift cần một cửa sổ
terminal riêng chạy ``python -m livelift.ingest.runner --platform ... --source-id
... --session-id <uuid>``. Người bán không kỹ thuật không làm được việc đó, và
tài liệu vận hành ghi thẳng "⚠️ CLI, không có nút bấm — cần một kỹ sư ngồi
cạnh". Mọi phiên tự tạo trên web vì vậy hiện "THIẾU nguồn" ở Bình luận và Người
xem. Đây là rào cản số một giữa "bản demo" và "sản phẩm tự chạy".

Mô hình
-------
Một :class:`IngestManager` cho mỗi ứng dụng (``app.state.ingest``), tối đa một
:class:`IngestJob` đang chạy cho mỗi phiên. Mỗi job là một tác vụ asyncio giám
sát (supervisor) quanh đúng các client nền tảng mà runner CLI dùng, nên hành vi
đọc nền tảng (quota, backoff, phân loại lỗi) chỉ có MỘT bản mã.

Vòng đời::

    dang_khoi_dong ─► dang_thu ◄─► dang_thu_lai
          │              │  ▲
          ▼              ▼  │
     cho_len_song ───────┘  │      (nền tảng báo "chưa phát" ⇒ chờ, không tính lỗi)
                         │
                         ▼
     da_dung · phien_ket_thuc · nguon_ket_thuc · loi      (trạng thái cuối)

* Lỗi TẠM THỜI (mạng, 5xx, yt-dlp bị ngắt) ⇒ ``dang_thu_lai`` với backoff mũ,
  tối đa :data:`MAX_RESTARTS` lần.
* Nền tảng nói buổi live CHƯA bắt đầu ⇒ ``cho_len_song``, dò lại mỗi
  :data:`WAIT_FOR_LIVE_S` giây, không tính vào số lần thử lại. Nhờ vậy người
  vận hành bật bộ thu TRƯỚC giờ phát và nó tự bắt đầu thu khi host lên sóng.
* Lỗi CẤU HÌNH (thiếu khoá, token sai) ⇒ ``loi`` ngay: thử lại không sửa được
  một token hỏng, chỉ đốt quota.
* Phiên LiveLift chuyển sang ``ended``/``cancelled`` ⇒ ``phien_ket_thuc``.

Quyền riêng tư (quy tắc cứng 1)
--------------------------------
:class:`StoreSink` chạy ``scrub()`` TRƯỚC khi dựng bất kỳ đối tượng nào ra khỏi
vòng đọc, rồi đưa văn bản đã lọc vào đúng hàm lưu mà ``POST /comments`` dùng
(hàm đó lọc thêm một lần nữa — lọc là idempotent). Không dòng log hay thông báo
lỗi nào ở đây chứa văn bản bình luận: lỗi chỉ ghi tên lớp ngoại lệ.

Giới hạn nói thẳng
------------------
Job sống trong TIẾN TRÌNH API — cùng quy tắc một-worker như ``autopilot``: chạy
nhiều worker uvicorn thì mỗi worker có manager riêng. Khởi động lại API không
làm mất cấu hình: danh sách job đang chạy được ghi vào tệp trạng thái và
:meth:`IngestManager.resume` tự nối lại cho các phiên chưa đóng.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from livelift.ingest.base import Backoff, RawComment, RawTick
from livelift.ingest.pii import scrub

logger = logging.getLogger("livelift.api.ingest")

NEN_TANG_THU: tuple[str, ...] = ("youtube", "facebook", "shopee")
"""Nền tảng có client thu trực tiếp. TikTok cố ý KHÔNG có: không có API công
khai, và đường không chính thức bị Cloudflare chặn 10/10 lần (đo 10/09/2026)."""

TRANG_THAI_CUOI: frozenset[str] = frozenset({"da_dung", "phien_ket_thuc", "nguon_ket_thuc", "loi"})
TRANG_THAI_PHIEN_DONG: frozenset[str] = frozenset({"ended", "cancelled"})

MAX_RESTARTS = 20
RESTART_BASE_S = 5.0
RESTART_CAP_S = 120.0
WAIT_FOR_LIVE_S = 20.0
WATCH_SESSION_EVERY_S = 5.0

_DAU_HIEU_CHUA_PHAT: tuple[str, ...] = (
    "has no active live chat",  # YouTube Data API: video chưa/không live
    "không ở trạng thái phát trực tiếp",  # yt-dlp: ERR_NOT_LIVE
    "KHÔNG có buổi live nào đang phát",  # Facebook: Page chưa phát
)
_DAU_HIEU_CAU_HINH: tuple[str, ...] = (
    "API key không hợp lệ",
    "access token hết hạn hoặc thiếu quyền",
    "Thiếu danh tính Shopee",
    "Chưa có FACEBOOK_PAGE_ID",
    "Thiếu thư viện yt-dlp",
    "INGEST_YOUTUBE_BACKEND không hợp lệ",
    "unsupported platform",
    "vượt ngưỡng an toàn",
)


def _now() -> datetime:
    return datetime.now(UTC)


def phan_loai_loi(exc: BaseException) -> str:
    """``"chua_phat"`` | ``"cau_hinh"`` | ``"tam_thoi"`` cho một lỗi của client."""
    thong_diep = str(exc)
    if any(d in thong_diep for d in _DAU_HIEU_CHUA_PHAT):
        return "chua_phat"
    if isinstance(exc, (NotImplementedError, ValueError)):
        return "cau_hinh"
    if any(d in thong_diep for d in _DAU_HIEU_CAU_HINH):
        return "cau_hinh"
    return "tam_thoi"


def mo_ta_loi(exc: BaseException) -> str:
    """Câu cho người vận hành. Chỉ RuntimeError/ValueError mang thông điệp của
    chính các client nền tảng (tiếng Việt, về cấu hình — không chứa bình luận);
    mọi loại khác chỉ để lộ tên lớp, phòng một thông điệp lạ lẫn văn bản người xem."""
    if isinstance(exc, (RuntimeError, ValueError)) and str(exc):
        return str(exc)[:400]
    return f"{type(exc).__name__} — lỗi tạm thời khi đọc nền tảng"


# ---------------------------------------------------------------------------
# Sink: ghi thẳng vào kho qua đúng hàm của các route POST
# ---------------------------------------------------------------------------


class StoreSink:
    """:class:`livelift.ingest.base.IngestSink` ghi thẳng vào kho của tiến trình.

    Không đi qua HTTP nên không cần token, không vướng giới hạn tần suất, và
    không có chặng mạng nào để hỏng. Hàm lưu được gọi trong luồng phụ
    (``asyncio.to_thread``) vì kho Postgres chặn; ``Broadcaster.publish`` an toàn
    đa luồng từ 17/09/2026 nên WebSocket vẫn nhận ngay.
    """

    def __init__(self, store: Any, session_id: str) -> None:
        self._store = store
        self._session_id = session_id
        self.comments_seen = 0
        self.comments_posted = 0
        self.comments_skipped = 0
        self.ticks_posted = 0
        self.failures = 0
        self.last_error: str | None = None
        self.last_event_at: datetime | None = None
        self.last_viewers: float | None = None

    async def post_comment(self, comment: RawComment) -> bool:
        from livelift.api.routes.events import _store_comment
        from livelift.api.schemas import CommentIn

        self.comments_seen += 1
        text = scrub(comment.text).text.strip()
        if not text:
            # Sticker/ảnh không kèm chữ: không có gì để lưu, không phải lỗi.
            self.comments_skipped += 1
            return True
        try:
            body = CommentIn(
                text=text[:2000],
                platform=comment.platform,  # type: ignore[arg-type]
                ext_id=comment.ext_id[:128],
                ts_utc=comment.ts_utc,
            )
            await asyncio.to_thread(_store_comment, self._session_id, body, self._store)
        except Exception as exc:  # noqa: BLE001 — sink không bao giờ làm chết vòng đọc
            self.failures += 1
            self.last_error = f"Ghi bình luận thất bại: {type(exc).__name__}"
            return False
        self.comments_posted += 1
        self.last_event_at = _now()
        return True

    async def post_tick(self, tick: RawTick) -> bool:
        from livelift.api.routes.events import _store_tick
        from livelift.api.schemas import TickIn

        try:
            body = TickIn(viewers=max(0.0, float(tick.viewers)), ts_utc=tick.ts_utc)
            await asyncio.to_thread(_store_tick, self._session_id, body, self._store)
        except Exception as exc:  # noqa: BLE001
            self.failures += 1
            self.last_error = f"Ghi số người xem thất bại: {type(exc).__name__}"
            return False
        self.ticks_posted += 1
        self.last_viewers = float(tick.viewers)
        self.last_event_at = _now()
        return True


# ---------------------------------------------------------------------------
# Job + manager
# ---------------------------------------------------------------------------


ClientFactory = Callable[[str], Any]


def client_mac_dinh(platform: str) -> Any:
    """Cùng bộ chọn client với runner CLI (tôn trọng INGEST_YOUTUBE_BACKEND)."""
    from livelift.ingest.runner import _build_client

    return _build_client(platform)


@dataclass
class IngestJob:
    session_id: str
    platform: str
    source_id: str
    state: str = "dang_khoi_dong"
    started_at: datetime = field(default_factory=_now)
    ended_at: datetime | None = None
    restarts: int = 0
    last_error: str | None = None
    tick_error: str | None = None
    resolved_source: str | None = None
    """Id thật đang đọc khi ``source_id`` rỗng (Facebook tự tìm buổi đang phát)."""
    sink: StoreSink | None = None
    client: Any = None
    task: asyncio.Task[None] | None = None

    @property
    def dang_chay(self) -> bool:
        return self.state not in TRANG_THAI_CUOI

    def trang_thai(self) -> dict[str, Any]:
        sink = self.sink
        client_err = getattr(self.client, "last_error", None)
        giay_tu_su_kien: float | None = None
        if sink is not None and sink.last_event_at is not None:
            giay_tu_su_kien = round((_now() - sink.last_event_at).total_seconds(), 1)
        return {
            "session_id": self.session_id,
            "platform": self.platform,
            "source_id": self.source_id,
            "resolved_source": self.resolved_source,
            "state": self.state,
            "running": self.dang_chay,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "restarts": self.restarts,
            "comments_seen": sink.comments_seen if sink else 0,
            "comments_posted": sink.comments_posted if sink else 0,
            "ticks_posted": sink.ticks_posted if sink else 0,
            "last_viewers": sink.last_viewers if sink else None,
            "write_failures": sink.failures if sink else 0,
            "last_event_at": sink.last_event_at if sink else None,
            "seconds_since_last_event": giay_tu_su_kien,
            "last_error": self.last_error or client_err or (sink.last_error if sink else None),
            "tick_error": self.tick_error,
            "api_usage_pct": getattr(self.client, "last_usage_pct", None),
        }


class IngestConflictError(Exception):
    """Phiên đã có một bộ thu đang chạy."""


class IngestManager:
    def __init__(
        self,
        store: Any,
        client_factory: ClientFactory | None = None,
        state_path: str | os.PathLike[str] | None = None,
        *,
        restart_base_s: float = RESTART_BASE_S,
        restart_cap_s: float = RESTART_CAP_S,
        max_restarts: int = MAX_RESTARTS,
        wait_for_live_s: float = WAIT_FOR_LIVE_S,
        watch_every_s: float = WATCH_SESSION_EVERY_S,
    ) -> None:
        self._store = store
        self._client_factory = client_factory or client_mac_dinh
        self._state_path = Path(state_path) if state_path is not None else None
        self._restart_base_s = restart_base_s
        self._restart_cap_s = restart_cap_s
        self._max_restarts = max_restarts
        self._wait_for_live_s = wait_for_live_s
        self._watch_every_s = watch_every_s
        self._jobs: dict[str, IngestJob] = {}

    # -- truy vấn ------------------------------------------------------------
    def get(self, session_id: str) -> IngestJob | None:
        return self._jobs.get(session_id)

    def all(self) -> list[IngestJob]:
        return list(self._jobs.values())

    # -- điều khiển ----------------------------------------------------------
    def start(self, session_id: str, platform: str, source_id: str) -> IngestJob:
        """Bật bộ thu. Phải gọi TRONG event loop đang chạy."""
        if platform not in NEN_TANG_THU:
            raise ValueError(f"unsupported platform: {platform}")
        cu = self._jobs.get(session_id)
        if cu is not None and cu.dang_chay:
            raise IngestConflictError(session_id)
        job = IngestJob(session_id=session_id, platform=platform, source_id=source_id)
        job.sink = StoreSink(self._store, session_id)
        self._jobs[session_id] = job
        job.task = asyncio.create_task(self._supervise(job), name=f"ingest-{session_id}")
        self._persist()
        logger.info("Bật bộ thu: phiên=%s nền tảng=%s nguồn=%s", session_id, platform, source_id)
        return job

    async def stop(self, session_id: str) -> IngestJob | None:
        job = self._jobs.get(session_id)
        if job is None:
            return None
        if job.task is not None and not job.task.done():
            job.task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await job.task
        if job.dang_chay:
            job.state = "da_dung"
            job.ended_at = _now()
        self._persist()
        logger.info("Tắt bộ thu: phiên=%s", session_id)
        return job

    async def shutdown(self) -> None:
        """Tắt API: huỷ mọi job nhưng GIỮ tệp trạng thái để lần khởi động sau nối lại."""
        dang_chay = [j for j in self._jobs.values() if j.task is not None and not j.task.done()]
        for job in dang_chay:
            job.task.cancel()  # type: ignore[union-attr]
        for job in dang_chay:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await job.task  # type: ignore[misc]

    async def resume(self) -> int:
        """Nối lại các job ghi trong tệp trạng thái cho phiên chưa đóng."""
        if self._state_path is None or not self._state_path.is_file():
            return 0
        try:
            muc = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("Tệp trạng thái bộ thu hỏng, bỏ qua: %s", self._state_path)
            return 0
        so = 0
        for m in muc if isinstance(muc, list) else []:
            sid, platform, source = m.get("session_id"), m.get("platform"), m.get("source_id")
            if not (sid and platform in NEN_TANG_THU and source is not None):
                continue
            try:
                phien = await asyncio.to_thread(self._store.get_session, sid)
            except Exception as exc:  # noqa: BLE001 — kho chết lúc khởi động: không nối lại
                logger.warning(
                    "Không nối lại bộ thu phiên %s: kho không trả lời (%s)",
                    sid,
                    type(exc).__name__,
                )
                continue
            if phien is None or phien.get("status") in TRANG_THAI_PHIEN_DONG:
                continue
            with contextlib.suppress(IngestConflictError, ValueError):
                self.start(sid, platform, str(source))
                so += 1
        if so:
            logger.warning("Đã TỰ NỐI LẠI %d bộ thu sau khi API khởi động lại", so)
        return so

    # -- nội bộ --------------------------------------------------------------
    def _persist(self) -> None:
        if self._state_path is None:
            return
        muc = [
            {"session_id": j.session_id, "platform": j.platform, "source_id": j.source_id}
            for j in self._jobs.values()
            if j.dang_chay
        ]
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(muc, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self._state_path)
        except OSError as exc:
            logger.warning("Không ghi được tệp trạng thái bộ thu: %s", type(exc).__name__)

    async def _phien_da_dong(self, session_id: str) -> bool:
        try:
            phien = await asyncio.to_thread(self._store.get_session, session_id)
        except Exception:  # noqa: BLE001 — kho chập chờn không có nghĩa là phiên đã đóng
            return False
        return phien is None or phien.get("status") in TRANG_THAI_PHIEN_DONG

    async def _supervise(self, job: IngestJob) -> None:
        backoff = Backoff(base_s=self._restart_base_s, cap_s=self._restart_cap_s)
        try:
            while True:
                if await self._phien_da_dong(job.session_id):
                    job.state = "phien_ket_thuc"
                    return
                ket_qua = await self._chay_mot_lan(job)
                if ket_qua in ("phien_ket_thuc", "nguon_ket_thuc"):
                    job.state = ket_qua
                    return
                if ket_qua == "cho_len_song":
                    job.state = "cho_len_song"
                    await asyncio.sleep(self._wait_for_live_s)
                    continue
                if ket_qua == "loi_cau_hinh":
                    job.state = "loi"
                    return
                job.restarts += 1
                if job.restarts > self._max_restarts:
                    job.state = "loi"
                    job.last_error = (
                        f"Đã thử lại {self._max_restarts} lần không thành công — bộ thu dừng. "
                        f"Lỗi gần nhất: {job.last_error or 'không rõ'}"
                    )
                    return
                job.state = "dang_thu_lai"
                await asyncio.sleep(backoff.next_delay())
        finally:
            if job.state in TRANG_THAI_CUOI:
                job.ended_at = job.ended_at or _now()
                self._persist()
                logger.info("Bộ thu phiên %s dừng: %s", job.session_id, job.state)

    async def _chay_mot_lan(self, job: IngestJob) -> str:
        try:
            client = self._client_factory(job.platform)
        except Exception as exc:  # noqa: BLE001
            job.last_error = mo_ta_loi(exc)
            return "loi_cau_hinh" if phan_loai_loi(exc) != "tam_thoi" else "loi_tam_thoi"
        job.client = client
        sink = job.sink
        assert sink is not None

        nguon = job.source_id
        if job.platform == "facebook" and not nguon:
            # Tự tìm buổi đang phát trên Page: bật bộ thu trước giờ G, host bấm
            # phát trên điện thoại là LiveLift tự bắt được.
            try:
                nguon = await client.get_active_live_video_id()
            except Exception as exc:  # noqa: BLE001
                job.last_error = mo_ta_loi(exc)
                with contextlib.suppress(Exception):
                    await client.aclose()
                loai = phan_loai_loi(exc)
                if loai == "chua_phat":
                    return "cho_len_song"
                return "loi_cau_hinh" if loai == "cau_hinh" else "loi_tam_thoi"
            job.resolved_source = nguon

        async def binh_luan() -> None:
            async for c in client.iter_comments(nguon):
                if job.state != "dang_thu":
                    job.state = "dang_thu"
                    job.last_error = None
                await sink.post_comment(c)

        async def nguoi_xem() -> None:
            async for t in client.iter_viewers(nguon):
                await sink.post_tick(t)

        async def canh_phien() -> None:
            while not await self._phien_da_dong(job.session_id):
                await asyncio.sleep(self._watch_every_s)

        tac_vu = {
            asyncio.create_task(binh_luan(), name="binh_luan"): "binh_luan",
            asyncio.create_task(nguoi_xem(), name="nguoi_xem"): "nguoi_xem",
            asyncio.create_task(canh_phien(), name="canh_phien"): "canh_phien",
        }
        job.state = "dang_thu"
        try:
            con_lai = set(tac_vu)
            while con_lai:
                xong, con_lai = await asyncio.wait(con_lai, return_when=asyncio.FIRST_COMPLETED)
                for t in xong:
                    ten = tac_vu[t]
                    exc = t.exception()
                    if ten == "canh_phien":
                        if exc is None:
                            return "phien_ket_thuc"
                        continue
                    if exc is not None:
                        loai = phan_loai_loi(exc)
                        if ten == "nguoi_xem" and loai == "tam_thoi":
                            # Người xem là tín hiệu phụ: giữ bình luận chạy tiếp.
                            job.tick_error = mo_ta_loi(exc)
                            continue
                        job.last_error = mo_ta_loi(exc)
                        if loai == "chua_phat":
                            return "cho_len_song"
                        if loai == "cau_hinh":
                            return "loi_cau_hinh"
                        return "loi_tam_thoi"
                    if ten == "binh_luan":
                        return "nguon_ket_thuc"
            return "nguon_ket_thuc"
        finally:
            for t in tac_vu:
                t.cancel()
            for t in tac_vu:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await t
            with contextlib.suppress(Exception):
                await client.aclose()


# ---------------------------------------------------------------------------
# Mức sẵn sàng của từng nền tảng — không bao giờ trả giá trị khoá
# ---------------------------------------------------------------------------


def _co_yt_dlp() -> bool:
    import importlib.util

    return importlib.util.find_spec("yt_dlp") is not None


def muc_san_sang_nen_tang(settings: Any) -> list[dict[str, Any]]:
    """Trả lời "nền tảng nào thu được NGAY BÂY GIỜ, thiếu gì" cho trang web.

    Chỉ trả TÊN biến còn thiếu, không bao giờ trả giá trị khoá.
    """
    ket: list[dict[str, Any]] = []

    backend = (settings.ingest_youtube_backend or "api").strip().lower()
    if backend == "ytdlp":
        ket.append(
            {
                "platform": "youtube",
                "ten": "YouTube Live",
                "ready": _co_yt_dlp(),
                "mode": "du_phong",
                "missing": [] if _co_yt_dlp() else ["yt-dlp (pip install yt-dlp)"],
                "source_hint": "Dán link video đang live (youtube.com/watch?v=… hoặc /live/…)",
                "note": (
                    "Đang dùng đường DỰ PHÒNG yt-dlp: không cần khoá nhưng trái Điều khoản "
                    "YouTube, trễ ~25 giây. Chỉ dùng cho kênh của chính mình; đường chuẩn là "
                    "YOUTUBE_API_KEY với INGEST_YOUTUBE_BACKEND=api."
                ),
            }
        )
    else:
        co_khoa = bool(settings.youtube_api_key)
        ket.append(
            {
                "platform": "youtube",
                "ten": "YouTube Live",
                "ready": co_khoa,
                "mode": "chinh_thuc",
                "missing": [] if co_khoa else ["YOUTUBE_API_KEY"],
                "source_hint": "Dán link video đang live (youtube.com/watch?v=… hoặc /live/…)",
                "note": (
                    "YouTube Data API v3, miễn phí, hạn mức 10.000 đơn vị/ngày — đủ khoảng một "
                    "buổi 90 phút khi thu bình luận và người xem."
                ),
            }
        )

    thieu_fb = [
        ten
        for ten, gia_tri in (
            ("FACEBOOK_PAGE_ACCESS_TOKEN", settings.facebook_page_access_token),
            ("FACEBOOK_PAGE_ID", settings.facebook_page_id),
        )
        if not gia_tri
    ]
    ket.append(
        {
            "platform": "facebook",
            "ten": "Facebook Live (Page của bạn)",
            "ready": not thieu_fb,
            "mode": "chinh_thuc",
            "missing": thieu_fb,
            "source_hint": "Để trống để tự tìm buổi đang phát trên Page, hoặc dán live-video id",
            "note": (
                "Graph API, cần quyền pages_read_engagement VÀ pages_read_user_content "
                "(thiếu quyền thứ hai sẽ đọc được 0 bình luận mà không báo lỗi)."
            ),
        }
    )

    thieu_sp = [
        ten
        for ten, gia_tri in (
            ("SHOPEE_PARTNER_ID", settings.shopee_partner_id),
            ("SHOPEE_PARTNER_KEY", settings.shopee_partner_key),
            ("SHOPEE_SHOP_ID", settings.shopee_shop_id),
            ("SHOPEE_ACCESS_TOKEN", settings.shopee_access_token),
        )
        if not gia_tri
    ]
    ket.append(
        {
            "platform": "shopee",
            "ten": "Shopee Live (shop của bạn)",
            "ready": not thieu_sp,
            "mode": "chinh_thuc",
            "missing": thieu_sp,
            "source_hint": "Dán Shopee Live session_id",
            "note": (
                "Shopee Open Platform v2. access_token chỉ sống 4 giờ. Cần xác minh shop "
                "Việt Nam có được cấp nhóm API livestream hay không trước khi dựa vào."
            ),
        }
    )

    ket.append(
        {
            "platform": "tiktok",
            "ten": "TikTok LIVE",
            "ready": False,
            "mode": "khong_ho_tro",
            "missing": [],
            "source_hint": "",
            "note": (
                "Không có API công khai cho bình luận live. Đường không chính thức bị "
                "Cloudflare chặn 10/10 lần (đo 10/09/2026). Dùng shortlink đo click và ghi "
                "đơn bằng tệp CSV xuất từ TikTok Shop Seller Center."
            ),
        }
    )
    return ket


def chuan_hoa_nguon(platform: str, source: str) -> str:
    """Rút id nguồn từ thứ người dùng dán vào; ``ValueError`` tiếng Việt nếu sai.

    * YouTube: id 11 ký tự hoặc link ``watch?v=``, ``youtu.be/``, ``/live/``…
    * Facebook: chuỗi rỗng = tự tìm buổi đang phát trên Page; hoặc id số.
    * Shopee: session_id số.
    """
    s = (source or "").strip()
    if platform == "youtube":
        from livelift.ingest.youtube_replay import _VIDEO_ID_RE, extract_video_id

        if _VIDEO_ID_RE.match(s):
            return s
        vid = extract_video_id(s)
        if vid is None:
            raise ValueError(
                "Không nhận ra video YouTube. Dán link dạng youtube.com/watch?v=… , "
                "youtu.be/… hoặc youtube.com/live/… (link kênh chưa được hỗ trợ)."
            )
        return vid
    if platform == "facebook":
        if not s:
            return ""
        digits = s.rstrip("/").rsplit("/", 1)[-1]
        if not digits.isdigit():
            raise ValueError(
                "Live-video id của Facebook là một dãy số. Để trống để LiveLift tự tìm "
                "buổi đang phát trên Page."
            )
        return digits
    if platform == "shopee":
        if not s.isdigit():
            raise ValueError("Shopee Live session_id là một dãy số.")
        return s
    raise ValueError(f"Nền tảng {platform!r} chưa có bộ thu trực tiếp.")
