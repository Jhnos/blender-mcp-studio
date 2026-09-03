"""Low-level Blender mesh primitives for hollow side-hinge generation."""

from __future__ import annotations

import math

import bpy


def _m(value_mm: float) -> float:
    return value_mm / 1000.0


def create_box(
    name: str,
    dimensions_mm: tuple[float, float, float],
    location_mm: tuple[float, float, float],
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=tuple(_m(value) for value in location_mm))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple(_m(value) for value in dimensions_mm)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.select_set(False)
    return obj


def create_clipped_lug(
    name: str,
    axis: str,
    side_center_mm: float,
    joint_z_mm: float,
    thickness_mm: float,
    lug_diameter_mm: float,
    joint_gap_mm: float,
    running_clearance_mm: float,
    keep_upper_arc: bool,
) -> bpy.types.Object:
    """Create a watertight D-profile lug without a topology-damaging clip Boolean."""

    radius = lug_diameter_mm / 2.0
    cap_from_center = joint_gap_mm / 2.0 - running_clearance_mm
    cap_angle = math.asin(cap_from_center / radius)
    if keep_upper_arc:
        start_angle = -cap_angle
        end_angle = math.pi + cap_angle
    else:
        start_angle = math.pi - cap_angle
        end_angle = 2.0 * math.pi + cap_angle
    outline = [
        (
            radius * math.cos(start_angle + (end_angle - start_angle) * index / 40.0),
            radius * math.sin(start_angle + (end_angle - start_angle) * index / 40.0),
        )
        for index in range(41)
    ]
    vertices: list[tuple[float, float, float]] = []
    for axial in (-thickness_mm / 2.0, thickness_mm / 2.0):
        for radial, z_offset in outline:
            if axis == "X":
                vertices.append(
                    (
                        _m(side_center_mm + axial),
                        _m(radial),
                        _m(joint_z_mm + z_offset),
                    )
                )
            else:
                vertices.append(
                    (
                        _m(radial),
                        _m(side_center_mm + axial),
                        _m(joint_z_mm + z_offset),
                    )
                )
    count = len(outline)
    faces: list[tuple[int, ...]] = [
        tuple(reversed(range(count))),
        tuple(range(count, 2 * count)),
    ]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, next_index + count, index + count))
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    lug = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(lug)
    return lug
