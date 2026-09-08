"""V3's released package must be complete, independently measurable, and not V2's.

Same contract as the V1, V2 and V6 packages: every committed binary is re-read
here rather than trusted from the manifest that shipped beside it, because a
manifest that agrees with itself proves nothing.

Two checks are specific to this package. V3 shares the name `palm_mm.stl` with
both octopus packages, so a stray copy would satisfy every well-formedness
assertion in this file — the palms are compared to each other instead. And the
phalanx is the part printed nineteen times, so its being one part rather than
four is the claim worth pinning.
"""

import hashlib
import json
from pathlib import Path

import pytest

from src.verification.artifact_files import binary_stl_metrics

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "models" / "hand-v3"
V2_PACKAGE = ROOT / "models" / "octopus-hand-v2"
EXPECTED = {
    "phalanx_mm.stl": (3906, (24.0, 22.0, 67.0)),
    "palm_mm.stl": (3218, (140.0, 44.0, 90.0)),
    "finger_v3_mm.stl": (15624, (24.0, 22.0, 229.0)),
    "hand_v3_mm.stl": (77432, (140.0, 44.1, 319.5)),
}


def test_versioned_hand_v3_print_package_matches_verified_meshes() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    assert manifest["model_revision"] == "hand-V3"
    assert manifest["units"] == "mm"
    assert manifest["source_generator"] == "scripts/model_finger_v3.py"
    assert set(manifest["files"]) == {*EXPECTED, "finger_v3.blend"}
    for name, (triangles, dimensions) in EXPECTED.items():
        payload = (PACKAGE / name).read_bytes()
        measured = binary_stl_metrics(payload)
        assert measured.triangle_count == triangles, name
        assert measured.dimensions_mm == pytest.approx(dimensions, abs=0.1), name
        assert manifest["files"][name]["sha256"] == hashlib.sha256(payload).hexdigest()
    blend = (PACKAGE / "finger_v3.blend").read_bytes()
    assert len(blend) > 100_000
    assert manifest["files"]["finger_v3.blend"]["sha256"] == hashlib.sha256(blend).hexdigest()


def test_the_assembled_hand_is_deliberately_too_tall_for_the_bed() -> None:
    """It is a reference, not a print, and the README has to say so.

    Someone reading a 319.5 mm dimension against a 256 mm bed should find the
    answer in the package rather than guessing that the package is broken.
    """
    hand = binary_stl_metrics((PACKAGE / "hand_v3_mm.stl").read_bytes())
    phalanx = binary_stl_metrics((PACKAGE / "phalanx_mm.stl").read_bytes())

    assert max(hand.dimensions_mm) > 256.0
    assert max(phalanx.dimensions_mm) < 256.0
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    assert "too tall" in readme.lower()
    assert "auto-arrange" in readme.lower()


def test_the_package_claims_nothing_about_the_pneumatic_layer() -> None:
    """It has never been built, so the package must not imply otherwise."""
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")

    assert "no physical print has been made yet" in readme.lower()
    assert "never been built" in readme.lower()


def test_v3_is_not_a_copy_of_an_octopus_palm_under_a_new_name() -> None:
    """`palm_mm.stl` is a name three packages share, so compare the bytes."""
    assert (PACKAGE / "palm_mm.stl").read_bytes() != (V2_PACKAGE / "palm_mm.stl").read_bytes()

    v3_palm = binary_stl_metrics((PACKAGE / "palm_mm.stl").read_bytes())
    v2_palm = binary_stl_metrics((V2_PACKAGE / "palm_mm.stl").read_bytes())
    # A row of knuckles is a different shape from a pentagon: wider than it is
    # deep, where the octopus plate is nearly square.
    assert v3_palm.dimensions_mm[0] / v3_palm.dimensions_mm[1] > 2.0
    assert v2_palm.dimensions_mm[0] / v2_palm.dimensions_mm[1] < 1.2
