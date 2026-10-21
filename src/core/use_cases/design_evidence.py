"""Evidence documents a user can open for the import and geometry stages (no host paths).

``import.json`` checksums every source file the run read (STLs and the project 3MF), so the
package manifest, which checksums ``import.json``, transitively pins the verified sources.
``geometry.json`` holds every verdict with its path relative to the artifact root.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from src.core.domain.mesh_integrity import MeshIntegrityReport, MeshVerdict
from src.core.use_cases.design_files import relative_path

IMPORT_EVIDENCE = "import.json"
GEOMETRY_EVIDENCE = "geometry.json"
_CHUNK = 1 << 20


def _file_row(path: Path, root: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
    return {
        "path": relative_path(path, (root,)),
        "sha256": digest.hexdigest(),
        "bytes": path.stat().st_size,
    }


def import_document(
    root: Path, stls: tuple[Path, ...], project: Path | None, skipped: tuple[str, ...]
) -> dict[str, object]:
    """Blocking (hashes files): sources relative to ``root`` with sha256 and size."""
    return {
        "stls": [_file_row(p, root) for p in stls],
        "project_3mf": None if project is None else _file_row(project, root),
        "skipped": list(skipped),
    }


def verdict_reason(verdict: MeshVerdict, shown: str) -> str:
    """The failure reason without the adapter's ``<path>: `` prefix, named once by ``shown``."""
    reason = verdict.error or "not a closed, non-self-intersecting mesh"
    return f"{shown}: {reason.removeprefix(verdict.path + ': ')}"


def geometry_document(
    report: MeshIntegrityReport, root: Path, scrub: Callable[[str], str]
) -> dict[str, object]:
    """Every verdict root-relative; reasons pass the pipeline's one host-path scrubber."""
    rows = []
    for v in report.verdicts:
        shown = relative_path(v.path, (root,))
        rows.append(
            {
                "path": shown,
                "passed": v.passed,
                "vertices": v.vertices,
                "triangles": v.triangles,
                "watertight": v.watertight,
                "self_intersecting": v.self_intersecting,
                "error": None if v.passed else scrub(verdict_reason(v, shown)),
            }
        )
    return {"passed": report.passed, "verdicts": rows}
