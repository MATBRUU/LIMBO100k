from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PhaseAgent:
    base_fraction: float = 0.1
    base_multiplier: float = 4.0
    minimum_stake: float = 0.1

    def __post_init__(self) -> None:
        self.start_capital: float | None = None
        self.current_fraction = self.base_fraction
        self.current_multiplier = self.base_multiplier
        self.up_count = 0
        self.down_count = 0

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        if bankroll <= 0:
            return 0.0, self.current_multiplier

        if self.start_capital is None:
            self.start_capital = bankroll

        ratio = bankroll / self.start_capital

        if ratio < 2:
            self.current_fraction = max(self.current_fraction, 0.10)
            self.current_multiplier = max(self.current_multiplier, 4.0)
        elif ratio < 10:
            self.current_fraction = max(self.current_fraction, 0.14)
            self.current_multiplier = max(self.current_multiplier, 6.0)
        elif ratio < 100:
            self.current_fraction = max(self.current_fraction, 0.18)
            self.current_multiplier = max(self.current_multiplier, 10.0)
        else:
            self.current_fraction = min(self.current_fraction, 0.08)
            self.current_multiplier = min(self.current_multiplier, 3.0)

        amount = bankroll * self.current_fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)
        return round(amount, 2), round(self.current_multiplier, 4)

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.up_count += 1
            self.down_count = 0
            self.current_fraction = min(0.5, self.current_fraction * 1.2)
            if self.up_count >= 2:
                self.current_multiplier = min(300.0, self.current_multiplier * 1.35)
        else:
            self.down_count += 1
            self.up_count = 0
            self.current_fraction = max(0.04, self.current_fraction * 0.85)
            if self.down_count >= 2:
                self.current_multiplier = max(2.0, self.current_multiplier * 0.75)
