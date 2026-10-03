"""Blender fixtures and measurements for the shared scenario runner."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

import bpy

from scripts import lab_cable_routes as routes
from scripts import model_lab_platform as model
from scripts.lab_station_render import configure_electrode_view
from src.core.domain.cable_paths import sample_path
from src.core.planning.cable_path_plan import RouteSearchSpec
from src.verification.cable_route_cases import CONTACT_CASES, ROUTE_CASES, ContactProbe, RoutePose
from src.verification.scenario_runner import Observation, require_complete, run_scenarios


class ContactFixture:
    """One owned solid per case; cleanup cannot remove another caller's object."""

    def __init__(self) -> None:
        self.object: bpy.types.Object | None = None

    def observe(self, case: ContactProbe) -> Observation:
        if case.check == "self":
            hit = routes.nonlocal_self_hit(
                sample_path((case.curve,)), case.boundary.cable_radius_mm
            )
            return Observation(str(hit["reason"]) if hit else "clear", {"hit": hit})
        bpy.ops.mesh.primitive_cube_add(size=0.02, location=(2, 2, 2))
        self.object = bpy.context.object
        self.object.name = "ROUTE_CHECK_solid"
        self.object.scale.x = -1
        bpy.context.view_layer.update()
        mirrored = self.object.matrix_world.determinant() < 0
        if not mirrored:
            raise ValueError("Contact fixture must exercise a mirrored mesh")
        obstacles = routes.RouteObstacles()
        name = self.object.name
        obstacles.meshes = {name: obstacles.meshes[name]}
        obstacles.bounds = {name: obstacles.bounds[name]}
        obstacles.closed.intersection_update({name})
        hit = obstacles.first_hit(
            sample_path((case.curve,)),
            case.boundary,
            self.object.name if case.terminal else None,
        )
        if hit and hit.get("object") != self.object.name:
            raise ValueError("Fixture touched an unrelated object: " + str(hit))
        return Observation(
            str(hit["reason"]) if hit else "clear",
            {"hit": hit, "mirrored_fixture": mirrored},
        )

    def cleanup(self, case: ContactProbe) -> None:
        if self.object is not None:
            mesh = self.object.data
            bpy.data.objects.remove(self.object, do_unlink=True)
            self.object = None
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)


class RouteFixture:
    def __init__(self, output: Path, *, render: bool) -> None:
        self.output = output
        self.render = render

    def cleanup(self, case: RoutePose) -> None:
        for obj in list(bpy.data.objects):
            if self.render and obj.name.startswith("RESEARCH_route_"):
                bpy.data.objects.remove(obj, do_unlink=True)
        for head in ("capillary", "pH_temp"):
            model.pose(head)
        bpy.context.view_layer.update()

    def observe(self, case: RoutePose) -> Observation:
        self.cleanup(case)
        model.pose(case.head, 0, case.lift_mm)
        selected, report = routes.select_route(
            routes.RouteCase(case.head, case.channel, "head", case.length_mm),
            RouteSearchSpec(candidate_count=256),
        )
        if selected is not None and self.render and case.preview_stem:
            routes.draw_route(selected, (0.04, 0.05, 0.06, 1))
            scene = configure_electrode_view()
            scene.render.resolution_x = 1000
            scene.render.resolution_y = 850
            scene.render.resolution_percentage = 100
            scene.render.filepath = str(self.output / (case.preview_stem + ".png"))
            bpy.ops.render.render(write_still=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(self.output / (case.preview_stem + ".blend")))
        return Observation(
            "found" if selected is not None else "not_found",
            {
                "lift_mm": case.lift_mm,
                "pass": selected is not None,
                **report,
            },
        )


def run(output: Path, *, render: bool = True) -> None:
    output.mkdir(parents=True, exist_ok=True)
    contact_fixture = ContactFixture()
    controls = run_scenarios(CONTACT_CASES, contact_fixture.observe, contact_fixture.cleanup)
    report: dict[str, object] = {
        "schema_version": 2,
        "controls": {row.evidence.name: row.evidence.passed for row in controls},
        "control_evidence": [asdict(row) for row in controls],
        "control_cases": [asdict(case) for case in CONTACT_CASES],
        "route_cases": [asdict(case) for case in ROUTE_CASES],
        "rows": [],
    }
    path = output / "engine-verification.json"
    path.write_text(json.dumps(report, indent=2))
    require_complete(CONTACT_CASES, controls)
    fixture = RouteFixture(output, render=render)
    results = run_scenarios(ROUTE_CASES, fixture.observe, fixture.cleanup)
    report["route_evidence"] = [asdict(row) for row in results]
    report["rows"] = [dict(row.measurements) for row in results]
    path.write_text(json.dumps(report, indent=2))
    require_complete(ROUTE_CASES, results)
    print(
        f"Shared scenario runner: {len(controls)} contact cases and {len(results)} route cases passed"
    )


@contextmanager
def preserve_current_scene() -> Iterator[None]:
    """Restore only fields this suite can change; never open or overwrite a user file."""
    if bpy.context.mode != "OBJECT":
        raise ValueError("Switch Blender to Object Mode before running verification")
    keys = ("shoulder_release_mm", "elbow_release_mm", "wrist_release_mm")
    fields = (
        "location",
        "rotation_euler",
        "rotation_quaternion",
        "rotation_axis_angle",
        "scale",
        "delta_location",
        "delta_rotation_euler",
        "delta_rotation_quaternion",
        "delta_scale",
    )
    saved = [
        (
            obj,
            {field: tuple(getattr(obj, field)) for field in fields},
            {key: obj[key] for key in keys if key in obj},
        )
        for obj in bpy.data.objects
    ]
    original_objects = set(bpy.data.objects)
    original_meshes = set(bpy.data.meshes)
    selected = tuple(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    try:
        yield
    finally:
        for obj, transforms, properties in saved:
            for field, values in transforms.items():
                setattr(obj, field, values)
            for key in keys:
                if key in properties:
                    obj[key] = properties[key]
                elif key in obj:
                    del obj[key]
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in selected)
        bpy.context.view_layer.objects.active = active
        bpy.context.view_layer.update()
        if set(bpy.data.objects) != original_objects or set(bpy.data.meshes) != original_meshes:
            raise ValueError("Verification left missing or additional objects/meshes")
        for obj, transforms, properties in saved:
            if {field: tuple(getattr(obj, field)) for field in fields} != transforms or {
                key: obj[key] for key in keys if key in obj
            } != properties:
                raise ValueError("Verification could not restore " + obj.name)


def run_registered(suite_id: str) -> dict[str, object]:
    """Public, bounded checks reuse offline cases without loading, saving or rendering scenes."""
    with preserve_current_scene():
        if suite_id == "cable-contact-controls":
            fixture = ContactFixture()
            results = run_scenarios(CONTACT_CASES, fixture.observe, fixture.cleanup)
        elif suite_id == "electrode-head-routes":
            if "electrode_configuration" not in bpy.context.scene:
                raise ValueError(
                    "Open a generated lab-station electrode assembly before running this suite"
                )
            route_fixture = RouteFixture(Path(), render=False)
            results = run_scenarios(ROUTE_CASES, route_fixture.observe, route_fixture.cleanup)
        else:
            raise ValueError("Unknown registered verification suite: " + suite_id)
    return {
        "suite_id": suite_id,
        "restored": True,
        "checks": [
            {
                "name": row.evidence.name,
                "expected": row.expected,
                "observed": row.observed,
                "passed": row.evidence.passed,
                "detail": row.evidence.detail,
            }
            for row in results
        ],
    }
