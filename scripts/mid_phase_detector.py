from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median


def to_float(value):

    if value in ("", "None", None):
        return None

    try:
        return float(value)
    except ValueError:
        return None


def summarize(label, rows):

    if not rows:
        return

    d1k10k = [
        r["d1k10k"]
        for r in rows
        if r["d1k10k"] is not None
    ]

    d10k25k = [
        r["d10k25k"]
        for r in rows
        if r["d10k25k"] is not None
    ]

    drawdowns = [
        r["drawdown"]
        for r in rows
        if r["drawdown"] is not None
    ]

    momentum25 = [
        r["momentum25"]
        for r in rows
        if r["momentum25"] is not None
    ]

    print(
        f"{label}: "
        f"count={len(rows)} | "
        f"avg_d1k10k={round(mean(d1k10k),2) if d1k10k else None} | "
        f"median_d1k10k={round(median(d1k10k),2) if d1k10k else None} | "
        f"avg_d10k25k={round(mean(d10k25k),2) if d10k25k else None} | "
        f"median_d10k25k={round(median(d10k25k),2) if d10k25k else None} | "
        f"avg_dd={round(mean(drawdowns),2) if drawdowns else None} | "
        f"median_dd={round(median(drawdowns),2) if drawdowns else None} | "
        f"avg_momentum25={round(mean(momentum25),2) if momentum25 else None} | "
        f"median_momentum25={round(median(momentum25),2) if momentum25 else None}"
    )


def main():

    parser = argparse.ArgumentParser(
        description="Winner vs Breakout Mid Phase Analysis"
    )

    parser.add_argument(
        "--input",
        default="results/trajectory_analyzer_phase_state_v2.csv",
    )

    args = parser.parse_args()

    path = Path(args.input)

    winners = []
    breakouts = []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            profile = row["profile"]

            cleaned = {
                "d1k10k": to_float(
                    row.get("d1k10k")
                ),
                "d10k25k": to_float(
                    row.get("d10k25k")
                ),
                "drawdown": to_float(
                    row.get("max_drawdown")
                ),
                "momentum25": to_float(
                    row.get("momentum25")
                ),
            }

            if profile == "winner":
                winners.append(cleaned)

            elif profile == "breakout":
                breakouts.append(cleaned)

    print(
        "\n=== LIMBO100k Mid Phase Detector ==="
    )

    summarize(
        "WINNERS",
        winners,
    )

    summarize(
        "BREAKOUTS",
        breakouts,
    )

    print("\nHypothesis check:")

    if winners and breakouts:

        winner_momentum = mean(
            r["momentum25"]
            for r in winners
            if r["momentum25"] is not None
        )

        breakout_momentum = mean(
            r["momentum25"]
            for r in breakouts
            if r["momentum25"] is not None
        )

        print(
            f"Momentum ratio = "
            f"{round(winner_momentum / breakout_momentum, 2)}x"
        )


if __name__ == "__main__":
    main()
