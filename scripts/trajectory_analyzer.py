from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng
from limbo100k.session_runner import build_agent


def checkpoint_round(history: list[dict], threshold: float) -> int | None:
    for row in history:
        if row["capital"] >= threshold:
            return row["round"]
    return None


def max_drawdown(history: list[dict], initial_capital: float) -> float:
    peak = initial_capital
    worst = 0.0

    for row in history:
        capital = row["capital"]
        peak = max(peak, capital)
        worst = max(worst, peak - capital)

    return round(worst, 2)


def longest_streak(history: list[dict], outcome: str) -> int:
    best = 0
    current = 0

    for row in history:
        if row["outcome"] == outcome:
            current += 1
            best = max(best, current)
        else:
            current = 0

    return best


def late_momentum(history: list[dict], window: int = 25) -> float:
    if len(history) < 2:
        return 0.0

    tail = history[-window:]

    start = tail[0]["capital"]
    end = tail[-1]["capital"]

    if start <= 0:
        return 0.0

    return round((end / start) - 1, 4)


def classify(final_capital: float, peak_capital: float, target_capital: float) -> str:
    if final_capital >= target_capital:
        return "winner"

    if peak_capital >= target_capital * 0.5:
        return "near_miss_high"

    if peak_capital >= target_capital * 0.1:
        return "near_miss_mid"

    if peak_capital >= 1000:
        return "breakout"

    if peak_capital > 50:
        return "small_lift"

    return "dead"


def analyze_session(args: argparse.Namespace, session_index: int) -> dict:
    real_index = session_index + args.seed_offset

    rng = ProvablyFairRng(
        server_seed=f"FREE_SERVER_{args.strategy}_{real_index}",
        client_seed=f"FREE_CLIENT_{args.strategy}_{real_index}",
    )

    engine = LimboEngine(rng=rng)

    agent = build_agent(
        args.strategy,
        args.stake,
        args.multiplier,
        args.risk_fraction,
    )

    capital = args.initial_capital
    peak_capital = capital
    lowest_capital = capital
    history = []

    positive_rounds = 0
    negative_rounds = 0
    negative_sequence = 0
    stop_reason = "round_limit"

    for round_number in range(1, args.rounds + 1):

        if capital <= 0:
            stop_reason = "capital_floor"
            break

        if capital >= args.target_capital:
            stop_reason = "objective_reached"
            break

        amount, target = agent.next_bet(capital)

        if amount <= 0:
            stop_reason = "no_amount"
            break

        result = engine.play(
            stake=amount,
            target_multiplier=target,
        )

        capital += result.profit

        peak_capital = max(peak_capital, capital)
        lowest_capital = min(lowest_capital, capital)

        if result.won:
            positive_rounds += 1
            negative_sequence = 0
        else:
            negative_rounds += 1
            negative_sequence += 1

        history.append(
            {
                "round": round_number,
                "stake": round(amount, 2),
                "target": round(target, 4),
                "roll": round(result.rolled_multiplier, 4),
                "outcome": "success" if result.won else "failure",
                "profit": round(result.profit, 2),
                "capital": round(capital, 2),
                "drawdown": round(peak_capital - capital, 2),
            }
        )

        if hasattr(agent, "observe"):
            agent.observe(result.won, capital)

    final_capital = round(capital, 2)

    return {
        "session_index": real_index,
        "profile": classify(final_capital, peak_capital, args.target_capital),
        "final_capital": final_capital,
        "peak_capital": round(peak_capital, 2),
        "lowest_capital": round(lowest_capital, 2),
        "total_rounds": positive_rounds + negative_rounds,
        "stop_reason": stop_reason,
        "r_1000": checkpoint_round(history, 1000),
        "r_10000": checkpoint_round(history, 10000),
        "r_25000": checkpoint_round(history, 25000),
        "r_50000": checkpoint_round(history, 50000),
        "r_100000": checkpoint_round(history, 100000),
        "max_drawdown": max_drawdown(history, args.initial_capital),
        "longest_win_streak": longest_streak(history, "success"),
        "longest_loss_streak": longest_streak(history, "failure"),
        "late_momentum_25": late_momentum(history, 25),
    }


def summarize(rows: list[dict]) -> None:
    profiles = sorted(set(row["profile"] for row in rows))

    print("\n=== LIMBO100k Free Trajectory Analyzer ===")
    print(f"Analyzed sessions: {len(rows)}")

    for profile in profiles:
        subset = [row for row in rows if row["profile"] == profile]

        finals = [row["final_capital"] for row in subset]
        peaks = [row["peak_capital"] for row in subset]
        rounds = [row["total_rounds"] for row in subset]
        drawdowns = [row["max_drawdown"] for row in subset]

        print(
            f"{profile}: count={len(subset)} | "
            f"avg_final={round(mean(finals), 2)} € | "
            f"median_final={round(median(finals), 2)} € | "
            f"avg_peak={round(mean(peaks), 2)} € | "
            f"avg_rounds={round(mean(rounds), 2)} | "
            f"avg_drawdown={round(mean(drawdowns), 2)} €"
        )

    top = sorted(
        rows,
        key=lambda row: row["final_capital"],
        reverse=True,
    )[:20]

    print("\nTop 20 trajectories:")

    for row in top:
        print(
            f"index={row['session_index']} | "
            f"profile={row['profile']} | "
            f"final={row['final_capital']} € | "
            f"peak={row['peak_capital']} € | "
            f"rounds={row['total_rounds']} | "
            f"r1k={row['r_1000']} | "
            f"r10k={row['r_10000']} | "
            f"r25k={row['r_25000']} | "
            f"r100k={row['r_100000']} | "
            f"dd={row['max_drawdown']} € | "
            f"wins={row['longest_win_streak']} | "
            f"losses={row['longest_loss_streak']} | "
            f"momentum25={row['late_momentum_25']}"
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Analyze free-agent trajectories"
    )

    parser.add_argument(
        "--strategy",
        default="momentum_phase",
        choices=[
            "fixed",
            "percentage",
            "adaptive",
            "dynamic",
            "convex",
            "phase",
            "meta_phase",
            "temporal",
            "momentum_phase",
            "density_phase",
        ],
    )

    parser.add_argument("--sessions", type=int, default=10000)
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

    for local_index in range(args.sessions):
        rows.append(analyze_session(args, local_index))

        if (local_index + 1) % 1000 == 0:
            print(f"Analyzed {local_index + 1}/{args.sessions} sessions")

    summarize(rows)

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)

        output_path = (
            output_dir
            / f"trajectory_analyzer_{args.strategy}.csv"
        )

        with output_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys()),
            )

            writer.writeheader()
            writer.writerows(rows)

        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
