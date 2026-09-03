"""Generate a short multi-joint chain with a clear central sensor-wire channel."""

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

from scripts.blender_artifact_export import export_stl_mm  # noqa: E402
from scripts.hollow_hinge_geometry import create_box, create_clipped_lug  # noqa: E402
from scripts.hollow_hinge_render import (  # noqa: E402
    add_text,
    create_bent_preview,
    duplicate_print_layout,
    m,
    render_views,
    setup_render,
)
from src.core.domain.hollow_side_hinge import HollowSideHingeSpec  # noqa: E402

PREFIX = "HH_"
OUTPUT_DIR = Path(
    os.environ.get("HOLLOW_HINGE_OUTPUT_DIR", str(PROJECT_ROOT / "tmp" / "hollow-side-hinge"))
)
SPEC = HollowSideHingeSpec()


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0):
    result = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = color
    result.metallic = metallic
    result.roughness = 0.24 if metallic else 0.42
    principled = result.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = result.roughness
    return result


MODULE_MAT = material("HH_MAT_MODULE", (0.72, 0.44, 0.13, 1.0), metallic=0.06)
MODULE_ALT_MAT = material("HH_MAT_MODULE_ALT", (0.96, 0.65, 0.2, 1.0), metallic=0.04)
X_MAT = material("HH_MAT_X_PIN", (0.96, 0.07, 0.06, 1.0), metallic=0.55)
Y_MAT = material("HH_MAT_Y_PIN", (0.06, 0.28, 0.98, 1.0), metallic=0.55)
BEARING_MAT = material("HH_MAT_BEARING", (0.86, 0.92, 0.98, 1.0), metallic=0.95)
TENDON_MAT = material("HH_MAT_TENDON", (0.0, 0.96, 0.82, 1.0), metallic=0.08)
CABLE_MAT = material("HH_MAT_SENSOR_CABLE", (0.93, 0.08, 0.82, 1.0), metallic=0.12)
TEXT_MAT = material("HH_MAT_TEXT", (0.96, 0.98, 1.0, 1.0))
FLOOR_MAT = material("HH_MAT_FLOOR", (0.015, 0.022, 0.035, 1.0))


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
    vertices: int = 48,
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


def boolean(target: bpy.types.Object, tool: bpy.types.Object, operation: str) -> None:
    bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(name=f"HH_{operation}", type="BOOLEAN")
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


def add_side_lugs(module: bpy.types.Object) -> None:
    body_radius = SPEC.body_outer_diameter_mm / 2.0
    bridge_inner = body_radius - 0.6
    for side in (-1.0, 1.0):
        male = create_clipped_lug(
            f"HH_MALE_SIDE_LUG_{side:+.0f}",
            "X",
            side * SPEC.side_male_center_mm,
            SPEC.joint_center_offset_mm,
            SPEC.male_lug_thickness_mm,
            SPEC.lug_outer_diameter_mm,
            SPEC.joint_gap_mm,
            SPEC.lug_profile_clearance_mm,
            False,
        )
        boolean(module, male, "UNION")
        male_bridge_outer = SPEC.side_male_center_mm - SPEC.male_lug_thickness_mm / 2.0 + 0.6
        male_bridge_length = male_bridge_outer - bridge_inner
        male_bridge = create_box(
            f"HH_MALE_BRIDGE_{side:+.0f}",
            (male_bridge_length, SPEC.bridge_width_mm, SPEC.bridge_thickness_mm),
            (
                side * (bridge_inner + male_bridge_length / 2.0),
                0.0,
                SPEC.joint_center_offset_mm - SPEC.bridge_center_from_joint_mm,
            ),
        )
        boolean(module, male_bridge, "UNION")

        female = create_clipped_lug(
            f"HH_FEMALE_SIDE_LUG_{side:+.0f}",
            "Y",
            side * SPEC.side_female_center_mm,
            -SPEC.joint_center_offset_mm,
            SPEC.female_lug_thickness_mm,
            SPEC.lug_outer_diameter_mm,
            SPEC.joint_gap_mm,
            SPEC.lug_profile_clearance_mm,
            True,
        )
        boolean(module, female, "UNION")
        female_bridge_outer = SPEC.side_female_center_mm - SPEC.female_lug_thickness_mm / 2.0 + 0.6
        female_bridge_length = female_bridge_outer - bridge_inner
        female_bridge = create_box(
            f"HH_FEMALE_BRIDGE_{side:+.0f}",
            (SPEC.bridge_width_mm, female_bridge_length, SPEC.bridge_thickness_mm),
            (
                0.0,
                side * (bridge_inner + female_bridge_length / 2.0),
                -SPEC.joint_center_offset_mm + SPEC.bridge_center_from_joint_mm,
            ),
        )
        boolean(module, female_bridge, "UNION")


def cut_center_and_tendons(module: bpy.types.Object) -> None:
    cutter_depth = 2.0 * SPEC.joint_center_offset_mm + SPEC.lug_outer_diameter_mm + 4.0
    center = add_cylinder(
        "HH_CUT_CENTER_CHANNEL",
        SPEC.center_channel_diameter_mm / 2.0,
        cutter_depth,
        (0.0, 0.0, 0.0),
    )
    boolean(module, center, "DIFFERENCE")
    for index, (x_mm, y_mm) in enumerate(SPEC.tendon_positions_mm, start=1):
        tendon = add_cylinder(
            f"HH_CUT_TENDON_{index}",
            SPEC.tendon_hole_diameter_mm / 2.0,
            SPEC.body_length_mm + 2.0,
            (x_mm, y_mm, 0.0),
        )
        boolean(module, tendon, "DIFFERENCE")


def cut_side_hardware_seats(module: bpy.types.Object) -> None:
    for side in (-1.0, 1.0):
        male_bore = add_cylinder(
            f"HH_CUT_MALE_BORE_{side:+.0f}",
            SPEC.printed_pin_bore_mm / 2.0,
            SPEC.male_lug_thickness_mm + 1.0,
            (side * SPEC.side_male_center_mm, 0.0, SPEC.joint_center_offset_mm),
            axis="X",
        )
        boolean(module, male_bore, "DIFFERENCE")

        female_bore = add_cylinder(
            f"HH_CUT_FEMALE_BORE_{side:+.0f}",
            SPEC.printed_pin_bore_mm / 2.0,
            SPEC.female_lug_thickness_mm + 1.0,
            (0.0, side * SPEC.side_female_center_mm, -SPEC.joint_center_offset_mm),
            axis="Y",
        )
        boolean(module, female_bore, "DIFFERENCE")
        seat_center = side * (
            SPEC.side_female_center_mm
            + (SPEC.female_lug_thickness_mm - SPEC.bearing_width_mm) / 2.0
        )
        bearing_seat = add_cylinder(
            f"HH_CUT_BEARING_SEAT_{side:+.0f}",
            SPEC.bearing_seat_diameter_mm / 2.0,
            SPEC.bearing_width_mm,
            (0.0, seat_center, -SPEC.joint_center_offset_mm),
            axis="Y",
        )
        boolean(module, bearing_seat, "DIFFERENCE")


def create_module(assembly: bpy.types.Collection) -> bpy.types.Object:
    module = add_cylinder(
        "HH_PRINTABLE_MODULE_1",
        SPEC.body_outer_diameter_mm / 2.0,
        SPEC.body_length_mm,
        (0.0, 0.0, 0.0),
        vertices=64,
    )
    move_to_collection(module, assembly)
    assign(module, MODULE_MAT)
    add_side_lugs(module)
    cut_center_and_tendons(module)
    cut_side_hardware_seats(module)
    cleanup_mesh(module)
    return module


def repeat_module(
    master: bpy.types.Object,
    assembly: bpy.types.Collection,
) -> list[bpy.types.Object]:
    master.material_slots[0].link = "OBJECT"
    master.material_slots[0].material = MODULE_MAT
    parts = [master]
    for index, rotation_deg in enumerate(SPEC.assembly_rotations_deg[1:], start=2):
        copy = master.copy()
        copy.data = master.data
        copy.name = f"HH_PRINTABLE_MODULE_{index}"
        copy.location.z = m((index - 1) * SPEC.unit_pitch_mm)
        copy.rotation_euler.z = math.radians(rotation_deg)
        assembly.objects.link(copy)
        copy.material_slots[0].link = "OBJECT"
        copy.material_slots[0].material = MODULE_ALT_MAT if index % 2 == 0 else MODULE_MAT
        parts.append(copy)
    bpy.context.view_layer.update()
    return parts


def create_bearing(
    name: str,
    joint_z_mm: float,
    axis: str,
    side: float,
    hardware: bpy.types.Collection,
) -> None:
    face_offset = SPEC.side_female_center_mm + SPEC.female_lug_thickness_mm / 2.0 + 0.2
    location = (
        (side * face_offset, 0.0, joint_z_mm)
        if axis == "X"
        else (0.0, side * face_offset, joint_z_mm)
    )
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
    inner_edge = SPEC.center_channel_diameter_mm / 2.0 + SPEC.minimum_running_clearance_mm
    outer_edge = SPEC.side_female_center_mm + SPEC.female_lug_thickness_mm / 2.0 + 0.4
    segment_center = (inner_edge + outer_edge) / 2.0
    segment_length = outer_edge - inner_edge
    for side in (-1.0, 1.0):
        location = (
            (side * segment_center, 0.0, joint_z)
            if axis == "X"
            else (0.0, side * segment_center, joint_z)
        )
        pin = add_cylinder(
            f"HH_PIN_J{joint}_{axis}_{'POS' if side > 0 else 'NEG'}",
            SPEC.pin_diameter_mm / 2.0,
            segment_length,
            location,
            axis=axis,
        )
        move_to_collection(pin, hardware)
        assign(pin, X_MAT if axis == "X" else Y_MAT)
        pin.hide_viewport = True
        create_bearing(
            f"HH_BEARING_J{joint}_{'POS' if side > 0 else 'NEG'}",
            joint_z,
            axis,
            side,
            hardware,
        )


def create_route_guides(
    z_min_mm: float,
    z_max_mm: float,
    hardware: bpy.types.Collection,
) -> None:
    depth = z_max_mm - z_min_mm
    center_z = (z_min_mm + z_max_mm) / 2.0
    cable = add_cylinder("HH_SENSOR_CABLE_ROUTE", 1.55, depth, (0.0, 0.0, center_z))
    move_to_collection(cable, hardware)
    assign(cable, CABLE_MAT)
    cable.show_in_front = True
    cable.hide_viewport = True
    for index, (x_mm, y_mm) in enumerate(SPEC.tendon_positions_mm, start=1):
        tendon = add_cylinder(f"HH_TENDON_{index}", 0.4, depth, (x_mm, y_mm, center_z))
        move_to_collection(tendon, hardware)
        assign(tendon, TENDON_MAT)
        tendon.show_in_front = True
        tendon.hide_viewport = True


def build_scene() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    assembly = collection("HH_ASSEMBLY")
    hardware = collection("HH_HARDWARE")
    print_layout = collection("HH_PRINT_LAYOUT")
    bent_preview = collection("HH_BENT_PREVIEW")

    master = create_module(assembly)
    printable_parts = repeat_module(master, assembly)
    labels: list[bpy.types.Object] = []
    for joint, axis_name in enumerate(SPEC.axis_names, start=1):
        create_joint_hardware(joint, hardware)
        joint_z = (joint - 1) * SPEC.unit_pitch_mm + SPEC.joint_center_offset_mm
        axis = axis_name.rsplit("_", 1)[1]
        labels.append(
            add_text(
                f"HH_LABEL_{axis_name}",
                f"J{joint} {axis}",
                ((25.0 if axis == "X" else -25.0), -29.0, joint_z + 1.0),
                TEXT_MAT,
                2.2,
            )
        )

    bottom_z = -SPEC.joint_center_offset_mm - SPEC.lug_outer_diameter_mm / 2.0 - 2.0
    top_z = (
        (SPEC.assembly_unit_count - 1) * SPEC.unit_pitch_mm
        + SPEC.joint_center_offset_mm
        + SPEC.lug_outer_diameter_mm / 2.0
        + 2.0
    )
    create_route_guides(bottom_z, top_z, hardware)
    labels.extend(
        (
            add_text(
                "HH_LABEL_TITLE",
                "HINGE V4 / ONE HOLLOW MODULE x9 / 8 JOINTS",
                (0.0, -5.0, top_z + 5.0),
                TEXT_MAT,
                3.2,
            ),
            add_text(
                "HH_LABEL_CHANNEL",
                "CENTER DIA 10 SENSOR BUS / DUAL M4 SIDE PINS",
                (0.0, -38.0, bottom_z + 7.0),
                TEXT_MAT,
                2.5,
            ),
            add_text(
                "HH_LABEL_RANGE",
                (
                    f"X {SPEC.cumulative_articulation_x_deg:.0f} DEG / "
                    f"Y {SPEC.cumulative_articulation_y_deg:.0f} DEG CUMULATIVE (CONCEPT)"
                ),
                (0.0, -38.0, bottom_z + 1.0),
                TEXT_MAT,
                2.2,
            ),
        )
    )

    layout_objects = duplicate_print_layout(master, print_layout)
    bent_objects, bent_cable, bent_target = create_bent_preview(
        master,
        bent_preview,
        SPEC,
        MODULE_MAT,
        MODULE_ALT_MAT,
        CABLE_MAT,
    )
    camera, _support_objects = setup_render(SPEC, FLOOR_MAT, assign)
    render_views(
        OUTPUT_DIR,
        camera,
        printable_parts,
        hardware,
        labels,
        layout_objects,
        bent_objects,
        bent_cable,
        bent_target,
    )

    scene["HH_SPEC_MM"] = {
        "joint_count": SPEC.joint_count,
        "assembly_unit_count": SPEC.assembly_unit_count,
        "printable_part_type_count": len(SPEC.printable_part_types),
        "body_length": SPEC.body_length_mm,
        "unit_pitch": SPEC.unit_pitch_mm,
        "assembled_height": SPEC.assembled_height_mm,
        "body_outer_diameter": SPEC.body_outer_diameter_mm,
        "center_channel_diameter": SPEC.center_channel_diameter_mm,
        "side_pin_diameter": SPEC.pin_diameter_mm,
        "bearing_seat_diameter": SPEC.bearing_seat_diameter_mm,
        "cumulative_x": SPEC.cumulative_articulation_x_deg,
        "cumulative_y": SPEC.cumulative_articulation_y_deg,
    }
    scene["HH_PRINTABLE_PARTS"] = [obj.name for obj in printable_parts]
    scene["HH_PRINTABLE_PART_TYPES"] = list(SPEC.printable_part_types)
    scene["HH_AXIS_NAMES"] = list(SPEC.axis_names)
    scene["HH_COMMON_HARDWARE"] = list(SPEC.common_hardware)
    scene["HH_DESIGN_NOTE"] = (
        "Center channel is hardware-free; validate wire bend radius, M4 fit, and MR84 seats."
    )
    export_stl_mm([master], OUTPUT_DIR / "hollow_side_hinge_module.stl")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_DIR / "hollow_side_hinge_8joint.blend"))
    print(
        "HOLLOW_SIDE_HINGE_READY",
        {
            "joints": SPEC.joint_count,
            "parts": [obj.name for obj in printable_parts],
            "axes": SPEC.axis_names,
            "center_channel_mm": SPEC.center_channel_diameter_mm,
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
        build_scene()
    finally:
        for obj, hide_render, hide_viewport in external_visibility:
            obj.hide_render = hide_render
            obj.hide_viewport = hide_viewport


if __name__ == "__main__":
    main()
