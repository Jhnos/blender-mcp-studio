"""Execute the closed screen plan on staged handles; no source or output selection.

The caller owns NativeSceneSession and the independent validation callback. No
artifact is accepted merely because a Boolean, rebase or save returned normally.
"""

from collections.abc import Callable, Mapping, Sequence

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

from scripts.blender_mesh_primitives import add_cylinder, boolean, loft_rings
from scripts.blender_mesh_rebase import rebase_mesh
from scripts.blender_mesh_triangulation import triangulate_mesh
from src.core.domain.lab_station_joints import SerratedJointSpec
from src.core.domain.native_revision import NativeRevisionError
from src.core.planning.screen_revision_plan import ScreenRevisionPlan
from src.core.planning.serrated_contact_plan import plan_contact_triangulation
from src.infrastructure.narrowing import (
    as_finite_number,
    as_int,
    as_nonempty_sequence,
    required,
)
from src.verification.artifact_files import binary_stl_surface

Surface = dict[str, object]
Observe = Callable[[str, Mapping[str, Surface]], None]


def surface(obj: bpy.types.Object) -> Surface:
    obj.data.calc_loop_triangles()
    return {
        "vertices": [tuple(v.co) for v in obj.data.vertices],
        "faces": [tuple(t.vertices) for t in obj.data.loop_triangles],
        "matrix_world": [tuple(row) for row in obj.matrix_world],
    }


def _rows3(value: object) -> list[Sequence[object]]:
    rows = required(
        value,
        as_nonempty_sequence,
        message="missing canonical coordinates",
        error=NativeRevisionError,
    )
    result = []
    for raw in rows:
        row = required(
            raw, as_nonempty_sequence, message="invalid canonical row", error=NativeRevisionError
        )
        if len(row) != 3:
            raise NativeRevisionError("canonical rows must have three components")
        result.append(row)
    return result


def _points(value: object) -> list[tuple[float, float, float]]:
    def number(value: object) -> float:
        return required(
            value, as_finite_number, message="invalid canonical point", error=NativeRevisionError
        )

    return [(number(row[0]), number(row[1]), number(row[2])) for row in _rows3(value)]


def _faces(value: object) -> list[tuple[int, int, int]]:
    def index(value: object) -> int:
        return required(value, as_int, message="invalid canonical index", error=NativeRevisionError)

    return [(index(row[0]), index(row[1]), index(row[2])) for row in _rows3(value)]


def _registered_frame(
    obj: bpy.types.Object, points: Sequence[Sequence[float]], wrist: bool
) -> tuple[Matrix, float]:
    frame = (
        Matrix(((0, 0, -0.001, 0), (0, -0.001, 0, 0), (0.001, 0, 0, 0), (0, 0, 0, 1)))
        if wrist
        else Matrix.Diagonal((0.001, 0.001, 0.001, 1))
    )
    original = [v.co.copy() for v in obj.data.vertices]
    transformed = [frame @ Vector(p) for p in points]
    if not original or not transformed:
        raise NativeRevisionError("canonical binding requires nonempty source geometry")
    frame.translation = Vector(
        tuple(min(v[i] for v in original) - min(v[i] for v in transformed) for i in range(3))
    )
    transformed = [frame @ Vector(p) for p in points]
    errors: list[float] = []
    for first, second in ((original, transformed), (transformed, original)):
        tree = KDTree(len(second))
        for index, point in enumerate(second):
            tree.insert(point, index)
        tree.balance()
        errors.extend(tree.find(point)[2] for point in first)
    maximum = max(errors) * 1000
    if maximum > 0.001 or (obj.matrix_world @ frame).determinant() <= 0:
        raise NativeRevisionError(
            "canonical print asset does not match the registered source frame"
        )
    return frame, maximum


def prepare_screen_source(
    objects: Mapping[str, bpy.types.Object],
    plan: ScreenRevisionPlan,
    canonical: Mapping[str, bytes],
    observe: Observe,
) -> dict[str, float]:
    """Explicit source preparation; canonical bytes are supplied by the source receipt."""
    owners = (*plan.modified_owners, plan.wrist_owner)
    required_names = {*owners, *plan.triangulate_owners, "整機_螢幕收折"}
    if not required_names <= set(objects) or set(canonical) != set(owners):
        raise NativeRevisionError("screen recipe requires its exact registered source owners")
    if any(
        objects[name].type != "MESH"
        or objects[name].modifiers
        or objects[name].vertex_groups
        or objects[name].data.shape_keys
        for name in (*owners, *plan.triangulate_owners)
    ):
        raise NativeRevisionError("screen preparation requires rigid source meshes")
    decoded = {name: binary_stl_surface(canonical[name]) for name in owners}
    observe("canonical-input", decoded)
    frames = {}
    points_by_name = {}
    errors = {}
    for name in owners:
        points = _points(decoded[name]["vertices"])
        frame, errors[name] = _registered_frame(objects[name], points, name == plan.wrist_owner)
        frames[name], points_by_name[name] = frame, points
    before = {name: obj.matrix_world.copy() for name, obj in objects.items()}
    for name in plan.triangulate_owners:
        obj = objects[name]
        vertices = [tuple(v.co) for v in obj.data.vertices]
        triangulate_mesh(obj.data)
        if [tuple(v.co) for v in obj.data.vertices] != vertices:
            raise NativeRevisionError("source triangulation changed original coordinates")
        observe("prepare-" + name, {name: surface(obj)})
    for name in owners:
        faces = _faces(decoded[name]["faces"])
        rebase_mesh(objects[name], points_by_name[name], faces, frames[name])
        observe("bind-" + name, {name: surface(objects[name])})
    bpy.context.view_layer.update()
    probes = [Vector(p) for p in ((0, 0, 0), (0.01, 0, 0), (0, 0.01, 0), (0, 0, 0.01))]
    maximum = max(
        (objects[name].matrix_world @ p - matrix @ p).length * 1000
        for name, matrix in before.items()
        if name not in owners
        for p in probes
    )
    if maximum > 0.001:
        raise NativeRevisionError("canonical binding moved unrelated rigid frames")
    errors["unrelated_frame_drift_mm"] = maximum
    observe(
        "prepared-all", {name: surface(obj) for name, obj in objects.items() if obj.type == "MESH"}
    )
    return errors


def apply_screen_geometry(
    objects: Mapping[str, bpy.types.Object], plan: ScreenRevisionPlan, observe: Observe
) -> None:
    """Two operations on the same two rigid identities; temporary tools are consumed."""
    before = {
        name: obj.data
        for name, obj in objects.items()
        if obj.type == "MESH" and name not in plan.modified_owners
    }
    for index, name in enumerate(plan.modified_owners):
        target = objects[name]
        hidden = target.hide_viewport, target.hide_get()
        try:
            target.hide_viewport = False
            target.hide_set(False)
            if index == 0:
                bore = plan.bore
                tool = add_cylinder(
                    bore.name,
                    bore.radius_mm,
                    bore.height_mm,
                    bore.center_mm,
                    axis=bore.axis,
                    vertices=bore.segments or 96,
                    collection=bpy.context.scene.collection,
                )
                tool.rotation_euler.x = plan.bore_phase_rad
            else:
                tool = loft_rings("NATIVE_CLAMP_stop", plan.stop_rings_mm)
            bpy.context.view_layer.update()
            boolean(
                target,
                tool,
                "DIFFERENCE" if index == 0 else "UNION",
                depsgraph=bpy.context.view_layer.depsgraph,
            )
            triangulate_mesh(target.data)
        finally:
            target.hide_viewport = hidden[0]
            target.hide_set(hidden[1])
        observe("operation-" + str(index), {name: surface(target)})
    for name in plan.modified_owners:
        target = objects[name]
        vertices = [tuple(v.co) for v in target.data.vertices]
        faces = [tuple(p.vertices) for p in target.data.polygons]
        pivot = Vector(plan.pivot_mm)
        points = [tuple((target.matrix_world @ v.co) * 1000 - pivot) for v in target.data.vertices]
        patch = plan_contact_triangulation(
            points, faces, SerratedJointSpec(), axial_bounds_mm=(-86, -83)
        )
        rebase_mesh(target, vertices, patch.faces, Matrix.Identity(4))
        observe("contact-" + name, {name: surface(target)})
    if any(objects[name].data != mesh for name, mesh in before.items()):
        raise NativeRevisionError("screen geometry replaced unrelated mesh data")
