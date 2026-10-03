"""Verification delivery resolves registered suites and refuses incomplete evidence."""

from dataclasses import replace

import pytest

from src.core.domain.verification import (
    CheckResult,
    SuiteObservation,
    VerificationError,
    VerificationSuite,
)
from src.core.use_cases.verification import VerificationService

SUITE = VerificationSuite(
    "example", "Example", "Geometric checks only", (("a", "clear"), ("b", "contact"))
)


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.result = SuiteObservation(
            "example",
            (
                CheckResult("a", "clear", "clear", True, "clear"),
                CheckResult("b", "contact", "contact", True, "contact"),
            ),
            True,
        )

    async def run_suite(self, suite: VerificationSuite) -> SuiteObservation:
        self.calls.append(suite.suite_id)
        return self.result


@pytest.mark.asyncio
async def test_catalog_and_run_use_the_same_registered_suite() -> None:
    runner = FakeRunner()
    service = VerificationService(runner, (SUITE,))
    assert await service.list_suites() == (SUITE,)
    report = await service.run("example")
    assert report.passed and len(report.checks) == 2
    assert runner.calls == ["example"]


@pytest.mark.asyncio
async def test_unknown_suite_never_reaches_blender() -> None:
    runner = FakeRunner()
    with pytest.raises(VerificationError):
        await VerificationService(runner, (SUITE,)).run("../arbitrary.py")
    assert runner.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", ["missing", "duplicate", "wrong_suite", "unrestored", "forged_pass"]
)
async def test_incomplete_or_untrustworthy_observation_is_rejected(failure: str) -> None:
    runner = FakeRunner()
    if failure == "missing":
        runner.result = replace(runner.result, checks=runner.result.checks[:1])
    elif failure == "duplicate":
        runner.result = replace(runner.result, checks=(runner.result.checks[0],) * 2)
    elif failure == "wrong_suite":
        runner.result = replace(runner.result, suite_id="other")
    elif failure == "unrestored":
        runner.result = replace(runner.result, restored=False)
    else:
        runner.result = replace(
            runner.result,
            checks=(replace(runner.result.checks[0], observed="contact"), runner.result.checks[1]),
        )
    with pytest.raises(VerificationError):
        await VerificationService(runner, (SUITE,)).run("example")


@pytest.mark.asyncio
async def test_failed_check_is_a_report_not_a_transport_error() -> None:
    runner = FakeRunner()
    runner.result = replace(
        runner.result,
        checks=(
            replace(runner.result.checks[0], observed="contact", passed=False),
            runner.result.checks[1],
        ),
    )
    result = await VerificationService(runner, (SUITE,)).run("example")
    assert not result.passed
    assert result.checks[1].passed
