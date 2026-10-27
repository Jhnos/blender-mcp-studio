"""Factory lifecycle validation has one fixed, portable, non-server command plan."""

import plistlib
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
    }
    steps = fixture_steps(current=False)
    assert steps[0].phase == "source" and steps[-1].phase == "reopen"
    assert {step.case for step in steps if step.phase == "exercise"} == set(CASES)
    current = fixture_steps(current=True)
    assert current[0].phase == "record"
    assert "multiple" not in {step.case for step in current}
    assert current[-1].blend == "candidate-success.blend"


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
