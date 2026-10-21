"""Shared STL loader: one place that decides what an unreadable STL is."""

from __future__ import annotations

from pathlib import Path

import pytest
import trimesh

from src.adapters.mesh.stl_loader import load_stl


def test_load_stl_returns_mesh(tmp_path: Path) -> None:
    trimesh.creation.box().export(str(tmp_path / "a.stl"))
    assert len(load_stl(tmp_path / "a.stl").faces) == 12


def test_load_stl_rejects_zero_faces_without_path_prefix(tmp_path: Path) -> None:
    (tmp_path / "bad.stl").write_bytes(b"not an stl")
    with pytest.raises(ValueError, match="no triangles") as info:
        load_stl(tmp_path / "bad.stl")
    assert "bad.stl" not in str(info.value)


def test_load_stl_missing_file_is_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot read STL"):
        load_stl(tmp_path / "missing.stl")
