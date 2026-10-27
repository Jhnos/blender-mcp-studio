"""The five design pipeline stages as plain functions over ports.

Each stage returns a ``StageReport``; an exception is turned into a FAILED report by the
caller. Stages never touch jobs or report.json.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

from src.core.domain.design_run import StageName, StageOutcome, StageReport
from src.core.domain.import_limits import ImportLimits
from src.core.domain.model_spec import (
    ImportedArtifact,
    ModelSpec,
    ModelSpecError,
    PrintTarget,
    is_hidden_path,
    resolve_artifact_file,
)
from src.core.domain.native_revision import CapturedNativeRevision, NativeRevisionError
from src.core.domain.packaging import ToolUse
from src.core.domain.slicing import SliceRequest, ToolUnavailableError
from src.core.ports.mechanism_simulation_port import MechanismSimulationPort
from src.core.ports.mesh_integrity_port import MeshIntegrityPort
from src.core.ports.native_product_port import NativeProductPort
from src.core.ports.packaging_port import PackagingPort
from src.core.ports.slicing_port import SlicingPort
from src.core.use_cases import design_evidence as evidence_docs
from src.core.use_cases.blender_lease import run_to_completion
from src.core.use_cases.design_files import public_run_file, relative_path
from src.core.use_cases.design_reports import REPORT_NAME, write_evidence
from src.core.use_cases.native_revision import NativeRevisionService

SLICER_LICENSE = "AGPL-3.0-only"
MECHANISM_NOT_EVALUATED = "mechanism not evaluated in Phase 1 (import path)"
MAX_SKIPPED_EVIDENCE = 20  # import.json lists at most this many skips; the metric counts all


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


def _too_big(path: Path, rel: str, limit: int) -> str | None:
    size = path.stat().st_size
    return f"{rel}: {size} bytes exceeds the {limit} byte limit" if size > limit else None


@dataclass(frozen=True, slots=True)
class Scan:
    """Result of expanding the source glob; ``error`` set means nothing else is usable."""

    stls: tuple[Path, ...] = ()
    project: Path | None = None
    error: str | None = None
    skipped: tuple[str, ...] = ()


def _scan_source(spec: ModelSpec, limits: ImportLimits) -> Scan:
    """Blocking: expand the glob, gate every file, check caps.

    A lexical skip (hidden relative part, non-``.stl`` suffix) keeps ignored files visible in
    ``skipped``; directories are not files and not skips. Every other match, and the project
    3MF, goes through ``resolve_artifact_file`` - the one path gate - so a symlink into a hidden
    or foreign target fails the stage instead of being read.
    """
    root = Path(spec.source.root_dir).resolve()
    roots = (root,)
    stls: list[tuple[str, Path]] = []
    skipped: list[str] = []
    for match in sorted(root.glob(spec.source.stl_glob)):
        rel = match.relative_to(root).as_posix()
        if is_hidden_path(match.relative_to(root).parts) or match.suffix.lower() != ".stl":
            if match.is_file():
                skipped.append(rel)
            continue
        if not (match.is_file() or match.is_symlink()):
            continue
        try:
            stls.append((rel, resolve_artifact_file(rel, suffix=".stl", roots=roots)))
        except ModelSpecError as exc:
            return Scan(error=f"{rel}: {exc}")
    if len(stls) > limits.max_stl_files:
        return Scan(error=f"{len(stls)} STL files exceed the {limits.max_stl_files} file limit")
    total = 0
    for rel, resolved in stls:
        error = _too_big(resolved, rel, limits.max_stl_bytes)
        if error is not None:
            return Scan(error=error)
        total += resolved.stat().st_size
    if total > limits.max_total_stl_bytes:
        return Scan(
            error=f"{total} STL bytes in total exceed the {limits.max_total_stl_bytes} byte total limit"
        )
    project = None
    if spec.source.project_3mf is not None:
        name = spec.source.project_3mf
        try:
            project = resolve_artifact_file(name, suffix=".3mf", roots=roots)
        except ModelSpecError as exc:
            return Scan(error=f"{name}: {exc}")
        error = _too_big(project, name, limits.max_3mf_bytes)
        if error is not None:
            return Scan(error=error)
    return Scan(tuple(resolved for _, resolved in stls), project, None, tuple(skipped))


async def import_stage(
    spec: ModelSpec, state: RunState, limits: ImportLimits, run_dir: Path
) -> StageReport:
    """Gate and cap the sources, then write ``import.json`` (paths, sha256, bytes, skips)."""
    scan = await asyncio.to_thread(_scan_source, spec, limits)
    stls, project, error, skipped = scan.stls, scan.project, scan.error, scan.skipped
    if error is not None:
        return failed(StageName.IMPORT, error)
    if not stls:
        return failed(StageName.IMPORT, f"no STL matches {spec.source.stl_glob!r}")
    root = Path(spec.source.root_dir).resolve()
    state.root = str(root)
    state.stls = tuple(str(p.resolve()) for p in stls)
    state.project_3mf = None if project is None else str(project)
    doc = await asyncio.to_thread(
        evidence_docs.import_document,
        root,
        tuple(Path(p) for p in state.stls),
        project,
        skipped[:MAX_SKIPPED_EVIDENCE],
    )
    await asyncio.to_thread(write_evidence, run_dir, evidence_docs.IMPORT_EVIDENCE, doc)
    metrics = (
        ("stl_count", str(len(stls))),
        ("project_3mf", str(project is not None).lower()),
        ("skipped", str(len(skipped))),
    )
    return _report(
        StageName.IMPORT, StageOutcome.PASSED, "", metrics, (evidence_docs.IMPORT_EVIDENCE,)
    )


async def geometry_stage(
    integrity: MeshIntegrityPort,
    state: RunState,
    run_dir: Path,
    scrub: Callable[[str], str] = str,
) -> StageReport:
    """Check every imported STL and write ``geometry.json``; the message names each failure once.

    The message is scrubbed by the pipeline's ``_execute`` choke point; ``scrub`` is that same
    scrubber for the reasons written into ``geometry.json``.
    """
    result = await integrity.check(state.stls)
    root = Path(state.root)
    doc = evidence_docs.geometry_document(result, root, scrub)
    await asyncio.to_thread(write_evidence, run_dir, evidence_docs.GEOMETRY_EVIDENCE, doc)
    bad = [v for v in result.verdicts if not v.passed]
    metrics = (("checked", str(len(result.verdicts))), ("failing", str(len(bad))))
    proof = (evidence_docs.GEOMETRY_EVIDENCE,)
    if result.passed:
        return _report(StageName.GEOMETRY, StageOutcome.PASSED, "", metrics, proof)
    detail = "; ".join(evidence_docs.verdict_reason(v, relative_path(v.path, (root,))) for v in bad)
    return _report(StageName.GEOMETRY, StageOutcome.FAILED, detail, metrics, proof)


async def mechanism_stage(spec: ModelSpec, simulation: MechanismSimulationPort) -> StageReport:
    suites = spec.mechanism.suites
    if not suites:
        return _report(StageName.MECHANISM, StageOutcome.NOT_APPLICABLE, MECHANISM_NOT_EVALUATED)
    reports = await simulation.run(suites)
    if len(reports) != len(suites):
        return failed(
            StageName.MECHANISM, f"expected {len(suites)} suite reports, got {len(reports)}"
        )
    metrics = tuple((r.suite_id, "passed" if r.passed else "failed") for r in reports)
    bad = [r.suite_id for r in reports if not r.passed]
    outcome = StageOutcome.FAILED if bad else StageOutcome.PASSED
    message = f"suites failed: {', '.join(bad)}" if bad else ""
    return _report(StageName.MECHANISM, outcome, message, metrics)  # no run-dir evidence


async def print_stage(
    spec: ModelSpec, slicing: SlicingPort, state: RunState, run_dir: Path
) -> StageReport:
    if state.project_3mf is None:
        return failed(StageName.PRINT, "no project 3MF to slice")
    request = SliceRequest.from_target(state.project_3mf, str(run_dir / "print"), spec.print_target)
    try:
        result = await run_to_completion(slicing.slice(request))
    except ToolUnavailableError as exc:
        return failed(StageName.PRINT, str(exc))
    evidence = tuple(
        relative_path(p, (run_dir,))
        for p in (result.output_3mf, result.settings_json, result.log_path)
        if p
    )
    metrics = (("return_code", str(result.return_code)),)
    if not result.passed:
        return _report(StageName.PRINT, StageOutcome.FAILED, result.message, metrics, evidence)
    tool = await slicing.availability()
    state.tools = (ToolUse(tool.name, tool.version, SLICER_LICENSE, "subprocess"),)
    return _report(StageName.PRINT, StageOutcome.PASSED, result.message, metrics, evidence)


def _run_files(run_dir: Path) -> tuple[str, ...]:
    """Every file under run_dir except report.json (it changes after packaging)."""
    found = (
        p.relative_to(run_dir).as_posix()
        for p in run_dir.rglob("*")
        if p.is_file() and public_run_file(run_dir, p)
    )
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
        (relative_path(manifest.manifest_path, (run_dir,)),),
    )


async def native_import_stage(
    run_id: str,
    captured: CapturedNativeRevision,
    native: NativeRevisionService | None,
    products: NativeProductPort | None,
    state: RunState,
    limits: ImportLimits,
    run_dir: Path,
) -> StageReport:
    if native is None or products is None:
        raise NativeRevisionError("native print pipeline is not configured")
    executed = await native.execute_captured(run_id, captured)
    product = await products.build(executed)
    root = (run_dir.parent / product.directory).resolve()
    if root != (run_dir / "native-product").resolve():
        raise NativeRevisionError("native product must belong to the same job")
    spec = replace(
        captured.spec,
        source=ImportedArtifact(
            str(root), "parts/" + captured.spec.source.stl_glob, product.project.path
        ),
    )
    return await import_stage(spec, state, limits, run_dir)


def check_target(target: PrintTarget, slicing: SlicingPort) -> None:
    supported = slicing.supported()
    for label, value, allowed in (
        ("printer", target.printer, supported.printers),
        ("material", target.material, supported.materials),
    ):
        if value not in allowed:
            raise ModelSpecError(
                f"unsupported print_target.{label} {value!r}; supported: {', '.join(allowed)}"
            )


@dataclass(frozen=True, slots=True)
class DesignStages:
    """Stage dependencies and construction, shared by imported and native jobs."""

    limits: ImportLimits
    integrity: MeshIntegrityPort
    simulation: MechanismSimulationPort
    slicing: SlicingPort
    packaging: PackagingPort
    scrub: Callable[[str], str]
    native: NativeRevisionService | None
    products: NativeProductPort | None

    def plan(
        self,
        run_id: str,
        spec: ModelSpec,
        state: RunState,
        run_dir: Path,
        captured: CapturedNativeRevision | None,
    ) -> list[tuple[StageName, Callable[[], Awaitable[StageReport]]]]:
        return [
            (
                StageName.IMPORT,
                lambda: (
                    native_import_stage(
                        run_id,
                        captured,
                        self.native,
                        self.products,
                        state,
                        self.limits,
                        run_dir,
                    )
                    if captured is not None
                    else import_stage(spec, state, self.limits, run_dir)
                ),
            ),
            (
                StageName.GEOMETRY,
                lambda: geometry_stage(self.integrity, state, run_dir, self.scrub),
            ),
            (StageName.MECHANISM, lambda: mechanism_stage(spec, self.simulation)),
            (StageName.PRINT, lambda: print_stage(spec, self.slicing, state, run_dir)),
            (
                StageName.PACKAGE,
                lambda: package_stage(run_id, spec, self.packaging, state, run_dir),
            ),
        ]
