from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PhaseState(str, Enum):
    EXPLORATION = "exploration"
    BREAKOUT = "breakout"
    DENSITY = "density"
    HYPER = "hyper"
    SURVIVOR = "survivor"
    TERMINAL = "terminal"


@dataclass
class PhaseStateAgent:
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
        self.state = PhaseState.EXPLORATION
        self.previous_state = self.state

        self.r1k: int | None = None
        self.r10k: int | None = None
        self.r25k: int | None = None
        self.r50k: int | None = None
        self.r100k: int | None = None

        self.density_1k_10k: int | None = None
        self.density_10k_25k: int | None = None
        self.density_25k_50k: int | None = None

        self.max_drawdown = 0.0
        self.last_transition_round = 0
        self.state_transitions: list[dict] = []

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        self.rounds += 1

        if bankroll <= 0:
            return 0.0, self.multiplier

        if self.start is None:
            self.start = bankroll
            self.peak = bankroll

        self.peak = max(self.peak, bankroll)
        drawdown = self.peak - bankroll
        self.max_drawdown = max(self.max_drawdown, drawdown)

        self._track_thresholds(bankroll)
        self._transition(bankroll, drawdown)
        self._apply_state_floor(bankroll, drawdown)

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

    def _track_thresholds(self, bankroll: float) -> None:
        if bankroll >= 1000 and self.r1k is None:
            self.r1k = self.rounds

        if bankroll >= 10000 and self.r10k is None:
            self.r10k = self.rounds
            if self.r1k is not None:
                self.density_1k_10k = self.r10k - self.r1k

        if bankroll >= 25000 and self.r25k is None:
            self.r25k = self.rounds
            if self.r10k is not None:
                self.density_10k_25k = self.r25k - self.r10k

        if bankroll >= 50000 and self.r50k is None:
            self.r50k = self.rounds
            if self.r25k is not None:
                self.density_25k_50k = self.r50k - self.r25k

        if bankroll >= 100000 and self.r100k is None:
            self.r100k = self.rounds

    def _transition(self, bankroll: float, drawdown: float) -> None:
        previous = self.state

        if bankroll >= 85000:
            self.state = PhaseState.TERMINAL
        elif self.state == PhaseState.EXPLORATION and bankroll >= 1000:
            self.state = PhaseState.BREAKOUT
        elif self.state in {PhaseState.EXPLORATION, PhaseState.BREAKOUT}:
            if self.density_1k_10k is not None and self.density_1k_10k <= 15:
                self.state = PhaseState.DENSITY
        elif self.state == PhaseState.DENSITY:
            if self.density_10k_25k is not None and self.density_10k_25k <= 10:
                self.state = PhaseState.HYPER
        elif self.state == PhaseState.HYPER:
            if drawdown >= max(10000.0, self.peak * 0.35):
                self.state = PhaseState.SURVIVOR
        elif self.state == PhaseState.SURVIVOR:
            if self.up >= 3 or bankroll >= self.peak * 0.85:
                self.state = PhaseState.HYPER

        if self.state != previous:
            self.previous_state = previous
            self.last_transition_round = self.rounds
            self.state_transitions.append(
                {
                    "round": self.rounds,
                    "from": previous.value,
                    "to": self.state.value,
                    "bankroll": round(bankroll, 2),
                    "peak": round(self.peak, 2),
                    "drawdown": round(drawdown, 2),
                    "d1k10k": self.density_1k_10k,
                    "d10k25k": self.density_10k_25k,
                }
            )

    def _apply_state_floor(self, bankroll: float, drawdown: float) -> None:
        if self.state == PhaseState.EXPLORATION:
            self.fraction = max(self.fraction, self.base_fraction)
            self.multiplier = max(self.multiplier, self.base_multiplier)

        elif self.state == PhaseState.BREAKOUT:
            self.fraction = max(self.fraction, 0.20)
            self.multiplier = max(self.multiplier, 6.0)

        elif self.state == PhaseState.DENSITY:
            self.fraction = max(self.fraction, 0.24)
            self.multiplier = max(self.multiplier, 8.0)

        elif self.state == PhaseState.HYPER:
            self.fraction = max(self.fraction, 0.28)
            self.multiplier = max(self.multiplier, 10.0)

        elif self.state == PhaseState.SURVIVOR:
            self.fraction = max(self.fraction, 0.18)
            self.multiplier = max(self.multiplier, 6.0)

        elif self.state == PhaseState.TERMINAL:
            self.fraction = min(self.fraction, 0.10)
            self.multiplier = min(self.multiplier, 4.0)

    def _after_win(self) -> None:
        if self.state == PhaseState.EXPLORATION:
            self.fraction = min(0.32, self.fraction * 1.12)
            if self.up >= 2:
                self.multiplier = min(80.0, self.multiplier * 1.18)

        elif self.state == PhaseState.BREAKOUT:
            self.fraction = min(0.36, self.fraction * 1.13)
            self.multiplier = min(100.0, self.multiplier * 1.24)

        elif self.state == PhaseState.DENSITY:
            self.fraction = min(0.44, self.fraction * 1.17)
            self.multiplier = min(180.0, self.multiplier * 1.36)

        elif self.state == PhaseState.HYPER:
            self.fraction = min(0.52, self.fraction * 1.22)
            self.multiplier = min(320.0, self.multiplier * 1.55)

        elif self.state == PhaseState.SURVIVOR:
            self.fraction = min(0.34, self.fraction * 1.08)
            self.multiplier = min(120.0, self.multiplier * 1.16)

        elif self.state == PhaseState.TERMINAL:
            self.fraction = max(0.04, self.fraction * 0.96)
            self.multiplier = max(2.0, self.multiplier * 0.97)

    def _after_loss(self) -> None:
        if self.state == PhaseState.EXPLORATION:
            self.fraction = max(0.10, self.fraction * 0.89)
            self.multiplier = max(3.0, self.multiplier * 0.87)

        elif self.state == PhaseState.BREAKOUT:
            self.fraction = max(0.11, self.fraction * 0.90)
            self.multiplier = max(3.5, self.multiplier * 0.88)

        elif self.state == PhaseState.DENSITY:
            self.fraction = max(0.13, self.fraction * 0.90)
            self.multiplier = max(5.0, self.multiplier * 0.88)

        elif self.state == PhaseState.HYPER:
            self.fraction = max(0.15, self.fraction * 0.90)
            self.multiplier = max(6.0, self.multiplier * 0.88)

        elif self.state == PhaseState.SURVIVOR:
            self.fraction = max(0.14, self.fraction * 0.94)
            self.multiplier = max(5.0, self.multiplier * 0.92)

        elif self.state == PhaseState.TERMINAL:
            self.fraction = max(0.03, self.fraction * 0.90)
            self.multiplier = max(1.8, self.multiplier * 0.92)
