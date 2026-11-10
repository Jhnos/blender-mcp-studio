"""Factory lifecycle validation has one fixed, portable, non-server command plan."""

import hashlib
import json
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.verify.native_session_verify_factory import CASES, fixture_steps


def test_factory_plan_covers_every_case_and_reopens_the_written_file():
    assert set(CASES) == {
        "success",
        "operation-failure",
        "crosslink",
        "existing",
        "hash",
        "multiple",
        "extra",
        "rename",
        "replace",
        "original-driver",
        "original-ui",
        "late-output",
        "pending-failure",
        "source-overwrite",
        "current-file",
        "malformed",
        "original-linked",
        "edit-mode",
        "primitive-context",
    }
    steps = fixture_steps(current=False)
    assert steps[0].phase == "source" and steps[-1].phase == "reopen"
    assert {step.case for step in steps if step.phase == "exercise"} == set(CASES)
    current = fixture_steps(current=True)
    assert current[0].phase == "record"
    assert "multiple" not in {step.case for step in current}
    assert current[-1].blend == "candidate-success.blend"


def test_current_preview_uses_the_same_native_snapshot_as_the_geometry_record():
    current = fixture_steps(current=True)
    record, preview = current[:2]
    assert record.phase == "record"
    assert preview.phase == "preview" and preview.blend == record.blend
    assert all(step.phase != "preview" for step in fixture_steps(current=False))


def test_every_worker_is_factory_background_and_disables_file_auto_execution(tmp_path):
    for step in fixture_steps(current=False):
        command = step.command(Path("/opt/blender"), tmp_path)
        assert command[:4] == [
            "/opt/blender",
            "--background",
            "--factory-startup",
            "--disable-autoexec",
        ]
        assert command[command.index("--python-exit-code") + 1] == "1"
        assert "--python-expr" not in command and "--addons" not in command
        assert command[command.index("--work") + 1] == str(tmp_path)


def test_active_file_negative_uses_the_source_and_other_cases_use_a_distinct_original():
    for step in fixture_steps(current=True):
        if step.phase == "exercise":
            assert step.blend == (
                "source.blend" if step.case == "current-file" else "active-original.blend"
            )


def test_installed_executable_is_read_from_derived_service_state_without_a_path_fallback(tmp_path):
    from scripts.verify.native_session_verify_factory import installed_blender

    executable = tmp_path / "Blender"
    executable.touch()
    service = tmp_path / "service.plist"
    service.write_bytes(plistlib.dumps({"ProgramArguments": [str(executable), "--python"]}))
    assert installed_blender(service) == executable
    for value in ({}, {"ProgramArguments": []}, {"ProgramArguments": [42]}):
        service.write_bytes(plistlib.dumps(value))
        with pytest.raises(ValueError, match="executable"):
            installed_blender(service)


def test_real_ci_runs_both_factory_inputs_without_classifying_them_as_public_acceptance():
    root = Path(__file__).resolve().parents[3]
    real = (root / "scripts/ci.sh").read_text().split("if (( REAL )); then", 1)[1]
    assert '"$PY" scripts/verify/native_session_verify_factory.py --all' in real
    assert "isolated native scene lifetime (not public revision qualification)" in real


def test_current_source_recipe_gate_runs_positive_and_each_discriminating_control():
    from scripts.verify.native_revision_verify_factory import recipe_cases

    assert recipe_cases() == ("none", "skip-cut", "skip-stop", "stale-canonical")
    root = Path(__file__).resolve().parents[3]
    real = (root / "scripts/ci.sh").read_text().split("if (( REAL )); then", 1)[1]
    assert '"$PY" scripts/verify/native_revision_verify_factory.py --all' in real
    assert "isolated current-source screen revision and full STL" in real


def test_real_ci_checks_cup_extraction_from_the_current_factory_source():
    root = Path(__file__).resolve().parents[3]
    real = (root / "scripts/ci.sh").read_text().split("if (( REAL )); then", 1)[1]
    gate = '"$PY" scripts/verify/workstation_cup_verify_factory.py'
    assert gate in real
    assert real.index(gate) < real.index("workstation prototype fixture (research)")


def test_cup_extraction_rejects_an_old_source_and_an_incomplete_display_sweep():
    from scripts.verify.workstation_cup_verify_factory import assess

    with pytest.raises(ValueError, match="different native model"):
        assess({"native_sha256": "old"}, "current")
    with pytest.raises(ValueError, match="display sweep is incomplete"):
        assess({"native_sha256": "current", "parked": {}, "screen_frames": [{}]}, "current")


@pytest.mark.parametrize("stale", [False, True])
def test_cup_gate_uses_the_manifest_of_an_explicit_candidate(tmp_path, monkeypatch, stale):
    from scripts.verify import workstation_cup_verify_factory as cup
    from src.core.domain.native_revision import NativeSourceError

    bundle = tmp_path / "candidate"
    bundle.mkdir()
    assets = {"review.blend": b"candidate", "part.stl": b"part", "plate.3mf": b"plate"}
    for name, data in assets.items():
        (bundle / name).write_bytes(data)
    (bundle / "SHA256.json").write_text(
        json.dumps({name: hashlib.sha256(data).hexdigest() for name, data in assets.items()})
    )
    spec = tmp_path / "candidate.json"
    spec.write_text(
        json.dumps(
            {
                "spec_version": "1",
                "name": "candidate",
                "source": {
                    "root_dir": bundle.name,
                    "stl_glob": "*.stl",
                    "project_3mf": "plate.3mf",
                },
            }
        )
    )
    work = tmp_path / "capture"
    monkeypatch.setenv("ARTIFACT_ROOTS", str(tmp_path))
    monkeypatch.setattr(
        sys, "argv", ["cup", "--spec", str(spec), "--work", str(work), "--blender", "/fake"]
    )
    monkeypatch.setattr(
        cup.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 1)
    )
    if stale:
        (bundle / "review.blend").write_bytes(b"older scene")
        with pytest.raises(NativeSourceError, match="checksum"):
            cup.main()
        assert not work.exists()
        return

    with pytest.raises(RuntimeError, match="Blender cup capture failed"):
        cup.main()
    assert (work / "source.blend").read_bytes() == assets["review.blend"]
    assert (work / "spec.json").read_bytes() == spec.read_bytes()


def test_native_recipe_covers_every_indexed_target_and_rejects_before_staging(tmp_path):
    from scripts.verify.native_revision_verify_factory import host, recipe_targets
    from src.core.domain.native_revision import NativeRevisionError

    assert recipe_targets() == (0, 15, 30, 45, 60)
    with pytest.raises(NativeRevisionError):
        host(tmp_path / "invalid", Path("/missing/blender"), target_angle_deg=1)
    assert not (tmp_path / "invalid").exists()


def test_all_native_cases_include_the_actual_durable_callback_and_reopen():
    root = Path(__file__).resolve().parents[3]
    source = (root / "scripts/verify/native_revision_verify_factory.py").read_text()
    all_cases = source.split("if args.all:", 1)[1].split("elif args.phase", 1)[0]
    assert 'verify_callback(blender, work / "callback")' in all_cases
    assert '"callback-reopen"' in source
