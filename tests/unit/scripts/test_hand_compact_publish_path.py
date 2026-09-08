"""Publishing the human-scale instance is proven before the user is asked to run it.

The compact hand ships five meshes — two phalanx part numbers — where every
earlier package shipped four. This drives the publisher with synthetic files
for that package into a scratch directory, so the one command the user runs
after accepting the renders cannot be the first time the path is exercised.
"""

import json
import struct
from pathlib import Path

import pytest

from scripts.publish_print_package import PACKAGES, publish


def _stl(triangles: int) -> bytes:
    header = b"\0" * 80 + struct.pack("<I", triangles)
    face = struct.pack("<12fH", 0, 0, 0, 0, 0, 0, 10, 10, 10, 0, 0, 0, 0)
    return header + face * triangles


def _seed(source: Path) -> None:
    package = PACKAGES["hand-compact"]
    for index, name in enumerate(package.stl_files, start=1):
        (source / name).write_bytes(_stl(index))
    (source / package.blend_file).write_bytes(b"BLENDER" + b"\0" * 64)
    for name in package.render_files:
        (source / name).write_bytes(b"\x89PNG" + b"\0" * 16)


def test_the_compact_package_publishes_with_one_manifest_entry_per_file(tmp_path: Path) -> None:
    source, destination = tmp_path / "src", tmp_path / "dst"
    source.mkdir()
    _seed(source)
    package = PACKAGES["hand-compact"]

    publish(source, destination, package)

    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["model_revision"] == package.revision
    assert manifest["source_generator"] == "scripts/model_hand_compact.py"
    assert set(manifest["files"]) == {*package.stl_files, package.blend_file, *package.render_files}
    assert len(package.stl_files) == 5, "two phalanx part numbers, a palm, a finger, a hand"
    for index, name in enumerate(package.stl_files, start=1):
        assert manifest["files"][name]["triangle_count"] == index
    assert set(manifest["verification_contracts"]) == set(package.contracts)


def test_a_missing_render_refuses_to_publish(tmp_path: Path) -> None:
    source, destination = tmp_path / "src", tmp_path / "dst"
    source.mkdir()
    _seed(source)
    (source / PACKAGES["hand-compact"].layout_render).unlink()

    with pytest.raises(FileNotFoundError, match="missing"):
        publish(source, destination, PACKAGES["hand-compact"])
