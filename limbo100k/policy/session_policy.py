from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionPolicy:
    """Discipline policy for a simulated decision agent.

    The policy represents the key difference between a human and an automated
    agent: it follows predefined boundaries without hesitation or emotion.
    """

    max_retracement_fraction: float = 0.5
    objective_fraction: float = 2.0
    max_negative_sequence: int = 8
    minimum_capital: float = 0.0

    def evaluate(
        self,
        initial_capital: float,
        current_capital: float,
        peak_capital: float,
        negative_sequence: int,
    ) -> tuple[bool, str]:
        if current_capital <= self.minimum_capital:
            return True, "capital_floor"

        if peak_capital > 0:
            retracement = peak_capital - current_capital
            retracement_fraction = retracement / peak_capital
            if retracement_fraction >= self.max_retracement_fraction:
                return True, "retracement_boundary"

        if current_capital >= initial_capital * (1 + self.objective_fraction):
            return True, "objective_boundary"

        if negative_sequence >= self.max_negative_sequence:
            return True, "sequence_boundary"

        return False, "continue"
