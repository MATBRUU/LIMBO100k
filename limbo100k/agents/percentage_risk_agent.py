from dataclasses import dataclass


@dataclass
class PercentageRiskAgent:
    risk_fraction: float = 0.02
    target_multiplier: float = 2.0
    minimum_stake: float = 0.1

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        if bankroll <= 0:
            return 0.0, self.target_multiplier

        if not 0 < self.risk_fraction <= 1:
            raise ValueError("risk_fraction must be between 0 and 1")

        amount = bankroll * self.risk_fraction
        amount = max(amount, self.minimum_stake)
        amount = min(amount, bankroll)
        return round(amount, 2), self.target_multiplier
