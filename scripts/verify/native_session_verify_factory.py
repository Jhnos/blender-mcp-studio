"""Repeatable native-session factory validation, isolated from the shared addon.

--current reads the same selected-model policy; it never chooses an archive or
accepts a caller's native filename. This does not replace shared-runtime MCP gates.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import plistlib
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CASES = (
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
)


@dataclass(frozen=True, slots=True)
class FactoryStep:
    phase: str
    case: str = "success"
    blend: str | None = None

    @property
    def label(self) -> str:
        return self.case if self.phase == "exercise" else self.phase

    def command(self, blender: Path, work: Path) -> list[str]:
        return [
            str(blender),
            "--background",
            "--factory-startup",
            "--disable-autoexec",
            *([str(work / self.blend)] if self.blend else []),
            "--python-exit-code",
            "1",
            "--python",
            str(ROOT / "scripts/verify/native_scene_session_fixture.py"),
            "--",
            "--phase",
            self.phase,
            "--case",
            self.case,
            "--work",
            str(work),
        ]


def fixture_steps(*, current: bool) -> tuple[FactoryStep, ...]:
    first = FactoryStep("record", blend="source.blend") if current else FactoryStep("source")
    return (
        first,
        *(
            FactoryStep(
                "exercise",
                case,
                "source.blend" if case == "current-file" else "active-original.blend",
            )
            for case in CASES
            if case != "multiple" or not current
        ),
        FactoryStep("reopen", blend="candidate-success.blend"),
    )


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def installed_blender(service: Path) -> Path:
    from src.infrastructure.narrowing import as_mapping, as_sequence

    with service.open("rb") as handle:
        document = as_mapping(plistlib.load(handle))
    arguments = as_sequence(document.get("ProgramArguments")) if document is not None else None
    if not arguments or not isinstance(arguments[0], str):
        raise ValueError("installed Blender executable is not declared")
    executable = Path(arguments[0])
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError("installed Blender executable is unavailable")
    return executable


async def current_source() -> tuple[Path, str, str]:
    from src.adapters.artifacts.native_source import FilesystemNativeSource
    from src.core.use_cases.artifact_catalog import ArtifactCatalog
    from src.infrastructure.config_loader import load_selected_model_spec
    from src.infrastructure.tools_config import load_tools_config

    tools = load_tools_config()
    catalog = ArtifactCatalog(
        tools.artifact_roots,
        tools.import_limits.max_stl_files,
        load_selected_model_spec,
        native_sources=FilesystemNativeSource(tools.artifact_roots, tools.import_limits),
    )
    spec, source = await catalog.native_source_for(catalog.current())
    return Path(spec.source.root_dir) / source.native.path, source.native.sha256, source.model_name


def verify(blender: Path, work: Path, *, current: bool) -> dict[str, object]:
    if not blender.is_file():
        raise ValueError("Blender executable is unavailable")
    original: Path | None = None
    expected_sha: str | None = None
    model = "synthetic-fixture"
    if current:
        original, expected_sha, model = asyncio.run(current_source())
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    if original is not None:
        shutil.copy2(original, work / "source.blend")
        if sha256(work / "source.blend") != expected_sha:
            raise ValueError("current native changed while creating the fixture snapshot")
        shutil.copy2(work / "source.blend", work / "active-original.blend")
    steps = fixture_steps(current=current)
    for step in steps:
        log = work / f"{step.label}.log"
        try:
            with log.open("w") as output:
                done = subprocess.run(
                    step.command(blender, work),
                    cwd=ROOT,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    timeout=120,
                    check=False,
                )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"factory fixture {step.label} timed out; see {log}") from exc
        if done.returncode:
            raise RuntimeError(f"factory fixture {step.label} failed; see {log}")
        if step.phase == "source":
            shutil.copy2(work / "source.blend", work / "active-original.blend")
    if original is not None and sha256(original) != expected_sha:
        raise ValueError("current native input changed during factory verification")
    cases = [step.case for step in steps if step.phase == "exercise"]
    proof: dict[str, object] = {
        "scope": "isolated factory lifecycle only; not public MCP or manufacturing qualification",
        "model": model,
        "current_source_sha256": expected_sha,
        "cases": cases,
        "reopen_passed": True,
        "original_file_unchanged": True,
        "source_objects": len(json.loads((work / "source-geometry.json").read_text())),
        "artifact_sha256": sha256(work / "candidate-success.blend"),
    }
    (work / "verification.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2))
    return proof


def verify_callback(blender: Path, work: Path) -> dict[str, object]:
    """Run the actual closed program, then independently reopen and check the same parts."""
    from scripts.verify.native_revision_verify_factory import complete_outputs, stage_current
    from src.adapters.artifacts.native_execution import NativeExecutionJournal
    from src.adapters.generation.native_runner import NativeRunner, build_native_program
    from src.core.domain.native_revision import NativeRevisionRequest

    work = work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    captured = asyncio.run(stage_current(work, NativeRevisionRequest("screen-clamp", 30)))
    body, execution = build_native_program(captured, work / "snapshots")
    journal = NativeExecutionJournal(execution)
    journal.reserve(uuid.uuid4().hex, body, captured.staged.source.native.sha256)
    program = NativeRunner.dispatch_program(body)
    with (work / "native-program.py").open("x") as handle:
        handle.write(program)
    snapshot = work / "snapshots" / captured.staged.directory
    shutil.copy2(snapshot / captured.staged.source.native.path, work / "original-scene.blend")
    assert sha256(work / "original-scene.blend") == captured.staged.source.native.sha256
    (work / "callback.json").write_text(
        json.dumps(
            {
                "execution": execution.relative_to(work).as_posix(),
                "target_angle_deg": captured.request.target_angle_deg,
            }
        )
    )
    script = ROOT / "scripts/verify/native_revision_verify_factory.py"
    for phase, blend in (
        ("callback", work / "original-scene.blend"),
        ("callback-reopen", execution / "candidate.blend"),
    ):
        with (work / (phase + ".log")).open("x") as log:
            subprocess.run(
                [
                    str(blender),
                    "--background",
                    "--factory-startup",
                    "--disable-autoexec",
                    "--threads",
                    "1",
                    str(blend),
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(script),
                    "--",
                    "--phase",
                    phase,
                    "--work",
                    str(work),
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=600,
                check=True,
            )
        if phase == "callback":
            terminal = journal.acknowledge()
            assert terminal["status"] == "completed" and terminal["restored"] is True
    assert sha256(work / "original-scene.blend") == captured.staged.source.native.sha256
    complete_outputs(work, captured, execution / "candidate.blend", execution / "stages")
    from src.infrastructure.narrowing import as_str_keyed_exact, required

    return required(
        json.loads((work / "verification.json").read_text()),
        as_str_keyed_exact,
        message="invalid callback qualification",
        error=ValueError,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--blender", type=Path)
    parser.add_argument("--work", type=Path)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--current", action="store_true")
    inputs.add_argument("--all", action="store_true")
    args = parser.parse_args()
    blender = args.blender or installed_blender(
        Path.home() / "Library/LaunchAgents/com.blender-mcp.blender.plist"
    )
    work = args.work or ROOT / "tmp" / ("native-session-" + uuid.uuid4().hex)
    if args.all:
        work.mkdir(parents=True, exist_ok=False)
        for current in (False, True):
            proof = verify(blender, work / ("current" if current else "synthetic"), current=current)
            print(json.dumps(proof, ensure_ascii=False), flush=True)
    else:
        proof = verify(blender, work, current=args.current)
        print(json.dumps(proof, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
