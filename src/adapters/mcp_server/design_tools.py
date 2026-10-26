"""MCP tools and the ``run://`` resource for the design pipeline, integrity, slicing, instances.

Registered by ``create_mcp_server``; every tool is a thin translation over ``DesignPipeline`` or
``InstanceCatalogPort``. Caller-supplied paths are never interpreted here: the use case applies
the ModelSpec parser's path gate and the import caps. No result carries a host path: meshes are
relative to their artifact root, slice outputs are ``run://{run_id}/print/<name>`` URIs that the
``run://{run_id}/{name}`` resource serves, instance output dirs are repository-relative.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TypeVar

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations

from src.adapters.design_payloads import job_dict, report_dict, tool_dict
from src.adapters.generation.authorized_code import GENERATOR_TIMEOUT_S
from src.adapters.mcp_server.errors import exclusive, tool_error
from src.adapters.mcp_server.schemas import Name
from src.core.domain.exceptions import DomainError
from src.core.domain.import_limits import ImportLimits
from src.core.domain.mechanical_generation import InstanceBuild, InstanceSummary
from src.core.domain.mesh_integrity import MeshIntegrityReport
from src.core.domain.slicing import SliceResult
from src.core.ports.mechanical_generation_port import InstanceCatalogPort
from src.core.use_cases.blender_lease import BlenderLease
from src.core.use_cases.design_pipeline import DesignPipeline

#: Submitting only parses the spec, writes spec.json and schedules the run.
SUBMIT_TIMEOUT_S = 30.0
QUERY_TIMEOUT_S = 10.0
#: Measured 2026-10-21 with the real TrimeshCgalIntegrity on the 113 STLs of the v78 deliverable:
#: 5,858,592 bytes in total (largest 491,584), integrity check took 1.9 s. Rerun:
#: ``stat`` the STLs for the bytes, time ``TrimeshCgalIntegrity().check`` for the seconds.
V78_STL_TOTAL_BYTES = 5_858_592
V78_CHECK_S = 1.9
#: One sample on a shared host is a coin flip, so the timeout is 5 x the scaled measurement.
SAFETY_FACTOR = 5


def integrity_timeout_s(limits: ImportLimits) -> float:
    """Tool timeout for the largest request the caps admit, scaled from the v78 measurement.

    Check time is taken as proportional to bytes: the ``max_total_stl_bytes`` cap (the most one
    request or run may load, 5 x the v78 total) over the v78 total, times 1.9 s, times the
    safety factor. The check runs in ``to_thread`` and cannot be
    interrupted, so this timeout bounds the caller's wait, not the CPU the check keeps using.
    """
    return SAFETY_FACTOR * V78_CHECK_S * limits.max_total_stl_bytes / V78_STL_TOTAL_BYTES


#: Slicing and generation outlive their adapter deadline by the transport overhead. The slice
#: deadline comes from the slicing port (``DesignPipeline.slice_timeout_s``), not a concrete slicer.
TRANSPORT_MARGIN_S = 30.0
BUILD_TOOL_TIMEOUT_S = GENERATOR_TIMEOUT_S + TRANSPORT_MARGIN_S

RUN_URI_PREFIX = "run://"
_TEXT_SUFFIXES = frozenset({".json", ".log"})
_T = TypeVar("_T")


def _annotations(
    title: str, *, read_only: bool, destructive: bool = False, idempotent: bool
) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=read_only,
        destructiveHint=destructive,
        idempotentHint=idempotent,
        openWorldHint=False,
    )


def _configured(service: _T | None, what: str) -> _T:
    if service is None:
        raise ToolError(f"{what} is not configured on this server")
    return service


def mesh_report_dict(report: MeshIntegrityReport) -> dict[str, object]:
    """``passed`` is a property on the records, so it is added by hand (FastMCP drops it)."""
    return {
        "passed": report.passed,
        "verdicts": [{**asdict(v), "passed": v.passed} for v in report.verdicts],
    }


def slice_result_dict(result: SliceResult) -> dict[str, object]:
    """Output paths (``<run_id>/print/<name>``) become ``run://`` resource URIs."""

    def uri(path: str | None) -> str | None:
        return None if path is None else RUN_URI_PREFIX + path

    return {
        "passed": result.passed,
        "output_3mf": uri(result.output_3mf),
        "settings_json": uri(result.settings_json),
        "log_path": uri(result.log_path or None),
        "return_code": result.return_code,
        "message": result.message,
    }


def read_run_resource(design: DesignPipeline, run_id: str, name: str) -> str | bytes:
    """Serve one evidence file; ``ValueError`` for traversal, a bad run id or a missing file."""
    path = design.run_file(run_id, name)
    if not path.is_file():
        raise ValueError(f"no such file in run: {name}")
    data = path.read_bytes()
    return data.decode("utf-8", errors="replace") if path.suffix.lower() in _TEXT_SUFFIXES else data


def register_design_tools(
    mcp: FastMCP,
    *,
    design: DesignPipeline | None,
    generation: InstanceCatalogPort | None,
    lease: BlenderLease,
) -> None:
    """Add the design tools and the run resource; unconfigured ones say so when called."""
    integrity_timeout = (
        SAFETY_FACTOR * V78_CHECK_S if design is None else integrity_timeout_s(design.limits)
    )
    slice_timeout = (
        QUERY_TIMEOUT_S if design is None else design.slice_timeout_s + TRANSPORT_MARGIN_S
    )

    async def fail(exc: Exception) -> ToolError:
        """The design tools' error path: ``tool_error`` text with host paths scrubbed."""
        error = tool_error(exc)
        return error if design is None else ToolError(await design.clean(str(error)))

    @mcp.tool(
        timeout=SUBMIT_TIMEOUT_S,
        annotations=_annotations("Run design pipeline", read_only=False, idempotent=False),
    )
    async def run_design_pipeline(spec: dict[str, object] | None = None) -> dict[str, object]:
        """Submit the current selected model when spec is omitted, or an explicit ModelSpec.

        Return its queued job; poll get_job_status.

        Minimal spec: {"spec_version": "1", "name": ..., "source": {"root_dir": ...,
        "project_3mf": ...}}. Call describe_model_spec for the full schema, defaults and a worked
        example, and list_artifacts for valid root_dir values. The run imports the STLs under
        source.root_dir, checks geometry, slices the project 3MF and packages the evidence
        (mechanism is not evaluated in Phase 1). The call returns at once; read the verdict with
        get_run_report. A malformed, out-of-root or unsupported-printer spec is an error and
        creates no job. Ignored files are listed in the run's import.json.
        """
        pipeline = _configured(design, "design pipeline")
        try:
            return job_dict(await pipeline.submit(spec))
        except DomainError as exc:
            raise await fail(exc) from exc

    @mcp.tool(
        timeout=QUERY_TIMEOUT_S,
        annotations=_annotations("Describe model spec", read_only=True, idempotent=True),
    )
    async def describe_model_spec() -> dict[str, object]:
        """Return the ModelSpec v1 JSON Schema (fields, types, defaults, supported printers and
        materials) and a complete worked example for run_design_pipeline."""
        try:
            return await _configured(design, "design pipeline").describe_spec()
        except DomainError as exc:
            raise await fail(exc) from exc

    @mcp.tool(
        timeout=QUERY_TIMEOUT_S,
        annotations=_annotations("List artifacts", read_only=True, idempotent=True),
    )
    async def list_artifacts() -> dict[str, object]:
        """List deliverable directories usable as source.root_dir: each root-relative root_dir
        with its STL count per subdirectory and its 3MF names (at most 200, no hidden dirs).
        Use default_spec for the shared selected delivery. If default_available is false,
        report the missing delivery; never fall back to an archived version."""
        try:
            return await _configured(design, "design pipeline").list_artifacts()
        except DomainError as exc:
            raise await fail(exc) from exc

    @mcp.tool(
        timeout=QUERY_TIMEOUT_S,
        annotations=_annotations("Get job status", read_only=True, idempotent=True),
    )
    async def get_job_status(job_id: Name) -> dict[str, object]:
        """Return a design job's status (queued, running, done, failed, cancelled) and stage."""
        pipeline = _configured(design, "design pipeline")
        job = await pipeline.status(job_id)
        if job is None:
            raise ToolError(f"unknown job: {job_id}")
        return job_dict(job)

    @mcp.tool(
        timeout=QUERY_TIMEOUT_S,
        annotations=_annotations("Get run report", read_only=True, idempotent=True),
    )
    async def get_run_report(run_id: Name) -> dict[str, object]:
        """Return a run's per-stage verdicts, metrics and evidence plus the overall passed flag.

        Evidence files are readable through the run://{run_id}/{name} resource.
        """
        pipeline = _configured(design, "design pipeline")
        report = await pipeline.report(run_id)
        if report is None:
            raise ToolError(f"no report for run: {run_id}")
        return report_dict(report)

    @mcp.tool(
        timeout=integrity_timeout,
        annotations=_annotations("Check mesh integrity", read_only=True, idempotent=True),
    )
    async def check_mesh_integrity(stl_paths: list[str]) -> dict[str, object]:
        """Check binary STLs are closed, non-self-intersecting surfaces; no Blender needed.

        Each path is relative to an allowed artifact root, ends in .stl, has no hidden part and
        may not leave the root. File count and size are capped. Verdict paths are relative to
        the root; a failing mesh is a verdict with its reason, not a tool error.
        """
        pipeline = _configured(design, "design pipeline")
        try:
            return mesh_report_dict(await pipeline.check_meshes(tuple(stl_paths)))
        except DomainError as exc:
            raise await fail(exc) from exc

    @mcp.tool(
        timeout=slice_timeout,
        annotations=_annotations("Slice for print", read_only=False, idempotent=False),
    )
    async def slice_for_print(input_3mf: str, printer: Name = "bambu-p2s") -> dict[str, object]:
        """Slice one 3MF with the Bambu Studio CLI into a fresh run directory.

        input_3mf is relative to an allowed artifact root and ends in .3mf. Output files come
        back as run://{run_id}/print/<name> resource URIs, readable with the run resource. A
        missing slicer, a non-zero exit, or another print job holding the slicer ("slicer busy",
        retry later; this tool never queues) is a result with passed=false and a message.
        """
        pipeline = _configured(design, "design pipeline")
        try:
            return slice_result_dict(await pipeline.slice_file(input_3mf, printer, queue=False))
        except DomainError as exc:
            raise await fail(exc) from exc

    @mcp.tool(
        timeout=QUERY_TIMEOUT_S,
        annotations=_annotations("List instances", read_only=True, idempotent=True),
    )
    async def list_instances() -> tuple[InstanceSummary, ...]:
        """List registered parametric instances with the part files each build must produce."""
        catalog = _configured(generation, "instance catalog")
        return await catalog.list_instances()

    @mcp.tool(
        timeout=BUILD_TOOL_TIMEOUT_S,
        annotations=_annotations(
            "Build instance", read_only=False, destructive=True, idempotent=False
        ),
    )
    async def build_instance(slug: Name) -> InstanceBuild:
        """Build one registered instance in Blender and overwrite its declared STL files.

        Accepts only slugs from list_instances; no code is accepted. The build is checked
        against the instance's declared parts and reports face counts and dimensions.
        """
        catalog = _configured(generation, "instance catalog")
        async with exclusive(lease, "build_instance"):
            try:
                return await catalog.build(slug)
            except DomainError as exc:
                raise await fail(exc) from exc

    @mcp.tool(
        timeout=QUERY_TIMEOUT_S,
        annotations=_annotations("Tool status", read_only=True, idempotent=True),
    )
    async def tool_status() -> list[dict[str, object]]:
        """Report which external tools the pipeline needs (the slicer), with an install hint."""
        pipeline = _configured(design, "design pipeline")
        return [tool_dict(tool) for tool in await pipeline.tools()]

    @mcp.resource("run://{run_id}/{name*}", name="run_file")
    async def run_file(run_id: str, name: str) -> str | bytes:
        """One evidence file of a design run (report.json, print/<slicer outputs>, manifest)."""
        pipeline = _configured(design, "design pipeline")
        try:
            return read_run_resource(pipeline, run_id, name)
        except ValueError as exc:
            raise ResourceError(str(exc)) from exc
