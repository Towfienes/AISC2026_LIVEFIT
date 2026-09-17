"""Điều khiển bộ thu bình luận từ trình duyệt (kiểm toán 17/09/2026).

* ``GET  /platforms``                  — nền tảng nào thu được ngay, thiếu khoá gì
* ``GET  /sessions/{id}/ingest``       — trạng thái bộ thu của phiên
* ``POST /sessions/{id}/ingest``       — bật bộ thu (nền tảng + link/id nguồn)
* ``POST /sessions/{id}/ingest/stop``  — tắt bộ thu

Bật/tắt là đường TỐN TÀI NGUYÊN (mở kết nối tới nền tảng, đốt quota của khoá
thật) nên đòi token ghi như ``/replays/youtube`` — bản trưng bày công khai không
cho khách vãng lai bật. Chế độ phát triển cục bộ (INGEST_TOKEN rỗng) vẫn mở.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from livelift.api import service
from livelift.api.auth import chi_token
from livelift.api.ingest_jobs import (
    NEN_TANG_THU,
    IngestConflictError,
    IngestManager,
    chuan_hoa_nguon,
    muc_san_sang_nen_tang,
)
from livelift.api.service import StoreDep
from livelift.config import get_settings

router = APIRouter()


class PlatformReadiness(BaseModel):
    platform: str
    ten: str
    ready: bool
    mode: Literal["chinh_thuc", "du_phong", "khong_ho_tro"]
    missing: list[str] = Field(default_factory=list)
    source_hint: str = ""
    note: str = ""


class IngestStartIn(BaseModel):
    platform: Literal["youtube", "facebook", "shopee"] | None = None
    """Bỏ trống = dùng nền tảng của phiên (nếu nền tảng đó có bộ thu)."""
    source: str = Field(default="", max_length=500)
    """Link hoặc id nguồn. Facebook: bỏ trống để tự tìm buổi đang phát trên Page."""


class IngestStatus(BaseModel):
    session_id: str
    state: str
    running: bool
    platform: str | None = None
    source_id: str | None = None
    resolved_source: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    restarts: int = 0
    comments_seen: int = 0
    comments_posted: int = 0
    ticks_posted: int = 0
    last_viewers: float | None = None
    write_failures: int = 0
    last_event_at: datetime | None = None
    seconds_since_last_event: float | None = None
    last_error: str | None = None
    tick_error: str | None = None
    api_usage_pct: float | None = None


def _manager(request: Request) -> IngestManager:
    manager = getattr(request.app.state, "ingest", None)
    if manager is None:  # pragma: no cover — chỉ xảy ra nếu lifespan chưa chạy
        raise HTTPException(status_code=503, detail="Bộ thu chưa khởi tạo — API đang khởi động")
    return manager


def _chua_bat(session_id: str) -> IngestStatus:
    return IngestStatus(session_id=session_id, state="chua_bat", running=False)


@router.get("/platforms", response_model=list[PlatformReadiness])
def platforms() -> list[dict[str, Any]]:
    return muc_san_sang_nen_tang(get_settings())


@router.get("/sessions/{session_id}/ingest", response_model=IngestStatus)
def ingest_status(session_id: str, request: Request, store: StoreDep) -> IngestStatus:
    service.require_session(store, session_id)
    job = _manager(request).get(session_id)
    return IngestStatus(**job.trang_thai()) if job else _chua_bat(session_id)


@chi_token
@router.post("/sessions/{session_id}/ingest", response_model=IngestStatus, status_code=202)
async def ingest_start(
    session_id: str, body: IngestStartIn, request: Request, store: StoreDep
) -> IngestStatus:
    session = service.require_session(store, session_id)
    if session.get("status") in ("ended", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail="Phiên đã đóng — không bật bộ thu cho phiên đã kết thúc. Tạo phiên mới.",
        )
    platform = body.platform or session.get("platform")
    if platform not in NEN_TANG_THU:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Nền tảng {platform!r} chưa có bộ thu trực tiếp. Chọn youtube, facebook "
                "hoặc shopee; TikTok không có API công khai cho bình luận live."
            ),
        )
    san_sang = {p["platform"]: p for p in muc_san_sang_nen_tang(get_settings())}[platform]
    if not san_sang["ready"]:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{san_sang['ten']} chưa sẵn sàng: thiếu {', '.join(san_sang['missing'])}. "
                "Điền vào tệp .env rồi khởi động lại API."
            ),
        )
    try:
        nguon = chuan_hoa_nguon(platform, body.source)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        job = _manager(request).start(session_id, platform, nguon)
    except IngestConflictError as exc:
        raise HTTPException(
            status_code=409, detail="Phiên này đã có bộ thu đang chạy — tắt nó trước khi bật lại."
        ) from exc
    return IngestStatus(**job.trang_thai())


@chi_token
@router.post("/sessions/{session_id}/ingest/stop", response_model=IngestStatus)
async def ingest_stop(session_id: str, request: Request, store: StoreDep) -> IngestStatus:
    service.require_session(store, session_id)
    job = await _manager(request).stop(session_id)
    return IngestStatus(**job.trang_thai()) if job else _chua_bat(session_id)
