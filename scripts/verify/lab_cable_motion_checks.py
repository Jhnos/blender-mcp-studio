"""Reusable motion fixture: sampled family continuity and an intermediate-only obstacle."""

from collections.abc import Callable
from dataclasses import asdict

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

from scripts import lab_cable_routes as routes
from scripts import model_lab_platform as model
from scripts.lab_cable_motion import capture_frames, select_motion_routes, validate_motion
from src.core.domain.cable_paths import sample_path
from src.verification.cable_route_cases import CHAIN_ROUTES, MotionProbe
from src.verification.scenario_runner import Observation


class MotionFixture:
    def __init__(self, preview: Callable[[str], None] | None = None) -> None:
        self.preview = preview
        self.blocker: bpy.types.Object | None = None
        self.drawn: set[str] = set()

    def cleanup(self, case: MotionProbe) -> None:
        for name in self.drawn:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                data = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if isinstance(data, bpy.types.Curve) and data.users == 0:
                    bpy.data.curves.remove(data)
        self.drawn.clear()
        if self.blocker is not None:
            data = self.blocker.data
            bpy.data.objects.remove(self.blocker, do_unlink=True)
            self.blocker = None
            if data.users == 0:
                bpy.data.meshes.remove(data)
        for head in ("capillary", "pH_temp"):
            model.pose(head)

    def observe(self, case: MotionProbe) -> Observation:
        self.cleanup(case)
        cases = tuple(
            routes.RouteCase(r.head, r.channel, r.segment, r.length_mm) for r in CHAIN_ROUTES
        )
        frames = capture_frames(cases, case.lifts_mm)
        selected, report = select_motion_routes(cases, frames)
        if selected is None:
            return Observation("not_found", report)
        if case.insert_obstacle:
            endpoints = [
                index
                for index, frame in enumerate(frames)
                if frame.lift_mm in (case.lifts_mm[0], case.lifts_mm[-1])
            ]
            points = [
                p
                for index in endpoints
                for route in selected[index]
                for p in sample_path(route.curves).points_mm
            ]
            tree = KDTree(len(points))
            for index, point in enumerate(points):
                tree.insert(Vector(point), index)
            tree.balance()
            middle = next(
                index
                for index, frame in enumerate(frames)
                if frame.moving == case.obstacle_route.head
                and frame.lift_mm == case.lifts_mm[len(case.lifts_mm) // 2]
            )
            route_index = next(
                index
                for index, route in enumerate(cases)
                if (route.head, route.channel, route.segment)
                == (
                    case.obstacle_route.head,
                    case.obstacle_route.channel,
                    case.obstacle_route.segment,
                )
            )
            middle_points = sample_path(selected[middle][route_index].curves).points_mm
            point = max(middle_points, key=lambda p: tree.find(Vector(p))[2])
            endpoint_distance = tree.find(Vector(point))[2]
            if endpoint_distance <= 10:
                raise ValueError("No isolated middle-path location for obstruction control")
            bpy.ops.mesh.primitive_cube_add(size=0.004, location=Vector(point) / 1000)
            self.blocker = bpy.context.object
            self.blocker.name = "MOTION_CHECK_middle_blocker"
            obstacle = routes.RouteObstacles()
            name = self.blocker.name
            for frame in frames:
                frame.obstacles.meshes[name] = obstacle.meshes[name]
                frame.obstacles.bounds[name] = obstacle.bounds[name]
                frame.obstacles.closed.add(name)
            report["blocker"] = {"position_mm": point, "endpoint_distance_mm": endpoint_distance}
        replay = validate_motion(cases, frames, selected)
        report["replay"] = [asdict(row) for row in replay]
        report["selected"] = [[asdict(route) for route in row] for row in selected]
        blocked = any(row.hits for row in replay)
        if case.insert_obstacle:
            assert self.blocker is not None
            if any(
                row.hits for row in replay if row.lift_mm in (case.lifts_mm[0], case.lifts_mm[-1])
            ):
                raise ValueError("Obstruction control must leave both endpoints clear")
            if not any(
                hit.get("object") == self.blocker.name for row in replay for hit in row.hits
            ):
                raise ValueError("Intermediate obstacle was not rejected")
        elif not blocked and self.preview is not None:
            for frame, row in zip(frames, selected, strict=True):
                model.pose("capillary", 0, frame.lift_mm if frame.moving == "capillary" else 0)
                model.pose("pH_temp", 0, frame.lift_mm if frame.moving == "pH_temp" else 0)
                colors = ((0.05, 0.25, 0.85, 1), (0.85, 0.15, 0.05, 1), (0.02, 0.55, 0.25, 1))
                for index, route in enumerate(row):
                    routes.draw_route(route, colors[index // 3])
                    self.drawn.add("RESEARCH_route_" + route.boundary.name.replace("/", "_"))
                self.preview(f"motion-{frame.moving}-{frame.lift_mm:03.0f}")
        return Observation("blocked" if blocked else "clear", report)
