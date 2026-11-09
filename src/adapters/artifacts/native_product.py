"""Complete validated STL delivery before deriving the same-parts plate template."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

from src.adapters.artifacts.native_source import read_source_asset, unique_native_object
from src.adapters.artifacts.native_stl_writer import NativeStlWriter
from src.adapters.artifacts.plate_project import PlateProject
from src.core.domain.import_limits import ImportLimits
from src.core.domain.native_revision import (
    NativeModelSource,
    NativePrintProduct,
    NativeRevisionError,
    NativeRevisionResult,
    NativeStlSet,
    SourceArtifact,
)
from src.core.planning.screen_revision_plan import SCREEN_MODIFIED_OWNERS
from src.core.ports.mesh_integrity_port import MeshIntegrityPort
from src.core.use_cases.blender_lease import run_to_completion
from src.infrastructure.narrowing import as_mapping
from src.verification.artifact_files import binary_stl_surface


class NativeProductWriter:
    def __init__(self, integrity: MeshIntegrityPort, limits: ImportLimits, runs_dir: Path) -> None:
        self._stls = NativeStlWriter(integrity, limits)
        self._limits, self._runs_dir = limits, runs_dir.resolve()

    def _path(self, relative: str) -> Path:
        path = Path(relative)
        if path.is_absolute() or not path.parts or any(p in (".", "..") for p in path.parts):
            raise NativeRevisionError("native product requires a job-relative path")
        candidate = self._runs_dir
        for part in path.parts:
            candidate /= part
            if candidate.is_symlink():
                raise NativeRevisionError("native product paths must not be symlinks")
        if not candidate.resolve().is_relative_to(self._runs_dir):
            raise NativeRevisionError("native product path escapes its job root")
        return candidate

    async def build(self, result: NativeRevisionResult) -> NativePrintProduct:
        execution = self._path(result.directory)
        snapshot = self._path(result.prepared.staged.directory)
        if execution.parent != snapshot.parent:
            raise NativeRevisionError("native execution and snapshot must belong to the same job")
        changed = await asyncio.to_thread(self._surfaces, execution, result.surfaces)
        return await self.write(
            result.prepared.staged.source,
            snapshot,
            execution / result.native.path,
            result.native,
            changed,
            SCREEN_MODIFIED_OWNERS,
            execution.parent / "native-product",
        )

    def _surfaces(
        self, execution: Path, receipt: SourceArtifact
    ) -> dict[str, Mapping[str, object]]:
        payload = read_source_asset(execution, receipt, 128 * 1024 * 1024)
        data = as_mapping(json.loads(payload, object_pairs_hook=unique_native_object))
        if data is None:
            raise NativeRevisionError("native product requires changed surface receipts")
        changed = {}
        for owner, value in data.items():
            surface = as_mapping(value)
            if not isinstance(owner, str) or surface is None:
                raise NativeRevisionError("native product surface receipt is malformed")
            changed[owner] = surface
        return changed

    async def write(
        self,
        source: NativeModelSource,
        snapshot: Path,
        native: Path,
        native_receipt: SourceArtifact,
        changed: Mapping[str, Mapping[str, object]],
        changed_owners: tuple[str, ...],
        output: Path,
    ) -> NativePrintProduct:
        try:
            relative = output.relative_to(self._runs_dir).as_posix()
            self._path(relative)
            await run_to_completion(asyncio.to_thread(output.mkdir, parents=True, exist_ok=False))
            stls = await self._stls.write(
                source, snapshot, native, native_receipt, changed, changed_owners, output / "parts"
            )
            return await run_to_completion(
                asyncio.to_thread(self._plate, source, snapshot, stls, output, relative)
            )
        except (OSError, ValueError) as exc:
            raise NativeRevisionError("native print product could not be completed") from exc

    def _plate(
        self,
        source: NativeModelSource,
        snapshot: Path,
        stls: NativeStlSet,
        output: Path,
        relative: str,
    ) -> NativePrintProduct:
        receipt = source.project_3mf
        if receipt is None:
            raise NativeRevisionError("native product requires its captured plate template")
        project = PlateProject(
            read_source_asset(snapshot, receipt, self._limits.max_3mf_bytes),
            tuple(Path(p.path).stem for p in source.parts),
            max_bytes=self._limits.max_3mf_bytes,
        )
        original = {p.path: p for p in source.parts}
        revised = {p.path: p for p in stls.parts}
        changes = {
            Path(name).stem: (
                binary_stl_surface(
                    read_source_asset(snapshot, original[name], self._limits.max_stl_bytes)
                ),
                binary_stl_surface(
                    read_source_asset(output / "parts", revised[name], self._limits.max_stl_bytes)
                ),
            )
            for name in stls.changed_paths
        }
        payload, _ = project.revise(changes)
        with (output / "project.3mf").open("xb") as handle:
            handle.write(payload)
        result = NativePrintProduct(
            relative,
            stls,
            SourceArtifact("project.3mf", hashlib.sha256(payload).hexdigest(), len(payload)),
        )
        with (output / "product.json").open("x") as handle:
            json.dump(asdict(result), handle, ensure_ascii=False, indent=2)
        return result
