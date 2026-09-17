"""Event ingestion: comments (scrub-first, hard rule 1) and ticks.

Timestamps: when the client sends the platform timestamp (``ts_utc``) it is
authoritative for the event — block attribution near a boundary must follow
when the comment happened on-platform, not when the POST arrived (a runner
retry or spool replay can be minutes late). Without ``ts_utc`` the server
clock stamps the row, as before.

Idempotency: (platform, ext_id) is the dedup key — both store backends return
the existing row instead of inserting a duplicate, so a runner restart or a
spool replay is safe. Duplicate deliveries are not re-published to WebSocket
subscribers.

Auth: when the INGEST_TOKEN setting is non-empty, every POST endpoint here
requires ``Authorization: Bearer <token>``. Read endpoints stay open.

Từ 14/09/2026 phép kiểm tra ấy KHÔNG còn nằm trong tệp này: nó là
:func:`livelift.api.auth.require_write_auth`, gắn một lần ở cấp ứng dụng cho
cả 15 đường ghi. Ba đường ở đây khai báo mức :data:`~livelift.api.auth.
MUC_TOKEN` (``@chi_token``) — LUÔN đòi token, không có ngoại lệ "phiên demo":
đây là đường nạp dữ liệu của bộ thu, và một bình luận giả bơm vào phiên thật
là một điểm dữ liệu sai trong bài báo, không phải một trò nghịch vô hại.

Kho chết giữa phiên (sự cố 13/09/2026 — gói D-ĐỘ-BỀN). Khi PostgreSQL biến
mất trong lúc phiên đang phát, mọi lời gọi store ở đây ném lỗi kết nối và
FastAPI trả một ``500 Internal Server Error`` trống rỗng: người vận hành
không biết bình luận vừa rồi đã mất hay chưa, còn bộ thu thì không phân biệt
được "máy chủ hỏng tạm thời" với "payload sai vĩnh viễn". Mọi đường sự kiện
trong module này vì thế đi qua :func:`storage_guard`, biến lỗi kho thành
``503`` kèm thông điệp tiếng Việt nói thẳng: **bản ghi này CHƯA ĐƯỢC LƯU**,
nó đang nằm trong spool của bộ thu, và đây là lệnh nạp bù. 503 (chứ không
phải 4xx) là quan trọng: :class:`livelift.ingest.base.ApiSink` coi 5xx là lỗi
tạm thời và giữ bản ghi lại, còn 4xx-payload thì vứt đi.
"""

from __future__ import annotations

import logging
from bisect import bisect_left
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from livelift.api import service
from livelift.api.auth import chi_token
from livelift.api.schemas import CommentIn, CommentOut, ReactionIn, ReactionOut, TickIn, TickOut
from livelift.api.service import StoreDep
from livelift.ingest.pii import scrub
from livelift.ingest.pii.filter import KIND_PRIORITY
from livelift.nlp.intent import classify_with_confidence

logger = logging.getLogger("livelift.api.events")

router = APIRouter()

TICK_S = 30


# ---------------------------------------------------------------------------
# Kho chết giữa phiên: nhận ra, và NÓI RA
# ---------------------------------------------------------------------------

STORAGE_OUTAGE_STATUS = 503
"""Mã trả về khi kho không phản hồi. Phải là 5xx: bộ thu chỉ spool (giữ lại)
những lỗi nó tin là tạm thời."""

_STORAGE_OUTAGE_CLASS_NAMES = frozenset(
    {
        # DB-API 2.0: psycopg, psycopg_pool, sqlite3 đều đặt tên lớp như nhau.
        # So khớp theo TÊN lớp trên cây kế thừa thay vì import psycopg, vì
        # psycopg là phụ thuộc tùy chọn (extra 'server') — bản cài chỉ chạy
        # memory không được sập vì một import.
        "OperationalError",  # mất kết nối, server đóng, pool timeout
        "InterfaceError",  # connection đã đóng khi đang dùng
        "PoolClosed",  # psycopg_pool: pool đã đóng
        "AdminShutdown",  # postgres bị tắt dưới chân (docker stop)
        "CannotConnectNow",  # postgres đang khởi động lại
        # Ngoại lệ của CHÍNH tầng kho (gói A-HEALTH, sự cố 13/09/2026):
        # ``PostgresStore._connection`` nay DỊCH mọi ``OperationalError`` của
        # driver thành ``StoreUnavailableError`` kèm câu tiếng Việt, nên tên
        # lớp gốc không còn xuất hiện trên cây kế thừa nữa. Thiếu dòng này thì
        # một lần PostgreSQL chết thật sẽ KHÔNG được nhận là "kho chết" và bộ
        # thu mất đường spool — khoá bằng test ở
        # tests/test_health_su_that.py::test_loi_kho_chet_van_duoc_bo_thu_nhan_ra.
        "StoreUnavailableError",
    }
)


def is_storage_outage(exc: BaseException) -> bool:
    """Lỗi này có phải là "kho không phản hồi" không?

    Phân biệt rất có ý nghĩa: kho chết là lỗi TẠM THỜI (bản ghi phải được giữ
    lại và nạp bù), còn một bug trong code là lỗi VĨNH VIỄN (phải nổ ra để có
    người sửa, không được ngụy trang thành 503 rồi để bộ thu gửi lại mãi mãi).
    """
    if isinstance(exc, ConnectionError | TimeoutError):
        return True
    if isinstance(exc, OSError):  # socket bị cắt giữa chừng
        return True
    return any(cls.__name__ in _STORAGE_OUTAGE_CLASS_NAMES for cls in type(exc).__mro__)


def storage_outage_detail(what: str, session_id: str) -> str:
    """Thông điệp tiếng Việt cho người vận hành đang nhìn màn hình lúc 21h."""
    return (
        f"KHO DỮ LIỆU KHÔNG PHẢN HỒI — {what} này CHƯA ĐƯỢC LƯU. Bộ thu đang giữ bản ghi "
        f"trong data/spool/{session_id}.jsonl; sau khi kho sống lại hãy nạp bù bằng: "
        f"python -m livelift.ingest.spool_replay data/spool/{session_id}.jsonl "
        f"(gửi lại an toàn nhờ khóa idempotency). Trong lúc chờ, số liệu trên bàn điều "
        f"khiển là THIẾU — hãy dừng phiên hoặc ghi tay, đừng chạy tiếp trong vô vọng."
    )


@contextmanager
def storage_guard(what: str, session_id: str) -> Iterator[None]:
    """Biến lỗi kho thành 503 + tiếng Việt; mọi lỗi khác vẫn nổ nguyên trạng.

    ``what`` là danh từ đi vào câu thông báo ("Bình luận", "Lượt xem"...).
    """
    try:
        yield
    except HTTPException:
        raise  # 401/404/409 đã có thông điệp riêng — không nuốt
    except Exception as exc:
        if not is_storage_outage(exc):
            raise  # bug thật phải nổ, không được ngụy trang thành "kho chết"
        logger.error(
            "KHO KHÔNG PHẢN HỒI khi ghi/đọc %s của phiên %s (%s) — trả 503, bản ghi CHƯA LƯU",
            what,
            session_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=STORAGE_OUTAGE_STATUS,
            detail=storage_outage_detail(what, session_id),
            headers={"Retry-After": "5", "X-LiveLift-Storage": "down"},
        ) from exc


@chi_token
@router.post("/sessions/{session_id}/comments", response_model=CommentOut)
def post_comment(session_id: str, body: CommentIn, store: StoreDep) -> CommentOut:
    """Store a comment. The raw text is scrubbed BEFORE any persistence or
    logging; only the scrubbed text exists beyond this function's locals.
    (Ingest already scrubs — running it again here is defense in depth and
    is idempotent.)"""
    with storage_guard("Bình luận", session_id):
        return _store_comment(session_id, body, store)


def _store_comment(session_id: str, body: CommentIn, store: StoreDep) -> CommentOut:
    session = service.require_session(store, session_id)
    now = service.now_utc()
    ts = body.ts_utc or now
    result = scrub(body.text)
    intent, intent_confidence = classify_with_confidence(result.text)

    block_id = None
    if session["status"] == "live":
        # Attribute by the EVENT time, not arrival time: a delayed delivery
        # near a block boundary must land in the block it happened in.
        elapsed = service.elapsed_seconds(session, ts)
        block = service.block_at_offset(store.get_blocks(session_id), elapsed)
        if block is not None:
            block_id = block["block_id"]

    row = {
        "comment_id": service.new_id(),
        "session_id": session_id,
        "block_id": block_id,
        "ts": ts,
        "platform": body.platform,
        "ext_id": body.ext_id,
        "text_scrubbed": result.text,
        # Gộp loại PII máy chủ tự thấy với loại bộ thu đã lọc tại nguồn; chỉ
        # nhận tên loại mà bộ lọc thật sự có.
        "pii_kinds": sorted(
            {m.kind for m in result.matches} | {k for k in body.pii_kinds if k in KIND_PRIORITY}
        ),
        "intent_label": intent,
        "intent_confidence": intent_confidence,
        "sentiment": None,
    }
    stored = store.add_comment(session_id, row)
    # The store returns the EXISTING row for a (platform, ext_id) duplicate —
    # answer idempotently but do not broadcast the same comment twice.
    is_duplicate = stored["comment_id"] != row["comment_id"]
    out = CommentOut(
        comment_id=stored["comment_id"],
        session_id=session_id,
        block_id=stored.get("block_id"),
        ts=stored["ts"],
        text=stored["text_scrubbed"],
        pii_kinds=list(stored.get("pii_kinds", [])),
        intent=stored.get("intent_label"),
        intent_confidence=stored.get("intent_confidence"),
    )
    if not is_duplicate:
        store.publish(session_id, {"type": "comment", "data": out.model_dump(mode="json")})
    return out


@router.get("/sessions/{session_id}/comments", response_model=list[CommentOut])
def list_comments(session_id: str, store: StoreDep) -> list[CommentOut]:
    with storage_guard("Danh sách bình luận", session_id):
        service.require_session(store, session_id)
        return [
            CommentOut(
                comment_id=c["comment_id"],
                session_id=session_id,
                block_id=c.get("block_id"),
                ts=c["ts"],
                text=c["text_scrubbed"],
                pii_kinds=list(c.get("pii_kinds", [])),
                intent=c.get("intent_label"),
                intent_confidence=c.get("intent_confidence"),
            )
            for c in store.list_comments(session_id)
        ]


@chi_token
@router.post("/sessions/{session_id}/ticks", response_model=TickOut)
def post_tick(session_id: str, body: TickIn, store: StoreDep) -> TickOut:
    with storage_guard("Lượt xem (tick)", session_id):
        return _store_tick(session_id, body, store)


def _tick_bucket(session: dict, ts):
    """Mốc 30 giây chứa ``ts``, căn theo giờ bắt đầu phiên khi đã phát."""
    start = session.get("start_ts")
    if start is not None:
        offset = (ts - start).total_seconds()
        return start + timedelta(seconds=int(offset // TICK_S) * TICK_S)
    return ts.replace(second=(ts.second // TICK_S) * TICK_S, microsecond=0)


def _valid_clicks_by_bucket(session: dict, clicks: list[dict]) -> dict:
    """Đếm click HỢP LỆ theo mốc 30 giây từ bảng click — nguồn sự thật duy nhất.

    Kiểm toán 17/09/2026: ``click_count`` của tick trước đây luôn ghi bằng 0 với
    phiên thật (chỉ máy sinh demo điền số), vì link đo ``/r/{code}`` ghi vào bảng
    click chứ không vào tick. Ô "Lượt bấm / phút" và biểu đồ nhịp của Bàn trợ
    live vì thế luôn là 0 trong mọi buổi live thật, dù click vẫn được đo đúng.
    """
    counts: dict = {}
    start = session.get("start_ts")
    for c in clicks:
        if c.get("is_valid") is False:
            continue
        ts = c.get("ts")
        if ts is None or (start is not None and ts < start):
            continue
        bucket = _tick_bucket(session, ts)
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def nhip_binh_luan_theo_moc(
    buckets: Iterable[datetime], comments: list[dict[str, Any]], now: datetime
) -> dict[datetime, float]:
    """Bình luận/phút của từng mốc 30 giây, ĐẾM từ bảng bình luận.

    Kiểm toán 17/09/2026: mọi client live (YouTube, Facebook, Shopee, mô phỏng)
    chỉ gửi số người xem trong tick, nên ``comment_rate`` của phiên live luôn là
    giá trị mặc định 0.0. Ô "Bình luận / phút" của Bàn trợ live in số 0 cạnh một
    feed đầy bình luận, biểu đồ nhịp vẽ đường phẳng, và báo cáo kết luận "nhịp
    chat tương đối đều" từ chuỗi toàn 0 — số bịa. Cũng như lượt bấm
    (:func:`_valid_clicks_by_bucket`), nguồn sự thật là bảng sự kiện.

    Cửa sổ đo luôn dài đúng 30 giây và KẾT THÚC ở cuối mốc — hoặc ở ``now`` nếu
    mốc chưa trôi hết (mốc đang chạy dở). Nhờ vậy điểm mới nhất là "30 giây gần
    nhất" thật, không phải nửa mốc bị nhân đôi thành nửa nhịp.
    """
    moc = TICK_S
    thoi_diem = sorted(c["ts"] for c in comments if c.get("ts") is not None)
    ket: dict[datetime, float] = {}
    for b in buckets:
        cuoi = b + timedelta(seconds=moc)
        if b <= now < cuoi:
            cuoi = now
        dau = cuoi - timedelta(seconds=moc)
        so = bisect_left(thoi_diem, cuoi) - bisect_left(thoi_diem, dau)
        ket[b] = so * 60.0 / moc
    return ket


def gan_nhip_binh_luan(
    ticks: list[dict[str, Any]], comments: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    """Bản sao của ``ticks`` với ``comment_rate`` đo từ bảng bình luận.

    Giá trị đã lưu > 0 được GIỮ nguyên: máy sinh demo và đường nhập replay tự
    điền nhịp (và phải cho ra đúng những con số đã công bố); chỉ chỗ 0 mặc định
    của tick live mới được thay bằng số đếm.
    """
    if not ticks:
        return []
    nhip = nhip_binh_luan_theo_moc(
        [t["ts_bucket"] for t in ticks], comments, now or service.now_utc()
    )
    out = []
    for t in ticks:
        da_luu = float(t.get("comment_rate") or 0.0)
        out.append({**t, "comment_rate": da_luu if da_luu > 0 else nhip.get(t["ts_bucket"], 0.0)})
    return out


def _store_tick(session_id: str, body: TickIn, store: StoreDep) -> TickOut:
    session = service.require_session(store, session_id)
    ts = body.ts_utc or service.now_utc()
    # snap to the 30s bucket grid, aligned to session start when live
    bucket = _tick_bucket(session, ts)

    pinned = service.current_pinned_product_id(store.list_interventions(session_id))
    row = {
        "ts_bucket": bucket,
        "viewers": body.viewers,
        "comment_rate": body.comment_rate,
        "like_rate": body.like_rate,
        "click_count": _valid_clicks_by_bucket(session, store.list_clicks(session_id)).get(
            bucket, 0
        ),
        "pinned_product_id": pinned,
    }
    stored = store.add_tick(session_id, row)
    # Nhịp bình luận KHÔNG ghi vào dòng tick (đọc lại lúc trả về, như lượt bấm):
    # bình luận của mốc còn tiếp tục đến sau khi tick đã ghi.
    (co_nhip,) = gan_nhip_binh_luan([dict(stored)], store.list_comments(session_id))
    out = TickOut(session_id=session_id, **{k: co_nhip[k] for k in row})
    store.publish(session_id, {"type": "tick", "data": out.model_dump(mode="json")})
    return out


@router.get("/sessions/{session_id}/ticks", response_model=list[TickOut])
def list_ticks(session_id: str, store: StoreDep) -> list[TickOut]:
    with storage_guard("Danh sách lượt xem", session_id):
        session = service.require_session(store, session_id)
        # Click đến SAU khi tick của mốc đã ghi vẫn phải hiện: đọc lại từ bảng
        # click lúc trả về. max() giữ nguyên số của phiên demo (máy sinh điền
        # sẵn click_count VÀ ghi dòng click) mà không cộng đôi.
        theo_moc = _valid_clicks_by_bucket(session, store.list_clicks(session_id))
        # comment_rate: cùng lý do, đếm từ bảng bình luận (gan_nhip_binh_luan).
        ticks = gan_nhip_binh_luan(store.list_ticks(session_id), store.list_comments(session_id))
        return [
            TickOut(
                **{
                    **t,
                    "session_id": session_id,
                    "click_count": max(
                        int(t.get("click_count") or 0), theo_moc.get(t["ts_bucket"], 0)
                    ),
                }
            )
            for t in ticks
        ]


@chi_token
@router.post("/sessions/{session_id}/reactions", response_model=ReactionOut)
def post_reaction(session_id: str, body: ReactionIn, store: StoreDep) -> ReactionOut:
    """Store one paid/visible audience event (Super Chat, gift, sticker,
    membership, like — migration 0007).

    No author data exists on this path (hard rule 1): the model has no field
    for who sent the money, only the public amount string. Idempotent on
    (platform, ext_id), like comments — the runner may re-deliver freely.
    """
    with storage_guard("Tương tác trả phí", session_id):
        return _store_reaction(session_id, body, store)


def _store_reaction(session_id: str, body: ReactionIn, store: StoreDep) -> ReactionOut:
    service.require_session(store, session_id)
    row = {
        "reaction_id": service.new_id(),
        "session_id": session_id,
        "ts_utc": body.ts_utc or service.now_utc(),
        "kind": body.kind,
        "amount": body.amount,
        "currency": body.currency,
        "platform": body.platform,
        "ext_id": body.ext_id,
    }
    stored = store.add_reaction(session_id, row)
    is_duplicate = stored["reaction_id"] != row["reaction_id"]
    out = ReactionOut(
        reaction_id=stored["reaction_id"],
        session_id=session_id,
        ts_utc=stored["ts_utc"],
        kind=stored["kind"],
        amount=stored.get("amount"),
        currency=stored.get("currency"),
        platform=stored.get("platform"),
        ext_id=stored.get("ext_id"),
    )
    if not is_duplicate:
        store.publish(session_id, {"type": "reaction", "data": out.model_dump(mode="json")})
    return out


@router.get("/sessions/{session_id}/reactions", response_model=list[ReactionOut])
def list_reactions(session_id: str, store: StoreDep) -> list[ReactionOut]:
    with storage_guard("Danh sách tương tác trả phí", session_id):
        service.require_session(store, session_id)
        return [
            ReactionOut(
                reaction_id=r["reaction_id"],
                session_id=session_id,
                ts_utc=r["ts_utc"],
                kind=r["kind"],
                amount=r.get("amount"),
                currency=r.get("currency"),
                platform=r.get("platform"),
                ext_id=r.get("ext_id"),
            )
            for r in store.list_reactions(session_id)
        ]
