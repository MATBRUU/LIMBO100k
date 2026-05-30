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
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(mean(clean), 2)


def safe_median(values):
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(median(clean), 2)


def pct(values, threshold, mode="le"):
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    if mode == "le":
        count = sum(1 for value in clean if value <= threshold)
    else:
        count = sum(1 for value in clean if value >= threshold)
    return round((count / len(clean)) * 100, 2)


def enrich(row):
    r1k = to_float(row.get("r_1000"))
    r10k = to_float(row.get("r_10000"))
    r25k = to_float(row.get("r_25000"))
    r50k = to_float(row.get("r_50000"))
    r100k = to_float(row.get("r_100000"))

    d1k10k = None
    if r1k is not None and r10k is not None:
        d1k10k = r10k - r1k

    d10k25k = None
    if r10k is not None and r25k is not None:
        d10k25k = r25k - r10k

    d25k50k = None
    if r25k is not None and r50k is not None:
        d25k50k = r50k - r25k

    d50k100k = None
    if r50k is not None and r100k is not None:
        d50k100k = r100k - r50k

    d25k100k = None
    if r25k is not None and r100k is not None:
        d25k100k = r100k - r25k

    return {
        "session_index": row.get("session_index"),
        "profile": row.get("profile"),
        "final_capital": to_float(row.get("final_capital")),
        "peak_capital": to_float(row.get("peak_capital")),
        "total_rounds": to_float(row.get("total_rounds")),
        "max_drawdown": to_float(row.get("max_drawdown")),
        "longest_win_streak": to_float(row.get("longest_win_streak")),
        "longest_loss_streak": to_float(row.get("longest_loss_streak")),
        "late_momentum_25": to_float(row.get("late_momentum_25")),
        "r1k": r1k,
        "r10k": r10k,
        "r25k": r25k,
        "r50k": r50k,
        "r100k": r100k,
        "d1k10k": d1k10k,
        "d10k25k": d10k25k,
        "d25k50k": d25k50k,
        "d50k100k": d50k100k,
        "d25k100k": d25k100k,
    }


def summarize(label, rows):
    if not rows:
        print(f"{label}: count=0")
        return

    print(
        f"{label}: count={len(rows)} | "
        f"avg_final={safe_mean([r['final_capital'] for r in rows])} | "
        f"median_final={safe_median([r['final_capital'] for r in rows])} | "
        f"avg_peak={safe_mean([r['peak_capital'] for r in rows])} | "
        f"median_peak={safe_median([r['peak_capital'] for r in rows])} | "
        f"avg_rounds={safe_mean([r['total_rounds'] for r in rows])} | "
        f"median_rounds={safe_median([r['total_rounds'] for r in rows])} | "
        f"avg_dd={safe_mean([r['max_drawdown'] for r in rows])} | "
        f"median_dd={safe_median([r['max_drawdown'] for r in rows])} | "
        f"avg_loss_streak={safe_mean([r['longest_loss_streak'] for r in rows])} | "
        f"median_loss_streak={safe_median([r['longest_loss_streak'] for r in rows])} | "
        f"avg_win_streak={safe_mean([r['longest_win_streak'] for r in rows])} | "
        f"median_win_streak={safe_median([r['longest_win_streak'] for r in rows])}"
    )

    print(
        f"{label} phase: "
        f"avg_d1k10k={safe_mean([r['d1k10k'] for r in rows])} | "
        f"median_d1k10k={safe_median([r['d1k10k'] for r in rows])} | "
        f"avg_d10k25k={safe_mean([r['d10k25k'] for r in rows])} | "
        f"median_d10k25k={safe_median([r['d10k25k'] for r in rows])} | "
        f"avg_d25k50k={safe_mean([r['d25k50k'] for r in rows])} | "
        f"median_d25k50k={safe_median([r['d25k50k'] for r in rows])} | "
        f"avg_d50k100k={safe_mean([r['d50k100k'] for r in rows])} | "
        f"median_d50k100k={safe_median([r['d50k100k'] for r in rows])} | "
        f"avg_d25k100k={safe_mean([r['d25k100k'] for r in rows])} | "
        f"median_d25k100k={safe_median([r['d25k100k'] for r in rows])}"
    )

    print(
        f"{label} thresholds: "
        f"pct_d10k25k_le2={pct([r['d10k25k'] for r in rows], 2, 'le')} | "
        f"pct_d10k25k_le5={pct([r['d10k25k'] for r in rows], 5, 'le')} | "
        f"pct_d25k50k_le5={pct([r['d25k50k'] for r in rows], 5, 'le')} | "
        f"pct_d50k100k_le10={pct([r['d50k100k'] for r in rows], 10, 'le')} | "
        f"pct_loss_streak_ge10={pct([r['longest_loss_streak'] for r in rows], 10, 'ge')} | "
        f"pct_dd_ge25000={pct([r['max_drawdown'] for r in rows], 25000, 'ge')}"
    )


def print_top(label, rows, key, limit=15):
    print(f"\nTop {limit} {label} by {key}:")
    top = sorted(rows, key=lambda row: row[key] if row[key] is not None else -1, reverse=True)[:limit]
    for row in top:
        print(
            f"index={row['session_index']} | profile={row['profile']} | "
            f"final={row['final_capital']} | peak={row['peak_capital']} | "
            f"dd={row['max_drawdown']} | rounds={row['total_rounds']} | "
            f"d10k25k={row['d10k25k']} | d25k50k={row['d25k50k']} | "
            f"d50k100k={row['d50k100k']} | loss_streak={row['longest_loss_streak']} | "
            f"momentum25={row['late_momentum_25']}"
        )


def main():
    parser = argparse.ArgumentParser(description="Compare winners vs near_miss_high trajectories")
    parser.add_argument("--input", default="results/trajectory_analyzer_phase_state_v2.csv")
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    path = Path(args.input)
    winners = []
    near_high = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        print("\nDetected CSV columns:")
        print(reader.fieldnames)

        for row in reader:
            enriched = enrich(row)
            if enriched["profile"] == "winner":
                winners.append(enriched)
            elif enriched["profile"] == "near_miss_high":
                near_high.append(enriched)

    print("\n=== LIMBO100k Winner vs Near High ===")
    summarize("WINNERS", winners)
    summarize("NEAR_HIGH", near_high)

    print_top("winners", winners, "final_capital")
    print_top("near_high", near_high, "peak_capital")

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "winner_vs_nearhigh.csv"
        rows = winners + near_high
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV exported to: {output_path}")


if __name__ == "__main__":
    main()
