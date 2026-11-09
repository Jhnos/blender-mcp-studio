"""Existing indexed teeth share one surface, including the periodic seam."""

from math import cos, pi, sin

import pytest

from src.core.domain.lab_station_joints import SerratedJointSpec
from src.core.planning.serrated_contact_plan import plan_contact_triangulation


def _fixture(reverse: bool = False):
    spec = SerratedJointSpec(teeth=4)
    count = spec.teeth * 8
    vertices = [
        (spec.profile(q * 360 / count), r * cos(q * 2 * pi / count), r * sin(q * 2 * pi / count))
        for r in (spec.tooth_inner_radius_mm, spec.radius_mm)
        for q in range(count)
    ]
    faces = [(0, count, count + 1), (0, count + 1, 1)]
    for q in range(1, count):
        a, b, c, d = q, count + q, count + (q + 1) % count, (q + 1) % count
        faces.extend(((a, b, d), (b, c, d)))
    if reverse:
        faces = [tuple(reversed(f)) for f in faces]
    vertices.extend(((20, 0, 0), (21, 0, 0), (20, 1, 0)))
    faces.insert(7, (count * 2, count * 2 + 1, count * 2 + 2))
    return spec, vertices, faces


def _plan(vertices, faces, spec):
    return plan_contact_triangulation(vertices, faces, spec, axial_bounds_mm=(-0.1, 1.3))


def test_same_diagonal_replaces_only_contact_faces_and_is_idempotent() -> None:
    spec, vertices, faces = _fixture()
    original = vertices.copy(), faces.copy()
    plan = _plan(vertices, faces, spec)
    assert (vertices, faces) == original
    assert len(plan.face_indices) == 64
    assert len(plan.faces) == len(faces)
    assert plan.faces[7] == faces[7]
    assert plan.faces != tuple(faces)
    for q in range(32):
        canonical = {(q, 32 + q, 32 + (q + 1) % 32), (q, 32 + (q + 1) % 32, (q + 1) % 32)}
        assert canonical.issubset(plan.faces)
    assert _plan(vertices, plan.faces, spec) == plan


def test_opposite_winding_uses_the_same_unoriented_triangles() -> None:
    spec, vertices, faces = _fixture()
    opposite = _fixture(True)[2]
    one, two = _plan(vertices, faces, spec), _plan(vertices, opposite, spec)
    assert one.outward_x_sign == 1 and two.outward_x_sign == -1
    assert {frozenset(one.faces[i]) for i in one.face_indices} == {
        frozenset(two.faces[i]) for i in two.face_indices
    }


@pytest.mark.parametrize(
    "corruption", ["missing", "duplicate", "winding", "ambiguous", "off_grid", "nan", "index"]
)
def test_incomplete_or_ambiguous_source_is_rejected(corruption: str) -> None:
    spec, vertices, faces = _fixture()
    if corruption == "missing":
        faces.pop()
    elif corruption == "duplicate":
        faces[-1] = faces[-2]
    elif corruption == "winding":
        faces[-1] = tuple(reversed(faces[-1]))
    elif corruption == "ambiguous":
        vertices.append(vertices[0])
        faces[0] = (len(vertices) - 1, *faces[0][1:])
    elif corruption == "off_grid":
        x, y, z = vertices[0]
        vertices[0] = (x, y + 0.01, z)
    elif corruption == "nan":
        vertices[0] = (float("nan"), 6, 0)
    else:
        faces[0] = (True, 32, 33)
    with pytest.raises(ValueError):
        _plan(vertices, faces, spec)


@pytest.mark.parametrize(
    "bounds,tolerance",
    [
        ((1, -1), 0.001),
        ((0, float("inf")), 0.001),
        ((0, 2), 0),
        ((0, 2), float("nan")),
        ((0, 2), 1),
    ],
)
def test_invalid_registration_limits_are_rejected(bounds, tolerance) -> None:
    spec, vertices, faces = _fixture()
    with pytest.raises(ValueError):
        plan_contact_triangulation(
            vertices, faces, spec, axial_bounds_mm=bounds, registration_mm=tolerance
        )
