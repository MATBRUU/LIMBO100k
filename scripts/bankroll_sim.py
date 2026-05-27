from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median

from run_free_agent import run_one_session


def run_campaign(args: argparse.Namespace, campaign_index: int) -> dict:
    bankroll = args.global_bankroll
    peak_bankroll = bankroll
    attempts = 0
    hit_count = 0
    best_final = 0.0
    best_session_index = args.seed_offset + campaign_index * args.max_attempts

    for attempt_index in range(args.max_attempts):
        if bankroll < args.session_capital:
            break

        session_index = args.seed_offset + campaign_index * args.max_attempts + attempt_index
        bankroll -= args.session_capital
        attempts += 1

        final_capital, _, reason = run_one_session(
            strategy=args.strategy,
            initial_capital=args.session_capital,
            target_capital=args.session_target,
            stake=args.stake,
            multiplier=args.multiplier,
            fraction=args.risk_fraction,
            rounds=args.rounds,
            session_index=session_index,
            seed_offset=0,
        )

        if final_capital > best_final:
            best_final = final_capital
            best_session_index = session_index

        if reason == "objective_reached" or final_capital >= args.session_target:
            hit_count += 1
            bankroll += final_capital
            if args.stop_on_hit:
                break
        elif args.keep_residual:
            bankroll += max(0.0, final_capital)

        peak_bankroll = max(peak_bankroll, bankroll)

        if bankroll >= args.global_target:
            break

    return {
        "campaign_index": campaign_index,
        "final_bankroll": round(bankroll, 2),
        "peak_bankroll": round(peak_bankroll, 2),
        "attempts": attempts,
        "hit_count": hit_count,
        "success": bankroll >= args.global_target,
        "depleted": bankroll < args.session_capital,
        "best_final": round(best_final, 2),
        "best_session_index": best_session_index,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate global bankroll allocation across independent sessions")
    parser.add_argument("--strategy", default="temporal", choices=["fixed", "percentage", "adaptive", "dynamic", "convex", "phase", "meta_phase", "temporal"])
    parser.add_argument("--campaigns", type=int, default=1000)
    parser.add_argument("--global-bankroll", type=float, default=1000.0)
    parser.add_argument("--global-target", type=float, default=100000.0)
    parser.add_argument("--session-capital", type=float, default=50.0)
    parser.add_argument("--session-target", type=float, default=100000.0)
    parser.add_argument("--max-attempts", type=int, default=20)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--keep-residual", action="store_true")
    parser.add_argument("--stop-on-hit", action="store_true")
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    rows = []
    for campaign_index in range(args.campaigns):
        row = run_campaign(args, campaign_index)
        rows.append(row)
        if (campaign_index + 1) % 100 == 0:
            print(f"Campaign {campaign_index + 1}/{args.campaigns} | final={row['final_bankroll']} € | hits={row['hit_count']}")

    finals = [row["final_bankroll"] for row in rows]
    successes = sum(1 for row in rows if row["success"])
    depleted = sum(1 for row in rows if row["depleted"])
    hit_campaigns = sum(1 for row in rows if row["hit_count"] > 0)
    best_row = max(rows, key=lambda row: row["final_bankroll"])

    print("\n=== LIMBO100k Bankroll Simulation ===")
    print(f"Strategy: {args.strategy}")
    print(f"Campaigns: {args.campaigns}")
    print(f"Global bankroll: {args.global_bankroll} €")
    print(f"Session capital: {args.session_capital} €")
    print(f"Max attempts: {args.max_attempts}")
    print(f"Average final bankroll: {round(mean(finals), 2)} €")
    print(f"Median final bankroll: {round(median(finals), 2)} €")
    print(f"Success campaign rate: {round((successes / args.campaigns) * 100, 6)} %")
    print(f"Hit campaign rate: {round((hit_campaigns / args.campaigns) * 100, 6)} %")
    print(f"Depleted campaign rate: {round((depleted / args.campaigns) * 100, 6)} %")
    print(f"Best campaign final: {best_row['final_bankroll']} €")
    print(f"Best campaign index: {best_row['campaign_index']}")
    print(f"Best session inside campaigns: {best_row['best_session_index']}")

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"bankroll_sim_{args.strategy}.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
