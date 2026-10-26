"""Chain-safe polygon triangulation for Boolean output: constrained Delaunay per face.

An exact Boolean emits planar ngons whose edges carry chains of collinear vertices
wherever a finely triangulated face crossed them. Float rounding bends each chain by
nanometres, and the stock ear-clip/beautify method then draws triangles across the
chain, leaving nanometre-high slivers that become zero-area faces and intersecting
pairs once the part is placed metres from the origin. The Delaunay criterion fans
every chain vertex to the far side of the polygon instead. No vertex moves and none
is added; a polygon whose vertices coincide cannot be reproduced vertex-for-vertex
and is reported as the upstream Boolean defect it is, not repaired here.
"""

import bmesh
import bpy


def _delaunay_triangles(face: bmesh.types.BMFace) -> list[list[int]]:
    """Index triangles covering `face` vertex-for-vertex, or raise when none exist."""
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt

    normal = face.normal.copy()
    if normal.length == 0:
        raise ValueError("Cannot triangulate a polygon without a plane")
    normal.normalize()
    pivot = Vector((1, 0, 0)) if abs(normal.x) < 0.9 else Vector((0, 1, 0))
    axis_u = normal.cross(pivot).normalized()
    axis_v = normal.cross(axis_u)
    count = len(face.verts)
    points = [Vector((v.co.dot(axis_u), v.co.dot(axis_v))) for v in face.verts]
    coords, _, triangles, sources, _, _ = delaunay_2d_cdt(
        points, [(i, (i + 1) % count) for i in range(count)], [list(range(count))], 1, 0.0
    )
    if len(coords) != count or any(len(source) != 1 for source in sources):
        raise ValueError("Triangulation changed the vertex set of a polygon")
    if len(triangles) != count - 2 or any(len(item) != 3 for item in triangles):
        raise ValueError("Triangulation did not cover a polygon with triangles")
    return [[sources[index][0] for index in triangle] for triangle in triangles]


def triangulate_faces(mesh: bmesh.types.BMesh) -> None:
    """Triangulate every polygon by constrained Delaunay in its own plane."""
    for face in [item for item in mesh.faces if len(item.verts) > 3]:
        vertices = list(face.verts)
        normal = face.normal.copy()
        triangles = _delaunay_triangles(face)
        material = face.material_index
        bmesh.ops.delete(mesh, geom=[face], context="FACES_ONLY")
        for triangle in triangles:
            created = mesh.faces.new([vertices[index] for index in triangle])
            created.material_index = material
            if created.normal.dot(normal) < 0:
                created.normal_flip()
    mesh.faces.ensure_lookup_table()


def triangulate_mesh(mesh: bpy.types.Mesh) -> None:
    """Commit chain-safe triangles only after every source polygon is reproduced."""
    editable = bmesh.new()
    try:
        editable.from_mesh(mesh)
        triangulate_faces(editable)
        editable.to_mesh(mesh)
    finally:
        editable.free()
    mesh.update()
