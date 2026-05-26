from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass


@dataclass(frozen=True)
class FairRoundProof:
    server_seed_hash: str
    client_seed: str
    nonce: int
    digest: str


class ProvablyFairRng:
    """Deterministic, auditable random source for a fictional multiplier lab.

    The server seed can be committed by publishing its SHA-256 hash first.
    Later, revealing the server seed allows anyone to verify that all generated
    values came from the same committed source.
    """

    def __init__(self, server_seed: str, client_seed: str):
        if not server_seed:
            raise ValueError("server_seed must not be empty")
        if not client_seed:
            raise ValueError("client_seed must not be empty")

        self.server_seed = server_seed
        self.client_seed = client_seed
        self.server_seed_hash = hashlib.sha256(server_seed.encode("utf-8")).hexdigest()

    def digest_for_nonce(self, nonce: int) -> str:
        if nonce < 0:
            raise ValueError("nonce must be positive or zero")

        message = f"{self.client_seed}:{nonce}".encode("utf-8")
        key = self.server_seed.encode("utf-8")
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    def uniform_for_nonce(self, nonce: int) -> float:
        digest = self.digest_for_nonce(nonce)
        integer_value = int(digest[:13], 16)
        max_value = int("f" * 13, 16)
        return (integer_value + 1) / (max_value + 1)

    def proof_for_nonce(self, nonce: int) -> FairRoundProof:
        return FairRoundProof(
            server_seed_hash=self.server_seed_hash,
            client_seed=self.client_seed,
            nonce=nonce,
            digest=self.digest_for_nonce(nonce),
        )

    @staticmethod
    def verify_server_seed(server_seed: str, committed_hash: str) -> bool:
        return hashlib.sha256(server_seed.encode("utf-8")).hexdigest() == committed_hash
