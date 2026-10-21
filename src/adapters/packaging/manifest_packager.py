"""Hash files already under a run directory and write run_dir/manifest.json.

Copies nothing. The manifest is byte-stable: sorted keys, files and tools sorted, no
timestamps and no absolute paths. It also records the external tools used and their
licences (the slicer is an AGPL-3.0 black-box subprocess).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path

from src.adapters.mesh.stl_loader import load_stl
from src.core.domain.packaging import PackagedFile, PackageManifest, ToolUse

MANIFEST_NAME = "manifest.json"
_TMP_NAME = MANIFEST_NAME + ".tmp"
_CHUNK = 1 << 20


def _hash_and_size(path: Path) -> tuple[str, int]:
    """sha256 and byte count from the same read, so they describe the same file state."""
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _triangles(path: Path) -> int:
    try:
        return len(load_stl(path).faces)
    except ValueError as exc:
        raise ValueError(f"{path.name}: {exc}") from exc


def _resolve_inside(root: Path, raw: str) -> Path:
    # Relative inputs are run_dir-relative; an absolute raw stays as it is.
    resolved = (root / raw).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{raw}: file is outside the run directory")
    return resolved


def _tool_dict(tool: ToolUse) -> dict[str, str | None]:
    return {
        "name": tool.name,
        "version": tool.version,
        "license": tool.license,
        "invocation": tool.invocation,
    }


def _write_atomic(root: Path, text: str) -> Path:
    tmp = root / _TMP_NAME
    final = root / MANIFEST_NAME
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, final)
    finally:
        tmp.unlink(missing_ok=True)
    return final


def _build(
    run_id: str,
    spec_name: str,
    run_dir: str,
    files: tuple[str, ...],
    tools: tuple[ToolUse, ...],
) -> PackageManifest:
    if not Path(run_dir).is_dir():
        raise ValueError(f"{run_dir}: run directory not found")
    root = Path(run_dir).resolve()
    resolved = {_resolve_inside(root, raw) for raw in files}
    entries: list[PackagedFile] = []
    for path in sorted(resolved, key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if rel in (MANIFEST_NAME, _TMP_NAME):
            continue
        if not path.is_file():
            raise ValueError(f"{rel}: file not found")
        triangles = _triangles(path) if path.suffix.lower() == ".stl" else None
        digest, size = _hash_and_size(path)
        entries.append(PackagedFile(rel, digest, size, triangles))
    ordered_tools = tuple(sorted(tools, key=lambda t: t.name))
    payload = {
        "run_id": run_id,
        "spec_name": spec_name,
        "files": [
            {"path": f.path, "sha256": f.sha256, "bytes": f.bytes, "triangles": f.triangles}
            for f in entries
        ],
        "tools": [_tool_dict(t) for t in ordered_tools],
    }
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    manifest_path = _write_atomic(root, text)
    return PackageManifest(run_id, spec_name, tuple(entries), str(manifest_path), ordered_tools)


class ManifestPackager:
    async def package(
        self,
        run_id: str,
        spec_name: str,
        run_dir: str,
        files: tuple[str, ...],
        *,
        tools: tuple[ToolUse, ...] = (),
    ) -> PackageManifest:
        return await asyncio.to_thread(_build, run_id, spec_name, run_dir, files, tools)
