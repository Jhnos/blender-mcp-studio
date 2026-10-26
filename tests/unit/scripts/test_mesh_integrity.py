"""Independent mesh integrity checks reject topology and surface defects."""

from copy import deepcopy

import pytest

from src.verification.mesh_integrity import require_triangle_surface


def tetrahedron(offset: float = 0) -> dict[str, object]:
    return {
        "vertices": [
            [x + offset, y + offset, z + offset]
            for x, y, z in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        ],
        "faces": [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]],
    }


def combined(offset: float) -> dict[str, object]:
    first, second = tetrahedron(), tetrahedron(offset)
    return {
        "vertices": first["vertices"] + second["vertices"],
        "faces": first["faces"] + [[i + 4 for i in face] for face in second["faces"]],
    }


def test_closed_tetrahedron_passes() -> None:
    assert require_triangle_surface(tetrahedron()) == {"vertices": 4, "triangles": 4}


def test_separate_shells_pass() -> None:
    assert require_triangle_surface(combined(2)) == {"vertices": 8, "triangles": 8}


def test_crossing_closed_shells_fail() -> None:
    with pytest.raises(ValueError, match="Self-intersecting"):
        require_triangle_surface(combined(0.2))


@pytest.mark.parametrize(
    "change, message",
    [
        ("open", "edge"),
        ("winding", "edge"),
        ("degenerate", "Zero-area"),
        ("nonfinite", "finite"),
        ("index", "index"),
        ("boolean_index", "index"),
        ("unused", "Unused"),
        ("empty", "empty"),
    ],
)
def test_invalid_input_fails(change: str, message: str) -> None:
    mesh = deepcopy(tetrahedron())
    if change == "open":
        mesh["faces"].pop()
    elif change == "winding":
        mesh["faces"][0].reverse()
    elif change == "degenerate":
        mesh["vertices"][1] = mesh["vertices"][0]
    elif change == "nonfinite":
        mesh["vertices"][0][0] = float("nan")
    elif change == "index":
        mesh["faces"][0][0] = 99
    elif change == "boolean_index":
        mesh["faces"][0][0] = False
    elif change == "unused":
        mesh["vertices"].append([2, 2, 2])
    else:
        mesh["faces"] = []
    with pytest.raises(ValueError, match=message):
        require_triangle_surface(mesh)


def test_pinched_vertex_fails_even_when_every_edge_has_two_faces() -> None:
    mesh = tetrahedron()
    mesh["vertices"] += [[-1, 0, 0], [0, -1, 0], [0, 0, -1]]
    mesh["faces"] += [[0, 4, 5], [0, 6, 4], [0, 5, 6], [4, 6, 5]]
    with pytest.raises(ValueError, match="vertex link"):
        require_triangle_surface(mesh)


def test_conversion_must_preserve_every_face(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.verification.mesh_integrity as subject

    original = subject.polygon_soup_to_polygon_mesh

    def lose_face(points, faces, mesh):
        original(points, faces[:-1], mesh)

    monkeypatch.setattr(subject, "polygon_soup_to_polygon_mesh", lose_face)
    with pytest.raises(ValueError, match="face count"):
        require_triangle_surface(tetrahedron())


def test_conversion_must_preserve_triangle_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.verification.mesh_integrity as subject

    original = subject.polygon_soup_to_polygon_mesh

    def shift_points(points, faces, mesh):
        original([subject.Point_3(p.x() + 0.125, p.y(), p.z()) for p in points], faces, mesh)

    monkeypatch.setattr(subject, "polygon_soup_to_polygon_mesh", shift_points)
    with pytest.raises(ValueError, match="triangle coordinates"):
        require_triangle_surface(tetrahedron())


def test_bounded_sides_distinguishes_material_boundary_and_exterior() -> None:
    from src.verification.mesh_integrity import bounded_sides

    points = [[0.1, 0.1, 0.1], [0, 0, 0], [0.5, 0.5, 0], [2, 2, 2]]
    assert bounded_sides(tetrahedron(), points) == (1, 0, 0, -1)
    assert bounded_sides(combined(2), [[2.1, 2.1, 2.1], [1.5, 1.5, 1.5]]) == (1, -1)


def test_bounded_sides_respects_a_closed_internal_cavity() -> None:
    from src.verification.mesh_integrity import bounded_sides

    outer, inner = tetrahedron(), tetrahedron()
    mesh = {
        "vertices": outer["vertices"] + [[0.1 + v * 0.3 for v in p] for p in inner["vertices"]],
        "faces": outer["faces"] + [[i + 4 for i in reversed(f)] for f in inner["faces"]],
    }
    assert bounded_sides(mesh, [[0.15, 0.15, 0.15], [0.6, 0.1, 0.1]]) == (-1, 1)


@pytest.mark.parametrize("points", [[], [[float("nan"), 0, 0]], [[0, 0]]])
def test_bounded_sides_rejects_missing_or_invalid_queries(points) -> None:
    from src.verification.mesh_integrity import bounded_sides

    with pytest.raises(ValueError):
        bounded_sides(tetrahedron(), points)


def test_bounded_sides_rejects_invalid_target_before_classifying() -> None:
    from src.verification.mesh_integrity import bounded_sides

    with pytest.raises(ValueError, match="Self-intersecting"):
        bounded_sides(combined(0.2), [[0, 0, 0]])
    mesh = tetrahedron()
    mesh["faces"].pop()
    with pytest.raises(ValueError, match="edge"):
        bounded_sides(mesh, [[0, 0, 0]])
