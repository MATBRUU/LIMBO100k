from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median

from run_free_agent import run_one_session


def frange(start: float, stop: float, step: float) -> list[float]:
    values = []
    current = start
    while current <= stop + 1e-12:
        values.append(round(current, 6))
        current += step
    return values


def evaluate_setting(
    strategy: str,
    sessions: int,
    seed_offset: int,
    initial_capital: float,
    target_capital: float,
    stake: float,
    multiplier: float,
    fraction: float,
    rounds: int,
    early_check_round: int,
    early_min_capital: float,
) -> dict:
    final_values = []
    objective_count = 0
    floor_count = 0
    best_value = float("-inf")
    best_index = 0

    for index in range(sessions):
        real_index = seed_offset + index
        capped_rounds = rounds

        if early_check_round > 0:
            first_capital, completed, reason = run_one_session(
                strategy=strategy,
                initial_capital=initial_capital,
                target_capital=target_capital,
                stake=stake,
                multiplier=multiplier,
                fraction=fraction,
                rounds=early_check_round,
                session_index=real_index,
                seed_offset=0,
            )
            if reason != "objective_reached" and first_capital < early_min_capital:
                final_capital = first_capital
                final_reason = "early_filter"
            else:
                final_capital, _, final_reason = run_one_session(
                    strategy=strategy,
                    initial_capital=initial_capital,
                    target_capital=target_capital,
                    stake=stake,
                    multiplier=multiplier,
                    fraction=fraction,
                    rounds=capped_rounds,
                    session_index=real_index,
                    seed_offset=0,
                )
        else:
            final_capital, _, final_reason = run_one_session(
                strategy=strategy,
                initial_capital=initial_capital,
                target_capital=target_capital,
                stake=stake,
                multiplier=multiplier,
                fraction=fraction,
                rounds=capped_rounds,
                session_index=real_index,
                seed_offset=0,
            )

        final_values.append(final_capital)

        if final_reason == "objective_reached":
            objective_count += 1
        if final_reason == "capital_floor":
            floor_count += 1
        if final_capital > best_value:
            best_value = final_capital
            best_index = real_index

    objective_rate = (objective_count / sessions) * 100
    floor_rate = (floor_count / sessions) * 100
    avg = mean(final_values)
    med = median(final_values)

    score = best_value + (objective_rate * 10000) + avg

    return {
        "strategy": strategy,
        "sessions": sessions,
        "seed_offset": seed_offset,
        "risk_fraction": fraction,
        "multiplier": multiplier,
        "average_final_capital": round(avg, 2),
        "median_final_capital": round(med, 2),
        "objective_rate": round(objective_rate, 6),
        "capital_floor_rate": round(floor_rate, 4),
        "best_session": round(best_value, 2),
        "best_session_index": best_index,
        "score": round(score, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search LIMBO100k parameter grids")
    parser.add_argument("--strategy", default="phase", choices=["fixed", "percentage", "adaptive", "dynamic", "convex", "phase","meta_phase","temporal"])
    parser.add_argument("--sessions", type=int, default=2000)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--fraction-min", type=float, default=0.06)
    parser.add_argument("--fraction-max", type=float, default=0.18)
    parser.add_argument("--fraction-step", type=float, default=0.02)
    parser.add_argument("--multiplier-min", type=float, default=3.0)
    parser.add_argument("--multiplier-max", type=float, default=8.0)
    parser.add_argument("--multiplier-step", type=float, default=1.0)
    parser.add_argument("--early-check-round", type=int, default=0)
    parser.add_argument("--early-min-capital", type=float, default=20.0)
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    fractions = frange(args.fraction_min, args.fraction_max, args.fraction_step)
    multipliers = frange(args.multiplier_min, args.multiplier_max, args.multiplier_step)

    reports = []
    total = len(fractions) * len(multipliers)
    count = 0

    for fraction in fractions:
        for multiplier in multipliers:
            count += 1
            report = evaluate_setting(
                strategy=args.strategy,
                sessions=args.sessions,
                seed_offset=args.seed_offset,
                initial_capital=args.initial_capital,
                target_capital=args.target_capital,
                stake=args.stake,
                multiplier=multiplier,
                fraction=fraction,
                rounds=args.rounds,
                early_check_round=args.early_check_round,
                early_min_capital=args.early_min_capital,
            )
            reports.append(report)
            print(
                f"{count}/{total} | fraction={fraction} | multiplier={multiplier} | "
                f"objective={report['objective_rate']}% | best={report['best_session']} € | "
                f"avg={report['average_final_capital']} € | score={report['score']}"
            )

    reports.sort(key=lambda item: item["score"], reverse=True)

    print("\n=== LIMBO100k Parameter Search ===")
    print("Top 10 settings:")
    for rank, report in enumerate(reports[:10], start=1):
        print(
            f"#{rank} | fraction={report['risk_fraction']} | multiplier={report['multiplier']} | "
            f"objective={report['objective_rate']}% | best={report['best_session']} € | "
            f"best_index={report['best_session_index']} | avg={report['average_final_capital']} €"
        )

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "parameter_search.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(reports[0].keys()))
            writer.writeheader()
            writer.writerows(reports)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
