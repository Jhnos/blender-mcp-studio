"""Reusable electrode arm module: build local parts from immutable head configuration."""

import bpy
from mathutils import Matrix

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean, loft_rings
from scripts.lab_station_arm import finish_arm
from scripts.lab_station_clamp import compact_probe_head
from scripts.lab_station_joints import hand_knob_hardware, retained_pivot
from scripts.model_lab_simple import link
from src.core.domain.lab_station import ELECTRODE_ASSEMBLIES, ElectrodeArmSpec, ProbeHeadSpec


def bake(obj: bpy.types.Object, side: int) -> None:
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    if side > 0:
        obj.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    finish_arm(obj)


def build(label: str, head_spec: ProbeHeadSpec | None = None) -> None:
    head_spec = head_spec or ELECTRODE_ASSEMBLIES["baseline"].head(label)
    side = -1 if label == "capillary" else 1
    prefix = "S_" + label + "_"
    mat = bpy.data.objects[prefix + "upper"].data.materials[0]
    for suffix, x in (("upper", 4.2), ("lower", -4.2)):
        bpy.data.objects.remove(bpy.data.objects[prefix + suffix], do_unlink=True)
        obj = link(prefix + suffix, x, mat, radius_mm=11)
        if suffix == "upper":
            boolean(obj, add_cylinder("E_TOOL", 11, 8, (x, 0, 126), "X"), "UNION")
            finish_arm(obj)
            boolean(obj, add_cylinder("E_TOOL", 2.7, 40, (x, 0, 126), "X"), "DIFFERENCE")
            finish_arm(obj)
        if suffix == "upper":
            for z in (0, 150):
                boolean(
                    obj, add_cylinder("E_TOOL", 4.8, 5, (6.6, 0, z), "X", vertices=6), "DIFFERENCE"
                )
                finish_arm(obj)
        bake(obj, side)
    obj = link(prefix + "follower", -4.2, mat, radius_mm=11)
    bake(obj, side)
    spec = ElectrodeArmSpec()
    vertices = ((0, 0), (0, -24), (spec.platform_offset_mm, 0))
    obj = loft_rings(prefix + "platform", [[(x, y, z) for y, z in vertices] for x in (0.2, 8.2)])
    assign(obj, mat)
    for y, z in vertices:
        boolean(
            obj, add_cylinder("E_TOOL", spec.platform_boss_radius_mm, 8, (4.2, y, z), "X"), "UNION"
        )
        finish_arm(obj)
    for y, z in vertices:
        boolean(obj, add_cylinder("E_TOOL", 2.7, 30, (4.2, y, z), "X"), "DIFFERENCE")
        finish_arm(obj)
    boolean(
        obj,
        add_cylinder("E_TOOL", 4.8, 5, (6.6, spec.platform_offset_mm, 0), "X", vertices=6),
        "DIFFERENCE",
    )
    bake(obj, side)
    bpy.data.objects.remove(bpy.data.objects[prefix + "head"], do_unlink=True)
    for obj in compact_probe_head(label, mat, head_spec):
        bake(obj, side)
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix + "probe_"):
            shift = head_spec.probe_shift_mm(side)
            obj.data.transform(
                Matrix.Translation(
                    ((side * 24.2 + shift[0]) / 1000, shift[1] / 1000, shift[2] / 1000)
                )
            )
    for joint in ("proximal", "distal", "carrier"):
        for obj in retained_pivot(
            prefix + joint + "_", mat, axial_float_mm=2 if joint == "carrier" else 0
        ):
            obj.matrix_world = (
                Matrix.Translation((0.0084, 0, 0))
                @ Matrix.Diagonal((-1, 1, 1, 1))
                @ obj.matrix_world
            )
            bake(obj, side)
    for joint in ("shoulder", "elbow", "tip"):
        for suffix in ("bolt", "nut"):
            bpy.data.objects.remove(bpy.data.objects[prefix + joint + "_" + suffix], do_unlink=True)
        for obj in hand_knob_hardware(
            prefix + joint + "_",
            mat,
            bpy.data.materials["S_metal"],
            8.5 if joint == "tip" else 12.5,
            depth_mm=7.5 if joint == "tip" else 10,
        ):
            bake(obj, side)
