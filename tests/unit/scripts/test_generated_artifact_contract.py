from pathlib import Path

import pytest

from src.verification.generated_artifact_contract import (
    assess_verification,
    build_generator_code,
    contract_from_mapping,
)


def _mapping() -> dict[str, object]:
    return {
        "name": "fixture-model",
        "generator_script": "scripts/model_fixture.py",
        "reload_modules": ["scripts.fixture_geometry", "scripts.fixture_render"],
        "artifacts": ["/tmp/fixture/model.blend", "/tmp/fixture/preview.png"],
        "oracle": {
            "object_prefix": "FX_PART_",
            "expected_count": 3,
            "expected_rotations_deg": [0, 90, 0],
            "scene_list_property": "FX_AXES",
            "expected_scene_list": ["J1_X", "J2_Y"],
            "center_probe_object": "FX_PART_1",
            "collision_groups": [
                {"prefix": "FX_PART_", "expected_count": 3},
                {"prefix": "FX_BENT_", "expected_count": 3},
            ],
        },
        "readiness": {
            "selection_prefix": "FX_LAYOUT_",
            "expected_selection_count": 3,
            "forbidden_issue_codes": ["non_manifold_edges", "intersections"],
        },
    }


def test_contract_parser_resolves_paths_and_freezes_repeated_expectations(tmp_path: Path) -> None:
    contract = contract_from_mapping(_mapping(), tmp_path)

    assert contract.name == "fixture-model"
    assert contract.generator_script == tmp_path / "scripts/model_fixture.py"
    assert contract.reload_modules == ("scripts.fixture_geometry", "scripts.fixture_render")
    assert contract.oracle.expected_rotations_deg == (0.0, 90.0, 0.0)
    assert contract.oracle.collision_groups[1].prefix == "FX_BENT_"
    assert contract.readiness.forbidden_issue_codes == (
        "non_manifold_edges",
        "intersections",
    )


def test_generator_code_bootstraps_project_root_before_reloading_modules(tmp_path: Path) -> None:
    contract = contract_from_mapping(_mapping(), tmp_path)

    code = build_generator_code(contract, tmp_path)

    assert str(tmp_path) in code
    assert code.index("sys.path.insert") < code.index("importlib.import_module")
    assert str(contract.generator_script) in code


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("name",), "", "name"),
        (("oracle", "expected_count"), 0, "expected_count"),
        (("readiness", "selection_prefix"), "", "selection_prefix"),
    ],
)
def test_invalid_contracts_fail_loudly(
    tmp_path: Path,
    path: tuple[str, ...],
    value: object,
    message: str,
) -> None:
    mapping = _mapping()
    target: dict[str, object] = mapping
    for key in path[:-1]:
        target = target[key]  # type: ignore[assignment]
    target[path[-1]] = value

    with pytest.raises(ValueError, match=message):
        contract_from_mapping(mapping, tmp_path)


def test_assessment_combines_files_oracle_collision_and_mcp_evidence(tmp_path: Path) -> None:
    contract = contract_from_mapping(_mapping(), tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}
    oracle = {
        "object_count": 3,
        "shared_mesh_count": 1,
        "rotations_deg": [0, 90, 0],
        "scene_list": ["J1_X", "J2_Y"],
        "center_ray_hit": False,
        "collision_groups": {
            "FX_PART_": {"object_count": 3, "adjacent_overlap_pairs": [0, 0]},
            "FX_BENT_": {"object_count": 3, "adjacent_overlap_pairs": [0, 0]},
        },
    }
    readiness = {
        "selected_count": 3,
        "report": {
            "status": "review",
            "issues": [{"code": "overhangs", "severity": "warning"}],
        },
    }

    summary = assess_verification(contract, artifact_state, oracle, readiness)

    assert summary.passed
    assert all(item.passed for item in summary.evidence)


def test_assessment_rejects_a_bent_collision_even_when_mcp_report_is_green(
    tmp_path: Path,
) -> None:
    contract = contract_from_mapping(_mapping(), tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}
    oracle = {
        "object_count": 3,
        "shared_mesh_count": 1,
        "rotations_deg": [0, 90, 0],
        "scene_list": ["J1_X", "J2_Y"],
        "center_ray_hit": False,
        "collision_groups": {
            "FX_PART_": {"object_count": 3, "adjacent_overlap_pairs": [0, 0]},
            "FX_BENT_": {"object_count": 3, "adjacent_overlap_pairs": [0, 7]},
        },
    }
    readiness = {"selected_count": 3, "report": {"status": "ready", "issues": []}}

    summary = assess_verification(contract, artifact_state, oracle, readiness)

    assert not summary.passed
    assert any(item.name == "collision:FX_BENT_" and not item.passed for item in summary.evidence)


def test_optional_joint_sweep_is_parsed_and_missing_samples_fail_closed(tmp_path: Path) -> None:
    mapping = _mapping()
    oracle_mapping = mapping["oracle"]
    assert isinstance(oracle_mapping, dict)
    oracle_mapping["joint_sweep"] = {
        "master_object": "FX_PART_1",
        "pivot_offset_mm": 10.0,
        "axis": "X",
        "mating_twist_deg": 90.0,
        "angles_deg": [-34.0, 0.0, 34.0],
    }
    contract = contract_from_mapping(mapping, tmp_path)

    assert contract.oracle.joint_sweep is not None
    assert contract.oracle.joint_sweep.angles_deg == (-34.0, 0.0, 34.0)
    for sweep in (
        None,
        {"angles_deg": [-34, 0], "overlap_pairs": [0, 0]},
        {"angles_deg": [-34, 0, 34], "overlap_pairs": [0, 0, 2]},
    ):
        summary = assess_verification(contract, {}, {"joint_sweep": sweep}, {})
        assert any(item.name == "joint_sweep" and not item.passed for item in summary.evidence)

    summary = assess_verification(
        contract,
        {},
        {"joint_sweep": {"angles_deg": [-34, 0, 34], "overlap_pairs": [0, 0, 0]}},
        {},
    )
    assert any(item.name == "joint_sweep" and item.passed for item in summary.evidence)


@pytest.mark.parametrize(
    "report",
    [
        {},
        {"status": "invalid", "issues": []},
        {"status": "ready", "issues": [], "analysis_truncated": True},
    ],
)
def test_readiness_cannot_pass_when_invalid_incomplete_or_truncated(
    tmp_path: Path,
    report: dict[str, object],
) -> None:
    contract = contract_from_mapping(_mapping(), tmp_path)

    summary = assess_verification(contract, {}, {}, {"report": report})

    assert any(item.name == "readiness_issues" and not item.passed for item in summary.evidence)
