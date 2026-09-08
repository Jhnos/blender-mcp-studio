"""Blender adapter for low-poly architecture, landscape and stateful props."""

from __future__ import annotations

import math

import bpy

from scripts.blender_mesh_primitives import material, move_to_collection
from scripts.model_universal_room import PALETTES

FAMILIES = {
    "architecture": ("window", "column", "stairs", "arch", "fence", "gate_closed", "gate_open"),
    "outdoors": ("tree", "bush", "rock", "path", "planter", "well"),
    "props": (
        "barrel",
        "bench",
        "bed",
        "lever_off",
        "lever_on",
        "plate_up",
        "plate_down",
        "crystal_off",
        "crystal_on",
    ),
}
LABELS = {
    "window": "窗牆",
    "column": "柱子",
    "stairs": "階梯",
    "arch": "拱門",
    "fence": "圍籬",
    "gate_closed": "閘門・關",
    "gate_open": "閘門・開",
    "tree": "樹",
    "bush": "灌木",
    "rock": "岩石",
    "path": "步道",
    "planter": "花槽",
    "well": "水井",
    "barrel": "木桶",
    "bench": "長椅",
    "bed": "床",
    "lever_off": "拉桿・關",
    "lever_on": "拉桿・開",
    "plate_up": "壓板・升",
    "plate_down": "壓板・壓下",
    "crystal_off": "水晶・暗",
    "crystal_on": "水晶・亮",
}
STATE_PAIRS = [
    ("gate_closed", "gate_open"),
    ("lever_off", "lever_on"),
    ("plate_up", "plate_down"),
    ("crystal_off", "crystal_on"),
]


def build_prop(kind: str, palette: str) -> bpy.types.Collection:
    group = bpy.data.collections.new(f"WK_{palette}_{kind}")
    bpy.context.scene.collection.children.link(group)
    colors = list(PALETTES[palette]) + [
        (0.12, 0.31, 0.09, 1) if palette == "wood-stone" else (0.05, 0.36, 0.32, 1),
        (0.62, 0.57, 0.40, 1),
        (0.07, 0.19, 0.25, 1),
        (0.14, 0.82, 0.68, 1),
    ]
    mats = [
        material(f"WK_{palette}_{i}", c, 0.45 if palette == "metal" else 0.05)
        for i, c in enumerate(colors)
    ]

    def finish(
        obj: bpy.types.Object, name: str, size: tuple[float, float, float], mat: int
    ) -> bpy.types.Object:
        obj.name = f"WK_{palette}_{kind}_{name}"
        obj.dimensions = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(mats[mat])
        move_to_collection(obj, group)
        return obj

    def box(
        name: str, loc: tuple[float, float, float], size: tuple[float, float, float], mat: int = 0
    ) -> bpy.types.Object:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = finish(bpy.context.object, name, size, mat)
        bevel = obj.modifiers.new("edge bevel", "BEVEL")
        bevel.width = 0.012
        bevel.segments = 1
        obj.modifiers.new("normals", "WEIGHTED_NORMAL")
        return obj

    def cylinder(
        name: str,
        loc: tuple[float, float, float],
        radius: float,
        depth: float,
        mat: int = 0,
        vertices: int = 10,
    ) -> bpy.types.Object:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=vertices, radius=radius, depth=depth, location=loc
        )
        obj = bpy.context.object
        obj.name = f"WK_{palette}_{kind}_{name}"
        obj.data.materials.append(mats[mat])
        move_to_collection(obj, group)
        return obj

    def ico(
        name: str, loc: tuple[float, float, float], size: tuple[float, float, float], mat: int = 4
    ) -> bpy.types.Object:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=loc)
        return finish(bpy.context.object, name, size, mat)

    if kind == "window":
        for x in (-0.43, 0.43):
            box("pier", (x, 0, 0.8), (0.14, 0.22, 1.6), 1)
        for z in (0.3, 1.42):
            box("lintel", (0, 0, z), (1, 0.22, 0.32), 1)
        for z in (0.48, 1.23):
            box("sill", (0, -0.025, z), (0.82, 0.3, 0.07), 2)
        box("mullion", (0, 0, 0.86), (0.065, 0.12, 0.73), 0)
        box("transom", (0, 0, 0.86), (0.78, 0.12, 0.06), 0)
    elif kind == "column":
        for z in (0.06, 1.48):
            box("base", (0, 0, z), (0.6, 0.6, 0.12), 1)
        cylinder("shaft", (0, 0, 0.76), 0.19, 1.35, 1, 8)
        for z in (0.18, 1.32):
            cylinder("collar", (0, 0, z), 0.25, 0.09, 2, 8)
    elif kind == "stairs":
        for i in range(4):
            h = 0.15 * (i + 1)
            box("step", (0, -0.375 + i * 0.25, h / 2), (1, 0.25, h), 1)
            box("edge", (0, -0.475 + i * 0.25, h), (1, 0.04, 0.025), 2)
    elif kind == "arch":
        for x in (-0.43, 0.43):
            box("pier", (x, 0, 0.54), (0.16, 0.27, 1.08), 1)
        # A segmented true aperture; it is not a solid rectangle with a painted opening.
        for i in range(9):
            angle = math.pi * i / 8
            o = box(
                "archstone",
                (0.43 * math.cos(angle), 0, 1.06 + 0.43 * math.sin(angle)),
                (0.19, 0.28, 0.20),
                1 if i != 4 else 2,
            )
            o.rotation_euler.y = angle - math.pi / 2
    elif kind in ("fence", "gate_closed", "gate_open"):
        for x in (-0.46, 0.46):
            box("post", (x, 0, 0.5), (0.08, 0.12, 1), 1)
            box("cap", (x, 0, 1), (0.13, 0.15, 0.05), 2)
        for z in (0.25, 0.76):
            o = box("rail", (0, 0, z), (0.9, 0.065, 0.09), 0)
            if kind == "gate_open":
                o.location = (-0.44, -0.44, z)
                o.rotation_euler.z = math.pi / 2
        for i in range(5):
            x = -0.32 + i * 0.16
            loc = (-0.44, -x - 0.44, 0.50) if kind == "gate_open" else (x, 0, 0.50)
            box("slat", loc, (0.05, 0.05, 0.8), 0)
        if kind != "fence":
            box(
                "latch",
                (-0.44, -0.77, 0.55) if kind == "gate_open" else (0.31, -0.06, 0.55),
                (0.12, 0.06, 0.08),
                2,
            )
    elif kind == "tree":
        cylinder("trunk", (0, 0, 0.56), 0.10, 1.1, 0, 7)
        ico("crown", (0, 0.02, 1.2), (0.95, 0.88, 1.1))
        ico("crown_left", (-0.24, -0.02, 1.05), (0.5, 0.63, 0.68))
    elif kind == "bush":
        for x, y, z in [(-0.23, 0, 0.27), (0.2, 0.05, 0.30), (0, -0.14, 0.37)]:
            ico("foliage", (x, y, z), (0.48, 0.47, 0.55))
    elif kind == "rock":
        ico("rock", (0, 0, 0.26), (0.85, 0.67, 0.53), 1)
        ico("chip", (0.28, -0.17, 0.10), (0.28, 0.25, 0.2), 1)
    elif kind == "path":
        for x, y, a in [
            (-0.23, -0.23, 0.03),
            (0.24, -0.22, -0.04),
            (-0.23, 0.24, -0.06),
            (0.24, 0.24, 0.06),
        ]:
            o = box("paver", (x, y, 0.035), (0.43, 0.43, 0.07), 1)
            o.rotation_euler.z = a
    elif kind == "planter":
        box("soil", (0, 0, 0.28), (0.72, 0.36, 0.12), 3)
        for y in (-0.23, 0.23):
            box("side", (0, y, 0.19), (0.9, 0.06, 0.38), 0)
        for x in (-0.42, 0.42):
            box("end", (x, 0, 0.19), (0.06, 0.5, 0.38), 0)
        for x in (-0.25, 0, 0.25):
            ico("plant", (x, 0, 0.46), (0.25, 0.29, 0.38), 4)
    elif kind == "well":
        cylinder("water", (0, 0, 0.15), 0.30, 0.02, 6, 12)
        for level in range(2):
            for i in range(10):
                a = i * 2 * math.pi / 10 + level * math.pi / 10
                o = box(
                    "stone",
                    (0.36 * math.cos(a), 0.36 * math.sin(a), 0.14 + level * 0.23),
                    (0.24, 0.14, 0.22),
                    1,
                )
                o.rotation_euler.z = a + math.pi / 2
        for x in (-0.43, 0.43):
            box("upright", (x, 0, 0.8), (0.075, 0.09, 1.35), 0)
        box("beam", (0, 0, 1.45), (0.98, 0.15, 0.12), 0)
        box("rope", (0, 0, 0.96), (0.025, 0.025, 0.9), 2)
    elif kind == "barrel":
        cylinder("body", (0, 0, 0.39), 0.30, 0.76, 0, 12)
        for z in (0.12, 0.64):
            cylinder("band", (0, 0, z), 0.313, 0.07, 2, 12)
        cylinder("lid", (0, 0, 0.79), 0.29, 0.035, 0, 12)
        box("bung", (0.1, 0, 0.82), (0.07, 0.07, 0.035), 2)
    elif kind == "bench":
        for y in (-0.16, 0, 0.16):
            box("seat", (0, y, 0.48), (0.96, 0.13, 0.07))
        for x in (-0.36, 0.36):
            box("foot", (x, 0, 0.24), (0.08, 0.4, 0.48), 1)
            box("support", (x, 0.21, 0.69), (0.055, 0.06, 0.64), 1)
        for z in (0.74, 0.94):
            box("back", (0, 0.21, z), (0.96, 0.06, 0.15))
    elif kind == "bed":
        box("frame", (0, 0, 0.25), (0.83, 1.35, 0.16), 0)
        box("mattress", (0, 0, 0.39), (0.78, 1.28, 0.17), 5)
        box("blanket", (0, -0.18, 0.49), (0.8, 0.8, 0.045), 2)
        box("pillow", (0, 0.43, 0.52), (0.53, 0.26, 0.14), 5)
        for x in (-0.33, 0.33):
            for y in (-0.55, 0.55):
                box("leg", (x, y, 0.15), (0.08, 0.08, 0.30), 1)
        box("head", (0, 0.65, 0.55), (0.88, 0.08, 0.62), 0)
    elif kind.startswith("lever_"):
        box("base", (0, 0, 0.10), (0.52, 0.46, 0.2), 1)
        box("pivot", (0, 0, 0.30), (0.28, 0.18, 0.22), 2)
        on = kind.endswith("on")
        o = box("handle", (0, -0.16 if on else 0.16, 0.54), (0.065, 0.065, 0.57), 0)
        o.rotation_euler.x = 0.6 if on else -0.6
        ico("grip", (0, -0.31 if on else 0.31, 0.77), (0.17, 0.17, 0.17), 7 if on else 2)
        box("indicator", (0, -0.22, 0.18), (0.16, 0.03, 0.09), 7 if on else 3)
    elif kind.startswith("plate_"):
        down = kind.endswith("down")
        box("base", (0, 0, 0.04), (0.82, 0.82, 0.08), 1)
        box("plate", (0, 0, 0.105 if down else 0.19), (0.67, 0.67, 0.08), 2)
        box("inlay", (0, 0, 0.15 if down else 0.235), (0.20, 0.20, 0.014), 7 if down else 3)
    elif kind.startswith("crystal_"):
        cylinder("base", (0, 0, 0.09), 0.30, 0.18, 1, 6)
        bpy.ops.mesh.primitive_cone_add(
            vertices=6, radius1=0.22, radius2=0, depth=0.73, location=(0, 0, 0.57)
        )
        finish(bpy.context.object, "gem", (0.44, 0.40, 0.73), 7 if kind.endswith("on") else 6)
        for x in (-0.24, 0.24):
            ico("shard", (x, -0.08, 0.29), (0.13, 0.14, 0.32), 7 if kind.endswith("on") else 6)
    else:
        raise ValueError(kind)
    return group
