from __future__ import annotations

import argparse

from limbo100k.analytics.monte_carlo import run_monte_carlo


def main() -> None:
    parser = argparse.ArgumentParser(description="Run autonomous LIMBO100k simulations")

    parser.add_argument("--strategy", default="adaptive", choices=["fixed", "percentage", "adaptive", "dynamic", "convex"])
    parser.add_argument("--sessions", type=int, default=1000)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=2.0)
    parser.add_argument("--risk-fraction", type=float, default=0.02)
    parser.add_argument("--rounds", type=int, default=1000)

    args = parser.parse_args()

    report = run_monte_carlo(
        sessions=args.sessions,
        strategy=args.strategy,
        initial_capital=args.initial_capital,
        target_capital=args.target_capital,
        stake=args.stake,
        target_multiplier=args.multiplier,
        risk_fraction=args.risk_fraction,
        max_rounds=args.rounds,
    )

    print("\n=== LIMBO100k Autonomous Batch ===")
    print(f"Strategy: {report.strategy}")
    print(f"Sessions: {report.sessions}")
    print(f"Average final capital: {report.average_final_capital} €")
    print(f"Median final capital: {report.median_final_capital} €")
    print(f"Objective rate: {report.objective_rate} %")
    print(f"Capital floor rate: {report.floor_rate} %")
    print(f"Best session: {report.best_session} €")
    print(f"Worst session: {report.worst_session} €")
    print(f"Average rounds: {report.average_rounds}")
    print(f"Dominant stop reason: {report.dominant_stop_reason}")


if __name__ == "__main__":
    main()
