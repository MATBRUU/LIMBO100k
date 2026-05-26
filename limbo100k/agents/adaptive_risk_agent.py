from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdaptiveRiskAgent:
    """Simple adaptive exposure strategy for simulated risk experiments."""

    base_fraction: float = 0.02
    target_multiplier: float = 2.0
    minimum_stake: float = 0.1
    max_fraction: float = 0.08
    min_fraction: float = 0.005
    loss_sensitivity: float = 0.75
    win_sensitivity: float = 1.08

    def __post_init__(self) -> None:
        self.current_fraction = self.base_fraction
        self.consecutive_positive = 0
        self.consecutive_negative = 0

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        if bankroll <= 0:
            return 0.0, self.target_multiplier

        amount = bankroll * self.current_fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)
        return round(amount, 2), self.target_multiplier

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.consecutive_positive += 1
            self.consecutive_negative = 0
            self.current_fraction = min(
                self.max_fraction,
                self.current_fraction * self.win_sensitivity,
            )
        else:
            self.consecutive_negative += 1
            self.consecutive_positive = 0
            self.current_fraction = max(
                self.min_fraction,
                self.current_fraction * self.loss_sensitivity,
            )

        if bankroll <= 0:
            self.current_fraction = self.min_fraction
