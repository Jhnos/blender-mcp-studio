"""Isolated Blender worker and reload observer for the closed screen recipe."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bpy

    from src.core.domain.native_revision import NativeRevisionRequest
    from src.core.planning.screen_revision_plan import ScreenRevisionPlan

ROOT = Path(__file__).resolve().parents[2]


def assert_factory_isolated() -> None:
    import bpy

    addon_names = bpy.context.preferences.addons.keys()
    assert bpy.app.background and not any("blender_mcp" in name.lower() for name in addon_names)
    listeners = subprocess.run(
        ["lsof", "-nP", "-a", "-p", str(os.getpid()), "-iTCP", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert listeners.returncode == 1 and not listeners.stdout and not listeners.stderr


def check_control_motion(
    objects: Mapping[str, bpy.types.Object],
    plan: ScreenRevisionPlan,
    request: NativeRevisionRequest,
) -> dict[str, object]:
    """Independent phase/axis readback on the four real original hardware meshes."""
    import math

    import bpy
    from mathutils import Vector

    body = objects[plan.control_owner]
    hardware = [objects[name] for name in plan.clamp_owners]
    local = {
        obj: sum((v.co for v in obj.data.vertices), Vector()) / len(obj.data.vertices)
        for obj in hardware
    }
    identities = {obj: obj.data for obj in hardware}

    def update(progress: float, axial: float) -> None:
        body["收折進度"], body["樞軸軸向間隙"] = progress, axial
        for obj in (body, *hardware):
            obj.update_tag()
        bpy.context.view_layer.update()

    update(0.0, 0.0)
    baseline = {obj: obj.matrix_world @ point for obj, point in local.items()}
    maximum, maximum_angle = 0.0, 0.0
    progress_steps = list(range(101)) + list(range(100, -1, -1))
    for index, progress in enumerate(progress_steps):
        axial = (-0.28, 0.0, 0.28)[index % 3]
        update(float(progress), axial)
        phase = progress / 20
        if phase <= 1:
            angle, release, screw = 60.0, 0.0, 2.4 * phase
        elif phase <= 2:
            angle, release, screw = 60.0, 2.2 * (phase - 1), 2.4
        elif phase <= 3:
            angle, release, screw = 60.0 + (request.target_angle_deg - 60) * (phase - 2), 2.2, 2.4
        elif phase <= 4:
            angle, release, screw = request.target_angle_deg, 2.2 * (4 - phase), 2.4
        else:
            angle, release, screw = request.target_angle_deg, 0.0, 2.4 * (5 - phase)
        displacements = (release - screw, release, release + axial, release + axial)
        for obj, delta_x in zip(hardware, displacements, strict=True):
            point = obj.matrix_world @ local[obj]
            error = max(
                abs((point.x - baseline[obj].x) * 1000 - delta_x),
                abs(point.y - baseline[obj].y) * 1000,
                abs(point.z - baseline[obj].z) * 1000,
            )
            maximum = max(maximum, error)
            assert error < 0.001, (obj.name, progress, error)
            assert obj.data is identities[obj]
        expected = math.radians(angle - 60) - 2 * math.pi * screw / 0.8
        error_angle = abs(hardware[0].rotation_euler.x - expected)
        maximum_angle = max(maximum_angle, error_angle)
        assert error_angle < 0.00001 and abs(body["fold_angle_deg"] - angle) < 0.0001
    update(100.0, 0.0)
    assert abs(body["fold_angle_deg"] - request.target_angle_deg) < 0.0001
    assert all(obj.animation_data for obj in (body, hardware[0], hardware[2], hardware[3]))
    assert all(
        curve.driver.is_valid
        for obj in (body, *hardware)
        if obj.animation_data
        for curve in obj.animation_data.drivers
    )
    return {
        "samples": len(progress_steps),
        "target_angle_deg": request.target_angle_deg,
        "maximum_position_error_mm": maximum,
        "maximum_rotation_error_rad": maximum_angle,
        "mesh_ids_preserved": True,
    }


def worker(work: Path, host_python: Path, control: str = "none") -> None:
    import bpy

    import scripts.lab_station_native_revision as recipe_module
    from scripts.blender_native_session import NativeSceneSession
    from scripts.lab_station_native_revision import (
        apply_screen_controls,
        apply_screen_geometry,
        prepare_screen_source,
        surface,
    )
    from scripts.verify.native_scene_oracle import original_state, relations
    from src.adapters.artifacts.native_source import source_asset_path
    from src.core.domain.native_revision import SourceArtifact, parse_native_revision
    from src.core.planning.screen_revision_plan import plan_screen_revision

    assert_factory_isolated()
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
            request = parse_native_revision(metadata["request"])
            apply_screen_controls(objects, plan, request)
            motion = check_control_motion(objects, plan, request)
            final = {name: surface(obj) for name, obj in objects.items() if obj.type == "MESH"}
            observe("final-all", final)
            saved = {
                "request": metadata["request"],
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
                    "control_motion": motion,
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
    from scripts.verify.native_scene_oracle import relations
    from src.core.domain.native_revision import parse_native_revision
    from src.core.planning.screen_revision_plan import plan_screen_revision

    bpy.context.view_layer.update()
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
    objects = dict(bpy.data.objects.items())
    pivot = tuple(objects["整機_螢幕收折"].matrix_world.translation * 1000)
    # The control's X is the seated offset. The declared hinge datum is on X=0.
    plan = plan_screen_revision((0.0, pivot[1], pivot[2]))
    motion = check_control_motion(objects, plan, parse_native_revision(expected["request"]))
    (work / "reopened.json").write_text(
        json.dumps(
            {
                "control_motion": motion,
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


def callback(work: Path) -> None:
    import bpy

    from scripts.verify.native_scene_oracle import original_state
    from scripts.verify.native_scene_session_fixture import add_text_fixture

    assert_factory_isolated()
    original_types = {obj.name: obj.type for obj in bpy.data.objects}
    add_text_fixture("original_callback_text")
    before = original_state()
    exec((work / "native-program.py").read_text())
    assert original_state() == before
    (work / "worker.json").write_text(
        json.dumps(
            {
                "original_state_equal": True,
                "original_types": original_types,
                "original_objects": len(bpy.data.objects),
                "original_meshes": sum(obj.type == "MESH" for obj in bpy.data.objects),
                "active_objects": len(bpy.context.scene.objects),
                "external_libraries": len(bpy.data.libraries),
            }
        )
    )


def callback_reopen(work: Path) -> None:
    import bpy

    from scripts.lab_station_native_revision import surface
    from src.core.domain.native_revision import NativeRevisionRequest
    from src.core.planning.screen_revision_plan import plan_screen_revision

    metadata = json.loads((work / "callback.json").read_text())
    execution = work / metadata["execution"]
    expected_types = json.loads((work / "worker.json").read_text())["original_types"]
    bpy.context.view_layer.update()
    assert {obj.name: obj.type for obj in bpy.data.objects} == expected_types
    assert set(bpy.context.scene.objects.keys()) == set(expected_types) and not bpy.data.libraries
    final = list((execution / "stages").glob("*-final-all.json"))
    assert len(final) == 1
    expected = json.loads(final[0].read_text())["surfaces"]
    actual = {obj.name: surface(obj) for obj in bpy.data.objects if obj.type == "MESH"}

    def fingerprint(value: object) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    assert {name: fingerprint(value) for name, value in actual.items()} == {
        name: fingerprint(value) for name, value in expected.items()
    }
    objects = dict(bpy.data.objects.items())
    pivot = objects["整機_螢幕收折"].matrix_world.translation * 1000
    motion = check_control_motion(
        objects,
        plan_screen_revision((0.0, pivot.y, pivot.z)),
        NativeRevisionRequest("screen-clamp", metadata["target_angle_deg"]),
    )
    (work / "reopened.json").write_text(
        json.dumps(
            {
                "objects": len(expected_types),
                "meshes": len(actual),
                "active_scene_complete": True,
                "full_saved_surface_frames_equal": True,
                "control_motion": motion,
                "external_libraries": 0,
            }
        )
    )
