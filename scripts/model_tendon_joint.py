"""Generate a two-cell, four-DOF tendon universal-joint concept in Blender.

Run inside Blender (normally through the addon execute_code bridge). Dimensions in the
domain spec are millimetres; this adapter converts them to Blender metres at the boundary.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tendon_joint_render import (  # noqa: E402
    add_text,
    duplicate_print_layout,
    m,
    render_views,
    setup_render,
)
from src.core.domain.tendon_joint import TendonJointSpec  # noqa: E402

PREFIX = "TJ_"
OUTPUT_DIR = Path(os.environ.get("TENDON_JOINT_OUTPUT_DIR", "/tmp/blender-mcp-tendon-joint"))
SPEC = TendonJointSpec()


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    mat.metallic = metallic
    mat.roughness = 0.28 if metallic else 0.42
    principled = mat.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = mat.roughness
    return mat


PRINT_MAT = material("TJ_MAT_PRINTABLE", (0.12, 0.16, 0.22, 1.0), metallic=0.2)
MALE_MAT = material("TJ_MAT_MALE", (1.0, 0.28, 0.055, 1.0), metallic=0.1)
X_MAT = material("TJ_MAT_X_AXIS", (0.95, 0.08, 0.08, 1.0))
Y_MAT = material("TJ_MAT_Y_AXIS", (0.08, 0.3, 1.0, 1.0))
TENDON_MAT = material("TJ_MAT_TENDON", (0.02, 0.92, 0.95, 1.0), metallic=0.15)
TEXT_MAT = material("TJ_MAT_TEXT", (0.92, 0.94, 1.0, 1.0))
FLOOR_MAT = material("TJ_MAT_FLOOR", (0.025, 0.032, 0.045, 1.0))


def clear_previous() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name.startswith(PREFIX):
            bpy.data.collections.remove(collection)


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)


def assign(obj: bpy.types.Object, mat) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def apply_transform(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.select_set(False)


def add_cylinder(
    name: str,
    radius_mm: float,
    depth_mm: float,
    location_mm: tuple[float, float, float],
    axis: str = "Z",
    vertices: int = 32,
) -> bpy.types.Object:
    rotation = {
        "X": (0.0, math.pi / 2.0, 0.0),
        "Y": (math.pi / 2.0, 0.0, 0.0),
        "Z": (0.0, 0.0, 0.0),
    }[axis]
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=m(radius_mm),
        depth=m(depth_mm),
        location=tuple(m(value) for value in location_mm),
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    apply_transform(obj)
    return obj


def add_box(
    name: str,
    dimensions_mm: tuple[float, float, float],
    location_mm: tuple[float, float, float],
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=tuple(m(value) for value in location_mm))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple(m(value) for value in dimensions_mm)
    apply_transform(obj)
    return obj


def boolean(target: bpy.types.Object, cutter: bpy.types.Object, operation: str) -> None:
    bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(name=f"TJ_{operation}", type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def bevel(obj: bpy.types.Object, width_mm: float = 0.8) -> None:
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new(name="TJ_PRINT_BEVEL", type="BEVEL")
    modifier.width = m(width_mm)
    modifier.segments = 2
    modifier.limit_method = "ANGLE"
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def cleanup_mesh(obj: bpy.types.Object) -> None:
    mesh = obj.data
    editable = bmesh.new()
    editable.from_mesh(mesh)
    bmesh.ops.remove_doubles(editable, verts=editable.verts, dist=m(0.005))
    bmesh.ops.dissolve_degenerate(editable, edges=editable.edges, dist=m(0.001))
    bmesh.ops.recalc_face_normals(editable, faces=editable.faces)
    editable.to_mesh(mesh)
    editable.free()
    mesh.update()


def create_disc(index: int, z_mm: float, assembly: bpy.types.Collection) -> bpy.types.Object:
    role = ("BASE", "MID", "TIP")[index]
    disc = add_cylinder(
        f"TJ_PRINTABLE_DISC_{index}_{role}",
        SPEC.disc_diameter_mm / 2.0,
        SPEC.disc_thickness_mm,
        (0.0, 0.0, z_mm),
    )
    move_to_collection(disc, assembly)
    assign(disc, PRINT_MAT)
    for hole_index, (x_mm, y_mm) in enumerate(SPEC.tendon_positions_mm, start=1):
        cutter = add_cylinder(
            f"TJ_CUT_TENDON_{index}_{hole_index}",
            SPEC.tendon_hole_diameter_mm / 2.0,
            SPEC.disc_thickness_mm + 4.0,
            (x_mm, y_mm, z_mm),
        )
        boolean(disc, cutter, "DIFFERENCE")
    return disc


def add_snap_yoke(
    disc: bpy.types.Object,
    disc_z_mm: float,
    joint_z_mm: float,
    axis: str,
    side: str,
) -> None:
    """Add two flexible socket arms to a disc and cut a C-shaped snap opening."""
    radius_mm = SPEC.disc_diameter_mm / 2.0 - 6.0
    overlap_mm = 1.0
    lip_mm = 4.2
    opening_mm = SPEC.pin_diameter_mm * 0.72

    disc_surface = disc_z_mm + (
        SPEC.disc_thickness_mm / 2.0 if side == "UP" else -SPEC.disc_thickness_mm / 2.0
    )
    arm_end = joint_z_mm + (lip_mm if side == "UP" else -lip_mm)
    root = disc_surface - overlap_mm if side == "UP" else disc_surface + overlap_mm
    low, high = sorted((root, arm_end))
    height_mm = high - low
    arm_z_mm = (low + high) / 2.0

    for sign in (-1.0, 1.0):
        if axis == "X":
            location = (sign * radius_mm, 0.0, arm_z_mm)
            dimensions = (SPEC.yoke_wall_mm, SPEC.yoke_width_mm, height_mm)
        else:
            location = (0.0, sign * radius_mm, arm_z_mm)
            dimensions = (SPEC.yoke_width_mm, SPEC.yoke_wall_mm, height_mm)
        arm = add_box(f"TJ_ARM_{disc.name}_{axis}_{sign:+.0f}", dimensions, location)
        boolean(disc, arm, "UNION")

        socket_location = (
            (sign * radius_mm, 0.0, joint_z_mm)
            if axis == "X"
            else (0.0, sign * radius_mm, joint_z_mm)
        )
        socket = add_cylinder(
            f"TJ_CUT_SOCKET_{disc.name}_{axis}_{sign:+.0f}",
            SPEC.socket_diameter_mm / 2.0,
            SPEC.yoke_wall_mm + 3.0,
            socket_location,
            axis=axis,
        )
        boolean(disc, socket, "DIFFERENCE")

        opening_end = arm_end + (1.0 if side == "UP" else -1.0)
        slit_low, slit_high = sorted((joint_z_mm, opening_end))
        slit_height = slit_high - slit_low
        slit_z = (slit_low + slit_high) / 2.0
        if axis == "X":
            slit_dimensions = (SPEC.yoke_wall_mm + 3.0, opening_mm, slit_height)
            slit_location = (sign * radius_mm, 0.0, slit_z)
        else:
            slit_dimensions = (opening_mm, SPEC.yoke_wall_mm + 3.0, slit_height)
            slit_location = (0.0, sign * radius_mm, slit_z)
        slit = add_box(
            f"TJ_CUT_SLIT_{disc.name}_{axis}_{sign:+.0f}", slit_dimensions, slit_location
        )
        boolean(disc, slit, "DIFFERENCE")


def create_gimbal(cell: int, z_mm: float, assembly: bpy.types.Collection) -> bpy.types.Object:
    radius_mm = SPEC.disc_diameter_mm / 2.0 - 6.0
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        radius=m(4.2),
        location=(0.0, 0.0, m(z_mm)),
    )
    gimbal = bpy.context.object
    gimbal.name = f"TJ_PRINTABLE_GIMBAL_{cell}"
    move_to_collection(gimbal, assembly)
    assign(gimbal, MALE_MAT)
    for axis in ("X", "Y"):
        pin = add_cylinder(
            f"TJ_MALE_{cell}_{axis}",
            SPEC.pin_diameter_mm / 2.0,
            2.0 * radius_mm + SPEC.yoke_wall_mm,
            (0.0, 0.0, z_mm),
            axis=axis,
        )
        boolean(gimbal, pin, "UNION")
    bevel(gimbal, 0.45)
    cleanup_mesh(gimbal)
    return gimbal


def create_axis_guide(
    name: str,
    z_mm: float,
    axis: str,
    guides: bpy.types.Collection,
) -> None:
    guide = add_cylinder(name, 0.55, 56.0, (0.0, 0.0, z_mm), axis=axis, vertices=32)
    move_to_collection(guide, guides)
    assign(guide, X_MAT if axis == "X" else Y_MAT)
    guide.hide_viewport = True


def create_tendon_guides(z_min_mm: float, z_max_mm: float, guides: bpy.types.Collection) -> None:
    depth_mm = z_max_mm - z_min_mm
    z_mm = (z_min_mm + z_max_mm) / 2.0
    for index, (x_mm, y_mm) in enumerate(SPEC.tendon_positions_mm, start=1):
        tendon = add_cylinder(
            f"TJ_TENDON_{index}",
            0.62,
            depth_mm,
            (x_mm, y_mm, z_mm),
            vertices=32,
        )
        move_to_collection(tendon, guides)
        assign(tendon, TENDON_MAT)
        tendon.hide_viewport = True


def _build_scene() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"

    assembly = collection("TJ_ASSEMBLY")
    guides = collection("TJ_GUIDES")
    print_layout = collection("TJ_PRINT_LAYOUT")

    discs = [create_disc(index, index * SPEC.disc_pitch_mm, assembly) for index in range(3)]
    gimbals: list[bpy.types.Object] = []
    labels: list[bpy.types.Object] = []
    for cell in range(1, SPEC.cell_count + 1):
        lower_z = (cell - 1) * SPEC.disc_pitch_mm
        upper_z = cell * SPEC.disc_pitch_mm
        joint_z = (lower_z + upper_z) / 2.0
        add_snap_yoke(discs[cell - 1], lower_z, joint_z, "X", "UP")
        add_snap_yoke(discs[cell], upper_z, joint_z, "Y", "DOWN")
        gimbals.append(create_gimbal(cell, joint_z, assembly))
        create_axis_guide(f"TJ_AXIS_J{cell}_X", joint_z, "X", guides)
        create_axis_guide(f"TJ_AXIS_J{cell}_Y", joint_z, "Y", guides)
        labels.extend(
            (
                add_text(
                    f"TJ_LABEL_J{cell}_X",
                    f"J{cell}  X",
                    (30.0, -8.0, joint_z + 3.0),
                    TEXT_MAT,
                ),
                add_text(
                    f"TJ_LABEL_J{cell}_Y",
                    f"J{cell}  Y",
                    (-27.0, -18.0, joint_z - 2.0),
                    TEXT_MAT,
                ),
            )
        )

    for disc in discs:
        bevel(disc, 0.75)
        cleanup_mesh(disc)
    create_tendon_guides(-8.0, SPEC.assembled_height_mm + 8.0, guides)
    labels.extend(
        (
            add_text(
                "TJ_LABEL_TITLE",
                "2 CELLS  /  4 DOF",
                (0.0, -8.0, SPEC.assembled_height_mm + 14.0),
                TEXT_MAT,
                5.0,
            ),
            add_text(
                "TJ_LABEL_TENDON",
                "4 x 2.8 mm TENDON",
                (-30.0, -24.0, 5.0),
                TEXT_MAT,
                3.2,
            ),
        )
    )

    printable_parts = [*discs, *gimbals]
    layout_objects = duplicate_print_layout(printable_parts, print_layout)
    camera, _support_objects = setup_render(SPEC, FLOOR_MAT, assign)
    assembly_objects = [*printable_parts]
    render_views(OUTPUT_DIR, camera, assembly_objects, guides, labels, layout_objects)

    scene["TJ_SPEC_MM"] = {
        "cell_count": SPEC.cell_count,
        "degrees_of_freedom": SPEC.degrees_of_freedom,
        "disc_diameter": SPEC.disc_diameter_mm,
        "pin_diameter": SPEC.pin_diameter_mm,
        "socket_diameter": SPEC.socket_diameter_mm,
        "tendon_hole_diameter": SPEC.tendon_hole_diameter_mm,
        "radial_clearance": SPEC.radial_clearance_mm,
        "minimum_wall": SPEC.minimum_wall_mm,
        "maximum_articulation": SPEC.maximum_articulation_deg,
    }
    scene["TJ_PRINTABLE_PARTS"] = [obj.name for obj in printable_parts]
    scene["TJ_AXIS_NAMES"] = list(SPEC.axis_names)
    scene["TJ_DESIGN_NOTE"] = (
        "Concept prototype; validate line wear, snap fatigue, and load before use."
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_DIR / "tendon_joint_4dof.blend"))
    print(
        "TENDON_JOINT_READY",
        {
            "dof": SPEC.degrees_of_freedom,
            "axes": SPEC.axis_names,
            "parts": [obj.name for obj in printable_parts],
            "output": str(OUTPUT_DIR),
        },
    )


def main() -> None:
    clear_previous()
    external_visibility = [
        (obj, obj.hide_render, obj.hide_viewport)
        for obj in bpy.context.scene.objects
        if not obj.name.startswith(PREFIX)
    ]
    try:
        for obj, _, _ in external_visibility:
            obj.hide_render = True
            obj.hide_viewport = True
        _build_scene()
    finally:
        for obj, hide_render, hide_viewport in external_visibility:
            obj.hide_render = hide_render
            obj.hide_viewport = hide_viewport


if __name__ == "__main__":
    main()
