from __future__ import annotations

import argparse
import csv
from pathlib import Path

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng
from limbo100k.session_runner import build_agent


def replay_session(
    strategy: str,
    session_index: int,
    initial_capital: float,
    target_capital: float,
    stake: float,
    multiplier: float,
    fraction: float,
    rounds: int,
) -> list[dict]:
    rng = ProvablyFairRng(
        server_seed=f"FREE_SERVER_{strategy}_{session_index}",
        client_seed=f"FREE_CLIENT_{strategy}_{session_index}",
    )
    engine = LimboEngine(rng=rng)
    agent = build_agent(strategy, stake, multiplier, fraction)

    capital = initial_capital
    peak = initial_capital
    rows: list[dict] = []

    for round_number in range(1, rounds + 1):
        if capital <= 0 or capital >= target_capital:
            break

        amount, target = agent.next_bet(capital)
        if amount <= 0:
            break

        result = engine.play(stake=amount, target_multiplier=target)
        capital += result.profit
        peak = max(peak, capital)

        if hasattr(agent, "observe"):
            agent.observe(result.won, capital)

        rows.append(
            {
                "round": round_number,
                "nonce": result.nonce,
                "stake": round(amount, 2),
                "target_multiplier": round(target, 4),
                "rolled_multiplier": round(result.rolled_multiplier, 4),
                "outcome": "success" if result.won else "failure",
                "profit": round(result.profit, 2),
                "capital": round(capital, 2),
                "peak": round(peak, 2),
                "drawdown": round(peak - capital, 2),
                "server_seed_hash": result.proof.server_seed_hash,
                "digest": result.proof.digest,
            }
        )

    return rows


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Replay a LIMBO100k session"
    )

    parser.add_argument(
        "--strategy",
        default="phase",
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
        "--session-index",
        type=int,
        required=True,
    )

    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--export-csv", action="store_true")

    args = parser.parse_args()

    rows = replay_session(
        strategy=args.strategy,
        session_index=args.session_index,
        initial_capital=args.initial_capital,
        target_capital=args.target_capital,
        stake=args.stake,
        multiplier=args.multiplier,
        fraction=args.risk_fraction,
        rounds=args.rounds,
    )

    if not rows:
        print("No rounds executed.")
        return

    print("\n=== LIMBO100k Session Replay ===")
    print(f"Strategy: {args.strategy}")
    print(f"Session index: {args.session_index}")
    print(f"Rounds replayed: {len(rows)}")
    print(f"Final capital: {rows[-1]['capital']} €")
    print(f"Peak capital: {max(row['peak'] for row in rows)} €")
    print(f"Final outcome: {rows[-1]['outcome']}")
    print(f"Server seed hash: {rows[0]['server_seed_hash']}")

    print("\nLast 20 rounds:")
    for row in rows[-20:]:
        print(
            f"#{row['round']} | stake={row['stake']} € | "
            f"target=x{row['target_multiplier']} | roll=x{row['rolled_multiplier']} | "
            f"{row['outcome']} | capital={row['capital']} €"
        )

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"replay_{args.strategy}_{args.session_index}.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
