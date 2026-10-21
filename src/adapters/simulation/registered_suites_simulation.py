"""Mechanism simulation = the registered verification suites, run one after another."""

from __future__ import annotations

from src.core.domain.verification import VerificationReport
from src.core.ports.verification_port import VerificationQueryPort


class RegisteredSuitesSimulation:
    def __init__(self, verification: VerificationQueryPort) -> None:
        self._verification = verification

    async def run(self, suites: tuple[str, ...]) -> tuple[VerificationReport, ...]:
        # Sequential: the suites share one Blender scene and must not interleave.
        return tuple([await self._verification.run(suite_id) for suite_id in suites])
