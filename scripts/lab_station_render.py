"""Presentation of the laboratory assembly and actual printable tooth coupons."""

from pathlib import Path

import bpy

from scripts.hollow_hinge_render import configure_mechanical_camera, look_at, m
from scripts.lab_station_rig import set_pose


def render_views(
    output: Path,
    lid: bpy.types.Object,
    screen_pivot: bpy.types.Object,
    chassis: bpy.types.Object,
    cup: bpy.types.Object,
    coupon: bpy.types.Object,
) -> bpy.types.Object:
    scene = bpy.context.scene
    # All renders are actual model geometry. Colours distinguish functional groups.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.background_type = "WORLD"
    scene.world.color = (0.12, 0.14, 0.17)
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "LS_VIEW_camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = m(620)
    configure_mechanical_camera(camera)
    scene.camera = camera
    for name, at in (
        ("assembly", (430.0, -650.0, 420.0)),
        ("side", (650.0, -75.0, 210.0)),
        ("top", (0.0, -76.0, 750.0)),
    ):
        camera.location = tuple(m(v) for v in at)
        look_at(camera, (0, -75, 120))
        scene.render.filepath = str(output / (name + ".png"))
        bpy.ops.render.render(write_still=True)
        if name == "assembly":
            controls = [bpy.data.objects["LS_CTRL_" + label] for label in ("capillary", "pH_temp")]
            try:
                set_pose(controls[0], probe_slide_mm=100)
                scene.render.filepath = str(output / "independent-motion.png")
                bpy.ops.render.render(write_still=True)
                set_pose(controls[1], probe_slide_mm=100)
                scene.render.filepath = str(output / "probe-raised.png")
                bpy.ops.render.render(write_still=True)
                set_pose(controls[0], yaw_deg=-45)
                set_pose(controls[1], yaw_deg=45)
                scene.render.filepath = str(output / "probe-parked.png")
                bpy.ops.render.render(write_still=True)
            finally:
                for control in controls:
                    set_pose(control, probe_slide_mm=0, yaw_deg=0)
            try:
                set_pose(screen_pivot, tilt_step=0)
                scene.render.filepath = str(output / "screen-folded.png")
                bpy.ops.render.render(write_still=True)
            finally:
                set_pose(screen_pivot, tilt_step=4)
    # Service configuration: lid/HMI lifted, the outer chassis hidden for circuit bay inspection.
    lid.location.z += m(180)
    screen_pivot.location.z += m(180)
    chassis.hide_render = True
    cup.hide_render = True
    camera.location = (m(430), m(-650), m(620))
    camera.data.ortho_scale = m(650)
    look_at(camera, (0, -45, 190))
    scene.render.filepath = str(output / "service.png")
    bpy.ops.render.render(write_still=True)
    chassis.hide_render = False
    cup.hide_render = False
    lid.location.z -= m(180)
    screen_pivot.location.z -= m(180)
    render_clamp_views(scene, camera, output)
    # Face-up duplicates show the actual printable teeth without assembly occlusion.
    saved_visibility = [
        (obj, obj.hide_render) for obj in list(bpy.context.scene.objects) if obj.type == "MESH"
    ]
    preview = []
    try:
        for obj, _ in saved_visibility:
            obj.hide_render = True
        for x in (-23, 23):
            obj = coupon.copy()
            bpy.context.collection.objects.link(obj)
            obj.hide_render = False
            obj.hide_viewport = False
            obj.location = (m(x), 0, 0)
            preview.append(obj)
        camera.location = (m(65), m(-110), m(110))
        camera.data.ortho_scale = m(100)
        look_at(camera, (0, 0, 2))
        scene.render.filepath = str(output / "joint-coupon.png")
        bpy.ops.render.render(write_still=True)
    finally:
        for obj in preview:
            bpy.data.objects.remove(obj, do_unlink=True)
        for obj, hidden in saved_visibility:
            obj.hide_render = hidden
    camera.location = (m(430), m(-650), m(420))
    camera.data.ortho_scale = m(620)
    look_at(camera, (0, -75, 120))
    bpy.context.view_layer.update()
    render_wrist_tools(scene, camera, output)
    return camera


def render_clamp_views(scene: bpy.types.Scene, camera: bpy.types.Object, output: Path) -> None:
    """Actual assembly and exploded service view; restore every pose and visibility flag."""
    meshes = [o for o in scene.objects if o.type == "MESH"]
    state = [(o, o.hide_render, o.location.copy()) for o in meshes]
    camera_state = (camera.location.copy(), camera.rotation_euler.copy(), camera.data.ortho_scale)
    try:
        for obj in meshes:
            obj.hide_render = not (
                obj.name.startswith(("LS_FIT_pH_temp", "LS_HW_pH_temp", "LS_REF_pH_temp_guide"))
                or obj.name in ("LS_REF_E201C", "LS_REF_DS18B20")
            )
        camera.location = (m(160), m(-280), m(200))
        camera.data.ortho_scale = m(125)
        look_at(camera, (28, -135, 140))
        scene.render.filepath = str(output / "clamp-detail.png")
        bpy.ops.render.render(write_still=True)
        for obj in meshes:
            if obj.name == "LS_FIT_pH_temp_clamp_cap" or (
                obj.name.startswith("LS_HW_pH_temp_jaw") and obj.name.endswith("_nut")
            ):
                obj.location.x -= m(50)
            elif obj.name.startswith("LS_FIT_pH_temp_liner") and obj.name.endswith("_mate"):
                obj.location.x -= m(24)
            elif obj.name.startswith("LS_HW_pH_temp_jaw"):
                obj.location.x += m(40)
            elif obj.name == "LS_FIT_pH_temp_rod_keeper" or obj.name.startswith(
                "LS_HW_pH_temp_keeper"
            ):
                obj.location.z += m(-10 if obj.name.endswith("_nut") else 20)
        camera.location = (m(220), m(-350), m(290))
        camera.data.ortho_scale = m(260)
        look_at(camera, (25, -130, 190))
        scene.render.filepath = str(output / "clamp-exploded.png")
        bpy.ops.render.render(write_still=True)
    finally:
        for obj, hidden, location in state:
            obj.hide_render = hidden
            obj.location = location
        camera.location, camera.rotation_euler, camera.data.ortho_scale = camera_state
        bpy.context.view_layer.update()


def render_wrist_tools(scene: bpy.types.Scene, camera: bpy.types.Object, output: Path) -> None:
    """Show the same tool envelopes used by the assembly verifier."""
    from scripts.blender_mesh_primitives import assign
    from scripts.lab_station_wrist import wrist_tool_envelopes

    visibility = [(o, o.hide_render) for o in scene.objects if o.type == "MESH"]
    camera_state = (camera.location.copy(), camera.rotation_euler.copy(), camera.data.ortho_scale)
    tools = wrist_tool_envelopes("pH_temp")
    try:
        for obj, _ in visibility:
            obj.hide_render = obj.name not in (
                "LS_FIT_pH_temp_lift_frame",
                "LS_REF_pH_temp_link_1",
            ) and not obj.name.startswith("LS_HW_pH_temp_wrist")
        for tool in tools:
            assign(tool, bpy.data.objects["LS_FIT_capillary_lift_frame"].data.materials[0])
        camera.location = (m(155), m(70), m(235))
        camera.data.ortho_scale = m(190)
        look_at(camera, (15, -75, 177))
        scene.render.filepath = str(output / "wrist-tool-access.png")
        bpy.ops.render.render(write_still=True)
    finally:
        for obj, hidden in visibility:
            obj.hide_render = hidden
        for tool in tools:
            bpy.data.objects.remove(tool, do_unlink=True)
        camera.location, camera.rotation_euler, camera.data.ortho_scale = camera_state
        bpy.context.view_layer.update()


def render_rotary_views(output: Path) -> None:
    scene = bpy.context.scene
    camera = scene.camera
    assert camera is not None
    camera.location = (0.43, -0.65, 0.43)
    look_at(camera, (0, -65, 150))
    for name, left, right in (
        ("working", 0, 0),
        ("left-raised", 100, 0),
        ("both-raised", 100, 100),
    ):
        set_pose(bpy.data.objects["LR_CTRL_capillary"], lift_mm=left)
        set_pose(bpy.data.objects["LR_CTRL_pH_temp"], lift_mm=right)
        scene.render.filepath = str(output / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    set_pose(bpy.data.objects["LR_CTRL_capillary"], lift_mm=0)
    set_pose(bpy.data.objects["LR_CTRL_pH_temp"], lift_mm=0)
    saved_location, saved_rotation = camera.location.copy(), camera.rotation_euler.copy()
    saved_scale = camera.data.ortho_scale
    camera.location = (0.29, -0.28, 0.23)
    camera.data.ortho_scale = 0.15
    look_at(camera, (92, -128, 170))
    scene.render.filepath = str(output / "pivot-detail.png")
    bpy.ops.render.render(write_still=True)
    camera.location = (-0.32, -0.16, 0.32)
    camera.data.ortho_scale = 0.18
    look_at(camera, (-123, 7, 215))
    scene.render.filepath = str(output / "elbow-detail.png")
    bpy.ops.render.render(write_still=True)
    camera.location, camera.rotation_euler = saved_location, saved_rotation
    camera.data.ortho_scale = saved_scale
