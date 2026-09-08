"""Pins, bearings and route guides for the hollow side hinge chain.

Split from the generator at its line budget, the way the biaxial and V3
lines keep hardware and presentation beside the body builder. Materials are
handed in: creating them is the generator's business, and a module that made
its own would be a second palette to drift.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import bpy

from scripts.blender_mesh_primitives import add_cylinder, assign, move_to_collection
from scripts.hollow_hinge_render import m
from src.core.domain.hollow_side_hinge import HollowSideHingeSpec


@dataclass(frozen=True, slots=True)
class HardwareMaterials:
    bearing: bpy.types.Material
    x_pin: bpy.types.Material
    y_pin: bpy.types.Material
    tendon: bpy.types.Material
    cable: bpy.types.Material


def create_bearing(
    name: str,
    joint_z_mm: float,
    axis: str,
    side: float,
    hardware: bpy.types.Collection,
    spec: HollowSideHingeSpec,
    materials: HardwareMaterials,
) -> None:
    face_offset = spec.side_female_center_mm + spec.female_lug_thickness_mm / 2.0 + 0.2
    location = (
        (side * face_offset, 0.0, joint_z_mm)
        if axis == "X"
        else (0.0, side * face_offset, joint_z_mm)
    )
    rotation = (0.0, math.pi / 2.0, 0.0) if axis == "X" else (math.pi / 2.0, 0.0, 0.0)
    outer_radius = spec.bearing_seat_diameter_mm / 2.0
    inner_radius = spec.pin_diameter_mm / 2.0
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
    assign(bearing, materials.bearing)
    bearing.hide_viewport = True


def create_joint_hardware(
    joint: int,
    hardware: bpy.types.Collection,
    spec: HollowSideHingeSpec,
    materials: HardwareMaterials,
) -> None:
    joint_z = (joint - 1) * spec.unit_pitch_mm + spec.joint_center_offset_mm
    axis = "X" if joint % 2 else "Y"
    inner_edge = spec.center_channel_diameter_mm / 2.0 + spec.minimum_running_clearance_mm
    outer_edge = spec.side_female_center_mm + spec.female_lug_thickness_mm / 2.0 + 0.4
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
            spec.pin_diameter_mm / 2.0,
            segment_length,
            location,
            axis=axis,
        )
        move_to_collection(pin, hardware)
        assign(pin, materials.x_pin if axis == "X" else materials.y_pin)
        pin.hide_viewport = True
        create_bearing(
            f"HH_BEARING_J{joint}_{'POS' if side > 0 else 'NEG'}",
            joint_z,
            axis,
            side,
            hardware,
            spec,
            materials,
        )


def create_route_guides(
    z_min_mm: float,
    z_max_mm: float,
    hardware: bpy.types.Collection,
    spec: HollowSideHingeSpec,
    materials: HardwareMaterials,
) -> None:
    depth = z_max_mm - z_min_mm
    center_z = (z_min_mm + z_max_mm) / 2.0
    cable = add_cylinder("HH_SENSOR_CABLE_ROUTE", 1.55, depth, (0.0, 0.0, center_z))
    move_to_collection(cable, hardware)
    assign(cable, materials.cable)
    cable.show_in_front = True
    cable.hide_viewport = True
    for index, (x_mm, y_mm) in enumerate(spec.tendon_positions_mm, start=1):
        tendon = add_cylinder(f"HH_TENDON_{index}", 0.4, depth, (x_mm, y_mm, center_z))
        move_to_collection(tendon, hardware)
        assign(tendon, materials.tendon)
        tendon.show_in_front = True
        tendon.hide_viewport = True
