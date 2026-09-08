"""Builds one registered hand instance from its plan: geometry, gates, exports, views.

Composition and export only. The shape is in the plans, the numbers are in the
specs, the names are in the naming policy. Nothing here claims a grip force, a
print success, or a fit.
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_artifact_export import export_stl_mm  # noqa: E402
from scripts.blender_mesh_primitives import assign, collection, material  # noqa: E402
from scripts.hand_gates import (  # noqa: E402
    leave_only_the_hand_visible,
    refuse_a_cluttered_file,
    refuse_a_disconnected_knuckle,
    refuse_a_multi_shell,
    refuse_a_stale_scene,
    refuse_extra_part_numbers,
    refuse_footprint_drift,
)
from scripts.hand_geometry import assemble_hand, build_finger, build_palm  # noqa: E402
from scripts.hand_presentation import build_print_layout, present_hand  # noqa: E402
from src.core.domain.hand_instances import HAND_INSTANCES  # noqa: E402
from src.core.planning.hand_plan import HandPlan, hand_plan  # noqa: E402


def _adopt(obj: bpy.types.Object, group: bpy.types.Collection) -> None:
    scene = bpy.context.scene
    group.objects.link(obj)
    if obj.users_collection and scene.collection in obj.users_collection:
        scene.collection.objects.unlink(obj)


def build_hand(slug: str, cleared_prefix: str) -> None:
    """`cleared_prefix` is what the entry point told `run_generator` to clear; it has
    to be this instance's namespace or the previous run's hand is still in the scene."""
    instance = HAND_INSTANCES[slug]
    if cleared_prefix != instance.namespace:
        raise RuntimeError(
            f"the entry point clears {cleared_prefix!r} but {slug} builds under "
            f"{instance.namespace!r}; nothing of this hand would be cleared"
        )
    plan = hand_plan(instance)
    output = PROJECT_ROOT / instance.output_dir
    output.mkdir(parents=True, exist_ok=True)
    _build(plan, output)


def _build(plan: HandPlan, output: Path) -> None:
    instance, naming = plan.instance, plan.naming
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 1.0

    palette = plan.presentation.palette
    bone = material(naming.material("BODY"), palette.body)
    alt = material(naming.material("ALT"), palette.alt)
    finger = collection(naming.finger_collection)

    parts = build_finger(plan.loose_finger)
    for index, part in enumerate(parts, start=1):
        _adopt(part, finger)
        # Per-object material links, so alternating colours do not force the
        # units apart into separate meshes. Sharing the mesh is the point.
        assign(part, bone)
        part.material_slots[0].link = "OBJECT"
        part.material_slots[0].material = alt if index % 2 == 0 else bone
    refuse_extra_part_numbers(parts, plan)
    export_stl_mm(parts, output / instance.finger_stl)
    export_stl_mm([parts[0]], output / instance.phalanx_stl)

    palm = build_palm(plan.palm)
    refuse_a_disconnected_knuckle(palm, plan)
    _adopt(palm, finger)
    assign(palm, bone)
    refuse_a_multi_shell(palm)
    export_stl_mm([palm], output / instance.palm_stl)

    hand = assemble_hand(plan, palm)
    for unit in hand:
        if unit is not palm:
            _adopt(unit, finger)
            assign(unit, bone)
    export_stl_mm(hand, output / instance.hand_stl)
    scene[plan.scene_keys.stations] = list(plan.counts.stations)

    by_name = {part.name: part for part in [*parts, palm]}
    refuse_footprint_drift(by_name, plan)
    layout = build_print_layout(plan, by_name)

    scene[plan.scene_keys.phalanx_names] = [part.name for part in parts]
    scene[plan.scene_keys.design_note] = instance.design_note
    refuse_a_stale_scene(plan)
    present_hand(output, plan, parts, layout, hand)
    leave_only_the_hand_visible(hand)
    refuse_a_cluttered_file(hand)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / instance.blend_file))
    print("hand ready", instance.slug, str(output))
