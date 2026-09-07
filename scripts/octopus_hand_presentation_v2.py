"""Renders for V2, framed on the things V2 actually changed.

A view that shows the whole hand proves almost nothing about a 1.5 mm chamfer or a
buttress 8 mm tall. V1 learned that the expensive way: its rubric had to be judged
three times, and both re-runs were answered by adding close-ups rather than by
changing the model. So the close-ups are here from the start, one per claim — the
corner standing on its arm, the stem behind a socket, the pad facing the palm centre,
the chamfered rim, the wire bore beside each socket.

The camera rig, the lighting and the per-view capture all come from the existing
presentation modules rather than being forked; only the viewpoints are V2's.
"""

from __future__ import annotations

from pathlib import Path

import bpy

from scripts.biaxial_hinge_presentation import capture
from scripts.blender_mesh_primitives import material
from scripts.hollow_hinge_render import setup_render
from src.core.domain.octopus_hand_v2 import OctopusHandV2Spec


def _assign(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def present_octopus_v2(
    output: Path,
    spec: OctopusHandV2Spec,
    palm: bpy.types.Object,
    bodies: list[bpy.types.Object],
    pins: list[bpy.types.Object],
    layout_objects: list[bpy.types.Object],
) -> None:
    """Sixteen views: three of the whole hand, thirteen close enough to judge a millimetre."""
    output.mkdir(parents=True, exist_ok=True)
    white = material("HH_OCT2_LABEL", (0.92, 0.94, 0.98, 1))
    floor_material = material("HH_OCT2_FLOOR", (0.05, 0.06, 0.08, 1))
    camera, _rig = setup_render(spec.arm_spec, floor_material, _assign)

    # Everything with the project prefix starts hidden, so a close-up frames only what
    # it names. V1 found coupon parts wandering into shots that never mentioned them.
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name.startswith("HH_") and obj.name != "HH_FLOOR":
            obj.hide_render = True

    hand_objects = [palm, *bodies, *pins]
    span = spec.upright_footprint_mm
    height = spec.upright_height_mm
    station = spec.arm_station_positions_mm[0]
    tip_height = spec.arm_tip_height_mm
    pitch = spec.arm_spec.unit_pitch_mm
    stem_mid = (spec.stem_inner_radius_mm + spec.stem_outer_radius_mm) / 2

    capture(
        output,
        "octopus_v2_assembly.png",
        camera,
        hand_objects,
        (span * 1.5, -span * 2.4, span * 1.7),
        (0.0, 0.0, height / 2),
        span * 2.1,
        "Octopus hand V2 - assembled",
        white,
    )
    capture(
        output,
        "octopus_v2_palm_top.png",
        camera,
        hand_objects,
        (0.1, -0.1, span * 2.6),
        (0.0, 0.0, 0.0),
        span * 1.25,
        "V2 from above - a corner on every arm",
        white,
    )
    capture(
        output,
        "octopus_v2_print_layout.png",
        camera,
        layout_objects,
        (0.0, -span * 1.9, span * 0.9),
        (span * 0.55, 0.0, 10.0),
        span * 2.0,
        "Print layout - palm, body, tip",
        white,
    )

    # Close-ups. Shadows off: V1's reviewers read the in-scene label's shadow as a
    # double exposure and marked otherwise-passing items unclear.
    shading = bpy.context.scene.display.shading
    shadows = shading.show_shadows
    shading.show_shadows = False

    capture(
        output,
        "octopus_v2_palm_bare.png",
        camera,
        [palm],
        (0.1, -0.1, span * 2.4),
        (0.0, 0.0, 0.0),
        span * 1.15,
        "Palm alone - corners, stems, wire bores",
        white,
    )
    # The floor is a 300 mm plane at z = -25, so a camera under the plate looks at the
    # back of it and renders an empty frame. A fresh reviewer marked this view blank and
    # could not judge the bottom chamfer at all; the floor comes out for this shot only.
    floor = bpy.data.objects.get("HH_FLOOR")
    floor_hidden = floor.hide_render if floor is not None else None
    if floor is not None:
        floor.hide_render = True
    capture(
        output,
        "octopus_v2_palm_underside.png",
        camera,
        [palm],
        (0.1, -0.1, -span * 2.4),
        (0.0, 0.0, 0.0),
        span * 1.15,
        "Palm underside - rim chamfer and cable reliefs",
        white,
    )
    if floor is not None and floor_hidden is not None:
        floor.hide_render = floor_hidden
    # The rim looked at from *under* the plate's own plane. Every other view in this set
    # looks down from above the top face, which shows the top chamfer and leaves the
    # bottom one undecidable — from above, a chamfered rim and a plain vertical wall
    # render the same band. A reviewer asked for exactly this framing; edge-on at the
    # plate's mid-height was tried first and is not legible, because the sockets fill it.
    if floor is not None:
        floor.hide_render = True
    capture(
        output,
        "octopus_v2_rim_from_below.png",
        camera,
        [palm],
        (spec.palm_corner_flat_radius_mm + 90, 0.0, -46.0),
        (spec.palm_corner_flat_radius_mm - 8, 0.0, -2.0),
        44.0,
        "Rim from below - the bottom chamfer as its own face",
        white,
    )
    if floor is not None and floor_hidden is not None:
        floor.hide_render = floor_hidden
    capture(
        output,
        "octopus_v2_corner_rim.png",
        camera,
        [palm],
        (spec.palm_enclosing_radius_mm + 40, -30.0, 34.0),
        (spec.palm_corner_flat_radius_mm - 6, 0.0, 0.0),
        46.0,
        "Cut-back corner and its 45 deg rim chamfers",
        white,
    )
    capture(
        output,
        "octopus_v2_stem_detail.png",
        camera,
        [palm],
        (stem_mid + 46, -46.0, 30.0),
        (stem_mid, 0.0, spec.palm_top_face_z_mm + spec.stem_height_mm / 2),
        56.0,
        "Buttress behind the socket, ramping outward",
        white,
    )
    capture(
        output,
        "octopus_v2_wire_bore.png",
        camera,
        [palm],
        (spec.arm_wire_bore_positions_mm[0][0] + 24, -24.0, 40.0),
        (spec.arm_wire_bore_positions_mm[0][0], 0.0, 0.0),
        44.0,
        "Wire bore, inboard of its socket",
        white,
    )
    capture(
        output,
        "octopus_v2_socket_detail.png",
        camera,
        [palm, *[obj for obj in pins if obj.name.startswith("HH_OCT2_PIN_1_1_")]],
        (station[0] + 70, station[1] - 70, 34.0),
        (station[0], station[1], 4.0),
        72.0,
        "Base joint on its corner",
        white,
    )
    capture(
        output,
        "octopus_v2_pad_aim.png",
        camera,
        [obj for obj in bodies if obj.name == "HH_OCT2_SEG_1_2"],
        (station[0] + 30, station[1] - 30, 2 * pitch + 60),
        (station[0], station[1], 2 * pitch),
        70.0,
        "Grip pad aimed at the palm centre",
        white,
    )
    # One arm on its own, side on. In the assembled view the five stacks overlap and
    # self-occlude, and a reviewer could not count the segments — this is the view that
    # answers "five bodies then a cap" without anything else in frame.
    arm_one = [
        obj
        for obj in bodies + pins
        if obj.name.startswith(("HH_OCT2_SEG_1_", "HH_OCT2_TIP_1", "HH_OCT2_PIN_1_"))
    ]
    capture(
        output,
        "octopus_v2_arm_side.png",
        camera,
        arm_one,
        (station[0] + 210, station[1], height * 0.5),
        (station[0], station[1], height * 0.45),
        height * 1.2,
        "One arm, side on - five bodies and a cap",
        white,
    )
    # Looking straight down on the palm with only the lowest body of each arm left
    # standing. From above, the assembled hand hides every pad behind a tip cap, so the
    # pads' headings could not be read against the palm's centre.
    lowest = [obj for obj in bodies if obj.name.endswith("_1") and "SEG" in obj.name]
    capture(
        output,
        "octopus_v2_pad_ring.png",
        camera,
        [palm, *lowest],
        (0.1, -0.1, span * 2.6),
        (0.0, 0.0, 0.0),
        span * 1.25,
        "Lowest body of each arm, from above",
        white,
    )
    # One body and the plate's centre hole in the same straight-down frame. Two reviewers
    # read the assembled top view differently: a pad's two corners stand further out than
    # its face, so four pads present eight salient tips and the eye reads "tabs on the
    # diagonals". Only a frame holding both the pad and the centre it is supposed to aim
    # at can settle which of the four is pointing home.
    first_body = [obj for obj in bodies if obj.name == "HH_OCT2_SEG_1_1"]
    capture(
        output,
        "octopus_v2_pad_to_centre.png",
        camera,
        [palm, *first_body],
        (station[0] / 2, 0.0, span * 2.2),
        (station[0] / 2, 0.0, 0.0),
        span * 0.95,
        "One body and the palm centre, straight down",
        white,
    )
    # The same body alone and tight, straight down. A top chamfer reads here as a border
    # band inside each pad's outline; a square edge would leave the pad one flat tone.
    capture(
        output,
        "octopus_v2_pad_chamfer.png",
        camera,
        first_body,
        (station[0], station[1], 2 * pitch + 40),
        (station[0], station[1], pitch),
        52.0,
        "One body from directly above - pad top edges",
        white,
    )
    capture(
        output,
        "octopus_v2_tip_detail.png",
        camera,
        [obj for obj in bodies if obj.name == "HH_OCT2_TIP_1"],
        (station[0] + 90, -110.0, tip_height + 60),
        (station[0], station[1], tip_height - 10),
        90.0,
        "Terminal tip and its cable bores",
        white,
    )

    shading.show_shadows = shadows
    for obj in hand_objects:
        obj.hide_render = False
