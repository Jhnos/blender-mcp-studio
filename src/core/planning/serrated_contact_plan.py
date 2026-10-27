"""Register an existing tooth annulus and choose shared periodic contact diagonals.

Coordinates are millimetres in the joint frame, with its axis along X. No point
is fitted, moved, added or merged. A caller validates the complete solid before
and after applying this plan; this recognizer only establishes the contact patch.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from math import atan2, cos, dist, hypot, isfinite, pi, sin

from src.core.domain.lab_station import Point
from src.core.domain.lab_station_joints import SerratedJointSpec

Triangle = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class ContactTriangulation:
    faces: tuple[Triangle, ...]
    face_indices: tuple[int, ...]
    outward_x_sign: int


def _registered_keys(
    vertices: Sequence[Point],
    spec: SerratedJointSpec,
    bounds: tuple[float, float],
    tolerance: float,
) -> dict[int, tuple[int, int]]:
    count = spec.teeth * 8
    keys = {}
    for i, (x, y, z) in enumerate(vertices):
        if not bounds[0] < x < bounds[1]:
            continue
        for ring, radius in enumerate((spec.tooth_inner_radius_mm, spec.radius_mm)):
            if abs(hypot(y, z) - radius) > tolerance:
                continue
            q = round(atan2(z, y) * count / (2 * pi)) % count
            angle = q * 2 * pi / count
            if dist((y, z), (radius * cos(angle), radius * sin(angle))) <= tolerance:
                keys[i] = ring, q
    return keys


def _cell_corners(
    indices: Sequence[int], keys: dict[int, tuple[int, int]], count: int
) -> int | None:
    if not all(i in keys for i in indices):
        return None
    radial = {keys[i][0] for i in indices}
    angular = {keys[i][1] for i in indices}
    if len(radial) != 2 or len(angular) != 2:
        return None
    return next((q for q in angular if (q + 1) % count in angular), None)


def plan_contact_triangulation(
    vertices_mm: Sequence[Point],
    faces: Sequence[Triangle],
    spec: SerratedJointSpec,
    *,
    axial_bounds_mm: tuple[float, float],
    registration_mm: float = 0.001,
) -> ContactTriangulation:
    """Reject incomplete/ambiguous annuli; retain all unrelated face records.

    Each cell must contain exactly its four registered corners, one internal
    diagonal, four perimeter edges, and consistent outward winding. Registration
    tolerance identifies existing corners; it does not authorize surface repair.
    """
    count = spec.teeth * 8
    if (
        any(not isfinite(v) for v in (*axial_bounds_mm, registration_mm))
        or axial_bounds_mm[0] >= axial_bounds_mm[1]
        or not 0 < registration_mm < spec.tooth_inner_radius_mm * sin(pi / count) / 2
    ):
        raise ValueError("Invalid contact registration bounds or tolerance")
    if not vertices_mm or any(len(p) != 3 or any(not isfinite(v) for v in p) for p in vertices_mm):
        raise ValueError("Contact source requires finite 3D coordinates")
    if any(
        len(f) != 3 or any(type(i) is not int or not 0 <= i < len(vertices_mm) for i in f)
        for f in faces
    ):
        raise ValueError("Contact source requires valid triangle indices")
    keys = _registered_keys(vertices_mm, spec, axial_bounds_mm, registration_mm)
    cells: dict[int, list[int]] = {}
    index_by_key: dict[tuple[int, int], int] = {}
    signs: set[int] = set()
    for fi, face in enumerate(faces):
        q = _cell_corners(face, keys, count)
        if q is None:
            continue
        cells.setdefault(q, []).append(fi)
        for i in face:
            key = keys[i]
            if key in index_by_key and index_by_key[key] != i:
                raise ValueError("Ambiguous contact corner")
            index_by_key[key] = i
        p0, p1, p2 = (vertices_mm[i] for i in face)
        normal_x = (p1[1] - p0[1]) * (p2[2] - p0[2]) - (p1[2] - p0[2]) * (p2[1] - p0[1])
        if normal_x == 0:
            raise ValueError("Degenerate contact triangle")
        signs.add(1 if normal_x > 0 else -1)
    if (
        set(cells) != set(range(count))
        or any(len(ids) != 2 for ids in cells.values())
        or len(index_by_key) != count * 2
        or len(signs) != 1
    ):
        raise ValueError("Incomplete or inconsistently wound contact annulus")
    outward = signs.pop()
    result = list(faces)
    selected = []
    for q in range(count):
        a, b, c, d = (
            index_by_key[key]
            for key in ((0, q), (1, q), (1, (q + 1) % count), (0, (q + 1) % count))
        )
        ids = cells[q]
        edges = Counter(
            tuple(sorted((f[i], f[(i + 1) % 3])))
            for fi in ids
            for f in (faces[fi],)
            for i in range(3)
        )
        perimeter = {tuple(sorted(e)) for e in ((a, b), (b, c), (c, d), (d, a))}
        if {e for e, n in edges.items() if n == 1} != perimeter or sorted(edges.values()) != [
            1,
            1,
            1,
            1,
            2,
        ]:
            raise ValueError("Contact cell does not cover one quadrilateral")
        for fi, triangle in zip(ids, ((a, b, c), (a, c, d)), strict=True):
            result[fi] = triangle if outward > 0 else (triangle[2], triangle[1], triangle[0])
            selected.append(fi)
    return ContactTriangulation(tuple(result), tuple(sorted(selected)), outward)
