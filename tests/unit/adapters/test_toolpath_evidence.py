"""Fresh sliced archives require explicit machine limits and named first-layer evidence."""

import hashlib
import zipfile
from copy import deepcopy

import pytest

from src.adapters.slicing.toolpath_evidence import inspect_sliced_project
from src.core.domain.import_limits import ImportLimits

LIMITS = ImportLimits(10, 100000, 100000, 100000)
MACHINE = {
    "printable_area": ["0x0", "10x0", "10x10", "0x10"],
    "printable_height": "10",
    "bed_exclude_area": [],
    "extruder_offset": ["0X0"],
    "nozzle_diameter": ["0.4"],
}
GCODE = (
    "\n".join(
        [
            "G90",
            "M83",
            "G92 E0",
            "G0 X1 Y1 Z.2",
            "; CHANGE_LAYER",
            "; LAYER_HEIGHT: .2",
            "; LINE_WIDTH: .5",
            "; OBJECT_ID: 8",
            "; FEATURE: Support",
            "G1 X2 E.1",
        ]
    )
    + "\n"
)


def project(tmp_path, gcode=GCODE):
    path = tmp_path / "slice.3mf"
    settings = '<config><object id="2"><metadata key="name" value="lid"/></object><plate><metadata key="plater_id" value="1"/><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/><metadata key="identify_id" value="8"/></model_instance></plate></config>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Metadata/model_settings.config", settings)
        z.writestr("Metadata/plate_1.gcode", gcode)
    return path


def test_complete_inspection_binds_output_bytes_machine_limits_and_each_named_object(tmp_path):
    path = project(tmp_path)
    before = path.read_bytes()
    report = inspect_sliced_project(path, MACHINE, LIMITS)
    assert report["passed"]
    assert report["source"]["sha256"] == hashlib.sha256(before).hexdigest()
    (plate,) = report["plates"]
    assert plate["gcode_sha256"] == hashlib.sha256(GCODE.encode()).hexdigest()
    assert plate["objects"] == [{"object_id": 8, "name": "lid", "paths": 1, "bed_contact_paths": 1}]
    assert plate["support_paths"] == 1 and plate["outside_paths"] == 0
    assert report["build_volume"]["maximum_mm"] == (10, 10, 10)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "change", ["outside", "unknown-object", "no-contact", "custom-only", "missing-width"]
)
def test_failed_envelope_or_identity_keeps_explicit_failed_evidence(tmp_path, change):
    code = GCODE
    if change == "outside":
        code = code.replace("G1 X2 E.1", "G1 X20 E.1")
    if change == "unknown-object":
        code = code.replace("OBJECT_ID: 8", "OBJECT_ID: 9")
    if change == "no-contact":
        code = code.replace("Z.2", "Z1")
    if change == "custom-only":
        code = code.replace("FEATURE: Support", "FEATURE: Custom")
    if change == "missing-width":
        code = code.replace("; LINE_WIDTH: .5\n", "")
    assert not inspect_sliced_project(project(tmp_path, code), MACHINE, LIMITS)["passed"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("printable_area", ["0x0", "10x10", "0x10", "10x0"]),
        ("bed_exclude_area", ["0x0"]),
        ("extruder_offset", ["1x0"]),
        ("printable_height", "/Users/name/private"),
    ],
)
def test_unsupported_machine_geometry_never_falls_back_to_a_default_bed(tmp_path, field, value):
    machine = deepcopy(MACHINE)
    machine[field] = value
    report = inspect_sliced_project(project(tmp_path), machine, LIMITS)
    assert not report["passed"]
    assert "/Users/" not in str(report)


def test_invalid_archive_cannot_produce_successful_toolpath_evidence(tmp_path):
    path = tmp_path / "broken.3mf"
    path.write_bytes(b"not a zip")
    assert not inspect_sliced_project(path, MACHINE, LIMITS)["passed"]


def test_slicer_evidence_runs_without_model_solver_blender_or_delivery_frameworks():
    import subprocess
    import sys
    from pathlib import Path

    code = """import importlib.abc,sys
class RejectEngines(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'CGAL','bpy','fastapi','fastmcp'}:
            raise ImportError('slicer evidence loaded unrelated dependency: '+fullname)
sys.meta_path.insert(0,RejectEngines())
from src.adapters.slicing.toolpath_evidence import inspect_sliced_project
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_malformed_numeric_metadata_is_rejected_without_echoing_host_paths(tmp_path):
    code = GCODE.replace("; OBJECT_ID: 8", "; OBJECT_ID: /Users/name/private")
    report = inspect_sliced_project(project(tmp_path, code), MACHINE, LIMITS)
    assert not report["passed"] and "/Users/" not in str(report)


def test_inspection_deadline_stops_the_same_reader_with_failed_evidence(tmp_path):
    from itertools import chain, repeat

    ticks = iter(chain([0.0], repeat(10.0)))
    report = inspect_sliced_project(
        project(tmp_path), MACHINE, LIMITS, timeout_s=1, clock=lambda: next(ticks)
    )
    assert not report["passed"] and "budget" in report["error"]
