"""ManifestPackager: reproducible manifest of a run's delivered files."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
import trimesh

from src.adapters.packaging.manifest_packager import ManifestPackager
from src.core.domain.packaging import ToolUse


def _stl(path: Path) -> None:
    trimesh.creation.box().export(str(path))


async def _package(run_dir: Path, files: tuple[str, ...]):
    return await ManifestPackager().package("run1", "spec", str(run_dir), files)


@pytest.mark.asyncio
async def test_manifest_lists_every_file_with_sha256_and_triangles(tmp_path: Path) -> None:
    _stl(tmp_path / "part.stl")
    (tmp_path / "report.json").write_text('{"ok": true}')
    manifest = await _package(tmp_path, (str(tmp_path / "report.json"), str(tmp_path / "part.stl")))
    by_path = {f.path: f for f in manifest.files}
    assert list(by_path) == ["part.stl", "report.json"]
    stl = by_path["part.stl"]
    assert stl.sha256 == hashlib.sha256((tmp_path / "part.stl").read_bytes()).hexdigest()
    assert stl.bytes == (tmp_path / "part.stl").stat().st_size
    assert stl.triangles == 12
    assert by_path["report.json"].triangles is None
    assert manifest.manifest_path == str(tmp_path / "manifest.json")
    data = json.loads((tmp_path / "manifest.json").read_text())
    assert data["run_id"] == "run1" and data["spec_name"] == "spec"
    assert [f["path"] for f in data["files"]] == ["part.stl", "report.json"]


@pytest.mark.asyncio
async def test_manifest_rejects_file_outside_run_dir(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    outside = tmp_path / "outside.stl"
    _stl(outside)
    with pytest.raises(ValueError, match="outside.stl"):
        await _package(run_dir, (str(outside),))


@pytest.mark.asyncio
async def test_manifest_rejects_symlink_escaping_run_dir(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    outside = tmp_path / "secret.stl"
    _stl(outside)
    link = run_dir / "link.stl"
    os.symlink(outside, link)
    with pytest.raises(ValueError, match="link.stl"):
        await _package(run_dir, (str(link),))


@pytest.mark.asyncio
async def test_manifest_is_byte_stable_for_same_inputs(tmp_path: Path) -> None:
    _stl(tmp_path / "a.stl")
    (tmp_path / "b.txt").write_text("hello")
    files = (str(tmp_path / "b.txt"), str(tmp_path / "a.stl"))
    await _package(tmp_path, files)
    first = (tmp_path / "manifest.json").read_bytes()
    await _package(tmp_path, tuple(reversed(files)))
    assert (tmp_path / "manifest.json").read_bytes() == first
    assert first.endswith(b"\n")
    assert str(tmp_path).encode() not in first


@pytest.mark.asyncio
async def test_manifest_excludes_itself_and_duplicates(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("hello")
    await _package(tmp_path, (str(tmp_path / "b.txt"),))
    manifest = await _package(
        tmp_path,
        (
            str(tmp_path / "b.txt"),
            str(tmp_path / "b.txt"),
            str(tmp_path / "manifest.json"),
            "./manifest.json",
            "manifest.json.tmp",
        ),
    )
    assert [f.path for f in manifest.files] == ["b.txt"]


@pytest.mark.asyncio
async def test_relative_input_resolves_against_run_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _stl(run_dir / "out.stl")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    manifest = await _package(run_dir, ("out.stl",))
    assert [f.path for f in manifest.files] == ["out.stl"]


@pytest.mark.asyncio
async def test_manifest_write_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "b.txt").write_text("hello")
    await _package(tmp_path, (str(tmp_path / "b.txt"),))
    assert not (tmp_path / "manifest.json.tmp").exists()
    before = (tmp_path / "manifest.json").read_bytes()
    (tmp_path / "c.txt").write_text("more")

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="replace failed"):
        await _package(tmp_path, (str(tmp_path / "b.txt"), str(tmp_path / "c.txt")))
    assert (tmp_path / "manifest.json").read_bytes() == before


@pytest.mark.asyncio
async def test_manifest_records_tool_licenses(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("hello")
    tools = (
        ToolUse("trimesh", "5.1.1", "MIT", "library"),
        ToolUse("Bambu Studio", "2.x", "AGPL-3.0-only", "subprocess"),
    )
    manifest = await ManifestPackager().package(
        "run1", "spec", str(tmp_path), (str(tmp_path / "b.txt"),), tools=tools
    )
    data = json.loads((tmp_path / "manifest.json").read_text())
    assert data["tools"] == [
        {
            "name": "Bambu Studio",
            "version": "2.x",
            "license": "AGPL-3.0-only",
            "invocation": "subprocess",
        },
        {"name": "trimesh", "version": "5.1.1", "license": "MIT", "invocation": "library"},
    ]
    assert manifest.tools == tuple(reversed(tools))


@pytest.mark.asyncio
async def test_missing_run_dir_is_named(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(ValueError, match="nope.*run directory not found"):
        await _package(missing, ())


@pytest.mark.asyncio
async def test_unloadable_stl_raises(tmp_path: Path) -> None:
    (tmp_path / "bad.STL").write_bytes(b"not an stl")
    with pytest.raises(ValueError, match="bad.STL"):
        await _package(tmp_path, (str(tmp_path / "bad.STL"),))
