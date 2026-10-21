"""report.json and spec.json persistence for a design run (atomic, sorted keys)."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

from src.core.domain.design_run import DesignRunReport, StageName, StageOutcome, StageReport

REPORT_NAME = "report.json"
SPEC_NAME = "spec.json"


def to_json(report: DesignRunReport) -> str:
    data = {
        "run_id": report.run_id,
        "spec_name": report.spec_name,
        "run_dir": report.run_dir,
        "passed": report.passed,
        "stages": [
            {
                "name": s.name.value,
                "outcome": s.outcome.value,
                "metrics": [list(pair) for pair in s.metrics],
                "evidence": list(s.evidence),
                "message": s.message,
            }
            for s in report.stages
        ],
    }
    return json.dumps(data, sort_keys=True, indent=2) + "\n"


def from_json(text: str) -> DesignRunReport:
    data = json.loads(text)
    parsed = tuple(
        StageReport(
            StageName(s["name"]),
            StageOutcome(s["outcome"]),
            tuple((k, v) for k, v in s["metrics"]),
            tuple(s["evidence"]),
            s["message"],
        )
        for s in data["stages"]
    )
    return DesignRunReport(data["run_id"], data["spec_name"], parsed, data["run_dir"])


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_report(report: DesignRunReport) -> None:
    _write_atomic(Path(report.run_dir) / REPORT_NAME, to_json(report))


def read_report(run_dir: Path) -> DesignRunReport | None:
    path = run_dir / REPORT_NAME
    if not path.is_file():
        return None
    return from_json(path.read_text(encoding="utf-8"))


def write_spec(run_dir: Path, payload: Mapping[str, object]) -> None:
    _write_atomic(run_dir / SPEC_NAME, json.dumps(payload, sort_keys=True, indent=2) + "\n")


def read_spec(run_dir: Path) -> object:
    return json.loads((run_dir / SPEC_NAME).read_text(encoding="utf-8"))
