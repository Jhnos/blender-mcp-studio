"""Client-neutral catalog and evidence for registered model checks."""

from dataclasses import dataclass

from src.core.domain.exceptions import DomainError


class VerificationError(DomainError):
    """Unknown suite, unmet precondition or untrustworthy verification evidence."""


@dataclass(frozen=True, slots=True)
class VerificationSuite:
    suite_id: str
    title: str
    scope: str
    cases: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    expected: str
    observed: str | None
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class SuiteObservation:
    suite_id: str
    checks: tuple[CheckResult, ...]
    restored: bool


@dataclass(frozen=True, slots=True)
class VerificationReport:
    suite_id: str
    passed: bool
    checks: tuple[CheckResult, ...]
    scope: str
    scene_restored: bool
