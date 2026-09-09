"""Reports: per-session block table and the pooled experiment summary.

Everything returned here is ``source='experiment'`` (E2-04: CIs allowed).
The block outcome is rebuilt from stored ticks/clicks through the same pure
pipeline used in analysis (``features.block_frame``) — one code path from the
live desk to the final report, so the demo numbers and the paper numbers can
never diverge."""

from __future__ import annotations

from datetime import date, datetime
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
    ComplianceStats,
    DenominatorCheck,
    ExperimentSummary,
    SessionReport,
    SignalCoverageOut,
)
from livelift.api.service import StoreDep
from livelift.config import get_settings
from livelift.core.assigner import DesignParams
from livelift.core.features import Event, block_frame, blocks_to_dicts
from livelift.core.quality import derive_compliance
from livelift.core.signals import assess as assess_signals

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


@router.get("/sessions/{session_id}/signals", response_model=SignalCoverageOut)
def session_signals(session_id: str, store: StoreDep) -> SignalCoverageOut:
    """Signal coverage matrix: what this session's data can honestly support."""
    session = service.require_session(store, session_id)
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
    cov = assess_signals(
        has_schedule=bool(store.get_blocks(session_id)),
        n_ticks=len(ticks),
        n_ticks_with_viewers=n_with_viewers,
        tick_coverage_share=coverage_share,
        n_comments=len(store.list_comments(session_id)),
        n_clicks=len(store.list_clicks(session_id)),
        n_orders=len(getattr(store, "list_orders", lambda _sid: [])(session_id)),
        analysis_only=_is_analysis_only(session),
    )
    d = cov.to_dict()
    return SignalCoverageOut(session_id=session_id, **d)
