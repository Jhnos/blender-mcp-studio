"""Hash files already under a run directory and write run_dir/manifest.json.

Copies nothing. The manifest is byte-stable: sorted keys, files sorted by relative POSIX
path, no timestamps and no absolute paths.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import struct
from pathlib import Path

import trimesh

from src.core.domain.packaging import PackagedFile, PackageManifest

MANIFEST_NAME = "manifest.json"
_LOAD_ERRORS = (OSError, ValueError, EOFError, struct.error)
_CHUNK = 1 << 20


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _triangles(path: Path) -> int:
    try:
        mesh = trimesh.load(str(path), file_type="stl", force="mesh")
    except _LOAD_ERRORS as exc:
        raise ValueError(f"{path.name}: cannot read STL: {exc}") from exc
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"{path.name}: loaded {type(mesh).__name__}, expected a triangle mesh")
    if len(mesh.faces) == 0:
        raise ValueError(f"{path.name}: STL has no triangles")
    return int(len(mesh.faces))


def _resolve_inside(root: Path, raw: str) -> Path:
    resolved = Path(raw).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{raw}: file is outside the run directory")
    return resolved


def _build(run_id: str, spec_name: str, run_dir: str, files: tuple[str, ...]) -> PackageManifest:
    root = Path(run_dir).resolve()
    resolved = {_resolve_inside(root, raw) for raw in files}
    entries: list[PackagedFile] = []
    for path in sorted(resolved, key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if rel == MANIFEST_NAME:
            continue
        if not path.is_file():
            raise ValueError(f"{rel}: file not found")
        triangles = _triangles(path) if path.suffix.lower() == ".stl" else None
        entries.append(PackagedFile(rel, _sha256(path), path.stat().st_size, triangles))
    payload = {
        "run_id": run_id,
        "spec_name": spec_name,
        "files": [
            {"path": f.path, "sha256": f.sha256, "bytes": f.bytes, "triangles": f.triangles}
            for f in entries
        ],
    }
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    manifest_path = root / MANIFEST_NAME
    manifest_path.write_text(text, encoding="utf-8")
    return PackageManifest(run_id, spec_name, tuple(entries), str(manifest_path))


class ManifestPackager:
    async def package(
        self, run_id: str, spec_name: str, run_dir: str, files: tuple[str, ...]
    ) -> PackageManifest:
        return await asyncio.to_thread(_build, run_id, spec_name, run_dir, files)
