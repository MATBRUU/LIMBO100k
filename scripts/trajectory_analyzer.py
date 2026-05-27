from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median

from limbo100k.session_runner import run_strategy_session


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


def first_explosion_round(history: list[dict], initial_capital: float, multiplier: float) -> int | None:
    target = initial_capital * multiplier
    return checkpoint_round(history, target)


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
    summary = run_strategy_session(
        strategy=args.strategy,
        initial_capital=args.initial_capital,
        target_capital=args.target_capital,
        stake=args.stake,
        target_multiplier=args.multiplier,
        risk_fraction=args.risk_fraction,
        max_rounds=args.rounds,
       server_seed=f"FREE_SERVER_{args.strategy}_{session_index}",
       client_seed=f"FREE_CLIENT_{args.strategy}_{session_index}",
    )
    history = summary.history
    return {
        "session_index": session_index,
        "profile": classify(summary.final_capital, summary.peak_capital, args.target_capital),
        "final_capital": summary.final_capital,
        "peak_capital": summary.peak_capital,
        "lowest_capital": summary.lowest_capital,
        "total_rounds": summary.total_rounds,
        "stop_reason": summary.stop_reason,
        "r_1000": checkpoint_round(history, 1000),
        "r_10000": checkpoint_round(history, 10000),
        "r_25000": checkpoint_round(history, 25000),
        "r_50000": checkpoint_round(history, 50000),
        "r_100000": checkpoint_round(history, 100000),
        "first_x10": first_explosion_round(history, args.initial_capital, 10),
        "first_x100": first_explosion_round(history, args.initial_capital, 100),
        "max_drawdown": max_drawdown(history, args.initial_capital),
        "longest_win_streak": longest_streak(history, "success"),
        "longest_loss_streak": longest_streak(history, "failure"),
        "late_momentum_25": late_momentum(history, 25),
    }


def summarize(rows: list[dict]) -> None:
    profiles = sorted(set(row["profile"] for row in rows))
    print("\n=== LIMBO100k Trajectory Analyzer ===")
    print(f"Analyzed sessions: {len(rows)}")

    for profile in profiles:
        subset = [row for row in rows if row["profile"] == profile]
        if not subset:
            continue
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

    top = sorted(rows, key=lambda row: row["final_capital"], reverse=True)[:20]
    print("\nTop 20 trajectories:")
    for row in top:
        print(
            f"index={row['session_index']} | profile={row['profile']} | "
            f"final={row['final_capital']} € | peak={row['peak_capital']} € | "
            f"rounds={row['total_rounds']} | r1k={row['r_1000']} | "
            f"r10k={row['r_10000']} | r25k={row['r_25000']} | "
            f"r100k={row['r_100000']} | dd={row['max_drawdown']} € | "
            f"wins={row['longest_win_streak']} | losses={row['longest_loss_streak']}"
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Analyze trajectory structures across strategy sessions"
    )

    parser.add_argument(
        "--strategy",
        default="temporal",
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
        session_index = args.seed_offset + local_index
        rows.append(analyze_session(args, session_index))
        if (local_index + 1) % 1000 == 0:
            print(f"Analyzed {local_index + 1}/{args.sessions} sessions")

    summarize(rows)

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"trajectory_analyzer_{args.strategy}.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
