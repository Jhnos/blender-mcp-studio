"""Engine-independent checks for generated manufacturing files."""

import math
import struct
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BinaryStlMetrics:
    triangle_count: int
    dimensions_mm: tuple[float, float, float]


def binary_stl_metrics(payload: bytes) -> BinaryStlMetrics:
    """Read binary STL coordinates as millimetres under the project's export contract."""
    if len(payload) < 84:
        raise ValueError("STL header is incomplete")
    triangle_count = int(struct.unpack_from("<I", payload, 80)[0])
    if triangle_count <= 0 or len(payload) != 84 + 50 * triangle_count:
        raise ValueError("STL triangle count does not match a non-empty payload")
    minima = [math.inf, math.inf, math.inf]
    maxima = [-math.inf, -math.inf, -math.inf]
    for record in struct.iter_unpack("<12fH", payload[84:]):
        for vertex in range(3):
            for axis in range(3):
                value = float(record[3 + 3 * vertex + axis])
                if not math.isfinite(value):
                    raise ValueError("STL contains a non-finite coordinate")
                minima[axis] = min(minima[axis], value)
                maxima[axis] = max(maxima[axis], value)
    return BinaryStlMetrics(
        triangle_count,
        (maxima[0] - minima[0], maxima[1] - minima[1], maxima[2] - minima[2]),
    )
