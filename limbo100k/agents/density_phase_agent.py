from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DensityPhaseAgent:
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
        self.r1k: int | None = None
        self.r10k: int | None = None
        self.r25k: int | None = None
        self.density_level = 0

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        self.rounds += 1

        if bankroll <= 0:
            return 0.0, self.multiplier

        if self.start is None:
            self.start = bankroll
            self.peak = bankroll

        self.peak = max(self.peak, bankroll)
        self._track_density(bankroll)
        self._mode(bankroll)

        amount = bankroll * self.fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)

        return round(amount, 2), round(self.multiplier, 4)

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.up += 1
            self.down = 0
            self._after_win()
        else:
            self.down += 1
            self.up = 0
            self._after_loss()

    def _track_density(self, bankroll: float) -> None:
        if bankroll >= 1000 and self.r1k is None:
            self.r1k = self.rounds

        if bankroll >= 10000 and self.r10k is None:
            self.r10k = self.rounds
            if self.r1k is not None and self.r10k - self.r1k <= 3:
                self.density_level = max(self.density_level, 1)

        if bankroll >= 25000 and self.r25k is None:
            self.r25k = self.rounds
            if self.r10k is not None and self.r25k - self.r10k <= 5:
                self.density_level = max(self.density_level, 2)

    def _mode(self, bankroll: float) -> None:
        if bankroll >= 85000:
            self.mode = "close"
            self.fraction = min(self.fraction, 0.10)
            self.multiplier = min(self.multiplier, 4.0)
        elif self.density_level >= 2:
            self.mode = "density_2"
            self.fraction = max(self.fraction, 0.26)
            self.multiplier = max(self.multiplier, 9.0)
        elif self.density_level >= 1:
            self.mode = "density_1"
            self.fraction = max(self.fraction, 0.22)
            self.multiplier = max(self.multiplier, 7.0)
        elif bankroll >= 50000:
            self.mode = "upper"
            self.fraction = min(self.fraction, 0.14)
            self.multiplier = min(self.multiplier, 6.0)
        elif self.rounds <= 500:
            self.mode = "base"
            self.fraction = max(self.fraction, self.base_fraction)
            self.multiplier = max(self.multiplier, self.base_multiplier)
        else:
            self.mode = "mid"

    def _after_win(self) -> None:
        if self.mode == "density_2":
            self.fraction = min(0.50, self.fraction * 1.22)
            self.multiplier = min(300.0, self.multiplier * 1.55)
        elif self.mode == "density_1":
            self.fraction = min(0.42, self.fraction * 1.16)
            self.multiplier = min(180.0, self.multiplier * 1.38)
        elif self.mode == "base":
            self.fraction = min(0.32, self.fraction * 1.12)
            if self.up >= 2:
                self.multiplier = min(80.0, self.multiplier * 1.18)
        elif self.mode in {"upper", "close"}:
            self.fraction = max(0.05, self.fraction * 0.97)
            self.multiplier = max(2.0, self.multiplier * 0.98)
        else:
            self.fraction = min(0.28, self.fraction * 1.08)
            self.multiplier = min(45.0, self.multiplier * 1.10)

    def _after_loss(self) -> None:
        if self.mode == "density_2":
            self.fraction = max(0.14, self.fraction * 0.90)
            self.multiplier = max(6.0, self.multiplier * 0.88)
        elif self.mode == "density_1":
            self.fraction = max(0.12, self.fraction * 0.90)
            self.multiplier = max(5.0, self.multiplier * 0.88)
        elif self.mode == "base":
            self.fraction = max(0.10, self.fraction * 0.89)
            self.multiplier = max(3.0, self.multiplier * 0.87)
        elif self.mode == "close":
            self.fraction = max(0.04, self.fraction * 0.90)
            self.multiplier = max(1.8, self.multiplier * 0.92)
        elif self.mode == "upper":
            self.fraction = max(0.05, self.fraction * 0.91)
            self.multiplier = max(2.0, self.multiplier * 0.92)
        else:
            self.fraction = max(0.06, self.fraction * 0.90)
            self.multiplier = max(2.2, self.multiplier * 0.88)
