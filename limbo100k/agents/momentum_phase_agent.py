from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MomentumPhaseAgent:
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
        self.hyper_mode = False

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        self.rounds += 1

        if bankroll <= 0:
            return 0.0, self.multiplier

        if self.start is None:
            self.start = bankroll
            self.peak = bankroll

        self.peak = max(self.peak, bankroll)
        ratio = bankroll / self.start
        self._mode(ratio, bankroll)

        amount = bankroll * self.fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)

        return round(amount, 2), round(self.multiplier, 4)

    def observe(self, won: bool, bankroll: float) -> None:
        if won:
            self.up += 1
            self.down = 0
            self._after_win(bankroll)
        else:
            self.down += 1
            self.up = 0
            self.hyper_mode = False
            self._after_loss()

    def _mode(self, ratio: float, bankroll: float) -> None:
        if bankroll >= 85000:
            self.mode = "close"
            self.fraction = min(self.fraction, 0.08)
            self.multiplier = min(self.multiplier, 3.0)
        elif bankroll >= 50000:
            self.mode = "upper"
            self.fraction = min(self.fraction, 0.12)
            self.multiplier = min(self.multiplier, 5.0)
        elif ratio >= 20 and self.up >= 3:
            self.mode = "hyper"
            self.hyper_mode = True
        elif self.rounds <= 500:
            self.mode = "base"
            self.fraction = max(self.fraction, self.base_fraction)
            self.multiplier = max(self.multiplier, self.base_multiplier)
        else:
            self.mode = "mid"

    def _after_win(self, bankroll: float) -> None:
        if self.mode == "hyper":
            self.fraction = min(0.45, self.fraction * 1.20)
            self.multiplier = min(250.0, self.multiplier * 1.45)

        elif self.mode == "base":
            self.fraction = min(0.32, self.fraction * 1.12)

            if self.up >= 2:
                self.multiplier = min(80.0, self.multiplier * 1.18)

            if bankroll >= self.start * 10 and self.up >= 3:
                self.hyper_mode = True
                self.multiplier = min(120.0, self.multiplier * 1.35)
                self.fraction = min(0.38, self.fraction * 1.15)

        elif self.mode in {"upper", "close"}:
            self.fraction = max(0.04, self.fraction * 0.95)
            self.multiplier = max(2.0, self.multiplier * 0.97)

        else:
            self.fraction = min(0.26, self.fraction * 1.08)
            self.multiplier = min(40.0, self.multiplier * 1.10)

    def _after_loss(self) -> None:
        if self.mode == "hyper":
            self.fraction = max(0.12, self.fraction * 0.92)
            self.multiplier = max(6.0, self.multiplier * 0.90)

        elif self.mode == "base":
            self.fraction = max(0.10, self.fraction * 0.89)
            self.multiplier = max(3.0, self.multiplier * 0.87)

        elif self.mode == "close":
            self.fraction = max(0.03, self.fraction * 0.90)
            self.multiplier = max(1.8, self.multiplier * 0.92)

        elif self.mode == "upper":
            self.fraction = max(0.04, self.fraction * 0.91)
            self.multiplier = max(2.0, self.multiplier * 0.92)

        else:
            self.fraction = max(0.06, self.fraction * 0.90)
            self.multiplier = max(2.2, self.multiplier * 0.88)
