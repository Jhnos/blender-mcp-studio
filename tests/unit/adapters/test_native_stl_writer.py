"""Complete same-identity STL sets precede any derived 3MF."""

import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import trimesh

from src.adapters.artifacts.native_stl_writer import NativeStlWriter
from src.adapters.mesh.trimesh_cgal_integrity import TrimeshCgalIntegrity
from src.core.domain.import_limits import ImportLimits
from src.core.domain.mesh_integrity import MeshIntegrityReport
from src.core.domain.native_revision import NativeModelSource, NativeRevisionError, SourceArtifact


def setup(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    mesh = trimesh.creation.box((10, 8, 6))
    payload = trimesh.exchange.stl.export_stl(mesh)
    parts = []
    for name in ("back", "lid", "arm"):
        path = "STL/列印零件/" + name + ".stl"
        target = snapshot / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        parts.append(SourceArtifact(path, hashlib.sha256(payload).hexdigest(), len(payload)))
    native = tmp_path / "candidate.blend"
    native.write_bytes(b"already validated by native runner")
    native_receipt = SourceArtifact(
        "candidate.blend", hashlib.sha256(native.read_bytes()).hexdigest(), native.stat().st_size
    )
    source = NativeModelSource(
        "selected", "models/selected", native_receipt, tuple(parts), None, "0" * 64, 4, 100000
    )
    changed = trimesh.creation.box((9, 8, 6))
    surfaces = {
        name: {"vertices": changed.vertices.tolist(), "faces": changed.faces.tolist()}
        for name in ("back", "lid")
    }
    writer = NativeStlWriter(TrimeshCgalIntegrity(), ImportLimits(10, 100000, 100000, 100000))
    return writer, source, snapshot, native, native_receipt, surfaces, tmp_path / "output"


async def test_complete_set_preserves_unchanged_bytes_and_records_native_lineage(tmp_path):
    writer, source, snapshot, native, receipt, surfaces, output = setup(tmp_path)
    result = await writer.write(
        source, snapshot, native, receipt, surfaces, ("back", "lid"), output
    )
    assert len(result.parts) == len(source.parts) == 3
    for part in source.parts:
        same = (snapshot / part.path).read_bytes() == (output / part.path).read_bytes()
        assert same == (Path(part.path).stem == "arm")
    assert result.changed_paths == tuple(p.path for p in source.parts if Path(p.path).stem != "arm")
    manifest = json.loads((output / "SHA256.json").read_text())
    assert set(manifest) == {receipt.path, "native-output.json", *(p.path for p in source.parts)}
    assert all(
        hashlib.sha256((output / name).read_bytes()).hexdigest() == sha
        for name, sha in manifest.items()
    )
    assert not list(output.rglob("*.3mf"))
    assert (
        json.loads((output / "native-output.json").read_text())["source"]["native"]["sha256"]
        == source.native.sha256
    )


@pytest.mark.parametrize(
    "fault",
    [
        "extra",
        "missing",
        "stale-source",
        "stale-native",
        "existing",
        "invalid-mesh",
        "empty-verdict",
    ],
)
async def test_failed_output_has_no_success_manifest_and_never_changes_inputs(tmp_path, fault):
    writer, source, snapshot, native, receipt, surfaces, output = setup(tmp_path)
    if fault == "extra":
        surfaces["replacement"] = surfaces["back"]
    elif fault == "missing":
        surfaces.pop("lid")
    elif fault == "stale-source":
        (snapshot / source.parts[-1].path).write_bytes(b"changed")
    elif fault == "stale-native":
        receipt = replace(receipt, sha256="0" * 64)
    elif fault == "existing":
        output.mkdir()
        (output / "sentinel").write_bytes(b"keep")
    elif fault == "invalid-mesh":
        surfaces["back"]["faces"] = [[0, 1, 2]]
    elif fault == "empty-verdict":

        class Empty:
            async def check(self, _):
                return MeshIntegrityReport(())

        writer = NativeStlWriter(Empty(), ImportLimits(10, 100000, 100000, 100000))
    before = {str(p): p.read_bytes() for p in snapshot.rglob("*") if p.is_file()}
    with pytest.raises(NativeRevisionError):
        await writer.write(source, snapshot, native, receipt, surfaces, ("back", "lid"), output)
    assert not (output / "native-output.json").exists() and not (output / "SHA256.json").exists()
    assert all(Path(path).read_bytes() == data for path, data in before.items())
    if fault == "existing":
        assert (output / "sentinel").read_bytes() == b"keep"


@pytest.mark.parametrize("attack", ["tamper", "extra"])
async def test_successful_geometry_verdict_cannot_hide_changed_output_identity(tmp_path, attack):
    _, source, snapshot, native, receipt, surfaces, output = setup(tmp_path)

    class Changing:
        async def check(self, paths):
            if attack == "extra":
                (output / "unexpected.stl").write_bytes(Path(paths[0]).read_bytes())
            else:
                Path(paths[0]).write_bytes(
                    trimesh.exchange.stl.export_stl(trimesh.creation.box((4, 4, 4)))
                )
            return await TrimeshCgalIntegrity().check(paths)

    writer = NativeStlWriter(Changing(), ImportLimits(10, 100000, 100000, 100000))
    with pytest.raises(NativeRevisionError):
        await writer.write(source, snapshot, native, receipt, surfaces, ("back", "lid"), output)
    assert not (output / "native-output.json").exists()
    assert not (output / "SHA256.json").exists()


async def test_repeated_cancellation_drains_validation_without_publishing_success(tmp_path):
    _, source, snapshot, native, receipt, surfaces, output = setup(tmp_path)
    entered, release = asyncio.Event(), asyncio.Event()

    class Waiting:
        async def check(self, paths):
            entered.set()
            await release.wait()
            return await TrimeshCgalIntegrity().check(paths)

    writer = NativeStlWriter(Waiting(), ImportLimits(10, 100000, 100000, 100000))
    task = asyncio.create_task(
        writer.write(source, snapshot, native, receipt, surfaces, ("back", "lid"), output)
    )
    await entered.wait()
    for _ in range(3):
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not (output / "native-output.json").exists() and not (output / "SHA256.json").exists()


async def test_existing_success_receipts_are_never_deleted_by_a_collision(tmp_path):
    writer, source, snapshot, native, receipt, surfaces, output = setup(tmp_path)
    output.mkdir()
    for name in ("native-output.json", "SHA256.json"):
        (output / name).write_bytes(b"existing successful job")
    with pytest.raises(NativeRevisionError):
        await writer.write(source, snapshot, native, receipt, surfaces, ("back", "lid"), output)
    assert all(
        (output / name).read_bytes() == b"existing successful job"
        for name in ("native-output.json", "SHA256.json")
    )
