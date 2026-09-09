"""The measured spread of triangle counts across repeated builds of one part.

`SLIVER_TRIANGLES_PER_PART` says a booleaned part may come back two triangles
different from the shipped one. That number was derived from the plan and never
measured, which is the shape this project has already been bitten by: an exact
gate calibrated on one instance that happened to reproduce, red on the second.

This module reads the record `scripts/verify/build_determinism_probe.py` writes,
so a gate can compare the budget against something that was actually observed.

The record carries its measurement date and how many runs produced it, because
a measurement snapshot with no date cannot be told apart from a current fact,
and a spread measured across one run is not a spread at all.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src.infrastructure.narrowing import as_int, as_positive_int, as_str_keyed_exact, required

#: The measurement this repository ships with.
DEFAULT_RECORD = Path("docs/hand-framework/determinism.json")

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MINIMUM_RUNS = 2


@dataclass(frozen=True, slots=True)
class DeterminismRecord:
    measured_on: str
    runs: int
    #: instance slug -> part name -> largest triangle-count difference seen.
    spreads: Mapping[str, Mapping[str, int]]

    def max_spread(self, slug: str) -> int:
        """The worst part in one instance.

        An unmeasured instance raises rather than answering 0. Answering 0 would
        report "nothing was seen to differ" for something nobody looked at, and
        a `KeyError` says only that a dict lookup failed.
        """
        if slug not in self.spreads:
            raise KeyError(
                f"{slug} has no determinism measurement in this record "
                f"(taken {self.measured_on}); run build_determinism_probe.py --instance {slug}"
            )
        return max(self.spreads[slug].values(), default=0)


def load_determinism_record(path: Path) -> DeterminismRecord:
    source = required(
        json.loads(path.read_text(encoding="utf-8")),
        as_str_keyed_exact,
        message=f"{path.name} must contain one JSON object",
        error=ValueError,
    )
    measured_on = source.get("measured_on")
    if not isinstance(measured_on, str) or not _DATE.match(measured_on):
        raise ValueError(f"{path.name} needs measured_on as YYYY-MM-DD, got {measured_on!r}")
    runs = as_positive_int(source.get("runs"))
    if runs is None or runs < MINIMUM_RUNS:
        raise ValueError(
            f"{path.name} records {source.get('runs')!r} runs; a spread needs at least "
            f"{MINIMUM_RUNS} builds to exist"
        )
    instances = required(
        source.get("instances"),
        as_str_keyed_exact,
        message=f"{path.name} needs an instances object",
        error=ValueError,
    )
    spreads: dict[str, dict[str, int]] = {}
    for slug, payload in instances.items():
        parts = required(
            (as_str_keyed_exact(payload) or {}).get("parts"),
            as_str_keyed_exact,
            message=f"{path.name}: {slug} needs a parts object",
            error=ValueError,
        )
        measured: dict[str, int] = {}
        for part, value in parts.items():
            spread = as_int(value)
            if spread is None or spread < 0:
                raise ValueError(f"{path.name}: {slug}/{part} spread is not a count: {value!r}")
            measured[part] = spread
        spreads[slug] = measured
    return DeterminismRecord(measured_on=measured_on, runs=runs, spreads=spreads)
