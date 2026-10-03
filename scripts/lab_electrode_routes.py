"""Removable arm-mounted cable guides; cable paths and elastic fit are separate qualifications."""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from scripts.blender_mesh_primitives import (
    add_cylinder,
    assign,
    boolean,
    material,
    refine_closed_mesh,
)
from scripts.hand_gates import shell_count
from scripts.hollow_hinge_render import look_at
from scripts.lab_station_joints import block
from scripts.lab_station_motion_check import tree
from src.core.domain.lab_station import CableGuideSpec


def guide_name(label: str, role: str) -> str:
    return f"LS_ROUTE_{label}_{role}"


def guide_frame(label: str, role: str) -> Matrix:
    side = (1 if label == "capillary" else -1) * (1 if role == "upper" else -1)
    return Matrix.Translation(
        (side * 0.0042, 0, CableGuideSpec.bar_station_mm / 1000)
    ) @ Matrix.Diagonal((1 if label == "capillary" else -1, 1, 1, 1))


def channels(label: str) -> tuple[float, ...]:
    spec = CableGuideSpec()
    pitch = spec.bore_mm + spec.wall_mm
    return (0,) if label == "capillary" else (-pitch / 2, pitch / 2)


def build_guides() -> None:
    spec = CableGuideSpec()
    cavity_x, cavity_y = spec.arm_cavity_mm
    outer_x, outer_y = cavity_x + 2 * spec.wall_mm, cavity_y + 2 * spec.wall_mm
    mat = material("ROUTE_graphite", (0.11, 0.14, 0.16, 1))
    for label in ("capillary", "pH_temp"):
        for role in ("upper", "lower"):
            name = guide_name(label, role)
            if bpy.data.objects.get(name):
                raise ValueError("Guide already exists: " + name)
            obj = block(name, (outer_x, outer_y, spec.depth_mm), (0, 0, 0), mat)
            for y in channels(label):
                ring = add_cylinder(
                    "ROUTE_TOOL",
                    spec.bore_mm / 2 + spec.wall_mm,
                    spec.depth_mm,
                    (spec.channel_x_mm, y, 0),
                )
                boolean(obj, ring, "UNION")
            boolean(
                obj,
                block("ROUTE_TOOL", (cavity_x, cavity_y, spec.depth_mm + 2), (0, 0, 0), mat),
                "DIFFERENCE",
            )
            boolean(
                obj,
                block(
                    "ROUTE_TOOL",
                    (outer_x, spec.arm_mouth_mm, spec.depth_mm + 2),
                    (-outer_x / 2, 0, 0),
                    mat,
                ),
                "DIFFERENCE",
            )
            for y in channels(label):
                boolean(
                    obj,
                    add_cylinder(
                        "ROUTE_TOOL", spec.bore_mm / 2, spec.depth_mm + 2, (spec.channel_x_mm, y, 0)
                    ),
                    "DIFFERENCE",
                )
                boolean(
                    obj,
                    block(
                        "ROUTE_TOOL",
                        (spec.bore_mm + 2 * spec.wall_mm, spec.wire_mouth_mm, spec.depth_mm + 2),
                        (spec.channel_x_mm + spec.bore_mm / 2 + spec.wall_mm, y, 0),
                        mat,
                    ),
                    "DIFFERENCE",
                )
            obj.data.transform(obj.matrix_world)
            obj.matrix_world = Matrix.Identity(4)
            frame = guide_frame(label, role)
            obj.data.transform(frame)
            if frame.determinant() < 0:
                obj.data.flip_normals()
            refine_closed_mesh(obj)
            obj.parent = bpy.data.objects[f"S_{label}_{role}"]
            obj.matrix_parent_inverse = Matrix.Identity(4)
            obj.matrix_basis = Matrix.Identity(4)
            assign(obj, mat)
            obj["route_guide"] = True
            obj["provisional_wire_od_mm"] = spec.wire_od_mm
    bpy.context.view_layer.update()


def verify_guides(*, required: bool = False, meshes: dict[str, BVHTree] | None = None) -> int:
    """Check all actual guide meshes against every structural obstacle in this pose."""
    parents = {
        guide_name(label, role): f"S_{label}_{role}"
        for label in ("capillary", "pH_temp")
        for role in ("upper", "lower")
    }
    names = list(parents)
    present = [bpy.data.objects.get(name) for name in names]
    if not required and not any(present):
        return 0
    if any(obj is None for obj in present):
        raise ValueError("Missing arm cable guide")
    guides = [bpy.data.objects[name] for name in names]
    obstacles = (
        meshes
        if meshes is not None
        else {
            obj.name: tree(obj)
            for obj in bpy.data.objects
            if obj.type == "MESH"
            and not obj.hide_render
            and obj.name.startswith(("S_", "LS_FIT_", "LS_REF_vessel", "LS_ROUTE_"))
        }
    )
    for guide in guides:
        if guide.parent is None or guide.parent.name != parents[guide.name]:
            raise ValueError("Cable guide attached to wrong arm: " + guide.name)
        moved = obstacles[guide.name]
        hits = [
            name
            for name, obstacle in obstacles.items()
            if name != guide.name and moved.overlap(obstacle)
        ]
        if hits:
            raise ValueError(f"Cable guide collision: {guide.name}, {hits}")
        if guide.parent is None or guide.matrix_basis != Matrix.Identity(4):
            raise ValueError("Cable guide detached from arm: " + guide.name)
    return len(guides)


def verify_guide_geometry() -> dict[str, object]:
    spec = CableGuideSpec()
    rows = {}
    for label in ("capillary", "pH_temp"):
        upper = guide_frame(label, "upper").to_3x3() @ Vector((1, 0, 0))
        lower = guide_frame(label, "lower").to_3x3() @ Vector((1, 0, 0))
        if upper.dot(lower) < 0.999:
            raise ValueError("Cable guide channels face opposite sides")
        for role in ("upper", "lower"):
            obj = bpy.data.objects[guide_name(label, role)]
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            invalid = any(not edge.is_manifold for edge in mesh.edges)
            mesh.free()
            if invalid or shell_count(obj) != 1:
                raise ValueError("Cable guide is not one closed solid")
            frame = guide_frame(label, role)
            rays = 0
            for y in channels(label):
                for radius, blocked in (
                    (0, False),
                    (spec.wire_od_mm / 2, False),
                    (spec.bore_mm / 2 + spec.wall_mm / 2, True),
                ):
                    for angle in (60, 120, 180, 240, 300):
                        point = Vector(
                            (
                                (spec.channel_x_mm + radius * math.cos(math.radians(angle))) / 1000,
                                (y + radius * math.sin(math.radians(angle))) / 1000,
                                -0.02,
                            )
                        )
                        hit = obj.ray_cast(frame @ point, frame.to_3x3() @ Vector((0, 0, 1)))[0]
                        if hit != blocked:
                            raise ValueError("Cable guide channel/wall mismatch: " + obj.name)
                        rays += 1
            original = obj.matrix_basis.copy()
            arm = tree(obj.parent)
            try:
                for shift in (-0.002, 0.002):
                    obj.matrix_basis = Matrix.Translation((shift, 0, 0)) @ original
                    bpy.context.view_layer.update()
                    if not tree(obj).overlap(arm):
                        raise ValueError("Cable guide has no radial stop: " + obj.name)
            finally:
                obj.matrix_basis = original
                bpy.context.view_layer.update()
            rows[obj.name] = {
                "channels": len(channels(label)),
                "ray_samples": rays,
                "radial_stop_samples": 2,
            }
    return {
        "guides": rows,
        "assumed_wire_od_mm": spec.wire_od_mm,
        "scope": "Rigid guide geometry and clearance; no elastic snap, cable routing, bend radius or retention-force qualification.",
    }


def verify_guide_controls() -> dict[str, str]:
    obj = bpy.data.objects[guide_name("capillary", "upper")]
    original_name, original_matrix = obj.name, obj.matrix_basis.copy()
    original_parent = obj.parent
    results = {}
    for case in ("missing", "collision", "wrong_parent"):
        try:
            if case == "missing":
                obj.name = "ROUTE_DIAGNOSTIC_missing"
            elif case == "wrong_parent":
                obj.parent = bpy.data.objects["S_pH_temp_upper"]
            else:
                obj.matrix_basis = Matrix.Translation((0.001, 0, 0))
            bpy.context.view_layer.update()
            try:
                verify_guides(required=True)
            except ValueError as error:
                expected = {
                    "missing": "Missing arm cable guide",
                    "collision": "Cable guide collision",
                    "wrong_parent": "Cable guide attached to wrong arm",
                }[case]
                if expected not in str(error):
                    raise
                results[case] = str(error)
            else:
                raise ValueError("Invalid guide accepted: " + case)
        finally:
            obj.parent = original_parent
            obj.name, obj.matrix_basis = original_name, original_matrix
            bpy.context.view_layer.update()
        verify_guides(required=True)
    reflection = Matrix.Translation((0.0084, 0, 0)) @ Matrix.Diagonal((-1, 1, 1, 1))
    try:
        obj.data.transform(reflection)
        obj.data.flip_normals()
        try:
            verify_guide_geometry()
        except ValueError as error:
            if "Cable guide channel/wall mismatch" not in str(error):
                raise
            results["reversed_channel"] = str(error)
        else:
            raise ValueError("Reversed cable guide accepted")
    finally:
        obj.data.transform(reflection)
        obj.data.flip_normals()
    verify_guide_geometry()
    return results


def render_guide_detail(output: Path) -> None:
    scene = bpy.context.scene
    camera = scene.camera
    original, scale = camera.matrix_world.copy(), camera.data.ortho_scale
    frame = bpy.data.objects[guide_name("pH_temp", "lower")].matrix_world @ guide_frame(
        "pH_temp", "lower"
    )
    try:
        camera.location = frame @ Vector((0.040, -0.040, 0.035))
        camera.data.ortho_scale = 0.065
        look_at(camera, tuple(v * 1000 for v in frame @ Vector((0.006, 0, 0))))
        scene.render.filepath = str(output / "guide-detail.png")
        bpy.ops.render.render(write_still=True)
    finally:
        camera.matrix_world, camera.data.ortho_scale = original, scale
