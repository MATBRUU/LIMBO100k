from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import product
from statistics import mean, median

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng


@dataclass
class LabTemporalAgent:
    base_fraction: float
    base_multiplier: float
    win_fraction_boost: float
    win_multiplier_boost: float
    loss_fraction_decay: float
    loss_multiplier_decay: float
    late_fraction_cap: float
    late_multiplier_cap: float
    close_fraction_cap: float
    close_multiplier_cap: float
    minimum_stake: float = 0.1

    def __post_init__(self) -> None:
        self.start: float | None = None
        self.fraction = self.base_fraction
        self.multiplier = self.base_multiplier
        self.rounds = 0
        self.up = 0
        self.down = 0
        self.peak = 0.0
        self.mode = "base"

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        self.rounds += 1
        if bankroll <= 0:
            return 0.0, self.multiplier
        if self.start is None:
            self.start = bankroll
            self.peak = bankroll
        self.peak = max(self.peak, bankroll)
        self._mode(bankroll)
        amount = min(max(bankroll * self.fraction, self.minimum_stake), bankroll)
        return round(amount, 2), round(self.multiplier, 4)

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.up += 1
            self.down = 0
            self._after_win()
        else:
            self.down += 1
            self.up = 0
            self._after_loss()

    def _mode(self, bankroll: float) -> None:
        if bankroll >= 85000:
            self.mode = "close"
            self.fraction = min(self.fraction, self.close_fraction_cap)
            self.multiplier = min(self.multiplier, self.close_multiplier_cap)
        elif bankroll >= 50000:
            self.mode = "late"
            self.fraction = min(self.fraction, self.late_fraction_cap)
            self.multiplier = min(self.multiplier, self.late_multiplier_cap)
        elif self.rounds <= 500:
            self.mode = "base"
            self.fraction = max(self.fraction, self.base_fraction)
            self.multiplier = max(self.multiplier, self.base_multiplier)
        else:
            ratio = bankroll / self.start if self.start else 1.0
            self.mode = "low" if ratio < 2 else "mid"

    def _after_win(self) -> None:
        if self.mode == "base":
            self.fraction = min(0.36, self.fraction * self.win_fraction_boost)
            if self.up >= 2:
                self.multiplier = min(120.0, self.multiplier * self.win_multiplier_boost)
        elif self.mode in {"late", "close"}:
            self.fraction = max(0.04, self.fraction * 0.96)
            self.multiplier = max(2.0, self.multiplier * 0.98)
        else:
            self.fraction = min(0.28, self.fraction * 1.06)
            self.multiplier = min(40.0, self.multiplier * 1.08)

    def _after_loss(self) -> None:
        if self.mode == "base":
            self.fraction = max(0.10, self.fraction * self.loss_fraction_decay)
            self.multiplier = max(3.0, self.multiplier * self.loss_multiplier_decay)
        elif self.mode == "close":
            self.fraction = max(0.03, self.fraction * 0.90)
            self.multiplier = max(1.8, self.multiplier * 0.92)
        elif self.mode == "late":
            self.fraction = max(0.04, self.fraction * 0.92)
            self.multiplier = max(2.0, self.multiplier * 0.92)
        else:
            self.fraction = max(0.06, self.fraction * 0.90)
            self.multiplier = max(2.2, self.multiplier * 0.88)


def run_session(config: dict, session_index: int, args: argparse.Namespace) -> tuple[float, str]:
    rng = ProvablyFairRng(
        server_seed=f"LAB_SERVER_{session_index}",
        client_seed=f"LAB_CLIENT_{session_index}",
    )
    engine = LimboEngine(rng=rng)
    agent = LabTemporalAgent(**config)
    capital = args.initial_capital
    reason = "max_rounds"

    for _ in range(args.rounds):
        if capital <= 0:
            reason = "depleted"
            break
        if capital >= args.target_capital:
            reason = "objective_reached"
            break
        stake, target = agent.next_bet(capital)

if stake <= 0:
    reason = "no_exposure"
    break

result = engine.play(stake=stake, target_multiplier=target)
        capital += result.profit
        agent.observe(result.won, capital)

    return round(capital, 2), reason


def evaluate(config: dict, args: argparse.Namespace) -> dict:
    finals = []
    hits = 0
    best = 0.0
    best_index = args.seed_offset

    for local_index in range(args.sessions):
        session_index = args.seed_offset + local_index
        final, reason = run_session(config, session_index, args)
        finals.append(final)
        if reason == "objective_reached" or final >= args.target_capital:
            hits += 1
        if final > best:
            best = final
            best_index = session_index

    return {
        "avg": round(mean(finals), 2),
        "median": round(median(finals), 2),
        "objective_rate": round((hits / args.sessions) * 100, 6),
        "best": round(best, 2),
        "best_index": best_index,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-search TemporalAgent parameter variants")
    parser.add_argument("--sessions", type=int, default=5000)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--initial-capital", type=float, default=50.0)
    parser.add_argument("--target-capital", type=float, default=100000.0)
    parser.add_argument("--rounds", type=int, default=5000)
    args = parser.parse_args()

    base_fractions = [0.18, 0.20, 0.22]
    win_fraction_boosts = [1.10, 1.12, 1.15]
    win_multiplier_boosts = [1.18, 1.22, 1.26]
    loss_fraction_decays = [0.88, 0.91, 0.94]
    loss_multiplier_decays = [0.86, 0.89, 0.92]
    late_multiplier_caps = [4.0, 5.0, 6.0]

    results = []
    total = 0

    for values in product(
        base_fractions,
        win_fraction_boosts,
        win_multiplier_boosts,
        loss_fraction_decays,
        loss_multiplier_decays,
        late_multiplier_caps,
    ):
        total += 1
        config = {
            "base_fraction": values[0],
            "base_multiplier": 5.0,
            "win_fraction_boost": values[1],
            "win_multiplier_boost": values[2],
            "loss_fraction_decay": values[3],
            "loss_multiplier_decay": values[4],
            "late_fraction_cap": 0.12,
            "late_multiplier_cap": values[5],
            "close_fraction_cap": 0.08,
            "close_multiplier_cap": 3.0,
        }
        report = evaluate(config, args)
        report.update(config)
        results.append(report)
        print(
            f"Test {total} | avg={report['avg']} € | obj={report['objective_rate']}% | "
            f"best={report['best']} € | bf={config['base_fraction']} | "
            f"wmb={config['win_multiplier_boost']} | lfd={config['loss_fraction_decay']} | "
            f"lmd={config['loss_multiplier_decay']} | late_cap={config['late_multiplier_cap']}"
        )

    results.sort(key=lambda row: (row["objective_rate"], row["avg"], row["best"]), reverse=True)

    print("\n=== LIMBO100k Temporal Lab Top 20 ===")
    for rank, row in enumerate(results[:20], start=1):
        print(
            f"#{rank} | obj={row['objective_rate']}% | avg={row['avg']} € | best={row['best']} € | "
            f"bf={row['base_fraction']} | wfb={row['win_fraction_boost']} | "
            f"wmb={row['win_multiplier_boost']} | lfd={row['loss_fraction_decay']} | "
            f"lmd={row['loss_multiplier_decay']} | late_cap={row['late_multiplier_cap']}"
        )


if __name__ == "__main__":
    main()
