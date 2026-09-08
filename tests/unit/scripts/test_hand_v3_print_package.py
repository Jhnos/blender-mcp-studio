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
    "phalanx_mm.stl": (3494, (24.0, 22.0, 67.0)),
    # 2714 before the air port was lifted clear of the cuff clamp band. The
    # 28 triangles that went away were the intersection between a Ø6 bore
    # and the 3 mm groove it used to be cut straight through.
    "palm_mm.stl": (2686, (140.0, 44.0, 103.5)),
    "finger_v3_mm.stl": (10482, (24.0, 22.0, 175.0)),
    # Same 28 triangles as the palm, because the palm is part of this.
    "hand_v3_mm.stl": (55096, (140.0, 44.1, 265.5)),
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


def test_the_palm_roots_reach_the_height_the_fingers_hang_at() -> None:
    """The palm must be tall enough for its knuckles to meet anything.

    It was not, for several commits: every root sat 13.5 mm low, the palm topped
    out at 20.0 mm against fork bores at 27.0, and the package shipped watertight
    and contract-green while the hand could not be assembled. The palm's own
    height is the cheapest thing that would have caught it.
    """
    palm = binary_stl_metrics((PACKAGE / "palm_mm.stl").read_bytes())

    # Plate depth below plus the root standing above: 70 + 27 + 6.5.
    assert palm.dimensions_mm[2] == pytest.approx(103.5, abs=0.1)


def test_the_finger_that_shipped_carries_three_phalanges() -> None:
    """Three, not four, and the geometry says so without being told.

    The package shipped once with four phalanges per finger — a 320 mm hand,
    1.7 times human — and every machine check passed, because reachability,
    collision, clearance and watertightness are all blind to absolute size.

    Checked as arithmetic on the assembled finger rather than as a ratio of two
    bounding boxes. The first draft of this test did compare bboxes and failed at
    1.69, and it was right to fail: an assembled finger's box includes the unit
    hanging below its own knuckle, which lives at the palm and is not finger
    length. Proportion belongs in the spec, where it is measured base-joint to
    tip and reads 1.11. What the package can honestly see is how many units are
    in the stack.
    """
    finger = binary_stl_metrics((PACKAGE / "finger_v3_mm.stl").read_bytes())
    phalanx = binary_stl_metrics((PACKAGE / "phalanx_mm.stl").read_bytes())

    # A stack of n units spans (n-1) pitches plus one whole unit, and the pitch
    # is the unit's length minus the lug diameter it shares with its neighbour.
    unit = phalanx.dimensions_mm[2]
    pitch = 54.0
    units = round((finger.dimensions_mm[2] - unit) / pitch) + 1
    assert units == 3, f"the assembled finger holds {units} phalanges"
    assert finger.dimensions_mm[2] == pytest.approx((units - 1) * pitch + unit, abs=0.1)


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


def test_the_readme_describes_the_package_that_shipped() -> None:
    """The README is the only thing a human reads before printing the parts.

    It said nineteen phalanges, a 90.0 mm palm and a 319.5 mm hand — the
    four-phalanx hand, three commits after that hand stopped existing. Every
    machine gate was green throughout: the meshes were watertight, contract
    verified, and correctly measured. Nothing checked the prose that describes
    them, so the one artifact a person reads before spending nineteen hours of
    print time was the one artifact free to be wrong.

    A dimension written in a sentence is a claim like any other, and it is
    checkable against the bytes it claims to describe.
    """
    import re

    from src.core.domain.palm_v3 import AnthropomorphicPalmSpec

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
    assert quoted >= 3, "the README stopped quoting dimensions; it is meant to quote them"

    # How many of the one part number a person has to print. Wrong by four for
    # three commits, and four wasted prints is the cheapest way this bites.
    palm = AnthropomorphicPalmSpec()
    total = len(palm.row_finger_x_mm) * len(palm.finger_segment_lengths_mm) + len(
        palm.thumb_segment_lengths_mm
    )
    words = {
        13: "thirteen",
        14: "fourteen",
        15: "fifteen",
        16: "sixteen",
        19: "nineteen",
        20: "twenty",
    }
    assert words[total] in readme, f"the README never says how many parts to print ({total})"
    for count, word in words.items():
        if count != total:
            assert word not in readme, f"the README still says {word}; the hand takes {total}"


def test_the_readme_quotes_the_reach_the_spec_computes() -> None:
    """The thumb's closest approach is a headline number, so it must be current.

    It moved when the fingers went from four phalanges to three, and the README
    kept the old figure. This is the same defect class as the dimensions above,
    kept separate because it is computed from the spec rather than measured from
    a mesh — two different sources of truth, both able to drift from prose.
    """
    import dataclasses
    import re

    from src.core.domain.palm_v3 import AnthropomorphicPalmSpec

    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    spec = AnthropomorphicPalmSpec()

    # Both figures, because the first draft of this check read one line and the
    # sentence runs onto the next one: the opposed reach was caught and the
    # flat-thumb comparison it is quoted against sat stale underneath it.
    flat = dataclasses.replace(spec, thumb_opposition_deg=0.0, thumb_palmar_tilt_deg=0.0)
    lines = readme.splitlines()
    start = next(i for i, text in enumerate(lines) if "closest approach" in text)
    sentence = " ".join(lines[start : start + 2])
    quoted = [float(v) for v in re.findall(r"(\d+\.\d+) mm", sentence)]
    assert len(quoted) == 3, f"the reach sentence should quote three figures, found {quoted}"
    opposed, contact, flat_gap = quoted
    assert opposed == pytest.approx(spec.thumb_index_tip_gap_mm, abs=0.1), (
        f"the README says {opposed}, the spec computes {spec.thumb_index_tip_gap_mm:.1f}"
    )
    assert contact == pytest.approx(spec.pinch_contact_mm, abs=0.1)
    assert flat_gap == pytest.approx(flat.thumb_index_tip_gap_mm, abs=0.1), (
        f"the README says a flat thumb gives {flat_gap}, "
        f"the spec computes {flat.thumb_index_tip_gap_mm:.1f}"
    )
    assert opposed < flat_gap, "opposing the thumb has to be what closes the gap"
