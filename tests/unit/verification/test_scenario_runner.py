"""The shared runner must reject missing evidence and restore fixtures on every path."""

from dataclasses import replace

import pytest

from src.verification.scenario_runner import (
    Observation,
    Scenario,
    require_complete,
    run_scenarios,
)

CASES = (Scenario("clear", 0, "clear"), Scenario("contact", 1, "contact"))


def observe(value: int) -> Observation:
    return Observation("contact" if value else "clear", {"value": value})


def test_one_runner_executes_data_cases_with_stable_evidence() -> None:
    cleaned: list[int] = []
    rows = run_scenarios(CASES, observe, cleaned.append)
    require_complete(CASES, rows)
    assert cleaned == [0, 1]
    assert [r.evidence.name for r in rows] == ["clear", "contact"]
    assert rows[1].measurements == {"value": 1}


@pytest.mark.parametrize("mode", ["mismatch", "missing", "duplicate", "unexpected", "reordered"])
def test_incomplete_or_wrong_evidence_is_not_a_pass(mode: str) -> None:
    rows = run_scenarios(CASES, observe, lambda _: None)
    if mode == "mismatch":
        rows = run_scenarios(CASES, lambda _: Observation("clear", {}), lambda _: None)
    elif mode == "missing":
        rows = rows[:-1]
    elif mode == "duplicate":
        rows = (rows[0], rows[0])
    elif mode == "unexpected":
        rows = (*rows, replace(rows[0], evidence=replace(rows[0].evidence, name="extra")))
    else:
        rows = tuple(reversed(rows))
    with pytest.raises(ValueError):
        require_complete(CASES, rows)


def test_measurement_exception_is_failure_even_when_expected_text_matches() -> None:
    cleaned: list[int] = []

    def broken(value: int) -> Observation:
        raise RuntimeError("contact")

    rows = run_scenarios(CASES, broken, cleaned.append)
    assert cleaned == [0, 1]
    assert all(not r.evidence.passed for r in rows)
    assert "RuntimeError" in rows[0].evidence.detail
    with pytest.raises(ValueError):
        require_complete(CASES, rows)


def test_cleanup_failure_stops_before_next_case_and_fails_suite() -> None:
    observed: list[int] = []

    def recording(value: int) -> Observation:
        observed.append(value)
        return observe(value)

    def failed_cleanup(value: int) -> None:
        raise RuntimeError("restore failed")

    rows = run_scenarios(CASES, recording, failed_cleanup)
    assert observed == [0]
    assert not rows[0].evidence.passed
    assert "restore failed" in rows[0].evidence.detail
    with pytest.raises(ValueError):
        require_complete(CASES, rows)


@pytest.mark.parametrize("cases", [(), (CASES[0], CASES[0])])
def test_invalid_registry_is_rejected_before_touching_fixture(cases: tuple) -> None:
    with pytest.raises(ValueError):
        run_scenarios(cases, observe, lambda _: pytest.fail("fixture touched"))
