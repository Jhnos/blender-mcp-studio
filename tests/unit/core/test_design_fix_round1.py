"""Fix round 1: host paths at the boundary, one import gate, no orphan dirs, lease lifetime."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.adapters.slicing.orca_family_cli import OrcaFamilyCli
from src.core.domain.design_run import JobStatus, StageName, StageOutcome
from src.core.domain.packaging import ToolUse
from src.core.domain.slicing import SliceResult
from src.infrastructure.printer_catalog_loader import load_printer_catalog
from tests.unit.core.test_design_pipeline import _payload, _rig, _run


def missing_slicers(tmp_path: Path) -> OrcaFamilyCli:
    """The real adapter on a host with neither slicer installed."""
    binaries = {
        "bambu-studio": tmp_path / "nope" / "BambuStudio",
        "orcaslicer": tmp_path / "nope" / "OrcaSlicer",
    }
    return OrcaFamilyCli(load_printer_catalog(), binaries, overrides_dir=tmp_path)


def _real_missing_slicer(rig, tmp_path: Path) -> None:
    rig.slicing = missing_slicers(tmp_path)
    rig.pipeline._slicing = rig.slicing


def _leaks(text: str, tmp_path: Path) -> list[str]:
    return [p for p in (str(tmp_path), str(Path.home())) if p in text]


async def test_pipeline_job_error_has_no_host_path(tmp_path):
    rig = _rig(tmp_path)
    # Submit now accepts only printers whose slicer is installed, so the slicer goes missing
    # between submit and run (the run task has not started before the next await).
    job = await rig.pipeline.submit(_payload(rig))
    _real_missing_slicer(rig, tmp_path)
    await rig.pipeline.wait_idle()
    status, report = await rig.pipeline.status(job.job_id), await rig.pipeline.report(job.run_id)
    last = report.stages[-1]
    assert last.name is StageName.PRINT and last.outcome is StageOutcome.FAILED
    assert "not available" in last.message
    assert status.status is JobStatus.FAILED
    blob = json.dumps(
        [status.error, last.message, (rig.runs / job.run_id / "report.json").read_text()]
    )
    assert _leaks(blob, tmp_path) == []


async def test_stage_and_job_messages_are_scrubbed_at_the_choke_point(tmp_path):
    rig = _rig(tmp_path)
    rig.slicing.error = RuntimeError(f"boom at {tmp_path}/secret/place and {Path.home()}/x")
    job, status, report = await _run(rig, _payload(rig))
    blob = json.dumps([status.error, report.stages[-1].message])
    assert _leaks(blob, tmp_path) == [] and "boom at" in blob
    assert _leaks((rig.runs / job.run_id / "report.json").read_text(), tmp_path) == []


async def test_slice_file_failure_leaves_no_run_dir(tmp_path):
    rig = _rig(tmp_path)
    rig.slicing.error = RuntimeError("slicer exploded")
    with pytest.raises(RuntimeError):
        await rig.pipeline.slice_file("artifact/p.3mf", "bambu-p2s")
    assert not rig.runs.exists() or list(rig.runs.iterdir()) == []


async def test_slice_file_unavailable_tool_is_a_failed_result_and_leaves_no_dir(tmp_path):
    rig = _rig(tmp_path)
    _real_missing_slicer(rig, tmp_path)
    result = await rig.pipeline.slice_file("artifact/p.3mf", "bambu-p2s")
    assert result.passed is False and "not available" in result.message
    assert _leaks(repr(result), tmp_path) == []
    assert not rig.runs.exists() or list(rig.runs.iterdir()) == []


class BlockingSlicing:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def slice(self, request):
        self.started.set()
        await self.release.wait()
        return SliceResult(
            True, f"{request.output_dir}/o.3mf", None, f"{request.output_dir}/l", 0, "ok"
        )

    def printers(self):  # A4: submit checks the slicer's usable printers
        return (load_printer_catalog().printer("bambu-p2s-0.4"),)

    async def availability(self):
        raise AssertionError("not used")

    def tool_for(self, printer_id):
        return ToolUse("bambu-studio", "02.06.00.51", "AGPL-3.0-only", "subprocess")

    def check_target(self, printer_id, layer_height, material):
        return ()


async def test_cancelled_slice_holds_lease_until_slicer_returns(tmp_path):
    rig = _rig(tmp_path)
    blocking = BlockingSlicing()
    rig.pipeline._slicing = blocking
    task = asyncio.create_task(rig.pipeline.slice_file("artifact/p.3mf", "bambu-p2s"))
    await asyncio.wait_for(blocking.started.wait(), 2)
    task.cancel()
    await asyncio.sleep(0.05)
    assert rig.lease.holder is StageName.PRINT and not task.done()
    blocking.release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert rig.lease.holder is None


async def test_cancelled_print_stage_holds_lease_until_slicer_returns(tmp_path):
    rig = _rig(tmp_path)
    blocking = BlockingSlicing()
    rig.pipeline._slicing = blocking
    job = await rig.pipeline.submit(_payload(rig))
    await asyncio.wait_for(blocking.started.wait(), 2)
    (task,) = list(rig.pipeline._tasks)
    task.cancel()
    await asyncio.sleep(0.05)
    assert rig.lease.holder is StageName.PRINT
    blocking.release.set()
    await rig.pipeline.wait_idle()
    assert rig.lease.holder is None
    assert (await rig.pipeline.status(job.job_id)).status is JobStatus.CANCELLED
