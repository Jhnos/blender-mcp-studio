"""report.json and spec.json persistence for a design run (atomic, sorted keys).

``run_dir`` is never serialised (no host path in evidence); reads rebuild it from the
directory the report was read from.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

from src.core.domain.design_run import (
    DesignRunReport,
    JobRecord,
    StageName,
    StageOutcome,
    StageReport,
)

REPORT_NAME = "report.json"
SPEC_NAME = "spec.json"


def to_json(report: DesignRunReport) -> str:
    data = {
        "run_id": report.run_id,
        "spec_name": report.spec_name,
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


def from_json(text: str, run_dir: str) -> DesignRunReport:
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
    return DesignRunReport(data["run_id"], data["spec_name"], parsed, run_dir)


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
    return from_json(path.read_text(encoding="utf-8"), str(run_dir))


def write_evidence(run_dir: Path, name: str, data: Mapping[str, object]) -> None:
    """One stage evidence document (``import.json``, ``geometry.json``), atomic and sorted."""
    _write_atomic(run_dir / name, json.dumps(data, sort_keys=True, indent=2) + "\n")


def write_spec(run_dir: Path, payload: Mapping[str, object]) -> None:
    _write_atomic(run_dir / SPEC_NAME, json.dumps(payload, sort_keys=True, indent=2) + "\n")


def read_spec(run_dir: Path) -> object:
    return json.loads((run_dir / SPEC_NAME).read_text(encoding="utf-8"))


def record_interruption(run_dir: Path, job: JobRecord, message: str) -> None:
    """Keep orphan-job report persistence here, alongside every other report write."""
    if job.stage is None:
        return
    try:
        existing = read_report(run_dir)
    except (ValueError, KeyError, OSError):
        existing = DesignRunReport(job.run_id, "", (), str(run_dir))
    if existing is None or (existing.stages and existing.stages[-1].name is job.stage):
        return
    failed = StageReport(job.stage, StageOutcome.FAILED, (), (), message)
    write_report(
        DesignRunReport(
            existing.run_id, existing.spec_name, (*existing.stages, failed), existing.run_dir
        )
    )
