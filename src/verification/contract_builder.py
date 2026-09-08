"""Contracts as generated artifacts: a plan in, the committed JSON out.

Both V3 contracts used to be typed from the spec by hand, and one of them
drifted to describe a hand with four phalanges. Every value here is read off
the plan, so the only way to change a contract is to change the spec — and the
T2 test holds the committed files to this output, so the two cannot part.

The hand contract carries the assembly claims (every station, the palm's
channels, the bed); the finger contract carries one chain's kinematics (the
per-joint sweep and the coordinated closure). Same generator, same scene.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.core.planning.hand_plan import HandPlan
from src.core.planning.probe_plan import ChannelProbePlan
from src.verification.generator_imports import reload_modules_for

#: Print-readiness issue codes no shipped part may carry.
FORBIDDEN_ISSUE_CODES = (
    "no_mesh",
    "non_manifold_edges",
    "inconsistent_normals",
    "degenerate_geometry",
    "zero_volume",
    "intersections",
)

Mapping = dict[str, object]


def _points(points: tuple[tuple[float, float], ...]) -> list[list[float]]:
    return [[float(x), float(y)] for x, y in points]


def _channel(probe: ChannelProbePlan) -> Mapping:
    return {
        "object": probe.object_name,
        "axis": probe.axis,
        "open_points_mm": _points(probe.open_points_mm),
        "solid_points_mm": _points(probe.solid_points_mm),
    }


def _base(plan: HandPlan, project_root: Path, name: str) -> Mapping:
    instance = plan.instance
    out = instance.output_dir
    return {
        "name": name,
        "generator_script": instance.generator_script,
        "reload_modules": list(reload_modules_for(project_root, project_root / instance.generator_script)),
        "artifacts": [
            f"{out}/{instance.blend_file}",
            *(f"{out}/{stl}" for stl in instance.stl_files),
            *(f"{out}/{render}" for render in instance.render_files),
        ],
    }


def _oracle_common(plan: HandPlan) -> Mapping:
    naming, probes = plan.naming, plan.probes
    first = plan.stations[0]
    return {
        "object_prefix": naming.hand_chain_prefix(first.label),
        "expected_count": plan.counts.units_per_finger,
        "expected_rotations_deg": [float(a) for a in first.chain.joint_rotations_deg],
        "scene_list_property": naming.scene_key("HAND_STATIONS"),
        "expected_scene_list": list(plan.counts.stations),
        "center_probe_object": naming.hand_unit(first.label, 1),
        "center_channel_expected_open": probes.center_channel_open,
        "bore_probe_points_mm": _points(probes.bore_probe_points_mm),
    }


def _layout_group(plan: HandPlan) -> Mapping:
    return {"prefix": plan.naming.layout_prefix, "expected_count": plan.counts.layout_part_count}


def _readiness(plan: HandPlan, *, with_bed: bool) -> Mapping:
    readiness: Mapping = {
        "selection_prefix": plan.naming.layout_prefix,
        "expected_selection_count": plan.counts.layout_part_count,
        "forbidden_issue_codes": list(FORBIDDEN_ISSUE_CODES),
    }
    if with_bed:
        readiness["max_footprint_mm"] = [plan.layout.bed_mm, plan.layout.bed_mm]
    return readiness


def hand_contract_mapping(plan: HandPlan, project_root: Path) -> Mapping:
    naming, probes = plan.naming, plan.probes
    chains = [naming.hand_chain_prefix(station.label) for station in plan.stations]
    oracle = _oracle_common(plan)
    oracle["collision_groups"] = [
        *(
            {"prefix": prefix, "expected_count": station.chain.link.assembly_unit_count}
            for prefix, station in zip(chains, plan.stations, strict=True)
        ),
        _layout_group(plan),
    ]
    oracle["disjoint_groups"] = chains
    oracle["channel_probes"] = [_channel(probes.palm_tendon_probe), _channel(probes.air_port_probe)]
    oracle["expected_shells_per_object"] = 1
    return {
        **_base(plan, project_root, plan.instance.contract_name),
        "oracle": oracle,
        "readiness": _readiness(plan, with_bed=True),
    }


def finger_contract_mapping(plan: HandPlan, project_root: Path) -> Mapping:
    naming, probes = plan.naming, plan.probes
    first = plan.stations[0]
    chain_prefix = naming.hand_chain_prefix(first.label)
    oracle = _oracle_common(plan)
    oracle["joint_sweep"] = {
        "master_object": naming.hand_unit(first.label, 1),
        "pivot_offset_mm": probes.pivot_offset_mm,
        "axis": probes.hinge_axis,
        "mating_twist_deg": probes.mating_twist_deg,
        "angles_deg": list(probes.sweep_angles_deg),
    }
    oracle["collision_groups"] = [
        {"prefix": chain_prefix, "expected_count": first.chain.link.assembly_unit_count},
        _layout_group(plan),
    ]
    oracle["expected_shells_per_object"] = 1
    oracle["closure_trajectory"] = {
        "chain_prefix": chain_prefix,
        "pivot_offset_mm": probes.pivot_offset_mm,
        "axis": probes.hinge_axis,
        "travel_shares": [float(share) for share in probes.travel_shares],
        "full_travel_deg": probes.full_travel_deg,
        "steps": probes.closure_steps,
    }
    return {
        **_base(plan, project_root, f"{plan.instance.contract_name}_finger"),
        "oracle": oracle,
        "readiness": _readiness(plan, with_bed=False),
    }


def contract_mappings(plan: HandPlan, project_root: Path) -> dict[str, Mapping]:
    """Contract file name → mapping, for everything this instance is verified by."""
    name = plan.instance.contract_name
    return {
        f"{name}.json": hand_contract_mapping(plan, project_root),
        f"{name}_finger.json": finger_contract_mapping(plan, project_root),
    }


def render_contract(mapping: Mapping) -> str:
    return json.dumps(mapping, indent=2) + "\n"
