"""Isolated factory fixtures for the native scene lifetime; never connect to the addon.

Run with Blender --background --factory-startup --disable-autoexec --python-exit-code 1
--python this-file -- --phase source|exercise|reopen --work <new-directory> [--case ...].
This is lifecycle evidence only, not production MCP or manufacturing acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from scripts.verify.native_scene_oracle import (  # noqa: E402
    mesh_geometry,
    original_state,
    relations,
)
from scripts.verify.native_session_verify_factory import CASES  # noqa: E402


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def record(work: Path) -> None:
    (work / "source-geometry.json").write_text(
        json.dumps({obj.name: mesh_geometry(obj) for obj in bpy.data.objects})
    )
    (work / "source-relations.json").write_text(
        json.dumps({obj.name: relations(obj) for obj in bpy.data.objects})
    )


def add_text_fixture(name: str) -> None:
    curve = bpy.data.curves.new(name + "_curve", "FONT")
    text = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(text)
    assert curve.font.filepath == "<builtin>" and curve.font.is_property_readonly("name")


def source(work: Path) -> None:
    assert not (work / "source.blend").exists()
    add_text_fixture("fixture_source_text")
    root = bpy.data.objects.new("fixture_control", None)
    bpy.context.scene.collection.objects.link(root)
    root["progress"] = 0.0
    cube = bpy.data.objects["Cube"]
    cube.parent = root
    driver = cube.driver_add("location", 0).driver
    driver.expression = "position / 1000"
    variable = driver.variables.new()
    variable.name = "position"
    variable.targets[0].id = root
    variable.targets[0].data_path = '["progress"]'
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(work / "source.blend"))
    record(work)
    bpy.data.scenes.new("second_source_scene")
    bpy.ops.wm.save_as_mainfile(filepath=str(work / "multiple.blend"))


def exercise(work: Path, case: str) -> None:
    from scripts.blender_native_session import NativeSceneSession
    from src.core.domain.native_revision import (
        NativeSceneError,
        NativeSceneRestorationError,
        SourceArtifact,
    )

    output = work / f"candidate-{case}.blend"
    assert not output.exists()
    if case == "existing":
        output.write_bytes(b"existing-output")
    incoming = work / ("multiple.blend" if case == "multiple" else "source.blend")
    if case == "malformed":
        incoming = work / "malformed.blend"
        incoming.write_bytes(b"verified bytes are not necessarily a native Blender file")
    source_before = digest(incoming)
    expected = SourceArtifact(
        incoming.name, "0" * 64 if case == "hash" else source_before, incoming.stat().st_size
    )
    original_cube = next(obj for obj in bpy.data.objects if obj.type == "MESH")
    add_text_fixture("fixture_original_text")
    original_mesh = original_cube.data
    original_cube["original_sentinel"] = 123
    original_control = bpy.data.objects.new("fixture_control", None)
    bpy.context.scene.collection.objects.link(original_control)
    original_control["progress"] = 7.0
    original_control.id_properties_ui("progress").update(min=0.0, max=100.0)
    original_driver = original_cube.driver_add("location", 0).driver
    original_driver.expression = "position / 1000"
    variable = original_driver.variables.new()
    variable.name = "position"
    variable.targets[0].id = original_control
    variable.targets[0].data_path = '["progress"]'
    bpy.context.view_layer.update()
    if case == "original-linked":
        with bpy.data.libraries.load(str(incoming), link=True) as (library, linked):
            linked.objects = [library.objects[0]]
        assert bpy.data.libraries, "linked-data precondition was not exercised"
    if case == "edit-mode":
        bpy.context.view_layer.objects.active = original_cube
        original_cube.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        assert original_cube.mode == "EDIT"
    before = original_state()
    identities = set(bpy.data.user_map())
    rejected = False
    session = NativeSceneSession(incoming, expected)
    try:
        with session as stage:
            assert bpy.context.scene == stage.scene
            assert bpy.context.window.scene != stage.scene
            assert set(stage.objects) == set(
                json.loads((work / "source-geometry.json").read_text())
            )
            changed = next(obj for obj in stage.objects.values() if obj.type == "MESH")
            if case == "primitive-context":
                from scripts.blender_mesh_primitives import add_cylinder

                inside_before = original_state()
                tool = add_cylinder(
                    "STAGED_primitive", 1, 2, (0, 0, 0), collection=stage.scene.collection
                )
                assert tool in set(stage.scene.objects), "primitive escaped the staged scene"
                assert tool not in set(bpy.context.window.scene.objects), (
                    "primitive entered the original scene"
                )
                mesh = tool.data
                bpy.data.objects.remove(tool, do_unlink=True)
                bpy.data.meshes.remove(mesh)
                assert original_state() == inside_before, (
                    "primitive changed existing selection or context"
                )
            if case == "operation-failure":
                raise RuntimeError("injected native operation failure")
            if case == "original-driver":
                original_driver.expression = "0.007"
            if case == "original-ui":
                original_control.id_properties_ui("progress").update(max=77.0)
            if case == "crosslink":
                changed.data = original_mesh
            if case == "extra":
                extra = bpy.data.objects.new("unexpected_part", None)
                stage.scene.collection.objects.link(extra)
            if case == "rename":
                changed.name = "replacement_part"
            if case == "replace":
                name, mesh = changed.name, changed.data
                bpy.data.objects.remove(changed, do_unlink=True)
                changed = bpy.data.objects.new(name, mesh)
                stage.scene.collection.objects.link(changed)
            changed["fixture_revision_probe"] = "staged-only"
            stage.write_native(incoming if case == "source-overwrite" else output)
            assert not output.exists() or case == "existing", (
                "output published before original restoration"
            )
            if case == "late-output":
                output.write_bytes(b"late-output")
            if case == "pending-failure":
                raise RuntimeError("injected native operation failure")
    except (NativeSceneError, RuntimeError) as error:
        if case in ("success", "primitive-context"):
            raise
        if isinstance(error, RuntimeError) and not isinstance(error, NativeSceneError):
            assert (
                case in ("operation-failure", "pending-failure")
                and str(error) == "injected native operation failure"
            )
        if case in ("original-driver", "original-ui"):
            assert isinstance(error, NativeSceneRestorationError)
        rejected = True
    assert rejected == (case not in ("success", "primitive-context")), case
    assert set(bpy.data.user_map()) == identities
    original_equal = original_state() == before
    if case in ("original-driver", "original-ui"):
        assert not original_equal, "fault injection did not actually change the original control"
    else:
        assert original_equal, "native session altered originals or active context"
    if case == "edit-mode":
        assert original_cube.mode == "EDIT", "rejected session changed the operator's mode"
    if case in ("success", "primitive-context"):
        assert output.is_file()
    elif case in ("existing", "late-output"):
        assert output.read_bytes() == (b"existing-output" if case == "existing" else b"late-output")
    else:
        assert not output.exists()
    assert digest(incoming) == source_before
    assert not list(work.glob(".native-pending-*.blend")), "pending output leaked after session"
    (work / f"{case}.json").write_text(
        json.dumps(
            {
                "case": case,
                "rejected": rejected,
                "original_state_equal": original_equal,
                "source_digest": digest(incoming),
                "scope": "factory lifecycle only",
            }
        )
    )
    print(json.dumps({"case": case, "original_state_equal": original_equal}), flush=True)


def reopen(work: Path) -> None:
    expected = json.loads((work / "source-geometry.json").read_text())
    actual = {obj.name: mesh_geometry(obj) for obj in bpy.data.objects}
    assert actual == expected
    assert len(bpy.data.scenes) == 1 and not bpy.data.libraries
    assert set(bpy.context.scene.objects.keys()) == set(expected)
    changed = [
        obj for obj in bpy.data.objects if obj.get("fixture_revision_probe") == "staged-only"
    ]
    assert len(changed) == 1
    expected_relations = json.loads((work / "source-relations.json").read_text())
    assert {obj.name: relations(obj) for obj in bpy.data.objects} == expected_relations
    invalid = [
        (obj.name, c.data_path)
        for obj in bpy.data.objects
        if obj.animation_data
        for c in obj.animation_data.drivers
        if not c.driver.is_valid
    ]
    assert not invalid, invalid
    if "fixture_control" not in bpy.data.objects:
        print(
            json.dumps(
                {
                    "reopened": True,
                    "objects": len(actual),
                    "meshes": sum(v is not None for v in actual.values()),
                    "active_scene_objects": len(bpy.context.scene.objects),
                    "parent_and_driver_bindings_equal": True,
                    "external_libraries": 0,
                }
            ),
            flush=True,
        )
        return
    cube = bpy.data.objects["Cube"]
    assert cube.parent == bpy.data.objects["fixture_control"]
    bpy.data.objects["fixture_control"]["progress"] = 25.0
    bpy.data.objects["fixture_control"].update_tag()
    bpy.context.view_layer.update()
    assert abs(cube.location.x - 0.025) < 1e-6
    print(
        json.dumps(
            {
                "reopened": True,
                "objects": len(actual),
                "active_scene_objects": len(bpy.context.scene.objects),
                "driver_readback": cube.location.x,
                "external_libraries": 0,
            }
        ),
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", choices=("source", "record", "exercise", "reopen"), required=True
    )
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument(
        "--case",
        choices=CASES,
        default="success",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.work.mkdir(parents=True, exist_ok=True)
    addon_names = bpy.context.preferences.addons.keys()
    assert not any("mcp" in key.lower() for key in addon_names)
    if args.phase == "source":
        source(args.work)
    elif args.phase == "record":
        record(args.work)
    elif args.phase == "exercise":
        exercise(args.work, args.case)
    else:
        reopen(args.work)


if __name__ == "__main__":
    main()
