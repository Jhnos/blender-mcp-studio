"""Sequential joint bearing take-up, measured on actual surfaces in one shared pose."""

import math
from itertools import combinations

import bpy
from mathutils import Matrix, Vector

from scripts.lab_electrode_check import verify_closed_part
from scripts.lab_station_motion_check import tree
from src.core.domain.lab_station_joints import (
    ElbowClosureSpec,
    ShoulderClosureSpec,
    WristClosureSpec,
)


def closure_spec(joint: str) -> ElbowClosureSpec:
    specs = {"elbow": ElbowClosureSpec, "shoulder": ShoulderClosureSpec, "tip": WristClosureSpec}
    if joint not in specs:
        raise ValueError("Unsupported bearing chain")
    return specs[joint]()


def bearing_pairs(
    label: str, joint: str = "elbow"
) -> list[tuple[bpy.types.Object, bpy.types.Object, float]]:
    closure_spec(joint)
    prefix = "S_" + label + "_"
    support, carrier = {
        "elbow": ("lower", "upper"),
        "shoulder": ("base", "upper"),
        "tip": ("head", "platform"),
    }[joint]
    return [
        (bpy.data.objects[prefix + left], bpy.data.objects[prefix + right], radius)
        for left, right, radius in (
            (joint + "_bolt", joint + "_knob", 3.5),
            (joint + "_knob", support, 6.5),
            (support, carrier, 8.0),
            (carrier, joint + "_nut", 3.5),
        )
    ]


def joint_frame(label: str, joint: str = "elbow") -> Matrix:
    closure_spec(joint)
    side = 1 if label == "capillary" else -1
    support = {"elbow": "upper", "shoulder": "base", "tip": "platform"}[joint]
    return (
        bpy.data.objects[f"S_{label}_{support}"].matrix_world
        @ Matrix.Translation((0, 0.022 if joint == "tip" else 0, 0.15 if joint == "elbow" else 0))
        @ Matrix.Diagonal((side, 1, 1, 1))
    )


def face_coordinate(
    obj: bpy.types.Object, frame: Matrix, radius: float, angle: float, sign: int
) -> float:
    origin = frame @ Vector(
        (sign * 0.03, radius * math.cos(angle) / 1000, radius * math.sin(angle) / 1000)
    )
    direction = frame.to_3x3() @ Vector((-sign, 0, 0))
    inverse = obj.matrix_world.inverted()
    hit, point, _, _ = obj.ray_cast(inverse @ origin, inverse.to_3x3() @ direction)
    if not hit:
        raise ValueError("Missing bearing surface: " + obj.name)
    return float((frame.inverted() @ obj.matrix_world @ point).x * 1000)


def measure_gaps(label: str, joint: str = "elbow") -> list[tuple[float, float]]:
    frame = joint_frame(label, joint)
    result = []
    for left, right, radius in bearing_pairs(label, joint):
        gaps = []
        count = 192 if radius == 8 else 12
        tooth_radii = (6.2, 7.0, 7.8) if joint == "tip" else (6.5, 8.0, 10.0)
        for sample_radius in tooth_radii if radius == 8 else (radius,):
            for index in range(count):
                angle = math.radians(0.37 + index * 360 / count)
                gaps.append(
                    face_coordinate(right, frame, sample_radius, angle, -1)
                    - face_coordinate(left, frame, sample_radius, angle, 1)
                )
        result.append((min(gaps), max(gaps)))
    return result


def verify_pin_service() -> int:
    """Withdraw each pin after removing its clip in the raised, tilted service pose."""
    samples = 0
    for label in ("capillary", "pH_temp"):
        side = 1 if label == "capillary" else -1
        for joint in ("proximal", "distal", "carrier"):
            pin = bpy.data.objects[f"S_{label}_{joint}_pin"]
            clip = bpy.data.objects[f"S_{label}_{joint}_clip"]
            obstacles = {
                obj.name: tree(obj)
                for obj in bpy.data.objects
                if obj.type == "MESH"
                and not obj.hide_render
                and obj.name.startswith(("S_", "LS_FIT_", "LS_REF_vessel"))
                and obj not in (pin, clip)
            }
            saved = pin.matrix_world.copy()
            try:
                for shift in range(26):
                    pin.matrix_world = saved @ Matrix.Translation((-side * shift / 1000, 0, 0))
                    bpy.context.view_layer.update()
                    moved = tree(pin)
                    hits = [name for name, obstacle in obstacles.items() if moved.overlap(obstacle)]
                    if hits:
                        raise ValueError(f"Pin service blocked: {pin.name}, {shift} mm, {hits}")
                    samples += 1
            finally:
                pin.matrix_world = saved
                bpy.context.view_layer.update()
    return samples


def verify_seated(label: str, joint: str = "elbow") -> list[tuple[float, float]]:
    gaps = measure_gaps(label, joint)
    if any(abs(value) > 0.01 for bounds in gaps for value in bounds):
        raise ValueError(joint + " bearing chain is not simultaneously seated: " + str(gaps))
    return gaps


def take_up_offsets(label: str, travel_mm: float, joint: str) -> dict[str, float]:
    offsets = closure_spec(joint).offsets(travel_mm)
    if joint == "shoulder":
        prefix = f"S_{label}_"
        return {
            **{obj.name[len(prefix) :]: offsets["upper"] for obj in shoulder_members(label)},
            **offsets,
        }
    if joint == "tip":
        prefix = f"S_{label}_"
        return {
            **{
                obj.name[len(prefix) :]: offsets["head"]
                for obj in bpy.data.objects
                if obj.name.startswith(prefix)
                and (obj.get("compact_head_part") or obj.name.startswith(prefix + "probe_"))
            },
            **offsets,
        }
    return offsets


def apply_take_up(label: str, travel_mm: float, joint: str = "elbow") -> None:
    """Relative to the aligned pose; shoulder moves its whole connected front assembly."""
    side = 1 if label == "capillary" else -1
    for suffix, offset in take_up_offsets(label, travel_mm, joint).items():
        obj = bpy.data.objects[f"S_{label}_{suffix}"]
        obj.matrix_world = obj.matrix_world @ Matrix.Translation((side * offset / 1000, 0, 0))
    bpy.context.view_layer.update()


def verify_interference(label: str, joint: str = "elbow") -> None:
    moving = {f"S_{label}_{suffix}" for suffix in take_up_offsets(label, 0, joint)}
    objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and not obj.hide_render
        and obj.name.startswith(("S_", "LS_FIT_", "LS_REF_vessel"))
    ]
    meshes = {obj.name: tree(obj) for obj in objects}
    contacts = {
        frozenset((left.name, right.name)): (left, right)
        for contact_joint in ("elbow", "shoulder", "tip")
        for left, right, _ in bearing_pairs(label, contact_joint)
    }
    axis = joint_frame(label, joint).to_3x3() @ Vector((1, 0, 0))
    for first, second in combinations(objects, 2):
        if not moving.intersection((first.name, second.name)) or not meshes[first.name].overlap(
            meshes[second.name]
        ):
            continue
        key = frozenset((first.name, second.name))
        if key not in contacts:
            raise ValueError(f"Take-up obstructed: {first.name}, {second.name}")
        left, right = contacts[key]
        original = left.matrix_world.copy()
        try:
            left.matrix_world = Matrix.Translation(-axis * 0.00001) @ original
            bpy.context.view_layer.update()
            if tree(left).overlap(meshes[right.name]):
                raise ValueError("Bearing penetrates beyond 0.01 mm separation: " + left.name)
        finally:
            left.matrix_world = original
            bpy.context.view_layer.update()


def verify_take_up(label: str, joint: str = "elbow") -> dict[str, object]:
    spec = closure_spec(joint)
    parts = [bpy.data.objects[f"S_{label}_{suffix}"] for suffix in take_up_offsets(label, 0, joint)]
    originals = {obj.name: obj.matrix_world.copy() for obj in parts}
    rows = []
    try:
        for index in range(15):
            travel = spec.stroke_mm * index / 14
            for obj in parts:
                obj.matrix_world = originals[obj.name]
            apply_take_up(label, travel, joint)
            offsets = spec.offsets(travel)
            support = "head" if joint == "tip" else "lower"
            expected = (
                (
                    spec.head_gap_mm + offsets[joint + "_knob"] - offsets[joint + "_bolt"],
                    spec.knob_gap_mm + offsets[support] - offsets[joint + "_knob"],
                    spec.tooth_gap_mm - offsets[support],
                    spec.nut_gap_mm + offsets[joint + "_nut"],
                )
                if joint in ("elbow", "tip")
                else ()
            )
            if joint == "shoulder":
                expected = (
                    spec.head_gap_mm + offsets["shoulder_knob"] - offsets["shoulder_bolt"],
                    spec.knob_gap_mm - offsets["shoulder_knob"],
                    spec.tooth_gap_mm + offsets["upper"],
                    spec.nut_gap_mm + offsets["shoulder_nut"] - offsets["upper"],
                )
            measured = measure_gaps(label, joint)
            for gap, bounds in zip(expected, measured, strict=True):
                if any(abs(value - gap) > 0.01 for value in bounds):
                    raise ValueError(
                        f"Take-up surface gap mismatch: expected {gap}, measured {bounds}"
                    )
            verify_interference(label, joint)
            inverse = joint_frame(label, joint).inverted()
            ends = []
            for suffix in (joint + "_bolt", joint + "_nut"):
                obj = bpy.data.objects[f"S_{label}_{suffix}"]
                transform = inverse @ obj.matrix_world
                ends.append(max((transform @ vertex.co).x for vertex in obj.data.vertices) * 1000)
            protrusion = ends[0] - ends[1]
            if not 0 <= protrusion <= 1.5:
                raise ValueError("Seating loses the bolt end budget: " + str(protrusion))
            rows.append(
                {"travel_mm": travel, "gap_bounds_mm": measured, "bolt_protrusion_mm": protrusion}
            )
        verify_seated(label, joint)
    finally:
        for obj in parts:
            obj.matrix_world = originals[obj.name]
        bpy.context.view_layer.update()
    return {
        "samples": rows,
        "scope": "Rigid nominal seating, not thread engagement, elastic preload or force qualification.",
    }


def shoulder_members(label: str) -> list[bpy.types.Object]:
    prefix = f"S_{label}_"
    fixed = {"base", "yaw_bolt", "yaw_nut", "shoulder_bolt", "shoulder_knob"}
    return [
        obj
        for obj in bpy.data.objects
        if obj.name.startswith(prefix) and obj.name[len(prefix) :] not in fixed
    ]


def apply_shoulder_release(label: str, travel_mm: float) -> None:
    """Relative axial release of the connected front assembly, retaining the base."""
    if not math.isfinite(travel_mm) or not 0 <= travel_mm <= 2:
        raise ValueError("Shoulder release must lie within 0–2 mm")
    side = 1 if label == "capillary" else -1
    for obj in shoulder_members(label):
        obj.matrix_world = obj.matrix_world @ Matrix.Translation((side * travel_mm / 1000, 0, 0))
    bpy.data.objects[f"S_{label}_base"]["shoulder_release_mm"] = travel_mm
    bpy.context.view_layer.update()


def verify_joint_release(label: str, joint: str = "elbow") -> int:
    """Sample joint release against the other arm, hardware, vessel and enclosure."""
    prefix = "S_" + label + "_"
    side = 1 if label == "capillary" else -1
    if joint not in ("elbow", "shoulder"):
        raise ValueError("Unsupported toothed joint")
    moving = (
        shoulder_members(label)
        if joint == "shoulder"
        else [bpy.data.objects[prefix + suffix] for suffix in ("lower", "elbow_bolt", "elbow_knob")]
    )
    originals = {obj.name: obj.matrix_world.copy() for obj in moving}
    obstacles = {
        obj.name: tree(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and not obj.hide_render
        and obj.name.startswith(("S_", "LS_FIT_", "LS_REF_vessel"))
        and obj not in moving
    }
    try:
        for step in range(21):
            for obj in moving:
                obj.matrix_world = originals[obj.name] @ Matrix.Translation(
                    ((-side if joint == "elbow" else side) * step / 10000, 0, 0)
                )
            bpy.context.view_layer.update()
            for obj in moving:
                moved = tree(obj)
                hits = [name for name, obstacle in obstacles.items() if moved.overlap(obstacle)]
                if hits:
                    raise ValueError(f"{joint} release blocked: {obj.name}, {step / 10} mm, {hits}")
    finally:
        for obj in moving:
            obj.matrix_world = originals[obj.name]
        bpy.context.view_layer.update()
    return 21


def verify_joint_teeth(label: str, joint: str = "elbow") -> int:
    """Local mating-face test; isolated rotations do not claim closed-chain arm motion."""
    prefix = "S_" + label + "_"
    if joint not in ("elbow", "shoulder", "tip"):
        raise ValueError("Unsupported toothed joint")
    pair = {
        "elbow": ("upper", "lower"),
        "shoulder": ("base", "upper"),
        "tip": ("platform", "head"),
    }[joint]
    upper, lower = (bpy.data.objects[prefix + suffix] for suffix in pair)
    side = 1 if label == "capillary" else -1
    for part in (upper, lower):
        verify_closed_part(part)
    original = lower.matrix_world.copy()
    fixed = tree(upper)
    samples = 0
    try:
        for release in (0, 2):
            for angle in (-15, -7.5, 0, 7.5, 15):
                lower.matrix_world = (
                    original
                    @ Matrix.Translation(
                        ((-side if joint in ("elbow", "tip") else side) * release / 1000, 0, 0)
                    )
                    @ Matrix.Rotation(math.radians(angle), 4, "X")
                )
                bpy.context.view_layer.update()
                contact = bool(tree(lower).overlap(fixed))
                expected = release == 0 and abs(angle) == 7.5
                if contact != expected:
                    raise ValueError(
                        f"{joint} tooth engagement mismatch: release={release}, angle={angle}, contact={contact}"
                    )
                samples += 1
    finally:
        lower.matrix_world = original
        bpy.context.view_layer.update()
    return samples


def verify_bearing_chains(label: str) -> dict[str, object]:
    return {
        "closure": verify_take_up(label),
        "shoulder_closure": verify_take_up(label, "shoulder"),
        "wrist_closure": verify_take_up(label, "tip"),
    }
