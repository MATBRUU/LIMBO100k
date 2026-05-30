from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng
from limbo100k.session_runner import build_agent


def classify(
    final_capital: float,
    peak_capital: float,
    target_capital: float,
) -> str:

    if final_capital >= target_capital:
        return "winner"

    if peak_capital >= target_capital * 0.5:
        return "near_miss_high"

    if peak_capital >= target_capital * 0.1:
        return "near_miss_mid"

    if peak_capital >= 1000:
        return "dead_breakout"

    return "dead"


def safe_mean(values):

    clean = [
        value
        for value in values
        if value is not None
    ]

    if not clean:
        return None

    return round(mean(clean), 2)


def analyze_session(
    args,
    local_index,
):

    real_index = args.seed_offset + local_index

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
    peak = capital

    wins = 0
    losses = 0

    wins_before_1k = 0
    losses_before_1k = 0

    max_roll_before_1k = 0.0

    r100 = None
    r250 = None
    r500 = None
    r750 = None
    r1000 = None

    stop_reason = "round_limit"

    for round_number in range(
        1,
        args.rounds + 1,
    ):

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

        peak = max(
            peak,
            capital,
        )

        if capital < 1000:

            max_roll_before_1k = max(
                max_roll_before_1k,
                result.rolled_multiplier,
            )

            if result.won:
                wins_before_1k += 1
            else:
                losses_before_1k += 1

        if result.won:
            wins += 1
        else:
            losses += 1

        if hasattr(agent, "observe"):
            agent.observe(
                result.won,
                capital,
            )

        if r100 is None and capital >= 100:
            r100 = round_number

        if r250 is None and capital >= 250:
            r250 = round_number

        if r500 is None and capital >= 500:
            r500 = round_number

        if r750 is None and capital >= 750:
            r750 = round_number

        if r1000 is None and capital >= 1000:
            r1000 = round_number

    return {
        "session_index": real_index,
        "profile": classify(
            capital,
            peak,
            args.target_capital,
        ),
        "final_capital": round(capital, 2),
        "peak_capital": round(peak, 2),
        "wins": wins,
        "losses": losses,
        "wins_before_1k": wins_before_1k,
        "losses_before_1k": losses_before_1k,
        "max_roll_before_1k": round(
            max_roll_before_1k,
            4,
        ),
        "r100": r100,
        "r250": r250,
        "r500": r500,
        "r750": r750,
        "r1000": r1000,
        "stop_reason": stop_reason,
    }


def print_group(
    profile,
    rows,
):

    if not rows:
        return

    print(
        f"{profile}: "
        f"count={len(rows)} | "
        f"avg_final={round(mean(r['final_capital'] for r in rows),2)} € | "
        f"avg_peak={round(mean(r['peak_capital'] for r in rows),2)} € | "
        f"avg_wins_before_1k={round(mean(r['wins_before_1k'] for r in rows),2)} | "
        f"avg_losses_before_1k={round(mean(r['losses_before_1k'] for r in rows),2)} | "
        f"avg_max_roll_before_1k={round(mean(r['max_roll_before_1k'] for r in rows),2)} | "
        f"avg_r100={safe_mean([r['r100'] for r in rows])} | "
        f"avg_r250={safe_mean([r['r250'] for r in rows])} | "
        f"avg_r500={safe_mean([r['r500'] for r in rows])} | "
        f"avg_r750={safe_mean([r['r750'] for r in rows])} | "
        f"avg_r1000={safe_mean([r['r1000'] for r in rows])}"
    )


def main():

    parser = argparse.ArgumentParser(
        description="Direct Hyper Detector"
    )

    parser.add_argument(
        "--strategy",
        default="phase_state_v2",
    )

    parser.add_argument(
        "--sessions",
        type=int,
        default=100000,
    )

    parser.add_argument(
        "--seed-offset",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--initial-capital",
        type=float,
        default=50.0,
    )

    parser.add_argument(
        "--target-capital",
        type=float,
        default=100000.0,
    )

    parser.add_argument(
        "--stake",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--multiplier",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--risk-fraction",
        type=float,
        default=0.18,
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=5000,
    )

    parser.add_argument(
        "--export-csv",
        action="store_true",
    )

    args = parser.parse_args()

    rows = []

    for local_index in range(
        args.sessions
    ):

        rows.append(
            analyze_session(
                args,
                local_index,
            )
        )

        if (
            local_index + 1
        ) % 1000 == 0:

            print(
                f"Analyzed "
                f"{local_index + 1}/"
                f"{args.sessions}"
            )

    groups = defaultdict(list)

    for row in rows:
        groups[row["profile"]].append(row)

    print(
        "\n=== LIMBO100k Direct Hyper Detector ==="
    )

    for profile in sorted(groups):
        print_group(
            profile,
            groups[profile],
        )

    if args.export_csv:

        output_dir = Path(
            "results"
        )

        output_dir.mkdir(
            exist_ok=True
        )

        output_path = (
            output_dir
            / f"direct_hyper_detector_{args.strategy}.csv"
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

        print(
            f"\nCSV exported to: "
            f"{output_path}"
        )


if __name__ == "__main__":
    main()
