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
from src.adapters.mcp_server.schemas import Name
from src.adapters.slicing.bambu_studio_cli import SLICE_TIMEOUT_S
from src.core.domain.exceptions import DomainError
from src.core.domain.mechanical_generation import InstanceBuild, InstanceSummary
from src.core.domain.mesh_integrity import MeshIntegrityReport
from src.core.domain.slicing import SliceResult
from src.core.ports.mechanical_generation_port import InstanceCatalogPort
from src.core.use_cases.design_pipeline import DesignPipeline

#: Submitting only parses the spec, writes spec.json and schedules the run.
SUBMIT_TIMEOUT_S = 30.0
QUERY_TIMEOUT_S = 10.0
#: Measured 2026-10-21 with TrimeshCgalIntegrity on the 113 v78 STLs: 1.9 s (rounded up to 2).
#: ``max_stl_files`` (565, config/tools.yaml) is 5 x 113, so the largest admissible request takes
#: 5 x 2 s; the timeout is 5 x that, because one sample on a shared host is a coin flip.
INTEGRITY_MEASURED_S = 2
INTEGRITY_CAP_FACTOR = 5
INTEGRITY_TOOL_TIMEOUT_S = 5.0 * INTEGRITY_CAP_FACTOR * INTEGRITY_MEASURED_S
#: Slicing and generation outlive their adapter deadline by the transport overhead.
SLICE_TOOL_TIMEOUT_S = SLICE_TIMEOUT_S + 30.0
BUILD_TOOL_TIMEOUT_S = GENERATOR_TIMEOUT_S + 30.0

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
        "log_path": uri(result.log_path),
        "return_code": result.return_code,
        "message": result.message,
    }


def read_run_resource(design: DesignPipeline, run_id: str, name: str) -> str | bytes:
    """Serve one evidence file; ``ValueError`` for traversal, a bad run id or a missing file."""
    path = design.run_file(run_id, name)
    if not path.is_file():
        raise ValueError(f"no such file in run: {name}")
    data = path.read_bytes()
    return data.decode("utf-8") if path.suffix.lower() in _TEXT_SUFFIXES else data


def register_design_tools(
    mcp: FastMCP,
    *,
    design: DesignPipeline | None,
    generation: InstanceCatalogPort | None,
) -> None:
    """Add the eight design tools and the run resource; unconfigured ones say so when called."""
    # Late import: server.py imports this module, so a top-level import would be circular.
    from src.adapters.mcp_server.server import _tool_error

    @mcp.tool(
        timeout=SUBMIT_TIMEOUT_S,
        annotations=_annotations("Run design pipeline", read_only=False, idempotent=False),
    )
    async def run_design_pipeline(spec: dict[str, object]) -> dict[str, object]:
        """Submit a ModelSpec (spec_version 1) and return its queued job; poll get_job_status.

        The run imports the STLs under source.root_dir, checks geometry, runs the declared
        mechanism suites, slices the project 3MF and packages the evidence. The call returns at
        once; read the verdict with get_run_report. A malformed or out-of-root spec is an error
        and creates no job. Files that were ignored are listed in the import stage evidence.
        """
        pipeline = _configured(design, "design pipeline")
        try:
            return job_dict(await pipeline.submit(spec))
        except DomainError as exc:
            raise _tool_error(exc) from exc

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
        timeout=INTEGRITY_TOOL_TIMEOUT_S,
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
            raise _tool_error(exc) from exc

    @mcp.tool(
        timeout=SLICE_TOOL_TIMEOUT_S,
        annotations=_annotations("Slice for print", read_only=False, idempotent=False),
    )
    async def slice_for_print(input_3mf: str, printer: Name = "bambu-p2s") -> dict[str, object]:
        """Slice one 3MF with the Bambu Studio CLI into a fresh run directory.

        input_3mf is relative to an allowed artifact root and ends in .3mf. Output files come
        back as run://{run_id}/print/<name> resource URIs, readable with the run resource. A
        missing slicer or a non-zero exit is a result with passed=false and the log tail.
        """
        pipeline = _configured(design, "design pipeline")
        try:
            return slice_result_dict(await pipeline.slice_file(input_3mf, printer))
        except DomainError as exc:
            raise _tool_error(exc) from exc

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
        try:
            return await catalog.build(slug)
        except DomainError as exc:
            raise _tool_error(exc) from exc

    @mcp.tool(
        timeout=QUERY_TIMEOUT_S,
        annotations=_annotations("Tool status", read_only=True, idempotent=True),
    )
    async def tool_status() -> list[dict[str, object]]:
        """Report which external tools the pipeline needs (the slicer), with an install hint."""
        pipeline = _configured(design, "design pipeline")
        rows = []
        for tool in await pipeline.tools():
            row = tool_dict(tool)
            row.pop("path")  # a host path; availability and version are the contract
            rows.append(row)
        return rows

    @mcp.resource("run://{run_id}/{name*}", name="run_file")
    async def run_file(run_id: str, name: str) -> str | bytes:
        """One evidence file of a design run (report.json, print/<slicer outputs>, manifest)."""
        pipeline = _configured(design, "design pipeline")
        try:
            return read_run_resource(pipeline, run_id, name)
        except ValueError as exc:
            raise ResourceError(str(exc)) from exc
