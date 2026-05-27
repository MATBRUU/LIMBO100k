from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median

from run_free_agent import run_one_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Qualify a large deterministic sample and keep the strongest subset")
    parser.add_argument("--strategy", default="phase", choices=["fixed", "percentage", "adaptive", "dynamic", "convex", "phase","meta_phase"])
    parser.add_argument("--source-sessions", type=int, default=200000)
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--checkpoint-rounds", type=int, default=120)
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    rows = []

    for local_index in range(args.source_sessions):
        real_index = args.seed_offset + local_index

        checkpoint_capital, checkpoint_rounds, checkpoint_reason = run_one_session(
            strategy=args.strategy,
            initial_capital=args.initial_capital,
            target_capital=args.target_capital,
            stake=args.stake,
            multiplier=args.multiplier,
            fraction=args.risk_fraction,
            rounds=args.checkpoint_rounds,
            session_index=real_index,
            seed_offset=0,
        )

        final_capital, completed_rounds, reason = run_one_session(
            strategy=args.strategy,
            initial_capital=args.initial_capital,
            target_capital=args.target_capital,
            stake=args.stake,
            multiplier=args.multiplier,
            fraction=args.risk_fraction,
            rounds=args.rounds,
            session_index=real_index,
            seed_offset=0,
        )

        reached_objective = reason == "objective_reached"
        score = final_capital + (checkpoint_capital * 0.2) + (100000 if reached_objective else 0)

        rows.append(
            {
                "session_index": real_index,
                "checkpoint_capital": round(checkpoint_capital, 2),
                "checkpoint_rounds": checkpoint_rounds,
                "checkpoint_reason": checkpoint_reason,
                "final_capital": round(final_capital, 2),
                "completed_rounds": completed_rounds,
                "reason": reason,
                "reached_objective": reached_objective,
                "score": round(score, 2),
            }
        )

        if (local_index + 1) % 10000 == 0:
            print(f"Scanned {local_index + 1}/{args.source_sessions} sessions")

    rows.sort(key=lambda row: row["score"], reverse=True)
    qualified = rows[: args.sample_size]

    objective_count = sum(1 for row in rows if row["reached_objective"])
    qualified_objective_count = sum(1 for row in qualified if row["reached_objective"])

    print("\n=== LIMBO100k Qualified Sample ===")
    print(f"Strategy: {args.strategy}")
    print(f"Source sessions: {args.source_sessions}")
    print(f"Qualified sample size: {args.sample_size}")
    print(f"Source objective rate: {round((objective_count / args.source_sessions) * 100, 6)} %")
    print(f"Qualified objective rate: {round((qualified_objective_count / args.sample_size) * 100, 6)} %")
    print(f"Best final capital: {qualified[0]['final_capital']} €")
    print(f"Best session index: {qualified[0]['session_index']}")
    print(f"Qualified average final capital: {round(mean(row['final_capital'] for row in qualified), 2)} €")
    print(f"Qualified median final capital: {round(median(row['final_capital'] for row in qualified), 2)} €")

    print("\nTop 20 qualified sessions:")
    for rank, row in enumerate(qualified[:20], start=1):
        print(
            f"#{rank} | index={row['session_index']} | checkpoint={row['checkpoint_capital']} € | "
            f"final={row['final_capital']} € | reason={row['reason']} | score={row['score']}"
        )

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "qualified_sample.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(qualified[0].keys()))
            writer.writeheader()
            writer.writerows(qualified)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
