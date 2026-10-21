"""Host-side STL integrity check: trimesh loads, the CGAL guard judges. No Blender needed."""

from __future__ import annotations

import asyncio

import trimesh

from src.core.domain.mesh_integrity import MeshIntegrityReport, MeshVerdict
from src.verification.mesh_integrity import require_triangle_surface

_SELF_INTERSECTION_MARKER = "Self-intersecting"


def _check_one(path: str) -> MeshVerdict:
    try:
        mesh = trimesh.load(path, file_type="stl", force="mesh")
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError(f"loaded {type(mesh).__name__}, expected a triangle mesh")
        vertices = len(mesh.vertices)
        triangles = len(mesh.faces)
        watertight = bool(mesh.is_watertight)
        soup = {"vertices": mesh.vertices.tolist(), "faces": mesh.faces.tolist()}
    except Exception as exc:  # unreadable input is a verdict, never a crash
        return MeshVerdict(path, 0, 0, False, False, f"{path}: cannot read STL: {exc}")
    if triangles == 0:
        return MeshVerdict(path, vertices, 0, False, False, f"{path}: STL has no triangles")
    try:
        require_triangle_surface(soup)
    except ValueError as exc:
        message = str(exc)
        if _SELF_INTERSECTION_MARKER in message:
            return MeshVerdict(path, vertices, triangles, watertight, True, None)
        if not watertight:
            return MeshVerdict(path, vertices, triangles, False, False, None)
        return MeshVerdict(path, vertices, triangles, watertight, False, f"{path}: {message}")
    return MeshVerdict(path, vertices, triangles, watertight, False, None)


class TrimeshCgalIntegrity:
    async def check(self, stl_paths: tuple[str, ...]) -> MeshIntegrityReport:
        verdicts = await asyncio.to_thread(lambda: tuple(_check_one(p) for p in stl_paths))
        return MeshIntegrityReport(verdicts=verdicts)
