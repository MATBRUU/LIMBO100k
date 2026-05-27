from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median


def to_float(value: str) -> float | None:
    if value in {"", "None", "none", "null"}:
        return None
    return float(value)


def to_int(value: str) -> int | None:
    if value in {"", "None", "none", "null"}:
        return None
    return int(float(value))


def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def enrich(row: dict) -> dict:
    r1k = to_int(row.get("r_1000", ""))
    r10k = to_int(row.get("r_10000", ""))
    r25k = to_int(row.get("r_25000", ""))
    r100k = to_int(row.get("r_100000", ""))
    peak = to_float(row.get("peak_capital", "0")) or 0.0
    final = to_float(row.get("final_capital", "0")) or 0.0
    rounds = to_int(row.get("total_rounds", "0")) or 0
    wins = to_int(row.get("longest_win_streak", "0")) or 0
    losses = to_int(row.get("longest_loss_streak", "0")) or 0
    drawdown = to_float(row.get("max_drawdown", "0")) or 0.0
    momentum25 = to_float(row.get("late_momentum_25", "0")) or 0.0

    density_1k_10k = None if r1k is None or r10k is None else r10k - r1k
    density_10k_25k = None if r10k is None or r25k is None else r25k - r10k
    density_25k_100k = None if r25k is None or r100k is None else r100k - r25k

    return {
        **row,
        "r1k": r1k,
        "r10k": r10k,
        "r25k": r25k,
        "r100k": r100k,
        "peak": peak,
        "final": final,
        "rounds": rounds,
        "wins": wins,
        "losses": losses,
        "drawdown": drawdown,
        "momentum25": momentum25,
        "density_1k_10k": density_1k_10k,
        "density_10k_25k": density_10k_25k,
        "density_25k_100k": density_25k_100k,
    }


def avg(values: list[float | int | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(mean(clean), 4)


def med(values: list[float | int | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(median(clean), 4)


def summarize_group(name: str, rows: list[dict]) -> None:
    if not rows:
        return

    print(
        f"{name}: count={len(rows)} | "
        f"avg_peak={round(mean(row['peak'] for row in rows), 2)} € | "
        f"avg_final={round(mean(row['final'] for row in rows), 2)} € | "
        f"avg_r1k={avg([row['r1k'] for row in rows])} | "
        f"avg_1k_10k={avg([row['density_1k_10k'] for row in rows])} | "
        f"median_1k_10k={med([row['density_1k_10k'] for row in rows])} | "
        f"avg_wins={round(mean(row['wins'] for row in rows), 2)} | "
        f"avg_losses={round(mean(row['losses'] for row in rows), 2)} | "
        f"avg_dd={round(mean(row['drawdown'] for row in rows), 2)} €"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze breakout density from trajectory analyzer CSV")
    parser.add_argument("--input", default="results/trajectory_analyzer_momentum_phase.csv")
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    path = Path(args.input)
    rows = [enrich(row) for row in load_rows(path)]
    breakouts = [row for row in rows if row["r1k"] is not None]
    winners = [row for row in breakouts if row.get("profile") == "winner"]
    near_misses = [row for row in breakouts if row.get("profile") in {"near_miss_high", "near_miss_mid"}]
    dead_breakouts = [row for row in breakouts if row.get("profile") == "breakout"]
    fast_density = [row for row in breakouts if row["density_1k_10k"] is not None and row["density_1k_10k"] <= 5]

    print("\n=== LIMBO100k Breakout Density Analysis ===")
    print(f"Input: {path}")
    print(f"Total rows: {len(rows)}")
    print(f"Breakouts reaching 1k: {len(breakouts)}")
    print(f"Winners among breakouts: {len(winners)}")
    print(f"Conversion 1k -> 100k: {round((len(winners) / len(breakouts)) * 100, 6) if breakouts else 0} %")
    print(f"Fast 1k->10k density <= 5 rounds: {len(fast_density)}")

    print("\nBy profile:")
    summarize_group("winner", winners)
    summarize_group("near_miss", near_misses)
    summarize_group("dead_breakout", dead_breakouts)
    summarize_group("fast_density", fast_density)

    print("\nTop density trajectories with r1k and r10k:")
    ranked = sorted(
        [row for row in breakouts if row["density_1k_10k"] is not None],
        key=lambda row: (row["density_1k_10k"], -row["peak"]),
    )[: args.top]

    for row in ranked:
        print(
            f"index={row['session_index']} | profile={row['profile']} | "
            f"peak={round(row['peak'], 2)} € | final={round(row['final'], 2)} € | "
            f"r1k={row['r1k']} | r10k={row['r10k']} | r25k={row['r25k']} | r100k={row['r100k']} | "
            f"d1k10k={row['density_1k_10k']} | d10k25k={row['density_10k_25k']} | "
            f"wins={row['wins']} | losses={row['losses']} | dd={round(row['drawdown'], 2)} €"
        )


if __name__ == "__main__":
    main()
