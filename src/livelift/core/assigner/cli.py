"""CLI: generate a pre-session switchback schedule.

Usage:
    livelift-schedule --duration 90 [--block 5] [--washout 0] [--seed N] [--out file.json]

Prints the schedule as JSON. The operator runbook (ops/runbooks) requires this
to be run and persisted at T-1h, BEFORE broadcast. When ``--seed`` is omitted a
seed is drawn from the OS entropy source and printed — record it.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys

from livelift.console import configure as _configure_console
from livelift.core.assigner.outer import DesignParams, generate_schedule


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = argparse.ArgumentParser(prog="livelift-schedule", description=__doc__)
    parser.add_argument("--duration", type=int, required=True, help="session length, minutes")
    parser.add_argument("--block", type=int, default=5, help="block length, minutes")
    parser.add_argument(
        "--washout",
        type=int,
        default=0,
        help="design washout, minutes (default 0: analysis burn-in instead)",
    )
    parser.add_argument("--jitter", type=int, default=30, help="boundary jitter, seconds")
    parser.add_argument(
        "--no-endpoint-double",
        action="store_true",
        help="disable doubled first/last blocks",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", type=str, default=None, help="write JSON here instead of stdout")
    args = parser.parse_args(argv)

    seed = args.seed if args.seed is not None else secrets.randbits(63)
    params = DesignParams(
        block_min=args.block,
        washout_min=args.washout,
        jitter_s=args.jitter,
        endpoint_double=not args.no_endpoint_double,
    )
    schedule = generate_schedule(args.duration, params, seed)
    payload = {
        "session_duration_min": schedule.session_duration_min,
        "design": {
            "block_min": params.block_min,
            "washout_min": params.washout_min,
            "endpoint_double": params.endpoint_double,
            "jitter_s": params.jitter_s,
            "p": params.p,
            "min_per_arm_per_phase": params.min_per_arm_per_phase,
        },
        "seed": schedule.seed,
        "n_redraws": schedule.n_redraws,
        "n_measurement_blocks": len(schedule.measurement_blocks),
        "n_on": schedule.n_on,
        "n_off": schedule.n_off,
        "blocks": schedule.to_rows(),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"schedule written to {args.out} (seed={seed})", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
