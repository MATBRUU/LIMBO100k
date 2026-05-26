from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class LimboResult:
    target_multiplier: float
    rolled_multiplier: float
    won: bool
    profit: float


class LimboEngine:
    """
    Fictional Limbo engine.

    This engine reproduces a simplified probabilistic environment
    inspired by Limbo-style mechanics.
    """

    def __init__(self, house_edge: float = 0.99, max_multiplier: float = 1_000_000.0):
        self.house_edge = house_edge
        self.max_multiplier = max_multiplier

    def roll_multiplier(self) -> float:
        r = random.random()
        multiplier = self.house_edge / (1.0 - r)
        return min(multiplier, self.max_multiplier)

    def play(self, bet_amount: float, target_multiplier: float) -> LimboResult:
        rolled = self.roll_multiplier()
        won = rolled >= target_multiplier

        if won:
            profit = bet_amount * (target_multiplier - 1)
        else:
            profit = -bet_amount

        return LimboResult(
            target_multiplier=target_multiplier,
            rolled_multiplier=rolled,
            won=won,
            profit=profit,
        )
