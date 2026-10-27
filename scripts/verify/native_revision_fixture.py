"""Isolated Blender worker and reload observer for the closed screen recipe."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def worker(work: Path, host_python: Path, control: str = "none") -> None:
    import bpy

    import scripts.lab_station_native_revision as recipe_module
    from scripts.blender_native_session import NativeSceneSession
    from scripts.lab_station_native_revision import (
        apply_screen_geometry,
        prepare_screen_source,
        surface,
    )
    from scripts.verify.native_scene_session_fixture import original_state, relations
    from src.adapters.artifacts.native_source import source_asset_path
    from src.core.domain.native_revision import SourceArtifact
    from src.core.planning.screen_revision_plan import plan_screen_revision

    addon_names = bpy.context.preferences.addons.keys()
    assert bpy.app.background and not any("blender_mcp" in name.lower() for name in addon_names)
    listeners = subprocess.run(
        ["lsof", "-nP", "-a", "-p", str(os.getpid()), "-iTCP", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert listeners.returncode == 1 and not listeners.stdout and not listeners.stderr
    metadata = json.loads((work / "input.json").read_text())
    snapshot = work / "snapshots" / metadata["directory"]
    native = snapshot / metadata["native"]["path"]
    before = original_state()
    stages: list[str] = []
    output = work / "candidate.blend"
    if control != "none":
        from scripts.blender_mesh_primitives import boolean as original_boolean

        def controlled_boolean(
            target: bpy.types.Object,
            tool: bpy.types.Object,
            operation: str,
            *,
            depsgraph: bpy.types.Depsgraph | None = None,
        ) -> None:
            if (control == "skip-cut" and operation == "DIFFERENCE") or (
                control == "skip-stop" and operation == "UNION"
            ):
                bpy.data.objects.remove(tool, do_unlink=True)
                return
            original_boolean(target, tool, operation, depsgraph=depsgraph)

        vars(recipe_module)["boolean"] = controlled_boolean

    def observe(label: str, surfaces: Mapping[str, dict[str, object]]) -> None:
        path = work / "stages" / f"{len(stages):02}-{label}.json"
        with path.open("x") as handle:
            json.dump({"stage": label, "surfaces": surfaces, "pivot_mm": plan.pivot_mm}, handle)
        with path.with_suffix(".log").open("x") as log:
            subprocess.run(
                [
                    str(host_python),
                    str(ROOT / "scripts/verify/native_revision_verify_factory.py"),
                    "--phase",
                    "check",
                    "--work",
                    str(work),
                    "--payload",
                    str(path),
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=120,
                check=True,
            )
        stages.append(label)

    try:
        declared = {item["path"]: item for item in metadata["source"]["parts"]}
        canonical = {}
        for name, relative in metadata["canonical"].items():
            receipt = declared[relative]
            with source_asset_path(snapshot, relative).open("rb") as handle:
                payload = handle.read(receipt["size_bytes"] + 1)
            if (
                len(payload) != receipt["size_bytes"]
                or hashlib.sha256(payload).hexdigest() != receipt["sha256"]
            ):
                (work / "input-rejected.json").write_text(
                    json.dumps({"reason": "canonical-checksum-mismatch", "owner": name})
                )
                raise ValueError("canonical-checksum-mismatch")
            canonical[name] = payload
        with NativeSceneSession(native, SourceArtifact(**metadata["native"])) as stage:
            objects = stage.objects
            names = sorted(objects)
            pivot = tuple(objects["整機_螢幕收折"].matrix_world.translation * 1000)
            plan = plan_screen_revision(pivot)
            errors = prepare_screen_source(objects, plan, canonical, observe)
            apply_screen_geometry(objects, plan, observe)
            final = {name: surface(obj) for name, obj in objects.items() if obj.type == "MESH"}
            observe("final-all", final)
            saved = {
                "names": names,
                "relations": {name: relations(obj) for name, obj in objects.items()},
                "parents": {
                    name: obj.parent.name if obj.parent else None for name, obj in objects.items()
                },
                "surfaces": {
                    name: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
                    for name, value in final.items()
                },
            }
            (work / "saved.json").write_text(json.dumps(saved))
            stage.write_native(output)
        assert original_state() == before
        (work / "worker.json").write_text(
            json.dumps(
                {
                    "stages": stages,
                    "registration_errors_mm": errors,
                    "original_state_equal": True,
                    "objects": len(names),
                    "meshes": len(final),
                    "original_objects": len(bpy.data.objects),
                    "worker_pid": os.getpid(),
                    "background": True,
                    "mcp_addon_loaded": False,
                    "tcp_listeners": False,
                }
            )
        )
    finally:
        (work / "cleanup.json").write_text(
            json.dumps(
                {
                    "original_state_equal": original_state() == before,
                    "candidate_published": output.exists(),
                    "stages_completed": stages,
                }
            )
        )


def reopen(work: Path) -> None:
    import bpy

    from scripts.lab_station_native_revision import surface
    from scripts.verify.native_scene_session_fixture import relations

    expected = json.loads((work / "saved.json").read_text())
    assert sorted(bpy.data.objects.keys()) == expected["names"]
    assert sorted(bpy.context.scene.objects.keys()) == expected["names"]
    assert len(bpy.data.scenes) == 1 and not bpy.data.libraries
    assert {
        obj.name: obj.parent.name if obj.parent else None for obj in bpy.data.objects
    } == expected["parents"]
    actual = {
        obj.name: hashlib.sha256(json.dumps(surface(obj), sort_keys=True).encode()).hexdigest()
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    assert actual == expected["surfaces"]
    assert {obj.name: relations(obj) for obj in bpy.data.objects} == expected["relations"]
    assert not [
        obj.name
        for obj in bpy.data.objects
        if obj.animation_data
        and any(not curve.driver.is_valid for curve in obj.animation_data.drivers)
    ]
    (work / "reopened.json").write_text(
        json.dumps(
            {
                "objects": len(expected["names"]),
                "meshes": len(actual),
                "active_scene_complete": True,
                "geometry_and_frames_equal": True,
                "parents_equal": True,
                "driver_bindings_equal": True,
                "external_libraries": 0,
            }
        )
    )
