"""CLI: run the post-session data-quality checks (plan §8.3) against the DB.

    livelift-qc --session-id <uuid> [--platform-total 1234000]

Exit code 0 = all checks pass, 1 = at least one failure (usable in cron/CI).
"""

from __future__ import annotations

import argparse
import sys

import psycopg

from livelift.config import get_settings
from livelift.console import configure as _configure_console
from livelift.core.quality import run_all


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

        blocks = [
            {
                "block_index": r[0],
                "assignment": r[1],
                "is_washout": r[2],
            }
            for r in conn.execute(
                "SELECT block_index, assignment, is_washout FROM experiment_block "
                "WHERE session_id = %s ORDER BY block_index",
                (sid,),
            ).fetchall()
        ]
        ticks = [
            r[0]
            for r in conn.execute(
                "SELECT EXTRACT(EPOCH FROM (ts_bucket - s.start_ts)) "
                "FROM session_tick t JOIN live_session s USING (session_id) "
                "WHERE t.session_id = %s AND s.start_ts IS NOT NULL",
                (sid,),
            ).fetchall()
        ]
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

    results = run_all(
        scheduled_blocks=scheduled,
        recorded_blocks=blocks,
        tick_timestamps_s=[float(t) for t in ticks],
        session_duration_s=float(duration_s),
        interventions=interventions,
        scrubbed_texts=comments,
        db_order_total=float(order_total),
        platform_report_total=args.platform_total,
    )
    failed = 0
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"[{mark}] {r.name}: {r.detail}")
        failed += 0 if r.passed else 1
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
