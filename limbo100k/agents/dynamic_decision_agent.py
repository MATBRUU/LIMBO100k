from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DynamicDecisionAgent:
    """Agent that adapts both exposure and target multiplier every round."""

    base_fraction: float = 0.02
    base_multiplier: float = 2.0
    minimum_stake: float = 0.1
    min_fraction: float = 0.005
    max_fraction: float = 0.08
    min_multiplier: float = 1.25
    max_multiplier: float = 20.0

    def __post_init__(self) -> None:
        self.current_fraction = self.base_fraction
        self.current_multiplier = self.base_multiplier
        self.positive_sequence = 0
        self.negative_sequence = 0

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        if bankroll <= 0:
            return 0.0, self.current_multiplier

        amount = bankroll * self.current_fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)

        return round(amount, 2), round(self.current_multiplier, 4)

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.positive_sequence += 1
            self.negative_sequence = 0
            self._increase_confidence()
        else:
            self.negative_sequence += 1
            self.positive_sequence = 0
            self._reduce_exposure()

        if bankroll <= 0:
            self.current_fraction = self.min_fraction
            self.current_multiplier = self.min_multiplier

    def _increase_confidence(self) -> None:
        self.current_fraction = min(self.max_fraction, self.current_fraction * 1.06)

        if self.positive_sequence >= 3:
            self.current_multiplier = min(self.max_multiplier, self.current_multiplier * 1.08)

    def _reduce_exposure(self) -> None:
        self.current_fraction = max(self.min_fraction, self.current_fraction * 0.72)

        if self.negative_sequence >= 2:
            self.current_multiplier = max(self.min_multiplier, self.current_multiplier * 0.82)

        if self.negative_sequence >= 5:
            self.current_fraction = self.min_fraction
            self.current_multiplier = self.min_multiplier
