"""DesignPipeline - import -> geometry -> mechanism -> print -> package for one ModelSpec.

REST and MCP share jobs, evidence and stage execution. Native jobs capture selection before
queueing and retain RUNNING when remote completion is unknown; startup preserves their
quarantine until durable terminal/restoration receipts are verified.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from pathlib import Path

from src.core.domain.design_run import (
    DesignRunReport,
    JobRecord,
    JobStatus,
    StageName,
    StageOutcome,
    StageReport,
)
from src.core.domain.exceptions import BlenderExecutionUncertainError
from src.core.domain.import_limits import ImportLimits
from src.core.domain.mesh_integrity import MeshIntegrityReport
from src.core.domain.model_spec import JOB_DEFAULTS, PrintTarget, parse_model_spec
from src.core.domain.native_revision import (
    CapturedNativeRevision,
    NativeRevisionError,
    parse_native_revision,
)
from src.core.domain.slicing import SliceResult, ToolAvailability
from src.core.ports.job_store_port import JobStorePort
from src.core.ports.mechanism_simulation_port import MechanismSimulationPort
from src.core.ports.mesh_integrity_port import MeshIntegrityPort
from src.core.ports.native_product_port import NativeProductPort
from src.core.ports.packaging_port import PackagingPort
from src.core.ports.slicing_port import SlicingPort
from src.core.use_cases import design_files as files
from src.core.use_cases import design_reports as reports
from src.core.use_cases import design_stages as stages
from src.core.use_cases import print_targets
from src.core.use_cases.artifact_catalog import ArtifactCatalog
from src.core.use_cases.blender_lease import BlenderLease
from src.core.use_cases.native_revision import NativeRevisionService
from src.core.use_cases.printer_listing import PrinterListing, list_printers, readable
from src.core.use_cases.slice_file import slice_one

logger = logging.getLogger(__name__)

_LEASED = frozenset({StageName.MECHANISM, StageName.PRINT})
INTERRUPTED = "interrupted: service restarted"
NATIVE_UNCONFIRMED = "native execution completion unconfirmed; verified recovery is required"


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
        limits: ImportLimits,
        artifacts: ArtifactCatalog,
        native: NativeRevisionService | None = None,
        native_products: NativeProductPort | None = None,
    ) -> None:
        self._artifacts = artifacts
        self._jobs = jobs
        self._lease = lease
        self._runs_dir = Path(runs_dir)
        self._roots = artifact_roots
        self._scrub = files.PathScrubber(artifact_roots, Path(runs_dir))
        self._stages = stages.DesignStages(
            limits,
            integrity,
            simulation,
            slicing,
            packaging,
            self._scrub.text,
            native,
            native_products,
        )
        self._tasks: set[asyncio.Task[DesignRunReport]] = set()

    @property
    def limits(self) -> ImportLimits:
        return self._stages.limits

    @property
    def lease(self) -> BlenderLease:
        """The one Blender lease; delivery adapters guard scene tools with this instance."""
        return self._lease

    @property
    def slice_timeout_s(self) -> float:
        """The slowest catalog slicer's deadline, installed or not (adapters add their margin).

        Not only usable printers: with no slicer installed at startup the MCP tool timeout
        would otherwise collapse to the bare transport margin.
        """
        return self._stages.slicing.max_timeout_s()

    async def submit(
        self,
        payload: Mapping[str, object] | None = None,
        *,
        revision: Mapping[str, object] | None = None,
    ) -> JobRecord:
        """Parse (ModelSpecError, no side effects), create job + run dir + spec.json, schedule.

        A printer not usable here, or a material it lacks, is rejected before any job exists.
        """
        if revision is not None and payload is not None:
            raise NativeRevisionError("native revision uses the current selected model; omit spec")
        request = parse_native_revision(revision) if revision is not None else None
        if request is not None and (self._stages.native is None or self._stages.products is None):
            raise NativeRevisionError("native print pipeline is not configured")
        selected = await asyncio.to_thread(self._artifacts.current) if payload is None else payload
        target = parse_model_spec(selected, artifact_roots=self._roots).print_target
        await print_targets.check_print_target(target, self._stages.slicing)
        captured = (
            await self._stages.native.capture_revision(selected, request)
            if request is not None and self._stages.native is not None
            else None
        )
        run_id = uuid.uuid4().hex
        job = await self._jobs.create(run_id)
        try:
            run_dir = self._runs_dir / run_id
            run_dir.mkdir(parents=True)
            reports.write_spec(run_dir, selected)
            if captured is not None:
                reports.write_native_request(run_dir, captured.request)
        except Exception as exc:
            error = await self.clean(f"{type(exc).__name__}: {exc}")
            await self._jobs.update(job.job_id, status=JobStatus.FAILED, error=error)
            raise
        task = asyncio.create_task(self.run(job.job_id, native=captured))
        self._tasks.add(task)
        task.add_done_callback(self._finished)
        return job

    async def describe_spec(self) -> dict[str, object]:
        """Spec v2 as JSON Schema with this host's usable printers and their materials.

        Reading the bundle profiles and the selection blocks, so it runs in a worker thread.
        """
        return await asyncio.to_thread(self._describe)

    def _describe(self) -> dict[str, object]:
        slicing = self._stages.slicing
        usable = readable(slicing, slicing.machine_facts())
        ranges = {p.id: known.layer_range for p, known in usable}
        return self._artifacts.describe(tuple(p for p, _ in usable), ranges)

    async def list_artifacts(self) -> dict[str, object]:
        """Candidate ``source.root_dir`` values under the artifact roots (relative only)."""
        return await self._artifacts.discover()

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
        """External tools the pipeline depends on (one entry per catalog slicer)."""
        return await self._stages.slicing.availability()

    async def check_meshes(self, paths: tuple[str, ...]) -> MeshIntegrityReport:
        """Integrity-check STLs named relative to an artifact root (no run, no Blender lease).

        Paths pass the ModelSpec parser's gate and the import caps; verdicts come back relative.
        """
        found = await asyncio.to_thread(
            files.resolve_inputs,
            tuple(paths),
            suffix=".stl",
            roots=self._roots,
            max_count=self._stages.limits.max_stl_files,
            max_bytes=self._stages.limits.max_stl_bytes,
            max_total_bytes=self._stages.limits.max_total_stl_bytes,
        )
        report = await self._stages.integrity.check(tuple(str(f.absolute) for f in found))
        return files.relative_report(report, found, self._scrub)

    async def list_printers(self) -> PrinterListing:
        """The printers this host can slice for (with machine facts) and those it cannot."""
        return await list_printers(self._stages.slicing, self.clean)

    async def slice_file(
        self,
        input_3mf: str,
        printer: str,
        material: str,
        *,
        layer_height_mm: float | None = None,
        queue: bool = True,
    ) -> SliceResult:
        """Slice one 3MF under the artifact roots into a fresh run directory.

        Printer and material are required; the layer height defaults to the job default.
        Output paths come back relative to the runs dir: ``<run_id>/print/<name>``.
        """
        height = JOB_DEFAULTS.layer_height_mm if layer_height_mm is None else layer_height_mm
        target = PrintTarget(printer=printer, material=material, layer_height_mm=height)
        result = await slice_one(
            self._stages.slicing,
            self._lease,
            self._runs_dir,
            self._roots,
            self._stages.limits,
            input_3mf,
            target,
            queue=queue,
        )
        result = replace(result, message=await self.clean(result.message))
        return files.relative_slice(result, self._runs_dir, self._scrub)

    async def _slicer_dirs(self) -> tuple[str, ...]:
        """Every slicer binary's directory: the one extra-prefix list all scrubbing shares."""
        try:
            tools = await self._stages.slicing.availability()
        except Exception:  # noqa: BLE001 - scrubbing must never fail a run
            tools = ()
        return tuple(str(Path(tool.path).parent) for tool in tools if tool.path)

    async def clean(self, text: str) -> str:
        """Strip host paths from free text, including every slicer binary's directory."""
        return self._scrub.text(text, await self._slicer_dirs())

    async def run(
        self, job_id: str, *, native: CapturedNativeRevision | None = None
    ) -> DesignRunReport:
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
            spec = native.spec if native is not None else reports.load_spec(run_dir, self._roots)
            spec_name = spec.name
            state = stages.RunState()
            for name, step in self._stages.plan(run_id, spec, state, run_dir, native):
                current = name
                await self._jobs.update(job_id, status=JobStatus.RUNNING, stage=name)
                done.append(await self._execute(name, step, run_dir))
                reports.write_report(snapshot())
                if done[-1].outcome is StageOutcome.FAILED:
                    break
            report = snapshot()
            if report.passed:
                status, error = JobStatus.DONE, None
            else:
                error = f"{done[-1].name.value}: {done[-1].message}"
            return report
        except BlenderExecutionUncertainError:
            if native is None:
                raise
            status, error = JobStatus.RUNNING, NATIVE_UNCONFIRMED
            reports.write_report(snapshot())
            return snapshot()
        except asyncio.CancelledError:
            if (
                native is not None
                and self._stages.native is not None
                and run_id in self._stages.native.unresolved_run_ids
            ):
                status, error = JobStatus.RUNNING, NATIVE_UNCONFIRMED
                reports.write_report(snapshot())
                raise
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
                if error:
                    error = await self.clean(error)
                await self._jobs.update(job_id, status=status, stage=current, error=error)

    async def _execute(
        self, name: StageName, step: Callable[[], Awaitable[StageReport]], run_dir: Path
    ) -> StageReport:
        try:
            if name in _LEASED:
                async with self._lease.hold(name):
                    report = await step()
            else:
                report = await step()
        except BlenderExecutionUncertainError:
            raise  # A possibly active native callback is not a definitive failed stage.
        except Exception as exc:  # noqa: BLE001 - any stage error is a FAILED stage, not a crash
            report = stages.failed(name, f"{type(exc).__name__}: {exc}")
        finally:
            if name is StageName.PRINT:  # the one place slicer logs are scrubbed, pass or fail
                files.scrub_logs(run_dir / "print", self._scrub, await self._slicer_dirs())
        if report.message:  # choke point: no stage message leaves with a host path
            report = replace(report, message=await self.clean(report.message))
        return report

    async def recover_interrupted(self, *, unresolved_run_ids: tuple[str, ...] = ()) -> int:
        """Startup-only orphan recovery; unresolved native executions remain quarantined."""
        if self._tasks:
            raise RuntimeError("recover_interrupted is startup-only: runs are in flight")
        return await reports.recover_interrupted(
            self._jobs, self._runs_dir, unresolved_run_ids, INTERRUPTED
        )

    async def status(self, job_id: str) -> JobRecord | None:
        job = await self._jobs.get(job_id)
        if (
            job is not None
            and job.error == NATIVE_UNCONFIRMED
            and not self._tasks
            and self._stages.native is not None
            and await self._stages.native.reconcile_execution(job.run_id)
        ):
            message = "native terminal verified; pipeline interrupted before qualification finished"
            job = await self._jobs.update(
                job_id, status=JobStatus.FAILED, stage=job.stage, error=message
            )
            reports.record_interruption(self._runs_dir / job.run_id, job, message)
        return job

    async def report(self, run_id: str) -> DesignRunReport | None:
        if not files.RUN_ID.fullmatch(run_id):
            return None
        return reports.read_report(self._runs_dir / run_id)

    def run_file(self, run_id: str, name: str) -> Path:
        """Resolve a file inside one run directory; anything escaping it raises ValueError."""
        return files.resolve_run_file(self._runs_dir, run_id, name)
