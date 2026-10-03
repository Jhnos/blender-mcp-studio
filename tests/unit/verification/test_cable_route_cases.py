"""The declared matrix is the coverage contract, independent of Blender execution."""

from pathlib import Path

import pytest

from src.core.domain.cable_paths import sample_path
from src.verification.cable_route_cases import CONTACT_CASES, ROUTE_CASES, ContactProbe
from src.verification.generator_imports import reload_modules_for
from src.verification.scenario_runner import Observation, Scenario, require_complete, run_scenarios


@pytest.mark.parametrize("case", CONTACT_CASES, ids=lambda case: case.name)
def test_contact_fixture_path_matches_declared_terminals(case: Scenario[ContactProbe]) -> None:
    sampled = sample_path((*case.inputs.prefix, case.inputs.curve))
    assert sampled.points_mm[0] == case.inputs.boundary.start_mm
    assert sampled.points_mm[-1] == case.inputs.boundary.end_mm
    assert case.expected in {
        "clear",
        "envelope_contact",
        "start_inside",
        "terminal_not_on_outward_face",
        "nonlocal_self_contact",
    }


def test_route_matrix_retains_both_heads_channels_and_lift_endpoints() -> None:
    assert [
        (c.inputs.head, c.inputs.channel, c.inputs.length_mm, c.inputs.lift_mm) for c in ROUTE_CASES
    ] == [
        ("capillary", 0, 220, 0),
        ("capillary", 0, 220, 100),
        ("pH_temp", 0, 150, 0),
        ("pH_temp", 1, 150, 0),
    ]
    assert all(c.expected == "found" for c in ROUTE_CASES)
    assert len({c.name for c in ROUTE_CASES}) == 4


def test_new_contact_case_is_consumed_without_changing_runner() -> None:
    extra = Scenario("another_clearance", CONTACT_CASES[0].inputs, "clear")
    cases = (CONTACT_CASES[0], extra)
    observed: list[ContactProbe] = []

    def measure(probe: ContactProbe) -> Observation:
        observed.append(probe)
        return Observation("clear", {})

    rows = run_scenarios(cases, measure, lambda _: None)
    require_complete(cases, rows)
    assert len(observed) == 2
    assert rows[-1].evidence.name == "another_clearance"


def test_real_bootstrap_reloads_cases_runner_and_production_measurements() -> None:
    root = Path(__file__).resolve().parents[3]
    closure = reload_modules_for(root, root / "scripts/verify/lab_cable_route_checks.py")
    assert {
        "src.verification.cable_route_cases",
        "src.verification.scenario_runner",
        "scripts.lab_cable_routes",
        "scripts.model_lab_platform",
    } <= set(closure)


def test_bundle_catalog_covers_all_three_channels_and_independent_lifts() -> None:
    from src.verification.cable_route_cases import (
        BUNDLE_CASES,
        BUNDLE_ROUTES,
        PAIR_CASES,
        registered_suites,
    )

    assert [(c.inputs.capillary_lift_mm, c.inputs.ph_temp_lift_mm) for c in BUNDLE_CASES[:3]] == [
        (0, 0),
        (100, 0),
        (0, 100),
    ]
    assert [(r.head, r.channel, r.length_mm) for r in BUNDLE_ROUTES] == [
        ("capillary", 0, 220),
        ("pH_temp", 0, 170),
        ("pH_temp", 1, 170),
    ]
    assert BUNDLE_CASES[-1].expected == "not_found"
    assert BUNDLE_CASES[-1].inputs.obstruction_radius_mm == 500
    assert {c.expected for c in PAIR_CASES} == {"clear", "wire_contact"}
    catalog = {s.suite_id: s for s in registered_suites()}
    assert catalog["electrode-head-bundle"].cases == tuple(
        (c.name, c.expected) for c in BUNDLE_CASES
    )
    assert len(catalog["cable-contact-controls"].cases) == len(CONTACT_CASES) + len(PAIR_CASES)


def test_full_chain_matrix_keeps_three_ordered_segments_per_wire() -> None:
    from src.verification.cable_route_cases import CHAIN_CASES, CHAIN_ROUTES, registered_suites

    assert len(CHAIN_ROUTES) == 9
    for start in (0, 3, 6):
        wire = CHAIN_ROUTES[start : start + 3]
        assert [r.segment for r in wire] == ["base", "joint", "head"]
        assert len({(r.head, r.channel) for r in wire}) == 1
    assert [(c.inputs.capillary_lift_mm, c.inputs.ph_temp_lift_mm) for c in CHAIN_CASES] == [
        (0, 0),
        (100, 0),
        (0, 100),
    ]
    assert all(c.inputs.routes == CHAIN_ROUTES and c.expected == "found" for c in CHAIN_CASES)
    assert next(
        s for s in registered_suites() if s.suite_id == "electrode-full-chains"
    ).cases == tuple((c.name, c.expected) for c in CHAIN_CASES)


def test_motion_cases_require_middle_samples_and_blocked_control() -> None:
    from src.verification.cable_route_cases import MOTION_CASES, registered_suites

    assert [c.expected for c in MOTION_CASES] == ["clear", "blocked"]
    assert all(
        tuple(p.lift_mm for p in c.inputs.points if p.path == "lift") == tuple(range(0, 101, 10))
        for c in MOTION_CASES
    )
    assert [c.inputs.insert_obstacle for c in MOTION_CASES] == [False, True]
    assert next(
        s for s in registered_suites() if s.suite_id == "electrode-cable-motion"
    ).cases == tuple((c.name, c.expected) for c in MOTION_CASES)


def test_motion_matrix_preserves_paths_coordinates_and_saved_wire_identity() -> None:
    from src.verification.cable_route_cases import CHAIN_ROUTES, MOTION_CASES, MotionPoint

    for scenario in MOTION_CASES:
        points = scenario.inputs.points
        assert [(p.forward_mm, p.lift_mm) for p in points if p.path == "lift"] == [
            (0, lift) for lift in range(0, 101, 10)
        ]
        assert [(p.forward_mm, p.lift_mm) for p in points if p.path == "raised-reach"] == [
            (f, 100) for f in range(-20, 21, 5)
        ]
        assert [(p.forward_mm, p.lift_mm) for p in points if p.path == "mixed"] == [
            (2 * i, 10 * i) for i in range(11)
        ]
        assert len(scenario.inputs.families) == len(CHAIN_ROUTES)
        assert len({f.name for f in scenario.inputs.families}) == 9
        assert [f.length_mm for f in scenario.inputs.families] == [
            r.length_mm for r in CHAIN_ROUTES
        ]
    assert MOTION_CASES[0].inputs.families == MOTION_CASES[1].inputs.families
    with pytest.raises(ValueError):
        MotionPoint("mixed", float("nan"), 100)
    with pytest.raises(ValueError):
        MotionPoint("", 0, 0)
