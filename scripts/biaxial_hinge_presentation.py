"""V6 pin workflows: distinct manufacturing layouts and diagnostic close-up views."""

import math

import bpy
from mathutils import Matrix, Vector

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


def duplicate(source, name, matrix):
    obj = source.copy()
    obj.data = source.data
    obj.name = name
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = matrix
    obj.hide_render = obj.hide_viewport = True
    return obj


def create_coupons(output, spec, parts, pins, masters):
    captive, removable, clip = masters
    frame = Matrix.Rotation(math.pi / 2, 4, "Y") @ Matrix.Translation(
        (0, 0, m(-spec.joint_center_offset_mm))
    )
    sources = [*parts[:2], *pins[:2]]
    pip = [
        duplicate(obj, f"HH_PIP_PART_{i}", frame @ obj.matrix_world)
        for i, obj in enumerate(sources, 1)
    ]
    bed = -min((obj.matrix_world @ v.co).z for obj in pip for v in obj.data.vertices)
    for obj in pip:
        obj.location.z += bed
    bpy.context.view_layer.update()
    export_stl_mm(pip, output / "print_in_place_2body_double_head_mm.stl")

    split = [
        duplicate(obj, f"HH_SPLIT_BODY_{i}", obj.matrix_world.copy())
        for i, obj in enumerate(parts[:2], 1)
    ]
    for i, source in enumerate(pins[:2], 1):
        split.append(duplicate(removable, f"HH_SPLIT_HW_{i}", source.matrix_world.copy()))
        side = -1 if i == 1 else 1
        clip_outer = (
            spec.retainer_inner_radius_mm + (spec.groove_length_mm + spec.clip_thickness_mm) / 2
        )
        orientation = Vector((-side, 0, 0)).to_track_quat("Z", "Y").to_matrix().to_4x4()
        matrix = (
            Matrix.Translation((m(side * clip_outer), 0, m(spec.joint_center_offset_mm)))
            @ orientation
        )
        split.append(duplicate(clip, f"HH_SPLIT_HW_{i + 2}", matrix))
    bpy.context.view_layer.update()

    layout = []
    for i, x in enumerate((-23, 23), 1):
        matrix = Matrix.Translation(
            (m(x), 0, m(spec.joint_center_offset_mm + spec.lug_outer_diameter_mm / 2))
        )
        if i == 2:
            matrix @= Matrix.Rotation(math.pi, 4, "X")
        layout.append(duplicate(parts[0], f"HH_COUPON_BODY_{i}", matrix))
    for i, x in enumerate((-6, 6), 1):
        layout.append(
            duplicate(removable, f"HH_COUPON_PIN_{i}", Matrix.Translation((m(x), m(-27), 0)))
        )
    for i, x in enumerate((-16, 16), 1):
        layout.append(duplicate(clip, f"HH_COUPON_CLIP_{i}", Matrix.Translation((m(x), m(-27), 0))))
    bpy.context.view_layer.update()
    export_stl_mm(layout, output / "separate_parts_2body_2pin_2clip_mm.stl")
    return pip, split, layout


def capture(output, name, camera, objects, location, target, scale, title, white):
    scene = bpy.context.scene
    for obj in objects:
        obj.hide_render = False
    camera.location = tuple(m(v) for v in location)
    camera.data.ortho_scale = m(scale)
    look_at(camera, target)
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1100
    up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
    label_position = Vector(target) + up * (scale * 1100 / 1400 * 0.43)
    label = add_text("HH_VIEW_LABEL", title, tuple(label_position), white, scale * 0.018)
    face_camera(label, camera)
    scene.render.filepath = str(output / name)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(label, do_unlink=True)
    for obj in objects:
        obj.hide_render = True


def present_biaxial(output, spec, parts, pins, hardware, masters, layout, bent, cable, target):
    floor = material("HH_V6_FLOOR", (0.018, 0.028, 0.045, 1))
    white = material("HH_V6_TEXT", (0.95, 0.98, 1, 1))
    camera, support = setup_render(spec, floor, assign)
    label = add_text(
        "HH_V6_TITLE", "V6 / FOUR-WAY ROOTS / CAPTIVE SIDE PINS", (0, -8, 174), white, 3
    )
    render_views(output, camera, parts, hardware, [label], layout, bent, cable, target)
    for obj in masters:
        obj.hide_render = True
    pip, split, coupon = create_coupons(output, spec, parts, pins, masters)
    scene = bpy.context.scene
    saved = (
        camera.location.copy(),
        camera.rotation_euler.copy(),
        camera.data.ortho_scale,
        scene.render.resolution_x,
        scene.render.resolution_y,
    )
    for obj in [*parts, *pins, label]:
        obj.hide_render = True
    scene.display.shading.show_shadows = False
    capture(
        output,
        "biaxial_detail.png",
        camera,
        coupon,
        (60, -120, 92),
        (0, 0, 12),
        106,
        "SEPARATE PARTS / 2 BODIES + 2 GROOVED PINS + 2 C CLIPS",
        white,
    )
    capture(
        output,
        "biaxial_side.png",
        camera,
        [parts[0]],
        (0, -100, 32),
        (0, 0, 1),
        53,
        "SIDE ROOTS RISE TO THE EAR / 36 mm DISC",
        white,
    )
    pip_views = []
    for i, obj in enumerate(pip):
        pip_views.append(
            duplicate(
                obj,
                f"HH_PIP_VIEW_A_{i}",
                Matrix.Translation((m(-32), 0, 0)) @ obj.matrix_world,
            )
        )
        reverse = (
            Matrix.Translation((m(32), 0, m(36)))
            @ Matrix.Rotation(math.pi, 4, "X")
            @ Matrix.Rotation(math.radians(35), 4, "Z")
        )
        pip_views.append(duplicate(obj, f"HH_PIP_VIEW_B_{i}", reverse @ obj.matrix_world))
    capture(
        output,
        "print_in_place.png",
        camera,
        pip_views,
        (80, -160, 120),
        (0, 0, 18),
        148,
        "PIP / TOP-FRONT + BOTTOM-BACK / TWO CAPTIVE PINS",
        white,
    )

    split_views = [
        duplicate(
            obj,
            f"HH_VIEW_SPLIT_ASSEMBLED_{i}",
            Matrix.Translation((m(-30), 0, 0)) @ obj.matrix_world,
        )
        for i, obj in enumerate(split)
    ]
    for i, obj in enumerate(split[2:]):
        reveal = Matrix.Translation((m(34), 0, 0)) @ Matrix.Rotation(math.radians(-25), 4, "Z")
        split_views.append(duplicate(obj, f"HH_VIEW_SPLIT_HARDWARE_{i}", reveal @ obj.matrix_world))
    capture(
        output,
        "separate_assembled.png",
        camera,
        split_views,
        (88, -160, 110),
        (0, 0, 10),
        128,
        "LEFT: ASSEMBLED / RIGHT: HARDWARE AT INSTALLED COORDINATES",
        white,
    )

    displays = [
        duplicate(masters[0], "HH_PIN_STYLE_CAPTIVE", Matrix.Translation((m(-9), 0, 0))),
        duplicate(masters[1], "HH_PIN_STYLE_SEPARATE", Matrix.Translation((m(7), 0, 0))),
        duplicate(masters[2], "HH_PIN_STYLE_CLIP", Matrix.Translation((m(14), m(-4), 0))),
    ]
    capture(
        output,
        "pin_styles.png",
        camera,
        displays,
        (24, -50, 36),
        (2, 0, 3),
        40,
        "LEFT: CAPTIVE / RIGHT: GROOVED PIN + C CLIP",
        white,
    )
    capture(
        output,
        "biaxial_top.png",
        camera,
        [parts[0]],
        (0, 0, 100),
        (0, 0, 0),
        60,
        "IN-DISC ROOTS / CLEAR CENTRE + FOUR TENDON HOLES",
        white,
    )
    for obj in [*parts, *pins, label]:
        obj.hide_render = False
    camera.location, camera.rotation_euler, camera.data.ortho_scale = saved[:3]
    scene.render.resolution_x, scene.render.resolution_y = saved[3:]
    scene.render.filepath = str(output / "hollow_side_hinge_assembly.png")
    for obj in support:
        obj.hide_viewport = True
