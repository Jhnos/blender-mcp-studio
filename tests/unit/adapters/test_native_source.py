"""Selected, checksum-bound native provenance; no Blender process involved."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from src.adapters.artifacts.native_source import FilesystemNativeSource
from src.core.domain.import_limits import ImportLimits
from src.core.domain.model_spec import ImportedArtifact, ModelSpec
from src.core.domain.native_revision import NativeSourceError


def fixture(tmp_path: Path):
    root = tmp_path / "models" / "selected"
    root.mkdir(parents=True)
    files = {
        "native.blend": b"opaque-native",
        "STL/列印零件/a.stl": b"a",
        "STL/列印零件/b.stl": b"b",
        "plate.3mf": b"plate",
        "README.md": b"notes",
    }
    for name, data in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    manifest = {n: hashlib.sha256(v).hexdigest() for n, v in files.items()}
    (root / "SHA256.json").write_text(json.dumps(manifest))
    spec = ModelSpec(
        "1", "selected", ImportedArtifact(str(root), "STL/列印零件/*.stl", "plate.3mf")
    )
    limits = ImportLimits(10, 1000, 1000, 2000)
    return root, manifest, spec, FilesystemNativeSource((tmp_path,), limits)


async def test_current_native_and_printed_identities_are_typed_relative_and_verified(tmp_path):
    root, manifest, spec, reader = fixture(tmp_path)
    (root / "old-unlisted.blend").write_bytes(b"history")
    source = await reader.resolve(spec)
    assert source.model_name == "selected" and source.root_dir == "models/selected"
    assert source.native.path == "native.blend" and source.native.sha256 == manifest["native.blend"]
    assert [p.path for p in source.parts] == ["STL/列印零件/a.stl", "STL/列印零件/b.stl"]
    assert source.project_3mf.path == "plate.3mf" and source.verified_files == 5
    assert source.manifest_sha256 == hashlib.sha256((root / "SHA256.json").read_bytes()).hexdigest()
    assert str(tmp_path) not in repr(source)
    with pytest.raises(FrozenInstanceError):
        source.model_name = "other"


@pytest.mark.parametrize(
    "damage",
    [
        "native",
        "part",
        "metadata",
        "missing",
        "unlisted_part",
        "missing_manifest",
        "duplicate_native",
        "empty_glob",
        "bad_sha",
        "nonstring_sha",
        "outside_path",
        "hidden_path",
        "backslash",
        "noncanonical",
        "symlink",
        "duplicate_key",
        "wrong_document",
        "absolute_path",
        "parent_symlink",
        "empty_native",
        "empty_part",
        "empty_project",
        "missing_native",
    ],
)
async def test_bad_source_is_rejected_without_fallback_or_host_path(tmp_path, damage):
    root, m, spec, reader = fixture(tmp_path)
    if damage == "native":
        (root / "native.blend").write_bytes(b"changed")
    elif damage == "part":
        (root / "STL/列印零件/a.stl").write_bytes(b"changed")
    elif damage == "metadata":
        (root / "README.md").write_bytes(b"changed")
    elif damage == "missing":
        (root / "STL/列印零件/a.stl").unlink()
    elif damage == "unlisted_part":
        (root / "STL/列印零件/extra.stl").write_bytes(b"extra")
    elif damage == "missing_manifest":
        (root / "SHA256.json").unlink()
    elif damage == "duplicate_native":
        (root / "second.blend").write_bytes(b"other")
        m["second.blend"] = hashlib.sha256(b"other").hexdigest()
    elif damage == "empty_glob":
        spec = replace(spec, source=replace(spec.source, stl_glob="none/*.stl"))
    elif damage == "bad_sha":
        m["native.blend"] = "not-a-digest"
    elif damage == "nonstring_sha":
        m["native.blend"] = 3
    elif damage == "outside_path":
        m["../escape.blend"] = hashlib.sha256(b"x").hexdigest()
    elif damage == "absolute_path":
        m[str(root / "native.blend")] = m["native.blend"]
    elif damage == "parent_symlink":
        (root / "alias").symlink_to(root / "STL", target_is_directory=True)
        m["alias/列印零件/a.stl"] = m["STL/列印零件/a.stl"]
    elif damage in ("empty_native", "empty_part", "empty_project"):
        name = {
            "empty_native": "native.blend",
            "empty_part": "STL/列印零件/a.stl",
            "empty_project": "plate.3mf",
        }[damage]
        (root / name).write_bytes(b"")
        m[name] = hashlib.sha256(b"").hexdigest()
    elif damage == "missing_native":
        del m["native.blend"]
    elif damage == "hidden_path":
        m[".hidden.blend"] = hashlib.sha256(b"x").hexdigest()
    elif damage == "backslash":
        m["bad\\name.blend"] = hashlib.sha256(b"x").hexdigest()
    elif damage == "noncanonical":
        m["STL//列印零件/a.stl"] = m["STL/列印零件/a.stl"]
    elif damage == "symlink":
        (root / "native.blend").unlink()
        (root / "native.blend").symlink_to(root / "README.md")
        m["native.blend"] = m["README.md"]
    if damage not in ("missing_manifest", "duplicate_key", "wrong_document"):
        (root / "SHA256.json").write_text(json.dumps(m))
    elif damage == "duplicate_key":
        (root / "SHA256.json").write_text(
            '{"native.blend":"'
            + m["native.blend"]
            + '","native.blend":"'
            + m["native.blend"]
            + '"}'
        )
    elif damage == "wrong_document":
        (root / "SHA256.json").write_text("[]")
    with pytest.raises(NativeSourceError) as error:
        await reader.resolve(spec)
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize(
    "limits",
    [
        ImportLimits(1, 1000, 1000, 2000),
        ImportLimits(10, 0, 1000, 2000),
        ImportLimits(10, 1000, 3, 2000),
        ImportLimits(10, 1000, 1000, 1),
    ],
)
async def test_source_honors_existing_import_caps(tmp_path, limits):
    root, m, spec, reader = fixture(tmp_path)
    reader = FilesystemNativeSource((tmp_path,), limits)
    with pytest.raises(NativeSourceError):
        await reader.resolve(spec)


async def test_outside_selected_root_is_rejected(tmp_path):
    root, m, spec, reader = fixture(tmp_path)
    reader = FilesystemNativeSource((tmp_path / "elsewhere",), ImportLimits(10, 1000, 1000, 2000))
    with pytest.raises(NativeSourceError):
        await reader.resolve(spec)


@pytest.mark.parametrize("kwargs", [{"max_source_bytes": 5}, {"max_manifest_bytes": 2}])
async def test_manifest_and_total_source_budgets_are_enforced(tmp_path, kwargs):
    root, m, spec, _ = fixture(tmp_path)
    reader = FilesystemNativeSource((tmp_path,), ImportLimits(10, 1000, 1000, 2000), **kwargs)
    with pytest.raises(NativeSourceError):
        await reader.resolve(spec)


async def test_file_changed_after_hash_read_is_rejected(tmp_path, monkeypatch):
    root, m, spec, reader = fixture(tmp_path)
    original = hashlib.file_digest

    def changing(handle, digest):
        result = original(handle, digest)
        if Path(handle.name).name == "native.blend":
            (root / "native.blend").write_bytes(b"changed-after-read")
        return result

    monkeypatch.setattr(hashlib, "file_digest", changing)
    with pytest.raises(NativeSourceError, match="changed during read"):
        await reader.resolve(spec)


async def test_symlink_loop_is_a_safe_source_error(tmp_path):
    root, manifest, spec, reader = fixture(tmp_path)
    (root / "native.blend").unlink()
    (root / "native.blend").symlink_to("native.blend")
    with pytest.raises(NativeSourceError) as error:
        await reader.resolve(spec)
    assert str(tmp_path) not in str(error.value)


async def test_looped_selected_directory_is_a_safe_source_error(tmp_path):
    root, manifest, spec, reader = fixture(tmp_path)
    loop = tmp_path / "loop"
    loop.symlink_to("loop", target_is_directory=True)
    spec = replace(spec, source=replace(spec.source, root_dir=str(loop)))
    with pytest.raises(NativeSourceError) as error:
        await reader.resolve(spec)
    assert str(tmp_path) not in str(error.value)


async def test_manifest_changed_while_assets_are_checked_is_rejected(tmp_path, monkeypatch):
    root, manifest, spec, reader = fixture(tmp_path)
    original = hashlib.file_digest

    def changing(handle, digest):
        result = original(handle, digest)
        if Path(handle.name).name == "native.blend":
            path = root / "SHA256.json"
            path.write_text(path.read_text() + "\n")
        return result

    monkeypatch.setattr(hashlib, "file_digest", changing)
    with pytest.raises(NativeSourceError, match="manifest changed"):
        await reader.resolve(spec)
