from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


NUMERIC_FIELDS = {
    "final_capital",
    "peak_capital",
    "lowest_capital",
    "rounds",
    "wins",
    "losses",
    "longest_win_streak",
    "longest_loss_streak",
    "max_drawdown",
    "r_1000",
    "r_10000",
    "r_25000",
    "r_50000",
    "r_100000",
    "d_1k_10k",
    "d_10k_25k",
}


def as_number(value: str):
    if value is None or value == "" or value == "None":
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_rows(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = []
        for row in reader:
            cleaned = {}
            for key, value in row.items():
                cleaned[key] = as_number(value) if key in NUMERIC_FIELDS else value
            rows.append(cleaned)
    return rows


def classify_family(row: dict) -> str:
    existing = row.get("shape")
    if existing:
        return str(existing)

    drawdown = row.get("max_drawdown") or 0
    d1 = row.get("d_1k_10k")
    d2 = row.get("d_10k_25k")
    rounds = row.get("rounds") or 0

    if drawdown <= 5000 and d2 is not None and d2 <= 3:
        return "clean_direct_hyper"
    if drawdown >= 25000 and d2 is not None and d2 <= 5:
        return "chaotic_re_density"
    if rounds >= 150:
        return "slow_convex_survivor"
    if d1 is not None and d1 <= 5:
        return "fast_breakout"
    if d2 is not None and d2 <= 5:
        return "post_10k_density"
    return "unclassified"


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


def summarize_family(name: str, rows: list[dict]) -> dict:
    finals = [row.get("final_capital") for row in rows]
    peaks = [row.get("peak_capital") for row in rows]
    drawdowns = [row.get("max_drawdown") for row in rows]

    return {
        "family": name,
        "count": len(rows),
        "avg_final": avg(finals),
        "median_final": med(finals),
        "max_final": max(finals) if finals else None,
        "avg_peak": avg(peaks),
        "avg_drawdown": avg(drawdowns),
        "max_drawdown": max(drawdowns) if drawdowns else None,
        "avg_wins": avg([row.get("wins") for row in rows]),
        "avg_losses": avg([row.get("losses") for row in rows]),
        "avg_rounds": avg([row.get("rounds") for row in rows]),
        "avg_d1k10k": avg([row.get("d_1k_10k") for row in rows]),
        "median_d1k10k": med([row.get("d_1k_10k") for row in rows]),
        "avg_d10k25k": avg([row.get("d_10k_25k") for row in rows]),
        "median_d10k25k": med([row.get("d_10k_25k") for row in rows]),
    }


def print_summary(summary: dict) -> None:
    print(
        f"{summary['family']}: "
        f"count={summary['count']} | "
        f"avg_final={summary['avg_final']} € | "
        f"median_final={summary['median_final']} € | "
        f"max_final={summary['max_final']} € | "
        f"avg_peak={summary['avg_peak']} € | "
        f"avg_dd={summary['avg_drawdown']} € | "
        f"max_dd={summary['max_drawdown']} € | "
        f"avg_wins={summary['avg_wins']} | "
        f"avg_losses={summary['avg_losses']} | "
        f"avg_rounds={summary['avg_rounds']} | "
        f"avg_d1k10k={summary['avg_d1k10k']} | "
        f"avg_d10k25k={summary['avg_d10k25k']}"
    )


def print_top_by_family(families: dict[str, list[dict]], limit: int) -> None:
    for family, rows in sorted(families.items()):
        print(f"\nTop {limit} — {family}:")
        top = sorted(rows, key=lambda row: row.get("final_capital") or 0, reverse=True)[:limit]
        for rank, row in enumerate(top, start=1):
            print(
                f"#{rank} | index={row.get('session_index')} | "
                f"final={row.get('final_capital')} € | "
                f"dd={row.get('max_drawdown')} € | "
                f"rounds={row.get('rounds')} | "
                f"wins={row.get('wins')} | losses={row.get('losses')} | "
                f"d1={row.get('d_1k_10k')} | d2={row.get('d_10k_25k')}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze winner trajectory families")
    parser.add_argument(
        "--input",
        default="results/winner_autopsy_summary_phase_state_v2.csv",
        help="CSV produced by scripts/winner_autopsy.py --export-csv",
    )
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--export-csv", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    rows = load_rows(input_path)

    families: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        family = classify_family(row)
        row["family"] = family
        families[family].append(row)

    print("\n=== LIMBO100k Trajectory Family Analysis ===")
    print(f"Input: {input_path}")
    print(f"Rows analyzed: {len(rows)}")

    summaries = []
    print("\nBy family:")
    for family in sorted(families):
        summary = summarize_family(family, families[family])
        summaries.append(summary)
        print_summary(summary)

    print_top_by_family(families, args.top)

    all_top = sorted(rows, key=lambda row: row.get("final_capital") or 0, reverse=True)[: args.top]
    print(f"\nTop {args.top} overall:")
    for rank, row in enumerate(all_top, start=1):
        print(
            f"#{rank} | family={row['family']} | index={row.get('session_index')} | "
            f"final={row.get('final_capital')} € | dd={row.get('max_drawdown')} € | "
            f"rounds={row.get('rounds')} | d1={row.get('d_1k_10k')} | d2={row.get('d_10k_25k')}"
        )

    if args.export_csv:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)

        summary_path = output_dir / "trajectory_family_summary.csv"
        with summary_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(summaries[0].keys()))
            writer.writeheader()
            writer.writerows(summaries)

        classified_path = output_dir / "trajectory_family_classified.csv"
        with classified_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nCSV exported to: {summary_path}")
        print(f"CSV exported to: {classified_path}")


if __name__ == "__main__":
    main()
