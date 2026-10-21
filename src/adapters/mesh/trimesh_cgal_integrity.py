"""Host-side STL integrity check: trimesh loads, the CGAL guard judges. No Blender needed."""

from __future__ import annotations

import asyncio
import os
import struct

import trimesh

from src.core.domain.mesh_integrity import MeshIntegrityReport, MeshVerdict
from src.verification.mesh_integrity import (
    cgal_self_intersects,
    parse_closed_surface,
)

# trimesh 5.1.1 defines no load-specific exception type; STL parsing surfaces these.
_LOAD_ERRORS = (OSError, ValueError, EOFError, struct.error)


def _intersects(
    points: list[tuple[float, float, float]], faces: list[tuple[int, int, int]]
) -> bool | None:
    """True/False from CGAL, or None when the conversion could not be evaluated."""
    try:
        return cgal_self_intersects(points, faces)
    except ValueError:
        return None


def _check_one(path: str) -> MeshVerdict:
    if not os.path.isfile(path):
        return MeshVerdict(path, 0, 0, False, None, f"{path}: file not found")
    try:
        mesh = trimesh.load(path, file_type="stl", force="mesh")
    except _LOAD_ERRORS as exc:
        return MeshVerdict(path, 0, 0, False, None, f"{path}: cannot read STL: {exc}")
    if not isinstance(mesh, trimesh.Trimesh):
        reason = f"loaded {type(mesh).__name__}, expected a triangle mesh"
        return MeshVerdict(path, 0, 0, False, None, f"{path}: {reason}")
    vertices, triangles = len(mesh.vertices), len(mesh.faces)
    if triangles == 0:
        return MeshVerdict(path, vertices, 0, False, None, f"{path}: STL has no triangles")
    watertight = bool(mesh.is_watertight)
    soup = {"vertices": mesh.vertices.tolist(), "faces": mesh.faces.tolist()}
    error: str | None = None
    try:
        points, faces = parse_closed_surface(soup)
    except ValueError as exc:
        error = f"{path}: {exc}"
        points = [(float(x), float(y), float(z)) for x, y, z in mesh.vertices]
        faces = [(int(a), int(b), int(c)) for a, b, c in mesh.faces]
    # Self-intersection is evaluated independently of closedness.
    self_intersecting = _intersects(points, faces)
    return MeshVerdict(path, vertices, triangles, watertight, self_intersecting, error)


class TrimeshCgalIntegrity:
    async def check(self, stl_paths: tuple[str, ...]) -> MeshIntegrityReport:
        verdicts = await asyncio.to_thread(lambda: tuple(_check_one(p) for p in stl_paths))
        return MeshIntegrityReport(verdicts=verdicts)
