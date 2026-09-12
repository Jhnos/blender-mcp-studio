"""Electrode-holder concept: retained upper hinge, parallel forearm, triangular head carrier."""

from __future__ import annotations

import json
import math
import shutil
from itertools import combinations
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, loft_rings
from scripts.hollow_hinge_render import look_at
from scripts.lab_station_arm import finish_arm
from scripts.lab_station_joints import block
from scripts.lab_station_motion_check import tree
from scripts.lab_station_rig import set_pose
from scripts.model_lab_simple import hardware, link, ring, verify_clearance
from src.core.domain.lab_station import ElectrodeArmSpec

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/lab-station-electrode"


def bake(obj: bpy.types.Object, side: int) -> None:
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    if side > 0:
        obj.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    finish_arm(obj)


def build(label: str) -> None:
    side = -1 if label == "capillary" else 1
    prefix = "S_" + label + "_"
    upper = bpy.data.objects[prefix + "upper"]
    mat = upper.data.materials[0]
    # Work in the existing upper-arm local mesh, then restore its world frame.
    saved = upper.matrix_world.copy()
    upper.matrix_world = Matrix.Identity(4)
    x = 4.2 if side < 0 else -4.2
    boolean(upper, add_cylinder("E_TOOL", 18, 8, (x, 0, 110), "X"), "UNION")
    boolean(upper, add_cylinder("E_TOOL", 2.7, 40, (x, 0, 110), "X"), "DIFFERENCE")
    finish_arm(upper)
    upper.matrix_world = saved
    obj = link(prefix + "follower", 12.6, mat)
    bake(obj, side)
    vertices = ((0, 0), (0, -40), (45, 0))
    obj = loft_rings(prefix + "platform", [[(x, y, z) for y, z in vertices] for x in (0.2, 8.2)])
    assign(obj, mat)
    for y, z in vertices:
        boolean(obj, add_cylinder("E_TOOL", 18, 8, (4.2, y, z), "X"), "UNION")
    for y, z in vertices:
        boolean(obj, add_cylinder("E_TOOL", 2.7, 30, (4.2, y, z), "X"), "DIFFERENCE")
    bake(obj, side)
    bpy.data.objects.remove(bpy.data.objects[prefix + "head"], do_unlink=True)
    obj = ring(prefix + "head", -4.2, 0, mat)
    boolean(obj, block("E_TOOL", (24, 16, 12), (-14, 0, -16), mat), "UNION")
    boolean(obj, block("E_TOOL", (26, 22, 22), (-20, 0, -20), mat), "UNION")
    for dx, radius in ((0, 3),) if label == "capillary" else ((-7, 6), (7, 3)):
        boolean(obj, add_cylinder("E_TOOL", radius + 0.3, 30, (-20 + dx, 0, -20)), "DIFFERENCE")
    bake(obj, side)
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix + "probe_"):
            obj.data.transform(Matrix.Translation(((-24.2 if side < 0 else 24.2) / 1000, 0, 0)))
    hardware(prefix + "carrier_", bpy.data.materials["S_metal"])
    for suffix in ("bolt", "nut"):
        bake(bpy.data.objects[prefix + "carrier_" + suffix], side)
    for suffix in ("proximal_pin", "distal_pin"):
        obj = add_cylinder(prefix + suffix, 2.4, 22, (8.2, 0, 0), "X")
        boolean(obj, add_cylinder("E_TOOL", 4.5, 2, (18.2, 0, 0), "X"), "UNION")
        assign(obj, mat)
        obj["printed_pin_envelope"] = True
        bake(obj, side)


def pose(label: str, forward: float = 0, lift: float = 0) -> None:
    root, a, b, c, d, tip = ElectrodeArmSpec().joints(forward, lift)
    side = -1 if label == "capillary" else 1
    world = Matrix.Translation((side * 0.098, 0.045, 0.108)) @ Matrix.Rotation(
        math.atan2(side * 80, -190)
        + math.atan2(math.hypot(80, 190), -side * 4.2)
        - math.atan2(ElectrodeArmSpec().reach_mm, side * 20),
        4,
        "Z",
    )

    def at(point: tuple[float, float]) -> Matrix:
        return world @ Matrix.Translation((0, point[0] / 1000, point[1] / 1000))

    upper_angle = -math.atan2(a[0], a[1])
    lower_angle = -math.atan2(c[0] - a[0], c[1] - a[1])
    prefix = "S_" + label + "_"
    for suffix, matrix in (
        ("base", world),
        ("upper", at(root) @ Matrix.Rotation(upper_angle, 4, "X")),
        ("lower", at(a) @ Matrix.Rotation(lower_angle, 4, "X")),
        ("follower", at(b) @ Matrix.Rotation(lower_angle, 4, "X")),
        ("platform", at(c) @ Matrix.Rotation(upper_angle, 4, "X")),
        ("head", at(tip)),
        ("proximal_pin", at(b)),
        ("distal_pin", at(d)),
    ):
        bpy.data.objects[prefix + suffix].matrix_world = matrix
    for joint, point in (
        ("shoulder", root),
        ("elbow", a),
        ("carrier", c),
        ("tip", tip),
        ("yaw", root),
    ):
        for suffix in ("bolt", "nut"):
            bpy.data.objects[prefix + joint + "_" + suffix].matrix_world = at(point)
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix + "probe_"):
            obj.matrix_world = at(tip)
    bpy.context.view_layer.update()


def verify_local(label: str) -> None:
    prefix = "S_" + label + "_"
    members = [
        bpy.data.objects[prefix + s]
        for s in ("base", "upper", "lower", "follower", "platform", "head")
    ]
    for first, second in combinations(members, 2):
        if tree(first).overlap(tree(second)):
            raise ValueError(f"Electrode self collision: {first.name}, {second.name}")
    # Compare physical bore locations on each mesh through its evaluated world matrix.
    side = 1 if label == "capillary" else -1
    upper, lower, follower, platform, head = members[1:]

    def point(obj: bpy.types.Object, x: float, y: float, z: float) -> Vector:
        local = Vector((side * x / 1000, y / 1000, z / 1000))
        start = local + Vector((-0.08, 0, 0))
        for offset in (0, 0.006):
            if obj.ray_cast(start + Vector((0, 0, offset)), Vector((1, 0, 0)))[0] != bool(offset):
                raise ValueError("Electrode bore material disconnected: " + obj.name)
        return obj.matrix_world @ local

    for first, second in (
        (point(upper, 4.2, 0, 150), point(lower, -4.2, 0, 0)),
        (point(upper, 4.2, 0, 110), point(follower, 12.6, 0, 0)),
        (point(lower, -4.2, 0, 150), point(platform, 4.2, 0, 0)),
        (point(follower, 12.6, 0, 150), point(platform, 4.2, 0, -40)),
        (point(platform, 4.2, 45, 0), point(head, -4.2, 0, 0)),
    ):
        # Axes may differ in X by layer spacing but must be coaxial in the arm plane.
        axis = upper.matrix_world.to_3x3() @ Vector((1, 0, 0))
        delta = first - second
        if (delta - axis * delta.dot(axis)).length > 1e-7:
            raise ValueError("Electrode physical joint disconnected")


def verify() -> dict[str, object]:
    rows = []
    vessel = bpy.data.objects["LS_REF_vessel_250ml_ENVELOPE"]
    for label in ("capillary", "pH_temp"):
        other = "pH_temp" if label == "capillary" else "capillary"
        saved = bpy.data.objects[f"S_{other}_head"].matrix_world.copy()
        for forward in (-20, 0, 20):
            for lift in range(0 if forward == 0 else 100, 101, 5):
                pose(label, forward, lift)
                verify_local(label)
                verify_clearance()
                for obj in bpy.data.objects:
                    if obj.name.startswith(f"S_{label}_probe_") and tree(obj).overlap(tree(vessel)):
                        raise ValueError("Electrode probe intersects vessel")
                if bpy.data.objects[f"S_{other}_head"].matrix_world != saved:
                    raise ValueError("Other head moved")
                rows.append((label, forward, lift))
        pose(label)
    screen = bpy.data.objects["LS_SCREEN_CONTROL"]
    for label in ("capillary", "pH_temp"):
        pose(label, 0, 100)
    for step in range(16):
        set_pose(screen, tilt_step=step / 3, release_mm=0)
        verify_clearance()
    set_pose(screen, tilt_step=4, release_mm=0)
    for label in ("capillary", "pH_temp"):
        pose(label)
    actual_metal = sum(
        bool(o.get("nominal_hardware") or o.get("screen_hardware")) for o in bpy.data.objects
    )
    if actual_metal != 24:
        raise ValueError("Electrode hardware budget changed")
    return {
        "samples": rows,
        "sample_count": len(rows),
        "screen_samples_with_raised_heads": 16,
        "metal_screws": 12,
        "metal_nuts": 12,
        "printed_pivot_envelopes": 4,
        "scope": "Sampled manual coordinated motion, not automatic vertical guidance. Printed-pin retention, locks, load and printing remain unqualified.",
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline = OUTPUT / "baseline.blend"
    shutil.copyfile(ROOT / "tmp/lab-station-simple/simple-concept.blend", baseline)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    with bpy.data.libraries.load(str(baseline), link=False) as (source, loaded):
        loaded.objects = source.objects
    for obj in loaded.objects:
        if obj is not None:
            bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.update()
    for label in ("capillary", "pH_temp"):
        build(label)
        pose(label)
    report = verify()
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1100
    scene.render.resolution_percentage = 100
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.camera = bpy.data.objects["LS_VIEW_camera"]
    scene.camera.location = (0.43, -0.65, 0.45)
    scene.camera.data.ortho_scale = 0.65
    look_at(scene.camera, (0, -60, 150))
    for name, forward, lift in (
        ("working", 0, 0),
        ("raised", 0, 100),
        ("extended", 20, 100),
        ("screen_folded", 0, 100),
    ):
        for label in ("capillary", "pH_temp"):
            pose(label, forward, lift)
        set_pose(
            bpy.data.objects["LS_SCREEN_CONTROL"],
            tilt_step=0 if name == "screen_folded" else 4,
            release_mm=0,
        )
        verify_clearance()
        scene.render.filepath = str(OUTPUT / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    for label in ("capillary", "pH_temp"):
        pose(label)
    set_pose(bpy.data.objects["LS_SCREEN_CONTROL"], tilt_step=4, release_mm=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "electrode-concept.blend"))


if __name__ == "__main__":
    main()
