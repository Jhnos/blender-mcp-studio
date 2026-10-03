"""Measure and inspect cable-route data against the current Blender assembly."""

from collections import Counter
from dataclasses import asdict, dataclass
from math import dist, isfinite, pi
from typing import Literal

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from scripts.blender_mesh_primitives import material
from scripts.lab_electrode_routes import channels, guide_frame
from src.core.domain.cable_paths import SampledPath, sample_path
from src.core.domain.lab_station import CableGuideSpec, Point
from src.core.planning.cable_path_plan import (
    RouteBoundary,
    RouteCandidate,
    RouteSearchSpec,
    candidates,
)


@dataclass(frozen=True, slots=True)
class RouteCase:
    head: Literal["capillary", "pH_temp"]
    channel: int
    segment: Literal["base", "joint", "head"]
    length_mm: float
    cable_radius_mm: float = 3
    lead_mm: float = 6
    base_port_mm: Point | None = None

    def __post_init__(self) -> None:
        if self.head not in ("capillary", "pH_temp") or self.segment not in (
            "base",
            "joint",
            "head",
        ):
            raise ValueError("Unknown cable route interface")
        if type(self.channel) is not int or self.channel not in range(
            1 if self.head == "capillary" else 2
        ):
            raise ValueError("Cable channel is not present on this head")
        if not all(
            isfinite(v) and v > 0 for v in (self.length_mm, self.cable_radius_mm, self.lead_mm)
        ):
            raise ValueError("Cable dimensions must be positive and finite")
        if self.base_port_mm is not None and (
            len(self.base_port_mm) != 3 or not all(isfinite(v) for v in self.base_port_mm)
        ):
            raise ValueError("Base port must be a finite mm vector")


def point(vector: Vector, factor: float = 1) -> Point:
    return float(vector.x * factor), float(vector.y * factor), float(vector.z * factor)


def probe_name(case: RouteCase) -> str:
    suffix = "0" if case.head == "capillary" else ("-7" if case.channel == 0 else "7")
    return f"S_{case.head}_probe_{suffix}"


def measure(case: RouteCase) -> RouteBoundary:
    """Read current evaluated transforms; settings do not guess world-space anchors."""
    bpy.context.view_layer.update()
    frames = [
        bpy.data.objects[f"S_{case.head}_{r}"].matrix_world @ guide_frame(case.head, r)
        for r in ("upper", "lower")
    ]
    y = channels(case.head)[case.channel]
    guides = [f @ Vector((CableGuideSpec().channel_x_mm / 1000, y / 1000, 0)) for f in frames]
    axes = [(f.to_3x3() @ Vector((0, 0, 1))).normalized() for f in frames]
    if case.segment == "joint":
        a, b, u, v = guides[0], guides[1], axes[0], axes[1]
    elif case.segment == "base":
        side = -1 if case.head == "capillary" else 1
        port = case.base_port_mm or (side * 121, 45 if side < 0 else 55 - 20 * case.channel, 50)
        a, b, u, v = Vector(port) / 1000, guides[0], Vector((side, 0, 0)), axes[0]
    else:
        probe = bpy.data.objects[probe_name(case)]
        bounds = [Vector(p) for p in probe.bound_box]
        top = Vector(
            (
                (min(p.x for p in bounds) + max(p.x for p in bounds)) / 2,
                (min(p.y for p in bounds) + max(p.y for p in bounds)) / 2,
                max(p.z for p in bounds),
            )
        )
        a, b, u, v = (
            guides[1],
            probe.matrix_world @ top,
            axes[1],
            -(probe.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized(),
        )
    return RouteBoundary(
        f"{case.head}/{case.channel}/{case.segment}",
        point(a, 1000),
        point(b, 1000),
        point(u),
        point(v),
        case.length_mm,
        case.cable_radius_mm,
        case.lead_mm,
    )


class RouteObstacles:
    """One immutable mesh snapshot per pose; no repeated tree construction per curve."""

    def __init__(self) -> None:
        bpy.context.view_layer.update()
        self.meshes: dict[str, BVHTree] = {}
        self.closed: set[str] = set()
        self.bounds: dict[str, tuple[Vector, Vector]] = {}
        for obj in bpy.data.objects:
            if obj.type != "MESH" or obj.hide_render or obj.name.startswith("RESEARCH_"):
                continue
            vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
            if not vertices:
                continue
            incidence = Counter(edge for face in obj.data.polygons for edge in face.edge_keys)
            if incidence and all(count == 2 for count in incidence.values()):
                self.closed.add(obj.name)
            polygons = [tuple(face.vertices) for face in obj.data.polygons]
            if obj.matrix_world.determinant() < 0:
                polygons = [tuple(reversed(face)) for face in polygons]
            self.meshes[obj.name] = BVHTree.FromPolygons(vertices, polygons)
            self.bounds[obj.name] = (
                Vector(tuple(min(v[i] for v in vertices) for i in range(3))),
                Vector(tuple(max(v[i] for v in vertices) for i in range(3))),
            )

    def first_hit(
        self, sampled: SampledPath, request: RouteBoundary, terminal: str | None = None
    ) -> dict[str, object] | None:
        radius = sampled.inspection_radius_mm(request.cable_radius_mm) / 1000
        points = [Vector(p) / 1000 for p in sampled.points_mm]
        end = Vector(request.end_mm) / 1000
        axis = -Vector(request.end_direction).normalized()
        if terminal is not None:
            terminal_tree = self.meshes.get(terminal)
            if terminal_tree is None:
                raise ValueError("Cable terminal mesh is missing: " + terminal)
            surface = terminal_tree.find_nearest(end)
            if surface[0] is None or surface[3] > 1e-6 or surface[1].dot(axis) < 0.999:
                return {"object": terminal, "reason": "terminal_not_on_outward_face"}
        for name, tree in self.meshes.items():
            lo, hi = self.bounds[name]
            # Reject an entirely embedded path too; surface distances alone miss it.
            near = tree.find_nearest(points[0])
            if (
                name in self.closed
                and all(lo[i] <= points[0][i] <= hi[i] for i in range(3))
                and near[0] is not None
                and (points[0] - near[0]).dot(near[1]) < -1e-7
            ):
                return {
                    "object": name,
                    "reason": "start_inside",
                    "point_mm": point(points[0], 1000),
                }
            for p in points:
                if any(p[i] < lo[i] - radius or p[i] > hi[i] + radius for i in range(3)):
                    continue
                near = tree.find_nearest(p, radius)
                if near[0] is None:
                    continue
                if name == terminal:
                    delta = p - end
                    axial = delta.dot(axis)
                    if (
                        -0.000001 <= axial <= request.lead_mm / 1000 + 0.000001
                        and (delta - axis * axial).length < 0.00001
                    ):
                        continue
                return {
                    "object": name,
                    "reason": "envelope_contact",
                    "point_mm": point(p, 1000),
                    "distance_mm": float(near[3] * 1000),
                }
        return None


def nonlocal_self_hit(sampled: SampledPath, radius_mm: float) -> dict[str, object] | None:
    """Reject distant portions occupying one tube envelope; local neighbours are contiguous."""
    points = sampled.points_mm
    arclength = [0.0]
    tree = KDTree(len(points))
    for index, p in enumerate(points):
        tree.insert(Vector(p), index)
        if index:
            arclength.append(arclength[-1] + dist(points[index - 1], p))
    tree.balance()
    threshold = 2 * radius_mm + sampled.max_step_mm + 2 * sampled.deviation_mm
    local_arc = pi * radius_mm + sampled.max_step_mm
    for index, p in enumerate(points):
        for _, other, distance in tree.find_range(Vector(p), threshold):
            if other > index and arclength[other] - arclength[index] > local_arc:
                return {
                    "reason": "nonlocal_self_contact",
                    "samples": [index, other],
                    "distance_mm": float(distance),
                }
    return None


def select_route(
    case: RouteCase, search: RouteSearchSpec | None = None
) -> tuple[RouteCandidate | None, dict[str, object]]:
    search = search or RouteSearchSpec()
    request = measure(case)
    obstacles = RouteObstacles()
    attempts: list[dict[str, object]] = []
    choices = candidates(request, search)
    for candidate in choices:
        sampled = sample_path(candidate.curves)
        if (
            max(
                abs(sampled.length_lower_mm - request.length_mm),
                abs(sampled.length_upper_mm - request.length_mm),
            )
            > 0.05
        ):
            attempts.append({"reason": "length_interval"})
            continue
        self_hit = nonlocal_self_hit(sampled, request.cable_radius_mm)
        if self_hit is not None:
            attempts.append(self_hit)
            continue
        hit = obstacles.first_hit(
            sampled, request, probe_name(case) if case.segment == "head" else None
        )
        if hit is None:
            return candidate, {
                "case": asdict(case),
                "search": asdict(search),
                "boundary": asdict(request),
                "candidate_count": len(choices),
                "rejected": attempts,
                "length_bounds_mm": [sampled.length_lower_mm, sampled.length_upper_mm],
                "sampled_min_radius_mm": candidate.sampled_min_radius_mm,
                "selected_parameters_mm": candidate.parameters_mm,
                "curve_controls_mm": [c.controls_mm for c in candidate.curves],
                "scope": "One geometric route in one pose; no wire-pair, material or motion qualification",
            }
        attempts.append(hit)
    return None, {
        "case": asdict(case),
        "search": asdict(search),
        "boundary": asdict(request),
        "candidate_count": len(choices),
        "rejected": attempts,
        "scope": "No clear candidate in this bounded search; not a proof that no path exists",
    }


def draw_route(candidate: RouteCandidate, color: tuple[float, float, float, float]) -> None:
    name = "RESEARCH_route_" + candidate.boundary.name.replace("/", "_")
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    sampled = sample_path(candidate.curves)
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = candidate.boundary.cable_radius_mm / 1000
    data.bevel_resolution = 3
    spline = data.splines.new("POLY")
    spline.points.add(len(sampled.points_mm) - 1)
    for target, p in zip(spline.points, sampled.points_mm, strict=True):
        target.co = (p[0] / 1000, p[1] / 1000, p[2] / 1000, 1)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(material(name + "_material", color))
