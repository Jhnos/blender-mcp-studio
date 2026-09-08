"""Turning what a real Blender scene reported into a pass or a fail.

Split out of `generated_artifact_contract` because it answers a different question.
That module reads a contract — what the scene is *expected* to be — and this one reads
the scene's own report and decides. The two touch only through the frozen expectation
objects, which is why they can be read separately at all.

Every reader here goes through the narrowing SSOT rather than `isinstance`, and every
verdict is fail-closed: a measurement that did not arrive, arrived short, or arrived in
the wrong shape is a FAIL, never a skip and never a pass. A partial answer that reads as
a green tick is the failure mode this whole file exists to prevent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.infrastructure.narrowing import as_finite_number, as_mapping, as_str
from src.verification.generated_artifact_contract import (
    GeneratedArtifactContract,
    mapping_value,
    sequence_value,
)


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
    rotations = sequence_value(oracle, "rotations_deg")
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
    scene_list = sequence_value(oracle, "scene_list")
    observed_scene_list = tuple(value for value in scene_list or [] if isinstance(value, str))
    evidence.append(
        VerificationEvidence(
            "scene_list",
            observed_scene_list == expected.expected_scene_list,
            f"observed={observed_scene_list!r}, expected={expected.expected_scene_list!r}",
        )
    )
    center_ray_hit = oracle.get("center_ray_hit")
    # Fail-closed on anything that is not an actual boolean: a missing or
    # malformed measurement must never read as agreement with the expectation.
    wants_open = expected.center_channel_expected_open
    evidence.append(
        VerificationEvidence(
            "center_channel",
            isinstance(center_ray_hit, bool) and (center_ray_hit is not wants_open),
            f"center_ray_hit={center_ray_hit!r}, expected "
            f"{'an open channel' if wants_open else 'solid material'} on the axis",
        )
    )

    if expected.bore_probe_points_mm:
        # A short list is a partial answer, and a partial answer must never read as a
        # pass: the count is checked before the misses are.
        hits = sequence_value(oracle, "bore_ray_hits")
        opened = (
            hits is not None
            and len(hits) == len(expected.bore_probe_points_mm)
            and all(hit is False for hit in hits)
        )
        evidence.append(
            VerificationEvidence(
                "open_bores",
                opened,
                f"bore_ray_hits={hits!r}, expected {len(expected.bore_probe_points_mm)} misses",
            )
        )

    collision_records = mapping_value(oracle, "collision_groups")
    for collision in expected.collision_groups:
        record = (
            mapping_value(collision_records, collision.prefix)
            if collision_records is not None
            else None
        )
        count = record.get("object_count") if record is not None else None
        overlaps = sequence_value(record, "adjacent_overlap_pairs") if record is not None else None
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

    if expected.disjoint_groups:
        cross_overlaps = mapping_value(oracle, "cross_group_overlaps")
        # Sorted pairs, so the key is canonical and the order a contract happens
        # to list its groups in never becomes a hidden part of the format.
        wanted_pairs = [
            "|".join(sorted((a, b)))
            for index, a in enumerate(expected.disjoint_groups)
            for b in expected.disjoint_groups[index + 1 :]
        ]
        pair_counts = (
            {key: cross_overlaps.get(key) for key in wanted_pairs}
            if cross_overlaps is not None
            else {}
        )
        # Every declared pair present, and every one of them zero. A pair that
        # never came back is a FAIL: unmeasured is the condition this ends.
        disjoint = cross_overlaps is not None and all(
            type(pair_counts.get(key)) is int and pair_counts.get(key) == 0 for key in wanted_pairs
        )
        evidence.append(
            VerificationEvidence("disjoint_groups", disjoint, f"overlaps={pair_counts!r}")
        )

    selected_count = readiness.get("selected_count")
    if expected.joint_sweep is not None:
        sweep = mapping_value(oracle, "joint_sweep")
        angles = sequence_value(sweep, "angles_deg") if sweep is not None else None
        overlaps = sequence_value(sweep, "overlap_pairs") if sweep is not None else None
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
    bed = contract.readiness.max_footprint_mm
    if bed is not None:
        scene_footprint = sequence_value(readiness, "layout_footprint_mm")
        sides = [as_finite_number(value) for value in scene_footprint or []]
        # Fail-closed: a declared bed with no measurement, or one that came back
        # short or unparseable, is a FAIL. A layout nobody measured is exactly
        # the state this expectation exists to end.
        # Two measurements down independent paths, because one cannot catch
        # itself measuring the wrong thing: the scene read-back once returned a
        # stale `bound_box` and passed a bed check on a box 100 mm too small.
        # The readiness report measures the same objects through the addon.
        report_metrics = mapping_value(mapping_value(readiness, "report") or {}, "metrics")
        second = sequence_value(report_metrics, "dimensions_mm") if report_metrics else None
        second_sides = [as_finite_number(value) for value in (second or [])[:2]]
        agree = (
            len(sides) == 2
            and len(second_sides) == 2
            and all(value is not None for value in (*sides, *second_sides))
            and all(
                abs(a - b) <= 0.5  # type: ignore[operator]
                for a, b in zip(sides, second_sides, strict=True)
            )
        )
        fits = (
            scene_footprint is not None
            and agree
            and all(side <= limit for side, limit in zip(sides, bed, strict=True))  # type: ignore[operator]
        )
        evidence.append(
            VerificationEvidence(
                "layout_fits_bed",
                fits,
                f"scene={scene_footprint!r}, readiness={second_sides!r}, bed={list(bed)!r}",
            )
        )

    report = mapping_value(readiness, "report")
    issues = sequence_value(report, "issues") if report is not None else None
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
