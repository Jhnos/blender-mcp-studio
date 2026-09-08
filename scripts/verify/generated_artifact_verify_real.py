#!/usr/bin/env python3
"""Run a declarative Blender generator/oracle/MCP artifact verification contract."""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import sys
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.narrowing import (  # noqa: E402
    as_str,
    as_str_keyed_exact,
    required,
)
from src.verification.artifact_files import binary_stl_metrics  # noqa: E402
from src.verification.generated_artifact_contract import (  # noqa: E402
    GeneratedArtifactContract,
    build_generator_code,
    contract_from_mapping,
)
from src.verification.generated_artifact_verdict import assess_verification  # noqa: E402


class BlenderSocketOracle:
    def __init__(self, host: str, port: int, timeout: float = 180.0) -> None:
        self._address = (host, port)
        self._timeout = timeout

    def execute(self, code: str) -> Mapping[str, object]:
        payload = json.dumps({"type": "execute_code", "params": {"code": code}}).encode()
        with socket.create_connection(self._address, timeout=10.0) as connection:
            connection.settimeout(self._timeout)
            connection.sendall(payload)
            raw = b""
            while True:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                raw += chunk
                try:
                    response = json.loads(raw.decode())
                except json.JSONDecodeError:
                    continue
                narrowed = required(
                    response,
                    as_str_keyed_exact,
                    message="Blender socket returned a non-object response",
                    error=RuntimeError,
                )
                if narrowed.get("status") != "success":
                    raise RuntimeError(f"Blender execution failed: {narrowed!r}")
                return narrowed
        raise RuntimeError("Blender socket closed before returning complete JSON")

    def execute_json(self, code: str) -> Mapping[str, object]:
        response = self.execute(code)
        result = required(
            response.get("result"),
            as_str_keyed_exact,
            message=f"Blender result envelope is invalid: {response!r}",
            error=RuntimeError,
        )
        stdout = required(
            result.get("result"),
            as_str,
            message=f"Blender stdout is invalid: {result!r}",
            error=RuntimeError,
        )
        lines = [line for line in stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("Blender oracle returned empty stdout")
        return required(
            json.loads(lines[-1]),
            as_str_keyed_exact,
            message="Blender oracle JSON is not an object",
            error=RuntimeError,
        )


def load_contract(path: Path) -> GeneratedArtifactContract:
    decoded = required(
        json.loads(path.read_text(encoding="utf-8")),
        as_str_keyed_exact,
        message="verification contract must contain one JSON object",
        error=ValueError,
    )
    return contract_from_mapping(decoded, PROJECT_ROOT)


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
    return int(suffix.group(1)) if suffix else obj.name
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
shell_counts = {{}}
if config['count_shells']:
    for obj in parts:
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
    'shell_counts': shell_counts,
    'channel_probe_results': channel_probe_results,
    'joint_sweep': sweep_result,
    'selected_count': len(selected),
    'layout_footprint_mm': layout_footprint,
}}))
"""


async def mcp_readiness(
    endpoint: str,
    identity: str,
) -> Mapping[str, object]:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    transport = StreamableHttpTransport(
        endpoint,
        headers={"x-mes-identity": identity},
    )
    async with Client(transport) as client:
        result = await client.call_tool(
            "check_print_readiness",
            {
                "selection_only": True,
                "apply_modifiers": True,
                "min_wall_thickness_mm": 0.8,
                "overhang_angle_deg": 45.0,
            },
            raise_on_error=False,
        )
    structured = None if result.is_error else as_str_keyed_exact(result.structured_content)
    if structured is None:
        raise RuntimeError(f"MCP readiness failed: {result.content!r}")
    return structured


async def verify(args: argparse.Namespace) -> int:
    contract = load_contract(args.contract)
    oracle = BlenderSocketOracle(args.blender_host, args.blender_port)
    if not args.skip_generate:
        oracle.execute(build_generator_code(contract, PROJECT_ROOT))
    observation = oracle.execute_json(oracle_code(contract))
    readiness_report = await mcp_readiness(args.mcp_url, args.identity)
    readiness = {
        "selected_count": observation.get("selected_count"),
        "layout_footprint_mm": observation.get("layout_footprint_mm"),
        "report": readiness_report,
    }
    artifact_state = {
        str(path): path.is_file() and path.stat().st_size > 0 for path in contract.artifacts
    }
    artifact_metrics: dict[str, object] = {}
    for path in contract.artifacts:
        if artifact_state[str(path)] and path.suffix.lower() == ".stl":
            try:
                artifact_metrics[str(path)] = asdict(binary_stl_metrics(path.read_bytes()))
            except ValueError as exc:
                artifact_state[str(path)] = False
                artifact_metrics[str(path)] = {"error": str(exc)}
    summary = assess_verification(contract, artifact_state, observation, readiness)
    for item in summary.evidence:
        print(f"[{'PASS' if item.passed else 'FAIL'}] {item.name}: {item.detail}")
    print(
        json.dumps(
            {
                "contract": contract.name,
                "passed": summary.passed,
                "oracle": observation,
                "readiness": readiness_report,
                "artifact_metrics": artifact_metrics,
            },
            ensure_ascii=False,
        )
    )
    return 0 if summary.passed else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--blender-host", default="127.0.0.1")
    parser.add_argument("--blender-port", type=int, default=9876)
    parser.add_argument("--mcp-url", default="http://127.0.0.1:19505/mcp")
    parser.add_argument("--identity", default="generated-artifact-verifier")
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="verify the current Blender scene and existing artifacts without regenerating",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(verify(parse_args())))
