"""Source/template identity must use the captured receipts and unique owners."""

import hashlib
import zipfile
from dataclasses import replace

import pytest
import trimesh

from scripts.verify.native_revision_checks import check_plate_bindings
from src.core.domain.native_revision import NativeModelSource, SourceArtifact


def fixture(tmp_path):
    vertices = [(0, 0, 0), (2, 0, 0), (0, 3, 0), (0, 0, 5)]
    faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
    stl = trimesh.exchange.stl.export_stl(
        trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    )
    (tmp_path / "lid.stl").write_bytes(stl)
    point_xml = "".join(f'<vertex x="{10 - z}" y="{20 + y}" z="{30 + x}"/>' for x, y, z in vertices)
    face_xml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in faces)
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    prod = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
    with zipfile.ZipFile(tmp_path / "source.3mf", "w") as archive:
        archive.writestr(
            "Metadata/model_settings.config",
            '<config><object id="2"><metadata key="name" value="lid"/><part id="1"><metadata key="name" value="lid"/></part></object></config>',
        )
        archive.writestr(
            "3D/3dmodel.model",
            f'<model xmlns="{ns}" xmlns:p="{prod}" unit="millimeter"><resources><object id="2"><components><component p:path="/3D/Objects/lid.model" objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></components></object></resources><build><item objectid="2"/></build></model>',
        )
        archive.writestr(
            "3D/Objects/lid.model",
            f'<model xmlns="{ns}" unit="millimeter"><resources><object id="1"><mesh><vertices>{point_xml}</vertices><triangles>{face_xml}</triangles></mesh></object></resources></model>',
        )

    def receipt(path):
        data = (tmp_path / path).read_bytes()
        return SourceArtifact(path, hashlib.sha256(data).hexdigest(), len(data))

    return NativeModelSource(
        "test",
        "models/test",
        receipt("lid.stl"),
        (receipt("lid.stl"),),
        receipt("source.3mf"),
        "0" * 64,
        2,
    )


def test_exact_captured_source_template_binding(tmp_path):
    source = fixture(tmp_path)
    result = check_plate_bindings(source, tmp_path, ("lid",))
    assert set(result) == {"lid"}
    assert result["lid"]["binding"]["translation_mm"] == (10, 20, 30)


@pytest.mark.parametrize(
    "fault",
    [
        "stale-project",
        "stale-stl",
        "missing-project",
        "unknown-owner",
        "duplicate-owner",
        "empty-owner",
    ],
)
def test_invalid_or_ambiguous_binding_is_rejected(tmp_path, fault):
    source = fixture(tmp_path)
    owners = ("lid",)
    if fault == "stale-project":
        source = replace(source, project_3mf=replace(source.project_3mf, sha256="0" * 64))
    elif fault == "stale-stl":
        source = replace(source, parts=(replace(source.parts[0], sha256="0" * 64),))
    elif fault == "missing-project":
        source = replace(source, project_3mf=None)
    elif fault == "unknown-owner":
        owners = ("arm",)
    elif fault == "duplicate-owner":
        owners = ("lid", "lid")
    elif fault == "empty-owner":
        owners = ()
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError):
        check_plate_bindings(source, tmp_path, owners)
    assert before == {p: p.read_bytes() for p in tmp_path.iterdir()}
