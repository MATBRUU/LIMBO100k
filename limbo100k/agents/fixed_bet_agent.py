from dataclasses import dataclass


@dataclass
class FixedBetAgent:
    bet_size: float = 1.0
    target_multiplier: float = 2.0

    def next_bet(self, bankroll: float) -> tuple[float, float]:
        if bankroll <= 0:
            return 0.0, self.target_multiplier

        amount = min(self.bet_size, bankroll)
        return amount, self.target_multiplier
