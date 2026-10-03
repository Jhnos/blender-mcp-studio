"""Registered verification shared by all delivery paths; no Blender dialect here."""

from src.core.domain.verification import VerificationError, VerificationReport, VerificationSuite
from src.core.ports.verification_port import VerificationRunnerPort


class VerificationService:
    def __init__(
        self, runner: VerificationRunnerPort, suites: tuple[VerificationSuite, ...]
    ) -> None:
        if not suites or len({s.suite_id for s in suites}) != len(suites):
            raise ValueError("Verification catalog must be nonempty and unique")
        for suite in suites:
            if not suite.cases or len({name for name, _ in suite.cases}) != len(suite.cases):
                raise ValueError("Suite cases must be nonempty and unique")
        self._runner = runner
        self._suites = {suite.suite_id: suite for suite in suites}

    async def list_suites(self) -> tuple[VerificationSuite, ...]:
        return tuple(self._suites.values())

    async def run(self, suite_id: str) -> VerificationReport:
        suite = self._suites.get(suite_id)
        if suite is None:
            raise VerificationError(f"Unknown verification suite: {suite_id!r}")
        observation = await self._runner.run_suite(suite)
        if observation.suite_id != suite_id or not observation.restored:
            raise VerificationError(
                "Verification did not confirm the requested suite and scene restoration"
            )
        if tuple((c.name, c.expected) for c in observation.checks) != suite.cases:
            raise VerificationError("Verification returned missing, duplicated or unexpected cases")
        if any(c.passed and c.observed != c.expected for c in observation.checks):
            raise VerificationError("Verification success contradicts measured evidence")
        return VerificationReport(
            suite_id,
            all(c.passed for c in observation.checks),
            observation.checks,
            suite.scope,
            observation.restored,
        )
