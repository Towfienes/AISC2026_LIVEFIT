"""CLI: run the simulator validation study.

Examples:
    livelift-simulate --reps 50 --sessions 10 --effect 0.15
    livelift-simulate --reps 100 --sessions 10 --effect 0.0        # A/A study
    livelift-simulate --reps 50 --sessions 10 --effect 0.15 --carryover 120
"""

from __future__ import annotations

import argparse

from livelift.core.assigner.outer import DesignParams
from livelift.sim.simulator import SimParams
from livelift.sim.validate import run_validation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="livelift-simulate", description=__doc__)
    parser.add_argument("--reps", type=int, default=50)
    parser.add_argument("--sessions", type=int, default=10, help="sessions per replication")
    parser.add_argument("--minutes", type=int, default=90)
    parser.add_argument("--block", type=int, default=5)
    parser.add_argument("--effect", type=float, default=0.15)
    parser.add_argument("--carryover", type=float, default=0.0, help="carryover half-life, seconds")
    parser.add_argument("--burn-in", type=int, default=60, help="analysis burn-in, seconds")
    parser.add_argument("--draws", type=int, default=500, help="randomization draws")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    design = DesignParams(block_min=args.block)
    sim = SimParams(treatment_effect=args.effect, carryover_halflife_s=args.carryover)
    result = run_validation(
        n_reps=args.reps,
        n_sessions_per_rep=args.sessions,
        session_minutes=args.minutes,
        design=design,
        sim_params=sim,
        burn_in_s=args.burn_in,
        n_draws=args.draws,
        master_seed=args.seed,
    )
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
