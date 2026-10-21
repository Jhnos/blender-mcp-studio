"""DesignPipeline - import -> geometry -> mechanism -> print -> package for one ModelSpec.

REST and MCP both call this one service. Every run owns ``runs_dir/<run_id>/``; ``spec.json``
(the raw payload, a reproduction input) is written at submit and re-parsed at run time, and
``report.json`` is rewritten atomically after each stage. A job never stays QUEUED/RUNNING
after ``run()`` ends (finally), and ``recover_interrupted`` fails orphans after a restart.

Lease note (Phase 1b): mechanism and print take the Blender lease separately. Once print
loads STLs into Blender, Phase 1b must hold a single lease across both stages.
"""

from __future__ import annotations

import asyncio
import logging
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
from src.core.domain.slicing import ToolAvailability
from src.core.ports.job_store_port import JobStorePort
from src.core.ports.mechanism_simulation_port import MechanismSimulationPort
from src.core.ports.mesh_integrity_port import MeshIntegrityPort
from src.core.ports.packaging_port import PackagingPort
from src.core.ports.slicing_port import SlicingPort
from src.core.use_cases import design_reports as reports
from src.core.use_cases import design_stages as stages
from src.core.use_cases.blender_lease import BlenderLease

logger = logging.getLogger(__name__)

_RUN_ID = re.compile(r"[0-9a-f]{32}")
_LEASED = frozenset({StageName.MECHANISM, StageName.PRINT})
INTERRUPTED = "interrupted: service restarted"


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
        self._tasks: set[asyncio.Task[DesignRunReport]] = set()

    async def submit(self, payload: Mapping[str, object]) -> JobRecord:
        """Parse (ModelSpecError, no side effects), create job + run dir + spec.json, schedule."""
        parse_model_spec(payload, artifact_roots=self._roots)
        run_id = uuid.uuid4().hex
        job = await self._jobs.create(run_id)
        try:
            run_dir = self._runs_dir / run_id
            run_dir.mkdir(parents=True)
            reports.write_spec(run_dir, payload)
        except Exception as exc:
            await self._jobs.update(
                job.job_id, status=JobStatus.FAILED, error=f"{type(exc).__name__}: {exc}"
            )
            raise
        task = asyncio.create_task(self.run(job.job_id))
        self._tasks.add(task)
        task.add_done_callback(self._finished)
        return job

    def _finished(self, task: asyncio.Task[DesignRunReport]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("design run task failed", exc_info=task.exception())

    async def wait_idle(self) -> None:
        """Wait for every scheduled run to finish (tests, graceful shutdown)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def cancel_all(self) -> None:
        """Cancel every in-flight run and wait for each to record CANCELLED (shutdown).

        Not ``wait_idle``: a slice can run for minutes and shutdown must not hang.
        """
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def tools(self) -> tuple[ToolAvailability, ...]:
        """External tools the pipeline depends on (currently the slicer)."""
        return (await self._slicing.availability(),)

    def _load_spec(self, run_dir: Path) -> ModelSpec:
        raw = reports.read_spec(run_dir)
        if not isinstance(raw, Mapping):  # narrow-ok: spec.json is untrusted disk input
            raise ValueError("spec.json is not an object")
        return parse_model_spec(raw, artifact_roots=self._roots)

    async def run(self, job_id: str) -> DesignRunReport:
        job: JobRecord | None = None
        run_id, run_dir = "", self._runs_dir
        done: list[StageReport] = []
        status = JobStatus.FAILED
        error: str | None = "run interrupted"
        spec_name, current = "", None

        def snapshot() -> DesignRunReport:
            return DesignRunReport(run_id, spec_name, tuple(done), str(run_dir))

        try:
            job = await self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"unknown job: {job_id}")
            run_id = job.run_id
            run_dir = self._runs_dir / run_id
            spec = self._load_spec(run_dir)
            spec_name = spec.name
            state = stages.RunState()
            for name, step in self._plan(run_id, spec, state, run_dir):
                current = name
                await self._jobs.update(job_id, status=JobStatus.RUNNING, stage=name)
                done.append(await self._execute(name, step))
                reports.write_report(snapshot())
                if done[-1].outcome is StageOutcome.FAILED:
                    break
            report = snapshot()
            if report.passed:
                status, error = JobStatus.DONE, None
            else:
                error = f"{done[-1].name.value}: {done[-1].message}"
            return report
        except asyncio.CancelledError:
            status, error = JobStatus.CANCELLED, "cancelled"
            if current is not None and (not done or done[-1].name is not current):
                done.append(stages.failed(current, "cancelled"))
                reports.write_report(snapshot())
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            if job is not None:  # no job record (store failure / unknown id): nothing to update
                await self._jobs.update(job_id, status=status, stage=current, error=error)

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

    async def recover_interrupted(self) -> int:
        """Fail every QUEUED/RUNNING job left by a dead process; returns how many.

        Startup only, before any submit: it cannot tell an orphan from a live run.
        """
        if self._tasks:
            raise RuntimeError("recover_interrupted is startup-only: runs are in flight")
        orphans = await self._jobs.list_unfinished()
        for job in orphans:
            await self._jobs.update(
                job.job_id, status=JobStatus.FAILED, stage=job.stage, error=INTERRUPTED
            )
            if job.stage is None:
                continue
            run_dir = self._runs_dir / job.run_id
            try:
                existing = reports.read_report(run_dir)
            except (ValueError, KeyError, OSError):
                # unreadable report == missing: start a fresh one holding only the failure
                existing = DesignRunReport(job.run_id, "", (), str(run_dir))
            else:
                if existing is None:
                    continue
            if existing.stages and existing.stages[-1].name is job.stage:
                continue
            failed = stages.failed(job.stage, INTERRUPTED)
            reports.write_report(
                DesignRunReport(
                    existing.run_id,
                    existing.spec_name,
                    (*existing.stages, failed),
                    existing.run_dir,
                )
            )
        return len(orphans)

    async def status(self, job_id: str) -> JobRecord | None:
        return await self._jobs.get(job_id)

    async def report(self, run_id: str) -> DesignRunReport | None:
        if not _RUN_ID.fullmatch(run_id):
            return None
        return reports.read_report(self._runs_dir / run_id)

    def run_file(self, run_id: str, name: str) -> Path:
        """Resolve a file inside one run directory; anything escaping it raises ValueError."""
        if not _RUN_ID.fullmatch(run_id):
            raise ValueError("run_id must be 32 lowercase hex characters")
        run_dir = (self._runs_dir / run_id).resolve()
        target = (run_dir / name).resolve()
        if not target.is_relative_to(run_dir):
            raise ValueError(f"{name}: outside the run directory")
        return target
