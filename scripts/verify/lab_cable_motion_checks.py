"""Reusable motion fixture: sampled family continuity and an intermediate-only obstacle."""

from collections.abc import Callable
from dataclasses import asdict
from unittest.mock import patch

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

from scripts import lab_cable_motion as motion
from scripts import lab_cable_routes as routes
from scripts import model_lab_platform as model
from scripts.lab_cable_motion import capture_frames, refit_motion_routes, validate_motion
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
        verify_replay_cache()
        verify_cached_scene_changes()
        cases = tuple(
            routes.RouteCase(r.head, r.channel, r.segment, r.length_mm) for r in CHAIN_ROUTES
        )
        frames = capture_frames(cases, case.points)
        selected, report = refit_motion_routes(frames, case.families)
        if selected is None:
            return Observation("not_found", report)
        endpoints = [
            index
            for index, frame in enumerate(frames)
            if frame.path == "lift" and frame.lift_mm in (0, 100)
        ]
        if case.insert_obstacle:
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
                and frame.path == "lift"
                and frame.lift_mm == 50
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
        with patch.object(motion, "sample_path", wraps=sample_path) as sampler:
            replay = validate_motion(cases, frames, selected)
            if sampler.call_count != len(frames) * len(cases):
                raise ValueError("Motion must sample each segment once per frame")
            report["route_sample_calls"] = sampler.call_count
        report["replay"] = [asdict(row) for row in replay]
        report["selected"] = [[asdict(route) for route in row] for row in selected]
        blocked = any(row.hits for row in replay)
        if case.insert_obstacle:
            assert self.blocker is not None
            if any(replay[index].hits for index in endpoints):
                raise ValueError("Obstruction control must leave both endpoints clear")
            if not any(
                hit.get("object") == self.blocker.name for row in replay for hit in row.hits
            ):
                raise ValueError("Intermediate obstacle was not rejected")
        elif not blocked and self.preview is not None:
            for frame, row in zip(frames, selected, strict=True):
                for head in ("capillary", "pH_temp"):
                    model.pose(
                        head,
                        frame.forward_mm if frame.moving == head else 0,
                        frame.lift_mm if frame.moving == head else 0,
                    )
                colors = ((0.05, 0.25, 0.85, 1), (0.85, 0.15, 0.05, 1), (0.02, 0.55, 0.25, 1))
                for index, route in enumerate(row):
                    routes.draw_route(route, colors[index // 3])
                    self.drawn.add("RESEARCH_route_" + route.boundary.name.replace("/", "_"))
                self.preview(
                    f"motion-{frame.path}-{frame.moving}-{frame.forward_mm:+04.0f}-{frame.lift_mm:03.0f}"
                )
        return Observation("blocked" if blocked else "clear", report)


def verify_replay_cache() -> None:
    """Changed curve, radius and sampling bounds must not reuse an earlier verdict."""
    from dataclasses import replace

    from src.core.domain.cable_paths import CubicPath

    first = CubicPath(((0, 0, 0), (10, 0, 0), (20, 0, 0), (30, 0, 0)))
    near = CubicPath(((0, 3, 0), (10, 3, 0), (20, 3, 0), (30, 3, 0)))
    far = CubicPath(((0, 30, 0), (10, 30, 0), (20, 30, 0), (30, 30, 0)))
    with routes.replay_cache() as cache:
        a, b, c = (cache.sample((curve,)) for curve in (first, near, far))
        assert cache.sample((first,)) == a
        assert cache.sample.cache_info().hits == 1
        finer = cache.sample((first,), step_mm=0.05)
        assert len(finer.points_mm) > len(a.points_mm)
        assert cache.sample.cache_info().misses == 4
        assert cache.pair(a, 1, c, 1) is None
        assert cache.pair(a, 1, b, 1) is None
        hit = cache.pair(a, 2, b, 2)
        assert hit is not None and hit["reason"] == "wire_contact"
        assert cache.pair(a, 1, replace(b, deviation_mm=2), 1) is not None
        assert cache.pair.cache_info().misses == 4
        for i in range(520):
            cache.self_hit(a, 1 + i / 10000)
        assert cache.self_hit.cache_info().currsize == 512
    assert cache.sample.cache_info().currsize == 0
    assert cache.pair.cache_info().currsize == 0
    assert cache.self_hit.cache_info().currsize == 0
    with routes.replay_cache() as fresh:
        fresh.sample((first,))
        assert fresh.sample.cache_info().misses == 1
        assert fresh.sample.cache_info().hits == 0
    try:
        with routes.replay_cache() as interrupted:
            interrupted.sample((first,))
            raise RuntimeError("cache cleanup control")
    except RuntimeError:
        assert interrupted.sample.cache_info().currsize == 0


def verify_cached_scene_changes() -> None:
    """Reusing curve math must still observe a moved obstacle and isolate returned hits."""
    from src.core.domain.cable_paths import CubicPath
    from src.core.planning.cable_path_plan import RouteBoundary, RouteCandidate

    curve = CubicPath(((10000, 0, 0), (10010, 5, 0), (10020, 5, 0), (10030, 0, 0)))
    sampled = sample_path((curve,))
    boundary = RouteBoundary(
        "cache-control",
        curve.controls_mm[0],
        curve.controls_mm[-1],
        (1, 0, 0),
        (1, 0, 0),
        (sampled.length_lower_mm + sampled.length_upper_mm) / 2,
        cable_radius_mm=2,
    )
    candidate = RouteCandidate(boundary, (curve,), (1, 1, 1, 1, 1), boundary.length_mm, 100)
    bpy.ops.mesh.primitive_cube_add(size=0.004, location=(20, 0, 0))
    blocker = bpy.context.object
    blocker.name = "CACHE_CHECK_moving_blocker"
    try:
        with routes.replay_cache() as cache:
            for blocked in (False, True, False):
                blocker.location = (
                    Vector(sampled.points_mm[len(sampled.points_mm) // 2]) / 1000
                    if blocked
                    else Vector((20, 0, 0))
                )
                obstacles = routes.RouteObstacles()
                actual = routes.candidate_hit(candidate, sampled, obstacles, cache=cache)
                expected = routes.candidate_hit(candidate, sampled, obstacles)
                assert actual == expected
                assert (actual is not None) == blocked
                if blocked:
                    assert actual is not None and actual["object"] == blocker.name
            assert cache.self_hit.cache_info().hits == 2
            obstacles = routes.RouteObstacles()
            hit = routes.candidate_hit(
                candidate, sampled, obstacles, neighbours=((candidate, sampled),), cache=cache
            )
            assert hit is not None and hit["reason"] == "wire_contact"
            hit["samples"] = [-999, -999]
            repeated = routes.candidate_hit(
                candidate, sampled, obstacles, neighbours=((candidate, sampled),), cache=cache
            )
            assert repeated is not None and repeated["samples"] != [-999, -999]
    finally:
        mesh = blocker.data
        bpy.data.objects.remove(blocker, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
