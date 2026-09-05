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
from src.core.domain.tendon_joint import TendonVertebraSpec  # noqa: E402

PREFIX = "TJ_"
OUTPUT_DIR = Path(os.environ.get("TENDON_JOINT_OUTPUT_DIR", "/tmp/blender-mcp-tendon-joint"))
SPEC = TendonVertebraSpec()


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
PRINT_ALT_MAT = material("TJ_MAT_PRINTABLE_ALT", (0.22, 0.3, 0.4, 1.0), metallic=0.15)
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


def add_uv_sphere(name: str, diameter_mm: float, z_mm: float) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        radius=m(diameter_mm / 2.0),
        location=(0.0, 0.0, m(z_mm)),
    )
    sphere = bpy.context.object
    sphere.name = name
    return sphere


def create_vertebra(assembly: bpy.types.Collection) -> bpy.types.Object:
    """Create one reusable body with a male ball and a Y-split female socket."""
    vertebra = add_cylinder(
        "TJ_PRINTABLE_VERTEBRA_1",
        SPEC.body_diameter_mm / 2.0,
        SPEC.body_thickness_mm,
        (0.0, 0.0, 0.0),
    )
    move_to_collection(vertebra, assembly)
    assign(vertebra, PRINT_MAT)

    for hole_index, (x_mm, y_mm) in enumerate(SPEC.tendon_positions_mm, start=1):
        cutter = add_cylinder(
            f"TJ_CUT_TENDON_{hole_index}",
            SPEC.tendon_hole_diameter_mm / 2.0,
            SPEC.body_thickness_mm + 4.0,
            (x_mm, y_mm, 0.0),
        )
        boolean(vertebra, cutter, "DIFFERENCE")

    neck_depth = SPEC.joint_center_offset_mm - SPEC.body_thickness_mm / 2.0
    neck = add_cylinder(
        "TJ_MALE_X_NECK",
        SPEC.ball_neck_diameter_mm / 2.0,
        neck_depth,
        (0.0, 0.0, SPEC.body_thickness_mm / 2.0 + neck_depth / 2.0),
    )
    boolean(vertebra, neck, "UNION")
    ball = add_uv_sphere("TJ_MALE_X_BALL", SPEC.ball_diameter_mm, SPEC.joint_center_offset_mm)
    boolean(vertebra, ball, "UNION")

    socket_center = -SPEC.joint_center_offset_mm
    outer = add_uv_sphere("TJ_FEMALE_Y_OUTER", SPEC.socket_outer_diameter_mm, socket_center)
    boolean(vertebra, outer, "UNION")
    inner = add_uv_sphere("TJ_CUT_FEMALE_Y_CAVITY", SPEC.socket_diameter_mm, socket_center)
    boolean(vertebra, inner, "DIFFERENCE")

    outer_radius = SPEC.socket_outer_diameter_mm / 2.0
    opening_z = socket_center - SPEC.socket_retention_mm
    cutoff_depth = outer_radius + 4.0
    cutoff = add_box(
        "TJ_CUT_FEMALE_Y_OPENING",
        (
            SPEC.socket_outer_diameter_mm + 4.0,
            SPEC.socket_outer_diameter_mm + 4.0,
            cutoff_depth,
        ),
        (0.0, 0.0, opening_z - cutoff_depth / 2.0),
    )
    boolean(vertebra, cutoff, "DIFFERENCE")

    slot_high = socket_center + outer_radius * 0.72
    slot_height = slot_high - opening_z
    slot = add_box(
        "TJ_CUT_FEMALE_Y_SLOT",
        (SPEC.socket_slot_mm, SPEC.socket_outer_diameter_mm + 4.0, slot_height),
        (0.0, 0.0, opening_z + slot_height / 2.0),
    )
    boolean(vertebra, slot, "DIFFERENCE")

    cleanup_mesh(vertebra)
    return vertebra


def repeat_vertebra(
    master: bpy.types.Object,
    assembly: bpy.types.Collection,
) -> list[bpy.types.Object]:
    master.material_slots[0].link = "OBJECT"
    master.material_slots[0].material = PRINT_MAT
    parts = [master]
    for index in range(2, SPEC.assembly_unit_count + 1):
        copy = master.copy()
        copy.data = master.data
        copy.name = f"TJ_PRINTABLE_VERTEBRA_{index}"
        copy.location.z = m((index - 1) * SPEC.unit_pitch_mm)
        assembly.objects.link(copy)
        copy.material_slots[0].link = "OBJECT"
        copy.material_slots[0].material = PRINT_ALT_MAT if index % 2 == 0 else PRINT_MAT
        parts.append(copy)
    bpy.context.view_layer.update()
    return parts


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

    master = create_vertebra(assembly)
    printable_parts = repeat_vertebra(master, assembly)
    labels: list[bpy.types.Object] = []
    for interface in range(1, SPEC.interface_count + 1):
        joint_z = (interface - 1) * SPEC.unit_pitch_mm + SPEC.joint_center_offset_mm
        create_axis_guide(f"TJ_AXIS_J{interface}_X", joint_z, "X", guides)
        create_axis_guide(f"TJ_AXIS_J{interface}_Y", joint_z, "Y", guides)
        labels.extend(
            (
                add_text(
                    f"TJ_LABEL_J{interface}_X",
                    f"J{interface}  X",
                    (30.0, -8.0, joint_z + 3.0),
                    TEXT_MAT,
                ),
                add_text(
                    f"TJ_LABEL_J{interface}_Y",
                    f"J{interface}  Y",
                    (-27.0, -18.0, joint_z - 2.0),
                    TEXT_MAT,
                ),
            )
        )

    bottom_z = -SPEC.joint_center_offset_mm - SPEC.socket_retention_mm - 2.0
    top_z = (
        (SPEC.assembly_unit_count - 1) * SPEC.unit_pitch_mm
        + SPEC.joint_center_offset_mm
        + SPEC.ball_radius_mm
        + 2.0
    )
    create_tendon_guides(bottom_z, top_z, guides)
    labels.extend(
        (
            add_text(
                "TJ_LABEL_TITLE",
                "ONE PART x 3  /  4 DOF",
                (0.0, -8.0, top_z + 8.0),
                TEXT_MAT,
                4.3,
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

    layout_objects = duplicate_print_layout(printable_parts, print_layout)
    camera, _support_objects = setup_render(SPEC, FLOOR_MAT, assign)
    assembly_objects = [*printable_parts]
    render_views(OUTPUT_DIR, camera, assembly_objects, guides, labels, layout_objects)

    scene["TJ_SPEC_MM"] = {
        "interface_count": SPEC.interface_count,
        "assembly_unit_count": SPEC.assembly_unit_count,
        "printable_part_type_count": len(SPEC.printable_part_types),
        "degrees_of_freedom": SPEC.degrees_of_freedom,
        "body_diameter": SPEC.body_diameter_mm,
        "ball_diameter": SPEC.ball_diameter_mm,
        "socket_diameter": SPEC.socket_diameter_mm,
        "tendon_hole_diameter": SPEC.tendon_hole_diameter_mm,
        "radial_clearance": SPEC.radial_clearance_mm,
        "minimum_wall": SPEC.minimum_wall_mm,
        "maximum_articulation": SPEC.maximum_articulation_deg,
    }
    scene["TJ_PRINTABLE_PARTS"] = [obj.name for obj in printable_parts]
    scene["TJ_PRINTABLE_PART_TYPES"] = list(SPEC.printable_part_types)
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
