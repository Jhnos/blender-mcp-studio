"""Every figure the V3 docs quote is derived here, not trusted.

The package README shipped for three commits describing a hand that no longer
existed — nineteen parts, a 90.0 mm palm, a 319.5 mm hand — while every mesh
gate stayed green, because the gates verified the meshes and nothing verified
the sentences about them. The same figures are quoted in the doc tree, and the
same nothing was checking them.

So the doc tables are read back and compared against the two sources that can
actually answer: the domain spec for anything computed, and the shipped STLs
for anything measured. A number in a table is a claim; this is the check.
"""

import dataclasses
import re
from pathlib import Path

import pytest

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.verification.artifact_files import binary_stl_metrics

ROOT = Path(__file__).resolve().parents[3]
PALM_DOC = ROOT / "docs" / "hand-v3" / "04-palm-thumb.md"
PACKAGE = ROOT / "models" / "hand-v3"

DECIMAL = re.compile(r"\d+\.\d+")
_CHINESE = {3: "三", 4: "四", 5: "五"}


def _row(document: str, label: str) -> str:
    """The value cell of the one table row carrying this label."""
    rows = [line for line in document.splitlines() if line.startswith("|") and label in line]
    assert len(rows) == 1, f"expected exactly one row labelled {label!r}, found {len(rows)}"
    return rows[0].split("|")[2]


def _quoted(document: str, label: str, count: int) -> list[float]:
    found = [float(v) for v in DECIMAL.findall(_row(document, label))]
    assert len(found) >= count, f"{label}: expected {count} figures, found {found}"
    return found[:count]


def test_the_palm_doc_quotes_the_reach_the_spec_computes() -> None:
    doc = PALM_DOC.read_text(encoding="utf-8")
    spec = AnthropomorphicPalmSpec()
    flat = dataclasses.replace(spec, thumb_opposition_deg=0.0, thumb_palmar_tilt_deg=0.0)

    assert _quoted(doc, "對指後最近距離", 1)[0] == pytest.approx(
        spec.thumb_index_tip_gap_mm, abs=0.1
    )
    assert _quoted(doc, "接觸判準", 1)[0] == pytest.approx(spec.pinch_contact_mm, abs=0.1)
    assert _quoted(doc, "拇指沒轉、留在指列裡", 1)[0] == pytest.approx(
        flat.thumb_index_tip_gap_mm, abs=0.1
    )
    assert _quoted(doc, "掌寬 / 指距", 2) == pytest.approx(
        [spec.palm_width_mm, spec.row_pitch_mm], abs=0.1
    )
    assert _quoted(doc, "手指長 / 拇指長", 2) == pytest.approx(
        [sum(spec.finger_segment_lengths_mm), sum(spec.thumb_segment_lengths_mm)], abs=0.1
    )


def test_the_palm_doc_quotes_the_meshes_that_shipped() -> None:
    doc = PALM_DOC.read_text(encoding="utf-8")
    for label, name in (
        ("組裝包絡", "hand_v3_mm.stl"),
        ("掌盤單件", "palm_mm.stl"),
        ("指節單件", "phalanx_mm.stl"),
    ):
        measured = binary_stl_metrics((PACKAGE / name).read_bytes())
        assert _quoted(doc, label, 3) == pytest.approx(measured.dimensions_mm, abs=0.1), label

    # Written with a thin space for readability, so it has to be un-spaced to
    # be compared rather than eyeballed.
    faces = re.search(r"([\d ]+)\s*三角面", _row(doc, "掌盤單件"))
    assert faces is not None
    palm = binary_stl_metrics((PACKAGE / "palm_mm.stl").read_bytes())
    assert int(faces.group(1).replace(" ", "")) == palm.triangle_count


def test_the_palm_doc_counts_the_parts_the_spec_asks_for() -> None:
    """The count a person prints against, and the one that was wrong by four."""
    doc = PALM_DOC.read_text(encoding="utf-8")
    spec = AnthropomorphicPalmSpec()
    # Printed units, not kinematic segments. The two are equal in this hand and
    # that is a coincidence of the numbers, not a relation: a chain of n units
    # has n-1 joints between them, and the segment list counts from the knuckle.
    per_finger = spec.finger.link.joint_count + 1
    per_thumb = spec.thumb.link.joint_count + 1
    fingers = len(spec.row_finger_x_mm)

    # The row reads "1 個掌盤 + 15 個指節(四指各 3、拇指 3)" — the count of
    # fingers is written as a Chinese numeral and is prose, so the digits are
    # the plate, the total, and the two per-digit counts.
    cell = _row(doc, "零件")
    counts = [int(v) for v in re.findall(r"\d+", cell)]
    assert counts == [1, fingers * per_finger + per_thumb, per_finger, per_thumb], cell
    assert f"{_CHINESE[fingers]}指各" in cell, cell


def test_every_current_state_doc_quotes_the_same_reach() -> None:
    """The matrix and the task file quote the reach too, and drifted further.

    They still held 17.6 mm — a value one fix older than the README's 18.2 —
    which is the tell that this is a class and not an oversight: prose is
    copied forward, and each copy stops tracking at a different commit. Located
    by a stable label rather than by the number, so the check keeps working
    after the number moves again.
    """
    spec = AnthropomorphicPalmSpec()
    flat = dataclasses.replace(spec, thumb_opposition_deg=0.0, thumb_palmar_tilt_deg=0.0)
    expected = [spec.thumb_index_tip_gap_mm, spec.pinch_contact_mm, flat.thumb_index_tip_gap_mm]

    sources = {
        ROOT / "docs" / "hand-v3" / "v7-matrix.md": "兩指可達區域",
        ROOT / "docs" / "tasks" / "06_hand-v3.md": "對指可達性",
    }
    for path, label in sources.items():
        document = path.read_text(encoding="utf-8")
        lines = [line for line in document.splitlines() if label in line]
        assert len(lines) == 1, f"{path.name}: expected one line saying {label!r}"
        quoted = [float(v) for v in DECIMAL.findall(lines[0])]
        assert quoted[:3] == pytest.approx(expected, abs=0.1), f"{path.name}: {lines[0].strip()}"


def test_the_layout_the_docs_describe_is_the_layout_the_contract_declares() -> None:
    """How many parts are on the plate, and that the plate fits.

    The docs said five parts at 182.5 x 100.5 long after the layout became four
    at 242.0 x 103.5 — the margin against a 256 mm bed had gone from 73 mm to
    14 mm while the prose still described the roomy version.

    What this can check without Blender is the part count and that the quoted
    footprint is inside the declared bed. Whether the real layout fits is the
    contract's `layout_fits_bed`, measured twice on the real machine; this only
    stops the documents from describing a different plate than the one verified.
    """
    import json

    contract = json.loads(
        (ROOT / "scripts" / "verify" / "contracts" / "hand_v3.json").read_text(encoding="utf-8")
    )
    parts = contract["readiness"]["expected_selection_count"]
    bed = contract["readiness"]["max_footprint_mm"]
    spec = AnthropomorphicPalmSpec()
    assert parts == spec.finger.link.joint_count + 1 + 1, "the plate is one finger plus the palm"

    _CHINESE_COUNT = {4: "四", 5: "五"}
    for path, phrase in (
        (ROOT / "docs" / "hand-v3" / "v7-matrix.md", "佈局可印"),
        (ROOT / "docs" / "tasks" / "06_hand-v3.md", "列印佈局已交"),
    ):
        line = next(
            line for line in path.read_text(encoding="utf-8").splitlines() if phrase in line
        )
        assert f"{_CHINESE_COUNT[parts]}件一盤" in line, f"{path.name}: {line.strip()}"
        quoted = [float(v) for v in DECIMAL.findall(line)][:2]
        assert len(quoted) == 2 and all(
            side <= limit for side, limit in zip(quoted, bed, strict=True)
        ), f"{path.name} quotes a plate that does not fit the declared bed: {quoted} vs {bed}"

    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    plate = next(line for line in readme.splitlines() if "fits one plate" in line)
    sides = [float(v) for v in DECIMAL.findall(plate)][:2]
    assert all(side <= limit for side, limit in zip(sides, bed, strict=True)), plate


def test_the_finger_doc_quotes_the_finger_that_shipped() -> None:
    """The assembled height, which is the figure that moved when four became three."""
    doc = (ROOT / "docs" / "hand-v3" / "03-finger.md").read_text(encoding="utf-8")
    finger = binary_stl_metrics((PACKAGE / "finger_v3_mm.stl").read_bytes())

    line = next(line for line in doc.splitlines() if "整指高" in line)
    quoted = [float(v) for v in re.findall(r"整指高 \*{0,2}(\d+(?:\.\d+)?)", line)]
    assert len(quoted) == 1, f"the sentence should quote one height, found {quoted}: {line}"
    assert quoted[0] == pytest.approx(finger.dimensions_mm[2], abs=0.5), line


def test_the_population_the_docs_declare_is_the_prefix_the_generator_uses() -> None:
    """A declared population that matches nothing is the vacuous case itself.

    Five documents named the population `HH_V3_`; the generator namespaces its
    objects `HJ_`, and did from the first commit — chosen deliberately, because
    the default `HH_` collided with every earlier model and made the generator
    fail to clear its own output. So the line that exists to stop empty
    populations declared one.
    """
    import json
    import re

    prefix = re.search(
        r'run_generator\(build, prefix="([^"]+)"\)',
        (ROOT / "scripts" / "model_finger_v3.py").read_text(encoding="utf-8"),
    )
    assert prefix is not None, "the generator stopped naming its prefix where this can read it"
    namespace = prefix.group(1)

    contract = json.loads(
        (ROOT / "scripts" / "verify" / "contracts" / "hand_v3.json").read_text(encoding="utf-8")
    )
    assert contract["oracle"]["object_prefix"].startswith(namespace)

    declared = f"{namespace}V3_"
    for name in ("02-requirements", "v1-scope", "v5-fixtures", "v7-matrix", "09-glossary"):
        text = (ROOT / "docs" / "hand-v3" / f"{name}.md").read_text(encoding="utf-8")
        assert declared in text, f"{name} names a population other than {declared}"
        stale = re.findall(r"H[A-Z]_V3_", text)
        assert set(stale) <= {declared}, f"{name} still names {set(stale) - {declared}}"
