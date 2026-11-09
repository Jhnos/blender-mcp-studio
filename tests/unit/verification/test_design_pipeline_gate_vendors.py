"""Per-vendor design gate: contracts as data, manifest tool from the contract, the negatives.

The Bambu P2S contract and the Creality K1 Max contract run the same v78 deliverable; each names
its printer, material, slicer name/version/licence, and its negative controls as data.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.verify import design_gate_checks as gate

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "scripts" / "verify" / "contracts"


def load(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text("utf-8"))


P2S = load("archive/design_pipeline_v78.json")  # archived by main; still the P2S v2 spec
CURRENT = load("design_pipeline_current.json")
K1MAX = load("design_pipeline_v78_creality_k1max.json")
OUT = "print/x.3mf"


def manifest(tool: str, version: str, licence: str = "AGPL-3.0-only") -> dict:
    return {
        "files": [{"path": p} for p in (OUT, *P2S["expect"]["manifest_files"])],
        "tools": [{"name": tool, "version": version, "license": licence}],
    }


REPORT = {"stages": [{"name": "print", "outcome": "passed", "evidence": [OUT]}]}


def test_contracts_name_printer_material_and_tool() -> None:
    assert P2S["spec"]["spec_version"] == "2"
    assert P2S["spec"]["print_target"] == {"printer": "bambu-p2s-0.4", "material": "PLA"}
    assert K1MAX["spec"]["print_target"] == {"printer": "creality-k1-max-0.4", "material": "PLA"}
    # the current-selection contract carries no spec, so it names its printer itself
    assert CURRENT["spec_version"] == "2" and "spec" not in CURRENT
    assert CURRENT["print_target"] == {"printer": "bambu-p2s-0.4", "material": "PLA"}
    assert K1MAX["spec"]["source"] == P2S["spec"]["source"]
    assert K1MAX["expect"]["stl_count"] == 69 and K1MAX["expect"]["plates"] == 1
    assert (P2S["expect"]["slicer_tool"], P2S["expect"]["slicer_version"]) == (
        "bambu-studio",
        "02.08.02.61",
    )
    assert (K1MAX["expect"]["slicer_tool"], K1MAX["expect"]["slicer_version"]) == (
        "orcaslicer",
        "2.4.2",
    )
    assert K1MAX["negative_controls"]["plate_fit"]["printer"] == "creality-k1c-0.4"
    assert "plate_fit" not in P2S["negative_controls"]
    assert P2S["negative_controls"]["material"]["material"] == "PETG"
    assert K1MAX["negative_controls"]["material"]["material"] == "PETG"


def test_gate_asserts_tool_from_contract() -> None:
    for contract, other in ((P2S, K1MAX), (K1MAX, P2S)):
        expect = contract["expect"]
        ok = manifest(expect["slicer_tool"], expect["slicer_version"])
        assert gate.check_manifest(ok, REPORT, expect) == []
        wrong_tool = manifest(other["expect"]["slicer_tool"], expect["slicer_version"])
        assert gate.check_manifest(wrong_tool, REPORT, expect)
        failures = gate.check_manifest(manifest(expect["slicer_tool"], "0.0.1"), REPORT, expect)
        assert any(expect["slicer_version"] in f for f in failures), failures


def test_unpinned_current_contract_still_requires_tool_and_licence() -> None:
    expect = CURRENT["expect"]
    assert "slicer_version" not in expect  # main's current contract pins no version
    files = [{"path": p} for p in (OUT, *expect["manifest_files"])]
    good = {"files": files, "tools": [{"name": "bambu-studio", "license": "AGPL-3.0-only"}]}
    assert gate.check_manifest(good, REPORT, expect) == []
    wrong = {"files": files, "tools": [{"name": "orcaslicer", "license": "AGPL-3.0-only"}]}
    assert gate.check_manifest(wrong, REPORT, expect)
    unlicensed = {"files": files, "tools": [{"name": "bambu-studio", "license": "MIT"}]}
    assert gate.check_manifest(unlicensed, REPORT, expect)


def test_current_selection_must_resolve_to_the_contract_target() -> None:
    want = CURRENT["print_target"]
    selected = json.loads((ROOT / "models" / "lab-station" / "model-spec.json").read_text("utf-8"))
    assert gate.check_selected_target(selected, want) == []  # v1 "bambu-p2s" -> catalog id
    v1 = {"spec_version": "1", "name": "n", "source": {"root_dir": "r"}}
    unnamed = gate.check_selected_target(v1, want)
    assert unnamed and "printer, material" in unnamed[0]  # never the legacy machine
    k1max = {**v1, "print_target": {"printer": "creality-k1-max-0.4", "material": "PLA"}}
    (other,) = gate.check_selected_target(k1max, want)
    assert "creality-k1-max-0.4" in other and "bambu-p2s-0.4" in other


def _entry(printer: str) -> dict:
    return {"id": printer, "materials": ["PLA", "ABS"]}


def test_gate_fails_when_contract_printer_unavailable() -> None:
    listing = {
        "printers": [_entry("bambu-p2s-0.4")],
        "unavailable": [
            {
                "id": "creality-k1-max-0.4",
                "reason": "OrcaSlicer missing",
                "install_hint": "Install OrcaSlicer",
            }
        ],
    }
    assert gate.check_printer_listed(listing, "bambu-p2s-0.4") == []
    failures = gate.check_printer_listed(listing, "creality-k1-max-0.4")
    assert len(failures) == 1
    assert "OrcaSlicer missing" in failures[0] and "Install OrcaSlicer" in failures[0]
    unknown = gate.check_printer_listed({"printers": [], "unavailable": []}, "x-1")
    assert unknown and "x-1" in unknown[0]


def plate_fit_report(outcome: str, message: str) -> dict:
    return {"stages": [{"name": "print", "outcome": outcome, "message": message}]}


def test_k1c_plate_fit_negative_message_check() -> None:
    needles = K1MAX["negative_controls"]["plate_fit"]["message_contains"]
    assert needles == ["does not fit creality-k1c-0.4", "220×220"]
    good = plate_fit_report(
        "failed",
        "layout 241×241 mm does not fit creality-k1c-0.4 printable area 220×220 mm; "
        "choose a larger printer or re-lay out the plate",
    )
    assert gate.check_plate_fit_negative(good, needles) == []
    assert gate.check_plate_fit_negative(plate_fit_report("passed", "ok"), needles)
    wrong_bed = plate_fit_report("failed", "does not fit creality-k1c-0.4 printable area 300×300")
    assert any("220×220" in f for f in gate.check_plate_fit_negative(wrong_bed, needles))
    assert gate.check_plate_fit_negative({"stages": []}, needles)


def test_material_negative_rejected_at_submit() -> None:
    allowed = ["PLA", "ABS"]
    good = "unsupported print_target.material 'PETG' for bambu-p2s-0.4; allowed: PLA, ABS"
    assert gate.check_material_rejection(good, "PETG", allowed) == []
    assert gate.check_material_rejection(None, "PETG", allowed)  # accepted: a job was created
    assert gate.check_material_rejection("boom", "PETG", allowed)
    no_list = "unsupported print_target.material 'PETG' for bambu-p2s-0.4"
    assert gate.check_material_rejection(no_list, "PETG", allowed)


def test_ci_runs_both_vendor_gates() -> None:
    ci = (ROOT / "scripts" / "ci.sh").read_text().splitlines()
    lines = [t for t in ci if "design_pipeline_verify_real.py" in t]
    assert len(lines) == 2 and all("_run hard" in t for t in lines)
    assert "Bambu P2S via Bambu Studio" in lines[0]
    assert lines[0].endswith("design_pipeline_current.json")  # main: P2S gate = current selection
    assert "Creality K1 Max via OrcaSlicer" in lines[1]
    assert lines[1].endswith("design_pipeline_v78_creality_k1max.json")
    assert ci.index(lines[0]) + 1 == ci.index(lines[1])
