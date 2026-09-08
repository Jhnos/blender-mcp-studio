"""V2 composition: a turned, chamfered palm with buttressed sockets and aimed pads.

Everything the palm does not own is V1's, imported rather than re-typed: the V6 arm
body, the captive pins, the terminal tip, the fit coupon. What V2 replaces is the
plate itself and where the grip pads sit.

Objects carry an `HH_OCT2_` prefix so a V2 scene and a V1 scene can never be read as
each other by a contract that selects on names.
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_artifact_export import export_stl_mm  # noqa: E402
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.blender_mesh_primitives import collection, material  # noqa: E402
from scripts.hinge_retention import create_captive_pin, cut_retainer_seats  # noqa: E402
from scripts.hollow_hinge_render import m  # noqa: E402
from scripts.model_inset_hinge import create_body  # noqa: E402
from scripts.octopus_coupon import build_coupon, coupon_note  # noqa: E402
from scripts.octopus_grip_geometry_v2 import (  # noqa: E402
    add_grip_pads,
    assert_cap_faces_the_pads,
)
from scripts.octopus_hand_presentation_v2 import present_octopus_v2  # noqa: E402
from scripts.octopus_palm_geometry_v2 import create_palm  # noqa: E402
from scripts.octopus_tip_geometry import build_tip  # noqa: E402
from src.core.domain.octopus_hand_v2 import OctopusHandV2Spec  # noqa: E402

SPEC = OctopusHandV2Spec()
OUTPUT = PROJECT_ROOT / "tmp" / "octopus-hand-v2"


def layout_parts(
    parts: list[bpy.types.Object], target: bpy.types.Collection
) -> list[bpy.types.Object]:
    """Lay one copy of each master out in a row, for the readiness selection to read.

    V1's equivalent hard-codes its own object names, and V1's generator belongs to a
    package whose bytes are checksummed, so it is left alone rather than widened.
    """
    placed: list[bpy.types.Object] = []
    cursor = 0.0
    for index, source in enumerate(parts, 1):
        obj = source.copy()
        obj.data = source.data
        obj.name = f"HH_OCT2_LAYOUT_PART_{index}"
        target.objects.link(obj)
        width = max(source.dimensions) * 1000.0
        obj.location = (m(cursor + width / 2), 0.0, 0.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.hide_render = obj.hide_viewport = True
        cursor += width + 10.0
        placed.append(obj)
    return placed


def place_arm(
    master: bpy.types.Object,
    tip_master: bpy.types.Object,
    target: bpy.types.Collection,
    alternate: bpy.types.Material,
    arm_index: int,
    station_angle_deg: float,
    station_mm: tuple[float, float],
) -> list[bpy.types.Object]:
    """One arm's bodies, stacked up the station and twisted to alternate its joints."""
    arm = SPEC.arm_spec
    bodies: list[bpy.types.Object] = []
    for index in range(1, SPEC.arm_body_count + 1):
        is_tip = index == SPEC.arm_body_count
        source = tip_master if is_tip else master
        obj = source.copy()
        obj.data = source.data
        obj.name = f"HH_OCT2_TIP_{arm_index}" if is_tip else f"HH_OCT2_SEG_{arm_index}_{index}"
        target.objects.link(obj)
        obj.location = (m(station_mm[0]), m(station_mm[1]), m(index * arm.unit_pitch_mm))
        obj.rotation_euler.z = math.radians(
            (station_angle_deg + SPEC.body_twist_deg(index)) % 360.0
        )
        obj.hide_render = obj.hide_viewport = False
        obj.material_slots[0].link = "OBJECT"
        if index % 2:
            obj.material_slots[0].material = alternate
        bodies.append(obj)
    return bodies


def place_arm_pins(
    master: bpy.types.Object,
    target: bpy.types.Collection,
    arm_index: int,
    station_angle_deg: float,
    station_mm: tuple[float, float],
) -> list[bpy.types.Object]:
    """Two captive pins per joint, including the base joint the palm socket makes."""
    arm = SPEC.arm_spec
    outer = arm.pin_under_head_radius_mm + arm.pin_head_height_mm
    pins: list[bpy.types.Object] = []
    for joint in range(SPEC.arm_body_count):
        z_mm = joint * arm.unit_pitch_mm + arm.joint_center_offset_mm
        heading = math.radians(station_angle_deg + SPEC.joint_axis_twist_deg(joint))
        cos_h, sin_h = math.cos(heading), math.sin(heading)
        for side in (-1, 1):
            obj = master.copy()
            obj.data = master.data
            obj.name = f"HH_OCT2_PIN_{arm_index}_{joint + 1}_{side}"
            target.objects.link(obj)
            direction = Vector((-side * cos_h, -side * sin_h, 0.0))
            obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
            obj.location = (
                m(station_mm[0] + side * outer * cos_h),
                m(station_mm[1] + side * outer * sin_h),
                m(z_mm),
            )
            obj.hide_render = obj.hide_viewport = False
            pins.append(obj)
    return pins


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 1.0

    arm = SPEC.arm_spec
    teal = material("HH_OCT2_PALM_MAT", (0.10, 0.55, 0.52, 1))
    gold = material("HH_OCT2_BODY", (0.82, 0.48, 0.12, 1))
    light = material("HH_OCT2_ALT", (1.0, 0.7, 0.24, 1))
    cyan = material("HH_OCT2_PIN", (0.03, 0.7, 0.9, 1))

    hand, hardware, layout, coupon = (
        collection("HH_OCT2_" + name) for name in ("HAND", "HARDWARE", "LAYOUT", "COUPON")
    )

    palm = create_palm(hand, teal, SPEC)
    master = create_body(hand, gold, arm)
    master.name = "HH_OCT2_MASTER_BODY"
    cut_retainer_seats(master, arm)
    add_grip_pads(master, SPEC)

    # Copy the tip master while the body is still visible, and keep it visible until
    # its own geometry is applied: `hide_viewport` drops an object out of the depsgraph
    # and a Boolean on an unevaluated object silently does nothing.
    tip_master = master.copy()
    tip_master.data = master.data.copy()
    tip_master.name = "HH_OCT2_MASTER_TIP"
    hand.objects.link(tip_master)
    build_tip(tip_master, SPEC)
    assert_cap_faces_the_pads(tip_master, SPEC)
    if len(tip_master.data.polygons) == len(master.data.polygons):
        raise RuntimeError(
            "the tip is still a plain body: "
            f"{len(tip_master.data.polygons)} faces, same as the body it was cut from"
        )
    master.hide_render = master.hide_viewport = True
    tip_master.hide_render = tip_master.hide_viewport = True

    captive = create_captive_pin(hardware, cyan, arm)

    bodies: list[bpy.types.Object] = []
    pins: list[bpy.types.Object] = []
    stations = zip(SPEC.arm_station_angles_deg, SPEC.arm_station_positions_mm, strict=True)
    for arm_index, (angle, station) in enumerate(stations, 1):
        bodies.extend(place_arm(master, tip_master, hand, light, arm_index, angle, station))
        pins.extend(place_arm_pins(captive, hardware, arm_index, angle, station))

    layout_objects = layout_parts([palm, master, tip_master], layout)

    export_stl_mm([palm], OUTPUT / "palm_mm.stl")
    export_stl_mm([master], OUTPUT / "arm_body_mm.stl")
    export_stl_mm([tip_master], OUTPUT / "arm_tip_mm.stl")
    printed = [palm, *bodies, *pins]
    if len(printed) != SPEC.printed_part_count:
        raise RuntimeError(
            f"one-piece export has {len(printed)} parts, expected {SPEC.printed_part_count}"
        )
    export_stl_mm(printed, OUTPUT / "octopus_hand_v2_mm.stl")

    arm_bodies = [obj for obj in bodies if obj.name.startswith("HH_OCT2_SEG_1_")]
    arm_pins = [obj for obj in pins if obj.name.startswith("HH_OCT2_PIN_1_")]
    coupon_parts = build_coupon(palm, arm_bodies, arm_pins, coupon, SPEC)
    export_stl_mm(coupon_parts, OUTPUT / "test_coupon_mm.stl")

    scene["HH_OCT2_ARM_NAMES"] = [f"ARM_{index}" for index in range(1, SPEC.arm_count + 1)]
    scene["HH_OCT2_COUPON_NOTE"] = coupon_note(SPEC)
    scene["HH_OCT2_DESIGN_NOTE"] = (
        "Octopus hand V2: pentagon turned so a corner stands on each arm, corners cut "
        "back and both rims chamfered, a buttress behind every socket, one wire bore "
        "per arm, and grip pads aimed at the palm centre. Unqualified fit prototype; "
        "no grip force, retention or strength claim. Cables are threaded after printing."
    )
    present_octopus_v2(OUTPUT, SPEC, palm, bodies, pins, layout_objects)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "octopus_hand_v2.blend"))
    print("OCTOPUS_HAND_V2_READY", str(OUTPUT))


def main() -> None:
    run_generator(build)


if __name__ == "__main__":
    main()
