"""Generate a four-DOF chain from one repeatable, bearing-ready hinge phalanx."""

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

from scripts.hinge_chain_render import (  # noqa: E402
    add_text,
    duplicate_print_layout,
    m,
    render_views,
    setup_render,
)
from src.core.domain.hinge_chain import HingePhalanxSpec  # noqa: E402

PREFIX = "HJ_"
OUTPUT_DIR = Path(os.environ.get("HINGE_CHAIN_OUTPUT_DIR", "/tmp/blender-mcp-hinge-chain"))
SPEC = HingePhalanxSpec()


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    mat.metallic = metallic
    mat.roughness = 0.25 if metallic else 0.44
    principled = mat.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = mat.roughness
    return mat


PRINT_MAT = material("HJ_MAT_PHALANX", (0.68, 0.45, 0.22, 1.0), metallic=0.08)
PRINT_ALT_MAT = material("HJ_MAT_PHALANX_ALT", (0.9, 0.66, 0.31, 1.0), metallic=0.05)
X_MAT = material("HJ_MAT_X_PIN", (0.94, 0.08, 0.07, 1.0), metallic=0.5)
Y_MAT = material("HJ_MAT_Y_PIN", (0.07, 0.3, 0.95, 1.0), metallic=0.5)
BEARING_MAT = material("HJ_MAT_BEARING", (0.82, 0.88, 0.94, 1.0), metallic=0.9)
TENDON_MAT = material("HJ_MAT_TENDON", (0.02, 0.95, 0.9, 1.0), metallic=0.1)
TEXT_MAT = material("HJ_MAT_TEXT", (0.95, 0.97, 1.0, 1.0))
FLOOR_MAT = material("HJ_MAT_FLOOR", (0.02, 0.026, 0.038, 1.0))


def clear_previous() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    for group in list(bpy.data.collections):
        if group.name.startswith(PREFIX):
            bpy.data.collections.remove(group)


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
    vertices: int = 40,
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


def add_ellipsoid(
    name: str,
    dimensions_mm: tuple[float, float, float],
    location_mm: tuple[float, float, float],
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=40,
        ring_count=24,
        radius=1.0,
        location=tuple(m(value) for value in location_mm),
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(m(value / 2.0) for value in dimensions_mm)
    apply_transform(obj)
    return obj


def boolean(target: bpy.types.Object, tool: bpy.types.Object, operation: str) -> None:
    bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(name=f"HJ_{operation}", type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def cleanup_mesh(obj: bpy.types.Object) -> None:
    editable = bmesh.new()
    editable.from_mesh(obj.data)
    bmesh.ops.remove_doubles(editable, verts=editable.verts, dist=m(0.005))
    bmesh.ops.dissolve_degenerate(editable, edges=editable.edges, dist=m(0.001))
    bmesh.ops.recalc_face_normals(editable, faces=editable.faces)
    editable.to_mesh(obj.data)
    editable.free()
    obj.data.update()


def cut_tendon_routes(body: bpy.types.Object) -> None:
    for index, (x_mm, y_mm) in enumerate(SPEC.tendon_positions_mm, start=1):
        cutter = add_cylinder(
            f"HJ_CUT_TENDON_{index}",
            SPEC.tendon_hole_diameter_mm / 2.0,
            SPEC.body_length_mm + 6.0,
            (x_mm, y_mm, 0.0),
        )
        boolean(body, cutter, "DIFFERENCE")


def add_male_hinge(body: bpy.types.Object) -> None:
    lug = add_cylinder(
        "HJ_MALE_X_LUG",
        SPEC.lug_outer_diameter_mm / 2.0,
        SPEC.male_tongue_thickness_mm,
        (0.0, 0.0, SPEC.joint_center_offset_mm),
        axis="X",
    )
    boolean(body, lug, "UNION")
    bore = add_cylinder(
        "HJ_CUT_MALE_PIN_BORE",
        SPEC.printed_pin_bore_mm / 2.0,
        SPEC.male_tongue_thickness_mm + 4.0,
        (0.0, 0.0, SPEC.joint_center_offset_mm),
        axis="X",
    )
    boolean(body, bore, "DIFFERENCE")


def add_female_hinge(body: bpy.types.Object) -> None:
    center_z = -SPEC.joint_center_offset_mm
    lug_y = SPEC.fork_gap_mm / 2.0 + SPEC.fork_lug_thickness_mm / 2.0
    connector_height = 9.0
    connector_z = -SPEC.body_length_mm / 2.0 + 1.0
    for side in (-1.0, 1.0):
        y_mm = side * lug_y
        connector = add_box(
            f"HJ_FEMALE_Y_CONNECTOR_{side:+.0f}",
            (
                SPEC.lug_outer_diameter_mm * 0.72,
                SPEC.fork_lug_thickness_mm,
                connector_height,
            ),
            (0.0, y_mm, connector_z),
        )
        boolean(body, connector, "UNION")
        lug = add_cylinder(
            f"HJ_FEMALE_Y_LUG_{side:+.0f}",
            SPEC.lug_outer_diameter_mm / 2.0,
            SPEC.fork_lug_thickness_mm,
            (0.0, y_mm, center_z),
            axis="Y",
        )
        boolean(body, lug, "UNION")

    pin_bore = add_cylinder(
        "HJ_CUT_FEMALE_PIN_BORE",
        SPEC.printed_pin_bore_mm / 2.0,
        SPEC.fork_total_width_mm + 4.0,
        (0.0, 0.0, center_z),
        axis="Y",
    )
    boolean(body, pin_bore, "DIFFERENCE")

    outer_face = SPEC.fork_total_width_mm / 2.0
    seat_center = outer_face - SPEC.bearing_width_mm / 2.0
    for side in (-1.0, 1.0):
        seat = add_cylinder(
            f"HJ_CUT_MR84_SEAT_{side:+.0f}",
            SPEC.bearing_seat_diameter_mm / 2.0,
            SPEC.bearing_width_mm,
            (0.0, side * seat_center, center_z),
            axis="Y",
        )
        boolean(body, seat, "DIFFERENCE")


def create_phalanx(assembly: bpy.types.Collection) -> bpy.types.Object:
    body = add_ellipsoid(
        "HJ_PRINTABLE_PHALANX_1",
        (SPEC.body_width_mm, SPEC.body_depth_mm, SPEC.body_length_mm),
        (0.0, 0.0, 0.0),
    )
    move_to_collection(body, assembly)
    assign(body, PRINT_MAT)
    cut_tendon_routes(body)
    add_male_hinge(body)
    add_female_hinge(body)
    cleanup_mesh(body)
    return body


def repeat_phalanx(
    master: bpy.types.Object,
    assembly: bpy.types.Collection,
) -> list[bpy.types.Object]:
    master.material_slots[0].link = "OBJECT"
    master.material_slots[0].material = PRINT_MAT
    parts = [master]
    for index, rotation_deg in enumerate(SPEC.assembly_rotations_deg[1:], start=2):
        copy = master.copy()
        copy.data = master.data
        copy.name = f"HJ_PRINTABLE_PHALANX_{index}"
        copy.location.z = m((index - 1) * SPEC.unit_pitch_mm)
        copy.rotation_euler.z = math.radians(rotation_deg)
        assembly.objects.link(copy)
        copy.material_slots[0].link = "OBJECT"
        copy.material_slots[0].material = PRINT_ALT_MAT if index % 2 == 0 else PRINT_MAT
        parts.append(copy)
    bpy.context.view_layer.update()
    return parts


def create_bearing(
    name: str,
    joint_z: float,
    axis: str,
    axial_offset: float,
    hardware: bpy.types.Collection,
) -> None:
    location = (axial_offset, 0.0, joint_z) if axis == "X" else (0.0, axial_offset, joint_z)
    rotation = (0.0, math.pi / 2.0, 0.0) if axis == "X" else (math.pi / 2.0, 0.0, 0.0)
    outer_radius = SPEC.bearing_seat_diameter_mm / 2.0
    inner_radius = SPEC.pin_diameter_mm / 2.0
    bpy.ops.mesh.primitive_torus_add(
        major_segments=40,
        minor_segments=12,
        major_radius=m((outer_radius + inner_radius) / 2.0),
        minor_radius=m((outer_radius - inner_radius) / 2.0),
        location=tuple(m(value) for value in location),
        rotation=rotation,
    )
    bearing = bpy.context.object
    bearing.name = name
    move_to_collection(bearing, hardware)
    assign(bearing, BEARING_MAT)
    bearing.hide_viewport = True


def create_joint_hardware(joint: int, hardware: bpy.types.Collection) -> None:
    joint_z = (joint - 1) * SPEC.unit_pitch_mm + SPEC.joint_center_offset_mm
    axis = "X" if joint % 2 else "Y"
    pin = add_cylinder(
        f"HJ_PIN_J{joint}_{axis}",
        SPEC.pin_diameter_mm / 2.0,
        SPEC.fork_total_width_mm + 8.0,
        (0.0, 0.0, joint_z),
        axis=axis,
    )
    move_to_collection(pin, hardware)
    assign(pin, X_MAT if axis == "X" else Y_MAT)
    pin.hide_viewport = True

    bearing_face = SPEC.fork_total_width_mm / 2.0 + 0.35
    for side in (-1.0, 1.0):
        create_bearing(
            f"HJ_BEARING_J{joint}_{side:+.0f}",
            joint_z,
            axis,
            side * bearing_face,
            hardware,
        )


def create_tendon_guides(z_min_mm: float, z_max_mm: float, hardware: bpy.types.Collection) -> None:
    depth_mm = z_max_mm - z_min_mm
    z_mm = (z_min_mm + z_max_mm) / 2.0
    for index, (x_mm, y_mm) in enumerate(SPEC.tendon_positions_mm, start=1):
        tendon = add_cylinder(
            f"HJ_TENDON_{index}",
            0.48,
            depth_mm,
            (x_mm, y_mm, z_mm),
        )
        move_to_collection(tendon, hardware)
        assign(tendon, TENDON_MAT)
        tendon.show_in_front = True
        tendon.hide_viewport = True


def _build_scene() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    assembly = collection("HJ_ASSEMBLY")
    hardware = collection("HJ_HARDWARE")
    print_layout = collection("HJ_PRINT_LAYOUT")

    master = create_phalanx(assembly)
    printable_parts = repeat_phalanx(master, assembly)
    labels: list[bpy.types.Object] = []
    for joint, axis_name in enumerate(SPEC.axis_names, start=1):
        create_joint_hardware(joint, hardware)
        joint_z = (joint - 1) * SPEC.unit_pitch_mm + SPEC.joint_center_offset_mm
        axis = axis_name.rsplit("_", 1)[1]
        labels.append(
            add_text(
                f"HJ_LABEL_{axis_name}",
                f"J{joint}  {axis}",
                (30.0 if axis == "X" else -30.0, -35.0, joint_z + 2.0),
                TEXT_MAT,
                3.1,
            )
        )

    bottom_z = -SPEC.joint_center_offset_mm - SPEC.lug_outer_diameter_mm / 2.0 - 3.0
    top_z = (
        (SPEC.assembly_unit_count - 1) * SPEC.unit_pitch_mm
        + SPEC.joint_center_offset_mm
        + SPEC.lug_outer_diameter_mm / 2.0
        + 3.0
    )
    create_tendon_guides(bottom_z, top_z, hardware)
    labels.extend(
        (
            add_text(
                "HJ_LABEL_TITLE",
                "HINGE V3  /  ONE PART x 5  /  X-Y-X-Y",
                (0.0, -8.0, top_z + 4.0),
                TEXT_MAT,
                3.8,
            ),
            add_text(
                "HJ_LABEL_HARDWARE",
                "4 mm PIN  /  MR84 4x8x3 BEARING",
                (0.0, -48.0, bottom_z + 10.0),
                TEXT_MAT,
                2.8,
            ),
        )
    )

    layout_objects = duplicate_print_layout(master, print_layout)
    camera, _support_objects = setup_render(SPEC, FLOOR_MAT, assign)
    render_views(OUTPUT_DIR, camera, printable_parts, hardware, labels, layout_objects)

    scene["HJ_SPEC_MM"] = {
        "joint_count": SPEC.joint_count,
        "assembly_unit_count": SPEC.assembly_unit_count,
        "printable_part_type_count": len(SPEC.printable_part_types),
        "degrees_of_freedom": SPEC.degrees_of_freedom,
        "body_length": SPEC.body_length_mm,
        "body_width": SPEC.body_width_mm,
        "body_depth": SPEC.body_depth_mm,
        "pin_diameter": SPEC.pin_diameter_mm,
        "printed_pin_bore": SPEC.printed_pin_bore_mm,
        "bearing_seat_diameter": SPEC.bearing_seat_diameter_mm,
        "fork_gap": SPEC.fork_gap_mm,
        "minimum_wall": SPEC.minimum_wall_mm,
    }
    scene["HJ_PRINTABLE_PARTS"] = [obj.name for obj in printable_parts]
    scene["HJ_PRINTABLE_PART_TYPES"] = list(SPEC.printable_part_types)
    scene["HJ_AXIS_NAMES"] = list(SPEC.axis_names)
    scene["HJ_COMMON_HARDWARE"] = list(SPEC.common_hardware)
    scene["HJ_DESIGN_NOTE"] = (
        "Prototype with M4 pin clearance; validate bearing fit, fatigue, and tendon wear."
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_DIR / "hinge_chain_4dof.blend"))
    print(
        "HINGE_CHAIN_READY",
        {
            "dof": SPEC.degrees_of_freedom,
            "axes": SPEC.axis_names,
            "parts": [obj.name for obj in printable_parts],
            "hardware": SPEC.common_hardware,
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
