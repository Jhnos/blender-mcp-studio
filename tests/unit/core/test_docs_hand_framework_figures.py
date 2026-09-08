"""The hand-framework tree is held to the same rules that caught V3 drifting.

V3's documents drifted three ways in one week: figures quoted from a build that
no longer existed, a population prefix that matched nothing, and a Verified-by
column where 21 of 22 names pointed at nothing. Each got a guard after the
fact. This tree gets all of them before its first line of prose, so the
campaign starts red on an empty directory and goes green only when the
documents say what the specs and the repository actually contain.

Every assertion here reads a document and compares it to a source that can
answer: the domain specs for computed figures, the repository for named
verifiers, the generator for the population prefix. A number or a name in a
table is a claim; this is the check.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.core.domain.compact_link import CompactHingeLinkSpec
from src.core.domain.finger_v3 import SingleTendonFingerSpec
from src.core.domain.palm_v3 import AnthropomorphicPalmSpec

ROOT = Path(__file__).resolve().parents[3]
TREE = ROOT / "docs" / "hand-framework"
MATRIX = TREE / "02-requirements.md"
TIERS = "static|unit|integration|artifact|differential|monitor"
DECIMAL = re.compile(r"\d+\.\d+")

DESIGN_FILES = (
    "00-context",
    "01-boundaries",
    "02-requirements",
    "03-domain-spec",
    "04-plans",
    "05-execution",
    "06-naming",
    "07-contracts",
    "08-instances",
    "09-glossary",
)
PLAN_FILES = (
    "v0-INDEX",
    "v1-scope",
    "v2-hypotheses",
    "v3-failure-modes",
    "v4-scenarios",
    "v5-fixtures",
    "v6-scripts",
    "v7-matrix",
    "v8-results",
    "v9-references",
)


def _tree_file(name: str) -> str:
    path = TREE / f"{name}.md"
    assert path.is_file(), f"docs/hand-framework/{name}.md does not exist"
    return path.read_text(encoding="utf-8")


def test_the_tree_is_complete_and_flat() -> None:
    """Twenty-one files, one topic each, no subdirectory.

    Flat because the orphan gate walks two hops from docs/README.md and a
    subdirectory is the third hop. Complete because a navigation table that
    names a file which does not exist is a broken promise; this states the
    shape once, up front, instead of discovering it link by link.
    """
    assert TREE.is_dir(), "docs/hand-framework/ does not exist"
    present = {path.stem for path in TREE.glob("*.md")}
    expected = {"README", *DESIGN_FILES, *PLAN_FILES}
    missing = sorted(expected - present)
    assert not missing, f"the tree is missing {missing}"
    assert not [p.name for p in TREE.iterdir() if p.is_dir()], "the tree must stay flat"


def test_every_file_navigates_back_to_the_tree_root() -> None:
    """The header line is how a reader with one file open finds the others."""
    for name in (*DESIGN_FILES, *PLAN_FILES):
        text = _tree_file(name)
        header = next((line for line in text.splitlines() if line.startswith("> 回導航")), "")
        assert "[[hand-framework" in header, f"{name} has no navigation header"


def test_the_population_the_framework_declares_is_the_prefix_the_generator_uses() -> None:
    """A declared population that matches nothing is the vacuous case itself.

    The same guard V3 needed after five of its documents named `HH_V3_` while
    the generator namespaced `HJ_`. The prefix is read from the generator and
    never typed here, so the two cannot drift apart without this going red.
    """
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
    for name in ("02-requirements", "v1-scope", "v5-fixtures", "v7-matrix", "06-naming"):
        text = _tree_file(name)
        assert declared in text, f"{name} names a population other than {declared}"
        stale = re.findall(r"H[A-Z]_V3_", text)
        assert set(stale) <= {declared}, f"{name} still names {set(stale) - {declared}}"


def test_every_verifier_the_matrix_names_can_be_found() -> None:
    """A dead link in the shape of a live one is worse than no link: it looks safe.

    `trace_check.py` validates `tier:ref` shape only. This resolves each ref
    against the repository: a test function, an evidence name, a file. Unbuilt
    checks carry `TODO_` and are exempt, because visible is the point.
    """
    matrix = _tree_file("02-requirements")
    refs = set(re.findall(rf"(?:{TIERS}):([A-Za-z0-9_./|-]+)", matrix))
    assert len(refs) > 15, f"the matrix stopped naming verifiers: {refs}"

    haystack = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for tree in ("tests", "scripts", "src")
        for path in (ROOT / tree).rglob("*")
        if path.is_file() and path.suffix in {".py", ".json", ".sh"}
    )
    names = {path.name for path in ROOT.rglob("*") if path.is_file()}
    names |= {path.stem for path in ROOT.rglob("*.py")}

    missing = sorted(
        ref
        for ref in refs
        if not ref.startswith("TODO_") and ref not in haystack and ref not in names
    )
    assert not missing, f"the matrix names verifiers that do not exist: {missing}"


def test_the_matrix_does_not_hide_an_unbuilt_check_behind_a_real_looking_name() -> None:
    """A `TODO_` ref that already exists in code is a row lying the other way."""
    matrix = _tree_file("02-requirements")
    todos = {ref for ref in re.findall(r"(?:\w+):(TODO_[A-Za-z0-9_]+)", matrix)}
    for ref in todos:
        found = [
            path
            for tree in ("tests", "src", "scripts")
            for path in (ROOT / tree).rglob("*.py")
            if ref in path.read_text(encoding="utf-8", errors="ignore")
        ]
        assert not found, f"{ref} is marked TODO but exists in {found}"


def test_the_instance_table_quotes_what_the_specs_compute() -> None:
    """Every figure in the instance table is derived from a spec, not typed.

    The V3 package README once quoted a palm height, a part count and a thumb
    reach from a build that had stopped existing. The instance table is the
    same kind of document, a row of numbers a person plans by, so each number
    is recomputed from the spec that owns it. Rows are located by the slug of
    the instance, never by a number, so the check survives the numbers moving.
    """
    doc = _tree_file("08-instances")

    from src.core.domain.hand_instances import HAND_INSTANCES

    # From the registry, not rebuilt here: a spec typed a second time in a test
    # is the drift this guard exists to catch.
    for slug in ("hand-v3", "hand-compact"):
        finger = HAND_INSTANCES[slug].palm.finger
        link = finger.link
        rows = [line for line in doc.splitlines() if line.startswith("|") and f"`{slug}`" in line]
        assert len(rows) == 1, f"expected one instance row for {slug}, found {len(rows)}"
        quoted = [float(value) for value in DECIMAL.findall(rows[0])]
        reach = (
            2.0 * link.joint_center_offset_mm
            + link.unit_pitch_mm
            + link.lug_outer_diameter_mm / 2.0
        )
        expected = [
            link.body_length_mm,
            link.body_width_mm,
            link.body_depth_mm,
            finger.smallest_usable_moment_arm_mm,
            finger.largest_usable_moment_arm_mm,
            finger.largest_usable_moment_arm_mm / finger.smallest_usable_moment_arm_mm,
            reach,
            finger.adjacent_body_clearance_mm,
        ]
        assert quoted[: len(expected)] == pytest.approx(expected, abs=0.01), (
            f"{slug}: the table says {quoted[: len(expected)]}, the spec computes "
            f"{[round(v, 2) for v in expected]}"
        )


def test_the_results_template_marks_each_instance() -> None:
    """VOC-3: a reader learns what each registered instance passed from v8 alone.

    Exactly one status row per slug, and it says PASS or vacuous — never blank.
    """
    from src.core.domain.hand_instances import HAND_INSTANCES

    doc = (TREE / "v8-results.md").read_text(encoding="utf-8")
    for slug in HAND_INSTANCES:
        rows = [line for line in doc.splitlines() if line.startswith("|") and f"`{slug}`" in line]
        assert len(rows) == 1, f"v8-results must carry exactly one status row for {slug}"
        assert "PASS" in rows[0] or "vacuous" in rows[0], rows[0]
