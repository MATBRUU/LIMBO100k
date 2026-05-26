from __future__ import annotations

from dataclasses import dataclass

from limbo100k.agents.adaptive_risk_agent import AdaptiveRiskAgent
from limbo100k.agents.fixed_bet_agent import FixedBetAgent
from limbo100k.agents.percentage_risk_agent import PercentageRiskAgent
from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.provably_fair import ProvablyFairRng


@dataclass
class SessionSummary:
    final_capital: float
    peak_capital: float
    lowest_capital: float
    positive_rounds: int
    negative_rounds: int
    total_rounds: int
    reached_target: bool
    depleted: bool
    history: list[dict]


def build_agent(
    strategy: str,
    stake: float,
    target_multiplier: float,
    risk_fraction: float,
):
    if strategy == "fixed":
        return FixedBetAgent(bet_size=stake, target_multiplier=target_multiplier)

    if strategy == "percentage":
        return PercentageRiskAgent(
            risk_fraction=risk_fraction,
            target_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "adaptive":
        return AdaptiveRiskAgent(
            base_fraction=risk_fraction,
            target_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    raise ValueError(f"Unknown strategy: {strategy}")


def run_strategy_session(
    strategy: str,
    initial_capital: float,
    target_capital: float,
    stake: float,
    target_multiplier: float,
    risk_fraction: float,
    max_rounds: int,
    server_seed: str,
    client_seed: str,
    house_edge: float = 0.99,
) -> SessionSummary:
    rng = ProvablyFairRng(server_seed=server_seed, client_seed=client_seed)
    engine = LimboEngine(rng=rng, house_edge=house_edge)
    agent = build_agent(
        strategy=strategy,
        stake=stake,
        target_multiplier=target_multiplier,
        risk_fraction=risk_fraction,
    )

    capital = initial_capital
    peak_capital = capital
    lowest_capital = capital
    positive_rounds = 0
    negative_rounds = 0
    history: list[dict] = []

    for round_number in range(1, max_rounds + 1):
        if capital <= 0 or capital >= target_capital:
            break

        exposure, selected_multiplier = agent.next_bet(capital)
        if exposure <= 0:
            break

        result = engine.play(stake=exposure, target_multiplier=selected_multiplier)
        capital += result.profit
        peak_capital = max(peak_capital, capital)
        lowest_capital = min(lowest_capital, capital)

        if hasattr(agent, "observe"):
            agent.observe(result.won, capital)

        if result.won:
            positive_rounds += 1
        else:
            negative_rounds += 1

        history.append(
            {
                "round": round_number,
                "strategy": strategy,
                "nonce": result.nonce,
                "stake": round(exposure, 2),
                "target_multiplier": round(result.target_multiplier, 4),
                "rolled_multiplier": round(result.rolled_multiplier, 4),
                "outcome": "success" if result.won else "failure",
                "profit": round(result.profit, 2),
                "capital": round(capital, 2),
                "drawdown_from_peak": round(peak_capital - capital, 2),
                "server_seed_hash": result.proof.server_seed_hash,
                "digest": result.proof.digest,
            }
        )

    return SessionSummary(
        final_capital=round(capital, 2),
        peak_capital=round(peak_capital, 2),
        lowest_capital=round(lowest_capital, 2),
        positive_rounds=positive_rounds,
        negative_rounds=negative_rounds,
        total_rounds=positive_rounds + negative_rounds,
        reached_target=capital >= target_capital,
        depleted=capital <= 0,
        history=history,
    )


def run_fixed_strategy_session(
    initial_capital: float,
    target_capital: float,
    stake: float,
    target_multiplier: float,
    max_rounds: int,
    server_seed: str,
    client_seed: str,
    house_edge: float = 0.99,
) -> SessionSummary:
    return run_strategy_session(
        strategy="fixed",
        initial_capital=initial_capital,
        target_capital=target_capital,
        stake=stake,
        target_multiplier=target_multiplier,
        risk_fraction=0.02,
        max_rounds=max_rounds,
        server_seed=server_seed,
        client_seed=client_seed,
        house_edge=house_edge,
    )
