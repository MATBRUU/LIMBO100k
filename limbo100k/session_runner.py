from __future__ import annotations

from dataclasses import dataclass

from limbo100k.agents.adaptive_risk_agent import AdaptiveRiskAgent
from limbo100k.agents.convex_agent import ConvexAgent
from limbo100k.agents.density_phase_agent import DensityPhaseAgent
from limbo100k.agents.dynamic_decision_agent import DynamicDecisionAgent
from limbo100k.agents.fixed_bet_agent import FixedBetAgent
from limbo100k.agents.meta_phase_agent import MetaPhaseAgent
from limbo100k.agents.momentum_phase_agent import MomentumPhaseAgent
from limbo100k.agents.percentage_risk_agent import PercentageRiskAgent
from limbo100k.agents.phase_agent import PhaseAgent
from limbo100k.agents.temporal_agent import TemporalAgent

from limbo100k.engine.limbo_engine import LimboEngine
from limbo100k.policy.session_policy import SessionPolicy
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
    stop_reason: str
    history: list[dict]


def build_agent(
    strategy: str,
    stake: float,
    target_multiplier: float,
    risk_fraction: float,
):

    if strategy == "fixed":
        return FixedBetAgent(
            bet_size=stake,
            target_multiplier=target_multiplier,
        )

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

    if strategy == "dynamic":
        return DynamicDecisionAgent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "convex":
        return ConvexAgent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "phase":
        return PhaseAgent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "meta_phase":
        return MetaPhaseAgent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "temporal":
        return TemporalAgent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "momentum_phase":
        return MomentumPhaseAgent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "density_phase":
        return DensityPhaseAgent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
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
    use_policy: bool = True,
) -> SessionSummary:

    rng = ProvablyFairRng(
        server_seed=server_seed,
        client_seed=client_seed,
    )

    engine = LimboEngine(
        rng=rng,
        house_edge=house_edge,
    )

    policy = SessionPolicy()

    agent = build_agent(
        strategy,
        stake,
        target_multiplier,
        risk_fraction,
    )

    capital = initial_capital
    peak_capital = capital
    lowest_capital = capital

    positive_rounds = 0
    negative_rounds = 0
    negative_sequence = 0

    stop_reason = "max_rounds"

    history: list[dict] = []

    for round_number in range(1, max_rounds + 1):

        if use_policy:
            should_stop, reason = policy.evaluate(
                initial_capital=initial_capital,
                current_capital=capital,
                peak_capital=peak_capital,
                negative_sequence=negative_sequence,
            )

            if should_stop:
                stop_reason = reason
                break

        if capital <= 0:
            stop_reason = "capital_floor"
            break

        if capital >= target_capital:
            stop_reason = "objective_reached"
            break

        exposure, selected_multiplier = agent.next_bet(capital)

        if exposure <= 0:
            stop_reason = "no_exposure"
            break

        result = engine.play(
            stake=exposure,
            target_multiplier=selected_multiplier,
        )

        capital += result.profit

        peak_capital = max(peak_capital, capital)
        lowest_capital = min(lowest_capital, capital)

        if hasattr(agent, "observe"):
            agent.observe(result.won, capital)

        if result.won:
            positive_rounds += 1
            negative_sequence = 0
        else:
            negative_rounds += 1
            negative_sequence += 1

        history.append(
            {
                "round": round_number,
                "strategy": strategy,
                "nonce": result.nonce,
                "stake": round(exposure, 2),
                "target_multiplier": round(
                    result.target_multiplier,
                    4,
                ),
                "rolled_multiplier": round(
                    result.rolled_multiplier,
                    4,
                ),
                "outcome": (
                    "success"
                    if result.won
                    else "failure"
                ),
                "profit": round(result.profit, 2),
                "capital": round(capital, 2),
                "negative_sequence": negative_sequence,
                "drawdown_from_peak": round(
                    peak_capital - capital,
                    2,
                ),
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
        stop_reason=stop_reason,
        history=history,
    )
