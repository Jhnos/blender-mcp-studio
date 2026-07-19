"""Blender 5.1 anti-corruption layer for print-readiness inspection."""

from __future__ import annotations

import json
import math
import textwrap

from src.adapters.blender_response import execute_code_output, mapping, sequence, text
from src.core.domain.command import Command
from src.core.domain.exceptions import PrintReadinessError
from src.core.domain.print_readiness import (
    PrintInspection,
    PrintIssue,
    PrintIssueCode,
    PrintIssueSeverity,
    PrintMetrics,
    PrintReadinessSpec,
)
from src.core.ports.blender_port import BlenderPort

_MARKER = "PRINT_READINESS_JSON:"


def _analysis_code(spec: PrintReadinessSpec) -> str:
    object_filter = "obj.select_get()" if spec.selection_only else "True"
    mesh_source = textwrap.indent(
        (
            "source = obj.evaluated_get(depsgraph)\n"
            "mesh = source.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)\n"
            "matrix = source.matrix_world"
            if spec.apply_modifiers
            else "mesh = obj.data\nmatrix = obj.matrix_world"
        ),
        "        ",
    )
    mesh_cleanup = textwrap.indent(
        "source.to_mesh_clear()" if spec.apply_modifiers else "pass",
        "            ",
    )
    return f"""import bpy
import bmesh
import json
import math
from mathutils.bvhtree import BVHTree

MM = 1000.0
MIN_WALL_MM = {spec.min_wall_thickness_mm!r}
OVERHANG_DEG = {spec.overhang_angle_deg!r}
MAX_TRIANGLE_SAMPLES = 20000
MAX_INTERSECTION_PAIRS = 5000
BED_TOLERANCE_M = 0.00005
EPS_EDGE_M = 1e-9
EPS_AREA_M2 = 1e-18
EPS_VOLUME_M3 = 1e-15

objects = [
    obj for obj in bpy.context.scene.objects
    if obj.type == 'MESH' and obj.visible_get() and {object_filter}
]
issues = []
truncated = False

def add_issue(code, severity, count, names, message):
    if count:
        issues.append({{
            'code': code,
            'severity': severity,
            'count': int(count),
            'object_names': sorted(set(names)),
            'message': message,
        }})

if not objects:
    report = {{
        'metrics': {{
            'object_count': 0,
            'triangle_count': 0,
            'dimensions_mm': [0.0, 0.0, 0.0],
            'estimated_volume_mm3': 0.0,
            'surface_area_mm2': 0.0,
        }},
        'issues': [{{
            'code': 'no_mesh',
            'severity': 'error',
            'count': 0,
            'object_names': [],
            'message': 'No visible mesh objects are available for inspection',
        }}],
        'analysis_truncated': False,
    }}
else:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    records = []
    bounds_min = [float('inf')] * 3
    bounds_max = [float('-inf')] * 3
    total_triangles = 0
    total_volume_m3 = 0.0
    total_area_m2 = 0.0
    non_manifold_count = 0
    non_manifold_names = []
    inconsistent_count = 0
    inconsistent_names = []
    degenerate_count = 0
    degenerate_names = []
    zero_volume_count = 0
    zero_volume_names = []
    negative_scale_count = 0
    negative_scale_names = []

    for obj in objects:
{mesh_source}
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
        finally:
{mesh_cleanup}
        bm.transform(matrix)
        bm.normal_update()
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        for vert in bm.verts:
            for axis in range(3):
                bounds_min[axis] = min(bounds_min[axis], vert.co[axis])
                bounds_max[axis] = max(bounds_max[axis], vert.co[axis])

        triangles = len(bm.faces)
        area_m2 = sum(face.calc_area() for face in bm.faces)
        volume_m3 = abs(bm.calc_volume(signed=True)) if bm.faces else 0.0
        total_triangles += triangles
        total_area_m2 += area_m2
        total_volume_m3 += volume_m3

        bad_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
        bad_normals = sum(1 for edge in bm.edges if edge.is_manifold and not edge.is_contiguous)
        bad_geometry = sum(1 for edge in bm.edges if edge.calc_length() <= EPS_EDGE_M)
        bad_geometry += sum(1 for face in bm.faces if face.calc_area() <= EPS_AREA_M2)
        if bad_edges:
            non_manifold_count += bad_edges
            non_manifold_names.append(obj.name)
        if bad_normals:
            inconsistent_count += bad_normals
            inconsistent_names.append(obj.name)
        if bad_geometry:
            degenerate_count += bad_geometry
            degenerate_names.append(obj.name)
        if volume_m3 <= EPS_VOLUME_M3:
            zero_volume_count += 1
            zero_volume_names.append(obj.name)
        if matrix.to_3x3().determinant() < 0.0:
            negative_scale_count += 1
            negative_scale_names.append(obj.name)

        tree = BVHTree.FromBMesh(bm, epsilon=0.0)
        vertex_sets = [frozenset(vert.index for vert in face.verts) for face in bm.faces]
        records.append({{
            'name': obj.name,
            'bm': bm,
            'tree': tree,
            'vertex_sets': vertex_sets,
        }})

    add_issue('non_manifold_edges', 'error', non_manifold_count, non_manifold_names,
              f'{{non_manifold_count}} non-manifold edges need review')
    add_issue('inconsistent_normals', 'error', inconsistent_count, inconsistent_names,
              f'{{inconsistent_count}} edges have inconsistent face normals')
    add_issue('degenerate_geometry', 'error', degenerate_count, degenerate_names,
              f'{{degenerate_count}} zero-length edges or zero-area faces found')
    add_issue('zero_volume', 'error', zero_volume_count, zero_volume_names,
              f'{{zero_volume_count}} mesh objects have no measurable volume')

    intersection_count = 0
    intersection_names = []
    for record in records:
        for left, right in record['tree'].overlap(record['tree']):
            if left >= right:
                continue
            if record['vertex_sets'][left] & record['vertex_sets'][right]:
                continue
            intersection_count += 1
            intersection_names.append(record['name'])
            if intersection_count >= MAX_INTERSECTION_PAIRS:
                truncated = True
                break
        if intersection_count >= MAX_INTERSECTION_PAIRS:
            break
    if intersection_count < MAX_INTERSECTION_PAIRS:
        for left_index, left_record in enumerate(records):
            for right_record in records[left_index + 1:]:
                overlaps = left_record['tree'].overlap(right_record['tree'])
                remaining = MAX_INTERSECTION_PAIRS - intersection_count
                if len(overlaps) > remaining:
                    overlaps = overlaps[:remaining]
                    truncated = True
                if overlaps:
                    intersection_count += len(overlaps)
                    intersection_names.extend([left_record['name'], right_record['name']])
                if intersection_count >= MAX_INTERSECTION_PAIRS:
                    break
            if intersection_count >= MAX_INTERSECTION_PAIRS:
                break
    add_issue('intersections', 'warning', intersection_count, intersection_names,
              f'{{intersection_count}} intersecting triangle pairs may need a Boolean union')

    global_min_z = bounds_min[2]
    sample_budget = MAX_TRIANGLE_SAMPLES
    thin_count = 0
    thin_names = []
    overhang_count = 0
    overhang_names = []
    max_wall_m = MIN_WALL_MM / MM
    overhang_z = -math.sin(math.radians(OVERHANG_DEG))
    ray_offset = min(1e-7, max_wall_m / 100.0)

    for record in records:
        faces = list(record['bm'].faces)
        if not faces or sample_budget <= 0:
            if faces:
                truncated = True
            continue
        if len(faces) > sample_budget:
            stride = max(1, math.ceil(len(faces) / sample_budget))
            samples = faces[::stride][:sample_budget]
            truncated = True
        else:
            samples = faces
        sample_budget -= len(samples)

        for face in samples:
            if min(vertex.co.z for vertex in face.verts) > global_min_z + BED_TOLERANCE_M:
                if face.normal.z < overhang_z:
                    overhang_count += 1
                    overhang_names.append(record['name'])

            center = face.calc_center_median()
            distances = []
            for direction in (-face.normal, face.normal):
                hit = record['tree'].ray_cast(
                    center + direction * ray_offset,
                    direction,
                    max_wall_m,
                )
                if hit[0] is not None and hit[2] != face.index and hit[3] is not None:
                    distances.append(hit[3])
            if distances and min(distances) < max_wall_m:
                thin_count += 1
                thin_names.append(record['name'])

    add_issue('thin_walls', 'warning', thin_count, thin_names,
              f'{{thin_count}} sampled faces may be thinner than {{MIN_WALL_MM:g}} mm')
    add_issue('overhangs', 'warning', overhang_count, overhang_names,
              f'{{overhang_count}} sampled faces exceed the {{OVERHANG_DEG:g}} degree overhang profile')
    add_issue('negative_scale', 'warning', negative_scale_count, negative_scale_names,
              f'{{negative_scale_count}} objects have a negative world-space scale')
    if truncated:
        add_issue('analysis_truncated', 'warning', 1, [record['name'] for record in records],
                  'Analysis sampling limits were reached; results are partial')

    dimensions = [max(0.0, (bounds_max[i] - bounds_min[i]) * MM) for i in range(3)]
    report = {{
        'metrics': {{
            'object_count': len(objects),
            'triangle_count': total_triangles,
            'dimensions_mm': [round(value, 6) for value in dimensions],
            'estimated_volume_mm3': round(total_volume_m3 * MM ** 3, 6),
            'surface_area_mm2': round(total_area_m2 * MM ** 2, 6),
        }},
        'issues': issues,
        'analysis_truncated': truncated,
    }}
    for record in records:
        record['bm'].free()

print('{_MARKER}' + json.dumps(report, separators=(',', ':')))
"""


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PrintReadinessError(f"Blender returned invalid {context}; expected a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise PrintReadinessError(f"Blender returned invalid {context}; expected a finite number")
    return number


def _integer(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PrintReadinessError(f"Blender returned invalid {context}; expected an integer")
    return value


def _parse_inspection(output: str) -> PrintInspection:
    marker_index = output.rfind(_MARKER)
    if marker_index < 0:
        raise PrintReadinessError("Blender print inspection returned no structured report")
    encoded = output[marker_index + len(_MARKER) :].strip().splitlines()[0]
    try:
        raw: object = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise PrintReadinessError("Blender print inspection returned invalid JSON") from exc
    report = mapping(raw, "print-readiness report", PrintReadinessError)
    if not {"metrics", "issues", "analysis_truncated"}.issubset(report):
        raise PrintReadinessError("Blender print inspection report is missing required fields")
    metrics = mapping(report["metrics"], "print metrics", PrintReadinessError)
    required_metrics = {
        "object_count",
        "triangle_count",
        "dimensions_mm",
        "estimated_volume_mm3",
        "surface_area_mm2",
    }
    if not required_metrics.issubset(metrics):
        raise PrintReadinessError("Blender print metrics are missing required fields")
    dimensions = sequence(metrics["dimensions_mm"], "print dimensions", PrintReadinessError)
    if len(dimensions) != 3:
        raise PrintReadinessError("Blender print dimensions must contain three values")
    parsed_metrics = PrintMetrics(
        object_count=_integer(metrics["object_count"], "object count"),
        triangle_count=_integer(metrics["triangle_count"], "triangle count"),
        dimensions_mm=(
            _number(dimensions[0], "dimension"),
            _number(dimensions[1], "dimension"),
            _number(dimensions[2], "dimension"),
        ),
        estimated_volume_mm3=_number(metrics["estimated_volume_mm3"], "estimated volume"),
        surface_area_mm2=_number(metrics["surface_area_mm2"], "surface area"),
    )
    issues: list[PrintIssue] = []
    for raw_issue in sequence(report["issues"], "print issues", PrintReadinessError):
        issue = mapping(raw_issue, "print issue", PrintReadinessError)
        if not {"code", "severity", "count", "object_names", "message"}.issubset(issue):
            raise PrintReadinessError("Blender print issue is missing required fields")
        names = sequence(issue["object_names"], "issue object names", PrintReadinessError)
        issues.append(
            PrintIssue(
                code=PrintIssueCode(text(issue["code"], "issue code", PrintReadinessError)),
                severity=PrintIssueSeverity(
                    text(issue["severity"], "issue severity", PrintReadinessError)
                ),
                count=_integer(issue["count"], "issue count"),
                object_names=tuple(
                    text(item, "issue object name", PrintReadinessError) for item in names
                ),
                message=text(issue["message"], "issue message", PrintReadinessError),
            )
        )
    truncated = report["analysis_truncated"]
    if not isinstance(truncated, bool):
        raise PrintReadinessError("Blender analysis_truncated must be a boolean")
    return PrintInspection(parsed_metrics, tuple(issues), truncated)


class BlenderPrintReadinessAdapter:
    """Inspect evaluated meshes without mutating the Blender scene."""

    def __init__(self, blender: BlenderPort) -> None:
        self._blender = blender

    async def inspect(self, spec: PrintReadinessSpec) -> PrintInspection:
        result = await self._blender.execute(
            Command(tool_name="execute_code", arguments={"code": _analysis_code(spec)})
        )
        if not result.success:
            raise PrintReadinessError(
                result.error or "Blender print inspection failed without a reason"
            )
        try:
            return _parse_inspection(execute_code_output(result.output, PrintReadinessError))
        except (ValueError, TypeError) as exc:
            if isinstance(exc, PrintReadinessError):
                raise
            raise PrintReadinessError(f"Blender returned an invalid print report: {exc}") from exc
