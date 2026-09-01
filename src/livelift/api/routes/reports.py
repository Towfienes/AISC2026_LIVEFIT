"""Reports: per-session block table and the pooled experiment summary.

Everything returned here is ``source='experiment'`` (E2-04: CIs allowed).
The block outcome is rebuilt from stored ticks/clicks through the same pure
pipeline used in analysis (``features.block_frame``) — one code path from the
live desk to the final report, so the demo numbers and the paper numbers can
never diverge."""

from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter

from livelift.analysis.estimators import analyze_outer, diff_in_means
from livelift.analysis.power import Scenario, scenario_table, within_session_cv
from livelift.api import service
from livelift.api.schemas import ComplianceStats, ExperimentSummary, SessionReport
from livelift.api.service import StoreDep
from livelift.core.features import Event, block_frame, blocks_to_dicts

router = APIRouter()

BURN_IN_S = 60


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
        events.append(Event("click", offset, product_id=c.get("product_id")))
    for c in store.list_comments(session_id):
        offset = (c["ts"] - start).total_seconds()
        events.append(Event("comment", offset))
    return events


def _session_frame(session: dict[str, Any], store) -> list[dict[str, Any]]:
    """Block-level analysis rows for one session.

    Only blocks that actually aired AND carry enough exposure are returned:
    a session that ends early keeps its planned blocks, and entering those as
    y = 0.0 attenuated the pooled estimate by ~38% (audit 30/08).
    """
    blocks = store.get_blocks(session["session_id"])
    start = session.get("start_ts")
    if not blocks or start is None:
        return []
    schedule = service.rebuild_schedule(session, blocks)
    events = _events_from_store(session, store)
    end = session.get("end_ts")
    live_until_s = (end - start).total_seconds() if end is not None else None
    rows = blocks_to_dicts(
        block_frame(schedule, events, burn_in_s=BURN_IN_S, live_until_s=live_until_s)
    )
    return [r for r in rows if r.get("measurable", True)]


def _compliance(session_id: str, store) -> ComplianceStats:
    blocks = store.get_blocks(session_id)
    interventions = store.list_interventions(session_id)
    on_ids = {b["block_id"] for b in blocks if b.get("assignment") == "ON"}
    pinned_on = {
        i["block_id"]
        for i in interventions
        if i.get("executed")
        and i.get("source") == "model"
        and i.get("action_type") == "pin"
        and i.get("block_id") in on_ids
    }
    overrides = sum(1 for i in interventions if i.get("source") == "human")
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
            compliance=_compliance(session_id, store),
        )
    frame = _session_frame(session, store)
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
        compliance=_compliance(session_id, store),
    )


@router.get("/experiment/summary", response_model=ExperimentSummary)
def experiment_summary(store: StoreDep) -> ExperimentSummary:
    """Pooled primary analysis over every ENDED session that has a schedule.

    Runs the pre-registered estimator (randomization inference, redraws via the
    production assignment mechanism, Fisher CI) — the same functions the final
    notebook calls."""
    ys: list[float] = []
    zs: list[int] = []
    session_ids: list[str] = []
    phases: list[str] = []
    compliance_rates: list[float] = []

    ended = [
        s
        for s in store.list_sessions()
        if s.get("status") == "ended" and not _is_analysis_only(s)
    ]
    for session in ended:
        frame = _session_frame(session, store)
        for r in frame:
            ys.append(r["y"])
            zs.append(r["z"])
            session_ids.append(session["session_id"])
            phases.append(r["phase"])
        comp = _compliance(session["session_id"], store)
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
            message=(
                "Chưa đủ dữ liệu cho phân tích gộp (cần ≥ 2 phiên đã kết thúc và "
                "≥ 8 khối). Kết quả sẽ xuất hiện khi chuỗi thí nghiệm tích lũy thêm."
            ),
        )

    y = np.array(ys)
    z = np.array(zs)
    sids = np.array(session_ids)
    res = analyze_outer(y, z, sids, phases, n_draws=1000, seed=2026)

    # WITHIN-session CV, not the pooled one: the primary analysis differences
    # out the session effect (redraws per session, session FE, cluster-robust
    # SEs), so pooling raw blocks across sessions would charge the design for
    # between-session variance it never pays (audit 30/08).
    cv_val = within_session_cv(y, sids)
    cv = float(cv_val) if np.isfinite(cv_val) else None

    # Compliance: use the MEASURED value when there is one. A field literally
    # named measured_compliance sitting next to a table that ignored it and
    # used a literal 0.95 was indefensible (audit 30/08). No CUPED R² is
    # estimated anywhere in this path, so none is claimed: assuming R²=0.3
    # would shave 16% off the MDE on the strength of nothing.
    measured_comp = (
        float(np.mean(compliance_rates)) if compliance_rates else None
    )
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

    return ExperimentSummary(
        n_sessions=n_sessions,
        n_blocks=res.n_blocks,
        n_on=res.n_on,
        n_off=res.n_off,
        estimate=res.estimate,
        estimate_ht=res.estimate_ht,
        ci_low=res.ci_low,
        ci_high=res.ci_high,
        p_value=res.p_value,
        n_draws=res.n_draws,
        measured_cv=cv,
        measured_compliance=(float(np.mean(compliance_rates)) if compliance_rates else None),
        power_table=power_rows,
    )
