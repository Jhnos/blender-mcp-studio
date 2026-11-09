"""Complete same-part STLs precede a derived plate; failed products are never published."""

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from dataclasses import asdict, replace

import pytest
import trimesh

from src.adapters.artifacts.native_product import NativeProductWriter
from src.adapters.mesh.trimesh_cgal_integrity import TrimeshCgalIntegrity
from src.core.domain.import_limits import ImportLimits
from src.core.domain.native_revision import NativeModelSource, NativeRevisionError, SourceArtifact
from tests.unit.adapters.test_plate_project import original, template


def fixture(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()

    def asset(name, payload):
        p = snapshot / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
        return SourceArtifact(name, hashlib.sha256(payload).hexdigest(), len(payload))

    native = asset("original.blend", b"original")
    mesh = original()
    payload = trimesh.exchange.stl.export_stl(
        trimesh.Trimesh(vertices=mesh["vertices"], faces=mesh["faces"], process=False)
    )
    part = asset("STL/lid.stl", payload)
    project = asset("plate.3mf", template())
    source = NativeModelSource(
        "selected",
        "models/selected",
        native,
        (part,),
        project,
        "0" * 64,
        3,
        sum(p.size_bytes for p in (native, part, project)),
    )
    candidate = tmp_path / "candidate.blend"
    candidate.write_bytes(b"candidate")
    receipt = SourceArtifact(
        candidate.name, hashlib.sha256(candidate.read_bytes()).hexdigest(), candidate.stat().st_size
    )
    changed = deepcopy(mesh)
    changed["vertices"] = [(x, y, z * 1.1) for x, y, z in changed["vertices"]]
    writer = NativeProductWriter(
        TrimeshCgalIntegrity(), ImportLimits(10, 100000, 100000, 100000), tmp_path
    )
    return writer, source, snapshot, candidate, receipt, {"lid": changed}, tmp_path / "product"


async def test_full_stl_manifest_exists_before_plate_revision_and_lineage_is_relative(
    tmp_path, monkeypatch
):
    import src.adapters.artifacts.native_product as module

    writer, source, snapshot, native, receipt, changed, output = fixture(tmp_path)
    real = module.PlateProject

    class ObservedProject(real):
        def revise(self, changes):
            manifest = json.loads((output / "parts/SHA256.json").read_text())
            assert "STL/lid.stl" in manifest
            assert not (output / "project.3mf").exists()
            return super().revise(changes)

    monkeypatch.setattr(module, "PlateProject", ObservedProject)
    before = {p: p.read_bytes() for p in snapshot.rglob("*") if p.is_file()}
    result = await writer.write(source, snapshot, native, receipt, changed, ("lid",), output)
    assert result.directory == "product" and len(result.stls.parts) == 1
    assert result.project.path == "project.3mf"
    assert (
        hashlib.sha256((output / result.project.path).read_bytes()).hexdigest()
        == result.project.sha256
    )
    assert str(tmp_path) not in json.dumps(asdict(result))
    assert before == {p: p.read_bytes() for p in before}
    with zipfile.ZipFile(io.BytesIO((output / "project.3mf").read_bytes())) as project:
        assert not any(n.endswith((".gcode", ".md5", ".png")) for n in project.namelist())
    assert (output / "product.json").is_file()


async def test_bad_template_keeps_complete_stls_but_has_no_success_product(tmp_path):
    writer, source, snapshot, native, receipt, changed, output = fixture(tmp_path)
    project = snapshot / source.project_3mf.path
    project.write_bytes(b"not a template")
    source = replace(
        source,
        project_3mf=SourceArtifact(
            source.project_3mf.path,
            hashlib.sha256(project.read_bytes()).hexdigest(),
            project.stat().st_size,
        ),
    )
    with pytest.raises(NativeRevisionError):
        await writer.write(source, snapshot, native, receipt, changed, ("lid",), output)
    assert (output / "parts/SHA256.json").is_file()
    assert not (output / "product.json").exists() and not (output / "project.3mf").exists()


async def test_existing_product_is_preserved_without_overwriting_any_file(tmp_path):
    writer, source, snapshot, native, receipt, changed, output = fixture(tmp_path)
    output.mkdir()
    marker = output / "project.3mf"
    marker.write_bytes(b"earlier revision")
    with pytest.raises(NativeRevisionError):
        await writer.write(source, snapshot, native, receipt, changed, ("lid",), output)
    assert marker.read_bytes() == b"earlier revision"
    assert set(output.iterdir()) == {marker}


async def test_source_changed_after_stl_validation_cannot_publish_plate(tmp_path, monkeypatch):
    writer, source, snapshot, native, receipt, changed, output = fixture(tmp_path)
    import src.adapters.artifacts.native_product as module

    real = module.PlateProject

    class TamperedProject(real):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            (snapshot / source.parts[0].path).write_bytes(b"changed after full STL check")

    monkeypatch.setattr(module, "PlateProject", TamperedProject)
    with pytest.raises(NativeRevisionError):
        await writer.write(source, snapshot, native, receipt, changed, ("lid",), output)
    assert (output / "parts/SHA256.json").is_file()
    assert not (output / "project.3mf").exists()
    assert not (output / "product.json").exists()


async def test_output_symlink_cannot_redirect_delivery_outside_job_root(tmp_path):
    writer, source, snapshot, native, receipt, changed, output = fixture(tmp_path)
    external = tmp_path.parent / (tmp_path.name + "-external")
    external.mkdir()
    output.symlink_to(external, target_is_directory=True)
    with pytest.raises(NativeRevisionError):
        await writer.write(source, snapshot, native, receipt, changed, ("lid",), output)
    assert not list(external.iterdir())
