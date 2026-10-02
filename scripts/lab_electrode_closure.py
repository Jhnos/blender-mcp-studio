"""Sequential elbow bearing take-up, measured on actual surfaces in one shared pose."""

import math
from itertools import combinations

import bpy
from mathutils import Matrix, Vector

from scripts.lab_station_motion_check import tree
from src.core.domain.lab_station_joints import ElbowClosureSpec


def bearing_pairs(label: str) -> list[tuple[bpy.types.Object, bpy.types.Object, float]]:
    prefix = "S_" + label + "_"
    return [
        (bpy.data.objects[prefix + left], bpy.data.objects[prefix + right], radius)
        for left, right, radius in (
            ("elbow_bolt", "elbow_knob", 3.5),
            ("elbow_knob", "lower", 6.5),
            ("lower", "upper", 8.0),
            ("upper", "elbow_nut", 3.5),
        )
    ]


def joint_frame(label: str) -> Matrix:
    side = 1 if label == "capillary" else -1
    return (
        bpy.data.objects[f"S_{label}_upper"].matrix_world
        @ Matrix.Translation((0, 0, 0.15))
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


def measure_gaps(label: str) -> list[tuple[float, float]]:
    frame = joint_frame(label)
    result = []
    for left, right, radius in bearing_pairs(label):
        gaps = []
        count = 192 if radius == 8 else 12
        for sample_radius in (6.5, 8.0, 10.0) if radius == 8 else (radius,):
            for index in range(count):
                angle = math.radians(0.37 + index * 360 / count)
                gaps.append(
                    face_coordinate(right, frame, sample_radius, angle, -1)
                    - face_coordinate(left, frame, sample_radius, angle, 1)
                )
        result.append((min(gaps), max(gaps)))
    return result


def verify_seated(label: str) -> list[tuple[float, float]]:
    gaps = measure_gaps(label)
    if any(abs(value) > 0.01 for bounds in gaps for value in bounds):
        raise ValueError("Elbow bearing chain is not simultaneously seated: " + str(gaps))
    return gaps


def apply_take_up(label: str, travel_mm: float) -> None:
    """Relative to the current aligned, uncompressed pose; do not call cumulatively."""
    side = 1 if label == "capillary" else -1
    for suffix, offset in ElbowClosureSpec().offsets(travel_mm).items():
        obj = bpy.data.objects[f"S_{label}_{suffix}"]
        obj.matrix_world = obj.matrix_world @ Matrix.Translation((side * offset / 1000, 0, 0))
    bpy.context.view_layer.update()


def verify_interference(label: str) -> None:
    moving = {f"S_{label}_{suffix}" for suffix in ElbowClosureSpec().offsets(0)}
    objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and not obj.hide_render
        and obj.name.startswith(("S_", "LS_FIT_", "LS_REF_vessel"))
    ]
    meshes = {obj.name: tree(obj) for obj in objects}
    contacts = {
        frozenset((left.name, right.name)): (left, right) for left, right, _ in bearing_pairs(label)
    }
    axis = joint_frame(label).to_3x3() @ Vector((1, 0, 0))
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


def verify_take_up(label: str) -> dict[str, object]:
    spec = ElbowClosureSpec()
    parts = [bpy.data.objects[f"S_{label}_{suffix}"] for suffix in spec.offsets(0)]
    originals = {obj.name: obj.matrix_world.copy() for obj in parts}
    rows = []
    try:
        for index in range(15):
            travel = spec.stroke_mm * index / 14
            for obj in parts:
                obj.matrix_world = originals[obj.name]
            apply_take_up(label, travel)
            offsets = spec.offsets(travel)
            expected = (
                spec.head_gap_mm + offsets["elbow_knob"] - offsets["elbow_bolt"],
                spec.knob_gap_mm + offsets["lower"] - offsets["elbow_knob"],
                spec.tooth_gap_mm - offsets["lower"],
                spec.nut_gap_mm + offsets["elbow_nut"],
            )
            measured = measure_gaps(label)
            for gap, bounds in zip(expected, measured, strict=True):
                if any(abs(value - gap) > 0.01 for value in bounds):
                    raise ValueError(
                        f"Take-up surface gap mismatch: expected {gap}, measured {bounds}"
                    )
            verify_interference(label)
            inverse = joint_frame(label).inverted()
            ends = []
            for suffix in ("elbow_bolt", "elbow_nut"):
                obj = bpy.data.objects[f"S_{label}_{suffix}"]
                transform = inverse @ obj.matrix_world
                ends.append(max((transform @ vertex.co).x for vertex in obj.data.vertices) * 1000)
            protrusion = ends[0] - ends[1]
            if not 0 <= protrusion <= 1.5:
                raise ValueError("Seating loses the bolt end budget: " + str(protrusion))
            rows.append(
                {"travel_mm": travel, "gap_bounds_mm": measured, "bolt_protrusion_mm": protrusion}
            )
        verify_seated(label)
    finally:
        for obj in parts:
            obj.matrix_world = originals[obj.name]
        bpy.context.view_layer.update()
    return {
        "samples": rows,
        "scope": "Rigid nominal seating, not thread engagement, elastic preload or force qualification.",
    }
