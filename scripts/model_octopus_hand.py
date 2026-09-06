"""V1 composition: pentagonal palm, five V6 arms, captive pins, tips and artifacts."""

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
from scripts.octopus_hand_presentation import layout_parts, present_octopus  # noqa: E402
from scripts.octopus_palm_geometry import create_palm  # noqa: E402
from scripts.octopus_tip_geometry import add_tip_features  # noqa: E402
from src.core.domain.octopus_hand import OctopusHandSpec  # noqa: E402

SPEC = OctopusHandSpec()
OUTPUT = PROJECT_ROOT / "tmp" / "octopus-hand-v1"


def body_rotation_deg(index: int) -> float:
    """Twist of arm body `index` (1-based) within its own chain.

    The palm's socket stands in for body zero, so the first arm body is the one
    that has to turn ninety degrees to bring its ears onto the socket's axis.
    """
    return 90.0 if index % 2 else 0.0


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
    spec = SPEC
    arm = spec.arm_spec
    bodies: list[bpy.types.Object] = []
    for index in range(1, spec.arm_body_count + 1):
        is_tip = index == spec.arm_body_count
        source = tip_master if is_tip else master
        obj = source.copy()
        obj.data = source.data
        # Tips carry extra geometry, so they cannot share the bodies' mesh. The
        # oracle requires one datablock per prefix, so they get their own name space.
        obj.name = f"HH_OCT_TIP_{arm_index}" if is_tip else f"HH_OCT_SEG_{arm_index}_{index}"
        target.objects.link(obj)
        obj.location = (m(station_mm[0]), m(station_mm[1]), m(index * arm.unit_pitch_mm))
        twist = (station_angle_deg + body_rotation_deg(index)) % 360.0
        obj.rotation_euler.z = math.radians(twist)
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
    spec = SPEC
    arm = spec.arm_spec
    outer = arm.pin_under_head_radius_mm + arm.pin_head_height_mm
    swing = math.radians(station_angle_deg)
    cos_a, sin_a = math.cos(swing), math.sin(swing)
    pins: list[bpy.types.Object] = []
    for joint in range(spec.arm_body_count):
        z_mm = joint * arm.unit_pitch_mm + arm.joint_center_offset_mm
        for side in (-1, 1):
            obj = master.copy()
            obj.data = master.data
            obj.name = f"HH_OCT_PIN_{arm_index}_{joint + 1}_{side}"
            target.objects.link(obj)
            local = Vector((-side, 0.0, 0.0)) if joint % 2 == 0 else Vector((0.0, -side, 0.0))
            direction = Vector(
                (
                    local.x * cos_a - local.y * sin_a,
                    local.x * sin_a + local.y * cos_a,
                    0.0,
                )
            )
            obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
            local_offset = (side * outer, 0.0) if joint % 2 == 0 else (0.0, side * outer)
            obj.location = (
                m(station_mm[0] + local_offset[0] * cos_a - local_offset[1] * sin_a),
                m(station_mm[1] + local_offset[0] * sin_a + local_offset[1] * cos_a),
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
    teal = material("HH_OCT_PALM_MAT", (0.10, 0.55, 0.52, 1))
    gold = material("HH_OCT_BODY", (0.82, 0.48, 0.12, 1))
    light = material("HH_OCT_ALT", (1.0, 0.7, 0.24, 1))
    cyan = material("HH_OCT_PIN", (0.03, 0.7, 0.9, 1))

    hand, hardware, layout = (
        collection("HH_OCT_" + name) for name in ("HAND", "HARDWARE", "LAYOUT")
    )

    palm = create_palm(hand, teal, SPEC)
    master = create_body(hand, gold, arm)
    master.name = "HH_OCT_MASTER_BODY"
    cut_retainer_seats(master, arm)

    # Copy the tip master while the body is still visible, and keep it visible until
    # its features are applied. `hide_viewport` drops an object out of the depsgraph,
    # and a Boolean applied to an object that is not evaluated silently does nothing —
    # the export then looks fine, because these features do not change the bounding box.
    tip_master = master.copy()
    tip_master.data = master.data.copy()
    tip_master.name = "HH_OCT_MASTER_TIP"
    hand.objects.link(tip_master)
    add_tip_features(tip_master, SPEC)
    if len(tip_master.data.polygons) <= len(master.data.polygons):
        # Observed 2026-09-06: with the tip master hidden, every Boolean was skipped
        # and arm_tip_mm.stl came out byte-identical to arm_body_mm.stl — 3436
        # triangles each. Neither the dimension readback nor the artifact contract
        # could see it, because eyelets and claw sit inside the body's bounding box.
        raise RuntimeError(
            "tip features did not apply: "
            f"{len(tip_master.data.polygons)} faces vs the plain body's "
            f"{len(master.data.polygons)}"
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
    export_stl_mm([palm, *bodies], OUTPUT / "octopus_hand_v1_mm.stl")

    scene["HH_OCT_ARM_NAMES"] = [f"ARM_{index}" for index in range(1, SPEC.arm_count + 1)]
    scene["HH_OCT_DESIGN_NOTE"] = (
        "Octopus hand V1: pentagonal palm, five V6 biaxial arms, print-in-place captive "
        "pins, four cable eyelets and one claw per tip. Unqualified fit prototype; no "
        "grip force, retention or strength claim. Cables are threaded after printing."
    )
    present_octopus(OUTPUT, SPEC, [palm, *bodies, *pins], layout_objects)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "octopus_hand_v1.blend"))
    print("OCTOPUS_HAND_READY", str(OUTPUT))


def main() -> None:
    run_generator(build)


if __name__ == "__main__":
    main()
