from __future__ import annotations

from dataclasses import dataclass

from limbo100k.provably_fair import FairRoundProof, ProvablyFairRng


@dataclass
class LimboResult:
    target_multiplier: float
    rolled_multiplier: float
    won: bool
    profit: float
    nonce: int
    proof: FairRoundProof


class LimboEngine:
    """
    Fictional Limbo engine powered by a deterministic auditable RNG.

    The objective is not to predict outcomes, but to reproduce and audit every
    simulated outcome from a committed server seed, a client seed and a nonce.
    """

    def __init__(
        self,
        rng: ProvablyFairRng,
        house_edge: float = 0.99,
        max_multiplier: float = 1_000_000.0,
    ):
        if not 0 < house_edge <= 1:
            raise ValueError("house_edge must be between 0 and 1")
        if max_multiplier <= 1:
            raise ValueError("max_multiplier must be greater than 1")

        self.rng = rng
        self.house_edge = house_edge
        self.max_multiplier = max_multiplier
        self.nonce = 0

    def roll_multiplier(self, nonce: int | None = None) -> tuple[float, int, FairRoundProof]:
        selected_nonce = self.nonce if nonce is None else nonce
        uniform_value = self.rng.uniform_for_nonce(selected_nonce)
        multiplier = self.house_edge / uniform_value
        capped_multiplier = min(multiplier, self.max_multiplier)
        proof = self.rng.proof_for_nonce(selected_nonce)

        if nonce is None:
            self.nonce += 1

        return capped_multiplier, selected_nonce, proof

    def play(self, stake: float, target_multiplier: float) -> LimboResult:
        if stake <= 0:
            raise ValueError("stake must be greater than 0")
        if target_multiplier <= 1:
            raise ValueError("target_multiplier must be greater than 1")

        rolled, nonce, proof = self.roll_multiplier()
        won = rolled >= target_multiplier

        if won:
            profit = stake * (target_multiplier - 1)
        else:
            profit = -stake

        return LimboResult(
            target_multiplier=target_multiplier,
            rolled_multiplier=rolled,
            won=won,
            profit=profit,
            nonce=nonce,
            proof=proof,
        )
