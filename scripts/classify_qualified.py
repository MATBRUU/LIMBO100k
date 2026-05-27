from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from replay_session import replay_session


LEVELS = [100, 500, 1000, 5000, 10000, 25000, 50000, 75000, 100000]


def load_rows(path: Path, limit: int | None) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    return rows[:limit] if limit else rows


def first_crossing(rows: list[dict], level: float) -> int | None:
    for row in rows:
        if float(row["capital"]) >= level:
            return int(row["round"])
    return None


def max_drop(rows: list[dict]) -> float:
    peak = 0.0
    largest = 0.0
    for row in rows:
        capital = float(row["capital"])
        peak = max(peak, capital)
        largest = max(largest, peak - capital)
    return round(largest, 2)


def biggest_gain(rows: list[dict]) -> float:
    best = 0.0
    for row in rows:
        best = max(best, float(row["profit"]))
    return round(best, 2)


def classify_profile(crossings: dict[str, int | None], final_capital: float) -> str:
    r100 = crossings.get("100")
    r1000 = crossings.get("1000")
    r10000 = crossings.get("10000")
    r50000 = crossings.get("50000")

    if final_capital >= 100000:
        if r10000 is not None and r10000 <= 150:
            return "early_explosion"
        if r1000 is not None and r1000 <= 250 and r50000 is not None and r50000 > 500:
            return "stair_step"
        if r10000 is not None and r10000 > 400:
            return "late_breakout"
        return "winning_mixed"

    if r50000 is not None:
        return "near_miss_high"
    if r10000 is not None:
        return "near_miss_mid"
    if r1000 is not None:
        return "minor_breakout"
    if r100 is not None:
        return "small_lift"
    return "flat_or_dead"


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify qualified LIMBO100k trajectories")
    parser.add_argument("--input", default="results/qualified_sample.csv")
    parser.add_argument("--strategy", default="phase")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--stake", type=float, default=1.0)
    parser.add_argument("--multiplier", type=float, default=5.0)
    parser.add_argument("--risk-fraction", type=float, default=0.18)
    parser.add_argument("--rounds", type=int, default=5000)
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    source_rows = load_rows(input_path, args.limit)
    classified = []
    profile_counts = Counter()

    for item in source_rows:
        session_index = int(item["session_index"])
        replay_rows = replay_session(
            strategy=args.strategy,
            session_index=session_index,
            initial_capital=args.initial_capital,
            target_capital=args.target_capital,
            stake=args.stake,
            multiplier=args.multiplier,
            fraction=args.risk_fraction,
            rounds=args.rounds,
        )

        if not replay_rows:
            continue

        crossings = {str(level): first_crossing(replay_rows, level) for level in LEVELS}
        final_capital = float(replay_rows[-1]["capital"])
        peak = max(float(row["peak"]) for row in replay_rows)
        profile = classify_profile(crossings, final_capital)
        profile_counts[profile] += 1

        classified.append(
            {
                "session_index": session_index,
                "profile": profile,
                "final_capital": round(final_capital, 2),
                "peak": round(peak, 2),
                "rounds": len(replay_rows),
                "max_drop": max_drop(replay_rows),
                "biggest_gain": biggest_gain(replay_rows),
                "round_to_100": crossings["100"],
                "round_to_1000": crossings["1000"],
                "round_to_10000": crossings["10000"],
                "round_to_50000": crossings["50000"],
                "round_to_100000": crossings["100000"],
            }
        )

        if len(classified) % 100 == 0:
            print(f"Classified {len(classified)}/{len(source_rows)}")

    print("\n=== LIMBO100k Trajectory Classification ===")
    print(f"Input rows: {len(source_rows)}")
    print(f"Classified rows: {len(classified)}")
    print("\nProfiles:")
    for profile, count in profile_counts.most_common():
        print(f"{profile}: {count}")

    print("\nTop 20 by final capital:")
    for row in sorted(classified, key=lambda item: item["final_capital"], reverse=True)[:20]:
        print(
            f"index={row['session_index']} | profile={row['profile']} | "
            f"final={row['final_capital']} € | peak={row['peak']} € | "
            f"r1000={row['round_to_1000']} | r10000={row['round_to_10000']} | "
            f"r100000={row['round_to_100000']}"
        )

    if args.export_csv and classified:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "classified_qualified.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(classified[0].keys()))
            writer.writeheader()
            writer.writerows(classified)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
