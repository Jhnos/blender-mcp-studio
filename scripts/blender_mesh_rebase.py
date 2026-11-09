"""Bind validated print coordinates to an existing rigid part, preserving its descendants."""

from collections.abc import Sequence
from math import isfinite

import bpy
from mathutils import Matrix


def rebase_mesh(
    obj: bpy.types.Object,
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    local_frame: Matrix,
) -> None:
    """Keep the input coordinates intact; compensate child frames for the new data basis.

    The caller validates the canonical surface and its registration. This adapter
    neither fits nor repairs geometry. A reflected local basis is valid when it
    compensates an existing mirrored object; physical handedness is checked by
    the caller using the composed world transform.
    """
    if obj.type != "MESH" or obj.modifiers or obj.vertex_groups or obj.data.shape_keys:
        raise ValueError("Rebase requires a rigid mesh without vertex-dependent modifiers")
    if (
        len(local_frame) != 4
        or any(len(row) != 4 or any(not isfinite(v) for v in row) for row in local_frame)
        or tuple(local_frame[3]) != (0, 0, 0, 1)
        or local_frame.determinant() == 0
    ):
        raise ValueError("Rebase requires a finite invertible affine frame")
    if (
        not vertices
        or not faces
        or any(len(point) != 3 or any(not isfinite(v) for v in point) for point in vertices)
    ):
        raise ValueError("Rebase requires non-empty finite three-dimensional coordinates")
    if any(
        len(face) != 3 or any(type(i) is not int or not 0 <= i < len(vertices) for i in face)
        for face in faces
    ):
        raise ValueError("Rebase requires valid triangle indices")
    inverse = local_frame.inverted()
    old = obj.data
    basis, world = obj.matrix_basis.copy(), obj.matrix_world.copy()
    children = [(child, child.matrix_parent_inverse.copy()) for child in obj.children]
    new = bpy.data.meshes.new(old.name + "_print_asset")
    try:
        new.from_pydata(vertices, [], faces)
        for material in old.materials:
            new.materials.append(material)
        new.update()
        obj.data = new
        obj.matrix_world = world @ local_frame
        for child, parent_inverse in children:
            child.matrix_parent_inverse = inverse @ parent_inverse
        bpy.context.view_layer.update()
    except BaseException:
        # Restore the real scene on interruption too; the original error propagates.
        obj.data = old
        obj.matrix_basis = basis
        for child, parent_inverse in children:
            child.matrix_parent_inverse = parent_inverse
        bpy.context.view_layer.update()
        bpy.data.meshes.remove(new)
        raise
    if old.users == 0:
        bpy.data.meshes.remove(old)
