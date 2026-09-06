"""A fit coupon: one palm chunk, two arm bodies, four captive pins.

The whole hand is 117 mm tall with twenty-five live joints, and the one thing no
check can settle is whether the joints survive the upright print pose — the pin
axes go horizontal there, so the bores become bridges and the captive pins get an
unsupported crown. Losing that print costs a night; losing this one costs an hour.

The coupon is cut from the real geometry rather than modelled again, so what it
proves transfers: the same socket, the same bodies, the same pins, in the same
positions they occupy on the hand.
"""

from __future__ import annotations

import bpy

from scripts.blender_mesh_primitives import add_cylinder, boolean, cleanup_mesh, move_to_collection
from src.core.domain.octopus_hand import OctopusHandSpec


def _clone(source: bpy.types.Object, name: str, target: bpy.types.Collection) -> bpy.types.Object:
    """A copy that shares nothing, so trimming it cannot reach the hand."""
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    target.objects.link(obj)
    return obj


def build_coupon(
    palm: bpy.types.Object,
    bodies: list[bpy.types.Object],
    pins: list[bpy.types.Object],
    target: bpy.types.Collection,
    spec: OctopusHandSpec,
) -> list[bpy.types.Object]:
    """Cut a station-sized chunk out of the palm and keep the parts standing on it.

    `bodies` and `pins` are the first arm's, in build order, so the slice taken here
    is the base joint plus as many body-to-body joints as the coupon declares.
    """
    station = spec.arm_station_positions_mm[0]
    chunk = _clone(palm, "HH_OCT_COUPON_PALM", target)
    keep = add_cylinder(
        "HH_OCT_COUPON_TRIM",
        spec.coupon_palm_radius_mm,
        spec.palm_thickness_mm + 20,
        (station[0], station[1], 0.0),
        vertices=48,
    )
    boolean(chunk, keep, "INTERSECT")
    cleanup_mesh(chunk)
    span_mm = max(chunk.dimensions) * 1000.0
    limit_mm = 2 * spec.coupon_palm_radius_mm + 1
    if span_mm > limit_mm:
        raise RuntimeError(
            f"palm chunk was not trimmed: {span_mm:.1f} mm across, expected under {limit_mm:.1f}"
        )

    parts = [chunk]
    for index in range(spec.coupon_body_count):
        parts.append(_clone(bodies[index], f"HH_OCT_COUPON_BODY_{index + 1}", target))
    for index in range(spec.coupon_pin_count):
        parts.append(_clone(pins[index], f"HH_OCT_COUPON_PIN_{index + 1}", target))

    if len(parts) != spec.coupon_part_count:
        raise RuntimeError(f"coupon has {len(parts)} parts, expected {spec.coupon_part_count}")
    for obj in parts:
        move_to_collection(obj, target)
        obj.hide_render = obj.hide_viewport = True
    return parts


def coupon_note(spec: OctopusHandSpec) -> str:
    """One line the operator needs before slicing this file."""
    return (
        f"Coupon: {spec.coupon_part_count} separate shells "
        f"({spec.coupon_body_count} bodies, {spec.coupon_pin_count} captive pins) — "
        f"{spec.coupon_height_mm:g} mm tall. Print arm-up, mm at 100%, "
        f"and do NOT let the slicer auto-arrange the shells. "
        f"Unqualified fit prototype: no strength, retention or release claim."
    )
