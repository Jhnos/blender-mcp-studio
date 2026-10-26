"""Independent closed triangle-surface checks; no repair or geometry simplification."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence

from CGAL.CGAL_Kernel import Point_3
from CGAL.CGAL_Polygon_mesh_processing import (
    Side_of_triangle_mesh,
    does_self_intersect,
    polygon_soup_to_polygon_mesh,
)
from CGAL.CGAL_Polyhedron_3 import Polyhedron_3

from src.infrastructure.narrowing import (
    as_finite_number,
    as_int,
    as_nonempty_sequence,
    required,
)


class SelfIntersectionError(ValueError):
    """The triangle surface intersects itself (still a ValueError for existing callers)."""


Point = tuple[float, float, float]
Triangle = tuple[int, int, int]


def _array(value: object) -> Sequence[object]:
    return required(
        value, as_nonempty_sequence, message="Mesh array is empty or invalid", error=ValueError
    )


def _point(value: object) -> Point:
    row = _array(value)
    if len(row) != 3:
        raise ValueError("Mesh coordinate must have three components")
    values = [
        required(item, as_finite_number, message="Mesh coordinate must be finite", error=ValueError)
        for item in row
    ]
    return values[0], values[1], values[2]


def _face(value: object, vertex_count: int) -> Triangle:
    row = _array(value)
    if len(row) != 3:
        raise ValueError("Mesh face must be a triangle")
    indices = [
        required(item, as_int, message="Mesh face index must be an integer", error=ValueError)
        for item in row
    ]
    if any(index < 0 or index >= vertex_count for index in indices):
        raise ValueError("Mesh face index is out of range")
    return indices[0], indices[1], indices[2]


def _topology(points: list[Point], faces: list[Triangle]) -> None:
    edges: dict[tuple[int, int], list[tuple[int, int]]] = {}
    links: dict[int, dict[int, set[int]]] = {}
    for face in faces:
        a, b, c = [points[index] for index in face]
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        if (
            math.hypot(
                u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]
            )
            == 0
        ):
            raise ValueError("Zero-area triangle")
        for i, j in zip(face, face[1:] + face[:1], strict=True):
            edges.setdefault((min(i, j), max(i, j)), []).append((i, j))
        for index, vertex in enumerate(face):
            first, second = face[(index + 1) % 3], face[(index + 2) % 3]
            graph = links.setdefault(vertex, {})
            graph.setdefault(first, set()).add(second)
            graph.setdefault(second, set()).add(first)
    if any(len(pair) != 2 or pair[0] != pair[1][::-1] for pair in edges.values()):
        raise ValueError("Open, nonmanifold or inconsistently oriented edge")
    if len(links) != len(points):
        raise ValueError("Unused mesh vertices")
    for graph in links.values():
        if any(len(neighbors) != 2 for neighbors in graph.values()):
            raise ValueError("Nonmanifold vertex link")
        remaining = set(graph)
        pending = [remaining.pop()]
        while pending:
            neighbors = graph[pending.pop()] & remaining
            remaining -= neighbors
            pending.extend(neighbors)
        if remaining:
            raise ValueError("Disconnected vertex link")


def parse_closed_surface(mesh: Mapping[str, object]) -> tuple[list[Point], list[Triangle]]:
    """Parse the soup and reject malformed, open, pinched or degenerate topology."""
    points = [_point(value) for value in _array(mesh.get("vertices"))]
    faces = [_face(value, len(points)) for value in _array(mesh.get("faces"))]
    _topology(points, faces)
    return points, faces


def require_triangle_surface(mesh: Mapping[str, object]) -> dict[str, int]:
    """Reject malformed, open, pinched or self-intersecting triangle surfaces.

    Multiple disjoint shells are permitted. This does not certify solid nesting,
    dimensions, assembly clearance, load capacity or print settings.
    """
    points, faces = parse_closed_surface(mesh)
    if cgal_self_intersects(points, faces):
        raise SelfIntersectionError("Self-intersecting triangle surface")
    return {"vertices": len(points), "triangles": len(faces)}


def cgal_self_intersects(points: list[Point], faces: list[Triangle]) -> bool:
    """Convert the soup to a CGAL polyhedron (round-trip checked) and test self-intersection.

    Independent of closedness: an open surface still gets a real answer. Raises
    ValueError when the conversion changes the face count or triangle coordinates.
    CGAL counts degenerate (zero-area) faces as self-intersecting; such a mesh still fails
    through ``error`` (``parse_closed_surface`` rejects degenerate faces), not only here.
    """
    return bool(does_self_intersect(_cgal_polyhedron(points, faces)))


def _cgal_polyhedron(points: list[Point], faces: list[Triangle]) -> Polyhedron_3:
    """Preserve the complete input surface at the independent solver boundary."""
    converted = Polyhedron_3()
    polygon_soup_to_polygon_mesh([Point_3(*point) for point in points], faces, converted)
    if converted.size_of_facets() != len(faces):
        raise ValueError("CGAL conversion changed the face count")
    actual: Counter[tuple[Point, ...]] = Counter()
    for facet in converted.facets():
        edge = facet.halfedge()
        coordinates: list[Point] = []
        for _ in range(3):
            point = edge.vertex().point()
            coordinates.append((float(point.x()), float(point.y()), float(point.z())))
            edge = edge.next()
        actual[tuple(sorted(coordinates))] += 1
    expected = Counter(tuple(sorted(points[index] for index in face)) for face in faces)
    if actual != expected:
        raise ValueError("CGAL conversion changed triangle coordinates")
    return converted


def bounded_sides(mesh: Mapping[str, object], queries: object) -> tuple[int, ...]:
    """Classify finite points as material (1), boundary (0), or exterior/cavity (-1).

    Coordinates share the target surface's units and frame. Invalid surfaces fail
    before querying; no welding, tolerance offset, or automatic repair is applied.
    """
    points, faces = parse_closed_surface(mesh)
    query_points = [_point(value) for value in _array(queries)]
    converted = _cgal_polyhedron(points, faces)
    if does_self_intersect(converted):
        raise SelfIntersectionError("Self-intersecting triangle surface")
    classifier = Side_of_triangle_mesh(converted)
    return tuple(int(classifier.bounded_side(Point_3(*point))) for point in query_points)
