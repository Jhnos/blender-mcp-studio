"""The Blender-side oracle: the code a contract runs inside the resident Blender.

Split out of the real verifier at its line budget. This module builds one
string of Python for another interpreter; it measures nothing itself and
imports no Blender. The verifier sends the string over the addon socket and
parses the JSON the last line prints.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from src.verification.generated_artifact_contract import GeneratedArtifactContract


def oracle_code(contract: GeneratedArtifactContract) -> str:
    expected = contract.oracle
    payload: dict[str, object] = {
        "object_prefix": expected.object_prefix,
        "scene_list_property": expected.scene_list_property,
        "center_probe_object": expected.center_probe_object,
        "bore_probe_points_mm": [list(point) for point in expected.bore_probe_points_mm],
        "collision_groups": [item.prefix for item in expected.collision_groups],
        "disjoint_groups": list(expected.disjoint_groups),
        "count_shells": expected.expected_shells_per_object is not None,
        "closure_trajectory": (
            {
                "chain_prefix": expected.closure_trajectory.chain_prefix,
                "pivot_offset_mm": expected.closure_trajectory.pivot_offset_mm,
                "axis": expected.closure_trajectory.axis,
                "shares": list(expected.closure_trajectory.travel_shares),
                "full_travel_deg": expected.closure_trajectory.full_travel_deg,
                "steps": expected.closure_trajectory.steps,
            }
            if expected.closure_trajectory is not None
            else None
        ),
        "channel_probes": [
            {
                "key": probe.key,
                "object": probe.object_name,
                "axis": probe.axis,
                "open": [list(point) for point in probe.open_points_mm],
                "solid": [list(point) for point in probe.solid_points_mm],
            }
            for probe in expected.channel_probes
        ],
        "selection_prefix": contract.readiness.selection_prefix,
        "joint_sweep": asdict(expected.joint_sweep) if expected.joint_sweep else None,
    }
    config_json = json.dumps(payload)
    return f"""\
import bpy, bmesh, json, math, re
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
config = json.loads({json.dumps(config_json)})
def natural_key(obj):
    suffix = re.search(r'(\\d+)$', obj.name)
    return (0, int(suffix.group(1)), obj.name) if suffix else (1, 0, obj.name)
def world_tree(obj, transform=None):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world if transform is None else transform)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    return bm, BVHTree.FromBMesh(bm, epsilon=0.0)
parts = sorted(
    [obj for obj in bpy.data.objects if obj.name.startswith(config['object_prefix'])],
    key=natural_key,
)
collision_results = {{}}
for prefix in config['collision_groups']:
    group = sorted(
        [obj for obj in bpy.data.objects if obj.name.startswith(prefix)],
        key=natural_key,
    )
    overlaps = []
    for left, right in zip(group, group[1:]):
        left_bm, left_tree = world_tree(left)
        right_bm, right_tree = world_tree(right)
        try:
            overlaps.append(len(left_tree.overlap(right_tree)))
        finally:
            left_bm.free()
            right_bm.free()
    collision_results[prefix] = {{
        'object_count': len(group),
        'adjacent_overlap_pairs': overlaps,
    }}
sweep_config = config['joint_sweep']
sweep_result = None
if sweep_config is not None:
    master = bpy.data.objects[sweep_config['master_object']]
    pivot = sweep_config['pivot_offset_mm'] / 1000.0
    offset = Matrix.Translation(Vector((0.0, 0.0, pivot)))
    twist = Matrix.Rotation(math.radians(sweep_config['mating_twist_deg']), 4, 'Z')
    left_bm, left_tree = world_tree(master)
    sweep_overlaps = []
    try:
        for angle in sweep_config['angles_deg']:
            bend = Matrix.Rotation(math.radians(angle), 4, sweep_config['axis'])
            transform = master.matrix_world @ offset @ bend @ twist @ offset
            right_bm, right_tree = world_tree(master, transform)
            try:
                sweep_overlaps.append(len(left_tree.overlap(right_tree)))
            finally:
                right_bm.free()
    finally:
        left_bm.free()
    sweep_result = {{'angles_deg': sweep_config['angles_deg'], 'overlap_pairs': sweep_overlaps}}
probe = bpy.data.objects.get(config['center_probe_object'])
center_hit = None
if probe is not None:
    center_hit, _, _, _ = probe.ray_cast(Vector((0.0, 0.0, -1.0)), Vector((0.0, 0.0, 1.0)))
bore_hits = []
if probe is not None:
    for point in config['bore_probe_points_mm']:
        start = Vector((point[0] / 1000.0, point[1] / 1000.0, -1.0))
        hit, _, _, _ = probe.ray_cast(start, Vector((0.0, 0.0, 1.0)))
        bore_hits.append(hit)
for obj in bpy.context.selected_objects:
    obj.select_set(False)
selected = []
for obj in bpy.data.objects:
    if obj.name.startswith(config['selection_prefix']):
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.select_set(True)
        selected.append(obj.name)
closure_overlaps = []
_traj = config['closure_trajectory']
if _traj is not None:
    chain = sorted(
        [o for o in bpy.data.objects if o.name.startswith(_traj['chain_prefix'])],
        key=natural_key,
    )
    axis_vector = {{'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}}[
        _traj['axis']
    ]
    for step in range(_traj['steps']):
        fraction = (step + 1) / _traj['steps']
        trees = []
        cumulative = 0.0
        for index, part in enumerate(chain):
            if index:
                cumulative += fraction * _traj['full_travel_deg'] * _traj['shares'][index - 1]
            if index == 0:
                transform = part.matrix_world
            else:
                # Each joint turns about the pivot between this unit and the one
                # before it, and the turns accumulate down the chain: that is
                # what makes it a closing finger rather than three loose hinges.
                pivot_z = (
                    chain[index - 1].matrix_world.translation.z
                    + _traj['pivot_offset_mm'] / 1000.0
                )
                pivot = Vector((0.0, 0.0, pivot_z))
                rotation = Matrix.Rotation(math.radians(cumulative), 4, axis_vector)
                transform = (
                    Matrix.Translation(pivot)
                    @ rotation
                    @ Matrix.Translation(-pivot)
                    @ part.matrix_world
                )
            trees.append(world_tree(part, transform))
        total = 0
        for first in range(len(trees)):
            for second in range(first + 1, len(trees)):
                total += len(trees[first][1].overlap(trees[second][1]))
        for bm, _tree in trees:
            bm.free()
        closure_overlaps.append(total)

shell_counts = {{}}
if config['count_shells']:
    # Every object the contract names anywhere, not just the one prefix the
    # oracle walks. Counting `parts` alone covered three phalanges out of
    # fifteen and no palm — a gate with a coverage hole the size of the model.
    shell_targets = {{}}
    _prefixes = [config['object_prefix'], *config['collision_groups'], *config['disjoint_groups']]
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and any(obj.name.startswith(p) for p in _prefixes):
            shell_targets[obj.name] = obj
    for probe in config['channel_probes']:
        named = bpy.data.objects.get(probe['object'])
        if named is not None and named.type == 'MESH':
            shell_targets[named.name] = named
    for obj in shell_targets.values():
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        seen = set()
        islands = 0
        for face in bm.faces:
            if face.index in seen:
                continue
            islands += 1
            stack = [face]
            while stack:
                current = stack.pop()
                if current.index in seen:
                    continue
                seen.add(current.index)
                for edge in current.edges:
                    for other in edge.link_faces:
                        if other.index not in seen:
                            stack.append(other)
        bm.free()
        shell_counts[obj.name] = islands

channel_probe_results = {{}}
for probe in config['channel_probes']:
    target = bpy.data.objects.get(probe['object'])
    if target is None or not target.data.polygons:
        channel_probe_results[probe['key']] = None
        continue
    axis = probe['axis']
    span = max(target.dimensions) * 1000.0 + 20.0
    def _cast(a_mm, b_mm, axis=axis, target=target, span=span):
        # The two given coordinates are the ones the axis does not run along,
        # in the order x, y, z with the axis dropped.
        if axis == 'Z':
            start = Vector((a_mm / 1000.0, b_mm / 1000.0, -span / 1000.0))
            direction = Vector((0.0, 0.0, 1.0))
        elif axis == 'Y':
            start = Vector((a_mm / 1000.0, -span / 1000.0, b_mm / 1000.0))
            direction = Vector((0.0, 1.0, 0.0))
        else:
            start = Vector((-span / 1000.0, a_mm / 1000.0, b_mm / 1000.0))
            direction = Vector((1.0, 0.0, 0.0))
        local = target.matrix_world.inverted() @ start
        local_dir = (target.matrix_world.inverted().to_3x3() @ direction).normalized()
        hit, _, _, _ = target.ray_cast(local, local_dir)
        return hit
    channel_probe_results[probe['key']] = {{
        'open': [_cast(a, b) for a, b in probe['open']],
        'solid': [_cast(a, b) for a, b in probe['solid']],
    }}

cross_group_overlaps = {{}}
for first_index, first_prefix in enumerate(config['disjoint_groups']):
    for second_prefix in config['disjoint_groups'][first_index + 1:]:
        firsts = [o for o in bpy.data.objects if o.name.startswith(first_prefix)]
        seconds = [o for o in bpy.data.objects if o.name.startswith(second_prefix)]
        total = 0
        for one in firsts:
            _, tree_one = world_tree(one)
            for other in seconds:
                _, tree_other = world_tree(other)
                total += len(tree_one.overlap(tree_other))
        # An empty group would report zero overlaps and read as clean, so the
        # count of what was compared is reported beside the result.
        key = '|'.join(sorted((first_prefix, second_prefix)))
        cross_group_overlaps[key] = total if (firsts and seconds) else None

layout_footprint = None
if selected:
    xs, ys = [], []
    for obj in bpy.data.objects:
        if obj.name.startswith(config['selection_prefix']):
            # Mesh vertices, not `bound_box`. The layout bakes its placement
            # into each copy's vertices, and `bound_box` is a cache that a
            # `data.transform()` does not invalidate — it returned the palm's
            # own un-laid-flat box, 140 x 44, and the bed check passed on it.
            for vertex in obj.data.vertices:
                world = obj.matrix_world @ vertex.co
                xs.append(world.x)
                ys.append(world.y)
    # World units are metres here, the same convention the bore probes use when
    # they divide their millimetre points by 1000.
    layout_footprint = [
        round((max(xs) - min(xs)) * 1000.0, 1),
        round((max(ys) - min(ys)) * 1000.0, 1),
    ]
scene_value = bpy.context.scene.get(config['scene_list_property'], [])
print(json.dumps({{
    'object_count': len(parts),
    'shared_mesh_count': len({{id(obj.data) for obj in parts}}),
    'rotations_deg': [round(math.degrees(obj.rotation_euler.z), 4) for obj in parts],
    'scene_list': list(scene_value),
    'center_ray_hit': center_hit,
    'bore_ray_hits': bore_hits,
    'collision_groups': collision_results,
    'cross_group_overlaps': cross_group_overlaps,
    'closure_overlaps': closure_overlaps,
    'shell_counts': shell_counts,
    'channel_probe_results': channel_probe_results,
    'joint_sweep': sweep_result,
    'selected_count': len(selected),
    'layout_footprint_mm': layout_footprint,
}}))
"""
