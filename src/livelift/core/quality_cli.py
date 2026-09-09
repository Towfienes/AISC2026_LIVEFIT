"""CLI: run the post-session data-quality checks (plan §8.3) against the DB.

    livelift-qc --session-id <uuid> [--platform-total 1234000]
                [--recount-clicks] [--tau 10]

``--recount-clicks`` (gói Q1, đối soát T+30'): chạy lại phân loại click hợp lệ
(refractory/volume-cap — quy tắc thời gian) trên toàn bộ click của phiên bằng
``livelift.core.click_validity.recount_click_validity``, CẬP NHẬT cờ
``is_valid``/``invalid_reason`` (không bao giờ xóa row — flag-don't-drop) và in
bảng sensitivity τ ∈ {5, 30, 60} (chỉ đếm, không ghi).

Exit code 0 = all checks pass, 1 = at least one failure (usable in cron/CI).
"""

from __future__ import annotations

import argparse
import sys

import psycopg

from livelift.config import get_settings
from livelift.console import configure as _configure_console
from livelift.core.click_validity import REFRACTORY_TAU_S, recount_click_validity
from livelift.core.features import Event, block_frame, blocks_to_dicts
from livelift.core.quality import run_all

SENSITIVITY_TAUS = (5.0, 30.0, 60.0)

BURN_IN_S = 60
"""Phải khớp `api.routes.reports.BURN_IN_S`.

Kiểm tra `assignment_integrity` chỉ đọc chỉ số khối và chuỗi gán — hai thứ
`block_frame` không bao giờ thay đổi theo burn-in — nên một lệch giá trị ở đây
không làm sai kết luận của nó; hằng số vẫn giữ đúng để khung dựng ở CLI là đúng
khung mà báo cáo dựng.
"""


def _analysis_frame(
    session: dict,
    block_rows: list[dict],
    tick_rows: list[tuple],
    click_rows: list[tuple],
    live_until_s: float | None,
) -> list[dict] | None:
    """Khung phân tích của phiên — dựng bằng ĐÚNG hàm mà ước lượng viên dùng.

    Dựng lại :class:`Schedule` từ ``experiment_block`` rồi chạy chính
    ``core.features.block_frame``. Kiểm tra ``assignment_integrity`` chỉ có giá
    trị nếu nó soi đúng khung này: một bản sao viết tay sẽ khớp với lịch đã lưu
    kể cả khi `block_frame`/`rebuild_schedule` có lỗi — tức là mù đúng chỗ cần
    nhìn.

    Trả về None khi phiên chưa có khối (chưa sinh lịch) — để kiểm tra báo đúng
    lý do thay vì so một danh sách rỗng với một danh sách rỗng.
    """
    if not block_rows:
        return None
    # I/O ở rìa: CLI là entry point, được phép chạm tầng api (tiền lệ:
    # nlp/label_llm.py). Lõi thuần trong core/ vẫn không phụ thuộc api.
    from livelift.api.service import rebuild_schedule

    schedule = rebuild_schedule(session, block_rows)
    events: list[Event] = [
        Event("viewer_count", float(offset), value=float(viewers)) for offset, viewers in tick_rows
    ]
    events += [
        Event("click", float(offset), is_valid=is_valid is not False)
        for offset, is_valid in click_rows
    ]
    return blocks_to_dicts(
        block_frame(schedule, events, burn_in_s=BURN_IN_S, live_until_s=live_until_s)
    )


def _recount_clicks(conn: psycopg.Connection, sid: str, tau_s: float) -> None:
    """Re-run the timing validity rules over the session's clicks and apply
    the flag changes (update-only; rows are never deleted)."""
    rows = [
        {
            "click_id": str(r[0]),
            "ts": r[1],
            "dedup_hash": r[2],
            "shortlink_code": r[3],
            "block_id": str(r[4]) if r[4] is not None else None,
            "is_valid": r[5],
            "invalid_reason": r[6],
        }
        for r in conn.execute(
            "SELECT click_id, ts, dedup_hash, shortlink_code, block_id, "
            "is_valid, invalid_reason FROM click_event "
            "WHERE session_id = %s ORDER BY ts",
            (sid,),
        ).fetchall()
    ]
    changes = recount_click_validity(rows, tau_s=tau_s)
    for ch in changes:
        conn.execute(
            "UPDATE click_event SET is_valid = %s, invalid_reason = %s WHERE click_id = %s",
            (ch["is_valid"], ch["invalid_reason"], ch["click_id"]),
        )
    n_valid = sum(1 for r in rows if r["is_valid"] is not False)
    delta = sum(1 for c in changes if not c["is_valid"]) - sum(1 for c in changes if c["is_valid"])
    print(
        f"[recount] τ={tau_s:g}s: {len(rows)} click, {len(changes)} cờ thay đổi "
        f"(hợp lệ {n_valid} -> {n_valid - delta})"
    )
    for sens_tau in SENSITIVITY_TAUS:
        sens = recount_click_validity(rows, tau_s=sens_tau)
        would_valid = n_valid - (
            sum(1 for c in sens if not c["is_valid"]) - sum(1 for c in sens if c["is_valid"])
        )
        print(f"[recount] sensitivity τ={sens_tau:g}s: {would_valid}/{len(rows)} click hợp lệ")


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = argparse.ArgumentParser(prog="livelift-qc", description=__doc__)
    parser.add_argument("--session-id", required=True)
    parser.add_argument(
        "--platform-total",
        type=float,
        default=0.0,
        help="gross order total from the platform report, for reconciliation",
    )
    parser.add_argument(
        "--recount-clicks",
        action="store_true",
        help="chạy lại phân loại click hợp lệ (đối soát T+30', gói Q1)",
    )
    parser.add_argument(
        "--tau",
        type=float,
        default=REFRACTORY_TAU_S,
        help="cửa sổ refractory τ (giây) cho --recount-clicks",
    )
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)

    url = args.database_url or get_settings().database_url
    sid = args.session_id
    with psycopg.connect(url) as conn:
        session = conn.execute(
            "SELECT planned_duration_min, design, start_ts, end_ts "
            "FROM live_session WHERE session_id = %s",
            (sid,),
        ).fetchone()
        if session is None:
            print(f"session {sid} not found", file=sys.stderr)
            return 2
        if args.recount_clicks:
            _recount_clicks(conn, sid, args.tau)
        planned_s = session[0] * 60
        design = session[1] or {}
        start_ts, end_ts = session[2], session[3]
        # Continuity must be judged over the window the session ACTUALLY ran.
        # Using the planned duration made every early-finished session report a
        # huge phantom gap (incident 27/08).
        if start_ts is not None and end_ts is not None:
            duration_s = max((end_ts - start_ts).total_seconds(), 0.0)
        else:
            duration_s = planned_s
        scheduled = design.get("blocks", [])
        session_stub = {"planned_duration_min": session[0], "design": design}

        block_rows = [
            {
                "block_index": r[0],
                "phase": r[1],
                "assignment": r[2],
                "propensity": r[3],
                "is_washout": r[4],
                "start_offset_s": r[5],
                "end_offset_s": r[6],
            }
            for r in conn.execute(
                "SELECT block_index, phase, assignment, propensity, is_washout, "
                "start_offset_s, end_offset_s FROM experiment_block "
                "WHERE session_id = %s ORDER BY block_index",
                (sid,),
            ).fetchall()
        ]
        blocks = [
            {k: b[k] for k in ("block_index", "assignment", "is_washout")} for b in block_rows
        ]
        tick_rows = conn.execute(
            "SELECT EXTRACT(EPOCH FROM (ts_bucket - s.start_ts)), t.viewers "
            "FROM session_tick t JOIN live_session s USING (session_id) "
            "WHERE t.session_id = %s AND s.start_ts IS NOT NULL ORDER BY ts_bucket",
            (sid,),
        ).fetchall()
        ticks = [r[0] for r in tick_rows]
        click_rows = conn.execute(
            "SELECT EXTRACT(EPOCH FROM (c.ts - s.start_ts)), c.is_valid "
            "FROM click_event c JOIN live_session s USING (session_id) "
            "WHERE c.session_id = %s AND s.start_ts IS NOT NULL ORDER BY c.ts",
            (sid,),
        ).fetchall()
        # Chỉ lượt rút thiết kế ĐÃ CHẠY: một phiên được sinh lại lịch khi chưa
        # phát sóng vẫn giữ dòng của lượt rút cũ trong bảng chỉ-ghi-thêm.
        d_hash = design.get("design_hash")
        assignment_events = (
            [
                {
                    "block_idx": r[0],
                    "assignment": r[1],
                    "block_start_s": r[2],
                    "block_end_s": r[3],
                }
                for r in conn.execute(
                    "SELECT block_idx, assignment, block_start_s, block_end_s "
                    "FROM assignment_event WHERE session_id = %s AND design_hash = %s "
                    "ORDER BY block_idx",
                    (sid, d_hash),
                ).fetchall()
            ]
            if d_hash
            else []
        )
        interventions = [
            {
                "action_id": str(r[0]),
                "block_id": r[1],
                "inner_propensity": r[2],
                "source": r[3],
                "executed": r[4],
                "override_reason": r[5],
            }
            for r in conn.execute(
                "SELECT action_id, block_id, inner_propensity, source, executed, "
                "override_reason FROM intervention_log WHERE session_id = %s",
                (sid,),
            ).fetchall()
        ]
        comments = [
            r[0]
            for r in conn.execute(
                "SELECT text_scrubbed FROM comment_event WHERE session_id = %s", (sid,)
            ).fetchall()
        ]
        order_total = conn.execute(
            "SELECT COALESCE(SUM(gross), 0) FROM order_event WHERE session_id = %s", (sid,)
        ).fetchone()[0]

    analysis_blocks = _analysis_frame(
        session=session_stub,
        block_rows=block_rows,
        tick_rows=tick_rows,
        click_rows=click_rows,
        # Cùng quy tắc với `api.routes.reports._session_frame`: cắt cửa sổ kết
        # quả theo lúc phát sóng THẬT SỰ dừng. Khi thiếu mốc thời gian,
        # `duration_s` đã rơi về thời lượng dự kiến nên giá trị này vô hại.
        live_until_s=float(duration_s),
    )

    results = run_all(
        scheduled_blocks=scheduled,
        recorded_blocks=blocks,
        tick_timestamps_s=[float(t) for t in ticks],
        session_duration_s=float(duration_s),
        interventions=interventions,
        scrubbed_texts=comments,
        db_order_total=float(order_total),
        platform_report_total=args.platform_total,
        analysis_blocks=analysis_blocks,
        assignment_events=assignment_events,
    )
    failed = 0
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"[{mark}] {r.name}: {r.detail}")
        failed += 0 if r.passed else 1
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
