"""A five-armed hand is a palm's worth of constraints the straight V6 chain never had.

The arm is `BiaxialHingeSpec` unchanged — composed, never subclassed, so V6's own
contract stays frozen. What is new is everything the palm imposes: five arm stations
that must not overlap, a wire channel that must clear twenty tendon holes, a tip that
must anchor a drive cable and still leave wall, and a printed envelope that must fit
the machine it is going to be printed on.

The bed limit is a spec invariant rather than a comment because it is the constraint
that chose the print pose: arms splayed flat do not fit 220 mm, arms upright do.
"""

import math

import pytest

from src.core.domain.biaxial_hinge import BiaxialHingeSpec
from src.core.domain.octopus_hand import OctopusHandSpec


def test_pentagon_palm_seats_five_arms_without_letting_them_overlap() -> None:
    spec = OctopusHandSpec()

    assert spec.arm_count == 5
    assert spec.arm_spec == BiaxialHingeSpec(joint_count=4)
    assert spec.arm_station_angles_deg == (0.0, 72.0, 144.0, 216.0, 288.0)
    assert spec.arm_station_radius_mm >= spec.minimum_station_radius_mm
    assert spec.palm_across_corners_mm == pytest.approx(2 * spec.palm_circumradius_mm)
    assert spec.total_tendon_count == 20

    # Neighbouring stations must be at least a full body plus a wall apart.
    first, second = spec.arm_station_positions_mm[:2]
    assert math.dist(first, second) >= spec.arm_spec.body_outer_diameter_mm + spec.palm_wall_mm


def test_upright_pose_fits_the_declared_bed_and_splayed_pose_does_not() -> None:
    """The comparison that chose the print pose, kept as an executable claim."""
    spec = OctopusHandSpec()

    assert spec.upright_footprint_mm <= spec.max_bed_mm
    assert spec.splayed_footprint_mm > spec.max_bed_mm

    # The palm's top face is a body centre plane, so the first arm body sits one
    # full pitch up — the arm gains a base joint the free-standing chain has not.
    assert spec.arm_base_offset_mm == pytest.approx(spec.arm_spec.unit_pitch_mm)
    assert spec.arm_body_count == 5
    assert spec.upright_height_mm == pytest.approx(
        spec.palm_thickness_mm
        + spec.arm_tip_height_mm
        + spec.tip_eyelet_diameter_mm
        + 2 * spec.tip_eyelet_wall_mm
    )
    assert spec.upright_height_mm > spec.arm_spec.assembled_height_mm


def test_every_tip_eyelet_sits_over_its_tendon_exit_and_still_leaves_wall() -> None:
    spec = OctopusHandSpec()
    arm = spec.arm_spec

    assert spec.tip_eyelet_count == len(arm.tendon_positions_mm)
    assert spec.tip_eyelet_radius_mm == pytest.approx(arm.tendon_radius_mm)
    assert (
        spec.tip_eyelet_radius_mm + spec.tip_eyelet_diameter_mm / 2 + spec.tip_eyelet_wall_mm
        <= arm.body_outer_diameter_mm / 2
    )
    # The eyelet must pass the cable the tendon holes carry.
    assert spec.tip_eyelet_diameter_mm > arm.tendon_hole_diameter_mm
    # Upright printing only stays support-free while the claw hangs under 45 degrees.
    assert 0 < spec.tip_claw_slope_deg < 45


def test_central_wire_channel_clears_every_tendon_hole_in_the_palm() -> None:
    spec = OctopusHandSpec()
    arm = spec.arm_spec

    innermost = min(
        math.hypot(x, y) - arm.tendon_hole_diameter_mm / 2 for x, y in spec.tendon_hole_positions_mm
    )
    assert innermost > spec.wire_channel_diameter_mm / 2 + spec.palm_wall_mm
    assert len(spec.tendon_hole_positions_mm) == spec.total_tendon_count
    # Holes belong to the palm disc, not outside it.
    assert all(
        math.hypot(x, y) + arm.tendon_hole_diameter_mm / 2 < spec.palm_inradius_mm
        for x, y in spec.tendon_hole_positions_mm
    )


def test_palm_is_thick_enough_to_carry_the_socket_roots() -> None:
    spec = OctopusHandSpec()
    root_base_height = spec.arm_spec.root_profile_mm[0][0]

    assert spec.palm_thickness_mm >= root_base_height + spec.palm_wall_mm
    assert spec.printable_part_types == ("octopus_palm", "biaxial_arm_body", "octopus_tip")


def test_cable_relief_widens_each_hole_exit_without_reaching_its_neighbour() -> None:
    """The palm's underside relieves twenty cables from a sharp exit edge.

    It is a counterbore, not a chamfer — it moves the bearing edge off the face
    and recesses it; it does not remove the edge.
    """
    spec = OctopusHandSpec()
    arm = spec.arm_spec
    relief_radius = arm.tendon_hole_diameter_mm / 2 + spec.cable_relief_widening_mm

    assert 0 < spec.cable_relief_depth_mm < spec.palm_thickness_mm / 2
    closest = min(
        math.dist(first, second)
        for index, first in enumerate(spec.tendon_hole_positions_mm)
        for second in spec.tendon_hole_positions_mm[index + 1 :]
    )
    assert closest > 2 * relief_radius
    innermost = min(math.hypot(x, y) for x, y in spec.tendon_hole_positions_mm)
    assert innermost - relief_radius > spec.wire_channel_diameter_mm / 2


def test_claw_points_at_the_palm_axis_once_the_arm_is_assembled() -> None:
    """The claw is built in the body's own frame, which the chain has already twisted.

    Bodies alternate 90 degrees up the chain, so the last one does not face the way
    the arm does. Building the claw along a fixed local axis would aim it sideways;
    the heading has to undo the body's own twist.
    """
    spec = OctopusHandSpec()

    assert spec.tip_body_rotation_deg == 90.0
    assert (spec.tip_claw_direction_deg + spec.tip_body_rotation_deg) % 360 == pytest.approx(180.0)
    # Same claim, made where it matters: at every station the claw ends up inward.
    for angle in spec.arm_station_angles_deg:
        heading = (angle + spec.tip_body_rotation_deg + spec.tip_claw_direction_deg) % 360
        assert heading == pytest.approx((angle + 180.0) % 360)


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"arm_count": 2}, id="two arms is not a hand"),
        pytest.param({"arm_count": 9}, id="more stations than the palm can space"),
        pytest.param({"arm_station_radius_mm": 20.0}, id="neighbouring arms would intersect"),
        pytest.param({"max_bed_mm": 90.0}, id="upright envelope exceeds the declared bed"),
        pytest.param(
            {"wire_channel_diameter_mm": 50.0}, id="wire channel swallows the tendon holes"
        ),
        pytest.param({"tip_eyelet_diameter_mm": 9.0}, id="eyelet leaves no wall in the end body"),
        pytest.param(
            {"tip_claw_slope_deg": 60.0}, id="claw would need support when printed upright"
        ),
        pytest.param({"palm_thickness_mm": 3.0}, id="palm too thin to carry the socket roots"),
        pytest.param(
            {"cable_relief_widening_mm": 7.0}, id="cable reliefs would merge into each other"
        ),
        pytest.param({"cable_relief_depth_mm": 5.0}, id="relief eats more than half the palm"),
    ],
)
def test_spec_rejects_geometry_that_cannot_be_built_or_printed(changes) -> None:
    with pytest.raises(ValueError):
        OctopusHandSpec(**changes)
