"""Reports: per-session block table and the pooled experiment summary.

Everything returned here is ``source='experiment'`` (E2-04: CIs allowed).
The block outcome is rebuilt from stored ticks/clicks through the same pure
pipeline used in analysis (``features.block_frame``) — one code path from the
live desk to the final report, so the demo numbers and the paper numbers can
never diverge."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
from fastapi import APIRouter

from livelift.analysis.estimators import analyze_outer, diff_in_means, randomization_test
from livelift.analysis.power import (
    Scenario,
    poisson_floor,
    scenario_table,
    within_session_cv,
)
from livelift.analysis.robust import ics_gate
from livelift.api import service
from livelift.api.schemas import (
    BaoCaoOut,
    BaoCaoTongQuan,
    ComplianceStats,
    DenominatorCheck,
    DinhBinhLuan,
    ExperimentSummary,
    KetQuaThiNghiem,
    KhoanhKhacOut,
    NguoiXemTomTat,
    PhanBoYDinh,
    ReactionTomTat,
    SessionReport,
    SignalCoverageOut,
)
from livelift.api.service import StoreDep
from livelift.config import get_settings
from livelift.core.assigner import DesignParams
from livelift.core.features import Event, block_frame, blocks_to_dicts
from livelift.core.moments import DEFAULT_WINDOW, detect_comment_spikes
from livelift.core.quality import derive_compliance
from livelift.core.signals import SignalCoverage
from livelift.core.signals import assess as assess_signals
from livelift.nlp.labels import LABEL_DISPLAY

router = APIRouter()

BURN_IN_S = 60

ICS_DRAWS = 300
"""Redraws for the denominator gate (gói P3).

Fewer than the primary test's 1000. This is a flag with a 0.10 threshold, not a
published p-value, and it is paid for on every call of ``/experiment/summary``;
300 draws resolve the neighborhood of 0.10 well enough to decide whether a
caveat prints, and the final analysis re-runs the gate offline at full depth.
"""

ICS_FROZEN_NOTE = (
    "Tiền đăng ký §7: cổng mẫu số cũng bị khóa cho tới ngày mở — nó kiểm định "
    "trên MỘT đại lượng hậu can thiệp (viewer-giây), nên đọc nó sớm vẫn là nhìn "
    "trộm tác động của can thiệp"
)


def _results_freeze_reason(now: datetime) -> str | None:
    """PREREGISTRATION §7 (no peeking): Vietnamese lock reason, or None.

    While the current UTC date is before ``RESULTS_FREEZE_UNTIL``, every
    inferential field of /experiment/summary is withheld. A malformed date
    fails CLOSED — a typo in the freeze config must never silently unlock the
    effect estimate before the pre-registered date.
    """
    raw = get_settings().results_freeze_until.strip()
    if not raw:
        return None
    try:
        freeze = date.fromisoformat(raw)
    except ValueError:
        return (
            "Tiền đăng ký §7: cấu hình RESULTS_FREEZE_UNTIL không hợp lệ "
            f"('{raw}' — cần dạng YYYY-MM-DD) nên ước lượng hiệu ứng bị khóa "
            "cho đến khi cấu hình được sửa — chỉ hiển thị số liệu vận hành"
        )
    if now.date() < freeze:
        return (
            f"Tiền đăng ký §7: ước lượng hiệu ứng bị khóa đến {freeze.isoformat()} "
            "— chỉ hiển thị số liệu vận hành"
        )
    return None


def _events_from_store(session: dict[str, Any], store) -> list[Event]:
    """Rebuild the normalized event stream from persisted rows (offsets are
    seconds from session start)."""
    start = session.get("start_ts")
    if start is None:
        return []
    session_id = session["session_id"]
    events: list[Event] = []
    for t in store.list_ticks(session_id):
        offset = (t["ts_bucket"] - start).total_seconds()
        events.append(Event("viewer_count", offset, value=float(t["viewers"])))
    for c in store.list_clicks(session_id):
        offset = (c["ts"] - start).total_seconds()
        events.append(
            Event(
                "click",
                offset,
                product_id=c.get("product_id"),
                # Migration 0004: flagged-invalid clicks leave the primary
                # numerator but stay in the row/raw series (flag-don't-drop).
                # Legacy rows without the flag remain valid.
                is_valid=c.get("is_valid") is not False,
            )
        )
    for c in store.list_comments(session_id):
        offset = (c["ts"] - start).total_seconds()
        events.append(Event("comment", offset))
    return events


def _session_frame(session: dict[str, Any], store) -> list[dict[str, Any]]:
    """Block-level analysis rows for one session — ALL scheduled blocks.

    Rows carry ``measurable`` / ``exclude_reason``; the caller filters. The
    full set is returned deliberately: the randomization test needs the whole
    schedule to redraw the design that actually ran, and only then applies the
    same exclusion mask (audit 30/08 + method review 02/09).
    """
    blocks = store.get_blocks(session["session_id"])
    start = session.get("start_ts")
    if not blocks or start is None:
        return []
    schedule = service.rebuild_schedule(session, blocks)
    events = _events_from_store(session, store)
    end = session.get("end_ts")
    live_until_s = (end - start).total_seconds() if end is not None else None
    return blocks_to_dicts(
        block_frame(schedule, events, burn_in_s=BURN_IN_S, live_until_s=live_until_s)
    )


def _compliance(session: dict[str, Any], store) -> ComplianceStats:
    """First-stage compliance for one session.

    Preferred source (gói Q3): the append-only ``assignment_event`` ×
    ``exposure_event`` join via :func:`derive_compliance` — two immutable tables
    nobody can edit into agreement. Only the assignment rows of the design that
    actually ran are used (filtered on ``design_hash``); a session rescheduled
    before broadcast carries an earlier draw's rows too, and counting both would
    inflate the denominator.

    Fallback: the pre-Q3 path over ``intervention_log``, for sessions recorded
    before the event tables existed. Silence would be worse than the old number
    — but the two must not be mixed, so the fallback is all-or-nothing per
    session.

    The switch keys on the ASSIGNMENT rows, not on the exposure rows: a session
    scheduled after gói Q3 whose desk never pinned anything has zero exposure
    rows and genuinely 0% compliance. Falling back there would answer a
    different question ("what does the old log say?") for a session whose new
    trail is complete and simply says nothing happened.

    ``override_count`` / ``n_interventions`` come from ``intervention_log`` in
    both paths: they describe the decision log, not exposure.
    """
    session_id = session["session_id"]
    interventions = store.list_interventions(session_id)
    overrides = sum(1 for i in interventions if i.get("source") == "human")

    d_hash = service.session_design_hash(session)
    assignments = [
        a for a in store.list_assignment_events(session_id) if a.get("design_hash") == d_hash
    ]
    if d_hash is not None and assignments:
        exposures = store.list_exposure_events(session_id)
        view = derive_compliance(assignments, exposures)
        return ComplianceStats(
            on_blocks=view.n_on,
            on_blocks_with_pin=view.n_on_exposed,
            compliance_rate=view.compliance_rate,
            override_count=overrides,
            n_interventions=len(interventions),
        )

    blocks = store.get_blocks(session_id)
    on_ids = {b["block_id"] for b in blocks if b.get("assignment") == "ON"}
    pinned_on = {
        i["block_id"]
        for i in interventions
        if i.get("executed")
        and i.get("source") == "model"
        and i.get("action_type") == "pin"
        and i.get("block_id") in on_ids
    }
    return ComplianceStats(
        on_blocks=len(on_ids),
        on_blocks_with_pin=len(pinned_on),
        compliance_rate=(len(pinned_on) / len(on_ids)) if on_ids else None,
        override_count=overrides,
        n_interventions=len(interventions),
    )


OBSERVATIONAL_LABEL = "phân tích quan sát — không phải thí nghiệm"


def _is_analysis_only(session: dict[str, Any]) -> bool:
    return bool((session.get("design") or {}).get("analysis_only"))


def _denominator_check(
    exposures: np.ndarray,
    z: np.ndarray,
    sids: np.ndarray,
    phases: list[str],
    all_phases: list[str],
    all_session_ids: list[str],
    keep: list[bool],
    design_params: dict[str, DesignParams],
) -> DenominatorCheck:
    """Run the ICS gate over the SAME design the primary test redraws.

    The gate only means anything if its reference distribution is the design
    that actually ran, so it is threaded with the full schedule, the analyzed
    mask and each session's persisted params exactly like ``analyze_outer`` —
    a gate redrawn under the default design would be testing someone else's
    experiment (method review 02/09, review 06/09).
    """

    def redraw_fn(outcome: np.ndarray, arms: np.ndarray) -> tuple[float, np.ndarray]:
        return randomization_test(
            outcome,
            arms,
            sids,
            phases,
            n_draws=ICS_DRAWS,
            seed=2026,
            all_phases=all_phases,
            all_session_ids=np.array(all_session_ids),
            analyzed_mask=np.array(keep, dtype=bool),
            design_params=design_params,
        )

    gate = ics_gate(exposures, z, redraw_fn)
    return DenominatorCheck(
        p_value=None if not np.isfinite(gate.p_value) else float(gate.p_value),
        flagged=gate.flagged,
        n_draws=gate.n_draws,
        estimate=None if not np.isfinite(gate.estimate) else float(gate.estimate),
        note=gate.message,
    )


@router.get("/sessions/{session_id}/report", response_model=SessionReport)
def session_report(session_id: str, store: StoreDep) -> SessionReport:
    session = service.require_session(store, session_id)
    # OBSERVATIONAL GUARD (E2-04 corollary): a replay analysis of someone
    # else's video — or any session without an assignment schedule — had no
    # randomization, so no experiment quantity (ON/OFF diff, CI) may ever be
    # displayed for it. Return an explicitly labeled observational report.
    if _is_analysis_only(session) or not store.get_blocks(session_id):
        return SessionReport(
            session_id=session_id,
            label=OBSERVATIONAL_LABEL,
            n_blocks=0,
            n_on=0,
            n_off=0,
            diff_in_means=None,
            blocks=[],
            compliance=_compliance(session, store),
        )
    # Report only the blocks that carry an outcome; the excluded ones keep
    # their reason in the frame for the QC gate, not for the reader.
    frame = [r for r in _session_frame(session, store) if r.get("measurable", True)]
    ys = np.array([r["y"] for r in frame], dtype=float)
    zs = np.array([r["z"] for r in frame], dtype=int)
    diff = diff_in_means(ys, zs) if len(frame) >= 4 else None
    return SessionReport(
        session_id=session_id,
        n_blocks=len(frame),
        n_on=int(zs.sum()) if len(frame) else 0,
        n_off=int(len(zs) - zs.sum()) if len(frame) else 0,
        diff_in_means=None if diff is None or np.isnan(diff) else float(diff),
        blocks=frame,
        compliance=_compliance(session, store),
    )


@router.get("/experiment/summary", response_model=ExperimentSummary)
def experiment_summary(store: StoreDep) -> ExperimentSummary:
    """Pooled primary analysis over every ENDED session that has a schedule.

    Runs the pre-registered estimator (randomization inference, redraws via the
    production assignment mechanism under each session's persisted design,
    Fisher CI) — the same functions the final notebook calls.

    While ``RESULTS_FREEZE_UNTIL`` is set and not yet reached (PREREGISTRATION
    §7), the inferential fields are withheld and only operational numbers are
    returned."""
    ys: list[float] = []
    zs: list[int] = []
    session_ids: list[str] = []
    phases: list[str] = []
    compliance_rates: list[float] = []

    ended = [
        s for s in store.list_sessions() if s.get("status") == "ended" and not _is_analysis_only(s)
    ]
    # Operational click totals (gói Q1): raw = every logged click, valid = the
    # IAB-valid subset that feeds the primary outcome. Counts, not inference —
    # they are served on every path, freeze included.
    raw_clicks = 0
    valid_clicks = 0
    for session in ended:
        for c in store.list_clicks(session["session_id"]):
            raw_clicks += 1
            if c.get("is_valid") is not False:
                valid_clicks += 1
    # Keep the FULL schedule alongside the analyzed subset: the reference
    # distribution has to be redrawn over the design that actually ran, then
    # masked to the analyzed blocks (method review 02/09).
    all_phases: list[str] = []
    all_session_ids: list[str] = []
    keep: list[bool] = []
    clicks: list[int] = []
    exposures: list[float] = []
    # The redraws must run each session's PERSISTED design (its own p /
    # rerandomization constraint), not the defaults — rebuilt the same way
    # rebuild_schedule does it.
    design_params: dict[str, DesignParams] = {}
    for session in ended:
        design_params[session["session_id"]] = service.rebuild_design_params(session)
        for r in _session_frame(session, store):
            all_phases.append(r["phase"])
            all_session_ids.append(session["session_id"])
            measurable = bool(r.get("measurable", True))
            keep.append(measurable)
            if measurable:
                ys.append(r["y"])
                zs.append(r["z"])
                session_ids.append(session["session_id"])
                phases.append(r["phase"])
                clicks.append(int(r.get("clicks", 0)))
                exposures.append(float(r.get("exposure_viewer_s", 0.0)))
        comp = _compliance(session, store)
        if comp.compliance_rate is not None:
            compliance_rates.append(comp.compliance_rate)

    n_blocks = len(ys)
    n_sessions = len(set(session_ids))
    if n_blocks < 8 or n_sessions < 2:
        return ExperimentSummary(
            n_sessions=n_sessions,
            n_blocks=n_blocks,
            n_on=sum(zs),
            n_off=n_blocks - sum(zs),
            raw_clicks=raw_clicks,
            valid_clicks=valid_clicks,
            message=(
                "Chưa đủ dữ liệu cho phân tích gộp (cần ≥ 2 phiên đã kết thúc và "
                "≥ 8 khối). Kết quả sẽ xuất hiện khi chuỗi thí nghiệm tích lũy thêm."
            ),
        )

    y = np.array(ys)
    z = np.array(zs)
    sids = np.array(session_ids)

    # PREREGISTRATION §7: before the freeze date the effect estimate is not
    # even COMPUTED here — the weekly view is operational numbers only.
    freeze_reason = _results_freeze_reason(service.now_utc())
    res = None
    denominator = DenominatorCheck(note=ICS_FROZEN_NOTE)
    if freeze_reason is None:
        res = analyze_outer(
            y,
            z,
            sids,
            phases,
            n_draws=1000,
            seed=2026,
            all_phases=all_phases,
            all_session_ids=np.array(all_session_ids),
            analyzed_mask=np.array(keep, dtype=bool),
            design_params=design_params,
        )
        denominator = _denominator_check(
            np.array(exposures, dtype=float),
            z,
            sids,
            phases,
            all_phases,
            all_session_ids,
            keep,
            design_params,
        )

    # WITHIN-session CV, not the pooled one: the primary analysis differences
    # out the session effect (redraws per session, session FE, cluster-robust
    # SEs), so pooling raw blocks across sessions would charge the design for
    # between-session variance it never pays (audit 30/08).
    cv_val = within_session_cv(y, sids)
    cv = float(cv_val) if np.isfinite(cv_val) else None

    # How much of that variance is irreducible counting noise? If almost all of
    # it is, no covariate can help and the only lever is design (longer blocks,
    # more viewers). Reporting this stops the team spending weeks on a
    # prognostic model with a measured R² ceiling of zero (method review 02/09).
    cv_floor, reducible = poisson_floor(
        y, np.array(clicks, dtype=float), np.array(exposures, dtype=float), sids
    )

    # Compliance: use the MEASURED value when there is one. A field literally
    # named measured_compliance sitting next to a table that ignored it and
    # used a literal 0.95 was indefensible (audit 30/08). No CUPED R² is
    # estimated anywhere in this path, so none is claimed: assuming R²=0.3
    # would shave 16% off the MDE on the strength of nothing.
    measured_comp = float(np.mean(compliance_rates)) if compliance_rates else None
    comp_auto = measured_comp if measured_comp is not None else 0.95
    comp_partner = min(comp_auto, 0.85)

    power_rows = []
    if cv is not None:
        power_rows = scenario_table(
            [
                Scenario("không đối tác (18 phiên)", 18, 90, 5, compliance=comp_auto),
                Scenario("có đối tác (+10 phiên)", 28, 90, 5, compliance=comp_partner),
            ],
            # Pass the measured value, not a rounded one — the table must show
            # the number that was actually measured.
            cv_grid=(cv,),
        )

    if res is None:
        # Frozen (§7): same shape, estimable=False, every inferential field
        # withheld — the operational numbers (sessions, blocks, CV, MDE,
        # compliance) that §7 explicitly allows are still served.
        return ExperimentSummary(
            n_sessions=n_sessions,
            n_blocks=n_blocks,
            n_on=int(sum(zs)),
            n_off=int(n_blocks - sum(zs)),
            raw_clicks=raw_clicks,
            valid_clicks=valid_clicks,
            estimable=False,
            message=freeze_reason,
            measured_cv=cv,
            cv_poisson_floor=float(cv_floor) if np.isfinite(cv_floor) else None,
            reducible_share=float(reducible) if np.isfinite(reducible) else None,
            measured_compliance=(float(np.mean(compliance_rates)) if compliance_rates else None),
            power_table=power_rows,
            denominator_check=denominator,
        )

    return ExperimentSummary(
        n_sessions=n_sessions,
        n_blocks=res.n_blocks,
        n_on=res.n_on,
        n_off=res.n_off,
        raw_clicks=raw_clicks,
        valid_clicks=valid_clicks,
        estimable=res.estimable,
        message=res.reason,
        # Never publish inference fields for a design that cannot be tested.
        # NOTE: no estimate_ht here — at the outer tier's constant p=0.5 the
        # Hájek/IPW estimate is algebraically identical to `estimate`, and two
        # copies of one number must not pose as two independent estimators
        # (PREREGISTRATION §5b, review 06/09).
        estimate=res.estimate if res.estimable else None,
        ci_low=res.ci_low if res.estimable else None,
        ci_high=res.ci_high if res.estimable else None,
        p_value=res.p_value if res.estimable else None,
        n_draws=res.n_draws if res.estimable else None,
        measured_cv=cv,
        cv_poisson_floor=float(cv_floor) if np.isfinite(cv_floor) else None,
        reducible_share=float(reducible) if np.isfinite(reducible) else None,
        measured_compliance=(float(np.mean(compliance_rates)) if compliance_rates else None),
        power_table=power_rows,
        denominator_check=denominator,
    )


def _signal_coverage(session: dict[str, Any], store) -> SignalCoverage:
    """Coverage matrix for one session — shared by /signals and /bao-cao."""
    session_id = session["session_id"]
    ticks = store.list_ticks(session_id)
    start, end = session.get("start_ts"), session.get("end_ts")
    coverage_share = 0.0
    if ticks and start is not None:
        horizon = ((end or ticks[-1]["ts_bucket"]) - start).total_seconds()
        if horizon > 0:
            covered = len(ticks) * 30.0  # one tick bucket = 30s of telemetry
            coverage_share = max(0.0, min(1.0, covered / horizon))
    # A replay analysis stores one tick per 30 s to carry the comment tempo and
    # leaves viewers at the placeholder 0.0 (a finished VOD does not expose
    # concurrent viewers). Those rows are not viewer telemetry, so they are
    # counted separately — otherwise the matrix claims "nhịp phiên (người xem
    # theo thời gian)" on a session with no viewer number at all.
    n_with_viewers = sum(1 for t in ticks if float(t.get("viewers") or 0.0) > 0.0)
    return assess_signals(
        has_schedule=bool(store.get_blocks(session_id)),
        n_ticks=len(ticks),
        n_ticks_with_viewers=n_with_viewers,
        tick_coverage_share=coverage_share,
        n_comments=len(store.list_comments(session_id)),
        n_clicks=len(store.list_clicks(session_id)),
        n_orders=len(getattr(store, "list_orders", lambda _sid: [])(session_id)),
        n_reactions=len(store.list_reactions(session_id)),
        platform=session.get("platform"),
        analysis_only=_is_analysis_only(session),
    )


@router.get("/sessions/{session_id}/signals", response_model=SignalCoverageOut)
def session_signals(session_id: str, store: StoreDep) -> SignalCoverageOut:
    """Signal coverage matrix: what this session's data can honestly support."""
    session = service.require_session(store, session_id)
    d = _signal_coverage(session, store).to_dict()
    return SignalCoverageOut(session_id=session_id, **d)


# ---------------------------------------------------------------------------
# Báo cáo sau phiên (post-live report)
# ---------------------------------------------------------------------------

OBS_SUFFIX = " — quan sát, chưa kiểm chứng nhân quả"

INTENT_CAVEAT = (
    "LƯU Ý BẮT BUỘC: nhãn ý định do bộ phân loại tự động gán; precision thực tế "
    "phụ thuộc TỶ LỆ NỀN của từng lớp trong phiên (đối chiếu live-fire 19.126 "
    "bình luận thật — docs/benchmarks/live-fire-da-nguon.md). Phân bố này chỉ "
    "mô tả, không dùng để suy diễn nhân quả."
)

#: analyze_outer cần ≥ MIN_BLOCKS_PER_ARM (2) khối MỖI nhánh; dưới 4 khối đo
#: được thì tuyên bố thiếu ngay thay vì gọi estimator với mảng gần rỗng.
MIN_BAO_CAO_BLOCKS = 4

BAO_CAO_FREEZE_NOTE = (
    "Chỉ số vận hành (số khối, số bình luận, khoảnh khắc) vẫn hiển thị; "
    "ước lượng hiệu ứng bị khóa theo tiền đăng ký §7."
)


def _finite(x: Any) -> float | None:
    """None cho NaN/inf/None — không bao giờ serialize một số không tồn tại."""
    if x is None:
        return None
    v = float(x)
    return v if np.isfinite(v) else None


def _signal_detail(cov: SignalCoverage, name: str) -> str:
    return next(s.detail for s in cov.signals if s.name == name)


def _bao_cao_tong_quan(
    session: dict[str, Any], store, cov: SignalCoverage
) -> tuple[BaoCaoTongQuan, dict[str, Any]]:
    """Thẻ số tổng quan + dữ liệu trung gian cho các phần sau của báo cáo.

    Không-bịa-số: mỗi ô hoặc mang giá trị đo được, hoặc là None kèm lý do
    trong ``thieu`` lấy từ chính ma trận tín hiệu — cùng một câu chữ ở mọi nơi.
    """
    session_id = session["session_id"]
    ticks = store.list_ticks(session_id)
    comments = store.list_comments(session_id)
    clicks = store.list_clicks(session_id)
    reactions = store.list_reactions(session_id)
    start, end = session.get("start_ts"), session.get("end_ts")

    thieu: dict[str, str] = {}

    if start is not None and end is not None:
        thoi_luong_s: float | None = (end - start).total_seconds()
    else:
        thoi_luong_s = None
        thieu["thoi_luong"] = "phiên chưa có đủ mốc bắt đầu/kết thúc"

    dinh: DinhBinhLuan | None = None
    rated = [t for t in ticks if float(t.get("comment_rate") or 0.0) > 0.0]
    if rated:
        peak = max(rated, key=lambda t: float(t["comment_rate"]))
        offset = (peak["ts_bucket"] - start).total_seconds() if start is not None else None
        dinh = DinhBinhLuan(
            gia_tri_per_phut=float(peak["comment_rate"]),
            offset_s=offset,
            ts=peak["ts_bucket"],
        )
    else:
        thieu["dinh_binh_luan"] = (
            "không có điểm đo nhịp bình luận nào mang giá trị — chưa xác định được đỉnh"
        )

    viewer_vals = [float(t["viewers"]) for t in ticks if float(t.get("viewers") or 0.0) > 0.0]
    nguoi_xem: NguoiXemTomTat | None = None
    if viewer_vals:
        nguoi_xem = NguoiXemTomTat(
            dinh=max(viewer_vals),
            trung_binh=float(sum(viewer_vals) / len(viewer_vals)),
            n_diem_do=len(viewer_vals),
        )
    else:
        thieu["nguoi_xem"] = _signal_detail(cov, "ticks")

    if clicks:
        luot_nhap: int | None = sum(1 for c in clicks if c.get("is_valid") is not False)
    else:
        luot_nhap = None
        thieu["luot_nhap"] = _signal_detail(cov, "clicks")

    reactions_out: ReactionTomTat | None = None
    if reactions:
        theo_loai: dict[str, int] = {}
        tong_tien: dict[str, float] = {}
        for r in reactions:
            theo_loai[r["kind"]] = theo_loai.get(r["kind"], 0) + 1
            amount = r.get("amount")
            if amount is not None:
                key = r.get("currency") or "khong_ro"
                tong_tien[key] = tong_tien.get(key, 0.0) + float(amount)
        reactions_out = ReactionTomTat(
            tong=len(reactions), theo_loai=theo_loai, tong_tien=tong_tien
        )
    else:
        thieu["reactions"] = _signal_detail(cov, "reactions")

    tong_quan = BaoCaoTongQuan(
        thoi_luong_s=thoi_luong_s,
        tong_binh_luan=len(comments),
        dinh_binh_luan=dinh,
        nguoi_xem=nguoi_xem,
        luot_nhap_hop_le=luot_nhap,
        reactions=reactions_out,
        thieu=thieu,
    )
    return tong_quan, {"ticks": ticks, "comments": comments}


def _bao_cao_khoanh_khac(
    session: dict[str, Any], ticks: list[dict[str, Any]], store
) -> tuple[list[KhoanhKhacOut], str | None]:
    """Spike bình luận/phút trên rolling window (core.moments — thuần, có test).

    Chuỗi quá ngắn → TUYÊN BỐ ngắn qua ghi chú, không hạ ngưỡng để nặn ra
    khoảnh khắc từ nhiễu.
    """
    if len(ticks) <= DEFAULT_WINDOW:
        return [], (
            f"Chuỗi quá ngắn để phát hiện khoảnh khắc: cần hơn {DEFAULT_WINDOW} "
            f"điểm đo 30 giây làm nền, hiện có {len(ticks)} — không suy diễn từ chuỗi ngắn."
        )
    base = session.get("start_ts") or ticks[0]["ts_bucket"]
    buckets = [
        ((t["ts_bucket"] - base).total_seconds(), float(t.get("comment_rate") or 0.0))
        for t in ticks
    ]
    moments = detect_comment_spikes(buckets)
    if not moments:
        return [], "Không có spike bình luận vượt ngưỡng trong phiên — nhịp chat tương đối đều."

    by_offset = {round((t["ts_bucket"] - base).total_seconds()): t for t in ticks}
    out: list[KhoanhKhacOut] = []
    for m in sorted(moments, key=lambda m: m.offset_s):
        tick = by_offset.get(round(m.offset_s))
        pinned_name: str | None = None
        if tick is not None and tick.get("pinned_product_id"):
            product = store.get_product(tick["pinned_product_id"])
            if product is not None:
                pinned_name = product.get("name")
        phut = int(m.offset_s // 60)
        mo_ta = (
            f"Phút {phut}: nhịp bình luận đạt {m.rate:.0f} tin/phút "
            f"(nền 5 phút trước đó: {m.baseline:.0f})"
        )
        if pinned_name:
            mo_ta += f" khi đang ghim '{pinned_name}'"
        mo_ta += OBS_SUFFIX
        out.append(
            KhoanhKhacOut(
                offset_s=m.offset_s,
                ts=base + timedelta(seconds=m.offset_s),
                binh_luan_per_phut=m.rate,
                nen_per_phut=m.baseline,
                ty_le=m.ratio,
                san_pham_dang_ghim=pinned_name,
                mo_ta=mo_ta,
            )
        )
    return out, None


def _bao_cao_ket_qua(session: dict[str, Any], store) -> KetQuaThiNghiem:
    """Phần nhân quả — đúng đường analyze_outer tiền đăng ký, tôn trọng §7.

    Freeze được kiểm TRƯỚC KHI ước lượng được tính: trong thời gian khóa,
    estimator không chạy — không tồn tại con số nào để rò rỉ.
    """
    frame_all = _session_frame(session, store)
    frame = [r for r in frame_all if r.get("measurable", True)]
    zs = [int(r["z"]) for r in frame]
    n_on, n_off = sum(zs), len(zs) - sum(zs)

    freeze_reason = _results_freeze_reason(service.now_utc())
    if freeze_reason is not None:
        return KetQuaThiNghiem(
            khoa=True,
            ly_do_khoa=freeze_reason,
            estimable=False,
            n_blocks=len(frame),
            n_on=n_on,
            n_off=n_off,
            message=BAO_CAO_FREEZE_NOTE,
        )
    if len(frame) < MIN_BAO_CAO_BLOCKS:
        return KetQuaThiNghiem(
            estimable=False,
            n_blocks=len(frame),
            n_on=n_on,
            n_off=n_off,
            message=(
                f"Chưa đủ khối đo được để ước lượng ({len(frame)} khối, cần ≥ "
                f"{MIN_BAO_CAO_BLOCKS}) — tuyên bố thiếu, không trả số."
            ),
        )

    sid = session["session_id"]
    res = analyze_outer(
        np.array([r["y"] for r in frame], dtype=float),
        np.array(zs, dtype=int),
        np.array([sid] * len(frame)),
        [r["phase"] for r in frame],
        n_draws=1000,
        seed=2026,
        all_phases=[r["phase"] for r in frame_all],
        all_session_ids=np.array([sid] * len(frame_all)),
        analyzed_mask=np.array([bool(r.get("measurable", True)) for r in frame_all], dtype=bool),
        design_params={sid: service.rebuild_design_params(session)},
    )
    return KetQuaThiNghiem(
        estimable=res.estimable,
        n_blocks=res.n_blocks,
        n_on=res.n_on,
        n_off=res.n_off,
        estimate=_finite(res.estimate) if res.estimable else None,
        ci_low=_finite(res.ci_low) if res.estimable else None,
        ci_high=_finite(res.ci_high) if res.estimable else None,
        p_value=_finite(res.p_value) if res.estimable else None,
        n_draws=res.n_draws if res.estimable else None,
        message=res.reason,
    )


def _bao_cao_goi_y(
    khoanh_khac: list[KhoanhKhacOut], dem_theo_nhan: dict[str, int], tong_binh_luan: int
) -> list[str]:
    """Gợi ý chiến thuật: CHỈ câu quan sát, mỗi câu dán nhãn tường minh.

    Không câu nào ở dạng nhân quả ("vì ghim X nên Y") — kể cả cho phiên thí
    nghiệm, phần nhân quả duy nhất nằm ở ``ket_qua_thi_nghiem``.
    """
    out: list[str] = []
    for kk in khoanh_khac:
        phut = int(kk.offset_s // 60)
        cau = f"Đỉnh bình luận rơi vào phút {phut} ({kk.binh_luan_per_phut:.0f} tin/phút)"
        if kk.san_pham_dang_ghim:
            cau += f" khi đang ghim '{kk.san_pham_dang_ghim}'"
        cau += "; xem lại lời thoại đoạn này khi soạn kịch bản phiên sau" + OBS_SUFFIX
        out.append(cau)
    dang_chu_y = {k: v for k, v in dem_theo_nhan.items() if k not in ("khac", "khong_ro") and v > 0}
    if dang_chu_y and tong_binh_luan > 0:
        label, count = max(dang_chu_y.items(), key=lambda kv: kv[1])
        # Tên hiển thị tiếng Việt, không lộ khóa snake_case ('chot_don') ra câu
        # hướng người dùng — bắt gặp trên báo cáo buổi Achan 11/09.
        ten_nhan = LABEL_DISPLAY.get(label, label)
        out.append(
            f"Ý định xuất hiện nhiều nhất trong chat là '{ten_nhan}' "
            f"({count}/{tong_binh_luan} bình luận, nhãn tự động)" + OBS_SUFFIX
        )
    return out


NHAN_QUAN_SAT = (
    "báo cáo sau phiên — phiên QUAN SÁT: chỉ số mô tả, KHÔNG có số nhân quả "
    "(không có lịch gán ngẫu nhiên để suy diễn)"
)
NHAN_THI_NGHIEM = (
    "báo cáo sau phiên — phiên thí nghiệm: phần nhân quả chạy đúng đường phân tích tiền đăng ký"
)


@router.get("/sessions/{session_id}/bao-cao", response_model=BaoCaoOut)
def session_bao_cao(session_id: str, store: StoreDep) -> BaoCaoOut:
    """Báo cáo tổng hợp sau phiên: tổng quan, ma trận tín hiệu, khoảnh khắc,
    phân bố ý định (kèm caveat bắt buộc), PII đã che, và — chỉ với phiên có
    lịch gán — kết quả nhân quả qua đường analyze_outer, tôn trọng khóa §7."""
    session = service.require_session(store, session_id)
    observational = _is_analysis_only(session) or not store.get_blocks(session_id)

    cov = _signal_coverage(session, store)
    tong_quan, mid = _bao_cao_tong_quan(session, store, cov)
    khoanh_khac, kk_ghi_chu = _bao_cao_khoanh_khac(session, mid["ticks"], store)

    comments = mid["comments"]
    dem_theo_nhan: dict[str, int] = {}
    pii_da_che: dict[str, int] = {}
    for c in comments:
        label = c.get("intent_label") or "khong_ro"
        dem_theo_nhan[label] = dem_theo_nhan.get(label, 0) + 1
        for kind in c.get("pii_kinds") or []:
            pii_da_che[kind] = pii_da_che.get(kind, 0) + 1

    cov_dict = cov.to_dict()
    return BaoCaoOut(
        session_id=session_id,
        tieu_de=session.get("title"),
        platform=session.get("platform") or "khong_ro",
        loai_phien="quan_sat" if observational else "thi_nghiem",
        nhan=NHAN_QUAN_SAT if observational else NHAN_THI_NGHIEM,
        tong_quan=tong_quan,
        tin_hieu=cov_dict["signals"],
        nang_luc=cov_dict["capabilities"],
        khoanh_khac=khoanh_khac,
        khoanh_khac_ghi_chu=kk_ghi_chu,
        phan_bo_y_dinh=PhanBoYDinh(
            tong=len(comments), dem_theo_nhan=dem_theo_nhan, caveat=INTENT_CAVEAT
        ),
        pii_da_che=pii_da_che,
        ket_qua_thi_nghiem=None if observational else _bao_cao_ket_qua(session, store),
        goi_y_chien_thuat=_bao_cao_goi_y(khoanh_khac, dem_theo_nhan, len(comments)),
    )
