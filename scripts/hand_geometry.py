"""Turns plans into meshes. No sizes, no names, no decisions.

Every solid here is one the plan asked for, at the position the plan gave,
in the order the plan listed. The three things this module knows are how to
call a primitive, how to run a Boolean, and that the plan's numbers are
millimetres.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix

from scripts.blender_mesh_primitives import add_cylinder, add_ellipsoid, boolean, cleanup_mesh
from scripts.hollow_hinge_geometry import create_box
from scripts.hollow_hinge_render import m
from src.core.planning.csg import Box, Cylinder, Ellipsoid, HollowBox, Operation, Solid
from src.core.planning.hand_plan import HandPlan
from src.core.planning.palm_plan import PalmPlan, RootPlan
from src.core.planning.phalanx_plan import FingerPlan, PhalanxPlan
from src.core.planning.station_plan import Basis


def realise(solid: Solid) -> bpy.types.Object:
    if isinstance(solid, Box):
        return create_box(solid.name, solid.size_mm, solid.center_mm)
    if isinstance(solid, Ellipsoid):
        return add_ellipsoid(solid.name, solid.size_mm, solid.center_mm)
    if isinstance(solid, Cylinder):
        if solid.segments is None:
            return add_cylinder(
                solid.name, solid.radius_mm, solid.height_mm, solid.center_mm, axis=solid.axis
            )
        return add_cylinder(
            solid.name,
            solid.radius_mm,
            solid.height_mm,
            solid.center_mm,
            axis=solid.axis,
            vertices=solid.segments,
        )
    outer = realise(solid.outer)
    boolean(outer, realise(solid.inner), "DIFFERENCE")
    outer.name = solid.name
    return outer


def apply(body: bpy.types.Object, operations: tuple[Operation, ...]) -> None:
    for operation in operations:
        boolean(body, realise(operation.solid), operation.mode)


def basis_matrix(basis: Basis) -> Matrix:
    """Columns are where the part's own x, y and z point in the world."""
    across, pad, axis = basis
    return Matrix(
        (
            (across[0], pad[0], axis[0], 0.0),
            (across[1], pad[1], axis[1], 0.0),
            (across[2], pad[2], axis[2], 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )


def translation(point_mm: tuple[float, float, float]) -> Matrix:
    return Matrix.Translation(tuple(m(value) for value in point_mm))


def build_part(plan: PhalanxPlan) -> bpy.types.Object:
    body = realise(plan.body)
    apply(body, plan.operations)
    cleanup_mesh(body)
    return body


def build_finger(plan: FingerPlan) -> list[bpy.types.Object]:
    """Each part built once; every unit that is a print of it shares the datablock.

    Sharing is the point: it is what makes a stack one part number instead of
    one per unit, and what the contract oracle counts when it asks for shared
    meshes.
    """
    masters = [build_part(part) for part in plan.parts]
    units: list[bpy.types.Object] = []
    for unit in plan.units:
        master = masters[unit.part_index]
        if master.name == unit.name:
            obj = master
        else:
            obj = master.copy()
            obj.data = master.data
            obj.name = unit.name
            bpy.context.collection.objects.link(obj)
        obj.location.z = m(unit.lift_mm)
        obj.rotation_euler.z = math.radians(unit.rotation_deg)
        units.append(obj)
    bpy.context.view_layer.update()
    return units


def _build_root(root: RootPlan) -> bpy.types.Object:
    stem = realise(root.stem)
    boolean(stem, realise(root.lug), "UNION")
    boolean(stem, realise(root.bore), "DIFFERENCE")
    stem.name = root.name
    # Bake the object's own offset into its mesh before placing it. `create_box`
    # keeps its centre height in the object transform, and placing overwrites
    # that transform: every knuckle once came out exactly the stem's half
    # height too low, watertight and contract-green.
    stem.data.transform(Matrix.Translation(stem.location))
    stem.location = (0.0, 0.0, 0.0)
    stem.matrix_world = translation(root.origin_mm) @ basis_matrix(root.basis)
    return stem


def build_palm(plan: PalmPlan) -> bpy.types.Object:
    plate = realise(plan.plate)
    apply(plate, plan.before_roots)
    roots = [_build_root(root) for root in plan.roots]
    bpy.context.view_layer.update()
    for root in roots:
        boolean(plate, root, "UNION")
    apply(plate, plan.after_roots)
    cleanup_mesh(plate)
    return plate


def assemble_hand(plan: HandPlan, palm: bpy.types.Object) -> list[bpy.types.Object]:
    """Palm plus one chain per station, each hung on the root that carries it."""
    placed: list[bpy.types.Object] = [palm]
    for station, chain in zip(plan.stations, plan.chains, strict=True):
        units = build_finger(chain)
        base = (
            translation(station.origin_mm)
            @ basis_matrix(station.basis)
            @ translation((0.0, 0.0, station.lift_mm))
        )
        for index, unit in enumerate(units, start=1):
            unit.name = plan.naming.hand_unit(station.label, index)
            unit.matrix_world = base @ unit.matrix_world
            placed.append(unit)
    bpy.context.view_layer.update()
    return placed
