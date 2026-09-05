"""Reusable view helpers plus close-up and printed-pin layout for V5."""

from __future__ import annotations

import math
from pathlib import Path

import bpy

from scripts.blender_artifact_export import export_stl_mm
from scripts.blender_mesh_primitives import assign, material
from scripts.hollow_hinge_render import (
    add_text,
    face_camera,
    look_at,
    m,
    render_views,
    setup_render,
)
from src.core.domain.inset_hinge import InsetHingeSpec


def present(
    output: Path,
    spec: InsetHingeSpec,
    parts: list[bpy.types.Object],
    hardware: bpy.types.Collection,
    pin: bpy.types.Object,
    pins: list[bpy.types.Object],
    layout: list[bpy.types.Object],
    bent: list[bpy.types.Object],
    cable: bpy.types.Object,
    bent_target: tuple[float, float, float],
) -> None:
    floor = material("HH_V5_FLOOR", (0.018, 0.028, 0.045, 1))
    white = material("HH_V5_TEXT", (0.95, 0.98, 1, 1))
    camera, support = setup_render(spec, floor, assign)
    labels = [
        add_text(
            "HH_TITLE", "V5 / INSET HINGE / 9 BODIES + 16 PRINTED PINS", (0, -8, 187), white, 3
        ),
        add_text(
            "HH_CAPTION",
            "34 mm DISC / 10 mm SENSOR CHANNEL / 20 mm PITCH",
            (0, -25, -12),
            white,
            2.5,
        ),
    ]
    render_views(output, camera, parts, hardware, labels, layout, bent, cable, bent_target)
    pin.hide_render = True  # The shared renderer restores the entire hardware collection.
    saved_camera = (camera.location.copy(), camera.rotation_euler.copy(), camera.data.ortho_scale)
    scene = bpy.context.scene
    scene.display.shading.show_shadows = False
    saved_resolution = (scene.render.resolution_x, scene.render.resolution_y)
    for obj in [*parts, *pins, *labels]:
        obj.hide_render = True
    # Two opposite body views and two head-down pins constitute a printable fit coupon.
    detail = []
    for i, x in enumerate((-22, 22), 1):
        obj = parts[0].copy()
        obj.name = f"HH_DETAIL_BODY_{i}"
        bpy.context.scene.collection.objects.link(obj)
        obj.rotation_euler.x = math.pi if i == 2 else 0
        obj.location = (m(x), 0, m(14.8))
        obj.hide_render = False
        obj.hide_viewport = True
        detail.append(obj)
    for i, x in enumerate((-6, 6), 1):
        obj = pin.copy()
        obj.name = f"HH_LAYOUT_PIN_{i}"
        bpy.context.scene.collection.objects.link(obj)
        obj.location = (m(x), m(-25), 0)
        obj.hide_render = False
        obj.hide_viewport = True
        detail.append(obj)
    export_stl_mm(detail, output / "inset_hinge_fit_coupon_mm.stl")
    camera.location = (m(60), m(-120), m(92))
    camera.data.ortho_scale = m(100)
    look_at(camera, (0, 0, 12))
    scene.render.resolution_x, scene.render.resolution_y = 1500, 1100
    detail_labels = [
        add_text(
            "HH_DETAIL_TITLE",
            "ONE BODY TYPE / FRONT + BACK / PRINTED SIDE PINS",
            (0, 0, 43),
            white,
            2.5,
        ),
        add_text(
            "HH_DETAIL_NOTE",
            "ROOT RAMPS <45 DEG / PROTOTYPE - RETENTION REQUIRED",
            (0, -36, -2),
            white,
            1.8,
        ),
    ]
    for label in detail_labels:
        face_camera(label, camera)
    scene.render.filepath = str(output / "inset_hinge_detail.png")
    bpy.ops.render.render(write_still=True)
    for obj in [*detail, *detail_labels]:
        obj.hide_render = True
    # Orthographic top view exposes the actual disc footprint and four tendon holes.
    parts[0].hide_render = False
    camera.location = (0, 0, m(150))
    look_at(camera, (0, 0, 0))
    camera.data.ortho_scale = m(41)
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.filepath = str(output / "inset_hinge_top.png")
    bpy.ops.render.render(write_still=True)
    for obj in [*parts, *pins, *labels]:
        obj.hide_render = False
    camera.location, camera.rotation_euler, camera.data.ortho_scale = saved_camera
    scene.render.resolution_x, scene.render.resolution_y = saved_resolution
    scene.render.filepath = str(output / "hollow_side_hinge_assembly.png")
    for obj in support:
        obj.hide_viewport = True
