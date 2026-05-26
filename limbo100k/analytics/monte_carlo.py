from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median

from limbo100k.session_runner import run_fixed_strategy_session


@dataclass
class MonteCarloReport:
    sessions: int
    average_final_capital: float
    median_final_capital: float
    success_rate: float
    depletion_rate: float
    best_session: float
    worst_session: float


def run_monte_carlo(
    sessions: int,
    initial_capital: float,
    target_capital: float,
    stake: float,
    target_multiplier: float,
    max_rounds: int,
) -> MonteCarloReport:
    results = []
    successes = 0
    depleted = 0

    for session_index in range(sessions):
        summary = run_fixed_strategy_session(
            initial_capital=initial_capital,
            target_capital=target_capital,
            stake=stake,
            target_multiplier=target_multiplier,
            max_rounds=max_rounds,
            server_seed=f"SERVER_{session_index}",
            client_seed=f"CLIENT_{session_index}",
        )

        results.append(summary.final_capital)

        if summary.reached_target:
            successes += 1

        if summary.depleted:
            depleted += 1

    return MonteCarloReport(
        sessions=sessions,
        average_final_capital=round(mean(results), 2),
        median_final_capital=round(median(results), 2),
        success_rate=round((successes / sessions) * 100, 2),
        depletion_rate=round((depleted / sessions) * 100, 2),
        best_session=round(max(results), 2),
        worst_session=round(min(results), 2),
    )
