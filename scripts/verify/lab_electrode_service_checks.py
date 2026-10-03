"""Single-head maintenance scenarios reuse assembly and cable collision predicates."""

from dataclasses import asdict
from functools import lru_cache

import bpy
from mathutils import Vector

from scripts import lab_cable_routes as routes
from scripts import model_lab_platform as model
from scripts.lab_cable_motion import MotionFrame, validate_motion
from scripts.lab_electrode_check import verify_clamps
from scripts.lab_station_rig import set_electrode_service_tilt, set_electrode_wrist_pose
from src.core.planning.cable_path_plan import fit_family
from src.verification.cable_route_cases import CHAIN_ROUTES, MOTION_FAMILIES
from src.verification.electrode_service_cases import SERVICE_CASES, WRIST_POINTS, ServiceProbe
from src.verification.scenario_runner import Observation, ScenarioResult, run_scenarios


class RouteBlocked(Exception):
    """A measured collision, distinct from a failed measurement or incomplete model."""


class ServiceFixture:
    def __init__(self) -> None:
        self.blocker: bpy.types.Object | None = None

    def cleanup(self, case: ServiceProbe) -> None:
        if self.blocker is not None:
            mesh = self.blocker.data
            bpy.data.objects.remove(self.blocker, do_unlink=True)
            self.blocker = None
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for head in ("capillary", "pH_temp"):
            model.pose(head)

    def observe(self, case: ServiceProbe) -> Observation:
        self.cleanup(case)
        for head in ("capillary", "pH_temp"):
            model.pose(head, 0, 100 if head == case.head and case.control != "working" else 0)
        if case.operation == "clamp" and case.control != "working":
            set_electrode_service_tilt(case.head)
        neighbour = "pH_temp" if case.head == "capillary" else "capillary"
        fields = ("location", "rotation_euler", "rotation_quaternion", "scale")

        def neighbour_state() -> dict[str, object]:
            return {
                obj.name: tuple(tuple(getattr(obj, field)) for field in fields)
                for obj in bpy.data.objects
                if obj.name.startswith("S_" + neighbour + "_")
            }

        unchanged = neighbour_state()
        cases = tuple(
            routes.RouteCase(r.head, r.channel, r.segment, r.length_mm) for r in CHAIN_ROUTES
        )
        rows: list[dict[str, object]] = []
        geometry: dict[str, int] = {}
        outcome = "clear"
        reason = ""
        fit = lru_cache(maxsize=512)(fit_family)
        with routes.replay_cache() as cache:

            def observe_step(
                head: str, moving: tuple[str, ...], removed: tuple[str, ...], step: int
            ) -> None:
                if head != case.head or neighbour_state() != unchanged:
                    raise ValueError("Service changed the other head")
                if set(moving) & set(removed):
                    raise ValueError("A removed part cannot also be moving")
                boundaries = tuple(routes.measure(route) for route in cases)
                selected = tuple(
                    fit(family, boundary)
                    for family, boundary in zip(MOTION_FAMILIES, boundaries, strict=True)
                )
                if any(route is None for route in selected):
                    raise ValueError("Saved service cable family is infeasible")
                candidates = tuple(route for route in selected if route is not None)
                target = (
                    case.operation == "wrist"
                    and step == 16
                    or case.operation == "clamp"
                    and step == 19
                    and "S_pH_temp_probe_-7" in moving
                )
                if case.control == "obstacle" and target:
                    sampled = cache.sample(candidates[5].curves)
                    point = sampled.points_mm[len(sampled.points_mm) // 2]
                    bpy.ops.mesh.primitive_cube_add(size=0.004, location=Vector(point) / 1000)
                    self.blocker = bpy.context.object
                    self.blocker.name = "SERVICE_CHECK_cable_blocker"
                obstacles = routes.RouteObstacles()
                for name in removed:
                    obstacles.meshes.pop(name, None)
                    obstacles.bounds.pop(name, None)
                    obstacles.closed.discard(name)
                frame = MotionFrame(case.head, 100, boundaries, obstacles, path=case.operation)
                evidence = validate_motion(cases, (frame,), (candidates,), cache=cache)[0]
                rows.append(
                    {
                        "moving": moving,
                        "removed": removed,
                        "step": step,
                        "evidence": asdict(evidence),
                    }
                )
                if evidence.hits:
                    if case.control == "obstacle" and (
                        self.blocker is None
                        or not any(hit.get("object") == self.blocker.name for hit in evidence.hits)
                    ):
                        raise ValueError("Service obstruction control hit a different object")
                    raise RouteBlocked(str(evidence.hits))

            try:
                if case.operation == "wrist":
                    for index, point in enumerate(WRIST_POINTS):
                        model.pose(case.head, 0, 100)
                        set_electrode_wrist_pose(case.head, point.angle_deg, point.release_mm)
                        model.verify_pose(case.head)
                        observe_step(case.head, (), (), index)
                else:
                    geometry = verify_clamps(
                        labels=(case.head,),
                        observe=None if case.control == "working" else observe_step,
                    )
            except RouteBlocked as error:
                outcome, reason = "blocked", str(error)
            except ValueError as error:
                if case.control != "working" or not str(error).startswith(
                    "Probe clamp removal blocked: S_" + case.head + "_"
                ):
                    raise
                outcome, reason = "blocked", str(error)
            finally:
                fit.cache_clear()
        if outcome == "clear":
            expected = (
                32 if case.operation == "wrist" else (130 if case.head == "capillary" else 156)
            )
            if len(rows) != expected:
                raise ValueError("Incomplete service sample coverage")
        return Observation(
            outcome,
            {
                "head": case.head,
                "operation": case.operation,
                "rows": rows,
                "geometry": geometry,
                "reason": reason,
            },
        )


def verify_service_control_discrimination() -> None:
    """An unrelated collision before the injected blocker must never satisfy its control."""
    from unittest.mock import patch

    from scripts.lab_cable_motion import FrameEvidence

    fixture = ServiceFixture()
    case = ServiceProbe("pH_temp", "wrist", "obstacle")
    unrelated = (FrameEvidence("pH_temp", 100, ({"object": "unrelated_obstacle"},)),)
    try:
        with patch(__name__ + ".validate_motion", return_value=unrelated):
            try:
                fixture.observe(case)
            except ValueError as error:
                assert "obstruction control" in str(error), str(error)
            else:
                raise AssertionError(
                    "Unrelated collision satisfied the service obstruction control"
                )
    finally:
        fixture.cleanup(case)


def run_service_cases(suite_id: str) -> tuple[ScenarioResult, ...]:
    verify_service_control_discrimination()
    fixture = ServiceFixture()
    return run_scenarios(SERVICE_CASES[suite_id], fixture.observe, fixture.cleanup)
