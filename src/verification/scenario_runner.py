"""Data cases, independent observations and fixture cleanup share one fail-closed runner."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

from src.verification.generated_artifact_verdict import VerificationEvidence, VerificationSummary

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Scenario(Generic[T]):
    name: str
    inputs: T
    expected: str


@dataclass(frozen=True, slots=True)
class Observation:
    outcome: str
    measurements: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    evidence: VerificationEvidence
    expected: str
    observed: str | None
    measurements: Mapping[str, object]


def _validate(cases: tuple[Scenario[T], ...]) -> None:
    names = [case.name for case in cases]
    if not names or len(set(names)) != len(names):
        raise ValueError("Scenario registry must be nonempty with unique names")
    if any(not case.name.strip() or not case.expected.strip() for case in cases):
        raise ValueError("Scenario names and expectations must be nonempty")


def run_scenarios(
    cases: tuple[Scenario[T], ...],
    observe: Callable[[T], Observation],
    cleanup: Callable[[T], None],
) -> tuple[ScenarioResult, ...]:
    """Cleanup is mandatory even after observation fails; failed cleanup stops the suite."""
    _validate(cases)
    results = []
    for case in cases:
        observation = None
        errors = []
        cleaned = True
        try:
            observation = observe(case.inputs)
        except Exception as error:
            errors.append(f"observation: {type(error).__name__}: {error}")
        finally:
            try:
                cleanup(case.inputs)
            except Exception as error:
                errors.append(f"cleanup: {type(error).__name__}: {error}")
                cleaned = False
        observed = observation.outcome if observation is not None else None
        detail = "; ".join(errors) or f"observed={observed!r}, expected={case.expected!r}"
        results.append(
            ScenarioResult(
                VerificationEvidence(case.name, not errors and observed == case.expected, detail),
                case.expected,
                observed,
                observation.measurements if observation is not None else {},
            )
        )
        if not cleaned:
            break
    return tuple(results)


def require_complete(cases: tuple[Scenario[T], ...], results: tuple[ScenarioResult, ...]) -> None:
    """No skip/partial/duplicate/reordered evidence can satisfy a declared registry."""
    _validate(cases)
    expected = [(case.name, case.expected) for case in cases]
    observed = [(row.evidence.name, row.expected) for row in results]
    if expected != observed:
        raise ValueError(f"Scenario coverage differs: expected={expected!r}, observed={observed!r}")
    summary = VerificationSummary(tuple(row.evidence for row in results))
    if not summary.passed:
        failures = [row.detail for row in summary.evidence if not row.passed]
        raise ValueError(f"Scenario checks failed: {failures!r}")
