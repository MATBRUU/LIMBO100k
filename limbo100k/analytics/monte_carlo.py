from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import mean, median

from limbo100k.session_runner import run_strategy_session


@dataclass
class MonteCarloReport:
    sessions: int
    strategy: str
    average_final_capital: float
    median_final_capital: float
    objective_rate: float
    floor_rate: float
    best_session: float
    worst_session: float
    average_rounds: float
    dominant_stop_reason: str


def run_monte_carlo(
    sessions: int,
    initial_capital: float,
    target_capital: float,
    stake: float,
    target_multiplier: float,
    max_rounds: int,
    strategy: str = "fixed",
    risk_fraction: float = 0.02,
) -> MonteCarloReport:
    final_values = []
    round_counts = []
    stop_reasons = Counter()
    objectives = 0
    floor_events = 0

    for session_index in range(sessions):
        summary = run_strategy_session(
            strategy=strategy,
            initial_capital=initial_capital,
            target_capital=target_capital,
            stake=stake,
            target_multiplier=target_multiplier,
            risk_fraction=risk_fraction,
            max_rounds=max_rounds,
            server_seed=f"SERVER_{strategy}_{session_index}",
            client_seed=f"CLIENT_{strategy}_{session_index}",
        )

        final_values.append(summary.final_capital)
        round_counts.append(summary.total_rounds)
        stop_reasons[summary.stop_reason] += 1

        if summary.reached_target:
            objectives += 1

        if summary.depleted:
            floor_events += 1

    dominant_stop_reason = stop_reasons.most_common(1)[0][0] if stop_reasons else "none"

    return MonteCarloReport(
        sessions=sessions,
        strategy=strategy,
        average_final_capital=round(mean(final_values), 2),
        median_final_capital=round(median(final_values), 2),
        objective_rate=round((objectives / sessions) * 100, 2),
        floor_rate=round((floor_events / sessions) * 100, 2),
        best_session=round(max(final_values), 2),
        worst_session=round(min(final_values), 2),
        average_rounds=round(mean(round_counts), 2),
        dominant_stop_reason=dominant_stop_reason,
    )
