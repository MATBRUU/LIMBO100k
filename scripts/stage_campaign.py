from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median

from run_free_agent import run_one_session


def parse_stages(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if len(values) < 2:
        raise ValueError("At least two stage values are required")
    return values


def run_stage_attempt(
    strategy: str,
    initial_capital: float,
    target_capital: float,
    stake: float,
    multiplier: float,
    fraction: float,
    rounds: int,
    session_index: int,
) -> tuple[float, bool]:
    final_capital, _, reason = run_one_session(
        strategy=strategy,
        initial_capital=initial_capital,
        target_capital=target_capital,
        stake=stake,
        multiplier=multiplier,
        fraction=fraction,
        rounds=rounds,
        session_index=session_index,
        seed_offset=0,
    )
    return final_capital, reason == "objective_reached" or final_capital >= target_capital


def apply_lock_rule(
    current: float,
    reserve: float,
    reached_target: float,
    lock_from_stage: float,
    lock_ratio: float,
) -> tuple[float, float, float]:
    if reached_target < lock_from_stage or lock_ratio <= 0:
        return current, reserve, 0.0

    locked = reached_target * lock_ratio
    next_current = reached_target - locked
    next_reserve = reserve + locked
    return next_current, next_reserve, locked


def run_campaign(args: argparse.Namespace, campaign_index: int, stages: list[float]) -> dict:
    reserve = args.global_bankroll
    current = stages[0]
    stage_index = 0
    attempts = 0
    stage_hits = 0
    locked_total = 0.0
    best_capital = current
    base_seed = args.seed_offset + campaign_index * args.max_attempts

    while attempts < args.max_attempts and reserve >= current and stage_index < len(stages) - 1:
        reserve -= current
        target = stages[stage_index + 1]
        session_index = base_seed + attempts
        attempts += 1

        final_capital, hit = run_stage_attempt(
            strategy=args.strategy,
            initial_capital=current,
            target_capital=target,
            stake=args.stake,
            multiplier=args.multiplier,
            fraction=args.risk_fraction,
            rounds=args.rounds,
            session_index=session_index,
        )

        best_capital = max(best_capital, final_capital)

        if hit:
            stage_hits += 1
            reached_target = min(final_capital, target)
            current = reached_target
            reserve += max(0.0, final_capital - target) if args.return_excess else 0.0

            current, reserve, locked = apply_lock_rule(
                current=current,
                reserve=reserve,
                reached_target=reached_target,
                lock_from_stage=args.lock_from_stage,
                lock_ratio=args.lock_ratio,
            )
            locked_total += locked
            stage_index += 1
        elif args.keep_residual:
            reserve += max(0.0, final_capital)

    final_total = reserve + current if stage_index >= len(stages) - 1 else reserve

    return {
        "campaign_index": campaign_index,
        "final_total": round(final_total, 2),
        "reserve": round(reserve, 2),
        "current_stage_capital": round(current, 2),
        "locked_total": round(locked_total, 2),
        "stage_index": stage_index,
        "stage_hits": stage_hits,
        "attempts": attempts,
        "success": stage_index >= len(stages) - 1,
        "best_capital": round(best_capital, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run staged bankroll campaigns")
    parser.add_argument("--strategy", default="temporal", choices=["fixed", "percentage", "adaptive", "dynamic", "convex", "phase", "meta_phase", "temporal"])
    parser.add_argument("--campaigns", type=int, default=1000)
    parser.add_argument("--global-bankroll", type=float, default=1000.0)
    parser.add_argument("--stages", default="50,500,5000,25000,100000")
    parser.add_argument("--max-attempts", type=int, default=100)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--lock-from-stage", type=float, default=25000.0)
    parser.add_argument("--lock-ratio", type=float, default=0.30)
    parser.add_argument("--keep-residual", action="store_true")
    parser.add_argument("--return-excess", action="store_true")
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    stages = parse_stages(args.stages)
    rows = []

    for campaign_index in range(args.campaigns):
        row = run_campaign(args, campaign_index, stages)
        rows.append(row)
        if (campaign_index + 1) % 100 == 0:
            print(
                f"Campaign {campaign_index + 1}/{args.campaigns} | "
                f"stage={row['stage_index']}/{len(stages) - 1} | "
                f"locked={row['locked_total']} € | "
                f"final={row['final_total']} €"
            )

    finals = [row["final_total"] for row in rows]
    locked_values = [row["locked_total"] for row in rows]
    successes = sum(1 for row in rows if row["success"])
    locked_campaigns = sum(1 for row in rows if row["locked_total"] > 0)
    stage_depths = [row["stage_index"] for row in rows]
    best_row = max(rows, key=lambda row: row["final_total"])

    print("\n=== LIMBO100k Staged Campaign ===")
    print(f"Strategy: {args.strategy}")
    print(f"Campaigns: {args.campaigns}")
    print(f"Global bankroll: {args.global_bankroll} €")
    print(f"Stages: {stages}")
    print(f"Lock from stage: {args.lock_from_stage} €")
    print(f"Lock ratio: {args.lock_ratio}")
    print(f"Average final total: {round(mean(finals), 2)} €")
    print(f"Median final total: {round(median(finals), 2)} €")
    print(f"Average locked total: {round(mean(locked_values), 2)} €")
    print(f"Campaigns with locked capital: {round((locked_campaigns / args.campaigns) * 100, 6)} %")
    print(f"Success campaign rate: {round((successes / args.campaigns) * 100, 6)} %")
    print(f"Average stage depth: {round(mean(stage_depths), 2)} / {len(stages) - 1}")
    print(f"Best campaign final: {best_row['final_total']} €")
    print(f"Best campaign index: {best_row['campaign_index']}")

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"stage_campaign_{args.strategy}.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
