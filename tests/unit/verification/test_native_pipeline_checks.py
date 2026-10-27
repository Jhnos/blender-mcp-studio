"""Native job evidence must bind every original identity and every public byte."""

import hashlib
from copy import deepcopy
from dataclasses import asdict

import pytest

from scripts.verify.native_pipeline_checks import check_downloads, check_product
from src.core.domain.native_revision import NativeModelSource, SourceArtifact
from src.core.planning.screen_revision_plan import SCREEN_MODIFIED_OWNERS


def evidence():
    def asset(path, payload):
        return SourceArtifact(path, hashlib.sha256(payload).hexdigest(), len(payload))

    original = tuple(
        asset(f"STL/{owner}.stl", b"old-" + owner.encode())
        for owner in (*SCREEN_MODIFIED_OWNERS, "arm")
    )
    source = NativeModelSource(
        "selected",
        "models/selected",
        asset("original.blend", b"original"),
        original,
        asset("plate.3mf", b"old plate"),
        "0" * 64,
        5,
        1000,
    )
    public = {
        "native-product/parts/candidate.blend": b"candidate",
        "native-product/project.3mf": b"new plate",
    }
    outputs = []
    for part in original:
        payload = (
            b"new-" if part.path.split("/")[-1][:-4] in SCREEN_MODIFIED_OWNERS else b"old-"
        ) + part.path.split("/")[-1][:-4].encode()
        outputs.append(asset(part.path, payload))
        public["native-product/parts/" + part.path] = payload
    product = {
        "directory": "a" * 32 + "/native-product",
        "stls": {
            "source": asdict(source),
            "native": asdict(asset("candidate.blend", b"candidate")),
            "parts": [asdict(p) for p in outputs],
            "changed_paths": [p.path for p in original[:2]],
        },
        "project": asdict(asset("project.3mf", b"new plate")),
    }
    selected = {"available": True, "scope": "file_identity_only", **asdict(source)}
    return selected, product, public


def test_complete_product_binds_selected_source_and_all_downloads():
    selected, product, public = evidence()
    assert check_product(product, selected, "a" * 32) == []
    assert check_downloads(product, public) == []


@pytest.mark.parametrize(
    "fault",
    [
        "source",
        "missing",
        "duplicate",
        "renamed",
        "extra",
        "changed-set",
        "unchanged-tampered",
        "unchanged-revision",
        "foreign-job",
        "path-escape",
    ],
)
def test_product_receipt_cannot_hide_missing_extra_stale_or_replaced_originals(fault):
    selected, product, _ = evidence()
    if fault == "source":
        product["stls"]["source"]["manifest_sha256"] = "9" * 64
    if fault == "missing":
        product["stls"]["parts"].pop()
    if fault == "duplicate":
        product["stls"]["parts"].append(deepcopy(product["stls"]["parts"][0]))
    if fault == "renamed":
        product["stls"]["parts"][0]["path"] = "STL/replacement.stl"
    if fault == "extra":
        product["stls"]["parts"].append(
            {"path": "STL/extra.stl", "sha256": "8" * 64, "size_bytes": 3}
        )
    if fault == "changed-set":
        product["stls"]["changed_paths"].pop()
    if fault == "unchanged-tampered":
        product["stls"]["parts"][-1]["sha256"] = "9" * 64
    if fault == "unchanged-revision":
        product["stls"]["parts"][0] = deepcopy(selected["parts"][0])
    if fault == "foreign-job":
        product["directory"] = "b" * 32 + "/native-product"
    if fault == "path-escape":
        product["project"]["path"] = "../private.3mf"
    assert check_product(product, selected, "a" * 32)


@pytest.mark.parametrize("fault", ["missing", "tampered", "size"])
def test_downloaded_bytes_must_match_every_output_receipt(fault):
    _, product, public = evidence()
    if fault == "missing":
        public.pop(next(iter(public)))
    if fault == "tampered":
        public["native-product/project.3mf"] = b"bad plate"
    if fault == "size":
        product["project"]["size_bytes"] += 1
    assert check_downloads(product, public)


@pytest.mark.parametrize("fault", [None, "skipped", "missing", "duplicate-instance", "extra-plate"])
def test_sliced_inventory_requires_every_original_once_and_enabled(fault):
    import io
    import zipfile

    from scripts.verify.native_pipeline_checks import check_slice_inventory

    owners = ("left", "right")
    objects = "".join(
        f'<object id="{i}"><metadata key="name" value="{name}"/></object>'
        for i, name in enumerate(owners, 1)
    )
    instances = "".join(
        f'<model_instance><metadata key="object_id" value="{i}"/><metadata key="instance_id" value="0"/></model_instance>'
        for i in (1, 2)
    )
    sliced = "".join(f'<object name="{name}" skipped="false"/>' for name in owners)
    if fault == "skipped":
        sliced = sliced.replace('skipped="false"', 'skipped="true"', 1)
    if fault == "missing":
        sliced = '<object name="left" skipped="false"/>'
    if fault == "duplicate-instance":
        instances += instances
    plate = f"<plate>{instances}</plate>"
    if fault == "extra-plate":
        plate += "<plate/>"
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as z:
        z.writestr("Metadata/model_settings.config", f"<config>{objects}{plate}</config>")
        z.writestr("Metadata/slice_info.config", f"<config><plate>{sliced}</plate></config>")
    failures = check_slice_inventory(payload.getvalue(), owners)
    assert bool(failures) == (fault is not None)


@pytest.mark.parametrize(
    "fault",
    [None, "stale", "outside", "floating", "missing-brim", "missing-support", "missing-object"],
)
def test_extrusion_receipt_binds_fresh_archive_and_removable_structure_paths(tmp_path, fault):
    import json
    import zipfile

    from scripts.verify.native_pipeline_checks import check_extrusion_receipt
    from src.adapters.slicing.toolpath_evidence import inspect_sliced_project
    from src.core.domain.import_limits import ImportLimits
    from tests.fakes.bambu_bundle import MACHINE_GEOMETRY, write_sliced_output

    project = tmp_path / "slice.3mf"
    write_sliced_output(project)
    with zipfile.ZipFile(project) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    contents["Metadata/plate_1.gcode"] += (
        b"; FEATURE: Support\nG1 X3 E.1\n; FEATURE: Brim\nG1 X4 E.1\n"
    )
    with zipfile.ZipFile(project, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    payload = project.read_bytes()
    receipt = inspect_sliced_project(
        project, MACHINE_GEOMETRY, ImportLimits(10, 100000, 100000, 100000)
    )
    receipt = json.loads(json.dumps(receipt))
    plate = receipt["plates"][0]
    if fault == "stale":
        receipt["source"]["sha256"] = "0" * 64
    if fault == "outside":
        plate["outside_paths"] = 1
    if fault == "floating":
        plate["objects"][0]["bed_contact_paths"] = 0
    if fault == "missing-brim":
        plate["bed_brim_paths"] = 0
    if fault == "missing-support":
        plate["bed_support_paths"] = 0
    if fault == "missing-object":
        plate["objects"] = []
    assert bool(check_extrusion_receipt(receipt, payload, ("lid",))) == (fault is not None)
