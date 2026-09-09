"""Low-poly rigid-weight character meshes and named, editable armature actions."""

from __future__ import annotations

import math

import bpy

from scripts.blender_mesh_primitives import material, move_to_collection
from scripts.living_asset_contract import CLIPS, ROLES


def build_actor(role: str) -> tuple[bpy.types.Object, bpy.types.Collection]:
    group = bpy.data.collections.new("LW_" + role)
    bpy.context.scene.collection.children.link(group)
    arm = bpy.data.armatures.new("LW_" + role + "_skeleton")
    rig = bpy.data.objects.new("LW_" + role + "_rig", arm)
    group.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    points = {
        "root": ((0, 0, 0), (0, 0, 0.2), None),
        "spine": ((0, 0, 0.73), (0, 0, 1.21), "root"),
        "head": ((0, 0, 1.24), (0, 0, 1.68), "spine"),
        "arm.L": ((0.32, 0, 1.15), (0.36, 0, 0.72), "spine"),
        "arm.R": ((-0.32, 0, 1.15), (-0.36, 0, 0.72), "spine"),
        "leg.L": ((0.15, 0, 0.75), (0.15, 0, 0.14), "root"),
        "leg.R": ((-0.15, 0, 0.75), (-0.15, 0, 0.14), "root"),
    }
    for name, (head, tail, parent) in points.items():
        bone = arm.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        if parent:
            bone.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    rig.show_in_front = True
    colors = {
        "skin": ROLES[role]["skin"],
        "coat": ROLES[role]["coat"],
        "trim": (0.80, 0.51, 0.13, 1),
        "boots": (0.07, 0.035, 0.024, 1),
        "pants": (0.08, 0.12, 0.15, 1),
        "hair": (0.075, 0.035, 0.018, 1),
        "eyes": (0.015, 0.021, 0.023, 1),
        "paper": (0.80, 0.75, 0.54, 1),
        "steel": (0.31, 0.38, 0.46, 1),
        "leather": (0.30, 0.13, 0.055, 1),
    }
    mats = {k: material("LW_" + role + "_" + k, v) for k, v in colors.items()}

    def part(
        name: str,
        loc: tuple[float, float, float],
        scale: tuple[float, float, float],
        mat: str,
        bone: str = "spine",
        sphere: bool = False,
    ) -> bpy.types.Object:
        if sphere:
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=loc)
        else:
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.object
        obj.name = f"LW_{role}_{name}"
        obj.scale = scale
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)
        obj.data.materials.append(mats[mat])
        if not sphere:
            bevel = obj.modifiers.new("Low-poly soft edges", "BEVEL")
            bevel.width, bevel.segments = 0.028, 1
        weights = obj.vertex_groups.new(name=bone)
        weights.add(list(range(len(obj.data.vertices))), 1, "REPLACE")
        modifier = obj.modifiers.new("Shared skeleton", "ARMATURE")
        modifier.object = rig
        obj.parent = rig
        move_to_collection(obj, group)
        return obj

    part("tunic", (0, 0, 1.00), (0.52, 0.32, 0.49), "coat")
    part("belt", (0, -0.015, 0.82), (0.54, 0.34, 0.065), "boots")
    part("buckle", (0, -0.195, 0.83), (0.085, 0.035, 0.075), "trim")
    part("collar", (0, -0.045, 1.22), (0.33, 0.34, 0.10), "trim")
    part("head", (0, -0.012, 1.46), (0.265, 0.24, 0.265), "skin", "head", True)
    part("hair", (0, 0.016, 1.61), (0.275, 0.245, 0.145), "hair", "head", True)
    for side, x in (("L", 0.15), ("R", -0.15)):
        part("trouser." + side, (x, 0, 0.48), (0.205, 0.24, 0.52), "pants", "leg." + side)
        part("boot." + side, (x, -0.08, 0.12), (0.235, 0.38, 0.23), "boots", "leg." + side)
        sx = 0.345 if side == "L" else -0.345
        part("sleeve." + side, (sx, 0, 0.99), (0.20, 0.27, 0.37), "coat", "arm." + side)
        part("hand." + side, (sx, -0.01, 0.745), (0.10, 0.11, 0.13), "skin", "arm." + side, True)
        part("eye." + side, (x * 0.60, -0.232, 1.475), (0.031, 0.024, 0.041), "eyes", "head", True)
    part("nose", (0, -0.254, 1.43), (0.045, 0.05, 0.047), "skin", "head", True)
    if role == "traveler":
        part("rucksack", (0, 0.245, 1.00), (0.38, 0.22, 0.42), "boots")
        part("bedroll", (0, 0.24, 1.25), (0.46, 0.19, 0.14), "paper")
        part("scarf", (0.08, -0.195, 1.075), (0.105, 0.055, 0.25), "trim")
    elif role == "guide":
        part("shoulder-cape", (0, 0.08, 1.12), (0.67, 0.38, 0.20), "trim")
        part("cap", (0, 0.01, 1.745), (0.35, 0.31, 0.075), "coat", "head", True)
        part("hat-brim", (0, -0.09, 1.65), (0.66, 0.48, 0.055), "coat", "head")
        part("scroll-case", (0.265, 0.05, 0.79), (0.14, 0.18, 0.39), "paper")
    elif role == "guard":
        part("breastplate", (0, -0.19, 1.04), (0.49, 0.08, 0.34), "steel")
        part("helmet", (0, 0.025, 1.66), (0.30, 0.26, 0.12), "steel", "head", True)
        part("crest", (0, 0.06, 1.785), (0.07, 0.30, 0.09), "trim", "head")
        part("shield", (0.43, -0.10, 0.90), (0.25, 0.12, 0.44), "steel", "arm.L")
        part("shield-emblem", (0.43, -0.18, 0.93), (0.08, 0.025, 0.22), "trim", "arm.L")
    elif role == "artisan":
        part("apron", (0, -0.195, 0.91), (0.40, 0.065, 0.54), "leather")
        part("apron-pocket", (0.05, -0.24, 0.87), (0.22, 0.03, 0.15), "trim")
        part("headband", (0, -0.04, 1.61), (0.51, 0.42, 0.065), "trim", "head")
        part("hammer-handle", (-0.37, -0.075, 0.82), (0.055, 0.07, 0.42), "leather", "arm.R")
        part("hammer-head", (-0.37, -0.075, 1.055), (0.30, 0.12, 0.14), "steel", "arm.R")
    for clip, (count, _) in CLIPS.items():
        rig.animation_data_create()
        action = bpy.data.actions.new(f"LW_{role}_{clip}")
        action.use_fake_user = True
        rig.animation_data.action = action
        for frame in range(1, count + 1):
            phase = 2 * math.pi * (frame - 1) / count
            for bone in rig.pose.bones:
                bone.rotation_mode = "XYZ"
                bone.rotation_euler = (0, 0, 0)
            if clip == "walk":
                for side, sign in (("L", 1), ("R", -1)):
                    rig.pose.bones["leg." + side].rotation_euler.x = sign * 0.38 * math.sin(phase)
                    rig.pose.bones["arm." + side].rotation_euler.x = -sign * 0.40 * math.sin(phase)
            elif clip == "interact":
                rig.pose.bones["arm.R"].rotation_euler.z = -0.65 - 0.20 * math.sin(phase)
                rig.pose.bones["arm.R"].rotation_euler.x = 0.55
                rig.pose.bones["head"].rotation_euler.x = 0.05 * math.sin(phase)
            else:
                rig.pose.bones["head"].rotation_euler.z = 0.035 if frame == 1 else -0.035
            for bone in rig.pose.bones:
                bone.keyframe_insert("rotation_euler", frame=frame)
    rig.animation_data.action = bpy.data.actions[f"LW_{role}_idle"]
    return rig, group
