"""Host-side STL integrity: closed, non-self-intersecting surfaces without Blender."""

from pathlib import Path

import trimesh

from src.adapters.mesh.trimesh_cgal_integrity import TrimeshCgalIntegrity


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
