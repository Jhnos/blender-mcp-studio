"""Port for running the mechanism checks a model spec declares."""

from __future__ import annotations

from typing import Protocol

from src.core.domain.verification import VerificationReport


class MechanismSimulationPort(Protocol):
    async def run(self, suites: tuple[str, ...]) -> tuple[VerificationReport, ...]: ...
