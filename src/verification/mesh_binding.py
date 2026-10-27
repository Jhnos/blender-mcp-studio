"""Prove a unique axis frame by complete oriented triangle identity, without repair.

Inputs must already use exact shared vertex indices (binary_stl_surface provides
those for STL). This is a frame identity check, not a fit or collision certificate.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.verification.mesh_integrity import Point, Triangle, parse_closed_surface

_TOLERANCE_MM = 0.00001


@dataclass(frozen=True, slots=True)
class MeshFrameBinding:
    rotation: tuple[tuple[int, int, int], ...]
    translation_mm: Point
    maximum_error_mm: float

    def transform(self, points: Sequence[Point]) -> list[Point]:
        result = []
        for point in points:
            values = [
                sum(row[j] * point[j] for j in range(3)) + shift
                for row, shift in zip(self.rotation, self.translation_mm, strict=True)
            ]
            result.append((values[0], values[1], values[2]))
        return result


def _rotations() -> list[tuple[tuple[int, int, int], ...]]:
    result: list[tuple[tuple[int, int, int], ...]] = []
    for perm in itertools.permutations(range(3)):
        parity = (-1) ** sum(perm[i] > perm[j] for i in range(3) for j in range(i + 1, 3))
        for signs in itertools.product((-1, 1), repeat=3):
            if parity * math.prod(signs) == 1:
                rows = [tuple(signs[i] if j == perm[i] else 0 for j in range(3)) for i in range(3)]
                result.append(tuple((row[0], row[1], row[2]) for row in rows))
    return result


def _oriented(faces: Sequence[Triangle]) -> Counter[Triangle]:
    return Counter(min(face, face[1:] + face[:1], face[2:] + face[:2]) for face in faces)


def _cell(point: Point) -> tuple[int, int, int]:
    values = [math.floor(v / _TOLERANCE_MM) for v in point]
    return values[0], values[1], values[2]


def _match(source: list[Point], target: list[Point]) -> tuple[list[int], float] | None:
    grid: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for index, point in enumerate(target):
        grid[_cell(point)].append(index)
    indices, maximum = [], 0.0
    for point in source:
        cell = _cell(point)
        candidates: list[tuple[float, int]] = []
        for offset in itertools.product((-1, 0, 1), repeat=3):
            key = (cell[0] + offset[0], cell[1] + offset[1], cell[2] + offset[2])
            candidates.extend((math.dist(point, target[i]), i) for i in grid.get(key, ()))
        candidates.sort()
        if not candidates or candidates[0][0] > _TOLERANCE_MM:
            return None
        if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
            return None
        distance, index = candidates[0]
        indices.append(index)
        maximum = max(maximum, distance)
    if len(set(indices)) != len(target) or len(source) != len(target):
        return None
    return indices, maximum


def bind_axis_frame(
    original: Mapping[str, object], placed: Mapping[str, object]
) -> MeshFrameBinding:
    """Reject ambiguity, reflections, scaling, missing faces and altered winding."""
    points, faces = parse_closed_surface(original)
    target, target_faces = parse_closed_surface(placed)
    expected = _oriented(target_faces)
    matches = []
    for rotation in _rotations():
        unshifted = MeshFrameBinding(rotation, (0, 0, 0), 0).transform(points)
        shift = tuple(min(p[i] for p in target) - min(p[i] for p in unshifted) for i in range(3))
        binding = MeshFrameBinding(rotation, (shift[0], shift[1], shift[2]), 0)
        mapped = binding.transform(points)
        if any(
            abs(max(p[i] for p in mapped) - max(p[i] for p in target)) > _TOLERANCE_MM
            for i in range(3)
        ):
            continue
        result = _match(mapped, target)
        if result is None:
            continue
        indices, maximum = result
        actual = [(indices[a], indices[b], indices[c]) for a, b, c in faces]
        if _oriented(actual) == expected:
            matches.append(MeshFrameBinding(rotation, binding.translation_mm, maximum))
    if len(matches) != 1:
        raise ValueError("mesh requires one unique oriented axis frame binding")
    return matches[0]


def require_same_oriented_surface(
    original: Mapping[str, object], actual: Mapping[str, object]
) -> float:
    """Compare complete surfaces in one existing frame, without fitting or repositioning."""
    points, faces = parse_closed_surface(original)
    target, target_faces = parse_closed_surface(actual)
    result = _match(points, target)
    if result is None:
        raise ValueError("surface coordinates differ in their existing frame")
    indices, maximum = result
    mapped = [(indices[a], indices[b], indices[c]) for a, b, c in faces]
    if _oriented(mapped) != _oriented(target_faces):
        raise ValueError("surface oriented triangles differ")
    return maximum
