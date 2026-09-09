"""The three-station gripper's released package must be complete, measurable, and honest.

Same contract as the V3 and compact packages: every committed binary is re-read
here rather than trusted from the manifest beside it, and the README's numbers
are held to the bytes and to the spec. What is specific to this package is the
row count — three chains, not five — so every "how many prints" number differs
from its neighbours, and prose copied across would be wrong in a way no mesh
check can see.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from pathlib import Path

import pytest

from src.core.domain.hand_instances import HAND_INSTANCES
from src.core.domain.opposition import thumb_rest_clearance_mm
from src.verification.artifact_files import binary_stl_metrics

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "models" / "hand-gripper"
INSTANCE = HAND_INSTANCES["hand-gripper"]
#: Measured from the published bytes (2026-09-09).
EXPECTED = {
    "phalanx_base_mm.stl": (2978, (17.0, 15.0, 53.0)),
    "phalanx_distal_mm.stl": (2986, (17.0, 15.0, 53.0)),
    "palm_mm.stl": (2086, (56.0, 30.0, 80.5)),
    "finger_gripper_mm.stl": (8950, (17.0, 15.0, 149.0)),
    "hand_gripper_mm.stl": (28936, (82.2, 30.3, 224.5)),
}
#: Every count word the README could plausibly inherit from a sibling package.
WORDS = {3: "three", 5: "five", 6: "six", 9: "nine", 10: "ten", 15: "fifteen"}


def test_versioned_hand_gripper_print_package_matches_verified_meshes() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    assert manifest["model_revision"] == "hand-gripper-V1"
    assert manifest["units"] == "mm"
    assert manifest["source_generator"] == INSTANCE.generator_script
    assert set(manifest["files"]) == {*EXPECTED, INSTANCE.blend_file, *INSTANCE.render_files}
    assert tuple(EXPECTED) == INSTANCE.stl_files
    for name, (triangles, dimensions) in EXPECTED.items():
        payload = (PACKAGE / name).read_bytes()
        measured = binary_stl_metrics(payload)
        assert measured.triangle_count == triangles, name
        assert measured.dimensions_mm == pytest.approx(dimensions, abs=0.1), name
        assert manifest["files"][name]["sha256"] == hashlib.sha256(payload).hexdigest()
    for name in (INSTANCE.blend_file, *INSTANCE.render_files):
        payload = (PACKAGE / name).read_bytes()
        assert len(payload) > 10_000, name
        assert manifest["files"][name]["sha256"] == hashlib.sha256(payload).hexdigest()


def test_the_palm_is_narrower_than_its_four_finger_siblings() -> None:
    """The whole point of the instance. If this palm ever measures as wide as the
    compact one, the row count stopped reaching the geometry."""
    gripper = binary_stl_metrics((PACKAGE / "palm_mm.stl").read_bytes())
    compact = binary_stl_metrics((ROOT / "models" / "hand-compact" / "palm_mm.stl").read_bytes())

    assert gripper.dimensions_mm[0] < compact.dimensions_mm[0]


def test_the_two_phalanx_part_numbers_share_an_envelope_and_differ_inside() -> None:
    base = binary_stl_metrics((PACKAGE / "phalanx_base_mm.stl").read_bytes())
    distal = binary_stl_metrics((PACKAGE / "phalanx_distal_mm.stl").read_bytes())

    assert base.dimensions_mm == pytest.approx(distal.dimensions_mm, abs=0.1)
    assert (PACKAGE / "phalanx_base_mm.stl").read_bytes() != (
        PACKAGE / "phalanx_distal_mm.stl"
    ).read_bytes()


def test_the_assembled_gripper_fits_the_bed_and_the_readme_does_not_say_otherwise() -> None:
    hand = binary_stl_metrics((PACKAGE / "hand_gripper_mm.stl").read_bytes())
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8").lower()

    assert max(hand.dimensions_mm) < 256.0
    assert "too tall" not in readme
    assert "auto-arrange" in readme
    assert "no physical print has been made yet" in readme
    assert "never been built" in readme


def test_the_readme_describes_the_package_that_shipped() -> None:
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    triple = re.compile(r"(\d+\.\d+) × (\d+\.\d+) × (\d+\.\d+) mm")

    quoted = 0
    for name in EXPECTED:
        measured = binary_stl_metrics((PACKAGE / name).read_bytes()).dimensions_mm
        for line in readme.splitlines():
            if name not in line:
                continue
            for found in triple.findall(line):
                quoted += 1
                assert tuple(float(v) for v in found) == pytest.approx(measured, abs=0.1), (
                    f"{name}: the README says {found}, the file measures {measured}"
                )
    assert quoted >= 4, "the README stopped quoting dimensions; it is meant to quote them"

    palm = INSTANCE.palm
    chains = len(palm.row_finger_x_mm) + 1
    units = palm.finger.link.assembly_unit_count
    base_prints, distal_prints = chains, chains * (units - 1)
    total = base_prints + distal_prints

    def says(word: str, text: str) -> bool:
        # Whole words only: "ten" must not be satisfied by "tendon".
        return re.search(rf"\b{word}\b", text, re.IGNORECASE) is not None

    assert says(WORDS[total], readme), f"the README never says how many parts to print ({total})"
    for count, word in WORDS.items():
        if count not in {base_prints, distal_prints, total}:
            assert not says(word, readme), f"the README still says {word}; this hand takes {total}"
    base_line = next(line for line in readme.splitlines() if "phalanx_base_mm.stl" in line)
    distal_line = next(line for line in readme.splitlines() if "phalanx_distal_mm.stl" in line)
    assert says(WORDS[base_prints], base_line)
    assert says(WORDS[distal_prints], distal_line)


def test_the_readme_quotes_the_reach_and_the_clearance_the_spec_computes() -> None:
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    spec = INSTANCE.palm
    flat = dataclasses.replace(
        spec, thumb_opposition_deg=0.0, thumb_palmar_tilt_deg=0.0, strict=False
    )
    lines = readme.splitlines()
    start = next(i for i, text in enumerate(lines) if "closest approach" in text)
    sentence = " ".join(lines[start : start + 2])
    quoted = [float(v) for v in re.findall(r"(\d+\.\d+) mm", sentence)]
    assert len(quoted) == 3, f"the reach sentence should quote three figures, found {quoted}"
    opposed, contact, flat_gap = quoted
    assert opposed == pytest.approx(spec.thumb_index_tip_gap_mm, abs=0.1)
    assert contact == pytest.approx(spec.pinch_contact_mm, abs=0.1)
    assert flat_gap == pytest.approx(flat.thumb_index_tip_gap_mm, abs=0.1)
    assert opposed < flat_gap

    rest = re.search(r"[Aa]t rest[^.]*?(\d+\.\d+) mm", readme)
    assert rest is not None, "the README no longer states the thumb's rest clearance"
    assert float(rest.group(1)) == pytest.approx(thumb_rest_clearance_mm(spec), abs=0.05)
