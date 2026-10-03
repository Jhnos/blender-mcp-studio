"""Blender fixtures and measurements for the shared scenario runner."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path

import bpy

from scripts import lab_cable_routes as routes
from scripts import model_lab_platform as model
from scripts.lab_station_render import configure_electrode_view
from src.core.domain.cable_paths import sample_path
from src.core.planning.cable_path_plan import RouteCandidate, RouteSearchSpec
from src.verification.cable_route_cases import (
    BUNDLE_CASES,
    BUNDLE_ROUTES,
    CHAIN_CASES,
    CONTACT_CASES,
    PAIR_CASES,
    ROUTE_CASES,
    BundlePose,
    ContactProbe,
    PairProbe,
    RoutePose,
)
from src.verification.scenario_runner import Observation, require_complete, run_scenarios


class ContactFixture:
    """One owned solid per case; cleanup cannot remove another caller's object."""

    def __init__(self) -> None:
        self.object: bpy.types.Object | None = None

    def observe(self, case: ContactProbe) -> Observation:
        if case.check == "self":
            if case.prefix and any(
                routes.nonlocal_self_hit(sample_path((curve,)), case.boundary.cable_radius_mm)
                for curve in (*case.prefix, case.curve)
            ):
                raise ValueError("Chain control requires individually clear segments")
            hit = routes.nonlocal_self_hit(
                sample_path((*case.prefix, case.curve)), case.boundary.cable_radius_mm
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


class PairFixture:
    @staticmethod
    def observe(case: PairProbe) -> Observation:
        first = sample_path((case.first,), step_mm=case.step_mm)
        second = sample_path((case.second,), step_mm=case.step_mm)
        hit = routes.pair_hit(first, case.first_radius_mm, second, case.second_radius_mm)
        reverse = routes.pair_hit(second, case.second_radius_mm, first, case.first_radius_mm)
        if bool(hit) != bool(reverse):
            raise ValueError("Wire contact must be symmetric")
        return Observation("wire_contact" if hit else "clear", {"hit": hit})

    @staticmethod
    def cleanup(case: PairProbe) -> None:
        pass


def reset_heads(*, previews: bool = False) -> None:
    for obj in list(bpy.data.objects):
        if previews and obj.name.startswith("RESEARCH_route_"):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Curve) and data.users == 0:
                bpy.data.curves.remove(data)
    for head in ("capillary", "pH_temp"):
        model.pose(head)
    bpy.context.view_layer.update()


def save_preview(output: Path, stem: str) -> None:
    scene = configure_electrode_view()
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 850
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / (stem + ".png"))
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / (stem + ".blend")))


class RouteFixture:
    def __init__(self, output: Path, *, render: bool) -> None:
        self.output = output
        self.render = render

    def cleanup(self, case: RoutePose) -> None:
        reset_heads(previews=self.render)

    def observe(self, case: RoutePose) -> Observation:
        self.cleanup(case)
        model.pose(case.head, 0, case.lift_mm)
        selected, report = routes.select_route(
            routes.RouteCase(case.head, case.channel, "head", case.length_mm),
            RouteSearchSpec(candidate_count=256),
        )
        if selected is not None and self.render and case.preview_stem:
            routes.draw_route(selected, (0.04, 0.05, 0.06, 1))
            save_preview(self.output, case.preview_stem)
        return Observation(
            "found" if selected is not None else "not_found",
            {
                "lift_mm": case.lift_mm,
                "pass": selected is not None,
                **report,
            },
        )


class BundleFixture:
    """All selected head routes share one obstacle snapshot and reserve earlier envelopes."""

    def __init__(self, output: Path | None = None) -> None:
        self.output = output

    def cleanup(self, case: BundlePose) -> None:
        reset_heads(previews=self.output is not None)

    def observe(self, case: BundlePose) -> Observation:
        self.cleanup(case)
        model.pose("capillary", 0, case.capillary_lift_mm)
        model.pose("pH_temp", 0, case.ph_temp_lift_mm)
        obstacles = routes.RouteObstacles()
        wires: dict[tuple[str, int], list[RouteCandidate]] = {}
        reports = []
        for route in case.routes:
            key = (route.head, route.channel)
            prefix = tuple(wires.get(key, []))
            occupied = tuple(s for k, segments in wires.items() if k != key for s in segments)
            selected, report = routes.select_route(
                routes.RouteCase(route.head, route.channel, route.segment, route.length_mm),
                RouteSearchSpec(candidate_count=256),
                occupied=occupied,
                prefix=prefix,
                obstacles=obstacles,
            )
            reports.append({"found": selected is not None, **report})
            if selected is None:
                if case.obstruction_radius_mm is not None and (
                    not report.get("wire_rejections")
                    or report.get("wire_rejections") != report.get("candidate_count")
                ):
                    raise ValueError(
                        "Obstruction control must reject candidates specifically on wire contact"
                    )
                return Observation(
                    "not_found", {"routes": reports, "expected_routes": len(case.routes)}
                )
            if not wires and case.obstruction_radius_mm is not None:
                selected = replace(
                    selected,
                    boundary=replace(selected.boundary, cable_radius_mm=case.obstruction_radius_mm),
                )
            wires.setdefault(key, []).append(selected)
        if len(wires) != 3:
            raise ValueError("Bundle requires capillary, pH and temperature head routes")
        if self.output is not None and case.preview_stem:
            colors = ((0.05, 0.25, 0.85, 1), (0.85, 0.15, 0.05, 1), (0.02, 0.55, 0.25, 1))
            for segments, color in zip(wires.values(), colors, strict=True):
                for selected in segments:
                    routes.draw_route(selected, color)
            save_preview(self.output, case.preview_stem)
        return Observation(
            "found",
            {
                "routes": reports,
                "pair_count": 3,
                "segment_count": len(case.routes),
                "scope": "Three wires with declared connected segments in one sampled pose",
            },
        )


def run(output: Path, *, render: bool = True) -> None:
    output.mkdir(parents=True, exist_ok=True)
    contact_fixture = ContactFixture()
    controls = run_scenarios(CONTACT_CASES, contact_fixture.observe, contact_fixture.cleanup)
    pair_fixture = PairFixture()
    pairs = run_scenarios(PAIR_CASES, pair_fixture.observe, pair_fixture.cleanup)
    report: dict[str, object] = {
        "schema_version": 2,
        "controls": {row.evidence.name: row.evidence.passed for row in controls},
        "control_evidence": [asdict(row) for row in controls],
        "pair_evidence": [asdict(row) for row in pairs],
        "control_cases": [asdict(case) for case in CONTACT_CASES],
        "route_cases": [asdict(case) for case in ROUTE_CASES],
        "rows": [],
    }
    path = output / "engine-verification.json"
    path.write_text(json.dumps(report, indent=2))
    require_complete(CONTACT_CASES, controls)
    require_complete(PAIR_CASES, pairs)
    fixture = RouteFixture(output, render=render)
    results = run_scenarios(ROUTE_CASES, fixture.observe, fixture.cleanup)
    report["route_evidence"] = [asdict(row) for row in results]
    report["rows"] = [dict(row.measurements) for row in results]
    path.write_text(json.dumps(report, indent=2))
    require_complete(ROUTE_CASES, results)
    bundle_fixture = BundleFixture(output if render else None)
    bundles = run_scenarios(BUNDLE_CASES, bundle_fixture.observe, bundle_fixture.cleanup)
    report["bundle_cases"] = [asdict(case) for case in BUNDLE_CASES]
    report["bundle_routes"] = [asdict(route) for route in BUNDLE_ROUTES]
    report["bundle_evidence"] = [asdict(row) for row in bundles]
    path.write_text(json.dumps(report, indent=2))
    require_complete(BUNDLE_CASES, bundles)
    chains = run_scenarios(CHAIN_CASES, bundle_fixture.observe, bundle_fixture.cleanup)
    report["chain_cases"] = [asdict(case) for case in CHAIN_CASES]
    report["chain_evidence"] = [asdict(row) for row in chains]
    path.write_text(json.dumps(report, indent=2))
    require_complete(CHAIN_CASES, chains)
    print(
        f"Shared scenarios: {len(controls)} contact, {len(pairs)} wire-pair, "
        f"{len(results)} single-route, {len(bundles)} bundle and {len(chains)} full-chain cases passed"
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
            pair_fixture = PairFixture()
            results += run_scenarios(PAIR_CASES, pair_fixture.observe, pair_fixture.cleanup)
        elif suite_id in ("electrode-head-bundle", "electrode-full-chains"):
            if "electrode_configuration" not in bpy.context.scene:
                raise ValueError(
                    "Open a generated lab-station electrode assembly before running this suite"
                )
            bundle_fixture = BundleFixture()
            cases = CHAIN_CASES if suite_id == "electrode-full-chains" else BUNDLE_CASES
            results = run_scenarios(cases, bundle_fixture.observe, bundle_fixture.cleanup)
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
