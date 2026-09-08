"""The three checks the matrix listed as TODO that never needed a printed part.

`notice_lists_every_external_source`, `render_set_present_and_uncropped` and
`results_template_marks_vacuous` sat as TODO beside the physical bench rows,
and were quietly treated as though they were waiting for the same thing. They
were not: every one of them is machine-decidable today, and one of them —
the renders — was the difference between a user being able to see the hand and
not.
"""

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "models" / "hand-v3"
RENDERS = ("finger_v3_assembly.png", "finger_v3_joint_detail.png", "finger_v3_print_layout.png")


def _declared_render_size() -> tuple[int, int]:
    """The resolution the presentation code sets, so the check moves with it."""
    source = (ROOT / "scripts" / "biaxial_hinge_presentation.py").read_text(encoding="utf-8")
    found = re.search(r"resolution_x,\s*scene\.render\.resolution_y\s*=\s*(\d+),\s*(\d+)", source)
    assert found is not None, "the presentation stopped declaring a resolution"
    return int(found.group(1)), int(found.group(2))


def _png_size(payload: bytes) -> tuple[int, int]:
    assert payload[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    width, height = struct.unpack(">II", payload[16:24])
    return width, height


def test_the_package_carries_the_pictures_a_person_judges_it_by() -> None:
    """VOC-4. A hand nobody can look at without Blender is not delivered.

    The renders existed only in the generator's scratch directory: handed over
    in conversation once and absent from the repository, so anyone cloning it
    got four STLs and no idea what they assemble into.
    """
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    declared = _declared_render_size()

    for name in RENDERS:
        payload = (PACKAGE / name).read_bytes()
        assert len(payload) > 100_000, name
        assert _png_size(payload) == declared, f"{name} is not the declared frame — cropped?"
        assert manifest["files"][name]["sha256"] == hashlib.sha256(payload).hexdigest(), name


def test_the_notice_names_every_source_the_prior_art_gives_a_licence() -> None:
    """VOC-3. An attribution file that misses a source is worse than none."""
    prior_art = (ROOT / "docs" / "hand-v3" / "01-prior-art.md").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")

    licensed = {
        row.split("|")[1].strip()
        for row in prior_art.splitlines()
        if row.startswith("|") and ("CC BY" in row or "MIT" in row)
    }
    assert len(licensed) >= 3, f"the prior-art licence table stopped parsing: {licensed}"
    missing = sorted(name for name in licensed if name not in notice)
    assert not missing, f"NOTICE does not name {missing}"
    assert "NonCommercial" in notice or "BY-NC" in notice


def test_no_inmoov_geometry_is_tracked_here() -> None:
    """The hard licence boundary: CC BY-NC would travel to the whole delivery.

    Checked against git's own index rather than the working tree, because an
    untracked file is exactly what this is allowed to be.
    """
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()

    geometry = {".stl", ".step", ".stp", ".obj", ".3mf", ".blend", ".sldprt", ".ipt"}
    offenders = [
        path
        for path in tracked
        if "inmoov" in path.lower() and Path(path).suffix.lower() in geometry
    ]
    assert not offenders, f"InMoov geometry is under version control: {offenders}"


def test_the_results_template_marks_what_has_not_been_measured() -> None:
    """VOC-5. An empty results table must read as empty, not as clean."""
    results = (ROOT / "docs" / "hand-v3" / "v8-results.md").read_text(encoding="utf-8")

    summary_rows = [
        row
        for row in results.splitlines()
        if row.startswith("| S") and re.search(r"\|\s*0\s*\|", row)
    ]
    assert summary_rows, "the summary table stopped declaring a population"
    for row in summary_rows:
        assert "vacuous" in row, f"a zero-population row that does not say so: {row.strip()}"
    assert "永遠不併入 pass" in results
