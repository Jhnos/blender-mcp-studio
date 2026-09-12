"""Rotary base retention and chassis load path; nominal hardware, not load qualification."""

import bpy
from mathutils import Vector

from scripts.blender_mesh_primitives import add_cylinder, assign, boolean
from scripts.lab_station_arm import finish_arm
from scripts.lab_station_joints import block
from scripts.lab_station_motion_check import tree
from src.core.domain.lab_station import LabStationSpec


def verify_base_mounts() -> list[dict[str, object]]:
    """Check real bores, neutral clearance and displaced retaining-stop contact."""
    chassis = bpy.data.objects["LS_FIT_chassis"]
    lid = bpy.data.objects["LS_FIT_lid"]
    saved_lid = lid.matrix_world.copy()
    try:
        # Separate the intentional rim contact by 0.01 mm; a penetrating tower
        # still crosses the lid and must fail rather than hide behind that contact.
        lid.location.z += 0.00001
        bpy.context.view_layer.update()
        if tree(chassis).overlap(tree(lid)):
            raise ValueError("Base support penetrates lid")
    finally:
        lid.matrix_world = saved_lid
        bpy.context.view_layer.update()
    rows: list[dict[str, object]] = []
    for label, side in (("capillary", -1), ("pH_temp", 1)):
        rotor = bpy.data.objects[f"LR_{label}_mount_envelope"]
        if not rotor.get("yaw_spigot"):
            raise ValueError("Base is not retained to chassis: " + label)
        parts = {}
        for suffix in ("sleeve", "bolt", "washer_lower", "washer_upper", "nut"):
            name = f"LR_BASE_{label}_{suffix}"
            if name not in bpy.data.objects:
                raise ValueError("Base retention part missing: " + name)
            parts[suffix] = bpy.data.objects[name]
        x, y, _ = LabStationSpec().arm_points(side)[0]
        for member in (chassis, lid, rotor):
            inverse = member.matrix_world.inverted()
            direction = (inverse.to_3x3() @ Vector((0, 0, 1))).normalized()
            for dx in (0, 9):
                start = inverse @ Vector(((x + dx) / 1000, y / 1000, -0.02))
                if member.ray_cast(start, direction)[0] != bool(dx):
                    raise ValueError("Base coaxial material missing: " + member.name)
        # Coplanar bearing faces are intentional; radial/axial stop probes below
        # distinguish a retained interface from a merely adjacent set of meshes.
        for suffix, part in parts.items():
            for member in (chassis, lid, rotor):
                if tree(part).overlap(tree(member)):
                    raise ValueError(
                        f"Base hardware interference: {label}, {suffix}, {member.name}"
                    )
        probes = (
            (rotor, parts["washer_upper"], (0, 0, 0.0002)),
            (parts["bolt"], parts["washer_lower"], (0, 0, 0.0002)),
            (rotor, parts["sleeve"], (0.0003, 0, 0)),
            (parts["washer_lower"], chassis, (0, 0, 0.0001)),
            (parts["washer_upper"], parts["nut"], (0, 0, 0.0001)),
        )
        for moving, stop, offset in probes:
            saved = moving.matrix_world.copy()
            try:
                shifted = saved.copy()
                shifted.translation += Vector(offset)
                moving.matrix_world = shifted
                bpy.context.view_layer.update()
                if not tree(moving).overlap(tree(stop)):
                    raise ValueError(f"Base retaining stop absent: {label}, {stop.name}")
            finally:
                moving.matrix_world = saved
                bpy.context.view_layer.update()
        rows.append({"base": label, "coaxial_material": True, "retaining_stop_probes": 5})
    obstacles = [o for o in bpy.data.objects if o.type == "MESH" and "UNCONFIRMED" in o.name]
    for obstacle in obstacles:
        if tree(chassis).overlap(tree(obstacle)):
            raise ValueError("Base tower intersects component envelope: " + obstacle.name)
    return rows


def build_base_mounts(metal: bpy.types.Material) -> None:
    """Integrate floor-supported sleeves and through-bolt retention under each yaw foot."""
    chassis = bpy.data.objects["LS_FIT_chassis"]
    lid = bpy.data.objects["LS_FIT_lid"]
    mat = chassis.data.materials[0]
    for label, side in (("capillary", -1), ("pH_temp", 1)):
        x, y, _ = LabStationSpec().arm_points(side)[0]
        rotor = bpy.data.objects[f"LR_{label}_mount_envelope"]
        boolean(rotor, add_cylinder("LR_TOOL_spigot", 6, 20.4, (x, y, 70)), "UNION")
        boolean(rotor, add_cylinder("LR_TOOL_bore", 2.7, 40, (x, y, 75)), "DIFFERENCE")
        boolean(chassis, add_cylinder("LR_TOOL_tower", 11.5, 70.1, (x, y, 40.85)), "UNION")
        boolean(
            chassis, block("LR_TOOL_gusset", (17, 8, 70.1), (side * 105.5, y, 40.85), mat), "UNION"
        )
        boolean(chassis, add_cylinder("LR_TOOL_bore", 2.7, 90, (x, y, 40)), "DIFFERENCE")
        boolean(chassis, add_cylinder("LR_TOOL_seat", 8.1, 18, (x, y, 68.5)), "DIFFERENCE")
        boolean(lid, add_cylinder("LR_TOOL_lid", 6.2, 10, (x, y, 78)), "DIFFERENCE")
        prefix = f"LR_BASE_{label}_"
        sleeve = add_cylinder(prefix + "sleeve", 8, 16, (x, y, 68))
        boolean(sleeve, add_cylinder("LR_TOOL_inner", 6.1, 18, (x, y, 68)), "DIFFERENCE")
        bolt = add_cylinder(prefix + "bolt", 2.5, 90, (x, y, 44.17))
        boolean(bolt, add_cylinder("LR_TOOL_head", 4.25, 5.2, (x, y, -3.43)), "UNION")
        boolean(
            bolt, add_cylinder("LR_TOOL_hex", 2.3094, 3.6, (x, y, -4.43), vertices=6), "DIFFERENCE"
        )
        nut = add_cylinder(prefix + "nut", 4.6, 2.4, (x, y, 87.04), vertices=6)
        boolean(nut, add_cylinder("LR_TOOL_thread", 2.6, 4, (x, y, 87.04)), "DIFFERENCE")
        parts = [sleeve, bolt, nut]
        for suffix, z in (("lower", -0.42), ("upper", 85.42)):
            washer = add_cylinder(prefix + "washer_" + suffix, 5, 0.8, (x, y, z))
            boolean(washer, add_cylinder("LR_TOOL_washer", 2.65, 2, (x, y, z)), "DIFFERENCE")
            parts.append(washer)
        for part in parts:
            assign(part, metal)
            finish_arm(part)
        finish_arm(rotor)
        rotor["yaw_spigot"] = True
    for x in (-103, 103):
        for y in (-63, 63):
            boolean(chassis, add_cylinder("LR_TOOL_foot", 7, 8.2, (x, y, -3.9)), "UNION")
    bpy.data.objects["LS_REF_pump_envelope_UNCONFIRMED"].location.x += 0.010
    finish_arm(chassis)
    finish_arm(lid)
    bpy.context.view_layer.update()
