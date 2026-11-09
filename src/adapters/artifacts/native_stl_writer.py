"""Complete original-identity STL sets; no selection, slicing or automatic promotion."""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

import trimesh

from src.adapters.artifacts.native_source import read_source_asset
from src.core.domain.import_limits import ImportLimits
from src.core.domain.native_revision import (
    NativeModelSource,
    NativeRevisionError,
    NativeStlSet,
    SourceArtifact,
)
from src.core.ports.mesh_integrity_port import MeshIntegrityPort
from src.core.use_cases.blender_lease import run_to_completion
from src.verification.mesh_integrity import parse_closed_surface


def _fingerprint(path: str, payload: bytes) -> SourceArtifact:
    return SourceArtifact(path, hashlib.sha256(payload).hexdigest(), len(payload))


class NativeStlWriter:
    def __init__(self, integrity: MeshIntegrityPort, limits: ImportLimits) -> None:
        self._integrity, self._limits = integrity, limits

    async def write(
        self,
        source: NativeModelSource,
        snapshot: Path,
        native: Path,
        native_receipt: SourceArtifact,
        changed: Mapping[str, Mapping[str, object]],
        changed_owners: tuple[str, ...],
        output: Path,
    ) -> NativeStlSet:
        owned = threading.Event()
        try:
            result = await run_to_completion(
                asyncio.to_thread(
                    self._files,
                    source,
                    snapshot,
                    native,
                    native_receipt,
                    changed,
                    changed_owners,
                    output,
                    owned,
                )
            )
            paths = tuple(str((output / part.path).resolve()) for part in result.parts)
            verdict = await run_to_completion(self._integrity.check(paths))
            if (
                len(verdict.verdicts) != len(paths)
                or {v.path for v in verdict.verdicts} != set(paths)
                or not verdict.passed
            ):
                raise NativeRevisionError(
                    "complete native STL set failed independent geometry validation"
                )
            await run_to_completion(asyncio.to_thread(self._finish, result, snapshot, output))
            return result
        except BaseException as exc:
            if owned.is_set():
                for name in ("native-output.json", "SHA256.json"):
                    (output / name).unlink(missing_ok=True)
            if isinstance(exc, (OSError, ValueError)):
                raise NativeRevisionError("native STL set could not be completed") from exc
            raise

    def _files(
        self,
        source: NativeModelSource,
        snapshot: Path,
        native: Path,
        native_receipt: SourceArtifact,
        changed: Mapping[str, Mapping[str, object]],
        changed_owners: tuple[str, ...],
        output: Path,
        owned: threading.Event,
    ) -> NativeStlSet:
        if (
            not changed_owners
            or len(set(changed_owners)) != len(changed_owners)
            or set(changed) != set(changed_owners)
        ):
            raise NativeRevisionError(
                "changed surfaces must exactly match registered recipe owners"
            )
        if not 0 < len(source.parts) <= self._limits.max_stl_files or len(
            {p.path for p in source.parts}
        ) != len(source.parts):
            raise NativeRevisionError("native output requires a unique complete original part set")
        if sum(part.size_bytes for part in source.parts) > self._limits.max_total_stl_bytes:
            raise NativeRevisionError("original STL set exceeds configured input byte limits")
        for owner in changed_owners:
            if sum(Path(part.path).stem == owner for part in source.parts) != 1:
                raise NativeRevisionError("changed owner is missing or ambiguous in original parts")
        if (
            native_receipt.path != native.name
            or native.suffix.lower() != ".blend"
            or native.is_symlink()
        ):
            raise NativeRevisionError("native output requires its exact validated candidate")
        native_payload = read_source_asset(native.parent, native_receipt, source.total_bytes)
        originals = {
            part.path: read_source_asset(snapshot, part, self._limits.max_stl_bytes)
            for part in source.parts
        }
        output.mkdir(parents=True, exist_ok=False)
        owned.set()
        with (output / native_receipt.path).open("xb") as handle:
            handle.write(native_payload)
        parts, changed_paths, total = [], [], 0
        for part in source.parts:
            owner = Path(part.path).stem
            payload = originals[part.path]
            if owner in changed:
                points, faces = parse_closed_surface(changed[owner])
                mesh = trimesh.Trimesh(vertices=points, faces=faces, process=False)
                payload = trimesh.exchange.stl.export_stl(mesh)
                changed_paths.append(part.path)
            total += len(payload)
            if (
                len(payload) > self._limits.max_stl_bytes
                or total > self._limits.max_total_stl_bytes
            ):
                raise NativeRevisionError("native STL set exceeds configured print byte limits")
            destination = output / part.path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(payload)
            parts.append(_fingerprint(part.path, payload))
        return NativeStlSet(source, native_receipt, tuple(parts), tuple(changed_paths))

    def _finish(self, result: NativeStlSet, snapshot: Path, output: Path) -> None:
        expected = {item.path: item for item in (result.native, *result.parts)}
        actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
        if actual != set(expected):
            raise NativeRevisionError("native output file population changed during validation")
        for part in result.source.parts:
            read_source_asset(snapshot, part, self._limits.max_stl_bytes)
        for item in expected.values():
            read_source_asset(
                output, item, max(result.source.total_bytes, self._limits.max_stl_bytes)
            )
        payload = json.dumps(asdict(result), ensure_ascii=False, indent=2).encode()
        with (output / "native-output.json").open("xb") as handle:
            handle.write(payload)
        manifest = {item.path: item.sha256 for item in expected.values()}
        manifest["native-output.json"] = hashlib.sha256(payload).hexdigest()
        with (output / "SHA256.json").open("x") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
