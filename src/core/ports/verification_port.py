"""One application boundary for REST/MCP, one outgoing boundary for Blender."""

from typing import Protocol

from src.core.domain.verification import SuiteObservation, VerificationReport, VerificationSuite


class VerificationRunnerPort(Protocol):
    async def run_suite(self, suite: VerificationSuite) -> SuiteObservation: ...


class VerificationQueryPort(Protocol):
    async def list_suites(self) -> tuple[VerificationSuite, ...]: ...

    async def run(self, suite_id: str) -> VerificationReport: ...
