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
from limbo100k.agents.phase_state_agent import PhaseStateAgent
from limbo100k.agents.phase_state_v2_agent import PhaseStateV2Agent
from limbo100k.agents.phase_state_v21_agent import PhaseStateV21Agent
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

    if strategy == "phase_state":
        return PhaseStateAgent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "phase_state_v2":
        return PhaseStateV2Agent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    if strategy == "phase_state_v21":
        return PhaseStateV21Agent(
            base_fraction=risk_fraction,
            base_multiplier=target_multiplier,
            minimum_stake=0.1,
        )

    raise ValueError(f"Unknown strategy: {strategy}")
