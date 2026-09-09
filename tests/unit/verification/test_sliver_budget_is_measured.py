"""The sliver budget has to be at least as wide as what was actually measured.

`SLIVER_TRIANGLES_PER_PART` used to rest on the plan alone. A budget narrower
than the observed spread makes the package differential go red for no reason a
person can act on; this gate makes that impossible to ship unnoticed.

The budget is allowed to be *wider* than the measurement on purpose. Tightening
it to whatever the last run happened to see would make a floating number the
reference, and "A differs from B" carries no information when B moves.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.domain.hand_instances import HAND_INSTANCES
from src.verification.determinism_record import (
    DEFAULT_RECORD,
    MINIMUM_RUNS,
    load_determinism_record,
)
from src.verification.package_reproduction import SLIVER_TRIANGLES_PER_PART

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RECORD = PROJECT_ROOT / DEFAULT_RECORD


def _record():
    return load_determinism_record(RECORD)


def test_the_measurement_record_exists_and_says_when_it_was_taken() -> None:
    record = _record()

    assert record.measured_on
    assert record.runs >= MINIMUM_RUNS


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_every_registered_instance_has_been_measured(slug: str) -> None:
    """A new instance is unmeasured until someone runs the probe against it.
    Inheriting another instance's numbers is the mistake this whole gate exists
    to prevent."""
    assert slug in _record().spreads, f"{slug} has no determinism measurement"


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_the_budget_covers_the_measured_spread(slug: str) -> None:
    record = _record()
    measured = record.max_spread(slug)

    assert SLIVER_TRIANGLES_PER_PART >= measured, (
        f"{slug} was measured at {measured} triangles of spread on "
        f"{record.measured_on} but the budget is {SLIVER_TRIANGLES_PER_PART}"
    )


def test_every_measured_part_is_covered_not_only_the_worst_one() -> None:
    record = _record()
    for slug, parts in record.spreads.items():
        assert parts, f"{slug} records no parts"
        for part, spread in parts.items():
            assert SLIVER_TRIANGLES_PER_PART >= spread, f"{slug}/{part} spread {spread}"


def test_the_gate_fires_when_a_measurement_exceeds_the_budget(tmp_path: Path) -> None:
    """Should-fire. A gate with no failing fixture looks exactly like a gate that
    can never fail."""
    planted = tmp_path / "determinism.json"
    planted.write_text(
        json.dumps(
            {
                "measured_on": "2026-01-01",
                "runs": 4,
                "instances": {"hand-compact": {"parts": {"HH_PHALANX": 99}}},
            }
        ),
        encoding="utf-8",
    )

    record = load_determinism_record(planted)

    assert record.max_spread("hand-compact") > SLIVER_TRIANGLES_PER_PART


def test_a_single_run_is_refused_as_a_spread(tmp_path: Path) -> None:
    planted = tmp_path / "determinism.json"
    planted.write_text(
        json.dumps(
            {
                "measured_on": "2026-01-01",
                "runs": 1,
                "instances": {"hand-compact": {"parts": {"HH_PHALANX": 0}}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least"):
        load_determinism_record(planted)


def test_a_record_without_a_date_is_refused(tmp_path: Path) -> None:
    """A measurement snapshot with no date reads like a current fact forever."""
    planted = tmp_path / "determinism.json"
    planted.write_text(
        json.dumps({"runs": 4, "instances": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="measured_on"):
        load_determinism_record(planted)
