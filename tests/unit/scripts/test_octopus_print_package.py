"""The octopus hand's released package must be complete and independently measurable.

Same contract as the V6 package: every committed binary is re-read here, not trusted
from the manifest that shipped with it. A package whose manifest agrees with itself
proves nothing.
"""

import hashlib
import json
from pathlib import Path

import pytest

from src.verification.artifact_files import binary_stl_metrics

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "models" / "octopus-hand-v1"
EXPECTED = {
    "test_coupon_mm.stl": (11636, (47.846, 48.0, 56.8)),
    "octopus_hand_v1_mm.stl": (129860, (144.408, 138.545, 117.0)),
    "palm_mm.stl": (10220, (144.408, 137.34, 18.8)),
    "arm_body_mm.stl": (3382, (43.547, 43.547, 29.6)),
    "arm_tip_mm.stl": (3480, (43.547, 43.547, 32.8)),
}


def test_versioned_octopus_print_package_matches_verified_meshes() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    assert manifest["model_revision"] == "octopus-hand-V1"
    assert manifest["units"] == "mm"
    assert set(manifest["files"]) == {*EXPECTED, "octopus_hand_v1.blend"}
    for name, (triangles, dimensions) in EXPECTED.items():
        payload = (PACKAGE / name).read_bytes()
        measured = binary_stl_metrics(payload)
        assert measured.triangle_count == triangles
        assert measured.dimensions_mm == pytest.approx(dimensions, abs=0.01)
        assert manifest["files"][name]["sha256"] == hashlib.sha256(payload).hexdigest()
    blend = (PACKAGE / "octopus_hand_v1.blend").read_bytes()
    assert len(blend) > 100_000
    assert manifest["files"]["octopus_hand_v1.blend"]["sha256"] == hashlib.sha256(blend).hexdigest()


def test_package_states_that_nothing_has_been_printed_yet() -> None:
    """The package ships before any physical print, so it must say so where a reader looks."""
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    assert "no physical print" in readme.lower()
    assert "auto-arrange" in readme.lower()
