"""Lays the parts out for the plate and renders the views the plan asks for.

The wrap-at-the-bed arithmetic is in `LayoutPlan`; this only bakes each slot
into a copy's mesh. Camera positions, margins, colours and captions come from
`PresentationPlan`; the only measuring done here is of Blender's own objects,
to put the floor under a view and to frame the assembly.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from scripts.biaxial_hinge_presentation import capture, duplicate
from scripts.blender_mesh_primitives import assign, collection, material
from scripts.hollow_hinge_render import m, setup_render
from scripts.presentation_profile import FINGER_PROFILE
from src.core.planning.hand_plan import HandPlan
from src.core.planning.presentation_plan import ViewPlan


def build_print_layout(
    plan: HandPlan, parts: dict[str, bpy.types.Object]
) -> list[bpy.types.Object]:
    """Every planned slot, as a flat copy whose placement is baked into its mesh.

    Baked, not carried on the object transform: carried there it survived every
    in-process check and came back as identity when the .blend was reopened.
    """
    layout = collection(plan.naming.layout_collection)
    lay_flat = Matrix.Rotation(math.pi / 2, 4, plan.presentation.lay_flat_axis)
    copies: list[bpy.types.Object] = []
    for index, slot in enumerate(plan.layout.placements, start=1):
        placed = duplicate(parts[slot.name], plan.naming.layout_part(index), Matrix.Identity(4))
        placed.data = parts[slot.name].data.copy()
        placed.data.transform(lay_flat)
        # Centred in its slot on its own bounding box, not on its origin.
        low = Vector(placed.bound_box[0])
        high = Vector(placed.bound_box[6])
        centre = (low + high) / 2
        placed.data.transform(
            Matrix.Translation((m(slot.x_mm) - centre.x, m(slot.y_mm) - centre.y, 0.0))
        )
        for existing in list(placed.users_collection):
            existing.objects.unlink(placed)
        layout.objects.link(placed)
        copies.append(placed)
    bpy.context.view_layer.update()
    return copies


def _corners(objects: list[bpy.types.Object]) -> list[Vector]:
    return [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]


def present_hand(
    output: Path,
    plan: HandPlan,
    parts: list[bpy.types.Object],
    layout: list[bpy.types.Object],
    hand: list[bpy.types.Object],
) -> None:
    palette = plan.presentation.palette
    floor_material = material(plan.naming.material("FLOOR"), palette.floor)
    white = material(plan.naming.material("LABEL"), palette.label)
    camera, rig = setup_render(plan.stations[0].chain.link, floor_material, assign, FINGER_PROFILE)
    floor = rig[0]
    subjects = {"hand": hand, "finger": parts, "layout": layout}

    for obj in bpy.data.objects:
        obj.hide_render = True

    def ground(objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
        """The floor just under this view's subject, handed to `capture` with it."""
        low = min(corner.z for corner in _corners(objects)) / m(1.0)
        floor.location.z = m(low - plan.presentation.floor_clearance_mm)
        return [*objects, floor]

    def framed(view: ViewPlan, subject: list[bpy.types.Object]) -> tuple[
        tuple[float, float, float], tuple[float, float, float], float
    ]:
        if view.framing is None:
            assert view.location_mm is not None and view.target_mm is not None
            assert view.scale_mm is not None
            return (view.location_mm, view.target_mm, view.scale_mm)
        corners = _corners(subject)
        zs = [corner.z / m(1.0) for corner in corners]
        xs = [corner.x / m(1.0) for corner in corners]
        mid_z = (min(zs) + max(zs)) / 2
        tall = max(zs) - min(zs)
        wide = max(xs) - min(xs)
        frame = view.framing.margin * max(wide, tall * view.framing.aspect)
        eye_x, eye_y, eye_z = view.framing.eye
        return ((frame * eye_x, frame * eye_y, mid_z + frame * eye_z), (0.0, 0.0, mid_z), frame)

    for view in plan.presentation.views:
        subject = subjects[view.subject]
        location, target, scale = framed(view, subject)
        capture(
            output,
            view.file_name,
            camera,
            ground(subject),
            location,
            target,
            scale,
            view.title,
            white,
            label_offset=view.label_offset,
        )

    for obj in bpy.data.objects:
        obj.hide_render = False
