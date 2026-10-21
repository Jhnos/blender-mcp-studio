"""Port for checking that STL files are closed, non-self-intersecting surfaces."""

from __future__ import annotations

from typing import Protocol

from src.core.domain.mesh_integrity import MeshIntegrityReport


class MeshIntegrityPort(Protocol):
    async def check(self, stl_paths: tuple[str, ...]) -> MeshIntegrityReport: ...
