"""Current-source screen-recipe fixture; isolated file evidence, no public qualification.

The host stages the current catalog source. Blender performs geometry only; the
host interpreter runs the existing independent CGAL checker after every step.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.domain.native_revision import NativeRevisionRequest, PreparedNativeRevision

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


async def stage_current(work: Path, request: NativeRevisionRequest) -> PreparedNativeRevision:
    from src.adapters.artifacts.native_source import FilesystemNativeSource
    from src.adapters.artifacts.native_staging import FilesystemNativeStaging
    from src.core.use_cases.artifact_catalog import ArtifactCatalog
    from src.core.use_cases.native_revision import NativeRevisionService
    from src.infrastructure.config_loader import load_selected_model_spec
    from src.infrastructure.tools_config import load_tools_config

    tools = load_tools_config()
    reader = FilesystemNativeSource(tools.artifact_roots, tools.import_limits)
    catalog = ArtifactCatalog(
        tools.artifact_roots,
        tools.import_limits.max_stl_files,
        load_selected_model_spec,
        native_sources=reader,
    )
    prepared = await NativeRevisionService(
        catalog, FilesystemNativeStaging(reader, work / "snapshots")
    ).prepare_revision(uuid.uuid4().hex, request)
    return prepared


def recipe_cases() -> tuple[str, ...]:
    return ("none", "skip-cut", "skip-stop", "stale-canonical")


def recipe_targets() -> tuple[int, ...]:
    return (0, 15, 30, 45, 60)


def host(work: Path, blender: Path, control: str = "none", target_angle_deg: float = 0) -> None:
    from src.core.domain.native_revision import NativeRevisionRequest

    request = NativeRevisionRequest("screen-clamp", target_angle_deg)
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    (work / "stages").mkdir()
    captured = asyncio.run(stage_current(work, request))
    prepared = captured.staged
    canonical: dict[str, str] = {}
    for owner in ("LS_FIT_lcd_back", "LS_FIT_lid", "TE_pH_temp_three_point_wrist"):
        matching = [part for part in prepared.source.parts if Path(part.path).stem == owner]
        if len(matching) != 1:
            raise ValueError("current selection has missing or ambiguous canonical recipe parts")
        canonical[owner] = matching[0].path
    metadata = {
        "directory": prepared.directory,
        "native": asdict(prepared.source.native),
        "canonical": canonical,
        "source": asdict(prepared.source),
        "request": asdict(captured.request),
        "spec": asdict(captured.spec),
    }
    (work / "input.json").write_text(json.dumps(metadata))
    original = work / "original-scene.blend"
    shutil.copy2(work / "snapshots" / prepared.directory / prepared.source.native.path, original)
    assert digest(original) == prepared.source.native.sha256
    if control == "stale-canonical":
        snapshot = work / "snapshots" / prepared.directory
        path = snapshot / next(iter(canonical.values()))
        payload = path.read_bytes()
        path.write_bytes(b"tampered source".ljust(80, b" ") + payload[80:])
    for phase in ("worker", "reopen"):
        command = [
            str(blender),
            "--background",
            "--factory-startup",
            "--disable-autoexec",
            "--threads",
            "1",
        ]
        if phase == "reopen":
            command.append(str(work / "candidate.blend"))
        else:
            command.append(str(original))
        command += [
            "--python-exit-code",
            "1",
            "--python",
            str(Path(__file__).resolve()),
            "--",
            "--phase",
            phase,
            "--work",
            str(work),
            "--host-python",
            sys.executable,
            "--control",
            control,
        ]
        with (work / f"{phase}.log").open("x") as log:
            completed = subprocess.run(
                command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=300, check=False
            )
        if control != "none":
            cleanup = json.loads((work / "cleanup.json").read_text())
            assert completed.returncode != 0, "skipped material operation was incorrectly accepted"
            assert cleanup["original_state_equal"] and not cleanup["candidate_published"]
            if control == "stale-canonical":
                assert not cleanup["stages_completed"]
                assert (
                    json.loads((work / "input-rejected.json").read_text())["reason"]
                    == "canonical-checksum-mismatch"
                )
            else:
                rejected = list((work / "stages").glob("*.rejected.json"))
                assert len(rejected) == 1
                refusal = json.loads(rejected[0].read_text())
                assert refusal["stage"] == (
                    "operation-0" if control == "skip-cut" else "operation-1"
                )
                assert refusal["reason"] == "material-change-missing", refusal
            print(
                json.dumps(
                    {
                        "control": control,
                        "rejected": True,
                        "original_state_equal": True,
                        "candidate_published": False,
                    }
                )
            )
            (work / "verification.json").write_text(
                json.dumps(
                    {
                        "control": control,
                        "passed": True,
                        "source_sha256": prepared.source.native.sha256,
                        "original_state_equal": True,
                        "candidate_published": False,
                    }
                )
            )
            return
        completed.check_returncode()
    complete_outputs(work, captured, work / "candidate.blend", work / "stages")


def complete_outputs(
    work: Path, captured: PreparedNativeRevision, native: Path, stages: Path
) -> None:
    """One complete-STL and same-template check for both direct and callback fixtures."""
    prepared = captured.staged
    from src.adapters.artifacts.native_stl_writer import NativeStlWriter
    from src.adapters.mesh.trimesh_cgal_integrity import TrimeshCgalIntegrity
    from src.core.domain.native_revision import SourceArtifact
    from src.infrastructure.tools_config import load_tools_config

    final_payload = list(stages.glob("*-final-all.json"))
    assert len(final_payload) == 1
    surfaces = json.loads(final_payload[0].read_text())["surfaces"]
    changed = {owner: surfaces[owner] for owner in ("LS_FIT_lcd_back", "LS_FIT_lid")}
    native_receipt = SourceArtifact(native.name, digest(native), native.stat().st_size)
    tools = load_tools_config()
    writer = NativeStlWriter(TrimeshCgalIntegrity(), tools.import_limits)
    stls = asyncio.run(
        writer.write(
            prepared.source,
            work / "snapshots" / prepared.directory,
            native,
            native_receipt,
            changed,
            tuple(changed),
            work / "complete-stl",
        )
    )
    from scripts.verify.native_revision_checks import check_plate_bindings

    bindings = check_plate_bindings(
        prepared.source, work / "snapshots" / prepared.directory, tuple(changed)
    )
    from src.adapters.artifacts.native_source import read_source_asset
    from src.adapters.artifacts.plate_project import PlateProject
    from src.verification.artifact_files import binary_stl_surface

    snapshot = work / "snapshots" / prepared.directory
    project_receipt = prepared.source.project_3mf
    if project_receipt is None:
        raise ValueError("current native revision requires its captured plate template")
    project = PlateProject(
        read_source_asset(snapshot, project_receipt, tools.import_limits.max_3mf_bytes),
        tuple(Path(p.path).stem for p in prepared.source.parts),
        max_bytes=tools.import_limits.max_3mf_bytes,
    )
    original_parts = {p.path: p for p in prepared.source.parts}
    revised_parts = {p.path: p for p in stls.parts}
    changes = {
        Path(name).stem: (
            binary_stl_surface(
                read_source_asset(snapshot, original_parts[name], tools.import_limits.max_stl_bytes)
            ),
            binary_stl_surface(
                read_source_asset(
                    work / "complete-stl", revised_parts[name], tools.import_limits.max_stl_bytes
                )
            ),
        )
        for name in stls.changed_paths
    }
    payload, _ = project.revise(changes)
    candidate = work / "candidate-unsliced.3mf"
    with candidate.open("xb") as handle:
        handle.write(payload)
    with (
        tempfile.TemporaryDirectory(prefix="bambu-info-") as datadir,
        (work / "bambu-info.log").open("x") as log,
    ):
        subprocess.run(
            [str(tools.bambu_studio_bin), "--datadir", datadir, "--info", str(candidate.resolve())],
            cwd=work,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=True,
        )
    result = {
        "request": asdict(captured.request),
        "print_target": asdict(captured.spec.print_target),
        "derived_plate_sha256": digest(candidate),
        "bambu_info_passed": True,
        "plate_source_bindings": bindings,
        "scope": "isolated current-source geometry and full STL only; not public MCP or manufacturing qualification",
        "worker": json.loads((work / "worker.json").read_text()),
        "reopened": json.loads((work / "reopened.json").read_text()),
        "candidate_sha256": digest(native),
        "complete_stl_count": len(stls.parts),
        "changed_stls": stls.changed_paths,
        "source_sha256": prepared.source.native.sha256,
    }
    (work / "verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("host", "worker", "check", "reopen", "callback", "callback-reopen"),
        default="host",
    )
    parser.add_argument("--work", type=Path)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--all", action="store_true")
    scope.add_argument("--target-angle-deg", type=float, default=0)
    parser.add_argument("--blender", type=Path)
    parser.add_argument("--host-python", type=Path)
    parser.add_argument("--payload", type=Path)
    parser.add_argument(
        "--control", choices=("none", "skip-cut", "skip-stop", "stale-canonical"), default="none"
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else None)
    if args.phase == "host":
        from scripts.verify.native_session_verify_factory import installed_blender

        work = args.work or ROOT / "tmp" / ("native-revision-" + uuid.uuid4().hex)
        blender = args.blender or installed_blender(
            Path.home() / "Library/LaunchAgents/com.blender-mcp.blender.plist"
        )
        if args.all:
            work.mkdir(parents=True, exist_ok=False)
            results = []
            for control in recipe_cases():
                host(work / control, blender, control)
                results.append(json.loads((work / control / "verification.json").read_text()))
            for target in recipe_targets()[1:]:
                target_work = work / ("target-" + str(target))
                host(target_work, blender, target_angle_deg=target)
                results.append(json.loads((target_work / "verification.json").read_text()))
            from scripts.verify.native_session_verify_factory import verify_callback

            results.append(verify_callback(blender, work / "callback"))
            assert len({result["source_sha256"] for result in results}) == 1
            assert {
                result["request"]["target_angle_deg"] for result in results if "request" in result
            } == set(recipe_targets())
            (work / "verification.json").write_text(
                json.dumps(
                    {
                        "results": results,
                        "scope": "isolated geometry and complete STL only; not public or manufacturing qualification",
                    },
                    indent=2,
                )
            )
        else:
            host(work, blender, args.control, args.target_angle_deg)
    elif args.phase in ("callback", "callback-reopen"):
        from scripts.verify.native_revision_fixture import callback, callback_reopen

        if args.work is None:
            raise ValueError("callback verification requires its job directory")
        (callback if args.phase == "callback" else callback_reopen)(args.work)
    elif args.phase == "worker":
        if args.host_python is None:
            raise ValueError("worker requires the host validation interpreter")
        from scripts.verify.native_revision_fixture import worker

        if args.work is None:
            raise ValueError("worker requires its job directory")
        worker(args.work, args.host_python, args.control)
    elif args.phase == "check":
        if args.payload is None:
            raise ValueError("checker requires a stage payload")
        from scripts.verify.native_revision_checks import check

        check(args.payload)
    else:
        from scripts.verify.native_revision_fixture import reopen

        if args.work is None:
            raise ValueError("reopen requires its job directory")
        reopen(args.work)


if __name__ == "__main__":
    main()
