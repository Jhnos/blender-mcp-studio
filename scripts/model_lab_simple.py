"""Reduced two-link assembly study; smooth joint envelopes precede tooth detailing."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, material
from scripts.hollow_hinge_render import look_at
from scripts.lab_station_arm import finish_arm
from scripts.lab_station_joints import block, placed_plate
from scripts.lab_station_motion_check import tree
from scripts.lab_station_rig import set_pose
from src.core.domain.lab_station import SimpleArmSpec

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/lab-station-simple"


def ring(name: str, x: float, z: float, mat: bpy.types.Material) -> bpy.types.Object:
    obj = add_cylinder(name, 18, 8, (x, 0, z), "X")
    boolean(obj, add_cylinder("S_TOOL", 2.7, 12, (x, 0, z), "X"), "DIFFERENCE")
    assign(obj, mat)
    return obj


def link(name: str, offset: float, mat: bpy.types.Material) -> bpy.types.Object:
    obj = add_cylinder(name, 18, 8, (offset, 0, 0), "X")
    assign(obj, mat)
    boolean(obj, block("S_TOOL", (8, 16, 150), (offset, 0, 75), mat), "UNION")
    boolean(obj, add_cylinder("S_TOOL", 18, 8, (offset, 0, 150), "X"), "UNION")
    for z in (0, 150):
        boolean(obj, add_cylinder("S_TOOL", 2.7, 16, (offset, 0, z), "X"), "DIFFERENCE")
    finish_arm(obj)
    return obj


def hardware(prefix: str, metal: bpy.types.Material) -> None:
    bolt = add_cylinder(prefix + "bolt", 2.5, 25, (0.3, 0, 0), "X")
    boolean(bolt, add_cylinder("S_TOOL", 4.5, 4, (-14.2, 0, 0), "X"), "UNION")
    nut = add_cylinder(prefix + "nut", 4.6, 4, (10.3, 0, 0), "X", vertices=6)
    boolean(nut, add_cylinder("S_TOOL", 2.6, 6, (10.3, 0, 0), "X"), "DIFFERENCE")
    for obj in (bolt, nut):
        assign(obj, metal)
        obj["nominal_hardware"] = True


def build_arm(label: str, mat: bpy.types.Material, metal: bpy.types.Material) -> None:
    prefix = "S_" + label + "_"
    link(prefix + "upper", 4.2, mat)
    link(prefix + "lower", -4.2, mat)
    base = add_cylinder(prefix + "base", 18, 8, (-4.2, 0, 0), "X")
    assign(base, mat)
    boolean(base, block("S_TOOL", (8, 18, 28), (-4.2, 0, -14), mat), "UNION")
    boolean(base, add_cylinder("S_TOOL", 24, 6, (0, 0, -25)), "UNION")
    boolean(base, add_cylinder("S_TOOL", 8.2, 3.3, (0, 0, -26.55)), "DIFFERENCE")
    boolean(base, add_cylinder("S_TOOL", 2.7, 12, (0, 0, -25)), "DIFFERENCE")
    boolean(base, add_cylinder("S_TOOL", 2.7, 30, (-4.2, 0, 0), "X"), "DIFFERENCE")
    head = ring(prefix + "head", 4.2, 0, mat)
    boolean(head, block("S_TOOL", (26, 22, 22), (4.2, 0, -20), mat), "UNION")
    for dx, radius, length in (
        ((0, 3, 100),) if label == "capillary" else ((-7, 6, 115), (7, 3, 115))
    ):
        boolean(head, add_cylinder("S_TOOL", radius + 0.3, 30, (4.2 + dx, 0, -20)), "DIFFERENCE")
        probe = add_cylinder(prefix + "probe_" + str(dx), radius, length, (4.2 + dx, 0, -67.5))
        assign(probe, metal)
    for part in (base, head):
        finish_arm(part)
    for joint in ("shoulder", "elbow", "tip"):
        hardware(prefix + joint + "_", metal)
    bolt = add_cylinder(prefix + "yaw_bolt", 2.5, 16, (0, 0, -29.8))
    boolean(bolt, add_cylinder("S_TOOL", 5, 4, (0, 0, -19.8)), "UNION")
    nut = add_cylinder(prefix + "yaw_nut", 4.6, 4, (0, 0, -34), vertices=6)
    boolean(nut, add_cylinder("S_TOOL", 2.6, 6, (0, 0, -34)), "DIFFERENCE")
    for obj in (bolt, nut):
        assign(obj, metal)
        obj["nominal_hardware"] = True


def pose(label: str, lift: float = 0, parked: bool = False) -> None:
    side = -1 if label == "capillary" else 1
    spec = SimpleArmSpec(reach_mm=55, working_rise_mm=85) if parked else SimpleArmSpec()
    points = spec.planar_joints(lift)
    # Local +Y points from each independent base toward the common vessel.
    yaw = math.atan2(side * 80, -190) + (side * math.radians(65) if parked else 0)
    world = Matrix.Translation(Vector((side * 0.098, 0.045, 0.108))) @ Matrix.Rotation(yaw, 4, "Z")
    frames = [world @ Matrix.Translation(Vector((0, p[0] / 1000, p[1] / 1000))) for p in points]
    angles = [
        -math.atan2(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:], strict=False)
    ]
    prefix = "S_" + label + "_"
    for suffix, frame in (
        ("base", world),
        ("upper", frames[0] @ Matrix.Rotation(angles[0], 4, "X")),
        ("lower", frames[1] @ Matrix.Rotation(angles[1], 4, "X")),
        ("head", frames[2]),
    ):
        bpy.data.objects[prefix + suffix].matrix_world = frame
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix + "probe_"):
            obj.matrix_world = frames[2]
    for joint, frame in zip(("shoulder", "elbow", "tip", "yaw"), (*frames, world), strict=True):
        for suffix in ("bolt", "nut"):
            bpy.data.objects[prefix + joint + "_" + suffix].matrix_world = frame
    bpy.context.view_layer.update()


def verify_interfaces(label: str) -> None:
    """Probe real material around the nominal bores, not just object origins."""
    for suffix, x, levels in (
        ("base", -4.2, (0,)),
        ("upper", 4.2, (0, 150)),
        ("lower", -4.2, (0, 150)),
        ("head", 4.2, (0,)),
    ):
        member = bpy.data.objects[f"S_{label}_{suffix}"]
        for z in levels:
            for dz in (0, 6):
                start = Vector(((x - 30) / 1000, 0, (z + dz) / 1000))
                if member.ray_cast(start, Vector((1, 0, 0)))[0] != bool(dz):
                    raise ValueError("Simple joint material disconnected: " + member.name)


def verify_clearance() -> None:
    members = [
        o
        for o in bpy.data.objects
        if o.type == "MESH"
        and o.name.startswith(("S_capillary_", "S_pH_temp_"))
        and not o.get("nominal_hardware")
        and not o.name.endswith("_base")
    ]
    obstacles = [
        bpy.data.objects[n]
        for n in ("LS_FIT_lcd_front", "LS_FIT_lcd_back", "LS_FIT_chassis", "LS_FIT_lid")
    ]
    for member in members:
        for obstacle in obstacles:
            if tree(member).overlap(tree(obstacle)):
                raise ValueError(f"Simple arm clearance: {member.name}, {obstacle.name}")
    for left in members:
        if left.name.startswith("S_capillary_"):
            for right in members:
                if right.name.startswith("S_pH_temp_") and tree(left).overlap(tree(right)):
                    raise ValueError(f"Simple arms collide: {left.name}, {right.name}")


def verify() -> dict[str, object]:
    vessel = bpy.data.objects["LS_REF_vessel_250ml_ENVELOPE"]
    samples = 0
    try:
        for label in ("capillary", "pH_temp"):
            other = "pH_temp" if label == "capillary" else "capillary"
            unchanged = bpy.data.objects[f"S_{other}_head"].matrix_world.copy()
            verify_interfaces(label)
            for amount in range(101):
                pose(label, amount)
                if amount % 10 == 0:
                    verify_clearance()
                for obj in bpy.data.objects:
                    if obj.name.startswith(f"S_{label}_probe_") and tree(obj).overlap(tree(vessel)):
                        raise ValueError("Probe intersects vessel: " + obj.name)
                if bpy.data.objects[f"S_{other}_head"].matrix_world != unchanged:
                    raise ValueError("Other arm moved")
                samples += 1
            pose(label)
    finally:
        pose("capillary")
        pose("pH_temp")
    hardware_count = sum(bool(o.get("nominal_hardware")) for o in bpy.data.objects)
    screen_count = sum(bool(o.get("screen_hardware")) for o in bpy.data.objects)
    if hardware_count != 16 or screen_count != 4:
        raise ValueError("Reduced arm hardware budget exceeded")
    return {
        "probe_vessel_samples": samples,
        "arm_hardware_envelopes": hardware_count,
        "screen_hardware_envelopes": screen_count,
        "mechanism_bolts": 10,
        "mechanism_nuts": 10,
        "independent_sleeves_and_washers": 0,
        "scope": "Manual coordinated lift only; no automatic leveling. Joint teeth, clamp fasteners, load and complete assembly qualification pending.",
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline = OUTPUT / "baseline.blend"
    shutil.copyfile(ROOT / "tmp/lab-station-v10/lab_station_v10.blend", baseline)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    with bpy.data.libraries.load(str(baseline), link=False) as (_, loaded):
        loaded.objects = [
            "LS_FIT_chassis",
            "LS_FIT_lid",
            "LS_FIT_sample_tray",
            "LS_FIT_spill_dish",
            "LS_REF_vessel_250ml_ENVELOPE",
            "LS_VIEW_camera",
        ]
    for obj in loaded.objects:
        if obj:
            bpy.context.collection.objects.link(obj)
    with bpy.data.libraries.load(str(baseline), link=False) as (_, loaded):
        loaded.objects = [
            "LS_SCREEN_CONTROL",
            "LS_REF_HMI_mount",
            "LS_FIT_lcd_front",
            "LS_FIT_lcd_back",
            "LS_REF_touch_glass",
            "LS_REF_lcd_pcb",
            "LS_REF_terminal_allowance",
        ]
    for obj in loaded.objects:
        if obj:
            bpy.context.collection.objects.link(obj)
    screen = bpy.data.objects["LS_SCREEN_CONTROL"]
    screen.location.z -= 0.010
    lid = bpy.data.objects["LS_FIT_lid"]
    lid_mat = lid.data.materials[0]
    for side in (-1, 1):
        hinge_x = -93 if side < 0 else 88
        boolean(lid, block("S_TOOL", (10, 24, 30), (hinge_x, -49, 94.9), lid_mat), "UNION")
        boolean(lid, add_cylinder("S_TOOL", 14, 10, (hinge_x, -49, 118), "X"), "UNION")
        boolean(lid, add_cylinder("S_TOOL", 2.8, 25, (hinge_x, -49, 118), "X"), "DIFFERENCE")
        boolean(lid, add_cylinder("S_TOOL", 8, 3.1, (side * 98, 45, 81.45)), "UNION")
        boolean(lid, add_cylinder("S_TOOL", 2.7, 12, (side * 98, 45, 79)), "DIFFERENCE")
    boolean(lid, placed_plate("S_TOOL", lid_mat, (-89.2, -49, 118), 1, 2.8), "UNION")
    finish_arm(lid)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1100
    scene.render.resolution_percentage = 100
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.camera = bpy.data.objects["LS_VIEW_camera"]
    metal = material("S_metal", (0.48, 0.53, 0.56, 1), 0.5)
    for side in (-1, 1):
        bolt = add_cylinder(f"S_SCREEN_bolt_{side}", 2.5, 32, (side * 87, -49, 118), "X")
        boolean(bolt, add_cylinder("S_TOOL", 4.5, 4, (side * 105, -49, 118), "X"), "UNION")
        nut = add_cylinder(f"S_SCREEN_nut_{side}", 4.6, 4, (side * 73, -49, 118), "X", vertices=6)
        boolean(nut, add_cylinder("S_TOOL", 2.6, 6, (side * 73, -49, 118), "X"), "DIFFERENCE")
        for obj in (bolt, nut):
            assign(obj, metal)
            obj["screen_hardware"] = True
    for label, color in (("capillary", (0.95, 0.52, 0.12, 1)), ("pH_temp", (0.05, 0.60, 0.64, 1))):
        build_arm(label, material("S_" + label, color), metal)
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name.startswith("S_"):
            obj.data.transform(obj.matrix_world)
            obj.matrix_world = Matrix.Identity(4)
            if obj.name.startswith("S_pH_temp_"):
                obj.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
                finish_arm(obj)
    for label in ("capillary", "pH_temp"):
        pose(label)
    report = verify()
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2))
    camera = scene.camera
    camera.location = (0.43, -0.65, 0.43)
    camera.data.ortho_scale = 0.60
    look_at(camera, (0, -60, 130))
    for name, raised, parked in (
        ("working", 0, False),
        ("raised", 100, False),
        ("parked", 0, True),
    ):
        for label in ("capillary", "pH_temp"):
            pose(label, raised, parked)
        set_pose(screen, tilt_step=0 if parked else 4, release_mm=0)
        verify_clearance()
        scene.render.filepath = str(OUTPUT / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    for label in ("capillary", "pH_temp"):
        pose(label)
    set_pose(screen, tilt_step=4, release_mm=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "simple-concept.blend"))


if __name__ == "__main__":
    main()
