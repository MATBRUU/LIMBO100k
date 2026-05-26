from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConvexAgent:
    """Agent designed to explore asymmetric outcome distributions."""

    base_fraction: float = 0.04
    base_multiplier: float = 3.0
    minimum_stake: float = 0.1
    min_fraction: float = 0.01
    max_fraction: float = 0.18
    min_multiplier: float = 1.5
    max_multiplier: float = 250.0
    capital_lock_threshold: float = 4.0

    def __post_init__(self) -> None:
        self.current_fraction = self.base_fraction
        self.current_multiplier = self.base_multiplier
        self.positive_sequence = 0
        self.negative_sequence = 0
        self.initial_capital: float | None = None

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        if bankroll <= 0:
            return 0.0, self.current_multiplier

        if self.initial_capital is None:
            self.initial_capital = bankroll

        fraction = self.current_fraction
        if bankroll >= self.initial_capital * self.capital_lock_threshold:
            fraction = max(self.min_fraction, self.current_fraction * 0.5)

        amount = bankroll * fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)
        return round(amount, 2), round(self.current_multiplier, 4)

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.positive_sequence += 1
            self.negative_sequence = 0
            self._expand_after_positive(bankroll)
        else:
            self.negative_sequence += 1
            self.positive_sequence = 0
            self._normalize_after_negative()

    def _expand_after_positive(self, bankroll: float) -> None:
        self.current_fraction = min(self.max_fraction, self.current_fraction * 1.18)

        if self.positive_sequence >= 2:
            self.current_multiplier = min(self.max_multiplier, self.current_multiplier * 1.35)

        if self.initial_capital and bankroll >= self.initial_capital * 10:
            self.current_fraction = max(self.min_fraction, self.current_fraction * 0.65)

    def _normalize_after_negative(self) -> None:
        self.current_fraction = max(self.min_fraction, self.current_fraction * 0.6)

        if self.negative_sequence <= 2:
            self.current_multiplier = max(self.min_multiplier, self.current_multiplier * 0.75)
        else:
            self.current_multiplier = self.base_multiplier
            self.current_fraction = self.base_fraction
