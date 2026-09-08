from pathlib import Path

import pytest

from src.verification.generated_artifact_contract import (
    build_generator_code,
    contract_from_mapping,
)
from src.verification.generated_artifact_verdict import assess_verification


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


def _green_oracle() -> dict[str, object]:
    return {
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


def test_optional_bore_probes_are_parsed_and_a_blocked_bore_fails(tmp_path: Path) -> None:
    """The centre probe answers one axis. A plate with a bore per arm needs one ray each."""
    mapping = _mapping()
    oracle_mapping = mapping["oracle"]
    assert isinstance(oracle_mapping, dict)
    oracle_mapping["bore_probe_points_mm"] = [[30.0, 0.0], [-24.27, 17.63]]
    contract = contract_from_mapping(mapping, tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}
    readiness = {"selected_count": 3, "report": {"status": "ready", "issues": []}}

    assert contract.oracle.bore_probe_points_mm == ((30.0, 0.0), (-24.27, 17.63))

    passing = assess_verification(
        contract, artifact_state, _green_oracle() | {"bore_ray_hits": [False, False]}, readiness
    )
    assert passing.passed

    blocked = assess_verification(
        contract, artifact_state, _green_oracle() | {"bore_ray_hits": [False, True]}, readiness
    )
    assert not blocked.passed
    assert any(item.name == "open_bores" and not item.passed for item in blocked.evidence)


def test_bore_probes_fail_closed_when_the_scene_reports_too_few(tmp_path: Path) -> None:
    """A short list is a partial answer, and a partial answer must never read as a pass.

    This is the shape that bites: two of the five rays come back, both miss, and a
    verdict that only checked `all(...)` would call an unmeasured bore open.
    """
    mapping = _mapping()
    oracle_mapping = mapping["oracle"]
    assert isinstance(oracle_mapping, dict)
    oracle_mapping["bore_probe_points_mm"] = [[30.0, 0.0], [0.0, 30.0], [-30.0, 0.0]]
    contract = contract_from_mapping(mapping, tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}
    readiness = {"selected_count": 3, "report": {"status": "ready", "issues": []}}

    for hits in ([False, False], None, "no", []):
        summary = assess_verification(
            contract, artifact_state, _green_oracle() | {"bore_ray_hits": hits}, readiness
        )
        assert not summary.passed, hits


def test_a_contract_without_bore_probes_claims_nothing_about_them(tmp_path: Path) -> None:
    """Absent means no claim — the evidence list must not grow an item nobody asked for."""
    contract = contract_from_mapping(_mapping(), tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}
    readiness = {"selected_count": 3, "report": {"status": "ready", "issues": []}}

    summary = assess_verification(contract, artifact_state, _green_oracle(), readiness)

    assert contract.oracle.bore_probe_points_mm == ()
    assert summary.passed
    assert not any(item.name == "open_bores" for item in summary.evidence)


@pytest.mark.parametrize(
    "points",
    [
        pytest.param([], id="an empty list claims nothing but says it does"),
        pytest.param([[1.0]], id="a probe point needs two coordinates"),
        pytest.param([[1.0, 2.0, 3.0]], id="a probe point is not three coordinates"),
        pytest.param([[1.0, "2"]], id="a probe coordinate must be a number"),
        pytest.param([[True, 2.0]], id="a bool is not a coordinate"),
        pytest.param("30,0", id="the points are a list, not a string"),
    ],
)
def test_malformed_bore_probe_points_fail_loudly(points: object, tmp_path: Path) -> None:
    mapping = _mapping()
    oracle_mapping = mapping["oracle"]
    assert isinstance(oracle_mapping, dict)
    oracle_mapping["bore_probe_points_mm"] = points

    with pytest.raises(ValueError):
        contract_from_mapping(mapping, tmp_path)


def _green_oracle(**overrides: object) -> dict[str, object]:
    """The fixture model's passing oracle, with one value swapped at a time."""
    oracle: dict[str, object] = {
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
    oracle.update(overrides)
    return oracle


def _green_readiness() -> dict[str, object]:
    return {"selected_count": 3, "report": {"status": "ready", "issues": []}}


def test_a_model_with_no_central_channel_declares_that_and_is_still_checked(
    tmp_path: Path,
) -> None:
    """Not every repeated part is a hollow tentacle, and a skip would be worse.

    The oracle has always demanded that a ray up the probe object's axis miss —
    right for V1, V2 and V6, whose bodies carry a cable channel down the middle.
    A finger has no such channel, and giving it one would cut straight through
    the pin bores. Making the check optional would let a future contract lose it
    silently, and this project's rule is that a missing measurement is a failure,
    never a skip.

    So the contract declares the expected answer instead. The ray still fires;
    only the expectation moves. "Solid on the axis" is itself an assertion — it
    is what says the tendon bore is offset rather than central.
    """
    mapping = _mapping()
    oracle_mapping = mapping["oracle"]
    assert isinstance(oracle_mapping, dict)
    oracle_mapping["center_channel_expected_open"] = False
    contract = contract_from_mapping(mapping, tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}

    assert contract.oracle.center_channel_expected_open is False

    solid = assess_verification(
        contract, artifact_state, _green_oracle(center_ray_hit=True), _green_readiness()
    )
    assert solid.passed, [item.detail for item in solid.evidence if not item.passed]

    # And it fires the other way: a model declared solid that comes out hollow is
    # a finding, not a shrug.
    hollow = assess_verification(
        contract, artifact_state, _green_oracle(center_ray_hit=False), _green_readiness()
    )
    assert not hollow.passed
    assert any(item.name == "center_channel" and not item.passed for item in hollow.evidence)


def test_the_default_expectation_is_still_an_open_channel(tmp_path: Path) -> None:
    """Every existing contract omits the field, and none of them may change meaning."""
    contract = contract_from_mapping(_mapping(), tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}

    assert contract.oracle.center_channel_expected_open is True
    assert assess_verification(
        contract, artifact_state, _green_oracle(center_ray_hit=False), _green_readiness()
    ).passed
    assert not assess_verification(
        contract, artifact_state, _green_oracle(center_ray_hit=True), _green_readiness()
    ).passed
