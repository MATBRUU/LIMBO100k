from __future__ import annotations

import argparse
import csv
from pathlib import Path

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng
from limbo100k.session_runner import build_agent


THRESHOLDS = [1000, 10000, 25000, 50000, 100000]


def parse_indexes(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def get_state(agent) -> str:
    state = getattr(agent, "state", None)
    if state is None:
        return "unknown"
    return getattr(state, "value", str(state))


def get_agent_value(agent, name: str):
    value = getattr(agent, name, None)
    if isinstance(value, float):
        return round(value, 6)
    return value


def classify_winner_shape(row: dict) -> str:
    max_drawdown = row["max_drawdown"]
    d1 = row["d_1k_10k"]
    d2 = row["d_10k_25k"]

    if max_drawdown <= 5000 and d2 is not None and d2 <= 3:
        return "clean_direct_hyper"
    if max_drawdown >= 25000 and d2 is not None and d2 <= 5:
        return "chaotic_re_density"
    if d1 is not None and d1 <= 5:
        return "fast_breakout"
    if d2 is not None and d2 <= 5:
        return "post_10k_density"
    return "slow_convex_survivor"


def replay_session(args: argparse.Namespace, session_index: int) -> tuple[dict, list[dict]]:
    rng = ProvablyFairRng(
        server_seed=f"FREE_SERVER_{args.strategy}_{session_index}",
        client_seed=f"FREE_CLIENT_{args.strategy}_{session_index}",
    )
    engine = LimboEngine(rng=rng)
    agent = build_agent(args.strategy, args.stake, args.multiplier, args.risk_fraction)

    capital = args.initial_capital
    peak = capital
    lowest = capital
    max_drawdown = 0.0
    threshold_rounds = {threshold: None for threshold in THRESHOLDS}
    history: list[dict] = []
    reason = "round_limit"
    wins = 0
    losses = 0
    current_win_streak = 0
    current_loss_streak = 0
    longest_win_streak = 0
    longest_loss_streak = 0

    for round_number in range(1, args.rounds + 1):
        if capital <= 0:
            reason = "capital_floor"
            break
        if capital >= args.target_capital:
            reason = "objective_reached"
            break

        state_before = get_state(agent)
        fraction_before = get_agent_value(agent, "fraction")
        multiplier_before = get_agent_value(agent, "multiplier")
        up_before = get_agent_value(agent, "up")
        down_before = get_agent_value(agent, "down")

        stake, target = agent.next_bet(capital)
        if stake <= 0:
            reason = "no_amount"
            break

        state_after_decision = get_state(agent)
        fraction_after_decision = get_agent_value(agent, "fraction")
        multiplier_after_decision = get_agent_value(agent, "multiplier")

        result = engine.play(stake=stake, target_multiplier=target)
        previous_capital = capital
        capital += result.profit
        peak = max(peak, capital)
        lowest = min(lowest, capital)
        drawdown = peak - capital
        max_drawdown = max(max_drawdown, drawdown)

        for threshold in THRESHOLDS:
            if threshold_rounds[threshold] is None and capital >= threshold:
                threshold_rounds[threshold] = round_number

        if result.won:
            wins += 1
            current_win_streak += 1
            current_loss_streak = 0
            longest_win_streak = max(longest_win_streak, current_win_streak)
        else:
            losses += 1
            current_loss_streak += 1
            current_win_streak = 0
            longest_loss_streak = max(longest_loss_streak, current_loss_streak)

        if hasattr(agent, "observe"):
            agent.observe(result.won, capital)

        state_after_observe = get_state(agent)
        fraction_after_observe = get_agent_value(agent, "fraction")
        multiplier_after_observe = get_agent_value(agent, "multiplier")

        history.append(
            {
                "session_index": session_index,
                "round": round_number,
                "state_before": state_before,
                "state_after_decision": state_after_decision,
                "state_after_observe": state_after_observe,
                "capital_before": round(previous_capital, 2),
                "stake": round(stake, 2),
                "target": round(target, 6),
                "roll": round(result.rolled_multiplier, 6),
                "outcome": "success" if result.won else "failure",
                "profit": round(result.profit, 2),
                "capital_after": round(capital, 2),
                "peak": round(peak, 2),
                "drawdown": round(drawdown, 2),
                "fraction_before": fraction_before,
                "fraction_after_decision": fraction_after_decision,
                "fraction_after_observe": fraction_after_observe,
                "multiplier_before": multiplier_before,
                "multiplier_after_decision": multiplier_after_decision,
                "multiplier_after_observe": multiplier_after_observe,
                "up_before": up_before,
                "down_before": down_before,
                "current_win_streak": current_win_streak,
                "current_loss_streak": current_loss_streak,
            }
        )

    d1 = None
    if threshold_rounds[1000] is not None and threshold_rounds[10000] is not None:
        d1 = threshold_rounds[10000] - threshold_rounds[1000]

    d2 = None
    if threshold_rounds[10000] is not None and threshold_rounds[25000] is not None:
        d2 = threshold_rounds[25000] - threshold_rounds[10000]

    summary = {
        "session_index": session_index,
        "final_capital": round(capital, 2),
        "peak_capital": round(peak, 2),
        "lowest_capital": round(lowest, 2),
        "rounds": len(history),
        "reason": reason,
        "wins": wins,
        "losses": losses,
        "longest_win_streak": longest_win_streak,
        "longest_loss_streak": longest_loss_streak,
        "max_drawdown": round(max_drawdown, 2),
        "r_1000": threshold_rounds[1000],
        "r_10000": threshold_rounds[10000],
        "r_25000": threshold_rounds[25000],
        "r_50000": threshold_rounds[50000],
        "r_100000": threshold_rounds[100000],
        "d_1k_10k": d1,
        "d_10k_25k": d2,
        "transitions": str(getattr(agent, "transitions", getattr(agent, "state_transitions", []))),
    }
    summary["shape"] = classify_winner_shape(summary)

    return summary, history


def print_compact_autopsy(summary: dict, history: list[dict], tail: int) -> None:
    print("\n=== Winner Autopsy ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nKey threshold rounds:")
    print(
        f"1k={summary['r_1000']} | 10k={summary['r_10000']} | "
        f"25k={summary['r_25000']} | 50k={summary['r_50000']} | 100k={summary['r_100000']}"
    )

    print(f"\nLast {tail} rounds:")
    for row in history[-tail:]:
        print(
            f"#{row['round']} | state={row['state_after_decision']}->{row['state_after_observe']} | "
            f"capital={row['capital_before']}→{row['capital_after']} € | "
            f"stake={row['stake']} € | target=x{row['target']} | roll=x{row['roll']} | "
            f"{row['outcome']} | dd={row['drawdown']} € | "
            f"fraction={row['fraction_after_observe']} | mult={row['multiplier_after_observe']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay and autopsy specific winner sessions")
    parser.add_argument("--strategy", default="phase_state_v2")
    parser.add_argument(
        "--indexes",
        default="241759,289130,231325,32409,8516,43417",
        help="Comma-separated absolute session indexes",
    )
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--tail", type=int, default=25)
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    indexes = parse_indexes(args.indexes)
    summaries = []
    all_history = []

    for index in indexes:
        summary, history = replay_session(args, index)
        summaries.append(summary)
        all_history.extend(history)
        print_compact_autopsy(summary, history, args.tail)

    print("\n=== Shape Summary ===")
    for summary in summaries:
        print(
            f"index={summary['session_index']} | shape={summary['shape']} | "
            f"final={summary['final_capital']} € | dd={summary['max_drawdown']} € | "
            f"d1={summary['d_1k_10k']} | d2={summary['d_10k_25k']} | "
            f"wins={summary['wins']} | losses={summary['losses']}"
        )

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)

        summary_path = output_dir / f"winner_autopsy_summary_{args.strategy}.csv"
        with summary_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(summaries[0].keys()))
            writer.writeheader()
            writer.writerows(summaries)

        history_path = output_dir / f"winner_autopsy_rounds_{args.strategy}.csv"
        with history_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(all_history[0].keys()))
            writer.writeheader()
            writer.writerows(all_history)

        print(f"\nCSV exported to: {summary_path}")
        print(f"CSV exported to: {history_path}")


if __name__ == "__main__":
    main()
