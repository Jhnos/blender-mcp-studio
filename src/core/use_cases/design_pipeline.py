"""DesignPipeline - import -> geometry -> mechanism -> print -> package for one ModelSpec.

REST and MCP both call this one service. Every run owns ``runs_dir/<run_id>/`` and
``report.json`` is rewritten atomically after each stage. Mechanism and print stages hold
the shared ``BlenderLease`` so concurrent runs queue instead of interleaving.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path

from src.core.domain.design_run import (
    DesignRunReport,
    JobRecord,
    JobStatus,
    StageName,
    StageOutcome,
    StageReport,
)
from src.core.domain.model_spec import ModelSpec, parse_model_spec
from src.core.ports.job_store_port import JobStorePort
from src.core.ports.mechanism_simulation_port import MechanismSimulationPort
from src.core.ports.mesh_integrity_port import MeshIntegrityPort
from src.core.ports.packaging_port import PackagingPort
from src.core.ports.slicing_port import SlicingPort
from src.core.use_cases import design_stages as stages
from src.core.use_cases.blender_lease import BlenderLease

_RUN_ID = re.compile(r"[0-9a-f]{32}")
_LEASED = frozenset({StageName.MECHANISM, StageName.PRINT})


def _to_json(report: DesignRunReport) -> str:
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


def _from_json(text: str) -> DesignRunReport:
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


class DesignPipeline:
    def __init__(
        self,
        *,
        integrity: MeshIntegrityPort,
        simulation: MechanismSimulationPort,
        slicing: SlicingPort,
        packaging: PackagingPort,
        jobs: JobStorePort,
        lease: BlenderLease,
        runs_dir: Path,
        artifact_roots: tuple[Path, ...],
    ) -> None:
        self._integrity = integrity
        self._simulation = simulation
        self._slicing = slicing
        self._packaging = packaging
        self._jobs = jobs
        self._lease = lease
        self._runs_dir = Path(runs_dir)
        self._roots = artifact_roots
        self._specs: dict[str, ModelSpec] = {}
        self._tasks: set[asyncio.Task[DesignRunReport]] = set()

    async def submit(self, payload: Mapping[str, object]) -> JobRecord:
        """Parse the spec (ModelSpecError before any side effect), then schedule the run."""
        spec = parse_model_spec(payload, artifact_roots=self._roots)
        run_id = uuid.uuid4().hex
        (self._runs_dir / run_id).mkdir(parents=True)
        job = await self._jobs.create(run_id)
        self._specs[job.job_id] = spec
        task = asyncio.create_task(self.run(job.job_id))
        self._tasks.add(task)
        task.add_done_callback(self._finished)
        return job

    def _finished(self, task: asyncio.Task[DesignRunReport]) -> None:
        self._tasks.discard(task)
        if not task.cancelled():
            task.exception()  # retrieved: run() already recorded the failure on the job

    async def wait_idle(self) -> None:
        """Wait for every scheduled run to finish (tests, graceful shutdown)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def run(self, job_id: str) -> DesignRunReport:
        job = await self._jobs.get(job_id)
        spec = self._specs.pop(job_id, None)
        if job is None or spec is None:
            raise KeyError(f"no queued job: {job_id}")
        run_dir = self._runs_dir / job.run_id
        done: list[StageReport] = []
        status = JobStatus.FAILED
        error: str | None = "run interrupted"
        try:
            state = stages.RunState()
            for name, step in self._plan(job.run_id, spec, state, run_dir):
                await self._jobs.update(job_id, status=JobStatus.RUNNING, stage=name)
                done.append(await self._execute(name, step))
                self._write(DesignRunReport(job.run_id, spec.name, tuple(done), str(run_dir)))
                if done[-1].outcome is StageOutcome.FAILED:
                    break
            report = DesignRunReport(job.run_id, spec.name, tuple(done), str(run_dir))
            if report.passed:
                status, error = JobStatus.DONE, None
            else:
                error = f"{done[-1].name.value}: {done[-1].message}"
            return report
        finally:
            await self._jobs.update(job_id, status=status, error=error)

    def _plan(
        self, run_id: str, spec: ModelSpec, state: stages.RunState, run_dir: Path
    ) -> list[tuple[StageName, Callable[[], Awaitable[StageReport]]]]:
        return [
            (StageName.IMPORT, lambda: stages.import_stage(spec, state)),
            (StageName.GEOMETRY, lambda: stages.geometry_stage(self._integrity, state)),
            (StageName.MECHANISM, lambda: stages.mechanism_stage(spec, self._simulation)),
            (StageName.PRINT, lambda: stages.print_stage(spec, self._slicing, state, run_dir)),
            (
                StageName.PACKAGE,
                lambda: stages.package_stage(run_id, spec, self._packaging, state, run_dir),
            ),
        ]

    async def _execute(
        self, name: StageName, step: Callable[[], Awaitable[StageReport]]
    ) -> StageReport:
        try:
            if name in _LEASED:
                async with self._lease.hold(name):
                    return await step()
            return await step()
        except Exception as exc:  # noqa: BLE001 - any stage error is a FAILED stage, not a crash
            return stages.failed(name, f"{type(exc).__name__}: {exc}")

    def _write(self, report: DesignRunReport) -> None:
        run_dir = Path(report.run_dir)
        tmp = run_dir / (stages.REPORT_NAME + ".tmp")
        tmp.write_text(_to_json(report), encoding="utf-8")
        os.replace(tmp, run_dir / stages.REPORT_NAME)

    async def status(self, job_id: str) -> JobRecord | None:
        return await self._jobs.get(job_id)

    async def report(self, run_id: str) -> DesignRunReport | None:
        if not _RUN_ID.fullmatch(run_id):
            return None
        path = self._runs_dir / run_id / stages.REPORT_NAME
        if not path.is_file():
            return None
        return _from_json(path.read_text(encoding="utf-8"))

    def run_file(self, run_id: str, name: str) -> Path:
        """Resolve a file inside one run directory; anything escaping it raises ValueError."""
        if not _RUN_ID.fullmatch(run_id):
            raise ValueError("run_id must be 32 lowercase hex characters")
        run_dir = (self._runs_dir / run_id).resolve()
        target = (run_dir / name).resolve()
        if not target.is_relative_to(run_dir):
            raise ValueError(f"{name}: outside the run directory")
        return target
