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
    assert spec.upright_height_mm == pytest.approx(spec.palm_thickness_mm + spec.arm_tip_height_mm)
    assert spec.upright_height_mm > spec.arm_spec.assembled_height_mm


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


def test_grip_pads_sit_only_where_no_joint_hardware_does() -> None:
    """Pads go on the four plain diagonals, which is also the rotation-invariant choice.

    Ears occupy the cardinal directions — male on X above, female on Y below — so the
    diagonals are the only free rim. They are also unchanged by the chain's ninety
    degree twist, so every body presents the same pad pattern whatever its own twist.
    """
    spec = OctopusHandSpec()
    arm = spec.arm_spec

    assert spec.grip_pad_angles_deg == (45.0, 135.0, 225.0, 315.0)
    assert len(spec.grip_pad_angles_deg) == len(arm.tendon_positions_mm)
    for angle in spec.grip_pad_angles_deg:
        assert angle % 90 != 0, "a pad on a cardinal direction would land on an ear"
    assert spec.grip_outer_diameter_mm > arm.body_outer_diameter_mm
    assert spec.grip_pad_projection_mm == pytest.approx(
        (spec.grip_outer_diameter_mm - arm.body_outer_diameter_mm) / 2
    )
    # The pad grows the rim outward past the tendon holes, never into them.
    assert spec.grip_outer_diameter_mm / 2 - arm.tendon_radius_mm > arm.tendon_hole_diameter_mm


def test_grip_pads_do_not_push_the_arms_into_each_other() -> None:
    """Growing the grip surface has to move the stations out, or the arms touch."""
    spec = OctopusHandSpec()

    assert spec.arm_station_radius_mm >= spec.minimum_station_radius_mm
    first, second = spec.arm_station_positions_mm[:2]
    # The pad's flat face is its *closest* point, not its farthest: the corners of
    # the chord sit further out than the face does. Spacing the arms on the face
    # radius let neighbouring pads intersect at their corners.
    assert spec.grip_envelope_radius_mm > spec.grip_outer_diameter_mm / 2
    assert math.dist(first, second) >= 2 * spec.grip_envelope_radius_mm + spec.palm_wall_mm
    assert spec.upright_footprint_mm <= spec.max_bed_mm


def test_grip_pad_underside_is_self_supporting_when_printed_upright() -> None:
    """A pad standing proud of a vertical disc would otherwise be a flat overhang."""
    spec = OctopusHandSpec()

    assert 0 < spec.grip_pad_slope_deg <= 45
    assert spec.grip_flat_face_height_mm > 0, "the chamfer ate the whole gripping face"
    assert spec.grip_flat_face_height_mm < spec.grip_pad_height_mm


def test_tip_is_a_terminal_polyhedron_not_a_body_with_parts_glued_on() -> None:
    """The tip ends the chain, so it keeps no ears it cannot use.

    Everything above the disc's top face is replaced by a faceted frustum: flat faces
    to press on an object, and a profile that never overhangs when printed upright.
    """
    spec = OctopusHandSpec()

    assert spec.tip_facet_count == 6
    assert spec.tip_cap_top_diameter_mm < spec.grip_outer_diameter_mm
    # Widens off the disc at a self-supporting slope, then only ever narrows.
    assert 0 < spec.tip_cap_flare_slope_deg <= 45
    # The cap must start strictly inside the disc. A base face flush with the disc's
    # own surface leaves coplanar geometry for the Boolean, which is where the
    # readiness check found non-manifold edges.
    assert spec.tip_cap_base_z_mm < spec.tip_feature_base_z_mm
    assert spec.tip_cap_base_radius_mm < spec.arm_spec.body_outer_diameter_mm / 2
    assert spec.tip_cap_taper_slope_deg < 90, "a frustum that widens upward would overhang"
    assert spec.tip_cap_top_z_mm > spec.tip_cap_shoulder_z_mm > spec.tip_feature_base_z_mm


def test_tip_cable_bores_cross_every_tendon_inside_the_cap() -> None:
    """Two through-bores, four cables: each one turns once and is tied through a ring."""
    spec = OctopusHandSpec()
    arm = spec.arm_spec

    assert len(spec.tip_cable_bore_angles_deg) == 2
    assert spec.tip_cable_bore_z_mm > spec.tip_cap_shoulder_z_mm
    # The bore has to be low enough that the tapering cap still has material at the
    # tendon radius, or it would break out of the side instead of crossing the cable.
    assert spec.tip_cap_radius_at_mm(spec.tip_cable_bore_z_mm) > arm.tendon_radius_mm
    assert spec.tip_cable_bore_diameter_mm > arm.tendon_hole_diameter_mm


def test_tip_features_stay_clear_of_the_joint_the_tip_actually_hangs_from() -> None:
    """Nothing mates above a tip, so the joint that matters is the one below it.

    The eyelets and claw are all built above the body's mid-plane, which is what
    keeps them out of the female ears the tip closes on body four with. This is
    the check that replaces a sweep of the tip against a copy of itself — that
    sweep measured a joint the hand does not have.
    """
    spec = OctopusHandSpec()
    arm = spec.arm_spec

    lower_joint_z = -arm.joint_center_offset_mm
    assert spec.tip_feature_base_z_mm > 0, "features must not cross the body's mid-plane"
    clearance = spec.tip_feature_base_z_mm - (lower_joint_z + arm.lug_outer_diameter_mm / 2)
    assert clearance > 0, "tip features reach into the ear below them"
    # The cap must not reach past the grip envelope the stations were spaced for.
    assert spec.tip_cap_max_radius_mm <= spec.grip_outer_diameter_mm / 2


def test_the_one_piece_export_has_to_contain_every_printed_part() -> None:
    """A print-in-place hand whose pins are missing prints as a pile of loose discs.

    The pins are separate objects in the scene, so an export list built from the
    palm and the bodies alone looks complete and slices without complaint — every
    joint just comes out as an empty bore.
    """
    spec = OctopusHandSpec()

    assert spec.printed_body_count == spec.arm_count * spec.arm_body_count
    assert spec.printed_pin_count == 2 * spec.printed_body_count
    assert spec.printed_part_count == 1 + spec.printed_body_count + spec.printed_pin_count
    assert spec.printed_part_count == 76


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"arm_count": 2}, id="two arms is not a hand"),
        pytest.param({"arm_count": 9}, id="more stations than the palm can space"),
        pytest.param({"arm_station_radius_mm": 20.0}, id="neighbouring arms would intersect"),
        pytest.param({"max_bed_mm": 90.0}, id="upright envelope exceeds the declared bed"),
        pytest.param(
            {"wire_channel_diameter_mm": 70.0}, id="wire channel swallows the tendon holes"
        ),
        pytest.param({"grip_outer_diameter_mm": 36.0}, id="grip pad flush with the body"),
        pytest.param({"grip_pad_arc_deg": 95.0}, id="grip pads would run into each other"),
        pytest.param({"grip_pad_slope_deg": 70.0}, id="pad underside would need support"),
        pytest.param({"grip_pad_height_mm": 2.0}, id="chamfer eats the whole gripping face"),
        pytest.param({"tip_cap_top_diameter_mm": 44.0}, id="cap widens instead of tapering"),
        pytest.param({"tip_cap_flare_mm": 0.5}, id="cap flare would need support"),
        pytest.param(
            {"tip_cap_top_diameter_mm": 2.0}, id="cap tapers so hard the bore misses the tendons"
        ),
        pytest.param({"tip_cable_bore_diameter_mm": 1.0}, id="bore too small for the cable"),
        pytest.param({"palm_thickness_mm": 3.0}, id="palm too thin to carry the socket roots"),
        pytest.param(
            {"cable_relief_widening_mm": 9.0}, id="cable reliefs would merge into each other"
        ),
        pytest.param({"cable_relief_depth_mm": 5.0}, id="relief eats more than half the palm"),
    ],
)
def test_spec_rejects_geometry_that_cannot_be_built_or_printed(changes) -> None:
    with pytest.raises(ValueError):
        OctopusHandSpec(**changes)
