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


def safe_mean(values):

    clean = [
        value
        for value in values
        if value is not None
    ]

    if not clean:
        return None

    return round(mean(clean), 2)


def safe_median(values):

    clean = [
        value
        for value in values
        if value is not None
    ]

    if not clean:
        return None

    return round(median(clean), 2)


def summarize(
    label,
    rows,
):

    if not rows:
        print(f"{label}: count=0")
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
        f"with_d1k10k={len(d1k10k)} | "
        f"with_d10k25k={len(d10k25k)} | "
        f"with_momentum25={len(momentum25)} | "
        f"avg_d1k10k={safe_mean(d1k10k)} | "
        f"median_d1k10k={safe_median(d1k10k)} | "
        f"avg_d10k25k={safe_mean(d10k25k)} | "
        f"median_d10k25k={safe_median(d10k25k)} | "
        f"avg_dd={safe_mean(drawdowns)} | "
        f"median_dd={safe_median(drawdowns)} | "
        f"avg_momentum25={safe_mean(momentum25)} | "
        f"median_momentum25={safe_median(momentum25)}"
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
    near_misses = []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        print("\nDetected CSV columns:")
        print(reader.fieldnames)

        for row in reader:

            profile = row.get("profile")

            r1k = to_float(
                row.get("r_1000")
            )

            r10k = to_float(
                row.get("r_10000")
            )

            r25k = to_float(
                row.get("r_25000")
            )

            d1k10k = None

            if (
                r1k is not None
                and r10k is not None
            ):
                d1k10k = (
                    r10k - r1k
                )

            d10k25k = None

            if (
                r10k is not None
                and r25k is not None
            ):
                d10k25k = (
                    r25k - r10k
                )

            cleaned = {
                "profile": profile,
                "d1k10k": d1k10k,
                "d10k25k": d10k25k,
                "drawdown": to_float(
                    row.get(
                        "max_drawdown"
                    )
                ),
                "momentum25": to_float(
                    row.get(
                        "late_momentum_25"
                    )
                ),
            }

            if profile == "winner":
                winners.append(
                    cleaned
                )

            elif profile == "breakout":
                breakouts.append(
                    cleaned
                )

            elif profile in {
                "near_miss_high",
                "near_miss_mid",
            }:
                near_misses.append(
                    cleaned
                )

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

    summarize(
        "NEAR_MISSES",
        near_misses,
    )

    print(
        "\nHypothesis check:"
    )

    winner_momentum = safe_mean(
        [
            r["momentum25"]
            for r in winners
        ]
    )

    breakout_momentum = safe_mean(
        [
            r["momentum25"]
            for r in breakouts
        ]
    )

    winner_d10k25k = safe_mean(
        [
            r["d10k25k"]
            for r in winners
        ]
    )

    breakout_d10k25k = safe_mean(
        [
            r["d10k25k"]
            for r in breakouts
        ]
    )

    print(
        f"winner_avg_momentum25={winner_momentum}"
    )

    print(
        f"breakout_avg_momentum25={breakout_momentum}"
    )

    print(
        f"winner_avg_d10k25k={winner_d10k25k}"
    )

    print(
        f"breakout_avg_d10k25k={breakout_d10k25k}"
    )

    if (
        winner_momentum is not None
        and breakout_momentum not in (
            None,
            0,
        )
    ):

        print(
            f"momentum_ratio="
            f"{round(winner_momentum / breakout_momentum, 2)}x"
        )

    if (
        winner_d10k25k is not None
        and breakout_d10k25k not in (
            None,
            0,
        )
    ):

        print(
            f"d10k25k_ratio="
            f"{round(winner_d10k25k / breakout_d10k25k, 2)}x"
        )


if __name__ == "__main__":
    main()
