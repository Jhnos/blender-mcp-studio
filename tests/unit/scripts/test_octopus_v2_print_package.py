"""V2's released package must be complete, independently measurable, and not V1's.

Same contract as the V1 and V6 packages: every committed binary is re-read here, not
trusted from the manifest that shipped beside it, because a manifest that agrees with
itself proves nothing.

One check is new. V1 and V2 export five files under the same five names, so the two
packages are trivially confusable — and a copy of V1 promoted into V2's directory
would satisfy every "is it well formed" assertion in this file. The last test asserts
they are actually different meshes, which is the assertion V1's own suite could not
have needed and this one cannot do without.
"""

import hashlib
import json
from pathlib import Path

import pytest

from src.verification.artifact_files import binary_stl_metrics

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "models" / "octopus-hand-v2"
V1_PACKAGE = ROOT / "models" / "octopus-hand-v1"
EXPECTED = {
    "test_coupon_mm.stl": (11894, (45.623, 48.0, 56.8)),
    "octopus_hand_v2_mm.stl": (131944, (119.442, 124.934, 118.0)),
    "palm_mm.stl": (11494, (116.618, 122.619, 18.8)),
    "arm_body_mm.stl": (3408, (42.0, 42.0, 29.6)),
    "arm_tip_mm.stl": (3538, (42.0, 42.0, 33.8)),
}


def test_versioned_octopus_v2_print_package_matches_verified_meshes() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    assert manifest["model_revision"] == "octopus-hand-V2.1"
    assert manifest["units"] == "mm"
    assert manifest["source_generator"] == "scripts/model_octopus_hand_v2.py"
    assert set(manifest["files"]) == {*EXPECTED, "octopus_hand_v2.blend"}
    for name, (triangles, dimensions) in EXPECTED.items():
        payload = (PACKAGE / name).read_bytes()
        measured = binary_stl_metrics(payload)
        assert measured.triangle_count == triangles
        assert measured.dimensions_mm == pytest.approx(dimensions, abs=0.01)
        assert manifest["files"][name]["sha256"] == hashlib.sha256(payload).hexdigest()
    blend = (PACKAGE / "octopus_hand_v2.blend").read_bytes()
    assert len(blend) > 100_000
    assert manifest["files"]["octopus_hand_v2.blend"]["sha256"] == hashlib.sha256(blend).hexdigest()


def test_package_states_that_nothing_has_been_printed_yet() -> None:
    """The package ships before any physical print, so it must say so where a reader looks."""
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    assert "no physical print" in readme.lower()
    assert "auto-arrange" in readme.lower()


def test_v2_is_not_a_copy_of_v1_under_a_new_name() -> None:
    """Two packages that should differ, compared to each other rather than to a table.

    "Both are well formed" and "both are the same file" look identical under every
    other assertion here. The three shared filenames are checked byte-wise, and the
    palm — the part V2 exists to change — is checked to have actually changed shape.
    """
    for name in ("palm_mm.stl", "arm_body_mm.stl", "arm_tip_mm.stl"):
        assert (PACKAGE / name).read_bytes() != (V1_PACKAGE / name).read_bytes(), name

    v2_palm = binary_stl_metrics((PACKAGE / "palm_mm.stl").read_bytes())
    v1_palm = binary_stl_metrics((V1_PACKAGE / "palm_mm.stl").read_bytes())
    # Turning the pentagon onto the arms is what makes the plate smaller; the whole
    # hand shrinks with it while keeping the same twenty-five joints.
    assert max(v2_palm.dimensions_mm[:2]) < max(v1_palm.dimensions_mm[:2])
    assert v2_palm.dimensions_mm[2] == pytest.approx(v1_palm.dimensions_mm[2], abs=0.01)

    v2_hand = binary_stl_metrics((PACKAGE / "octopus_hand_v2_mm.stl").read_bytes())
    v1_hand = binary_stl_metrics((V1_PACKAGE / "octopus_hand_v1_mm.stl").read_bytes())
    assert max(v2_hand.dimensions_mm[:2]) < max(v1_hand.dimensions_mm[:2])
