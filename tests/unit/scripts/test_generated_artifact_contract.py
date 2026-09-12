from pathlib import Path

import pytest

from src.verification.generated_artifact_bootstrap import build_generator_code
from src.verification.generated_artifact_contract import (
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


def test_a_layout_that_overruns_the_bed_fails_and_a_silent_one_fails_too() -> None:
    """Whether the plate fits is the first thing a person finds out, in a slicer.

    It was carried only in prose, and the prose said 182.5 × 100.5 across five
    parts long after the layout became four parts at 242.0 × 103.5 — the margin
    against a 256 mm bed had fallen from 73 mm to 14 mm and no machine anywhere
    knew. Declared here, so a part getting wider fails a gate instead of failing
    a print.

    Fail-closed, like every other expectation in this file: a contract that
    declares a bed and gets no measurement back is a FAIL, never a skip.
    """
    mapping = _mapping()
    mapping["readiness"]["max_footprint_mm"] = [256.0, 256.0]  # type: ignore[index]
    contract = contract_from_mapping(mapping, Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}

    assert contract.readiness.max_footprint_mm == (256.0, 256.0)

    def _readiness(footprint: list[float]) -> dict[str, object]:
        # Both measurements, because the check needs a second opinion — see
        # `test_the_bed_check_needs_two_measurements_that_agree`.
        return {
            "selected_count": 3,
            "layout_footprint_mm": footprint,
            "report": {
                "status": "ready",
                "issues": [],
                "metrics": {"dimensions_mm": [*footprint, 44.0]},
            },
        }

    fits = assess_verification(
        contract, artifact_state, _green_oracle(), _readiness([242.0, 103.5])
    )
    assert fits.passed
    assert any(item.name == "layout_fits_bed" and item.passed for item in fits.evidence)

    overruns = assess_verification(
        contract, artifact_state, _green_oracle(), _readiness([256.1, 103.5])
    )
    assert not overruns.passed

    silent = assess_verification(contract, artifact_state, _green_oracle(), _green_readiness())
    assert not silent.passed, "a declared bed with no measurement is a FAIL, not a skip"


def test_a_contract_without_a_bed_claims_nothing_about_the_layout_size() -> None:
    contract = contract_from_mapping(_mapping(), Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}

    summary = assess_verification(contract, artifact_state, _green_oracle(), _green_readiness())

    assert contract.readiness.max_footprint_mm is None
    assert summary.passed
    assert not any(item.name == "layout_fits_bed" for item in summary.evidence)


def test_the_bed_check_needs_two_measurements_that_agree() -> None:
    """One measurement cannot catch itself measuring the wrong thing.

    The first version of this gate read `bound_box`, which is a cache that an
    in-place `data.transform()` does not invalidate. It returned 140 x 44 — the
    palm's own box before it was laid flat — for a layout that is 242.0 x 103.5,
    and the gate passed, which is worse than having no gate. The readiness
    report measures the same objects down an independent path, so the two are
    required to agree before either is believed.
    """
    mapping = _mapping()
    mapping["readiness"]["max_footprint_mm"] = [256.0, 256.0]  # type: ignore[index]
    contract = contract_from_mapping(mapping, Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}

    def _assess(scene: list[float], report_dims: list[float] | None) -> bool:
        report: dict[str, object] = {"status": "ready", "issues": []}
        if report_dims is not None:
            report["metrics"] = {"dimensions_mm": report_dims}
        readiness = {
            "selected_count": 3,
            "layout_footprint_mm": scene,
            "report": report,
        }
        return assess_verification(contract, artifact_state, _green_oracle(), readiness).passed

    assert _assess([242.0, 103.5], [242.0, 103.5, 44.0])
    assert not _assess([140.0, 44.0], [242.0, 103.5, 44.0]), "the two disagree; believe neither"
    assert not _assess([242.0, 103.5], None), "no second opinion is not a pass"


def test_groups_declared_disjoint_must_be_measured_disjoint() -> None:
    """Collision groups compare adjacent units inside one digit — and nothing else.

    The thumb crosses in front of the whole finger row, and the only things
    standing behind "no interference between any two fingers" were a per-digit
    adjacency check and an analytic pitch-versus-width assertion that the thumb
    is not part of. The layout's `intersections` code covers the print plate,
    not the assembled hand. So the one digit that can hit another was the one
    digit nothing measured against another.

    Declared pairs are measured on the real mesh; a pair that comes back
    missing is a FAIL, because an unmeasured pair is the state this exists to
    end.
    """
    mapping = _mapping()
    mapping["oracle"]["disjoint_groups"] = ["FX_PART_", "FX_BENT_"]  # type: ignore[index]
    contract = contract_from_mapping(mapping, Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}
    assert contract.oracle.disjoint_groups == ("FX_PART_", "FX_BENT_")

    def _assess(overlaps: object) -> bool:
        oracle = _green_oracle() | {"cross_group_overlaps": overlaps}
        return assess_verification(contract, artifact_state, oracle, _green_readiness()).passed

    assert _assess({"FX_BENT_|FX_PART_": 0})
    assert not _assess({"FX_BENT_|FX_PART_": 7}), "touching digits are not disjoint"
    assert not _assess({}), "a declared pair with no measurement is a FAIL"
    assert not _assess(None), "no measurement at all is a FAIL"


def test_a_contract_declaring_no_disjoint_groups_claims_nothing() -> None:
    contract = contract_from_mapping(_mapping(), Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}

    summary = assess_verification(contract, artifact_state, _green_oracle(), _green_readiness())

    assert contract.oracle.disjoint_groups == ()
    assert summary.passed
    assert not any(item.name == "disjoint_groups" for item in summary.evidence)


def test_a_channel_probe_needs_a_hit_and_a_miss_to_mean_anything() -> None:
    """F12 was written down and its check was never built.

    "The air port is blocked by internal structure → no air goes in, and it
    looks identical from outside" is in the failure-mode table with `射線探針`
    beside it. The contract only ever probed the finger. So the palm's five
    tendon channels and its air port were claimed open in the package README
    and measured by nothing.

    A ray that misses proves a bore is open only if a ray a few millimetres
    away hits — otherwise "open" and "aimed at empty air" are the same reading.
    This project has already shipped a probe that reported five open bores
    through nothing at all, so both halves are mandatory here.
    """
    mapping = _mapping()
    mapping["oracle"]["channel_probes"] = [  # type: ignore[index]
        {
            "object": "FX_PLATE",
            "axis": "Z",
            "open_points_mm": [[-45.0, -6.6], [15.0, -6.6]],
            "solid_points_mm": [[-30.0, -6.6]],
        }
    ]
    contract = contract_from_mapping(mapping, Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}
    assert len(contract.oracle.channel_probes) == 1

    def _assess(result: object) -> bool:
        oracle = _green_oracle() | {"channel_probe_results": result}
        return assess_verification(contract, artifact_state, oracle, _green_readiness()).passed

    assert _assess({"FX_PLATE|Z": {"open": [False, False], "solid": [True]}})
    assert not _assess({"FX_PLATE|Z": {"open": [False, True], "solid": [True]}}), "a blocked bore"
    assert not _assess({"FX_PLATE|Z": {"open": [False, False], "solid": [False]}}), (
        "nothing was hit, so the misses were through empty air"
    )
    assert not _assess({"FX_PLATE|Z": {"open": [False], "solid": [True]}}), "a probe went missing"
    assert not _assess({}), "declared and unmeasured is a FAIL"
    assert not _assess(None)


def test_a_channel_probe_without_a_solid_control_is_refused_at_parse_time() -> None:
    """The vacuous half cannot be optional, so the parser will not accept it."""
    mapping = _mapping()
    mapping["oracle"]["channel_probes"] = [  # type: ignore[index]
        {"object": "FX_PLATE", "axis": "Z", "open_points_mm": [[0.0, 0.0]], "solid_points_mm": []}
    ]
    with pytest.raises(ValueError):
        contract_from_mapping(mapping, Path("/tmp"))


def test_a_part_that_arrives_in_two_pieces_fails_even_though_both_are_watertight() -> None:
    """Every V3 phalanx shipped as two disconnected solids, and everything was green.

    The male tongue is a bare disc at the joint centre. When that centre moved
    from 24 to 27 mm — the fix for adjacent bodies interpenetrating — the disc
    went with it and left its own body 0.5 mm behind. The female fork has a neck
    box joining lug to body; the male end never had one.

    Nothing saw it. Both pieces are watertight and manifold, so the mesh gates
    passed. Adjacent units overlap by zero, so the collision groups passed —
    more comfortably than before. Triangle counts matched the numbers recorded
    from the broken build. It took a person looking at a picture.

    So the count that no per-face check can see gets declared: how many separate
    solids a part is allowed to be.
    """
    mapping = _mapping()
    mapping["oracle"]["expected_shells_per_object"] = 1  # type: ignore[index]
    contract = contract_from_mapping(mapping, Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}
    assert contract.oracle.expected_shells_per_object == 1

    def _assess(counts: object) -> bool:
        oracle = _green_oracle() | {"shell_counts": counts}
        return assess_verification(contract, artifact_state, oracle, _green_readiness()).passed

    whole = {"FX_PART_1": 1, "FX_PART_2": 1, "FX_PART_3": 1}
    assert _assess(whole)
    assert not _assess(whole | {"FX_PART_2": 2}), "a part in two pieces is not a part"
    assert not _assess({"FX_PART_1": 1}), "a part that went unmeasured is a FAIL"
    assert not _assess({}), "declared and unmeasured is a FAIL"
    assert not _assess(None)


def test_a_contract_that_declares_no_shell_count_claims_nothing() -> None:
    contract = contract_from_mapping(_mapping(), Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}

    summary = assess_verification(contract, artifact_state, _green_oracle(), _green_readiness())

    assert contract.oracle.expected_shells_per_object is None
    assert summary.passed
    assert not any(item.name == "one_solid_per_part" for item in summary.evidence)


def test_a_closing_finger_is_swept_as_one_motion_not_one_joint_at_a_time() -> None:
    """PS-2's artifact half: joints that are each clear can still meet together.

    The existing sweep turns one joint through its whole travel and counts
    overlaps. That proves each joint's arc is clear in isolation, which is not
    the same claim as "the finger can close": two joints each half-flexed put
    surfaces somewhere neither of them visits alone.

    The trajectory is the one the spring gradient predicts — the base joint
    leads, the distal follows at its travel share — so this also checks that the
    ordering the spec computes describes a motion the geometry can actually
    perform.
    """
    mapping = _mapping()
    mapping["oracle"]["closure_trajectory"] = {  # type: ignore[index]
        "chain_prefix": "FX_PART_",
        "pivot_offset_mm": 27.0,
        "axis": "X",
        "travel_shares": [1.0, 0.625],
        "full_travel_deg": 50.0,
        "steps": 6,
    }
    contract = contract_from_mapping(mapping, Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}

    trajectory = contract.oracle.closure_trajectory
    assert trajectory is not None
    assert trajectory.travel_shares == (1.0, 0.625)
    assert trajectory.steps == 6

    def _assess(overlaps: object) -> bool:
        oracle = _green_oracle() | {"closure_overlaps": overlaps}
        return assess_verification(contract, artifact_state, oracle, _green_readiness()).passed

    assert _assess([0, 0, 0, 0, 0, 0])
    assert not _assess([0, 0, 4, 0, 0, 0]), "the finger meets itself halfway through"
    assert not _assess([0, 0, 0]), "three of six steps is not a swept trajectory"
    assert not _assess([]), "declared and unmeasured is a FAIL"
    assert not _assess(None)


def test_a_trajectory_whose_shares_do_not_lead_from_the_base_is_refused() -> None:
    """The ordering is the point, so a trajectory that inverts it is a mistake."""
    mapping = _mapping()
    mapping["oracle"]["closure_trajectory"] = {  # type: ignore[index]
        "chain_prefix": "FX_PART_",
        "pivot_offset_mm": 27.0,
        "axis": "X",
        "travel_shares": [0.625, 1.0],
        "full_travel_deg": 50.0,
        "steps": 6,
    }
    with pytest.raises(ValueError):
        contract_from_mapping(mapping, Path("/tmp"))


def test_a_contract_without_a_trajectory_claims_nothing_about_closing() -> None:
    contract = contract_from_mapping(_mapping(), Path("/tmp"))
    artifact_state = {str(path): True for path in contract.artifacts}

    summary = assess_verification(contract, artifact_state, _green_oracle(), _green_readiness())

    assert contract.oracle.closure_trajectory is None
    assert not any(item.name == "closure_trajectory" for item in summary.evidence)


def test_a_declared_part_number_count_replaces_the_hard_wired_one(tmp_path: Path) -> None:
    """PS-2: how many part numbers a finger is comes from the instance, not the verdict.

    `shared_mesh == 1` was wired into the verdict. A gradient finger is two
    parts by declaration and would have failed for being what it claims to be.
    """
    mapping = _mapping()
    oracle_mapping = mapping["oracle"]
    assert isinstance(oracle_mapping, dict)
    oracle_mapping["expected_shared_mesh_count"] = 2
    contract = contract_from_mapping(mapping, tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}

    assert contract.oracle.expected_shared_mesh_count == 2
    two = assess_verification(
        contract, artifact_state, _green_oracle(shared_mesh_count=2), _green_readiness()
    )
    assert two.passed, [item.detail for item in two.evidence if not item.passed]
    one = assess_verification(
        contract, artifact_state, _green_oracle(shared_mesh_count=1), _green_readiness()
    )
    assert not one.passed
    assert any(item.name == "shared_mesh" and not item.passed for item in one.evidence)


def test_the_default_part_number_count_is_still_one(tmp_path: Path) -> None:
    """Every committed contract omits the field, and none of them may change meaning."""
    contract = contract_from_mapping(_mapping(), tmp_path)
    artifact_state = {str(path): True for path in contract.artifacts}

    assert contract.oracle.expected_shared_mesh_count == 1
    assert not assess_verification(
        contract, artifact_state, _green_oracle(shared_mesh_count=2), _green_readiness()
    ).passed


def test_a_part_number_count_of_zero_is_refused(tmp_path: Path) -> None:
    mapping = _mapping()
    oracle_mapping = mapping["oracle"]
    assert isinstance(oracle_mapping, dict)
    oracle_mapping["expected_shared_mesh_count"] = 0

    with pytest.raises(ValueError):
        contract_from_mapping(mapping, tmp_path)


def test_oracle_orders_mixed_numbered_and_named_parts_without_type_error(tmp_path: Path) -> None:
    import ast
    import re
    from types import SimpleNamespace

    from src.verification.generated_artifact_oracle import oracle_code

    source = oracle_code(contract_from_mapping(_mapping(), tmp_path))
    function = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "natural_key"
    )
    namespace = {"re": re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "oracle_key", "exec"), namespace)
    key = namespace["natural_key"]
    assert callable(key)
    objects = [SimpleNamespace(name=name) for name in ("FX_cap", "FX_10", "FX_2")]
    assert [obj.name for obj in sorted(objects, key=key)] == ["FX_2", "FX_10", "FX_cap"]
