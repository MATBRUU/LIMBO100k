from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetaPhaseAgent:
    """Adaptive multi-profile agent based on trajectory family detection."""

    base_fraction: float = 0.18
    base_multiplier: float = 5.0
    minimum_stake: float = 0.1

    def __post_init__(self) -> None:
        self.initial_capital: float | None = None
        self.current_fraction = self.base_fraction
        self.current_multiplier = self.base_multiplier
        self.mode = "exploration"
        self.positive_sequence = 0
        self.negative_sequence = 0
        self.rounds = 0

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        self.rounds += 1

        if bankroll <= 0:
            return 0.0, self.current_multiplier

        if self.initial_capital is None:
            self.initial_capital = bankroll

        ratio = bankroll / self.initial_capital

        self._update_mode(ratio)

        amount = bankroll * self.current_fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)

        return round(amount, 2), round(self.current_multiplier, 4)

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.positive_sequence += 1
            self.negative_sequence = 0

            if self.mode == "early_explosion":
                self.current_fraction = min(0.45, self.current_fraction * 1.35)
                self.current_multiplier = min(500.0, self.current_multiplier * 1.45)

            elif self.mode == "stair_step":
                self.current_fraction = min(0.24, self.current_fraction * 1.08)
                self.current_multiplier = min(40.0, self.current_multiplier * 1.12)

            elif self.mode == "secure":
                self.current_fraction = max(0.04, self.current_fraction * 0.92)
                self.current_multiplier = max(2.0, self.current_multiplier * 0.95)

            else:
                self.current_fraction = min(0.30, self.current_fraction * 1.15)
                self.current_multiplier = min(80.0, self.current_multiplier * 1.2)

        else:
            self.negative_sequence += 1
            self.positive_sequence = 0

            if self.mode == "early_explosion":
                self.current_fraction = max(0.08, self.current_fraction * 0.82)
                self.current_multiplier = max(3.0, self.current_multiplier * 0.78)

            elif self.mode == "secure":
                self.current_fraction = max(0.03, self.current_fraction * 0.9)
                self.current_multiplier = max(1.8, self.current_multiplier * 0.92)

            else:
                self.current_fraction = max(0.05, self.current_fraction * 0.86)
                self.current_multiplier = max(2.0, self.current_multiplier * 0.82)

    def _update_mode(self, ratio: float) -> None:
        if ratio >= 1500:
            self.mode = "secure"
            self.current_fraction = min(self.current_fraction, 0.05)
            self.current_multiplier = min(self.current_multiplier, 2.2)
            return

        if ratio >= 200:
            self.mode = "stair_step"
            self.current_fraction = max(self.current_fraction, 0.12)
            self.current_multiplier = max(self.current_multiplier, 3.0)
            return

        if ratio >= 20:
            self.mode = "mixed"
            self.current_fraction = max(self.current_fraction, 0.18)
            self.current_multiplier = max(self.current_multiplier, 5.0)
            return

        if self.rounds <= 150:
            self.mode = "early_explosion"
            self.current_fraction = max(self.current_fraction, 0.22)
            self.current_multiplier = max(self.current_multiplier, 6.0)
        else:
            self.mode = "mixed"
