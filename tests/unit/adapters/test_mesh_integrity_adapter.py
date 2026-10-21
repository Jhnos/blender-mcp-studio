"""Host-side STL integrity: closed, non-self-intersecting surfaces without Blender."""

from pathlib import Path

import pytest
import trimesh

import src.adapters.mesh.trimesh_cgal_integrity as adapter_module
from src.adapters.mesh.trimesh_cgal_integrity import TrimeshCgalIntegrity
from src.verification.mesh_integrity import SelfIntersectionError, require_triangle_surface


def _export(mesh: trimesh.Trimesh, path: Path) -> str:
    mesh.export(path)
    return str(path)


async def test_closed_box_passes(tmp_path: Path) -> None:
    path = _export(trimesh.creation.box(extents=(1, 1, 1)), tmp_path / "box.stl")
    report = await TrimeshCgalIntegrity().check((path,))
    verdict = report.verdicts[0]
    assert verdict.watertight is True
    assert verdict.self_intersecting is False
    assert verdict.error is None
    assert verdict.triangles == 12
    assert verdict.passed is True
    assert report.passed is True


async def test_open_box_fails_watertight(tmp_path: Path) -> None:
    box = trimesh.creation.box(extents=(1, 1, 1))
    box.update_faces([i != 0 for i in range(len(box.faces))])
    path = _export(box, tmp_path / "open.stl")
    report = await TrimeshCgalIntegrity().check((path,))
    assert report.verdicts[0].watertight is False
    assert report.verdicts[0].passed is False
    assert report.passed is False


async def test_integrity_reports_unreadable_stl(tmp_path: Path) -> None:
    bad = tmp_path / "ascii.stl"
    bad.write_bytes(b"solid x" + bytes([10]))
    good = _export(trimesh.creation.box(extents=(1, 1, 1)), tmp_path / "box.stl")
    report = await TrimeshCgalIntegrity().check((str(bad), good))
    assert report.verdicts[0].error is not None
    assert str(bad) in report.verdicts[0].error
    assert report.verdicts[0].passed is False
    assert report.verdicts[1].passed is True
    assert report.passed is False


async def test_self_intersecting_pair_is_reported(tmp_path: Path) -> None:
    first = trimesh.creation.box(extents=(1, 1, 1))
    second = trimesh.creation.box(extents=(1, 1, 1))
    second.apply_translation((0.3, 0.3, 0.3))
    merged = trimesh.util.concatenate([first, second])
    path = _export(merged, tmp_path / "pair.stl")
    report = await TrimeshCgalIntegrity().check((path,))
    verdict = report.verdicts[0]
    assert verdict.self_intersecting is True
    assert verdict.passed is False
    assert report.passed is False


def _pair() -> trimesh.Trimesh:
    first = trimesh.creation.box(extents=(1, 1, 1))
    second = trimesh.creation.box(extents=(1, 1, 1))
    second.apply_translation((0.3, 0.3, 0.3))
    return trimesh.util.concatenate([first, second])


def test_guard_raises_typed_self_intersection() -> None:
    mesh = _pair()
    soup = {"vertices": mesh.vertices.tolist(), "faces": mesh.faces.tolist()}
    with pytest.raises(SelfIntersectionError):
        require_triangle_surface(soup)
    with pytest.raises(ValueError, match="Self-intersecting"):
        require_triangle_surface(soup)


async def test_open_self_intersecting_mesh_reports_both(tmp_path: Path) -> None:
    mesh = _pair()
    mesh.update_faces([i != 0 for i in range(len(mesh.faces))])
    report = await TrimeshCgalIntegrity().check((_export(mesh, tmp_path / "p.stl"),))
    assert report.verdicts[0].watertight is False
    assert report.verdicts[0].self_intersecting is True


async def test_self_intersection_not_evaluated_is_none_and_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(points: object, faces: object) -> bool:
        raise ValueError("CGAL conversion changed the face count")

    monkeypatch.setattr(adapter_module, "cgal_self_intersects", boom)
    path = _export(trimesh.creation.box(extents=(1, 1, 1)), tmp_path / "box.stl")
    verdict = (await TrimeshCgalIntegrity().check((path,))).verdicts[0]
    assert verdict.self_intersecting is None
    assert verdict.passed is False


async def test_open_mesh_error_names_reason(tmp_path: Path) -> None:
    box = trimesh.creation.box(extents=(1, 1, 1))
    box.update_faces([i != 0 for i in range(len(box.faces))])
    path = _export(box, tmp_path / "o.stl")
    verdict = (await TrimeshCgalIntegrity().check((path,))).verdicts[0]
    assert verdict.error is not None
    assert "Open, nonmanifold or inconsistently oriented edge" in verdict.error
    assert path in verdict.error


async def test_missing_file_is_named(tmp_path: Path) -> None:
    missing = str(tmp_path / "nope.stl")
    verdict = (await TrimeshCgalIntegrity().check((missing,))).verdicts[0]
    assert verdict.error == f"{missing}: file not found"


async def test_unexpected_error_propagates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object, **kwargs: object) -> object:
        raise AttributeError("programming error")

    monkeypatch.setattr(trimesh, "load", broken)
    path = _export(trimesh.creation.box(extents=(1, 1, 1)), tmp_path / "box.stl")
    with pytest.raises(AttributeError):
        await TrimeshCgalIntegrity().check((path,))
