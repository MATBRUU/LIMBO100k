from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng
from limbo100k.session_runner import build_agent


def run_protected_session(
    strategy: str,
    session_index: int,
    initial_capital: float,
    target_capital: float,
    stake: float,
    multiplier: float,
    fraction: float,
    rounds: int,
    protect_from: float,
    protect_ratio: float,
) -> dict:

    rng = ProvablyFairRng(
        server_seed=f"PROTECTED_SERVER_{strategy}_{session_index}",
        client_seed=f"PROTECTED_CLIENT_{strategy}_{session_index}",
    )

    engine = LimboEngine(rng=rng)

    agent = build_agent(
        strategy,
        stake,
        multiplier,
        fraction,
    )

    active = initial_capital
    protected = 0.0

    peak_total = initial_capital

    protected_once = False

    final_reason = "max_rounds"

    for round_number in range(1, rounds + 1):

        total = active + protected

        if total >= target_capital:
            final_reason = "objective_reached"
            break

        if active <= 0:
            final_reason = "active_depleted"
            break

        if (
            not protected_once
            and active >= protect_from
            and protect_ratio > 0
        ):

            locked = active * protect_ratio

            active -= locked
            protected += locked

            protected_once = True

        amount, target = agent.next_bet(active)

        if amount <= 0:
            final_reason = "no_exposure"
            break

        result = engine.play(
            stake=amount,
            target_multiplier=target,
        )

        active += result.profit

        total = active + protected

        peak_total = max(
            peak_total,
            total,
        )

        if hasattr(agent, "observe"):
            agent.observe(
                result.won,
                active,
            )

    return {
        "session_index": session_index,
        "final_total": round(active + protected, 2),
        "final_active": round(active, 2),
        "protected": round(protected, 2),
        "peak_total": round(peak_total, 2),
        "protected_once": protected_once,
        "reason": final_reason,
    }


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Run direct sessions with internal capital protection"
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
            "density_phase",
        ],
    )

    parser.add_argument(
        "--sessions",
        type=int,
        default=10000,
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
        "--protect-from",
        type=float,
        default=25000.0,
    )

    parser.add_argument(
        "--protect-ratio",
        type=float,
        default=0.30,
    )

    parser.add_argument(
        "--export-csv",
        action="store_true",
    )

    args = parser.parse_args()

    rows = []

    for local_index in range(args.sessions):

        session_index = (
            args.seed_offset
            + local_index
        )

        rows.append(
            run_protected_session(
                strategy=args.strategy,
                session_index=session_index,
                initial_capital=args.initial_capital,
                target_capital=args.target_capital,
                stake=args.stake,
                multiplier=args.multiplier,
                fraction=args.risk_fraction,
                rounds=args.rounds,
                protect_from=args.protect_from,
                protect_ratio=args.protect_ratio,
            )
        )

    finals = [
        row["final_total"]
        for row in rows
    ]

    protected_count = sum(
        1
        for row in rows
        if row["protected_once"]
    )

    objective_count = sum(
        1
        for row in rows
        if row["final_total"] >= args.target_capital
    )

    best_row = max(
        rows,
        key=lambda row: row["final_total"],
    )

    print("\n=== LIMBO100k Protected Session Batch ===")

    print(f"Strategy: {args.strategy}")

    print(
        f"Sessions: "
        f"{args.sessions}"
    )

    print(
        f"Average final total: "
        f"{round(mean(finals), 2)} €"
    )

    print(
        f"Median final total: "
        f"{round(median(finals), 2)} €"
    )

    print(
        f"Objective rate: "
        f"{round((objective_count / args.sessions) * 100, 6)} %"
    )

    print(
        f"Protection reached rate: "
        f"{round((protected_count / args.sessions) * 100, 6)} %"
    )

    print(
        f"Best final total: "
        f"{best_row['final_total']} €"
    )

    print(
        f"Best session index: "
        f"{best_row['session_index']}"
    )

    print(
        f"Best protected amount: "
        f"{best_row['protected']} €"
    )

    print(
        f"Best reason: "
        f"{best_row['reason']}"
    )

    if args.export_csv:

        output_dir = Path("results")

        output_dir.mkdir(exist_ok=True)

        output_path = (
            output_dir
            / f"protected_session_{args.strategy}.csv"
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
