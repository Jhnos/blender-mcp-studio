"""Released print packages must be complete, immutable, and independently measurable."""

import hashlib
import json
from pathlib import Path

import pytest

from src.verification.artifact_files import binary_stl_metrics

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "models" / "biaxial-hinge-v6"
EXPECTED = {
    "body_mm.stl": (3436, (36.0, 36.0, 29.6)),
    "assembly_pin_mm.stl": (1052, (6.0, 6.0, 9.2)),
    "retaining_clip_mm.stl": (310, (5.6967, 6.0, 0.9)),
    "print_in_place_2body_double_head_mm.stl": (8256, (48.6, 36.0, 36.0)),
    "separate_parts_2body_2pin_2clip_mm.stl": (9596, (82.0, 48.0, 29.6)),
}


def test_versioned_v6_print_package_matches_verified_meshes() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    assert manifest["model_revision"] == "V6"
    assert manifest["units"] == "mm"
    assert set(manifest["files"]) == {*EXPECTED, "biaxial_hinge_v6.blend"}
    for name, (triangles, dimensions) in EXPECTED.items():
        payload = (PACKAGE / name).read_bytes()
        measured = binary_stl_metrics(payload)
        assert measured.triangle_count == triangles
        assert measured.dimensions_mm == pytest.approx(dimensions, abs=0.01)
        assert manifest["files"][name]["sha256"] == hashlib.sha256(payload).hexdigest()
    blend = (PACKAGE / "biaxial_hinge_v6.blend").read_bytes()
    assert len(blend) > 100_000
    assert (
        manifest["files"]["biaxial_hinge_v6.blend"]["sha256"] == hashlib.sha256(blend).hexdigest()
    )
