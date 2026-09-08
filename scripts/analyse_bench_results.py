"""Read the bench table and print the verdict, so recording numbers is the whole job.

`src/verification/paired_bench_statistics` does the statistics. This reads the
markdown people actually fill in and hands it over, because an analysis you have
to call from Python is the same handover in a different costume.

Every scenario is reported even when it has no data: an empty arm comes back
`vacuous`, which is the check working rather than the check waiting. The
smallest effect worth caring about is a required argument and has no default —
how much slip force matters is a decision about this hand.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.verification.paired_bench_statistics import (  # noqa: E402
    ScenarioVerdict,
    assess_scenario,
    holm_adjusted,
)

#: Ten objects, per the protocol. A scenario short of this is vacuous.
PLANNED_PAIRS = 10

#: Column order of the trial table in `docs/hand-v3/v8-results.md`.
_OBJECT = 1
_GLOVE = 2
_CONDITION = 3
_FORCE = 7

#: The comparisons the protocol defines, each one condition against another.
SCENARIOS: tuple[tuple[str, str, str, str], ...] = (
    ("S9", "未充氣", "充氣", "condition"),
    ("S10", "G1", "G2", "glove"),
    ("S11", "加壓", "抽真空", "condition"),
)


@dataclass(frozen=True, slots=True)
class BenchTrial:
    """One row of the table: one object, one condition, one slip force."""

    object_id: str
    glove_id: str
    condition: str
    slip_force_n: float


def parse_trials(document: str) -> list[BenchTrial]:
    """Rows that carry a number. The placeholder row is not a trial."""
    trials: list[BenchTrial] = []
    for line in document.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) <= _FORCE:
            continue
        try:
            force = float(cells[_FORCE])
        except ValueError:
            continue
        trials.append(
            BenchTrial(
                object_id=cells[_OBJECT],
                glove_id=cells[_GLOVE],
                condition=cells[_CONDITION],
                slip_force_n=force,
            )
        )
    return trials


def scenario_pairs(
    trials: list[BenchTrial], *, before: str, after: str, field: str = "condition"
) -> list[tuple[float, float]]:
    """Pair by object across two conditions, in the order the objects appear.

    An object measured in only one condition is dropped. Half a pair is not a
    pair, and filling in the other half is fabrication.
    """
    first: dict[str, float] = {}
    second: dict[str, float] = {}
    order: list[str] = []
    for trial in trials:
        value = trial.condition if field == "condition" else trial.glove_id
        if trial.object_id not in order:
            order.append(trial.object_id)
        if value == before:
            first[trial.object_id] = trial.slip_force_n
        elif value == after:
            second[trial.object_id] = trial.slip_force_n
    return [(first[name], second[name]) for name in order if name in first and name in second]


def scenario_verdicts(document: str, *, sesoi: float) -> list[ScenarioVerdict]:
    """One verdict per declared comparison, vacuous ones included."""
    trials = parse_trials(document)
    verdicts = [
        assess_scenario(
            name,
            scenario_pairs(trials, before=before, after=after, field=field),
            planned_pairs=PLANNED_PAIRS,
            sesoi=sesoi,
        )
        for name, before, after, field in SCENARIOS
    ]
    return verdicts


def report_lines(document: str, *, sesoi: float) -> list[str]:
    """The report a person reads. Magnitude and population always present."""
    verdicts = scenario_verdicts(document, sesoi=sesoi)
    lines = [verdict.summary for verdict in verdicts]

    measured = [verdict for verdict in verdicts if not verdict.vacuous]
    if measured:
        # The family is the set of comparisons that actually ran; correcting
        # across vacuous arms would inflate the correction with nothing.
        adjusted = holm_adjusted([verdict.p_value for verdict in measured])
        lines.append(
            "Holm across "
            + ", ".join(verdict.scenario for verdict in measured)
            + ": "
            + ", ".join(f"{value:.4f}" for value in adjusted)
        )
    else:
        lines.append("Holm: nothing to correct — every scenario is vacuous.")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=PROJECT_ROOT / "docs" / "hand-v3" / "v8-results.md",
    )
    parser.add_argument(
        "--sesoi",
        type=float,
        required=True,
        help="smallest slip-force difference worth caring about, in newtons",
    )
    args = parser.parse_args()

    if args.sesoi <= 0.0:
        parser.error("the smallest effect worth caring about must be positive")

    for line in report_lines(args.results.read_text(encoding="utf-8"), sesoi=args.sesoi):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
