"""Caller-supplied files for the design use cases: one gate, the import caps, no host paths out.

``DesignPipeline.check_meshes`` and ``slice_file`` take paths from a remote host. They pass the
ModelSpec parser's own path gate (``resolve_artifact_file``) and the ``ImportLimits`` caps, and
everything handed back is relative to an artifact root or the runs directory.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from src.core.domain.mesh_integrity import MeshIntegrityReport
from src.core.domain.model_spec import ModelSpecError, resolve_artifact_file
from src.core.domain.slicing import SliceResult


@dataclass(frozen=True, slots=True)
class ResolvedFile:
    absolute: Path
    display: str  # relative to the artifact root the file was found in


def _display(path: Path, roots: tuple[Path, ...]) -> str:
    for root in roots:
        base = root.resolve()
        if path.is_relative_to(base):
            return path.relative_to(base).as_posix()
    return path.name


def resolve_inputs(
    paths: tuple[str, ...],
    *,
    suffix: str,
    roots: tuple[Path, ...],
    max_count: int,
    max_bytes: int,
    max_total_bytes: int | None = None,
) -> tuple[ResolvedFile, ...]:
    """Blocking: gate every path, then enforce the file-count and byte-size caps."""
    if not paths:
        raise ModelSpecError("at least one path is required")
    if len(paths) > max_count:
        raise ModelSpecError(f"{len(paths)} files exceed the {max_count} file limit")
    found: list[ResolvedFile] = []
    total = 0
    for raw in paths:
        try:
            absolute = resolve_artifact_file(raw, suffix=suffix, roots=roots)
        except ModelSpecError as exc:
            raise ModelSpecError(f"{raw}: {exc}") from exc
        display = _display(absolute, roots)
        size = absolute.stat().st_size
        if size > max_bytes:
            raise ModelSpecError(f"{display}: {size} bytes exceeds the {max_bytes} byte limit")
        total += size
        found.append(ResolvedFile(absolute, display))
    if max_total_bytes is not None and total > max_total_bytes:
        raise ModelSpecError(
            f"{total} bytes in total exceed the {max_total_bytes} byte total limit"
        )
    return tuple(found)


class PathScrubber:
    """Replace known host prefixes in free text (adapter messages, log tails)."""

    def __init__(self, roots: tuple[Path, ...], runs_dir: Path) -> None:
        pairs: dict[str, str] = {}
        for directory in (*roots, runs_dir):
            pairs[str(directory.resolve())] = ""
            if directory.is_absolute():
                pairs[str(directory)] = ""
        pairs[tempfile.gettempdir()] = "tmp/"
        pairs[str(Path(tempfile.gettempdir()).resolve())] = "tmp/"
        pairs[str(Path.home())] = "~/"
        self._pairs = sorted(
            ((prefix, repl) for prefix, repl in pairs.items() if prefix not in ("", "/")),
            key=lambda pair: len(pair[0]),
            reverse=True,
        )

    def text(self, value: str, extra: tuple[str, ...] = ()) -> str:
        """Strip the known prefixes plus ``extra`` directories (e.g. the slicer's)."""
        pairs = sorted(
            [*self._pairs, *((d, "") for d in extra if d not in ("", "/"))],
            key=lambda pair: len(pair[0]),
            reverse=True,
        )
        for prefix, repl in pairs:
            value = value.replace(prefix + "/", repl)
        return value


def relative_report(
    report: MeshIntegrityReport, found: tuple[ResolvedFile, ...], scrub: PathScrubber
) -> MeshIntegrityReport:
    """Verdict paths and error texts relative to their artifact root."""
    shown = {str(f.absolute): f.display for f in found}
    verdicts = []
    for verdict in report.verdicts:
        display = shown.get(verdict.path)
        error = verdict.error
        if error is not None:
            if display is not None:
                error = error.replace(verdict.path, display)
            error = scrub.text(error)
        verdicts.append(replace(verdict, path=display or scrub.text(verdict.path), error=error))
    return MeshIntegrityReport(tuple(verdicts))


def relative_slice(result: SliceResult, runs_dir: Path, scrub: PathScrubber) -> SliceResult:
    """Output paths relative to the runs dir (``<run_id>/print/<name>``); message scrubbed."""

    def rel(path: str | None) -> str | None:
        if not path:
            return None
        try:
            return Path(path).resolve().relative_to(runs_dir.resolve()).as_posix()
        except ValueError:
            return Path(path).name

    return replace(
        result,
        output_3mf=rel(result.output_3mf),
        settings_json=rel(result.settings_json),
        log_path=rel(result.log_path) or "",
        message=scrub.text(result.message),
    )
