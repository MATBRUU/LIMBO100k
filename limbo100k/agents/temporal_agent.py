from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TemporalAgent:
    base_fraction: float = 0.18
    base_multiplier: float = 5.0
    minimum_stake: float = 0.1

    def __post_init__(self) -> None:
        self.start: float | None = None
        self.fraction = self.base_fraction
        self.multiplier = self.base_multiplier
        self.rounds = 0
        self.up = 0
        self.down = 0
        self.peak = 0.0
        self.mode = "base"

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        self.rounds += 1
        if bankroll <= 0:
            return 0.0, self.multiplier

        if self.start is None:
            self.start = bankroll
            self.peak = bankroll

        self.peak = max(self.peak, bankroll)
        ratio = bankroll / self.start
        peak_ratio = self.peak / self.start
        self._mode(ratio, peak_ratio, bankroll)

        amount = bankroll * self.fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)
        return round(amount, 2), round(self.multiplier, 4)

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.up += 1
            self.down = 0
            self._up()
        else:
            self.down += 1
            self.up = 0
            self._down()

    def _mode(self, ratio: float, peak_ratio: float, bankroll: float) -> None:
        if bankroll >= 85000:
            self.mode = "close"
            self.fraction = min(self.fraction, 0.08)
            self.multiplier = min(self.multiplier, 3.0)
        elif bankroll >= 50000:
            self.mode = "upper"
            self.fraction = min(self.fraction, 0.12)
            self.multiplier = min(self.multiplier, 4.0)
        elif peak_ratio >= 200 and self.rounds > 250:
            self.mode = "upper_mid"
            self.fraction = min(max(self.fraction, 0.10), 0.18)
            self.multiplier = min(max(self.multiplier, 3.0), 8.0)
        elif self.rounds <= 500:
            self.mode = "base"
            self.fraction = max(self.fraction, self.base_fraction)
            self.multiplier = max(self.multiplier, self.base_multiplier)
        elif ratio < 2:
            self.mode = "late_low"
            self.fraction = max(self.fraction, 0.14)
            self.multiplier = max(self.multiplier, 4.0)
        else:
            self.mode = "mid"

    def _up(self) -> None:
        if self.mode == "base":
            self.fraction = min(0.32, self.fraction * 1.12)
            if self.up >= 2:
                self.multiplier = min(80.0, self.multiplier * 1.18)
        elif self.mode == "late_low":
            self.fraction = min(0.26, self.fraction * 1.10)
            if self.up >= 2:
                self.multiplier = min(50.0, self.multiplier * 1.12)
        elif self.mode in {"upper", "close"}:
            self.fraction = max(0.04, self.fraction * 0.94)
            self.multiplier = max(2.0, self.multiplier * 0.96)
        else:
            self.fraction = min(0.24, self.fraction * 1.06)
            self.multiplier = min(25.0, self.multiplier * 1.08)

    def _down(self) -> None:
        if self.mode == "base":
            self.fraction = max(0.10, self.fraction * 0.88)
            self.multiplier = max(3.0, self.multiplier * 0.86)
        elif self.mode == "late_low":
            self.fraction = max(0.08, self.fraction * 0.90)
            self.multiplier = max(2.5, self.multiplier * 0.88)
        elif self.mode == "close":
            self.fraction = max(0.03, self.fraction * 0.88)
            self.multiplier = max(1.8, self.multiplier * 0.90)
        elif self.mode == "upper":
            self.fraction = max(0.04, self.fraction * 0.90)
            self.multiplier = max(2.0, self.multiplier * 0.90)
        else:
            self.fraction = max(0.06, self.fraction * 0.88)
            self.multiplier = max(2.2, self.multiplier * 0.86)
