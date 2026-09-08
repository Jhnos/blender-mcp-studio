"""Shared Blender primitives for trusted local mechanical generators."""

from __future__ import annotations

import math
from collections.abc import Sequence

import bmesh
import bpy

from scripts.hollow_hinge_render import m


def material(
    name: str, color: tuple[float, float, float, float], metallic: float = 0.0
) -> bpy.types.Material:
    result = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = color
    result.metallic = metallic
    result.roughness = 0.24 if metallic else 0.42
    principled = result.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = result.roughness
    return result


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)


def assign(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def apply_transform(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.select_set(False)


def add_cylinder(
    name: str,
    radius_mm: float,
    depth_mm: float,
    location_mm: tuple[float, float, float],
    axis: str = "Z",
    vertices: int = 48,
) -> bpy.types.Object:
    rotation = {
        "X": (0.0, math.pi / 2.0, 0.0),
        "Y": (math.pi / 2.0, 0.0, 0.0),
        "Z": (0.0, 0.0, 0.0),
    }[axis]
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=m(radius_mm),
        depth=m(depth_mm),
        location=tuple(m(value) for value in location_mm),
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    apply_transform(obj)
    return obj


def add_ellipsoid(
    name: str,
    dimensions_mm: tuple[float, float, float],
    location_mm: tuple[float, float, float],
    segments: int = 40,
    rings: int = 24,
) -> bpy.types.Object:
    """A sphere scaled to three different diameters — a rounded, finger-like body.

    Built as a unit sphere and scaled, then the transform applied, so the object
    leaves with a scale of 1 and downstream Booleans and world-space measurement
    see the shape they expect rather than a scaled proxy.

    Segment counts stay modest for the same reason every other primitive here
    does: the readiness check samples a fixed triangle budget, and a body that
    blows the budget reports as truncated, which the contracts treat as failure.
    """
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=1.0,
        location=tuple(m(value) for value in location_mm),
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(m(value / 2.0) for value in dimensions_mm)
    apply_transform(obj)
    return obj


def loft_rings(
    name: str, rings: Sequence[Sequence[tuple[float, float, float]]]
) -> bpy.types.Object:
    """Close a stack of equal-length rings into one solid: bottom cap, sides, top cap.

    This shape has now been hand-written three times — `model_inset_hinge.root` builds
    a four-cornered stack, `octopus_tip_geometry.create_cap` an N-faceted one — so it
    lives here rather than being typed a third time. The earlier two are left where
    they are: they are part of controlled deliveries and re-pointing them would change
    files whose output is checksummed.

    Rings run bottom to top and must all carry the same number of points, wound the
    same way; a ring need not be planar, which is what lets a sloped rib be lofted the
    same way as a flat plate. Coordinates are millimetres.
    """
    if len(rings) < 2:
        raise ValueError("a loft needs at least two rings")
    width = len(rings[0])
    if width < 3 or any(len(ring) != width for ring in rings):
        raise ValueError("every ring in a loft needs the same three or more points")

    vertices = [tuple(m(value) for value in point) for ring in rings for point in ring]
    faces: list[tuple[int, ...]] = [tuple(reversed(range(width)))]
    for level in range(len(rings) - 1):
        base = level * width
        for index in range(width):
            following = (index + 1) % width
            faces.append(
                (base + index, base + following, base + following + width, base + index + width)
            )
    faces.append(tuple(range((len(rings) - 1) * width, len(rings) * width)))

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    cleanup_mesh(obj)
    return obj


def boolean(target: bpy.types.Object, tool: bpy.types.Object, operation: str) -> None:
    """Apply `tool` to `target`, refusing to do it to an object nobody evaluates.

    `hide_viewport` drops an object out of the depsgraph, and `modifier_apply` on a
    disabled modifier removes it without applying anything — no error, no geometry.
    Three separate features have shipped as silent no-ops that way, and each looked
    fine afterwards because none of them changed a bounding box. Callers that hide
    their masters must unhide them for the duration, as `hinge_retention` already does.
    """
    if target.hide_viewport:
        raise RuntimeError(
            f"{operation} on {target.name!r} would be skipped silently: the object is "
            "hidden in the viewport, so it is not evaluated. Unhide it while building."
        )
    bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(name=f"HH_{operation}", type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def cleanup_mesh(obj: bpy.types.Object) -> None:
    editable = bmesh.new()
    editable.from_mesh(obj.data)
    bmesh.ops.remove_doubles(editable, verts=editable.verts, dist=m(0.005))
    bmesh.ops.dissolve_degenerate(editable, edges=editable.edges, dist=m(0.001))
    # Wire debris the two thresholds above are too tight to catch. A boolean
    # between operands with coincident faces can leave an edge carrying no
    # faces at all — one turned up 0.01 mm long on a fork lug, which is longer
    # than either threshold and still means nothing. An edge with no faces
    # cannot be part of a solid, so removing it is not a repair, it is taking
    # out something that was never surface. Nothing here touches a face, so
    # every exported mesh stays identical to the byte.
    loose_edges = [edge for edge in editable.edges if not edge.link_faces]
    if loose_edges:
        bmesh.ops.delete(editable, geom=loose_edges, context="EDGES")
    loose_verts = [vert for vert in editable.verts if not vert.link_edges]
    if loose_verts:
        bmesh.ops.delete(editable, geom=loose_verts, context="VERTS")
    bmesh.ops.recalc_face_normals(editable, faces=editable.faces)
    editable.to_mesh(obj.data)
    editable.free()
    obj.data.update()
