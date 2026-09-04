"""V5: one repeated in-disc body and one reusable printed split-pin type."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_artifact_export import export_stl_mm  # noqa: E402
from scripts.blender_mesh_primitives import (  # noqa: E402
    add_cylinder,
    assign,
    boolean,
    cleanup_mesh,
    collection,
    material,
    move_to_collection,
)
from scripts.hollow_hinge_render import create_bent_preview, duplicate_print_layout, m  # noqa: E402
from scripts.inset_hinge_presentation import present  # noqa: E402
from src.core.domain.inset_hinge import InsetHingeSpec  # noqa: E402

SPEC = InsetHingeSpec()
OUTPUT = PROJECT_ROOT / "tmp" / "inset-hinge-v5"


def root(name: str, axis: str, center: float, z_sign: float) -> bpy.types.Object:
    """Closed loft: shallow four-sided foot, then tangential load-spreading ramps."""
    vertices = []
    for z, axial, tangent in SPEC.root_profile_mm:
        for a, t in ((-axial, -tangent), (axial, -tangent), (axial, tangent), (-axial, tangent)):
            point = (center + a, t, z_sign * z) if axis == "X" else (t, center + a, z_sign * z)
            vertices.append(tuple(m(value) for value in point))
    faces = [(3, 2, 1, 0), (8, 9, 10, 11)]
    for level in (0, 4):
        for corner in range(4):
            following = (corner + 1) % 4
            faces.append(
                (level + corner, level + following, level + following + 4, level + corner + 4)
            )
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    cleanup_mesh(obj)
    return obj


def create_body(target, mat) -> bpy.types.Object:
    body = add_cylinder(
        "HH_PRINTABLE_MODULE_1",
        SPEC.body_outer_diameter_mm / 2,
        SPEC.body_length_mm,
        (0, 0, 0),
        vertices=96,
    )
    move_to_collection(body, target)
    for axis, center, sign in (
        ("X", SPEC.side_male_center_mm, 1),
        ("Y", SPEC.side_female_center_mm, -1),
    ):
        for side in (-1, 1):
            location = (
                (side * center, 0, sign * SPEC.joint_center_offset_mm)
                if axis == "X"
                else (0, side * center, sign * SPEC.joint_center_offset_mm)
            )
            ear = add_cylinder(
                "HH_EAR", SPEC.lug_outer_diameter_mm / 2, SPEC.lug_thickness_mm, location, axis
            )
            boolean(body, root("HH_ROOT", axis, side * center, sign), "UNION")
            boolean(body, ear, "UNION")
            bore = add_cylinder(
                "HH_BORE", SPEC.printed_pin_bore_mm / 2, SPEC.lug_thickness_mm + 1, location, axis
            )
            boolean(body, bore, "DIFFERENCE")
    for name, radius, x, y in [
        ("CENTER", SPEC.center_channel_diameter_mm / 2, 0, 0),
        *[
            (f"TENDON_{i}", SPEC.tendon_hole_diameter_mm / 2, x, y)
            for i, (x, y) in enumerate(SPEC.tendon_positions_mm)
        ],
    ]:
        boolean(body, add_cylinder("HH_CUT_" + name, radius, 40, (x, y, 0)), "DIFFERENCE")
    cleanup_mesh(body)
    assign(body, mat)
    return body


def create_pin(target, mat) -> bpy.types.Object:
    pin = add_cylinder(
        "HH_PIN_MASTER",
        SPEC.pin_head_diameter_mm / 2,
        SPEC.pin_head_height_mm,
        (0, 0, SPEC.pin_head_height_mm / 2),
    )
    shaft_top = SPEC.pin_length_mm - SPEC.pin_tip_length_mm
    shaft_bottom = SPEC.pin_head_height_mm - 0.1
    shaft = add_cylinder(
        "HH_SHAFT",
        SPEC.pin_diameter_mm / 2,
        shaft_top - shaft_bottom,
        (0, 0, (shaft_top + shaft_bottom) / 2),
    )
    boolean(pin, shaft, "UNION")
    bpy.ops.mesh.primitive_cone_add(
        vertices=48,
        radius1=m(SPEC.pin_diameter_mm / 2),
        radius2=m(SPEC.pin_diameter_mm / 2 - 0.6),
        depth=m(SPEC.pin_tip_length_mm + 0.05),
        location=(0, 0, m((shaft_top - 0.05 + SPEC.pin_length_mm) / 2)),
    )
    boolean(pin, bpy.context.object, "UNION")
    cleanup_mesh(pin)
    assign(pin, mat)
    move_to_collection(pin, target)
    # Bake the head-centre location, making the head's bottom the placement origin.
    for vertex in pin.data.vertices:
        vertex.co += pin.location
    pin.location = (0, 0, 0)
    pin.hide_render = True
    pin.hide_viewport = True
    return pin


def repeat_body(master, target, alternate) -> list[bpy.types.Object]:
    parts = [master]
    for i, rotation in enumerate(SPEC.assembly_rotations_deg[1:], 1):
        obj = master.copy()
        obj.data = master.data
        obj.name = f"HH_PRINTABLE_MODULE_{i + 1}"
        obj.location.z = m(i * SPEC.unit_pitch_mm)
        obj.rotation_euler.z = math.radians(rotation)
        target.objects.link(obj)
        obj.material_slots[0].link = "OBJECT"
        if i % 2:
            obj.material_slots[0].material = alternate
        parts.append(obj)
    return parts


def place_pins(master, target) -> list[bpy.types.Object]:
    result = []
    outer = SPEC.pin_under_head_radius_mm + SPEC.pin_head_height_mm
    for i in range(SPEC.joint_count):
        for side in (-1, 1):
            obj = master.copy()
            obj.data = master.data
            obj.name = f"HH_ASSEMBLED_PIN_{i + 1}_{side}"
            target.objects.link(obj)
            direction = Vector((-side, 0, 0) if i % 2 == 0 else (0, -side, 0))
            obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
            z = i * SPEC.unit_pitch_mm + SPEC.joint_center_offset_mm
            obj.location = tuple(
                m(v) for v in ((side * outer, 0, z) if i % 2 == 0 else (0, side * outer, z))
            )
            obj.hide_render = False
            obj.hide_viewport = False
            result.append(obj)
    return result


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 1.0
    gold = material("HH_V5_BODY", (0.82, 0.48, 0.12, 1))
    light = material("HH_V5_ALT", (1.0, 0.7, 0.24, 1))
    cyan = material("HH_V5_PIN", (0.03, 0.7, 0.9, 1))
    magenta = material("HH_V5_CABLE", (0.85, 0.05, 0.6, 1))
    assembly, hardware, layout, bent = [
        collection("HH_" + name) for name in ("ASSEMBLY", "HARDWARE", "LAYOUT", "BENT")
    ]
    master = create_body(assembly, gold)
    pin = create_pin(hardware, cyan)
    parts = repeat_body(master, assembly, light)
    pins = place_pins(pin, hardware)
    layout_objects = duplicate_print_layout(master, layout)
    bent_objects, cable, target = create_bent_preview(master, bent, SPEC, gold, light, magenta)
    # Export first; image or display failures must not prevent delivery of geometry.
    export_stl_mm([master], OUTPUT / "inset_hinge_body_mm.stl")
    export_stl_mm([pin], OUTPUT / "inset_hinge_pin_mm.stl")
    scene["HH_AXIS_NAMES"] = list(SPEC.axis_names)
    scene["HH_DESIGN_NOTE"] = (
        "V5: 34 mm disc; 10 mm channel; 38.7/35 degree roots. Printed pins need external retention; no bearing seats or strength certification."
    )
    scene["HH_PRINTABLE_PART_TYPES"] = list(SPEC.printable_part_types)
    present(OUTPUT, SPEC, parts, hardware, pin, pins, layout_objects, bent_objects, cable, target)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "inset_hinge_v5.blend"))
    print("INSET_HINGE_V5_READY", str(OUTPUT))


def main() -> None:
    for obj in list(bpy.data.objects):
        if obj.name.startswith("HH_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    for group in list(bpy.data.collections):
        if group.name.startswith("HH_"):
            bpy.data.collections.remove(group)
    external = [(obj, obj.hide_render, obj.hide_viewport) for obj in bpy.context.scene.objects]
    try:
        for obj, _, _ in external:
            obj.hide_render = obj.hide_viewport = True
        build()
    finally:
        for obj, render, viewport in external:
            obj.hide_render, obj.hide_viewport = render, viewport


if __name__ == "__main__":
    main()
