"""Closed native callback: geometry, exclusive save, original restoration, then terminal."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from scripts.blender_native_session import NativeSceneSession
from scripts.lab_station_native_revision import (
    apply_screen_controls,
    apply_screen_geometry,
    prepare_screen_source,
    surface,
)
from src.adapters.artifacts.native_execution import NativeExecutionJournal
from src.adapters.artifacts.native_source import fingerprint_source_asset, read_source_asset
from src.core.domain.native_revision import NativeRevisionRequest, SourceArtifact
from src.core.planning.screen_revision_plan import plan_screen_revision

ROOT = Path(__file__).resolve().parents[1]


def run(
    directory: Path,
    snapshot: Path,
    native: SourceArtifact,
    canonical: dict[str, SourceArtifact],
    request: NativeRevisionRequest,
    host_python: Path,
    program_sha256: str,
) -> None:
    journal = NativeExecutionJournal(directory)
    identity = journal.mark_started(program_sha256, native.sha256)
    stage = NativeSceneSession(snapshot / native.path, native)
    terminal: dict[str, object] = {
        **identity,
        "status": "failed",
        "restored": False,
        "output": None,
        "surfaces": None,
        "error": "native callback did not finish",
    }
    try:
        stages = directory / "stages"
        stages.mkdir()
        count = 0

        def observe(label: str, surfaces: object) -> None:
            nonlocal count
            payload = stages / f"{count:02}-{label}.json"
            with payload.open("x") as handle:
                json.dump({"stage": label, "surfaces": surfaces, "pivot_mm": plan.pivot_mm}, handle)
            with payload.with_suffix(".log").open("x") as log:
                subprocess.run(
                    [
                        str(host_python),
                        "-c",
                        "from scripts.verify.native_revision_checks import check; import sys; from pathlib import Path; check(Path(sys.argv[1]))",
                        str(payload),
                    ],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=120,
                    check=True,
                )
            count += 1

        with stage:
            objects = stage.objects
            pivot = tuple(objects["整機_螢幕收折"].matrix_world.translation * 1000)
            plan = plan_screen_revision(pivot)
            payloads = {
                name: read_source_asset(snapshot, receipt, receipt.size_bytes)
                for name, receipt in canonical.items()
            }
            prepare_screen_source(objects, plan, payloads, observe)
            apply_screen_geometry(objects, plan, observe)
            apply_screen_controls(objects, plan, request)
            observe(
                "final-all",
                {name: surface(obj) for name, obj in objects.items() if obj.type == "MESH"},
            )
            with (directory / "changed-surfaces.json").open("x") as handle:
                json.dump({name: surface(objects[name]) for name in plan.modified_owners}, handle)
            stage.write_native(directory / "candidate.blend")
        output = fingerprint_source_asset(
            directory / "candidate.blend", "candidate.blend", 512 * 1024 * 1024
        )
        surfaces = fingerprint_source_asset(
            directory / "changed-surfaces.json", "changed-surfaces.json", 128 * 1024 * 1024
        )
        terminal.update(
            status="completed", output=asdict(output), surfaces=asdict(surfaces), error=None
        )
    except BaseException as exc:
        terminal["error"] = f"{type(exc).__name__}: {exc}"[:2048]
        raise
    finally:
        terminal["restored"] = stage.restoration_verified
        journal.publish_terminal(terminal)
