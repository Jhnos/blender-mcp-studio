"""The design pipeline real gate: its verdict rules, polling, prerequisites and ci.sh wiring.

The gate itself needs the deployed service; these tests pin the pure rules on fake reports so a
gate that cannot fail (or fails unreadably) is caught without Blender or the slicer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.verify import design_gate_checks as gate

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / "scripts/verify/contracts/design_pipeline_v78.json").read_text())
EXPECT = CONTRACT["expect"]
OUT_3MF = "print/整機69件-單盤排版-v78-P2S-PLA.3mf"
BAD_REL = "STL/列印零件/x.stl"


def good_report() -> dict:
    def stage(name, outcome, metrics=(), evidence=(), message=""):
        return {
            "name": name,
            "outcome": outcome,
            "metrics": [list(m) for m in metrics],
            "evidence": list(evidence),
            "message": message,
        }

    return {
        "run_id": "r1",
        "spec_name": "lab-station-v78",
        "passed": True,
        "stages": [
            stage("import", "passed", [("stl_count", "69"), ("skipped", "0")], ["a.stl"]),
            stage("geometry", "passed", [("checked", "69"), ("failing", "0")]),
            stage("mechanism", "not_applicable", message="no mechanism suites declared"),
            stage("print", "passed", [("return_code", "0")], [OUT_3MF, "print/slicer.log"]),
            stage("package", "passed", [("files", "9")], ["manifest.json"]),
        ],
    }


def good_manifest() -> dict:
    paths = [OUT_3MF, *EXPECT["manifest_files"]]
    return {
        "files": [{"path": p, "sha256": "0" * 64, "bytes": 1, "triangles": None} for p in paths],
        "tools": [
            {
                "name": "bambu-studio",
                "version": "2.0",
                "license": "AGPL-3.0-only",
                "invocation": "subprocess",
            }
        ],
    }


def stage_of(report: dict, name: str) -> dict:
    return next(s for s in report["stages"] if s["name"] == name)


def test_good_report_has_no_failures() -> None:
    assert gate.check_report(good_report(), EXPECT) == []


@pytest.mark.parametrize(
    "stage,outcome",
    [
        ("import", "failed"),
        ("geometry", "failed"),
        ("mechanism", "passed"),
        ("mechanism", "failed"),
        ("print", "failed"),
        ("package", "failed"),
        ("package", "not_applicable"),
    ],
)
def test_every_stage_outcome_rule(stage: str, outcome: str) -> None:
    report = good_report()
    stage_of(report, stage)["outcome"] = outcome
    failures = gate.check_report(report, EXPECT)
    assert any(stage in f and outcome in f for f in failures), failures


def test_missing_stage_is_named() -> None:
    report = good_report()
    report["stages"] = [s for s in report["stages"] if s["name"] != "package"]
    assert any("package" in f for f in gate.check_report(report, EXPECT))


def test_overall_failed_flag_fails() -> None:
    report = good_report()
    report["passed"] = False
    assert any("passed" in f for f in gate.check_report(report, EXPECT))


@pytest.mark.parametrize(
    "stage,key,value",
    [
        ("import", "stl_count", "113"),
        ("import", "skipped", "2"),
        ("geometry", "checked", "68"),
        ("geometry", "failing", "1"),
    ],
)
def test_wrong_metric_names_expected_and_actual(stage: str, key: str, value: str) -> None:
    report = good_report()
    metrics = dict(map(tuple, stage_of(report, stage)["metrics"]))
    metrics[key] = value
    stage_of(report, stage)["metrics"] = [list(p) for p in metrics.items()]
    failures = gate.check_report(report, EXPECT)
    assert any(key in f and value in f for f in failures), failures


def test_missing_metric_fails() -> None:
    report = good_report()
    stage_of(report, "import")["metrics"] = []
    assert any("stl_count" in f for f in gate.check_report(report, EXPECT))


@pytest.mark.parametrize("stage", ["print", "package"])
def test_report_without_evidence_paths_fails(stage: str) -> None:
    report = good_report()
    stage_of(report, stage)["evidence"] = []
    assert any(stage in f and "evidence" in f for f in gate.check_report(report, EXPECT))


def test_print_evidence_without_3mf_fails() -> None:
    report = good_report()
    stage_of(report, "print")["evidence"] = ["print/slicer.log"]
    assert any(".3mf" in f for f in gate.check_report(report, EXPECT))


def test_output_3mf_is_taken_from_print_evidence() -> None:
    assert gate.output_3mf(good_report()) == OUT_3MF


def plate_names(n: int) -> list[str]:
    names = ["[Content_Types].xml", "Metadata/model_settings.config", "Metadata/plate_1.json"]
    for i in range(1, n + 1):
        names += [f"Metadata/plate_{i}.gcode", f"Metadata/plate_{i}.gcode.md5"]
    return names


def test_one_plate_passes_and_md5_is_not_a_plate() -> None:
    assert gate.count_plates(plate_names(1)) == 1
    assert gate.check_plates(plate_names(1), 1) == []


@pytest.mark.parametrize("n", [0, 2])
def test_wrong_plate_count_fails(n: int) -> None:
    failures = gate.check_plates(plate_names(n), 1)
    assert failures and str(n) in failures[0] and "plate" in failures[0]


def test_good_manifest_has_no_failures() -> None:
    assert gate.check_manifest(good_manifest(), good_report(), EXPECT) == []


def test_missing_manifest_entry_is_named() -> None:
    manifest = good_manifest()
    manifest["files"] = [f for f in manifest["files"] if f["path"] != "print/process.json"]
    failures = gate.check_manifest(manifest, good_report(), EXPECT)
    assert any("print/process.json" in f for f in failures)


def test_missing_output_3mf_in_manifest_is_named() -> None:
    manifest = good_manifest()
    manifest["files"] = [f for f in manifest["files"] if f["path"] != OUT_3MF]
    assert any(OUT_3MF in f for f in gate.check_manifest(manifest, good_report(), EXPECT))


@pytest.mark.parametrize("tools", [[], [{"name": "bambu-studio", "license": "MIT"}]])
def test_missing_or_wrong_licence_tool_entry_fails(tools: list) -> None:
    manifest = good_manifest()
    manifest["tools"] = tools
    failures = gate.check_manifest(manifest, good_report(), EXPECT)
    assert any("AGPL-3.0-only" in f for f in failures)


@pytest.mark.parametrize(
    "leak", ["/Users/someone/x.stl", "/private/tmp/y", "/var/folders/ab/cd", "/home/dev/file"]
)
def test_absolute_host_path_anywhere_is_a_leak(leak: str) -> None:
    report = good_report()
    stage_of(report, "print")["message"] = f"failed at {leak}"
    leaks = gate.find_path_leaks({"report": report, "manifest": good_manifest()}, home="/Users/me")
    assert leaks and leak in leaks[0]


def test_home_directory_outside_marker_list_is_a_leak() -> None:
    assert gate.find_path_leaks({"m": {"files": ["/opt/me/x"]}}, home="/opt/me")


def test_clean_documents_have_no_leak() -> None:
    docs = {"report": good_report(), "manifest": good_manifest()}
    assert gate.find_path_leaks(docs, home="/Users/me") == []


def negative_report(message: str, outcome: str = "failed") -> dict:
    geometry = {
        "name": "geometry",
        "outcome": outcome,
        "metrics": [["checked", "69"], ["failing", "1"]],
        "evidence": [],
        "message": message,
    }
    return {"passed": False, "stages": [geometry]}


def test_negative_control_names_the_broken_file() -> None:
    assert gate.check_negative(negative_report(f"{BAD_REL}: bad header"), BAD_REL) == []


def test_negative_control_fails_when_geometry_passed() -> None:
    failures = gate.check_negative(negative_report("", outcome="passed"), BAD_REL)
    assert any("geometry" in f and "failed" in f for f in failures)


def test_negative_control_fails_when_another_file_is_named() -> None:
    failures = gate.check_negative(negative_report("STL/列印零件/y.stl: bad"), BAD_REL)
    assert any("x.stl" in f for f in failures)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_poll_returns_the_terminal_job_and_prints_heartbeats() -> None:
    clock = FakeClock()
    states = iter(["queued", "running", "running", "done"])
    lines: list[str] = []

    def status(_: str) -> dict:
        return {"status": next(states), "stage": "print", "error": None}

    job = gate.poll_job(
        status, "j1", budget_s=1000, pause_s=10, clock=clock, sleep=clock.sleep, say=lines.append
    )
    assert job["status"] == "done"
    assert len(lines) == 4 and all("j1" in line and "print" in line for line in lines)


def test_poll_budget_exhaustion_names_job_stage_and_budget() -> None:
    clock = FakeClock()

    def status(_: str) -> dict:
        return {"status": "running", "stage": "print", "error": None}

    with pytest.raises(gate.GateError, match=r"j1.*print.*100"):
        gate.poll_job(
            status,
            "j1",
            budget_s=100,
            pause_s=30,
            clock=clock,
            sleep=clock.sleep,
            say=lambda _: None,
        )
    assert clock.now >= 100


def test_failed_job_is_terminal_not_a_hang() -> None:
    job = gate.poll_job(
        lambda _: {"status": "failed", "stage": "geometry", "error": "boom"},
        "j2",
        budget_s=10,
        pause_s=1,
        clock=FakeClock(),
        sleep=lambda _: None,
        say=lambda _: None,
    )
    assert job["status"] == "failed"


def test_poll_budget_is_derived_from_the_slicer_timeout() -> None:
    from src.adapters.slicing.bambu_studio_cli import SLICE_TIMEOUT_S

    assert gate.poll_budget_s() == SLICE_TIMEOUT_S + 300


def test_absent_deliverable_is_a_failure_naming_the_directory(tmp_path: Path) -> None:
    failures = gate.check_deliverable(tmp_path, "雙上臂四點梯形-v78")
    assert failures == ["deliverable not present on this host: 雙上臂四點梯形-v78"]
    (tmp_path / "雙上臂四點梯形-v78").mkdir()
    assert gate.check_deliverable(tmp_path, "雙上臂四點梯形-v78") == []


def test_unavailable_slicer_is_a_failure_with_the_install_hint() -> None:
    rows = [{"name": "bambu-studio", "available": False, "install_hint": "Install BambuStudio.app"}]
    failures = gate.check_slicer(rows, "bambu-studio")
    assert failures and "Install BambuStudio.app" in failures[0]
    assert gate.check_slicer([{**rows[0], "available": True}], "bambu-studio") == []
    assert gate.check_slicer([], "bambu-studio")


def test_unreachable_endpoint_message_names_the_url_and_env() -> None:
    message = gate.unreachable_message("https://h/blender/mcp", OSError("refused"))
    assert "https://h/blender/mcp" in message and "BLENDER_MCP_PUBLIC_BASE_URL" in message


def test_truncated_header_keeps_exactly_the_requested_bytes(tmp_path: Path) -> None:
    source = tmp_path / "a.stl"
    source.write_bytes(bytes(range(200)))
    gate.truncate_header(source, 40)
    assert source.read_bytes() == bytes(range(40))


def test_contract_is_data() -> None:
    assert CONTRACT["spec"]["source"]["stl_glob"] == "STL/列印零件/*.stl"
    assert CONTRACT["spec"]["mechanism"]["suites"] == []
    assert EXPECT["stl_count"] == 69 and EXPECT["plates"] == 1


def test_real_ci_runs_the_design_pipeline_gate_after_the_determinism_probe() -> None:
    ci = (ROOT / "scripts" / "ci.sh").read_text()
    probe = ci.index("hand-compact build determinism within budget")
    line = ci.index(
        "scripts/verify/design_pipeline_verify_real.py "
        "scripts/verify/contracts/design_pipeline_v78.json"
    )
    assert probe < line
    wired = next(t for t in ci.splitlines() if "design_pipeline_verify_real.py" in t)
    assert "_run hard" in wired


def test_gitignore_keeps_deliverables_out_of_the_repo() -> None:
    assert "/雙上臂四點梯形-*" in (ROOT / ".gitignore").read_text().splitlines()
