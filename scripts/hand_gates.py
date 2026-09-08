"""What the generator refuses to export. Each gate here was a defect first.

Every expectation is read from the plan; the gates measure Blender's objects
and compare. A gate that decided its own number would be a second source of
truth for the thing it guards.
"""

from __future__ import annotations

import bpy
from mathutils import Vector

from scripts.hollow_hinge_render import m
from src.core.planning.hand_plan import HandPlan


def shell_count(obj: bpy.types.Object) -> int:
    """How many disconnected solids this mesh actually contains."""
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for edge in mesh.edges:
        left, right = (find(index) for index in edge.vertices)
        if left != right:
            parent[left] = right
    return len({find(index) for index in range(len(mesh.vertices))})


def refuse_a_multi_shell(obj: bpy.types.Object) -> None:
    """A printed part that is two shells is two parts, and watertightness cannot tell."""
    shells = shell_count(obj)
    if shells != 1:
        raise RuntimeError(f"{obj.name} came out as {shells} disconnected solids")


def refuse_extra_part_numbers(parts: list[bpy.types.Object], plan: HandPlan) -> None:
    """How many distinct meshes the finger is, against what the instance declares."""
    distinct = len({id(part.data) for part in parts})
    expected = plan.counts.phalanx_part_count
    if distinct != expected:
        raise RuntimeError(
            f"the finger is {distinct} part numbers where the spec declares {expected}; "
            "that is a decision, not a side effect"
        )


def refuse_a_disconnected_knuckle(palm: bpy.types.Object, plan: HandPlan) -> None:
    """The palm's roots must reach the height the fingers' forks sit at.

    Height is the cheap, decisive test: a root that does not reach cannot be
    coaxial with anything, and the palm was contract-green while every knuckle
    sat 13.5 mm low.
    """
    top = max((palm.matrix_world @ Vector(corner)).z for corner in palm.bound_box) / m(1.0)
    reach = plan.knuckle_reach_mm
    if abs(top - reach) > plan.tolerances.knuckle_mm:
        raise RuntimeError(
            f"the palm's knuckle roots reach {top:.2f} mm but the fingers need "
            f"{reach:.2f} mm of root — the hand cannot be assembled"
        )


def refuse_footprint_drift(parts: dict[str, bpy.types.Object], plan: HandPlan) -> None:
    """The plan's laid-flat footprints against the built parts' measured extents."""
    for footprint in plan.footprints:
        part = parts[footprint.name]
        width = part.dimensions.x / m(1.0)
        depth = part.dimensions.z / m(1.0)
        drift = max(abs(width - footprint.width_mm), abs(depth - footprint.depth_mm))
        if drift > plan.tolerances.footprint_mm:
            raise RuntimeError(
                f"{footprint.name} measures {width:.2f} x {depth:.2f} mm laid flat, "
                f"the plan says {footprint.width_mm:.2f} x {footprint.depth_mm:.2f}"
            )


def refuse_a_stale_scene(plan: HandPlan) -> None:
    """Fail loudly if a previous run's objects are still in the scene."""
    for prefix, count in plan.counts.stale_scene_expectations(plan.naming).items():
        found = sum(1 for obj in bpy.data.objects if obj.name.startswith(prefix))
        if found != count:
            raise RuntimeError(
                f"{found} objects under {prefix!r}, expected {count} — a previous run "
                "was not cleared, and everything downstream is measuring two hands"
            )


def leave_only_the_hand_visible(hand: list[bpy.types.Object]) -> None:
    """Hide everything that is not the hand, so opening the file shows the hand.

    Hidden, not deleted: `run_generator` restores visibility of everything
    outside its prefix in a `finally`, and removing an object out from under
    that bookkeeping makes the restore raise on a dead reference.
    """
    keep = {obj.name for obj in hand}
    for obj in list(bpy.data.objects):
        if obj.name in keep:
            continue
        if obj.type == "MESH":
            obj.hide_viewport = True
            obj.hide_render = True


def refuse_a_cluttered_file(hand: list[bpy.types.Object]) -> None:
    """What is visible on open must be the hand, and only the hand."""
    visible = {obj.name for obj in bpy.data.objects if obj.type == "MESH" and not obj.hide_viewport}
    expected = {obj.name for obj in hand}
    if visible != expected:
        raise RuntimeError(
            "opening this file would show "
            f"{sorted(visible - expected)} besides the hand, and would be missing "
            f"{sorted(expected - visible)}"
        )
