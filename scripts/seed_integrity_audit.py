from __future__ import annotations

import argparse
from collections import Counter
from statistics import mean, median

from run_free_agent import run_one_session
from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng
from limbo100k.session_runner import build_agent


def make_seeds(strategy: str, index: int) -> tuple[str, str]:
    return (
        f"FREE_SERVER_{strategy}_{index}",
        f"FREE_CLIENT_{strategy}_{index}",
    )


def audit_seed_uniqueness(strategy: str, start: int, sessions: int) -> dict:
    server_seen = set()
    client_seen = set()
    pair_seen = set()
    server_collisions = 0
    client_collisions = 0
    pair_collisions = 0

    for index in range(start, start + sessions):
        server_seed, client_seed = make_seeds(strategy, index)
        pair = (server_seed, client_seed)

        if server_seed in server_seen:
            server_collisions += 1
        if client_seed in client_seen:
            client_collisions += 1
        if pair in pair_seen:
            pair_collisions += 1

        server_seen.add(server_seed)
        client_seen.add(client_seed)
        pair_seen.add(pair)

    return {
        "server_collisions": server_collisions,
        "client_collisions": client_collisions,
        "pair_collisions": pair_collisions,
        "unique_servers": len(server_seen),
        "unique_clients": len(client_seen),
        "unique_pairs": len(pair_seen),
    }


def replay_signature(
    strategy: str,
    session_index: int,
    initial_capital: float,
    target_capital: float,
    stake: float,
    multiplier: float,
    fraction: float,
    rounds: int,
) -> tuple:
    final_capital, completed_rounds, reason = run_one_session(
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
    return final_capital, completed_rounds, reason


def audit_replay(args: argparse.Namespace, indexes: list[int]) -> list[dict]:
    mismatches = []

    for index in indexes:
        first = replay_signature(
            args.strategy,
            index,
            args.initial_capital,
            args.target_capital,
            args.stake,
            args.multiplier,
            args.risk_fraction,
            args.rounds,
        )
        second = replay_signature(
            args.strategy,
            index,
            args.initial_capital,
            args.target_capital,
            args.stake,
            args.multiplier,
            args.risk_fraction,
            args.rounds,
        )

        if first != second:
            mismatches.append(
                {
                    "index": index,
                    "first": first,
                    "second": second,
                }
            )

    return mismatches


def run_detailed_session(args: argparse.Namespace, index: int) -> dict:
    server_seed, client_seed = make_seeds(args.strategy, index)
    rng = ProvablyFairRng(server_seed=server_seed, client_seed=client_seed)
    engine = LimboEngine(rng=rng)
    agent = build_agent(args.strategy, args.stake, args.multiplier, args.risk_fraction)

    capital = args.initial_capital
    peak = capital
    lows = []
    rolls = []
    reason = "round_limit"
    completed = 0

    for _ in range(args.rounds):
        if capital <= 0:
            reason = "capital_floor"
            break
        if capital >= args.target_capital:
            reason = "objective_reached"
            break

        amount, target = agent.next_bet(capital)
        if amount <= 0:
            reason = "no_amount"
            break

        result = engine.play(stake=amount, target_multiplier=target)
        rolls.append(round(result.rolled_multiplier, 8))
        capital += result.profit
        peak = max(peak, capital)
        lows.append(capital)
        completed += 1

        if hasattr(agent, "observe"):
            agent.observe(result.won, capital)

    return {
        "index": index,
        "final": round(capital, 2),
        "peak": round(peak, 2),
        "rounds": completed,
        "reason": reason,
        "roll_head": tuple(rolls[:10]),
        "roll_tail": tuple(rolls[-10:]),
    }


def audit_neighbors(args: argparse.Namespace, winner_indexes: list[int], radius: int) -> list[dict]:
    rows = []
    seen = set()

    for winner in winner_indexes:
        for index in range(max(0, winner - radius), winner + radius + 1):
            if index in seen:
                continue
            seen.add(index)
            row = run_detailed_session(args, index)
            row["near_winner"] = winner
            row["distance"] = index - winner
            rows.append(row)

    return rows


def scan_ranges(args: argparse.Namespace) -> tuple[list[dict], list[int]]:
    rows = []
    winners = []
    total_ranges = (args.sessions + args.range_size - 1) // args.range_size

    for range_number in range(total_ranges):
        start = args.seed_offset + range_number * args.range_size
        stop = min(start + args.range_size, args.seed_offset + args.sessions)
        finals = []
        range_winners = 0
        range_best = float("-inf")
        range_best_index = start

        for index in range(start, stop):
            final_capital, _, reason = run_one_session(
                strategy=args.strategy,
                initial_capital=args.initial_capital,
                target_capital=args.target_capital,
                stake=args.stake,
                multiplier=args.multiplier,
                fraction=args.risk_fraction,
                rounds=args.rounds,
                session_index=index,
                seed_offset=0,
            )
            finals.append(final_capital)
            if reason == "objective_reached" or final_capital >= args.target_capital:
                range_winners += 1
                winners.append(index)
            if final_capital > range_best:
                range_best = final_capital
                range_best_index = index

        rows.append(
            {
                "range": range_number + 1,
                "start": start,
                "stop": stop - 1,
                "sessions": stop - start,
                "winners": range_winners,
                "average": round(mean(finals), 2),
                "median": round(median(finals), 2),
                "best": round(range_best, 2),
                "best_index": range_best_index,
            }
        )
        print(
            f"Range {range_number + 1}/{total_ranges} | "
            f"start={start} | winners={range_winners} | "
            f"best={round(range_best, 2)} € | best_index={range_best_index}"
        )

    return rows, winners


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit seed integrity and locality")
    parser.add_argument("--strategy", default="phase_state_v2")
    parser.add_argument("--sessions", type=int, default=100000)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--range-size", type=int, default=10000)
    parser.add_argument("--neighbor-radius", type=int, default=3)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    args = parser.parse_args()

    print("\n=== LIMBO100k Seed Integrity Audit ===")
    print(f"Strategy: {args.strategy}")
    print(f"Sessions: {args.sessions}")
    print(f"Seed offset: {args.seed_offset}")

    uniqueness = audit_seed_uniqueness(args.strategy, args.seed_offset, args.sessions)
    print("\nSeed uniqueness:")
    for key, value in uniqueness.items():
        print(f"{key}: {value}")

    ranges, winners = scan_ranges(args)

    replay_indexes = winners[:20]
    if not replay_indexes:
        replay_indexes = [args.seed_offset, args.seed_offset + 1, args.seed_offset + 2]

    replay_mismatches = audit_replay(args, replay_indexes)
    print("\nReplay consistency:")
    print(f"checked_indexes: {replay_indexes}")
    print(f"mismatches: {len(replay_mismatches)}")
    if replay_mismatches:
        print(replay_mismatches[:10])

    winner_mods = Counter(index % args.range_size for index in winners)
    print("\nWinner distribution:")
    print(f"winner_count: {len(winners)}")
    print(f"winner_indexes: {winners[:100]}")
    print(f"winner_mod_duplicates_top10: {winner_mods.most_common(10)}")

    if winners:
        gaps = [b - a for a, b in zip(winners, winners[1:])]
        if gaps:
            print(f"winner_gap_avg: {round(mean(gaps), 2)}")
            print(f"winner_gap_median: {round(median(gaps), 2)}")
            print(f"winner_gap_min: {min(gaps)}")
            print(f"winner_gap_max: {max(gaps)}")

    neighbor_rows = audit_neighbors(args, winners[:10], args.neighbor_radius)
    print("\nNeighbor audit around first winners:")
    for row in neighbor_rows[:100]:
        print(
            f"winner={row['near_winner']} | index={row['index']} | "
            f"dist={row['distance']} | final={row['final']} € | "
            f"peak={row['peak']} € | reason={row['reason']} | rounds={row['rounds']}"
        )

    print("\nVerdict helpers:")
    if all(value == 0 for key, value in uniqueness.items() if "collisions" in key):
        print("seed_collision_status: PASS")
    else:
        print("seed_collision_status: FAIL")

    print("replay_status: PASS" if not replay_mismatches else "replay_status: FAIL")


if __name__ == "__main__":
    main()
