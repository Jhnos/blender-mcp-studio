"""Closed screen revision intent; existing rigid parts, explicit preparation only."""

from dataclasses import FrozenInstanceError
from math import pi

import pytest

from src.core.domain.native_revision import NativeRevisionError, parse_native_revision
from src.core.planning.screen_revision_plan import plan_screen_revision


@pytest.mark.parametrize("target", [0, 15, 30, 45, 60])
def test_registered_request_reuses_the_existing_indexed_motion(target):
    request = parse_native_revision({"recipe_id": "screen-clamp", "target_angle_deg": target})
    assert request.clamp.sequence.target_angle_deg == target
    assert request.clamp.sequence.release_mm == 2.2
    assert request.clamp.sequence.screw_mm == 2.4
    with pytest.raises(FrozenInstanceError):
        request.recipe_id = "arbitrary"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"recipe_id": "unknown"},
        {"recipe_id": "screen-clamp", "code": "print(1)"},
        {"recipe_id": "screen-clamp", "source": "archive.blend"},
        {"recipe_id": "screen-clamp", "output": "overwrite.blend"},
        *(
            {"recipe_id": "screen-clamp", "target_angle_deg": angle}
            for angle in [True, "15", 1, -15, 75, float("nan"), float("inf"), 10**1000]
        ),
    ],
)
def test_invalid_intent_has_no_code_path_or_version_escape(payload):
    with pytest.raises(NativeRevisionError):
        parse_native_revision(payload)


def test_plan_modifies_two_existing_parts_and_names_every_source_preparation():
    plan = plan_screen_revision((0, -49, 124))
    assert plan.modified_owners == ("LS_FIT_lcd_back", "LS_FIT_lid")
    assert plan.triangulate_owners == (
        "RH_-101_M3_screw",
        "RH_101_M3_screw",
        "S_capillary_yaw_bolt",
    )
    assert plan.wrist_owner == "TE_pH_temp_three_point_wrist"
    assert plan.bore.axis == "X" and plan.bore.radius_mm == 3
    assert plan.bore.center_mm == (-68.75, -49, 124)
    assert plan.bore.height_mm == 5.5 and plan.bore.segments == 96
    assert plan.bore_phase_rad == pi / 192  # Half a half-segment, matching qualified research.
    assert len(plan.stop_rings_mm) == 2 and all(len(ring) == 5 for ring in plan.stop_rings_mm)
    first, second = plan.stop_rings_mm
    assert {p[1] for p in first} == {-54.25} and {p[1] for p in second} == {-50.25}
    # The underside gains one mm of height per one mm of inward travel.
    assert first[4][0] - first[3][0] == -1
    assert first[4][2] - first[3][2] == 1
    assert max(p[0] for p in first) == 83.5  # Positive overlap with the original x=83 wall.


def test_the_measured_hinge_pivot_translates_both_tools_without_changing_the_profile():
    a, b = plan_screen_revision((0, -49, 124)), plan_screen_revision((0, -39, 121))
    assert b.bore.center_mm == (
        a.bore.center_mm[0],
        a.bore.center_mm[1] + 10,
        a.bore.center_mm[2] - 3,
    )
    for ring_a, ring_b in zip(a.stop_rings_mm, b.stop_rings_mm, strict=True):
        for p, q in zip(ring_a, ring_b, strict=True):
            assert q == (p[0], p[1] + 10, p[2] - 3)


@pytest.mark.parametrize("pivot", [(1, -49, 124), (0, float("nan"), 124), (0, -49), (0, -49, True)])
def test_incompatible_or_invalid_hinge_frames_are_rejected(pivot):
    with pytest.raises(NativeRevisionError):
        plan_screen_revision(pivot)


def test_plan_names_the_existing_controller_and_four_original_hardware_roles():
    plan = plan_screen_revision((0, -49, 124))
    assert plan.control_owner == "整機_螢幕收折"
    assert plan.clamp_owners == (
        "S_SCREEN_bolt_-1",
        "S_SCREEN_nut_-1",
        "S_SCREEN_bolt_1",
        "S_SCREEN_nut_1",
    )
