"""Resolve the manifest's unique native source and complete selected STL identities."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath

from src.core.domain.import_limits import ImportLimits
from src.core.domain.model_spec import ModelSpec, ModelSpecError, resolve_artifact_file
from src.core.domain.native_revision import NativeModelSource, NativeSourceError, SourceArtifact
from src.infrastructure.narrowing import as_mapping

DEFAULT_MANIFEST_BYTES = 1024 * 1024


def unique_native_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise NativeSourceError("duplicate source manifest key")
        result[key] = value
    return result


def source_asset_path(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or path.as_posix() != name
    ):
        raise NativeSourceError("source manifest paths must be canonical and portable")
    lexical = root
    for part in path.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise NativeSourceError(f"source entry must not be a symlink: {name}")
    try:
        resolved = resolve_artifact_file(name, suffix=path.suffix, roots=(root,))
    except ModelSpecError as exc:
        raise NativeSourceError(f"invalid or missing source entry: {name}") from exc
    return resolved


def read_source_asset(root: Path, expected: SourceArtifact, budget: int) -> bytes:
    """Read one captured asset without accepting a changed or oversized file."""
    if not 0 < expected.size_bytes <= budget:
        raise NativeSourceError("source input exceeds its verified byte budget")
    with source_asset_path(root, expected.path).open("rb") as handle:
        payload = handle.read(expected.size_bytes + 1)
        size = os.fstat(handle.fileno()).st_size
    if (
        size != expected.size_bytes
        or len(payload) != expected.size_bytes
        or hashlib.sha256(payload).hexdigest() != expected.sha256
    ):
        raise NativeSourceError("source input fingerprint changed")
    return payload


def fingerprint_source_asset(path: Path, name: str, budget: int) -> SourceArtifact:
    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            if before.st_size > budget:
                raise NativeSourceError(f"source byte budget exceeded: {name}")
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
            after = os.fstat(handle.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise NativeSourceError(f"source entry changed during read: {name}")
        return SourceArtifact(name, digest, after.st_size)
    except OSError as exc:
        raise NativeSourceError(f"cannot read source entry: {name}") from exc


class FilesystemNativeSource:
    """Readonly, bounded file identity checks; Blender format/geometry is not evaluated."""

    def __init__(
        self,
        roots: tuple[Path, ...],
        limits: ImportLimits,
        *,
        max_source_bytes: int = 512 * 1024 * 1024,
        max_manifest_bytes: int = DEFAULT_MANIFEST_BYTES,
    ) -> None:
        if any(type(v) is not int or v <= 0 for v in (max_source_bytes, max_manifest_bytes)):
            raise ValueError("native source budgets must be positive integers")
        self._roots = roots
        self._limits = limits
        self._source_budget = max_source_bytes
        self._manifest_budget = max_manifest_bytes

    async def resolve(self, spec: ModelSpec) -> NativeModelSource:
        try:
            return await asyncio.to_thread(self._resolve, spec)
        except (OSError, RuntimeError) as exc:
            raise NativeSourceError("native source directory is unavailable") from exc

    def _resolve(self, spec: ModelSpec) -> NativeModelSource:
        root = Path(spec.source.root_dir).resolve()
        anchor = next((p.resolve() for p in self._roots if root.is_relative_to(p.resolve())), None)
        if anchor is None or not root.is_dir():
            raise NativeSourceError("selected native root is not an available approved directory")
        manifest_path = source_asset_path(root, "SHA256.json")
        try:
            with manifest_path.open("rb") as handle:
                raw = handle.read(self._manifest_budget + 1)
            if len(raw) > self._manifest_budget:
                raise NativeSourceError("source manifest byte budget exceeded")
            manifest = as_mapping(json.loads(raw, object_pairs_hook=unique_native_object))
        except (OSError, ValueError) as exc:
            raise NativeSourceError("source checksum manifest is unreadable") from exc
        if not manifest:
            raise NativeSourceError("source checksum manifest must be a nonempty object")
        files: dict[str, SourceArtifact] = {}
        total = 0
        for name, expected in sorted(manifest.items()):
            path = source_asset_path(root, name)
            if not isinstance(expected, str) or re.fullmatch("[0-9a-fA-F]{64}", expected) is None:
                raise NativeSourceError(f"invalid source checksum: {name}")
            budget = self._source_budget - total
            if path.suffix.lower() == ".stl":
                budget = min(budget, self._limits.max_stl_bytes)
            if path.suffix.lower() == ".3mf":
                budget = min(budget, self._limits.max_3mf_bytes)
            receipt = fingerprint_source_asset(path, name, budget)
            if receipt.sha256 != expected.lower():
                raise NativeSourceError(f"source checksum mismatch: {name}")
            files[name] = receipt
            total += receipt.size_bytes
        natives = [v for n, v in files.items() if PurePosixPath(n).suffix.lower() == ".blend"]
        if len(natives) != 1 or natives[0].size_bytes == 0:
            raise NativeSourceError("source manifest must declare exactly one native file")
        selected = []
        try:
            for path in sorted(root.glob(spec.source.stl_glob)):
                if path.is_symlink():
                    raise NativeSourceError("selected source part must not be a symlink")
                if not path.is_file():
                    continue
                name = path.relative_to(root).as_posix()
                source_asset_path(root, name)
                if name not in files:
                    raise NativeSourceError(
                        f"selected part is absent from checksum manifest: {name}"
                    )
                if files[name].size_bytes == 0:
                    raise NativeSourceError(f"selected source part is empty: {name}")
                selected.append(files[name])
        except OSError as exc:
            raise NativeSourceError("cannot enumerate selected source parts") from exc
        if not selected or len(selected) > self._limits.max_stl_files:
            raise NativeSourceError("selected source parts are empty or exceed the file limit")
        if sum(v.size_bytes for v in selected) > self._limits.max_total_stl_bytes:
            raise NativeSourceError("selected source parts exceed the total STL byte limit")
        project = None
        if spec.source.project_3mf is not None:
            project = files.get(spec.source.project_3mf)
            if project is None or project.size_bytes == 0:
                raise NativeSourceError("selected project is absent from checksum manifest")
        manifest_digest = hashlib.sha256(raw).hexdigest()
        final_manifest = fingerprint_source_asset(
            manifest_path, "SHA256.json", self._manifest_budget
        )
        if final_manifest.sha256 != manifest_digest:
            raise NativeSourceError("source manifest changed during asset verification")
        return NativeModelSource(
            spec.name,
            root.relative_to(anchor).as_posix(),
            natives[0],
            tuple(selected),
            project,
            manifest_digest,
            len(files),
            total,
        )
