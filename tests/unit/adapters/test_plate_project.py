"""A revised plate keeps original placement but cannot retain stale slice evidence."""

import io
import zipfile
from copy import deepcopy
from xml.etree import ElementTree as ET

import pytest

from src.adapters.artifacts.plate_project import PlateProject

NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PROD = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
POINTS = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 3.0, 0.0), (0.0, 0.0, 5.0)]
FACES = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


def original():
    return {"vertices": POINTS, "faces": FACES}


def template():
    payload = io.BytesIO()
    vertices = "".join(f'<vertex x="{10 - z}" y="{20 + y}" z="{30 + x}"/>' for x, y, z in POINTS)
    triangles = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in FACES)
    with zipfile.ZipFile(payload, "w") as z:
        z.writestr(
            "3D/3dmodel.model",
            f'<model xmlns="{NS}" xmlns:p="{PROD}" unit="millimeter"><resources><object id="2"><components><component p:path="/3D/Objects/lid.model" objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></components></object></resources><build><item objectid="2" transform="1 0 0 0 1 0 0 0 1 90 80 0"/></build></model>',
        )
        z.writestr(
            "3D/Objects/lid.model",
            f'<model xmlns="{NS}" unit="millimeter"><resources><object id="1"><mesh><vertices>{vertices}</vertices><triangles>{triangles}</triangles></mesh></object></resources></model>',
        )
        z.writestr(
            "Metadata/model_settings.config",
            '<config><object id="2"><metadata key="name" value="lid"/><metadata face_count="4"/><part id="1"><metadata key="name" value="lid"/><mesh_stat face_count="4"/></part></object><plate><metadata key="plater_id" value="1"/><metadata key="gcode_file" value="Metadata/plate_1.gcode"/></plate></config>',
        )
        z.writestr("Metadata/plate_1.gcode", "OLD INSTRUCTIONS")
        z.writestr("Metadata/plate_1.gcode.md5", "old digest")
        z.writestr("Metadata/plate_1.png", "OLD PREVIEW")
        z.writestr("Metadata/plate_1.json", "OLD BOUNDS")
        z.writestr("Metadata/slice_info.config", "OLD SLICE")
        z.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="model" Target="/3D/3dmodel.model"/><Relationship Id="preview" Target="/Metadata/plate_1.png"/></Relationships>',
        )
        z.writestr("Metadata/project_settings.config", "preserved print settings")
    return payload.getvalue()


def test_rewrite_binds_actual_original_surface_and_preserves_placement():
    source = template()
    project = PlateProject(source, ("lid",), max_bytes=100000)
    revised = deepcopy(original())
    revised["vertices"] = [(x, y, z * 1.1) for x, y, z in POINTS]
    payload, bindings = project.revise({"lid": (original(), revised)})
    with zipfile.ZipFile(io.BytesIO(source)) as old, zipfile.ZipFile(io.BytesIO(payload)) as new:
        assert new.read("3D/3dmodel.model") == old.read("3D/3dmodel.model")
        assert new.read("Metadata/project_settings.config") == old.read(
            "Metadata/project_settings.config"
        )
        assert new.read("3D/Objects/lid.model") != old.read("3D/Objects/lid.model")
        assert not any(
            n.endswith((".gcode", ".md5", ".png"))
            or n in ("Metadata/plate_1.json", "Metadata/slice_info.config")
            for n in new.namelist()
        )
        assert "plate_1" not in new.read("_rels/.rels").decode()
        assert b"<Relationships xmlns=" in new.read("_rels/.rels")
        assert b"ns0:" not in new.read("_rels/.rels")
        assert "gcode_file" not in new.read("Metadata/model_settings.config").decode()
        model = ET.fromstring(new.read("3D/Objects/lid.model"))
        points = [
            tuple(float(v.attrib[a]) for a in "xyz") for v in model.findall(f".//{{{NS}}}vertex")
        ]
        assert points == [(10 - z * 1.1, 20 + y, 30 + x) for x, y, z in POINTS]
    assert set(bindings) == {"lid"}


@pytest.mark.parametrize(
    "fault",
    [
        "owner-missing",
        "owner-extra",
        "owner-duplicate",
        "empty-change",
        "unknown-change",
        "original-changed",
        "open-new",
        "byte-budget",
    ],
)
def test_ambiguous_or_stale_inputs_are_rejected(fault):
    owners = ("lid",)
    change = {"lid": (original(), original())}
    budget = 100000
    if fault == "owner-missing":
        owners = ("arm",)
    elif fault == "owner-extra":
        owners = ("lid", "arm")
    elif fault == "owner-duplicate":
        owners = ("lid", "lid")
    elif fault == "empty-change":
        change = {}
    elif fault == "unknown-change":
        change = {"arm": (original(), original())}
    elif fault == "original-changed":
        change["lid"][0]["vertices"] = [(x * 2, y, z) for x, y, z in POINTS]
    elif fault == "open-new":
        change["lid"][1]["faces"] = FACES[:-1]
    elif fault == "byte-budget":
        budget = 10
    with pytest.raises(ValueError):
        PlateProject(template(), owners, max_bytes=budget).revise(change)


def test_readonly_binding_and_revision_share_the_same_source_identity_check():
    project = PlateProject(template(), ("lid",), max_bytes=100000)
    report = project.bind_originals({"lid": original()})
    assert report["lid"]["binding"]["translation_mm"] == (10, 20, 30)
    with pytest.raises(ValueError):
        project.bind_originals({"arm": original()})
    with pytest.raises(ValueError):
        project.bind_originals({})


@pytest.mark.parametrize(
    "fault",
    [
        "bad-zip",
        "missing-model",
        "malformed-xml",
        "duplicate-member",
        "component-transform",
        "dangling-relationship",
    ],
)
def test_invalid_archive_cannot_become_a_revision(fault):
    if fault == "bad-zip":
        payload = b"not a project"
    else:
        with zipfile.ZipFile(io.BytesIO(template())) as source:
            entries = {n: source.read(n) for n in source.namelist()}
        if fault == "missing-model":
            entries.pop("3D/Objects/lid.model")
        elif fault == "malformed-xml":
            entries["3D/3dmodel.model"] = b"<model"
        elif fault == "component-transform":
            entries["3D/3dmodel.model"] = entries["3D/3dmodel.model"].replace(
                b"1 0 0 0 1 0 0 0 1 0 0 0", b"1 0 0 0 1 0 0 0 1 1 0 0"
            )
        elif fault == "dangling-relationship":
            entries["_rels/.rels"] = entries["_rels/.rels"].replace(
                b"/3D/3dmodel.model", b"/missing.model"
            )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as target:
            for name, data in entries.items():
                target.writestr(name, data)
            if fault == "duplicate-member":
                with pytest.warns(UserWarning, match="Duplicate name"):
                    target.writestr("3D/3dmodel.model", entries["3D/3dmodel.model"])
        payload = buffer.getvalue()
    with pytest.raises(ValueError):
        PlateProject(payload, ("lid",), max_bytes=100000).revise({"lid": (original(), original())})
