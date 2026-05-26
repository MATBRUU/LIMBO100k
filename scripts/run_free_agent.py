from __future__ import annotations

import argparse
from statistics import mean, median

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng
from limbo100k.session_runner import build_agent


def run_one_session(
    strategy: str,
    initial_capital: float,
    target_capital: float,
    stake: float,
    multiplier: float,
    fraction: float,
    rounds: int,
    session_index: int,
    seed_offset: int,
) -> tuple[float, int, str]:
    real_index = session_index + seed_offset

    rng = ProvablyFairRng(
        server_seed=f"FREE_SERVER_{strategy}_{real_index}",
        client_seed=f"FREE_CLIENT_{strategy}_{real_index}",
    )

    engine = LimboEngine(rng=rng)
    agent = build_agent(strategy, stake, multiplier, fraction)

    capital = initial_capital
    completed_rounds = 0
    reason = "round_limit"

    for _ in range(rounds):
        if capital <= 0:
            reason = "capital_floor"
            break

        if capital >= target_capital:
            reason = "objective_reached"
            break

        amount, target = agent.next_bet(capital)
        if amount <= 0:
            reason = "no_amount"
            break

        result = engine.play(stake=amount, target_multiplier=target)
        capital += result.profit
        completed_rounds += 1

        if hasattr(agent, "observe"):
            agent.observe(result.won, capital)

    return round(capital, 2), completed_rounds, reason


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LIMBO100k free-form batches")

    parser.add_argument(
        "--strategy",
        default="convex",
        choices=["fixed", "percentage", "adaptive", "dynamic", "convex"],
    )

    parser.add_argument("--sessions", type=int, default=1000)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=3.0)
    parser.add_argument("--risk-fraction", type=float, default=0.04)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--seed-offset", type=int, default=0)

    args = parser.parse_args()

    final_values = []
    round_counts = []
    objective_count = 0
    floor_count = 0
    best_value = float("-inf")
    worst_value = float("inf")
    best_index = 0

    for index in range(args.sessions):
        final_capital, completed_rounds, reason = run_one_session(
            strategy=args.strategy,
            initial_capital=args.initial_capital,
            target_capital=args.target_capital,
            stake=args.stake,
            multiplier=args.multiplier,
            fraction=args.risk_fraction,
            rounds=args.rounds,
            session_index=index,
            seed_offset=args.seed_offset,
        )

        final_values.append(final_capital)
        round_counts.append(completed_rounds)

        if reason == "objective_reached":
            objective_count += 1

        if reason == "capital_floor":
            floor_count += 1

        if final_capital > best_value:
            best_value = final_capital
            best_index = index + args.seed_offset

        if final_capital < worst_value:
            worst_value = final_capital

    print("\n=== LIMBO100k Free Agent Batch ===")
    print(f"Strategy: {args.strategy}")
    print(f"Sessions: {args.sessions}")
    print(f"Seed offset: {args.seed_offset}")
    print(f"Average final capital: {round(mean(final_values), 2)} €")
    print(f"Median final capital: {round(median(final_values), 2)} €")
    print(f"Objective rate: {round((objective_count / args.sessions) * 100, 4)} %")
    print(f"Capital floor rate: {round((floor_count / args.sessions) * 100, 4)} %")
    print(f"Best session: {round(best_value, 2)} €")
    print(f"Best session index: {best_index}")
    print(f"Worst session: {round(worst_value, 2)} €")
    print(f"Average rounds: {round(mean(round_counts), 2)}")


if __name__ == "__main__":
    main()
