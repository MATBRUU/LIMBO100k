from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median

from run_free_agent import run_one_session


def evaluate_group(args: argparse.Namespace, group_index: int) -> dict:
    start_index = args.seed_offset + group_index * args.group_size
    values = []
    target_hits = 0
    low_events = 0
    best_value = float("-inf")
    best_index = start_index

    for local_index in range(args.group_size):
        session_index = start_index + local_index
        final_value, _, reason = run_one_session(
            strategy=args.strategy,
            initial_capital=args.initial_capital,
            target_capital=args.target_capital,
            stake=args.stake,
            multiplier=args.multiplier,
            fraction=args.risk_fraction,
            rounds=args.rounds,
            session_index=session_index,
            seed_offset=0,
        )
        values.append(final_value)

        if reason == "objective_reached":
            target_hits += 1
        if reason == "capital_floor":
            low_events += 1
        if final_value > best_value:
            best_value = final_value
            best_index = session_index

    return {
        "group_index": group_index,
        "start_index": start_index,
        "sessions": args.group_size,
        "avg_final": round(mean(values), 2),
        "median_final": round(median(values), 2),
        "target_hits": target_hits,
        "target_rate": round((target_hits / args.group_size) * 100, 6),
        "low_rate": round((low_events / args.group_size) * 100, 6),
        "best_final": round(best_value, 2),
        "best_index": best_index,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report strategy performance across independent cohorts")
    parser.add_argument("--strategy", default="temporal", choices=["fixed", "percentage", "adaptive", "dynamic", "convex", "phase", "meta_phase", "temporal"])
    parser.add_argument("--groups", type=int, default=100)
    parser.add_argument("--group-size", type=int, default=1000)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    rows = []
    for group_index in range(args.groups):
        row = evaluate_group(args, group_index)
        rows.append(row)
        print(
            f"Group {group_index + 1}/{args.groups} | "
            f"start={row['start_index']} | avg={row['avg_final']} € | "
            f"target={row['target_rate']}% | best={row['best_final']} €"
        )

    total_sessions = args.groups * args.group_size
    total_hits = sum(row["target_hits"] for row in rows)
    group_avgs = [row["avg_final"] for row in rows]
    positive_groups = sum(1 for row in rows if row["avg_final"] > args.initial_capital)
    hit_groups = sum(1 for row in rows if row["target_hits"] > 0)
    best_row = max(rows, key=lambda row: row["best_final"])

    print("\n=== LIMBO100k Cohort Report ===")
    print(f"Strategy: {args.strategy}")
    print(f"Total sessions: {total_sessions}")
    print(f"Groups: {args.groups}")
    print(f"Group size: {args.group_size}")
    print(f"Overall target rate: {round((total_hits / total_sessions) * 100, 6)} %")
    print(f"Average group final: {round(mean(group_avgs), 2)} €")
    print(f"Median group final: {round(median(group_avgs), 2)} €")
    print(f"Positive group rate: {round((positive_groups / args.groups) * 100, 4)} %")
    print(f"Groups with target hit: {round((hit_groups / args.groups) * 100, 4)} %")
    print(f"Best final: {best_row['best_final']} €")
    print(f"Best index: {best_row['best_index']}")

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"cohort_report_{args.strategy}.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
