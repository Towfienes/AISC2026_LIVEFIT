"""Session lifecycle: create → schedule (pre-live, hard rule 4) → start → end,
plus role-separated state (operator vs blinded host — rule L6)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request

from livelift.api import autopilot, service
from livelift.api.auth import cho_phep_demo, ghi_khong_token
from livelift.api.cards import build_candidates, build_cards, pin_cards_blocked_reason
from livelift.api.schemas import (
    AutopilotState,
    BlockOut,
    HostState,
    OperatorBlockState,
    OperatorState,
    PinnedProduct,
    ProductIn,
    ProductOut,
    ScheduleOut,
    ScheduleRequest,
    SessionCreate,
    SessionDetail,
    SessionOut,
    ShortlinkIn,
    ShortlinkOut,
)
from livelift.api.service import StoreDep
from livelift.api.store import ShortlinkCodeTakenError, Store
from livelift.core.assigner import (
    DesignParams,
    RerandomizationExhaustedError,
    ScheduleInfeasibleError,
)

router = APIRouter()


# -- products ---------------------------------------------------------------


@cho_phep_demo
@router.post("/products", response_model=ProductOut)
def create_product(body: ProductIn, store: StoreDep) -> ProductOut:
    row = body.model_dump()
    row["created_at"] = service.now_utc()
    return ProductOut(**store.create_product(row))


@router.get("/products", response_model=list[ProductOut])
def list_products(store: StoreDep) -> list[ProductOut]:
    return [ProductOut(**p) for p in store.list_products()]


# -- shortlinks -------------------------------------------------------------


@cho_phep_demo
@router.post("/shortlinks", response_model=ShortlinkOut)
def create_shortlink(body: ShortlinkIn, store: StoreDep) -> ShortlinkOut:
    if store.get_product(body.product_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    row = body.model_dump()
    row["created_at"] = service.now_utc()
    # Random 8-char code; retry on the (astronomically unlikely) collision so a
    # duplicate never silently overwrites an existing click-attribution link.
    for _ in range(5):
        row["code"] = secrets.token_urlsafe(6)[:8]
        try:
            return ShortlinkOut(**store.create_shortlink(row))
        except ShortlinkCodeTakenError:
            continue
    raise HTTPException(status_code=409, detail="Không sinh được mã liên kết, thử lại")


# -- sessions ---------------------------------------------------------------

GIO_VN = timezone(timedelta(hours=7))
"""Giờ Việt Nam cho tên phiên mặc định. Múi cố định +7 (Việt Nam không đổi giờ
mùa hè) — cùng quy ước với ``routes/orders.py``, và không phụ thuộc gói
``tzdata`` mà ảnh Docker gọn có thể không có."""

TEN_NEN_TANG: dict[str, str] = {
    "youtube": "YouTube",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "shopee": "Shopee",
    "replay": "Phát lại",
    "sim": "Mô phỏng",
}
"""Tên nền tảng viết đẹp cho người bán — cùng cách viết với bảng ``TEN_NEN_TANG``
của wizard ``web/src/app/chay-phien/page.tsx`` để tên do máy chủ đặt và tên do
trang web đặt trông như một. Nền tảng lạ (chưa có trong bảng) giữ nguyên mã
thay vì bị đoán tên."""


def ten_phien_mac_dinh(platform: str, planned_duration_min: int, created_at: datetime) -> str:
    """Tên dễ đọc cho phiên tạo KHÔNG có tiêu đề (kiểm toán 17/09/2026).

    ``"Live 17/09 07:38 · YouTube · 30 phút"`` — giờ Việt Nam lúc tạo. Trước
    đây phiên không tên lưu ``title=None`` và mọi ô chọn phiên, báo cáo, bàn
    trợ live chỉ còn in UUID thô: người bán không nhận ra buổi nào là buổi nào.

    Cùng khuôn với ``tenPhienMacDinh`` của wizard web (regex ``laTenMacDinh``
    nhận ra nó). Tên luôn bắt đầu bằng ``"Live "`` nên KHÔNG BAO GIỜ khớp dấu
    vết phiên mô phỏng của migration 0009 (``title LIKE 'Phiên mô phỏng seed=%'``)
    hay tiền tố ``"Demo vàng · "`` của bộ demo — tên mặc định không được làm
    một phiên thật trông như dữ liệu mẫu.
    """
    local = created_at.astimezone(GIO_VN)
    nen_tang = TEN_NEN_TANG.get(platform, platform)
    return f"Live {local:%d/%m %H:%M} · {nen_tang} · {planned_duration_min} phút"


@cho_phep_demo
@router.post("/sessions", response_model=SessionOut)
def create_session(body: SessionCreate, store: StoreDep, request: Request) -> SessionOut:
    """Create a session. ``dry_run`` is declared HERE or never (§8.2).

    ``is_demo`` KHÔNG BAO GIỜ do client đặt — ``SessionCreate`` không có
    trường ấy và ``store._SESSION_WRITE_ONCE`` khoá nó sau khi tạo, nên không
    ai gắn nhãn "mẫu" cho một phiên thật (hay ngược lại) sau khi đã nhìn số.
    **Máy chủ** quyết, và từ 14/09/2026 nó quyết theo đúng một câu hỏi: yêu
    cầu này có chứng minh được mình là người vận hành không?

    * có token (hoặc chạy cục bộ, chưa đặt ``INGEST_TOKEN``) ⇒ ``is_demo=False``
      — hành vi cũ, không đổi một ly: đây là dữ liệu thật;
    * không token, đi qua được nhờ chế độ trưng bày công khai ⇒
      ``is_demo=True``. Đó là sự thật chứ không phải một nhãn cho tiện: không
      buổi phát nào diễn ra và người tạo là một khách vãng lai. Nhờ vậy giám
      khảo chạy trọn wizard trên phiên của chính mình, còn dữ liệu ấy không
      bao giờ lọt vào kết quả khoa học thật (mọi đường gộp đã tự loại is_demo).

    Không gửi ``title`` (hoặc gửi chuỗi trắng) ⇒ máy chủ đặt tên mặc định dễ
    đọc bằng :func:`ten_phien_mac_dinh` thay vì lưu trống.
    """
    row = body.model_dump()
    created_at = service.now_utc()
    row.update(
        session_id=service.new_id(),
        status="planned",
        start_ts=None,
        end_ts=None,
        design=None,
        created_at=created_at,
        is_demo=ghi_khong_token(request),
    )
    if not (row.get("title") or "").strip():
        row["title"] = ten_phien_mac_dinh(
            row["platform"], int(row["planned_duration_min"]), created_at
        )
    return SessionOut(**store.create_session(row))


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(store: StoreDep, env: Literal["real", "demo"] | None = None) -> list[SessionOut]:
    """List sessions. Every row carries ``is_demo`` so the UI can label it.

    ``env`` filters by data source (UX spec B-3/L-B): ``real`` — real sessions
    only, ``demo`` — sample sessions only. Default (no param) returns both,
    each row LABELED — kept for operational tools and backward compatibility;
    result AGGREGATION never happens here, and the pooled endpoints enforce
    their own is_demo gate regardless of what this listing shows.
    """
    rows = store.list_sessions()
    if env is not None:
        want_demo = env == "demo"
        rows = [s for s in rows if bool(s.get("is_demo")) == want_demo]
    return [SessionOut(**s) for s in rows]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, store: StoreDep) -> SessionDetail:
    return SessionDetail(**service.require_session(store, session_id))


@cho_phep_demo
@router.post("/sessions/{session_id}/schedule", response_model=ScheduleOut)
def create_schedule(session_id: str, body: ScheduleRequest, store: StoreDep) -> ScheduleOut:
    """Generate + persist the switchback schedule. Only before broadcast:
    regenerating is allowed while planned/scheduled, never once live (the
    assignment must never be drawn during a session — plan §6.1)."""
    session = service.require_session(store, session_id)
    if session["status"] not in ("planned", "scheduled"):
        raise HTTPException(
            status_code=409,
            detail=(
                "Lịch gán chỉ được sinh TRƯỚC khi phát sóng — phiên này đang ở trạng thái "
                f"{_STATUS_VI.get(session['status'], session['status'])}."
            ),
        )
    params = DesignParams(
        block_min=body.block_min, washout_min=body.washout_min, jitter_s=body.jitter_s
    )
    seed = body.seed if body.seed is not None else secrets.randbits(63)
    try:
        updated, blocks = service.schedule_session(store, session, params, seed)
    except (ScheduleInfeasibleError, RerandomizationExhaustedError) as exc:
        # A configuration the operator can fix is a CLIENT answer. Before
        # 12/09 both paths escaped as an empty HTTP 500 — the 500 that blocked
        # "phiên 50 phút, khối 10 phút" on every seed (incident 12/09).
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    design = updated["design"]
    realized = int(design.get("realized_min_per_arm_per_phase", 0))
    realized_trans = int(design.get("realized_transition_pairs", 0))
    n_meas = len([b for b in blocks if not b.get("is_washout")])
    warnings: list[str] = []
    if realized < params.min_per_arm_per_phase:
        warnings.append(
            f"Phiên {session['planned_duration_min']} phút chỉ cho {n_meas} khối, nên mỗi "
            f"giai đoạn chỉ đảm bảo được {realized} khối/nhánh (thiết kế yêu cầu "
            f"{params.min_per_arm_per_phase}). Kết quả sẽ kém tin cậy hơn — cân nhắc "
            f"phiên dài hơn (từ 90 phút) hoặc khối ngắn hơn."
        )
    if realized_trans < params.min_transition_pairs:
        # Name a block length that actually fits the requested duration instead
        # of only "phiên dài hơn" — a 50-minute session cannot become 90.
        # 12 measurement blocks is the shortest chain that carries the full
        # 3-pair requirement, so duration // 12 is the concrete alternative.
        suggested = max(1, int(session["planned_duration_min"]) // 12)
        alternative = (
            f" Với phiên {session['planned_duration_min']} phút, khối {suggested} phút cho "
            f"chuỗi dài hơn và giữ được ràng buộc."
            if suggested < params.block_min
            else ""
        )
        warnings.append(
            f"Chuỗi {n_meas} khối chỉ ràng buộc được {realized_trans} cặp khối liền kề "
            f"cùng nhánh mỗi loại (thiết kế yêu cầu ≥ {params.min_transition_pairs} cặp "
            f"(BẬT,BẬT) và (TẮT,TẮT)). Các ước lượng nhạy carryover (τ̂ cặp liền kề, CRT) "
            f"sẽ kém tin cậy — cân nhắc phiên dài hơn (từ 90 phút).{alternative}"
        )
    return ScheduleOut(
        session_id=session_id,
        status=updated["status"],
        seed=design["seed"],
        n_redraws=design["n_redraws"],
        n_on=design["n_on"],
        n_off=design["n_off"],
        blocks=[BlockOut(**b) for b in blocks],
        design_hash=design["design_hash"],
        realized_min_per_arm_per_phase=realized,
        realized_transition_pairs=realized_trans,
        warning=" ".join(warnings) if warnings else None,
    )


@router.get("/sessions/{session_id}/schedule", response_model=list[BlockOut])
def get_schedule(session_id: str, store: StoreDep) -> list[BlockOut]:
    service.require_session(store, session_id)
    return [BlockOut(**b) for b in store.get_blocks(session_id)]


@cho_phep_demo
@router.post("/sessions/{session_id}/start", response_model=SessionOut)
def start_session(session_id: str, store: StoreDep) -> SessionOut:
    session = service.require_session(store, session_id)
    if session["status"] == "live":
        raise HTTPException(status_code=409, detail="Phiên đã đang phát")
    if session["status"] in ("ended", "cancelled"):
        # Terminal both ways: a closed session must never re-open and start a
        # second broadcast under the same id — its blocks, clicks and report
        # all key on one start_ts.
        raise HTTPException(
            status_code=409,
            detail=(
                f"Phiên {_STATUS_VI[session['status']]} — không phát lại được. "
                "Tạo phiên mới bằng POST /sessions."
            ),
        )
    try:
        updated = service.start_session(store, session, service.now_utc())
    except service.ScheduleMissingError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "Chưa có lịch gán khối — phiên không được phép phát sóng khi chưa sinh "
                "và lưu lịch gán (quy tắc bất biến, kế hoạch §6.1). "
                "Gọi POST /sessions/{id}/schedule trước."
            ),
        ) from exc
    store.publish(session_id, {"type": "state", "data": {"status": "live"}})
    return SessionOut(**updated)


@cho_phep_demo
@router.post("/sessions/{session_id}/end", response_model=SessionOut)
def end_session(session_id: str, store: StoreDep) -> SessionOut:
    """Close the session.

    A session that IS broadcasting ends as ``ended``. A session that never
    broadcast is closed as ``cancelled`` instead — same button, truthful
    record. Before 12/09 this route simply refused (409 "Phiên không ở trạng
    thái đang phát") and an observation session typed in by hand had NO way to
    close: it sat at ``planned`` forever, and the only workaround was to draw a
    randomization schedule and go live — making the operator stage an
    experiment they never intended to run, just to close a row
    (``docs/benchmarks/kiem-chung-van-hanh.md`` §3.3).
    """
    session = service.require_session(store, session_id)
    status = session["status"]
    if status in ("planned", "scheduled"):
        return _cancel(store, session)
    if status != "live":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Phiên đã ở trạng thái cuối ({_STATUS_VI.get(status, status)}) — "
                "không có buổi phát nào đang chạy để kết thúc."
            ),
        )
    updated = store.update_session(session_id, {"status": "ended", "end_ts": service.now_utc()})
    store.publish(session_id, {"type": "state", "data": {"status": "ended"}})
    return SessionOut(**updated)


@cho_phep_demo
@router.post("/sessions/{session_id}/cancel", response_model=SessionOut)
def cancel_session(session_id: str, store: StoreDep) -> SessionOut:
    """Close a session that never went on air, explicitly.

    Only from ``planned``/``scheduled``: a broadcast that already happened
    cannot be un-happened, so a live session must be ended (and a session
    already ended stays ended). Cancelling is idempotent.

    Scientific meaning, fixed here and in PREREGISTRATION §8.2: a cancelled
    session NEVER enters the pooled result. It carries no ``start_ts``, so it
    has no measurement blocks at all — the exclusion is structural, not a
    filter someone has to remember to apply.
    """
    session = service.require_session(store, session_id)
    status = session["status"]
    if status == "cancelled":
        return SessionOut(**session)  # idempotent: closing a closed thing is done
    if status not in ("planned", "scheduled"):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Phiên {_STATUS_VI.get(status, status)} — chỉ huỷ được phiên CHƯA phát "
                "sóng. Phiên đang phát thì gọi POST /sessions/{id}/end để kết thúc; "
                "phiên đã kết thúc thì giữ nguyên (buổi phát đã diễn ra là một sự thật, "
                "không xoá được bằng một nút bấm)."
            ),
        )
    return _cancel(store, session)


_STATUS_VI: dict[str, str] = {
    "planned": "mới lập, chưa có lịch gán",
    "scheduled": "đã có lịch gán, chưa phát sóng",
    "live": "đang phát",
    "ended": "đã kết thúc",
    "cancelled": "đã huỷ",
}


def _cancel(store: Store, session: dict) -> SessionOut:
    """Mark a never-aired session closed. ``start_ts`` stays None, always."""
    session_id = session["session_id"]
    updated = store.update_session(
        session_id,
        # end_ts records WHEN it was closed; start_ts stays None because no
        # broadcast ever started (migration 0008 enforces that pairing).
        {"status": "cancelled", "end_ts": service.now_utc()},
    )
    store.publish(session_id, {"type": "state", "data": {"status": "cancelled"}})
    return SessionOut(**updated)


# -- state (operator vs host — DISTINCT response models, rule L6) -----------


@router.get("/sessions/{session_id}/state", response_model=OperatorState | HostState)
def get_state(
    session_id: str, store: StoreDep, role: Literal["operator", "host"] = "operator"
) -> OperatorState | HostState:
    session = service.require_session(store, session_id)
    now = service.now_utc()
    elapsed = service.elapsed_seconds(session, now)
    interventions = store.list_interventions(session_id)
    pinned_id = service.current_pinned_product_id(interventions)
    pinned = store.get_product(pinned_id) if pinned_id else None

    if role == "host":
        # BLINDING (L6): HostState structurally cannot carry block info.
        return HostState(
            pinned_product=pinned["name"] if pinned else None,
            price=float(pinned["price"]) if pinned else None,
            stock=int(pinned["stock"]) if pinned else None,
            elapsed_s=elapsed,
        )

    blocks = store.get_blocks(session_id)
    current = service.block_at_offset(blocks, elapsed) if session["status"] == "live" else None
    block_state = None
    if current is not None:
        block_state = OperatorBlockState(
            index=current["block_index"],
            phase=current["phase"],
            assignment=current["assignment"],
            is_washout=bool(current["is_washout"]),
            seconds_remaining=max(0.0, current["end_offset_s"] - elapsed),
        )
    # Cards are an invitation to act, so they only exist where the action can
    # succeed. A finished replay analysis used to come back with three cards
    # offering to pin unrelated demo products (incident 12/09) — the desk
    # inviting a click that /actions/execute would refuse.
    cards_note = pin_cards_blocked_reason(session["status"], service.is_analysis_only(session))
    cards = []
    if cards_note is None:
        recent_clicks: dict[str, int] = {}
        for c in store.list_clicks(session_id):
            pid = c.get("product_id")
            if pid:
                recent_clicks[pid] = recent_clicks.get(pid, 0) + 1
        products = store.list_products()
        candidates = build_candidates(products, recent_clicks, store.list_ticks(session_id))
        cards = build_cards(candidates, {p["product_id"]: p for p in products})
    return OperatorState(
        session_id=session_id,
        status=session["status"],
        mode=session["mode"],
        elapsed_s=elapsed,
        current_block=block_state,
        pinned_product=(
            PinnedProduct(
                product_id=pinned["product_id"],
                name=pinned["name"],
                price=float(pinned["price"]),
                stock=int(pinned["stock"]),
            )
            if pinned
            else None
        ),
        cards=cards,
        cards_note=cards_note,
        design_hash=service.session_design_hash(session),
        autopilot=_autopilot_state(store, session, blocks, elapsed),
        # Nhãn DEMO đi cùng state để bàn điều khiển không bao giờ vẽ số mô
        # phỏng như số thật. HostState cố ý KHÔNG mang cờ này (L6: 4 trường).
        is_demo=bool(session.get("is_demo")),
    )


def _autopilot_state(
    store: Store, session: dict, blocks: list[dict], elapsed: float
) -> AutopilotState | None:
    """Executor status + silence alarm for auto sessions (operator view only).

    Suggest-mode sessions get ``None``: nothing is supposed to run for them,
    and an "enabled/0 actions" panel there would be noise. For auto sessions
    this is the only place the desk can learn that the treatment arm is
    getting no treatment — the failure that stayed silent until 12/09.
    """
    if session.get("mode") != "auto":
        return None
    exposures = store.list_exposure_events(session["session_id"])
    view = autopilot.view(session, blocks, exposures, elapsed)
    return AutopilotState(
        enabled=view.enabled,
        last_run_ts=view.last_run_ts,
        actions_taken=view.actions_taken,
        on_blocks_total=view.on_blocks_total,
        on_blocks_done=view.on_blocks_done,
        missed_on_blocks=list(view.missed_on_blocks),
        last_error=view.last_error,
        alarm=view.alarm,
    )
