from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PhaseStateV22(str, Enum):
    EXPLORATION = "exploration"
    BREAKOUT = "breakout"
    DENSITY = "density"
    DIRECT_HYPER = "direct_hyper"
    HYPER = "hyper"
    CHAOS = "chaos"
    TERMINAL = "terminal"


class TrajectoryMode(str, Enum):
    UNKNOWN = "unknown"
    DIRECT_HYPER = "direct_hyper"
    CHAOTIC_REDENSITY = "chaotic_redensity"
    SLOW_SURVIVOR = "slow_survivor"


@dataclass
class PhaseStateV22Agent:
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
        self.state = PhaseStateV22.EXPLORATION
        self.mode = TrajectoryMode.UNKNOWN

        self.direct_hyper_attempts = 0
        self.direct_hyper_failed = False

        self.r1k: int | None = None
        self.r10k: int | None = None
        self.r25k: int | None = None
        self.r50k: int | None = None
        self.r100k: int | None = None

        self.density_1k_10k: int | None = None
        self.density_10k_25k: int | None = None
        self.density_25k_50k: int | None = None

        self.max_drawdown = 0.0
        self.transitions: list[dict] = []
        self.mode_transitions: list[dict] = []

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
        self._update_mode(bankroll, drawdown)
        self._transition(bankroll, drawdown)
        self._apply_state_floor()

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

    def _update_mode(self, bankroll: float, drawdown: float) -> None:
        previous = self.mode

        clean_direct_signal = (
            not self.direct_hyper_failed
            and self.density_10k_25k is not None
            and self.density_10k_25k <= 3
            and drawdown <= max(5000.0, self.peak * 0.12)
        )

        early_direct_signal = (
            not self.direct_hyper_failed
            and self.density_1k_10k is not None
            and self.density_1k_10k <= 6
            and drawdown <= max(3000.0, self.peak * 0.18)
        )

        if clean_direct_signal or early_direct_signal:
            self.mode = TrajectoryMode.DIRECT_HYPER
        elif drawdown >= max(18000.0, self.peak * 0.35):
            self.mode = TrajectoryMode.CHAOTIC_REDENSITY
        elif self.rounds >= 120 and bankroll < 10000:
            self.mode = TrajectoryMode.SLOW_SURVIVOR

        if self.mode != previous:
            self.mode_transitions.append(
                {
                    "round": self.rounds,
                    "from": previous.value,
                    "to": self.mode.value,
                    "bankroll": round(bankroll, 2),
                    "peak": round(self.peak, 2),
                    "drawdown": round(drawdown, 2),
                    "d1k10k": self.density_1k_10k,
                    "d10k25k": self.density_10k_25k,
                    "direct_failed": self.direct_hyper_failed,
                }
            )

    def _transition(self, bankroll: float, drawdown: float) -> None:
        previous = self.state

        if bankroll >= 90000:
            self.state = PhaseStateV22.TERMINAL
        elif self.state == PhaseStateV22.EXPLORATION and bankroll >= 1000:
            self.state = PhaseStateV22.BREAKOUT
        elif self.state in {PhaseStateV22.EXPLORATION, PhaseStateV22.BREAKOUT}:
            if self.density_1k_10k is not None and self.density_1k_10k <= 20:
                self.state = PhaseStateV22.DENSITY
        elif self.state == PhaseStateV22.DENSITY:
            if self.mode == TrajectoryMode.DIRECT_HYPER and not self.direct_hyper_failed:
                self.state = PhaseStateV22.DIRECT_HYPER
                self.direct_hyper_attempts += 1
            elif self.density_10k_25k is not None and self.density_10k_25k <= 15:
                self.state = PhaseStateV22.HYPER
        elif self.state == PhaseStateV22.DIRECT_HYPER:
            if self.down >= 1 or drawdown >= max(8000.0, self.peak * 0.18):
                self.direct_hyper_failed = True
                self.mode = TrajectoryMode.CHAOTIC_REDENSITY
                self.state = PhaseStateV22.HYPER
            elif drawdown >= max(18000.0, self.peak * 0.45):
                self.direct_hyper_failed = True
                self.mode = TrajectoryMode.CHAOTIC_REDENSITY
                self.state = PhaseStateV22.CHAOS
        elif self.state == PhaseStateV22.HYPER:
            if drawdown >= max(15000.0, self.peak * 0.45):
                self.state = PhaseStateV22.CHAOS
        elif self.state == PhaseStateV22.CHAOS:
            if self.up >= 2 or bankroll >= self.peak * 0.65:
                self.state = PhaseStateV22.HYPER

        if self.state != previous:
            self.transitions.append(
                {
                    "round": self.rounds,
                    "from": previous.value,
                    "to": self.state.value,
                    "mode": self.mode.value,
                    "bankroll": round(bankroll, 2),
                    "peak": round(self.peak, 2),
                    "drawdown": round(drawdown, 2),
                    "d1k10k": self.density_1k_10k,
                    "d10k25k": self.density_10k_25k,
                    "direct_failed": self.direct_hyper_failed,
                }
            )

    def _apply_state_floor(self) -> None:
        if self.state == PhaseStateV22.EXPLORATION:
            self.fraction = max(self.fraction, self.base_fraction)
            self.multiplier = max(self.multiplier, self.base_multiplier)
        elif self.state == PhaseStateV22.BREAKOUT:
            self.fraction = max(self.fraction, 0.20)
            self.multiplier = max(self.multiplier, 6.0)
        elif self.state == PhaseStateV22.DENSITY:
            self.fraction = max(self.fraction, 0.25)
            self.multiplier = max(self.multiplier, 8.5)
        elif self.state == PhaseStateV22.DIRECT_HYPER:
            self.fraction = max(self.fraction, 0.32)
            self.multiplier = max(self.multiplier, 12.0)
        elif self.state == PhaseStateV22.HYPER:
            self.fraction = max(self.fraction, 0.30)
            self.multiplier = max(self.multiplier, 11.0)
        elif self.state == PhaseStateV22.CHAOS:
            self.fraction = max(self.fraction, 0.22)
            self.multiplier = max(self.multiplier, 8.0)
        elif self.state == PhaseStateV22.TERMINAL:
            if self.mode == TrajectoryMode.DIRECT_HYPER and not self.direct_hyper_failed:
                self.fraction = max(self.fraction, 0.16)
                self.multiplier = max(self.multiplier, 7.0)
            else:
                self.fraction = min(self.fraction, 0.12)
                self.multiplier = min(self.multiplier, 4.5)

    def _after_win(self) -> None:
        if self.state == PhaseStateV22.EXPLORATION:
            self.fraction = min(0.32, self.fraction * 1.12)
            if self.up >= 2:
                self.multiplier = min(80.0, self.multiplier * 1.18)
        elif self.state == PhaseStateV22.BREAKOUT:
            self.fraction = min(0.38, self.fraction * 1.14)
            self.multiplier = min(110.0, self.multiplier * 1.25)
        elif self.state == PhaseStateV22.DENSITY:
            self.fraction = min(0.46, self.fraction * 1.18)
            self.multiplier = min(200.0, self.multiplier * 1.38)
        elif self.state == PhaseStateV22.DIRECT_HYPER:
            self.fraction = min(0.54, self.fraction * 1.20)
            self.multiplier = min(260.0, self.multiplier * 1.45)
        elif self.state == PhaseStateV22.HYPER:
            self.fraction = min(0.56, self.fraction * 1.24)
            self.multiplier = min(350.0, self.multiplier * 1.58)
        elif self.state == PhaseStateV22.CHAOS:
            self.fraction = min(0.42, self.fraction * 1.12)
            self.multiplier = min(160.0, self.multiplier * 1.24)
        elif self.state == PhaseStateV22.TERMINAL:
            if self.mode == TrajectoryMode.DIRECT_HYPER and not self.direct_hyper_failed:
                self.fraction = min(0.36, self.fraction * 1.05)
                self.multiplier = min(90.0, self.multiplier * 1.12)
            else:
                self.fraction = max(0.05, self.fraction * 0.97)
                self.multiplier = max(2.0, self.multiplier * 0.98)

    def _after_loss(self) -> None:
        if self.state == PhaseStateV22.EXPLORATION:
            self.fraction = max(0.10, self.fraction * 0.89)
            self.multiplier = max(3.0, self.multiplier * 0.87)
        elif self.state == PhaseStateV22.BREAKOUT:
            self.fraction = max(0.11, self.fraction * 0.90)
            self.multiplier = max(3.5, self.multiplier * 0.88)
        elif self.state == PhaseStateV22.DENSITY:
            self.fraction = max(0.14, self.fraction * 0.90)
            self.multiplier = max(5.5, self.multiplier * 0.88)
        elif self.state == PhaseStateV22.DIRECT_HYPER:
            self.direct_hyper_failed = True
            self.mode = TrajectoryMode.CHAOTIC_REDENSITY
            self.fraction = max(0.17, self.fraction * 0.86)
            self.multiplier = max(7.0, self.multiplier * 0.82)
        elif self.state == PhaseStateV22.HYPER:
            self.fraction = max(0.17, self.fraction * 0.90)
            self.multiplier = max(7.0, self.multiplier * 0.88)
        elif self.state == PhaseStateV22.CHAOS:
            self.fraction = max(0.18, self.fraction * 0.96)
            self.multiplier = max(6.5, self.multiplier * 0.94)
        elif self.state == PhaseStateV22.TERMINAL:
            if self.mode == TrajectoryMode.DIRECT_HYPER and not self.direct_hyper_failed:
                self.fraction = max(0.10, self.fraction * 0.90)
                self.multiplier = max(4.5, self.multiplier * 0.90)
            else:
                self.fraction = max(0.04, self.fraction * 0.90)
                self.multiplier = max(1.8, self.multiplier * 0.92)
