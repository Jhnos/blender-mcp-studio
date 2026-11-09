"""Engine-independent checks for generated manufacturing files."""

import math
import struct
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BinaryStlMetrics:
    triangle_count: int
    dimensions_mm: tuple[float, float, float]


StlPoint = tuple[float, float, float]


def _binary_stl_triangles(payload: bytes) -> Iterator[tuple[StlPoint, StlPoint, StlPoint]]:
    if len(payload) < 84:
        raise ValueError("STL header is incomplete")
    count = int(struct.unpack_from("<I", payload, 80)[0])
    if count <= 0 or len(payload) != 84 + 50 * count:
        raise ValueError("STL triangle count does not match a non-empty payload")
    for record in struct.iter_unpack("<12fH", payload[84:]):
        points: list[StlPoint] = [
            (float(record[3 + 3 * i]), float(record[4 + 3 * i]), float(record[5 + 3 * i]))
            for i in range(3)
        ]
        if any(not math.isfinite(value) for point in points for value in point):
            raise ValueError("STL contains a non-finite coordinate")
        yield points[0], points[1], points[2]


def binary_stl_metrics(payload: bytes) -> BinaryStlMetrics:
    """Read binary STL coordinates as millimetres under the project's export contract."""
    minima = [math.inf, math.inf, math.inf]
    maxima = [-math.inf, -math.inf, -math.inf]
    count = 0
    for triangle in _binary_stl_triangles(payload):
        count += 1
        for point in triangle:
            for axis, value in enumerate(point):
                minima[axis] = min(minima[axis], value)
                maxima[axis] = max(maxima[axis], value)
    return BinaryStlMetrics(
        count, (maxima[0] - minima[0], maxima[1] - minima[1], maxima[2] - minima[2])
    )


def binary_stl_surface(payload: bytes) -> dict[str, object]:
    """Index only exactly equal STL coordinates; never weld nearby points or repair faces."""
    vertices: list[StlPoint] = []
    faces: list[tuple[int, int, int]] = []
    indices: dict[StlPoint, int] = {}
    for triangle in _binary_stl_triangles(payload):
        face = []
        for point in triangle:
            if point not in indices:
                indices[point] = len(vertices)
                vertices.append(point)
            face.append(indices[point])
        faces.append((face[0], face[1], face[2]))
    return {"vertices": vertices, "faces": faces}
