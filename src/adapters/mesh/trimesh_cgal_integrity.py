"""Host-side STL integrity check: trimesh loads, the CGAL guard judges. No Blender needed."""

from __future__ import annotations

import asyncio
import os

from src.adapters.mesh.stl_loader import load_stl
from src.core.domain.mesh_integrity import MeshIntegrityReport, MeshVerdict
from src.verification.mesh_integrity import (
    cgal_self_intersects,
    parse_closed_surface,
)


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
        mesh = load_stl(path)
    except ValueError as exc:
        return MeshVerdict(path, 0, 0, False, None, f"{path}: {exc}")
    vertices, triangles = len(mesh.vertices), len(mesh.faces)
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
