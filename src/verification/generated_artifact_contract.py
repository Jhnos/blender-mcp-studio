"""Pure contract parsing and evidence assessment for generated Blender artifacts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src.infrastructure.narrowing import (
    as_finite_number,
    as_mapping,
    as_nonempty_str,
    as_positive_int,
    as_sequence,
    as_str,
    as_str_keyed_exact,
    required,
)


@dataclass(frozen=True, slots=True)
class CollisionExpectation:
    prefix: str
    expected_count: int


@dataclass(frozen=True, slots=True)
class JointSweepExpectation:
    master_object: str
    pivot_offset_mm: float
    axis: str
    mating_twist_deg: float
    angles_deg: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class OracleExpectation:
    object_prefix: str
    expected_count: int
    expected_rotations_deg: tuple[float, ...]
    scene_list_property: str
    expected_scene_list: tuple[str, ...]
    center_probe_object: str
    collision_groups: tuple[CollisionExpectation, ...]
    joint_sweep: JointSweepExpectation | None = None


@dataclass(frozen=True, slots=True)
class ReadinessExpectation:
    selection_prefix: str
    expected_selection_count: int
    forbidden_issue_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeneratedArtifactContract:
    name: str
    generator_script: Path
    reload_modules: tuple[str, ...]
    artifacts: tuple[Path, ...]
    oracle: OracleExpectation
    readiness: ReadinessExpectation


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class VerificationSummary:
    evidence: tuple[VerificationEvidence, ...]

    @property
    def passed(self) -> bool:
        return bool(self.evidence) and all(item.passed for item in self.evidence)


def _required_mapping(source: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = _mapping_value(source, key)
    if value is None:
        raise ValueError(f"{key} must be an object")
    return value


def _required_string(source: Mapping[str, object], key: str) -> str:
    return required(
        source.get(key),
        as_nonempty_str,
        message=f"{key} must be a non-empty string",
        error=ValueError,
    )


def _required_positive_int(source: Mapping[str, object], key: str) -> int:
    return required(
        source.get(key),
        as_positive_int,
        message=f"{key} must be a positive integer",
        error=ValueError,
    )


def _required_strings(source: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = _sequence_value(source, key)
    if not value:
        raise ValueError(f"{key} must be a non-empty string array")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{key} must contain only non-empty strings")
    return tuple(item for item in value if isinstance(item, str))


def _required_numbers(source: Mapping[str, object], key: str) -> tuple[float, ...]:
    value = _sequence_value(source, key)
    if not value:
        raise ValueError(f"{key} must be a non-empty number array")
    narrowed = tuple(as_finite_number(item) for item in value)
    if any(item is None for item in narrowed):
        raise ValueError(f"{key} must contain only finite numbers")
    return tuple(item for item in narrowed if item is not None)


def _joint_sweep(source: Mapping[str, object]) -> JointSweepExpectation | None:
    if "joint_sweep" not in source:
        return None
    raw = _required_mapping(source, "joint_sweep")
    axis = _required_string(raw, "axis")
    if axis not in ("X", "Y", "Z"):
        raise ValueError("joint_sweep axis must be X, Y or Z")
    numbers = _required_numbers(
        {"values": [raw.get("pivot_offset_mm"), raw.get("mating_twist_deg")]}, "values"
    )
    if numbers[0] <= 0:
        raise ValueError("joint_sweep pivot_offset_mm must be positive")
    return JointSweepExpectation(
        _required_string(raw, "master_object"),
        numbers[0],
        axis,
        numbers[1],
        _required_numbers(raw, "angles_deg"),
    )


def _resolve_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


def contract_from_mapping(
    source: Mapping[str, object], project_root: Path
) -> GeneratedArtifactContract:
    name = _required_string(source, "name")
    generator_script = _resolve_path(project_root, _required_string(source, "generator_script"))
    reload_modules = _required_strings(source, "reload_modules")
    artifacts = tuple(
        _resolve_path(project_root, item) for item in _required_strings(source, "artifacts")
    )

    oracle_source = _required_mapping(source, "oracle")
    collision_source = _sequence_value(oracle_source, "collision_groups")
    if not collision_source:
        raise ValueError("collision_groups must be a non-empty object array")
    collision_groups: list[CollisionExpectation] = []
    for item in collision_source:
        record = _mapping_value({"record": item}, "record")
        if record is None:
            raise ValueError("collision_groups must contain only objects")
        collision_groups.append(
            CollisionExpectation(
                prefix=_required_string(record, "prefix"),
                expected_count=_required_positive_int(record, "expected_count"),
            )
        )
    oracle = OracleExpectation(
        object_prefix=_required_string(oracle_source, "object_prefix"),
        expected_count=_required_positive_int(oracle_source, "expected_count"),
        expected_rotations_deg=_required_numbers(oracle_source, "expected_rotations_deg"),
        scene_list_property=_required_string(oracle_source, "scene_list_property"),
        expected_scene_list=_required_strings(oracle_source, "expected_scene_list"),
        center_probe_object=_required_string(oracle_source, "center_probe_object"),
        collision_groups=tuple(collision_groups),
        joint_sweep=_joint_sweep(oracle_source),
    )
    if len(oracle.expected_rotations_deg) != oracle.expected_count:
        raise ValueError("expected_rotations_deg length must match expected_count")

    readiness_source = _required_mapping(source, "readiness")
    readiness = ReadinessExpectation(
        selection_prefix=_required_string(readiness_source, "selection_prefix"),
        expected_selection_count=_required_positive_int(
            readiness_source, "expected_selection_count"
        ),
        forbidden_issue_codes=_required_strings(readiness_source, "forbidden_issue_codes"),
    )
    return GeneratedArtifactContract(
        name=name,
        generator_script=generator_script,
        reload_modules=reload_modules,
        artifacts=artifacts,
        oracle=oracle,
        readiness=readiness,
    )


def build_generator_code(
    contract: GeneratedArtifactContract,
    project_root: Path,
) -> str:
    modules_json = json.dumps(list(contract.reload_modules))
    script_json = json.dumps(str(contract.generator_script))
    project_root_json = json.dumps(str(project_root))
    return f"""\
import importlib, runpy, sys
project_root = {project_root_json}
if project_root not in sys.path:
    sys.path.insert(0, project_root)
for module_name in {modules_json}:
    module = importlib.import_module(module_name)
    importlib.reload(module)
runpy.run_path({script_json}, run_name='__main__')
"""


def _mapping_value(source: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    return as_str_keyed_exact(source.get(key))


def _sequence_value(source: Mapping[str, object], key: str) -> list[object] | None:
    narrowed = as_sequence(source.get(key))
    return None if narrowed is None else list(narrowed)


def assess_verification(
    contract: GeneratedArtifactContract,
    artifact_state: Mapping[str, bool],
    oracle: Mapping[str, object],
    readiness: Mapping[str, object],
) -> VerificationSummary:
    evidence: list[VerificationEvidence] = []
    missing_artifacts = [
        str(path) for path in contract.artifacts if not artifact_state.get(str(path))
    ]
    evidence.append(
        VerificationEvidence(
            "artifacts",
            not missing_artifacts,
            "all generated files exist"
            if not missing_artifacts
            else f"missing: {missing_artifacts}",
        )
    )

    expected = contract.oracle
    object_count = oracle.get("object_count")
    evidence.append(
        VerificationEvidence(
            "object_count",
            object_count == expected.expected_count,
            f"observed={object_count!r}, expected={expected.expected_count}",
        )
    )
    shared_mesh_count = oracle.get("shared_mesh_count")
    evidence.append(
        VerificationEvidence(
            "shared_mesh",
            shared_mesh_count == 1,
            f"observed={shared_mesh_count!r}, expected=1",
        )
    )
    rotations = _sequence_value(oracle, "rotations_deg")
    observed_rotations = tuple(
        float(value) for value in rotations or [] if isinstance(value, (int, float))
    )
    evidence.append(
        VerificationEvidence(
            "rotations",
            observed_rotations == expected.expected_rotations_deg,
            f"observed={observed_rotations!r}, expected={expected.expected_rotations_deg!r}",
        )
    )
    scene_list = _sequence_value(oracle, "scene_list")
    observed_scene_list = tuple(value for value in scene_list or [] if isinstance(value, str))
    evidence.append(
        VerificationEvidence(
            "scene_list",
            observed_scene_list == expected.expected_scene_list,
            f"observed={observed_scene_list!r}, expected={expected.expected_scene_list!r}",
        )
    )
    center_ray_hit = oracle.get("center_ray_hit")
    evidence.append(
        VerificationEvidence(
            "center_channel",
            center_ray_hit is False,
            f"center_ray_hit={center_ray_hit!r}",
        )
    )

    collision_records = _mapping_value(oracle, "collision_groups")
    for collision in expected.collision_groups:
        record = (
            _mapping_value(collision_records, collision.prefix)
            if collision_records is not None
            else None
        )
        count = record.get("object_count") if record is not None else None
        overlaps = _sequence_value(record, "adjacent_overlap_pairs") if record is not None else None
        overlap_values = [value for value in overlaps or [] if isinstance(value, int)]
        collision_ok = (
            count == collision.expected_count
            and len(overlap_values) == collision.expected_count - 1
            and all(value == 0 for value in overlap_values)
        )
        evidence.append(
            VerificationEvidence(
                f"collision:{collision.prefix}",
                collision_ok,
                f"objects={count!r}, adjacent_overlaps={overlap_values!r}",
            )
        )

    selected_count = readiness.get("selected_count")
    if expected.joint_sweep is not None:
        sweep = _mapping_value(oracle, "joint_sweep")
        angles = _sequence_value(sweep, "angles_deg") if sweep is not None else None
        overlaps = _sequence_value(sweep, "overlap_pairs") if sweep is not None else None
        sweep_ok = (
            angles == list(expected.joint_sweep.angles_deg)
            and overlaps is not None
            and len(overlaps) == len(expected.joint_sweep.angles_deg)
            and all(type(value) is int and value == 0 for value in overlaps)
        )
        evidence.append(
            VerificationEvidence(
                "joint_sweep", sweep_ok, f"angles={angles!r}, overlaps={overlaps!r}"
            )
        )
    evidence.append(
        VerificationEvidence(
            "readiness_selection",
            selected_count == contract.readiness.expected_selection_count,
            (
                f"observed={selected_count!r}, "
                f"expected={contract.readiness.expected_selection_count}"
            ),
        )
    )
    report = _mapping_value(readiness, "report")
    issues = _sequence_value(report, "issues") if report is not None else None
    issue_mappings = [m for m in (as_mapping(item) for item in issues or []) if m is not None]
    issue_codes = {
        code for item in issue_mappings for code in [as_str(item.get("code"))] if code is not None
    }
    forbidden = issue_codes & set(contract.readiness.forbidden_issue_codes)
    evidence.append(
        VerificationEvidence(
            "readiness_issues",
            report is not None
            and report.get("status") in ("ready", "review")
            and report.get("analysis_truncated") is not True
            and issues is not None
            and len(issue_mappings) == len(issues)
            and len(issue_codes) == len(issues)
            and not forbidden,
            f"status={report.get('status') if report else None!r}, forbidden={sorted(forbidden)!r}",
        )
    )
    return VerificationSummary(tuple(evidence))
