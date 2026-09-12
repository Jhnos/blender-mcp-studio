"""Actual mesh regression probes; sampled clearances are not physical load tests."""

import math
from itertools import combinations, product

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

from scripts.lab_station_joints import placed_plate
from scripts.lab_station_rig import set_pose


def tree(obj: bpy.types.Object) -> BVHTree:
    return BVHTree.FromPolygons(
        [obj.matrix_world @ vertex.co for vertex in obj.data.vertices],
        [list(face.vertices) for face in obj.data.polygons],
    )


def verify_motion() -> dict[str, object]:
    control = bpy.data.objects["LS_SCREEN_CONTROL"]
    moving = [bpy.data.objects[name] for name in ("LS_FIT_lcd_front", "LS_FIT_lcd_back")]
    fixed = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and (
            obj.name.startswith(
                (
                    "LS_REF_capillary",
                    "LS_REF_pH_temp",
                    "LS_FIT_capillary",
                    "LS_FIT_pH_temp",
                    "LS_HW_capillary",
                    "LS_HW_pH_temp",
                )
            )
            or obj.name
            in (
                "LS_FIT_chassis",
                "LS_FIT_lid",
                "LS_FIT_screen_bracket_left",
                "LS_FIT_screen_bracket_right",
            )
        )
    ]
    samples = []
    try:
        for angle in range(0, 76, 5):
            set_pose(control, tilt_step=angle / 15, release_mm=2.0)
            hits = [(a.name, b.name) for a in moving for b in fixed if tree(a).overlap(tree(b))]
            minimum = min(
                (obj.matrix_world @ v.co).z * 1000 for obj in moving for v in obj.data.vertices
            )
            samples.append(
                {"angle_deg": angle, "surface_intersections": hits, "minimum_z_mm": minimum}
            )
            if hits or minimum < 86:
                raise ValueError(f"Screen sweep failed: {samples[-1]}")
    finally:
        set_pose(control, tilt_step=4, release_mm=0.0)
    mat = moving[0].data.materials[0]
    a = placed_plate("LS_DIAG_fixed", mat, (-4.7, 0, 0), 1)
    b = placed_plate("LS_DIAG_moving", mat, (4.7, 0, 0), -1)
    orientation = b.rotation_euler.to_matrix().to_4x4()
    coupon = []
    try:
        for coupon_angle, release, expected in (
            (0, 0, False),
            (15, 0, False),
            (7.5, 0, True),
            (7.5, 2, False),
        ):
            b.rotation_euler = (
                Matrix.Rotation(math.radians(coupon_angle), 4, "X") @ orientation
            ).to_euler()
            b.location.x = (4.7 + release) / 1000
            bpy.context.view_layer.update()
            pair_count = len(tree(a).overlap(tree(b)))
            coupon.append(
                {"angle_deg": coupon_angle, "release_mm": release, "intersection_pairs": pair_count}
            )
            if bool(pair_count) != expected:
                raise ValueError(f"Tooth engagement regression: {coupon[-1]}")
    finally:
        for obj in (a, b):
            bpy.data.objects.remove(obj, do_unlink=True)
    return {
        "screen_sweep": samples,
        "coupon_engagement": coupon,
        "scope": "Sampled surface intersections only; no force, cable, containment or full arm sweep acceptance.",
    }


def verify_coupled_motion() -> dict[str, object]:
    """Include all moving pairs within each head and a Cartesian grid between heads."""
    cache: dict[str, dict[int, dict[str, BVHTree]]] = {}
    internal_pairs = 0
    for label in ("capillary", "pH_temp"):
        control = bpy.data.objects["LR_CTRL_" + label]
        meshes = [
            o
            for o in bpy.context.scene.objects
            if o.type == "MESH"
            and not o.hide_render
            and o.name.startswith("LR_" + label + "_")
            and not any(tag in o.name for tag in ("support_envelope", "mount_envelope", "_fixed"))
            and not o.name.endswith("_base")
        ]
        required = {
            f"LR_{label}_{suffix}"
            for suffix in ("head", "bar_0", "bar_1", "clamp_cap", "pin_0_head", "pin_1_head")
        }
        required.update(
            f"LR_{label}_{part}_{i}_head"
            for part in (
                "nut",
                "washer_inner",
                "washer_spacer",
                "washer_outer",
                "sleeve_frame",
                "sleeve_link",
            )
            for i in (0, 1)
        )
        required.update(
            f"LR_{label}_liner_{i}{suffix}"
            for i in range(1 if label == "capillary" else 2)
            for suffix in ("", "_mate")
        )
        required.update(
            f"LR_{label}_probe_{name}"
            for name in (("glass",) if label == "capillary" else ("pH", "temperature"))
        )
        if not required <= {o.name for o in meshes}:
            raise ValueError("Coupled motion population incomplete")
        cache[label] = {}
        try:
            for amount in range(0, 101, 10):
                set_pose(control, lift_mm=amount)
                sample = {o.name: tree(o) for o in meshes}
                cache[label][amount] = sample
                for (a, ta), (b, tb) in combinations(sample.items(), 2):
                    internal_pairs += 1
                    if ta.overlap(tb):
                        raise ValueError(f"Internal rotary collision: {label}, {amount}, {a}, {b}")
        finally:
            set_pose(control, lift_mm=0)
    cross_pairs = 0
    poses = []
    for left, right in product(cache["capillary"], cache["pH_temp"]):
        for (a, ta), (b, tb) in product(
            cache["capillary"][left].items(), cache["pH_temp"][right].items()
        ):
            cross_pairs += 1
            if ta.overlap(tb):
                raise ValueError(f"Cross-head rotary collision: {left}, {right}, {a}, {b}")
        poses.append({"capillary_mm": left, "pH_temp_mm": right})
    return {
        "poses": poses,
        "internal_pair_checks": internal_pairs,
        "cross_pair_checks": cross_pairs,
        "scope": "11 positions per head, all 121 Cartesian combinations; surface intersections only, no continuous motion, containment, flex or cables.",
    }


def verify_rotary_screen() -> dict[str, object]:
    screen = bpy.data.objects["LS_SCREEN_CONTROL"]
    controls = [bpy.data.objects["LR_CTRL_" + name] for name in ("capillary", "pH_temp")]
    prior = [{"lift_mm": float(c["lift_mm"])} for c in controls]
    screen_prior = {key: float(screen[key]) for key in ("tilt_step", "release_mm")}
    moving = [
        bpy.data.objects[name]
        for name in (
            "LS_FIT_lcd_front",
            "LS_FIT_lcd_back",
            "LS_REF_touch_glass",
            "LS_REF_lcd_pcb",
            "LS_REF_terminal_allowance",
        )
    ]
    obstacles = [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH" and o.name.startswith("LR_") and not o.hide_render
    ]
    if len(obstacles) < 40:
        raise ValueError("Rotary screen population incomplete")
    rows = []
    try:
        for left, right in product((0, 50, 100), repeat=2):
            for c, height in zip(controls, (left, right), strict=True):
                set_pose(c, lift_mm=height)
            fixed = {o.name: tree(o) for o in obstacles}
            for angle in range(0, 76, 5):
                set_pose(screen, tilt_step=angle / 15, release_mm=2)
                for obj in moving:
                    body = tree(obj)
                    hits = [name for name, mesh in fixed.items() if body.overlap(mesh)]
                    if hits:
                        raise ValueError(
                            f"Rotary screen collision: {left}, {right}, {angle}, {obj.name}, {hits}"
                        )
                rows.append({"left_mm": left, "right_mm": right, "screen_deg": angle})
    finally:
        for c, values in zip(controls, prior, strict=True):
            set_pose(c, **values)
        set_pose(screen, **screen_prior)
    return {
        "samples": rows,
        "scope": "144 discrete combinations, surface collision only; not continuous motion, containment or cable qualification.",
    }


def verify_rotary_elbows(joint: str = "elbow") -> list[dict[str, object]]:
    """Require connected tooth members and discriminate locked/released half-pitch poses."""
    from scripts.lab_station_rig import set_pose

    if joint not in ("elbow", "shoulder"):
        raise ValueError("Unsupported rotary tooth joint: " + joint)
    rows: list[dict[str, object]] = []
    for label in ("capillary", "pH_temp"):
        control = bpy.data.objects["LR_CTRL_" + label]
        upper = bpy.data.objects[f"LR_{label}_support_envelope_0"]
        lower = bpy.data.objects[f"LR_{label}_support_envelope_1"]
        if joint == "shoulder":
            upper, lower = bpy.data.objects[f"LR_{label}_mount_envelope"], upper
        if not all(o.get(joint + "_integrated") for o in (upper, lower)):
            raise ValueError(f"Rotary {joint} is not an integrated tooth interface: " + label)
        if joint + "_release_mm" not in control:
            raise ValueError(f"Rotary {joint} release control missing: " + label)
        saved = {key: float(control[key]) for key in (joint + "_deg", joint + "_release_mm")}
        try:
            for angle, release, expected in (
                (0, 0, False),
                (7.5, 0, True),
                (7.5, 2, False),
                (15, 2, False),
                (15, 0, False),
            ):
                set_pose(control, **{joint + "_deg": angle, joint + "_release_mm": release})
                overlap = bool(tree(upper).overlap(tree(lower)))
                if overlap != expected:
                    raise ValueError(
                        f"Rotary {joint} tooth mismatch: {label}, {angle}, {release}, {overlap}"
                    )
                for suffix in ("bolt", "nut", "washer_left", "washer_right"):
                    part = bpy.data.objects[f"LR_{label}_{joint}_{suffix}"]
                    if any(tree(part).overlap(tree(link)) for link in (upper, lower)):
                        raise ValueError(
                            f"Rotary {joint} hardware collision: {label}, {angle}, {release}, {suffix}"
                        )
                rows.append(
                    {
                        "head": label,
                        "angle_deg": angle,
                        "release_mm": release,
                        "tooth_collision_expected": expected,
                    }
                )
        finally:
            set_pose(control, **saved)
    return rows


def verify_rotary_support_meshes() -> list[dict[str, object]]:
    """Check every structural arm member is connected and closed; not full readiness."""
    import bmesh

    rows: list[dict[str, object]] = []
    for label in ("capillary", "pH_temp"):
        for suffix in (
            "support_envelope_0",
            "support_envelope_1",
            "mount_envelope",
            "fixed",
            "head",
            "bar_0",
            "bar_1",
        ):
            obj = bpy.data.objects[f"LR_{label}_{suffix}"]
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            try:
                unseen = set(mesh.verts)
                shells = 0
                while unseen:
                    shells += 1
                    pending = [unseen.pop()]
                    while pending:
                        vertex = pending.pop()
                        for edge in vertex.link_edges:
                            other = edge.other_vert(vertex)
                            if other in unseen:
                                unseen.remove(other)
                                pending.append(other)
                bad_edges = sum(not edge.is_manifold for edge in mesh.edges)
                small_faces = sum(face.calc_area() < 1e-12 for face in mesh.faces)
                row = {
                    "part": obj.name,
                    "shells": shells,
                    "nonmanifold_edges": bad_edges,
                    "degenerate_faces": small_faces,
                }
                if shells != 1 or bad_edges or small_faces:
                    raise ValueError(f"Rotary support mesh invalid: {row}")
                rows.append(row)
            finally:
                mesh.free()
    return rows


def verify_rotary_elbow_assembly() -> dict[str, object]:
    """Fold the HMI before inserting inward-facing elbow washers and nuts."""
    from scripts.lab_station_arm import verify_elbow_assembly
    from scripts.lab_station_rig import set_pose

    screen = bpy.data.objects["LS_SCREEN_CONTROL"]
    saved = {key: float(screen[key]) for key in ("tilt_step", "release_mm")}
    try:
        set_pose(screen, tilt_step=0, release_mm=2)
        return verify_elbow_assembly(("LS_", "LR_"), "LR_")
    finally:
        set_pose(screen, **saved)


def verify_rotary_elbow_tools() -> dict[str, object]:
    """Check nominal straight tool bodies in the folded-screen assembly pose."""
    from scripts.lab_station_arm import rotary_elbow_tools
    from scripts.lab_station_rig import set_pose

    screen = bpy.data.objects["LS_SCREEN_CONTROL"]
    saved = {key: float(screen[key]) for key in ("tilt_step", "release_mm")}
    rows: list[dict[str, object]] = []
    try:
        set_pose(screen, tilt_step=0, release_mm=2)
        obstacles = {
            o.name: tree(o)
            for o in bpy.context.scene.objects
            if o.type == "MESH"
            and not o.hide_render
            and o.name.startswith(("LS_", "LR_"))
            and not o.name.startswith(("LS_CHECK_", "LS_DIAG_", "LR_DIAG_"))
        }
        for label in ("capillary", "pH_temp"):
            tools = rotary_elbow_tools(label)
            try:
                bpy.context.view_layer.update()
                for tool in tools:
                    hits = [name for name, mesh in obstacles.items() if tree(tool).overlap(mesh)]
                    if hits:
                        raise ValueError(
                            f"Rotary elbow tool obstructed: {label}, {tool.name}, {hits}"
                        )
                    rows.append({"head": label, "tool": tool.name, "surface_collisions": 0})
            finally:
                for tool in tools:
                    bpy.data.objects.remove(tool, do_unlink=True)
    finally:
        set_pose(screen, **saved)
    return {
        "samples": rows,
        "scope": "Nominal straight tool bodies at seating only; no insertion sweep, handles, thread or torque qualification.",
    }
