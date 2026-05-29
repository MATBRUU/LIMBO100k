from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from statistics import mean, median

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng
from limbo100k.session_runner import build_agent


THRESHOLDS = {
    "r_1000": 1000,
    "r_10000": 10000,
    "r_25000": 25000,
    "r_50000": 50000,
    "r_100000": 100000,
}


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
        return "breakout"

    if peak_capital > 50:
        return "small_lift"

    return "dead"


def extract_state(agent) -> str:

    state = getattr(agent, "state", None)

    if state is None:
        return "unknown"

    return getattr(state, "value", str(state))


def extract_transitions(agent) -> list[dict]:

    if hasattr(agent, "transitions"):
        return list(agent.transitions)

    if hasattr(agent, "state_transitions"):
        return list(agent.state_transitions)

    return []


def average_or_none(
    values: list[float | int | None],
) -> float | None:

    clean = [
        value
        for value in values
        if value is not None
    ]

    if not clean:
        return None

    return round(mean(clean), 4)


def run_session(
    args: argparse.Namespace,
    local_index: int,
) -> dict:

    real_index = (
        args.seed_offset
        + local_index
    )

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
    lowest = capital

    max_drawdown = 0.0

    reason = "round_limit"

    completed_rounds = 0

    wins = 0
    losses = 0

    longest_win_streak = 0
    longest_loss_streak = 0

    current_win_streak = 0
    current_loss_streak = 0

    threshold_rounds = {
        key: None
        for key in THRESHOLDS
    }

    state_rounds: Counter[str] = Counter()

    state_sequence: list[str] = []

    for round_number in range(1, args.rounds + 1):

        if capital <= 0:
            reason = "capital_floor"
            break

        if capital >= args.target_capital:
            reason = "objective_reached"
            break

        current_state = extract_state(agent)

        state_rounds[current_state] += 1

        if (
            not state_sequence
            or state_sequence[-1] != current_state
        ):
            state_sequence.append(current_state)

        amount, target = agent.next_bet(capital)

        if amount <= 0:
            reason = "no_amount"
            break

        result = engine.play(
            stake=amount,
            target_multiplier=target,
        )

        capital += result.profit

        completed_rounds += 1

        peak = max(peak, capital)

        lowest = min(lowest, capital)

        max_drawdown = max(
            max_drawdown,
            peak - capital,
        )

        for key, threshold in THRESHOLDS.items():

            if (
                threshold_rounds[key] is None
                and capital >= threshold
            ):
                threshold_rounds[key] = round_number

        if result.won:

            wins += 1

            current_win_streak += 1

            current_loss_streak = 0

            longest_win_streak = max(
                longest_win_streak,
                current_win_streak,
            )

        else:

            losses += 1

            current_loss_streak += 1

            current_win_streak = 0

            longest_loss_streak = max(
                longest_loss_streak,
                current_loss_streak,
            )

        if hasattr(agent, "observe"):
            agent.observe(
                result.won,
                capital,
            )

    final_capital = round(capital, 2)

    peak_capital = round(peak, 2)

    transitions = extract_transitions(agent)

    state_path = ">".join(state_sequence)

    transition_path = ">".join(
        f"{item.get('from')}:{item.get('to')}"
        for item in transitions
    )

    return {
        "session_index": real_index,
        "profile": classify(
            final_capital,
            peak_capital,
            args.target_capital,
        ),
        "final_capital": final_capital,
        "peak_capital": peak_capital,
        "lowest_capital": round(lowest, 2),
        "total_rounds": completed_rounds,
        "stop_reason": reason,
        "max_drawdown": round(max_drawdown, 2),
        "wins": wins,
        "losses": losses,
        "longest_win_streak": longest_win_streak,
        "longest_loss_streak": longest_loss_streak,
        "transition_count": len(transitions),
        "transition_path": transition_path,
        "state_path": state_path,
        "state_rounds": dict(state_rounds),
        "r_1000": threshold_rounds["r_1000"],
        "r_10000": threshold_rounds["r_10000"],
        "r_25000": threshold_rounds["r_25000"],
        "r_50000": threshold_rounds["r_50000"],
        "r_100000": threshold_rounds["r_100000"],
        "d_1k_10k": None
        if (
            threshold_rounds["r_1000"] is None
            or threshold_rounds["r_10000"] is None
        )
        else (
            threshold_rounds["r_10000"]
            - threshold_rounds["r_1000"]
        ),
        "d_10k_25k": None
        if (
            threshold_rounds["r_10000"] is None
            or threshold_rounds["r_25000"] is None
        )
        else (
            threshold_rounds["r_25000"]
            - threshold_rounds["r_10000"]
        ),
    }


def summarize(rows: list[dict]) -> None:

    print(
        "\n=== LIMBO100k State Transition Analyzer ==="
    )

    print(
        f"Analyzed sessions: "
        f"{len(rows)}"
    )

    profiles = sorted(
        set(row["profile"] for row in rows)
    )

    for profile in profiles:

        subset = [
            row
            for row in rows
            if row["profile"] == profile
        ]

        finals = [
            row["final_capital"]
            for row in subset
        ]

        peaks = [
            row["peak_capital"]
            for row in subset
        ]

        drawdowns = [
            row["max_drawdown"]
            for row in subset
        ]

        transitions = [
            row["transition_count"]
            for row in subset
        ]

        print(
            f"{profile}: "
            f"count={len(subset)} | "
            f"avg_final={round(mean(finals), 2)} € | "
            f"median_final={round(median(finals), 2)} € | "
            f"avg_peak={round(mean(peaks), 2)} € | "
            f"avg_dd={round(mean(drawdowns), 2)} € | "
            f"avg_transitions={round(mean(transitions), 2)} | "
            f"avg_d1k10k={average_or_none([row['d_1k_10k'] for row in subset])} | "
            f"avg_d10k25k={average_or_none([row['d_10k_25k'] for row in subset])}"
        )

    winner_paths = Counter(
        row["state_path"]
        for row in rows
        if row["profile"] == "winner"
    )

    near_paths = Counter(
        row["state_path"]
        for row in rows
        if row["profile"] in {
            "near_miss_high",
            "near_miss_mid",
        }
    )

    print("\nTop winner state paths:")

    for path, count in winner_paths.most_common(10):

        print(
            f"count={count} | {path}"
        )

    print("\nTop near-miss state paths:")

    for path, count in near_paths.most_common(10):

        print(
            f"count={count} | {path}"
        )

    print("\nTop 20 trajectories:")

    top = sorted(
        rows,
        key=lambda row: row["final_capital"],
        reverse=True,
    )[:20]

    for row in top:

        print(
            f"index={row['session_index']} | "
            f"profile={row['profile']} | "
            f"final={row['final_capital']} € | "
            f"peak={row['peak_capital']} € | "
            f"rounds={row['total_rounds']} | "
            f"transitions={row['transition_count']} | "
            f"r1k={row['r_1000']} | "
            f"r10k={row['r_10000']} | "
            f"r25k={row['r_25000']} | "
            f"r100k={row['r_100000']} | "
            f"d1k10k={row['d_1k_10k']} | "
            f"d10k25k={row['d_10k_25k']} | "
            f"dd={row['max_drawdown']} € | "
            f"states={row['state_path']}"
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Analyze internal state transitions"
    )

    parser.add_argument(
        "--strategy",
        default="phase_state_v2",
        choices=[
            "phase_state",
            "phase_state_v2",
            "phase_state_v21",
            "phase_state_v22",
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
        "--export-csv",
        action="store_true",
    )

    args = parser.parse_args()

    rows = []

    for local_index in range(args.sessions):

        rows.append(
            run_session(
                args,
                local_index,
            )
        )

        if (local_index + 1) % 1000 == 0:

            print(
                f"Analyzed "
                f"{local_index + 1}/"
                f"{args.sessions} sessions"
            )

    summarize(rows)

    if args.export_csv:

        output_dir = Path("results")

        output_dir.mkdir(exist_ok=True)

        output_path = (
            output_dir
            / f"state_transition_analyzer_{args.strategy}.csv"
        )

        export_rows = []

        for row in rows:

            cleaned = dict(row)

            cleaned["state_rounds"] = str(
                cleaned["state_rounds"]
            )

            export_rows.append(cleaned)

        with output_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=list(export_rows[0].keys()),
            )

            writer.writeheader()

            writer.writerows(export_rows)

        print(
            f"\nCSV exported to: "
            f"{output_path}"
        )


if __name__ == "__main__":
    main()
