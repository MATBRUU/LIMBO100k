from __future__ import annotations

import argparse
from statistics import mean, median

from run_free_agent import run_one_session


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan deterministic seed ranges for high-end trajectories")
    parser.add_argument("--strategy", default="convex", choices=["fixed", "percentage", "adaptive", "dynamic", "convex","phase","meta_phase","temporal"])
    parser.add_argument("--ranges", type=int, default=10)
    parser.add_argument("--range-size", type=int, default=10000)
    parser.add_argument("--start-offset", type=int, default=0)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=3.0)
    parser.add_argument("--risk-fraction", type=float, default=0.04)
    parser.add_argument("--rounds", type=int, default=5000)
    args = parser.parse_args()

    global_best_value = float("-inf")
    global_best_index = 0
    global_best_range = 0
    global_values = []
    objective_count = 0
    floor_count = 0
    total_sessions = args.ranges * args.range_size

    for range_number in range(args.ranges):
        offset = args.start_offset + range_number * args.range_size
        range_values = []
        range_best_value = float("-inf")
        range_best_index = offset

        for local_index in range(args.range_size):
            session_index = offset + local_index
            final_capital, _, reason = run_one_session(
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

            range_values.append(final_capital)
            global_values.append(final_capital)

            if reason == "objective_reached":
                objective_count += 1

            if reason == "capital_floor":
                floor_count += 1

            if final_capital > range_best_value:
                range_best_value = final_capital
                range_best_index = session_index

            if final_capital > global_best_value:
                global_best_value = final_capital
                global_best_index = session_index
                global_best_range = range_number

        print(
            f"Range {range_number + 1}/{args.ranges} | "
            f"offset={offset} | "
            f"best={round(range_best_value, 2)} € | "
            f"best_index={range_best_index} | "
            f"avg={round(mean(range_values), 2)} € | "
            f"median={round(median(range_values), 2)} €"
        )

    print("\n=== LIMBO100k Range Scan ===")
    print(f"Strategy: {args.strategy}")
    print(f"Total sessions: {total_sessions}")
    print(f"Start offset: {args.start_offset}")
    print(f"Best session: {round(global_best_value, 2)} €")
    print(f"Best session index: {global_best_index}")
    print(f"Best range number: {global_best_range + 1}")
    print(f"Average final capital: {round(mean(global_values), 2)} €")
    print(f"Median final capital: {round(median(global_values), 2)} €")
    print(f"Objective rate: {round((objective_count / total_sessions) * 100, 6)} %")
    print(f"Capital floor rate: {round((floor_count / total_sessions) * 100, 4)} %")


if __name__ == "__main__":
    main()
