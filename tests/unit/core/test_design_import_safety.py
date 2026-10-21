"""Import-stage caps, hidden-path skip and path-free reports (review fix round 1)."""

from __future__ import annotations

import json
from dataclasses import replace

from src.core.domain.design_run import JobStatus, StageName, StageOutcome
from src.core.domain.import_limits import ImportLimits
from tests.unit.core.test_design_pipeline import _payload, _rig, _run


def _tight(rig, **kw):
    rig.pipeline._limits = replace(rig.pipeline._limits, **kw)


async def test_import_skips_hidden_and_non_stl_matches(tmp_path):
    rig = _rig(tmp_path)
    (rig.root / ".hidden").mkdir()
    (rig.root / ".hidden" / "x.stl").write_bytes(b"x")
    payload = _payload(rig)
    payload["source"]["stl_glob"] = "**/*.stl"
    _, _, report = await _run(rig, payload)
    assert report.stages[0].evidence == ("STL/a.stl", "STL/b.stl")


async def test_import_rejects_too_many_stls(tmp_path):
    rig = _rig(tmp_path)
    _tight(rig, max_stl_files=1)
    _, status, report = await _run(rig, _payload(rig))
    assert len(report.stages) == 1 and report.stages[0].outcome is StageOutcome.FAILED
    assert "2" in report.stages[0].message and "1" in report.stages[0].message
    assert rig.integrity.seen == () and status.status is JobStatus.FAILED


async def test_import_rejects_oversized_stl(tmp_path):
    rig = _rig(tmp_path)
    (rig.root / "STL" / "b.stl").write_bytes(b"x" * 50)
    _tight(rig, max_stl_bytes=10)
    _, _, report = await _run(rig, _payload(rig))
    assert report.stages[0].outcome is StageOutcome.FAILED
    assert report.stages[0].message.startswith("STL/b.stl:")
    assert rig.integrity.seen == ()


async def test_import_rejects_oversized_3mf(tmp_path):
    rig = _rig(tmp_path)
    (rig.root / "p.3mf").write_bytes(b"x" * 50)
    _tight(rig, max_3mf_bytes=10)
    _, _, report = await _run(rig, _payload(rig))
    assert report.stages[0].outcome is StageOutcome.FAILED
    assert report.stages[0].message.startswith("p.3mf:")
    assert rig.slicing.requests == []


def _leaks(text: str, tmp_path) -> list[str]:
    from pathlib import Path

    return [p for p in (str(tmp_path), str(Path.home())) if p in text]


async def test_report_json_has_no_absolute_paths(tmp_path):
    rig = _rig(tmp_path, geometry_ok=False)
    abs_a = str((rig.root / "STL" / "a.stl").resolve())

    original = rig.integrity.check

    async def check(stl_paths):
        verdicts = await original(stl_paths)
        return replace(
            verdicts,
            verdicts=tuple(replace(v, error=f"{v.path}: open edges") for v in verdicts.verdicts),
        )

    rig.pipeline._integrity.check = check
    job, _, report = await _run(rig, _payload(rig))
    text = (rig.runs / job.run_id / "report.json").read_text()
    assert _leaks(text, tmp_path) == [] and abs_a not in text
    assert "run_dir" not in json.loads(text)
    geometry = report.stages[1]
    assert geometry.name is StageName.GEOMETRY and "STL/a.stl: open edges" in geometry.message
    # the in-memory report still knows where it lives (rebuilt from runs_dir / run_id)
    assert report.run_dir == str(rig.runs / job.run_id)


def test_import_limits_is_frozen_data():
    limits = ImportLimits(1, 2, 3)
    assert (limits.max_stl_files, limits.max_stl_bytes, limits.max_3mf_bytes) == (1, 2, 3)
