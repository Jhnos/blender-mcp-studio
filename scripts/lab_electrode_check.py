"""World-space interfaces and assembly checks for the compact electrode arms."""

import math
from itertools import combinations

import bmesh
import bpy
from mathutils import Matrix, Vector

from scripts.hand_gates import shell_count
from scripts.lab_station_motion_check import tree
from scripts.model_lab_simple import verify_clearance
from src.core.domain.lab_station import ElectrodeArmSpec


def verify_closed_part(part: bpy.types.Object) -> None:
    mesh = bmesh.new()
    mesh.from_mesh(part.data)
    invalid_edges = sum(not edge.is_manifold for edge in mesh.edges)
    mesh.free()
    if shell_count(part) != 1 or invalid_edges:
        raise ValueError("Part is not one closed solid: " + part.name)


def verify_forearm_stack() -> dict[str, float]:
    """Read actual shaft faces: both forearm bars occupy the same axial layer."""
    widths = {}
    for label in ("capillary", "pH_temp"):
        side = 1 if label == "capillary" else -1
        faces = []
        extent: list[float] = []
        for suffix in ("lower", "follower"):
            part = bpy.data.objects[f"S_{label}_{suffix}"]
            verify_closed_part(part)
            pair = []
            for sign in (-1, 1):
                hit, point, _, _ = part.ray_cast(
                    Vector((side * sign * 0.03, 0, 0.075)), Vector((-side * sign, 0, 0))
                )
                if not hit:
                    raise ValueError("Forearm shaft face missing: " + part.name)
                pair.append(side * point.x * 1000)
            faces.append(pair)
            extent.extend(side * vertex.co.x * 1000 for vertex in part.data.vertices)
        if any(abs(a - b) > 0.01 for a, b in zip(*faces, strict=True)):
            raise ValueError("Forearm bars are not in one axial layer: " + label)
        widths[label] = max(extent) - min(extent)
        if widths[label] > 10:
            raise ValueError("Forearm body stack exceeds 10 mm: " + label)
    return widths


def verify_local(label: str) -> None:
    prefix = "S_" + label + "_"
    members = [
        bpy.data.objects[prefix + s]
        for s in ("base", "upper", "lower", "follower", "platform", "head")
    ]
    extra = [
        obj
        for obj in bpy.data.objects
        if obj.name.startswith(prefix) and obj.get("compact_head_part") and obj not in members
    ]
    trees = {obj.name: tree(obj) for obj in [*members, *extra]}
    for first, second in combinations([*members, *extra], 2):
        if trees[first.name].overlap(trees[second.name]):
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
        (point(upper, 4.2, 0, 126), point(follower, -4.2, 0, 0)),
        (point(lower, -4.2, 0, 150), point(platform, 4.2, 0, 0)),
        (point(follower, -4.2, 0, 150), point(platform, 4.2, 0, -24)),
        (point(platform, 4.2, ElectrodeArmSpec.platform_offset_mm, 0), point(head, -4.2, 0, 0)),
    ):
        # Axes may differ in X by layer spacing but must be coaxial in the arm plane.
        axis = upper.matrix_world.to_3x3() @ Vector((1, 0, 0))
        delta = first - second
        if (delta - axis * delta.dot(axis)).length > 1e-7:
            raise ValueError("Electrode physical joint disconnected")


def verify_pins(label: str) -> int:
    """Rigid clearance/axial stops; elastic clip installation is not certified."""
    prefix = "S_" + label + "_"
    side = 1 if label == "capillary" else -1
    members = [
        bpy.data.objects[prefix + name]
        for name in ("base", "upper", "lower", "follower", "platform", "head")
    ]
    obstacles = [tree(member) for member in members]
    samples = 0
    for joint in ("proximal", "distal", "carrier"):
        pin = bpy.data.objects.get(prefix + joint + "_pin")
        if pin is None:
            raise ValueError("Passive pivot missing pin: " + joint)
        clip = bpy.data.objects.get(prefix + joint + "_clip")
        if clip is None:
            raise ValueError("Passive pivot missing retainer: " + joint)
        original = pin.matrix_world.copy()
        clip_original = clip.matrix_world.copy()
        try:
            if tree(pin).overlap(tree(clip)) or any(
                tree(part).overlap(obstacle) for part in (pin, clip) for obstacle in obstacles
            ):
                raise ValueError("Passive pivot neutral interference")
            stop_travel = 3.5 if joint == "carrier" else 1.5
            for shift in (-stop_travel, stop_travel):
                delta = Matrix.Translation((side * shift / 1000, 0, 0))
                pin.matrix_world = original @ delta
                clip.matrix_world = clip_original @ delta
                bpy.context.view_layer.update()
                if not any(
                    tree(part).overlap(obstacle) for part in (pin, clip) for obstacle in obstacles
                ):
                    raise ValueError("Passive pivot lacks axial stop")
                samples += 1
            clip.matrix_world = clip_original
            for shift in (-0.6, 0.6):
                pin.matrix_world = original @ Matrix.Translation((side * shift / 1000, 0, 0))
                bpy.context.view_layer.update()
                if not tree(pin).overlap(tree(clip)):
                    raise ValueError("Retainer misses pin groove shoulder")
                samples += 1
            # Remove clip before sliding pin out/in; no rigid snap-through claim.
            for shift in range(26):
                pin.matrix_world = original @ Matrix.Translation((-side * shift / 1000, 0, 0))
                bpy.context.view_layer.update()
                if any(tree(pin).overlap(obstacle) for obstacle in obstacles):
                    raise ValueError("Passive pin insertion path obstructed")
                samples += 1
        finally:
            pin.matrix_world = original
            clip.matrix_world = clip_original
            bpy.context.view_layer.update()
    return samples


def verify_bearing_contacts(
    pairs: list[tuple[bpy.types.Object, bpy.types.Object, float]], side: int
) -> None:
    """Require each bearing face within its local take-up budget, not force qualification."""
    for moving, fixed, travel_mm in pairs:
        original = moving.matrix_world.copy()
        try:
            if tree(moving).overlap(tree(fixed)):
                raise ValueError("Bearing faces already interfere: " + moving.name)
            moving.matrix_world = original @ Matrix.Translation((side * travel_mm / 1000, 0, 0))
            bpy.context.view_layer.update()
            if not tree(moving).overlap(tree(fixed)):
                raise ValueError("Bearing contact missing within take-up budget: " + moving.name)
        finally:
            moving.matrix_world = original
            bpy.context.view_layer.update()


def verify_knobs(label: str) -> None:
    prefix = "S_" + label + "_"
    obstacles = {
        obj.name: tree(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name.startswith(prefix) and not obj.get("nominal_hardware")
    }
    for joint in ("shoulder", "elbow", "tip"):
        knob = bpy.data.objects.get(prefix + joint + "_knob")
        if knob is None:
            raise ValueError("Missing hand knob: " + joint)
        knob_tree = obstacles[knob.name]
        for name, obstacle in obstacles.items():
            if name != knob.name and knob_tree.overlap(obstacle):
                raise ValueError("Hand knob interference: " + knob.name + ", " + name)
        bolt = bpy.data.objects[prefix + joint + "_bolt"]
        nut = bpy.data.objects[prefix + joint + "_nut"]
        side = 1 if label == "capillary" else -1
        bolt_end = max(side * vertex.co.x for vertex in bolt.data.vertices)
        nut_end = max(side * vertex.co.x for vertex in nut.data.vertices)
        if joint == "tip":
            coordinates = [
                side * vertex.co.x * 1000
                for part in (knob, bolt, nut)
                for vertex in part.data.vertices
            ]
            if max(coordinates) - min(coordinates) > 24.81:
                raise ValueError("Wrist fastener stack exceeds 24.8 mm")
        protrusion_mm = (bolt_end - nut_end) * 1000
        if not 0 <= protrusion_mm <= 1.5:
            raise ValueError(f"Knob bolt exposed end outside budget: {protrusion_mm:.3f} mm")
        body = bpy.data.objects[prefix + ("platform" if joint == "tip" else "upper")]
        support = bpy.data.objects[
            prefix + {"shoulder": "base", "elbow": "lower", "tip": "head"}[joint]
        ]
        verify_bearing_contacts(
            [
                (bolt, knob, 0.3),
                (knob, support, 0.2),
                (
                    support,
                    body,
                    0.5 + float(support.get(joint + "_release_mm", 0)),
                ),
                (nut, body, -0.3),
            ],
            side,
        )
        for moving, fixed in ((bolt, knob_tree), (nut, obstacles[body.name])):
            if tree(moving).overlap(fixed):
                raise ValueError("Hex capture neutral interference")
            saved = moving.matrix_world.copy()
            try:
                moving.matrix_world = saved @ Matrix.Rotation(math.pi / 6, 4, "X")
                bpy.context.view_layer.update()
                if not tree(moving).overlap(fixed):
                    raise ValueError("Hex capture cannot transmit torque")
            finally:
                moving.matrix_world = saved
                bpy.context.view_layer.update()


def verify_head_envelopes() -> dict[str, float]:
    """Measure actual cap depth below the wrist axis independently of the builder."""
    depths = {}
    for label, limit_mm in (("capillary", 29), ("pH_temp", 47)):
        cap = bpy.data.objects[f"S_{label}_clamp_cap"]
        depth_mm = -min(vertex.co.z for vertex in cap.data.vertices) * 1000
        if depth_mm > limit_mm + 0.01:
            raise ValueError(f"Probe head hangs too far below wrist: {label}, {depth_mm:.3f} mm")
        depths[label] = depth_mm
    return depths


def verify_platform_geometry() -> int:
    """Independent silhouette and material-ring samples on both real platform meshes."""
    for label in ("capillary", "pH_temp"):
        obj = bpy.data.objects[f"S_{label}_platform"]
        verify_closed_part(obj)
        ys = [vertex.co.y * 1000 for vertex in obj.data.vertices]
        if max(ys) - min(ys) > 40.01:
            raise ValueError("Electrode platform extends beyond compact envelope")
        for y, z in ((0, 0), (0, -24), (22, 0)):
            for index in range(24):
                angle = index * math.pi / 12
                start = Vector((-0.05, y / 1000, z / 1000))
                start += Vector((0, 0.008 * math.cos(angle), 0.008 * math.sin(angle)))
                if not obj.ray_cast(start, Vector((1, 0, 0)))[0]:
                    raise ValueError("Electrode platform lacks bore surround")
    return 144


def verify_clamps() -> dict[str, int]:
    """Check real meshes and straight removal paths; no elastic force qualification."""
    samples, printed = 0, 0
    for label, liner_count in (("capillary", 2), ("pH_temp", 4)):
        prefix = "S_" + label + "_"
        suffixes = ["head", "clamp_cap"] + [f"clamp_liner_{i}" for i in range(liner_count)]
        suffixes += [f"clamp_{i}_{kind}" for i in range(2) for kind in ("bolt", "nut")]
        missing = [
            prefix + suffix for suffix in suffixes if prefix + suffix not in bpy.data.objects
        ]
        if missing:
            raise ValueError("Missing removable probe clamp parts: " + str(missing))
        parts = [bpy.data.objects[prefix + suffix] for suffix in suffixes]
        for part in parts:
            if part.get("nominal_hardware"):
                continue
            verify_closed_part(part)
            printed += 1
        probes = [o for o in bpy.data.objects if o.name.startswith(prefix + "probe_")]
        if len(probes) != liner_count // 2:
            raise ValueError("Incomplete probe clamp population: " + label)
        neutral = {o.name: tree(o) for o in (*parts, *probes)}
        for first, second in combinations(neutral, 2):
            if neutral[first].overlap(neutral[second]):
                raise ValueError("Probe clamp neutral interference: " + first + ", " + second)
        head, cap = parts[:2]
        for index in range(liner_count):
            liner = bpy.data.objects[prefix + f"clamp_liner_{index}"]
            original = liner.matrix_world.copy()
            try:
                for shift in (-0.002, 0.002):
                    liner.matrix_world = original @ Matrix.Translation((0, 0, shift))
                    bpy.context.view_layer.update()
                    moved = tree(liner)
                    if not any(moved.overlap(neutral[o.name]) for o in (head, cap)):
                        raise ValueError("Probe liner lacks axial stop: " + liner.name)
                    samples += 1
            finally:
                liner.matrix_world = original
                bpy.context.view_layer.update()
        bolts = [bpy.data.objects[prefix + f"clamp_{i}_bolt"] for i in range(2)]
        nuts = [bpy.data.objects[prefix + f"clamp_{i}_nut"] for i in range(2)]
        moving_cap = [cap, *nuts] + [
            bpy.data.objects[prefix + f"clamp_liner_{i}"] for i in range(1, liner_count, 2)
        ]
        operations = [(moving_cap, bolts, 1, 25)]
        operations += [
            (
                [probe, bpy.data.objects[prefix + f"clamp_liner_{2 * index}"]],
                [*moving_cap, *bolts],
                1,
                25,
            )
            for index, probe in enumerate(sorted(probes, key=lambda obj: obj.name))
        ]
        operations += [([bolt], [], -1, 25) for bolt in bolts]
        operations += [([nut], [], 1, 12) for nut in nuts]
        for moving, removed, sign, distance in operations:
            obstacles = {
                obj.name: tree(obj)
                for obj in bpy.data.objects
                if obj.type == "MESH"
                and not obj.hide_render
                and obj.name.startswith(("S_", "LS_FIT_", "LS_REF_vessel"))
                and obj not in moving
                and obj not in removed
            }
            originals = {obj.name: obj.matrix_world.copy() for obj in moving}
            try:
                for step in range(distance + 1):
                    for obj in moving:
                        obj.matrix_world = originals[obj.name] @ Matrix.Translation(
                            (0, sign * step / 1000, 0)
                        )
                    bpy.context.view_layer.update()
                    for obj in moving:
                        moved = tree(obj)
                        hits = [
                            name for name, obstacle in obstacles.items() if moved.overlap(obstacle)
                        ]
                        if hits:
                            raise ValueError(
                                f"Probe clamp removal blocked: {obj.name}, step={step}, {hits}"
                            )
                    samples += 1
            finally:
                for obj in moving:
                    obj.matrix_world = originals[obj.name]
                bpy.context.view_layer.update()
    return {"closed_printed_parts": printed, "assembly_and_stop_samples": samples}


def verify_pose(label: str) -> int:
    verify_local(label)
    verify_knobs(label)
    verify_clearance()
    vessel = tree(bpy.data.objects["LS_REF_vessel_250ml_ENVELOPE"])
    for obj in bpy.data.objects:
        if obj.name.startswith(f"S_{label}_probe_") and tree(obj).overlap(vessel):
            raise ValueError("Electrode probe intersects vessel")
    return verify_pins(label)
