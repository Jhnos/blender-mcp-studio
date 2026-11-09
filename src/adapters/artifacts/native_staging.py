"""Exclusive, byte-bounded snapshots of an already selected native source."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path
from threading import Event

from src.adapters.artifacts.native_source import (
    DEFAULT_MANIFEST_BYTES,
    fingerprint_source_asset,
    source_asset_path,
)
from src.core.domain.model_spec import ModelSpec
from src.core.domain.native_revision import NativeModelSource, NativeSourceError, StagedNativeSource
from src.core.ports.native_source_port import NativeSourcePort
from src.core.use_cases.blender_lease import run_to_completion
from src.infrastructure.narrowing import as_mapping


class FilesystemNativeStaging:
    def __init__(
        self,
        sources: NativeSourcePort,
        runs_dir: Path,
        *,
        max_manifest_bytes: int = DEFAULT_MANIFEST_BYTES,
    ) -> None:
        if type(max_manifest_bytes) is not int or max_manifest_bytes <= 0:
            raise ValueError("snapshot manifest budget must be a positive integer")
        self._sources = sources
        self._runs_dir = runs_dir.resolve()
        self._manifest_budget = max_manifest_bytes

    async def stage(
        self, spec: ModelSpec, expected: NativeModelSource, run_id: str
    ) -> StagedNativeSource:
        if not isinstance(run_id, str) or re.fullmatch(r"[0-9a-f]{32}", run_id) is None:
            raise NativeSourceError("invalid native snapshot job identifier")
        if await self._sources.resolve(spec) != expected:
            raise NativeSourceError("native source receipt is stale")
        if expected.total_bytes <= 0:
            raise NativeSourceError("native source receipt has no verified byte budget")
        owned = Event()
        try:
            await run_to_completion(asyncio.to_thread(self._copy, spec, expected, run_id, owned))
        except asyncio.CancelledError:
            if owned.is_set():
                await run_to_completion(asyncio.to_thread(self._failure, run_id))
            raise
        try:
            if await self._sources.resolve(spec) != expected:
                raise NativeSourceError("native source changed during snapshot")
            result = StagedNativeSource(expected, f"{run_id}/native-source")
            await run_to_completion(asyncio.to_thread(self._receipt, run_id, result))
        except (NativeSourceError, asyncio.CancelledError):
            await run_to_completion(asyncio.to_thread(self._failure, run_id))
            raise
        return result

    def _copy(self, spec: ModelSpec, source: NativeModelSource, run_id: str, owned: Event) -> None:
        job = self._runs_dir / run_id
        destination = job / "native-source"
        created = False
        try:
            if any(p.is_symlink() for p in (job, self._runs_dir, *self._runs_dir.parents)):
                raise NativeSourceError("native snapshot job directory must not be symlinked")
            job.mkdir(parents=True, exist_ok=True)
            destination.mkdir()  # Exclusive: never truncate another job or partial snapshot.
            created = True
            owned.set()
            origin = Path(spec.source.root_dir)
            with source_asset_path(origin, "SHA256.json").open("rb") as handle:
                raw = handle.read(self._manifest_budget + 1)
            if (
                len(raw) > self._manifest_budget
                or hashlib.sha256(raw).hexdigest() != source.manifest_sha256
            ):
                raise NativeSourceError("native source manifest changed before snapshot")
            manifest = as_mapping(json.loads(raw))
            if manifest is None or len(manifest) != source.verified_files:
                raise NativeSourceError("native source manifest population changed")
            remaining = source.total_bytes
            for name, expected in sorted(manifest.items()):
                origin_file = source_asset_path(origin, name)
                target = destination / name  # Shared path gate has validated this relative name.
                target.parent.mkdir(parents=True, exist_ok=True)
                with origin_file.open("rb") as incoming, target.open("xb") as outgoing:
                    while block := incoming.read(min(1024 * 1024, remaining + 1)):
                        if len(block) > remaining:
                            raise NativeSourceError("native snapshot exceeds verified byte budget")
                        outgoing.write(block)
                        remaining -= len(block)
                with target.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                if not isinstance(expected, str) or digest != expected.lower():
                    raise NativeSourceError(f"native snapshot checksum mismatch: {name}")
            if remaining:
                raise NativeSourceError("native snapshot is shorter than its verified source")
            with (destination / "SHA256.json").open("xb") as handle:
                handle.write(raw)
        except (OSError, ValueError, NativeSourceError) as exc:
            if created:
                self._failure(run_id)
            if isinstance(exc, NativeSourceError):
                raise
            raise NativeSourceError("cannot create native source snapshot") from exc

    def _failure(self, run_id: str) -> None:
        try:
            (self._runs_dir / run_id / "native-source-receipt.json").unlink(missing_ok=True)
            with (self._runs_dir / run_id / "native-source-failure.json").open("x") as handle:
                json.dump({"scope": "file_identity_only", "verified": False}, handle)
        except FileExistsError:
            pass  # Preserve the first diagnostic, never replace it on a retry.
        except OSError as exc:
            raise NativeSourceError("cannot record native snapshot failure") from exc

    def _receipt(self, run_id: str, result: StagedNativeSource) -> None:
        destination = self._runs_dir / result.directory
        source = result.source
        try:
            with source_asset_path(destination, "SHA256.json").open("rb") as handle:
                raw = handle.read(self._manifest_budget + 1)
            if hashlib.sha256(raw).hexdigest() != source.manifest_sha256:
                raise NativeSourceError("snapshot manifest changed during copying")
            manifest = as_mapping(json.loads(raw))
            if manifest is None:
                raise NativeSourceError("invalid snapshot manifest")
            paths = list(destination.rglob("*"))
            if any(p.is_symlink() for p in paths):
                raise NativeSourceError("snapshot contains a symlink")
            found = {p.relative_to(destination).as_posix() for p in paths if p.is_file()}
            if found != {*manifest, "SHA256.json"}:
                raise NativeSourceError("snapshot asset population changed during copying")
            remaining = source.total_bytes
            for name, expected in sorted(manifest.items()):
                path = source_asset_path(destination, name)
                actual = fingerprint_source_asset(path, name, remaining)
                if actual.sha256 != str(expected).lower():
                    raise NativeSourceError(f"snapshot asset changed during copying: {name}")
                remaining -= actual.size_bytes
            if remaining:
                raise NativeSourceError("snapshot byte population changed during copying")
            with (self._runs_dir / run_id / "native-source-receipt.json").open("x") as handle:
                json.dump({"scope": "file_identity_only", "snapshot": asdict(result)}, handle)
        except (OSError, ValueError) as exc:
            raise NativeSourceError("cannot verify native source snapshot receipt") from exc
