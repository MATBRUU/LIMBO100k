from __future__ import annotations

import argparse

from run_free_agent import run_one_session
from trajectory_analyzer import analyze_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit runner consistency for LIMBO100k")
    parser.add_argument("--strategy", default="momentum_phase")
    parser.add_argument("--sessions", type=int, default=10000)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    args = parser.parse_args()

    mismatches = []
    winners = []

    for local_index in range(args.sessions):
        free_final, free_rounds, free_reason = run_one_session(
            strategy=args.strategy,
            initial_capital=args.initial_capital,
            target_capital=args.target_capital,
            stake=args.stake,
            multiplier=args.multiplier,
            fraction=args.risk_fraction,
            rounds=args.rounds,
            session_index=local_index,
            seed_offset=args.seed_offset,
        )

        row = analyze_session(args, local_index)

        analyzer_final = row["final_capital"]
        analyzer_rounds = row["total_rounds"]
        analyzer_reason = row["stop_reason"]

        if abs(free_final - analyzer_final) > 0.01 or free_rounds != analyzer_rounds or free_reason != analyzer_reason:
            mismatches.append(
                {
                    "index": local_index + args.seed_offset,
                    "free_final": free_final,
                    "analyzer_final": analyzer_final,
                    "free_rounds": free_rounds,
                    "analyzer_rounds": analyzer_rounds,
                    "free_reason": free_reason,
                    "analyzer_reason": analyzer_reason,
                }
            )

        if free_final >= args.target_capital:
            winners.append(local_index + args.seed_offset)

    print("\n=== LIMBO100k Runner Consistency Audit ===")
    print(f"Strategy: {args.strategy}")
    print(f"Sessions audited: {args.sessions}")
    print(f"Seed offset: {args.seed_offset}")
    print(f"Winners found: {len(winners)}")
    print(f"Winner indexes: {winners[:50]}")
    print(f"Mismatches: {len(mismatches)}")

    if mismatches:
        print("\nFirst 20 mismatches:")
        for item in mismatches[:20]:
            print(item)
    else:
        print("All audited sessions match between free runner and trajectory analyzer.")


if __name__ == "__main__":
    main()
