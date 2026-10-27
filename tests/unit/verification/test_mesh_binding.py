"""A shared bounding box cannot establish original plate geometry identity."""

from copy import deepcopy

import pytest

from src.verification.mesh_binding import bind_axis_frame

POINTS = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 3.0, 0.0), (0.0, 0.0, 5.0)]
FACES = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


def source():
    return {"vertices": POINTS, "faces": FACES}


def target():
    return {"vertices": [(10 - z, 20 + y, 30 + x) for x, y, z in POINTS], "faces": FACES}


def test_binding_preserves_oriented_triangles_under_axis_rotation_and_translation():
    result = bind_axis_frame(source(), target())
    assert result.rotation == ((0, 0, -1), (0, 1, 0), (1, 0, 0))
    assert result.translation_mm == (10, 20, 30)
    assert result.maximum_error_mm == 0
    assert result.transform(POINTS) == target()["vertices"]


def test_cyclic_face_order_is_equivalent():
    original = source()
    other = target()
    other["faces"] = [(b, c, a) for a, b, c in reversed(FACES)]
    assert bind_axis_frame(original, other).maximum_error_mm == 0


@pytest.mark.parametrize(
    "fault",
    ["face-change", "reversed-winding", "scale", "reflection", "nonfinite", "empty", "unused"],
)
def test_rejects_surface_mismatch_even_with_unchanged_extent(fault):
    other = deepcopy(target())
    if fault == "face-change":
        other["faces"] = [*FACES[:-1], FACES[0]]
    elif fault == "reversed-winding":
        other["faces"] = [(a, c, b) for a, b, c in FACES]
    elif fault == "scale":
        other["vertices"] = [(x * 2, y, z) for x, y, z in other["vertices"]]
    elif fault == "reflection":
        other["vertices"] = [(-x, y, z) for x, y, z in other["vertices"]]
    elif fault == "nonfinite":
        other["vertices"][0] = (float("nan"), 20, 30)
    elif fault == "empty":
        other["faces"] = []
    elif fault == "unused":
        other["vertices"].append((11, 21, 31))
    with pytest.raises(ValueError):
        bind_axis_frame(source(), other)


def test_symmetry_is_rejected_instead_of_selecting_an_arbitrary_rotation():
    import trimesh

    box = trimesh.creation.box()
    mesh = {"vertices": box.vertices.tolist(), "faces": box.faces.tolist()}
    with pytest.raises(ValueError, match="unique"):
        bind_axis_frame(mesh, mesh)


def test_rounding_tolerance_is_bounded_and_geometry_is_unchanged():
    first, other = deepcopy(source()), deepcopy(target())
    other["vertices"][1] = (10.000001, 20, 32)
    before = deepcopy(other)
    result = bind_axis_frame(first, other)
    assert result.maximum_error_mm < 0.00001
    assert other == before and first == source()
    other["vertices"][1] = (10.001, 20, 32)
    with pytest.raises(ValueError):
        bind_axis_frame(first, other)


def test_same_frame_surface_guard_rejects_repositioning_and_preserves_rounding_budget():
    from src.verification.mesh_binding import require_same_oriented_surface

    assert require_same_oriented_surface(source(), source()) == 0
    with pytest.raises(ValueError):
        require_same_oriented_surface(source(), target())
    shifted = deepcopy(source())
    shifted["vertices"] = [(x + 0.000001, y, z) for x, y, z in POINTS]
    assert require_same_oriented_surface(source(), shifted) < 0.00001
