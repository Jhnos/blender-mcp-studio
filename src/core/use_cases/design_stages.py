"""The five design pipeline stages as plain functions over ports.

Each stage returns a ``StageReport``; an exception is turned into a FAILED report by the
caller. Stages never touch jobs or report.json.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from src.core.domain.design_run import StageName, StageOutcome, StageReport
from src.core.domain.import_limits import ImportLimits
from src.core.domain.model_spec import ModelSpec
from src.core.domain.packaging import ToolUse
from src.core.domain.slicing import SliceRequest
from src.core.ports.mechanism_simulation_port import MechanismSimulationPort
from src.core.ports.mesh_integrity_port import MeshIntegrityPort
from src.core.ports.packaging_port import PackagingPort
from src.core.ports.slicing_port import SlicingPort
from src.core.use_cases.design_reports import REPORT_NAME

SLICER_LICENSE = "AGPL-3.0-only"


@dataclass(slots=True)
class RunState:
    """What later stages need from earlier ones."""

    root: str = ""
    stls: tuple[str, ...] = ()
    project_3mf: str | None = None
    tools: tuple[ToolUse, ...] = field(default_factory=tuple)


def _report(
    name: StageName,
    outcome: StageOutcome,
    message: str = "",
    metrics: tuple[tuple[str, str], ...] = (),
    evidence: tuple[str, ...] = (),
) -> StageReport:
    return StageReport(name, outcome, metrics, evidence, message)


def failed(name: StageName, message: str) -> StageReport:
    return _report(name, StageOutcome.FAILED, message)


def _rel(path: str, base: Path) -> str:
    try:
        return Path(path).resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path


def _hidden(rel: Path) -> bool:
    return any(part.startswith(".") for part in rel.parts)


def _too_big(path: Path, rel: str, limit: int) -> str | None:
    size = path.stat().st_size
    return f"{rel}: {size} bytes exceeds the {limit} byte limit" if size > limit else None


def _scan_source(
    spec: ModelSpec, limits: ImportLimits
) -> tuple[tuple[Path, ...], Path | None, str | None]:
    """Blocking: expand the glob, check containment and caps. Returns (stls, project, error).

    Defence in depth behind the parser: only ``.stl`` files outside hidden path parts count.
    """
    root = Path(spec.source.root_dir).resolve()
    stls: list[Path] = []
    for match in sorted(root.glob(spec.source.stl_glob)):
        rel = match.relative_to(root)
        if _hidden(rel) or match.suffix.lower() != ".stl":
            continue
        if not match.resolve().is_relative_to(root):
            return (), None, f"{rel.as_posix()}: resolves outside the artifact root"
        if match.is_file():
            stls.append(match)
    if len(stls) > limits.max_stl_files:
        return (), None, f"{len(stls)} STL files exceed the {limits.max_stl_files} file limit"
    for stl in stls:
        error = _too_big(stl, stl.relative_to(root).as_posix(), limits.max_stl_bytes)
        if error is not None:
            return (), None, error
    project = None
    if spec.source.project_3mf is not None:
        candidate = root / spec.source.project_3mf
        if not candidate.resolve().is_relative_to(root):
            return (), None, f"{spec.source.project_3mf}: resolves outside the artifact root"
        if not candidate.is_file():
            return (), None, f"{spec.source.project_3mf}: project 3MF not found"
        error = _too_big(candidate, spec.source.project_3mf, limits.max_3mf_bytes)
        if error is not None:
            return (), None, error
        project = candidate.resolve()
    return tuple(stls), project, None


async def import_stage(spec: ModelSpec, state: RunState, limits: ImportLimits) -> StageReport:
    stls, project, error = await asyncio.to_thread(_scan_source, spec, limits)
    if error is not None:
        return failed(StageName.IMPORT, error)
    if not stls:
        return failed(StageName.IMPORT, f"no STL matches {spec.source.stl_glob!r}")
    root = Path(spec.source.root_dir).resolve()
    state.root = str(root)
    state.stls = tuple(str(p.resolve()) for p in stls)
    state.project_3mf = None if project is None else str(project)
    evidence = tuple(_rel(p, root) for p in state.stls)
    metrics = (("stl_count", str(len(stls))), ("project_3mf", str(project is not None).lower()))
    return _report(StageName.IMPORT, StageOutcome.PASSED, "", metrics, evidence)


def _no_host_path(text: str, root: str) -> str:
    """Strip the artifact root from an adapter message so reports carry no host paths."""
    return text.replace(root + "/", "") if root else text


async def geometry_stage(integrity: MeshIntegrityPort, state: RunState) -> StageReport:
    result = await integrity.check(state.stls)
    bad = [v for v in result.verdicts if not v.passed]
    metrics = (("checked", str(len(result.verdicts))), ("failing", str(len(bad))))
    if result.passed:
        return _report(StageName.GEOMETRY, StageOutcome.PASSED, "", metrics)
    root = Path(state.root) if state.root else None
    detail = "; ".join(
        _no_host_path(
            f"{_rel(v.path, root) if root else v.path}: "
            f"{v.error or 'not a closed, non-self-intersecting mesh'}",
            state.root,
        )
        for v in bad
    )
    return _report(StageName.GEOMETRY, StageOutcome.FAILED, detail, metrics)


async def mechanism_stage(spec: ModelSpec, simulation: MechanismSimulationPort) -> StageReport:
    suites = spec.mechanism.suites
    if not suites:
        return _report(
            StageName.MECHANISM, StageOutcome.NOT_APPLICABLE, "no mechanism suites declared"
        )
    reports = await simulation.run(suites)
    if len(reports) != len(suites):
        return failed(
            StageName.MECHANISM, f"expected {len(suites)} suite reports, got {len(reports)}"
        )
    metrics = tuple((r.suite_id, "passed" if r.passed else "failed") for r in reports)
    bad = [r.suite_id for r in reports if not r.passed]
    outcome = StageOutcome.FAILED if bad else StageOutcome.PASSED
    message = f"suites failed: {', '.join(bad)}" if bad else ""
    return _report(StageName.MECHANISM, outcome, message, metrics, tuple(suites))


async def print_stage(
    spec: ModelSpec, slicing: SlicingPort, state: RunState, run_dir: Path
) -> StageReport:
    if state.project_3mf is None:
        return failed(StageName.PRINT, "no project 3MF to slice")
    request = SliceRequest.from_target(state.project_3mf, str(run_dir / "print"), spec.print_target)
    result = await slicing.slice(request)
    evidence = tuple(
        _rel(p, run_dir) for p in (result.output_3mf, result.settings_json, result.log_path) if p
    )
    metrics = (("return_code", str(result.return_code)),)
    if not result.passed:
        return _report(StageName.PRINT, StageOutcome.FAILED, result.message, metrics, evidence)
    tool = await slicing.availability()
    state.tools = (ToolUse(tool.name, tool.version, SLICER_LICENSE, "subprocess"),)
    return _report(StageName.PRINT, StageOutcome.PASSED, result.message, metrics, evidence)


def _run_files(run_dir: Path) -> tuple[str, ...]:
    """Every file under run_dir except report.json (it changes after packaging)."""
    found = (p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*") if p.is_file())
    return tuple(sorted(f for f in found if f != REPORT_NAME))


async def package_stage(
    run_id: str, spec: ModelSpec, packaging: PackagingPort, state: RunState, run_dir: Path
) -> StageReport:
    files = await asyncio.to_thread(_run_files, run_dir)
    manifest = await packaging.package(run_id, spec.name, str(run_dir), files, tools=state.tools)
    metrics = (("files", str(len(manifest.files))),)
    return _report(
        StageName.PACKAGE,
        StageOutcome.PASSED,
        "",
        metrics,
        (_rel(manifest.manifest_path, run_dir),),
    )
