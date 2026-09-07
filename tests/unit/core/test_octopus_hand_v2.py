"""V2 moves the pentagon's corners onto the arms, which changes what sizes the palm.

V1 sized the palm by its flats, because a flat faced every arm: material had to reach
past a socket standing on an edge. That put the thickest material — the corners — in
the empty sectors between arms, and the thinnest against the socket that loads it.

V2 turns the pentagon so a corner stands on each arm heading. The socket then sits
where the plate is deepest, and the edges only have to clear it at 36 degrees off the
heading, which is a shorter reach: the palm gets smaller while the arm gets more
material behind it. That is the whole claim of this file, and it is checked as a
comparison against V1 rather than against a copied constant.

V1 is a controlled delivery. The last test here is the gate that proves V2 did not
reach into it.
"""

import math

import pytest

from src.core.domain.biaxial_hinge import BiaxialHingeSpec
from src.core.domain.octopus_hand import OctopusHandSpec
from src.core.domain.octopus_hand_v2 import OctopusHandV2Spec


def test_v2_keeps_the_whole_arm_contract_v1_and_v6_already_froze() -> None:
    """Only the palm changes. The arm, its grip surfaces and its tip are V1's."""
    spec = OctopusHandV2Spec()

    assert spec.arm_spec == BiaxialHingeSpec(joint_count=4)
    assert spec.arm_count == 5
    assert spec.arm_station_angles_deg == (0.0, 72.0, 144.0, 216.0, 288.0)
    assert spec.arm_station_radius_mm == pytest.approx(OctopusHandSpec().arm_station_radius_mm)
    assert spec.total_tendon_count == 20
    assert spec.printed_part_count == 76
    assert spec.printable_part_types == ("octopus_palm", "biaxial_arm_body", "octopus_tip")


def test_declared_bed_is_the_p2s_the_hand_is_actually_going_to_be_printed_on() -> None:
    """The bed is a spec invariant because it is what chose the print pose.

    V1 declared 220 mm. The machine is a Bambu Lab P2S at 256 mm, and a bed
    declared smaller than the real one rejects poses the printer could take.
    """
    spec = OctopusHandV2Spec()

    assert spec.max_bed_mm == 256.0
    assert spec.upright_footprint_mm <= spec.max_bed_mm
    assert spec.splayed_footprint_mm > spec.max_bed_mm


def test_pentagon_corners_stand_on_the_arm_headings_instead_of_between_them() -> None:
    """The corner is the arm's, not the empty sector's.

    V1's corners fell 18 degrees off every arm — an artefact of the phase Blender's
    five-sided cylinder happens to start at, not a decision. Each arm therefore stood
    on an edge, where the plate is shallowest.
    """
    spec = OctopusHandV2Spec()

    assert spec.palm_corner_angles_deg == spec.arm_station_angles_deg
    assert len(spec.palm_corner_angles_deg) == spec.arm_count
    # Every corner carries an arm and every arm has a corner: no unowned corners.
    assert set(spec.palm_corner_angles_deg) == set(spec.arm_station_angles_deg)


def test_turning_the_corner_onto_the_arm_shrinks_the_palm_and_deepens_it_at_the_socket() -> None:
    """The two halves of the same change, asserted against V1 rather than a constant.

    With an edge facing the arm the plate must reach `station + envelope + wall` along
    the heading itself. With a corner facing the arm the edges only have to clear the
    socket at 36 degrees off it, and `cos 36` is what comes off the requirement.
    """
    spec = OctopusHandV2Spec()
    v1 = OctopusHandSpec()
    half_sector = math.pi / spec.arm_count

    reach = spec.arm_spec.connector_envelope_radius_mm + spec.palm_wall_mm
    assert spec.palm_inradius_mm == pytest.approx(
        spec.arm_station_radius_mm * math.cos(half_sector) + reach
    )
    assert spec.palm_circumradius_mm == pytest.approx(spec.palm_inradius_mm / math.cos(half_sector))

    # Smaller plate…
    assert spec.palm_inradius_mm < v1.palm_inradius_mm
    assert spec.palm_across_corners_mm < v1.palm_across_corners_mm

    # …and more material behind the socket than V1 had, which is where the stem goes.
    # V1's boundary along an arm heading is its inradius, because an edge faced the
    # arm; V2's is its corner, less whatever the truncation cut back off that corner.
    # Computed here rather than read off V1, which must not grow a property to serve
    # its successor.
    socket_reach = spec.arm_station_radius_mm + spec.arm_spec.connector_envelope_radius_mm
    v1_clearance = v1.palm_inradius_mm - (
        v1.arm_station_radius_mm + v1.arm_spec.connector_envelope_radius_mm
    )
    assert spec.socket_heading_clearance_mm == pytest.approx(
        spec.palm_corner_flat_radius_mm - socket_reach
    )
    assert spec.socket_heading_clearance_mm > v1_clearance
    assert v1_clearance == pytest.approx(v1.palm_wall_mm)


def test_every_socket_still_lands_on_solid_plate_all_the_way_round() -> None:
    """Shrinking the plate is only safe if no socket now hangs off an edge.

    Measured the way the lesson says to measure an envelope: the distance from the
    station to each of the five edge lines, taking the worst, not a nominal radius.
    """
    spec = OctopusHandV2Spec()
    envelope = spec.arm_spec.connector_envelope_radius_mm

    for station_angle in spec.arm_station_angles_deg:
        station = math.radians(station_angle)
        for corner_angle in spec.palm_corner_angles_deg:
            # Each edge's outward normal bisects two corners, half a sector off each.
            normal = math.radians(corner_angle) + math.pi / spec.arm_count
            reach = spec.arm_station_radius_mm * math.cos(normal - station)
            clearance = spec.palm_inradius_mm - reach - envelope
            # The two edges either side of an arm are exactly one wall away by
            # construction — that is what the inradius is solved for — so this
            # compares at tolerance rather than pretending the equality is strict.
            assert clearance >= spec.palm_wall_mm - 1e-9

    assert spec.socket_edge_clearance_mm == pytest.approx(spec.palm_wall_mm)


def test_tendon_holes_and_the_wire_channel_still_fit_the_smaller_plate() -> None:
    """A smaller palm is only correct if everything drilled through it still fits.

    Asked at each hole's own heading, because a pentagon is not a circle. V1 could
    compare against its inradius and be conservative; on V2 the inradius is the wrong
    boundary — the outermost holes sit near a corner, where the plate reaches much
    further than the inradius, and an inradius test would reject a plate that is fine.
    """
    spec = OctopusHandV2Spec()
    arm = spec.arm_spec

    assert len(spec.tendon_hole_positions_mm) == spec.total_tendon_count
    for x, y in spec.tendon_hole_positions_mm:
        boundary = spec.palm_boundary_radius_at_mm(math.degrees(math.atan2(y, x)))
        assert math.hypot(x, y) + spec.cable_relief_radius_mm + spec.palm_wall_mm <= boundary

    innermost = min(
        math.hypot(x, y) - arm.tendon_hole_diameter_mm / 2 for x, y in spec.tendon_hole_positions_mm
    )
    assert innermost > spec.wire_channel_diameter_mm / 2 + spec.palm_wall_mm


def test_palm_boundary_is_read_at_a_heading_not_as_one_radius() -> None:
    """The helper every "does this fit on the plate" question has to go through."""
    spec = OctopusHandV2Spec()

    for corner in spec.palm_corner_angles_deg:
        # On a corner's own heading the plate ends at the truncation flat, not at the
        # pentagon's point — the point was cut off.
        assert spec.palm_boundary_radius_at_mm(corner) == pytest.approx(
            spec.palm_corner_flat_radius_mm
        )
        assert spec.palm_boundary_radius_at_mm(corner) < spec.palm_circumradius_mm
        # Halfway between two corners is an edge's midpoint, the plate's closest point.
        edge_midpoint = corner + 180.0 / spec.arm_count
        assert spec.palm_boundary_radius_at_mm(edge_midpoint) == pytest.approx(
            spec.palm_inradius_mm
        )
    # Never closer than the inradius, never further than the outline actually reaches.
    for step in range(0, 360, 7):
        radius = spec.palm_boundary_radius_at_mm(float(step))
        assert spec.palm_inradius_mm - 1e-9 <= radius <= spec.palm_enclosing_radius_mm + 1e-9


def test_every_body_presents_a_pad_to_what_the_hand_is_closing_on() -> None:
    """V1's pads sat on the free rim; V2's are aimed, and the rim was never the reason.

    V1 put pads on the diagonals because "ears occupy the cardinal directions". That
    is true inside the disc and false out at the rim, where the pads live — measured
    on the real mesh, joint hardware reaches 16.70 mm and the pad's buried face starts
    at 17.00 mm. Aiming also turned out to be the roomier placement: swept through the
    full -34..+34 degrees, pad-to-pad clearance is 0.204 mm on the diagonals and
    0.553 mm on the cardinals.
    """
    spec = OctopusHandV2Spec()

    assert spec.grip_pad_angles_deg == (0.0, 90.0, 180.0, 270.0)
    assert spec.body_twists_deg == (0.0, 90.0, 0.0, 90.0, 0.0)

    # The claim: whatever a body's own twist, one of its pads points at the palm.
    for twist in spec.body_twists_deg:
        assert (180.0 - twist) % 360.0 in spec.grip_pad_angles_deg
    assert set(spec.inward_pad_angles_deg) <= set(spec.grip_pad_angles_deg)

    # And the pattern survives the twist, so all five bodies still share one mesh.
    placed = set(spec.grip_pad_angles_deg)
    for twist in spec.body_twists_deg:
        assert {(angle + twist) % 360.0 for angle in placed} == placed

    # A pad is a span, not a ray. The hardware's own reach varies across it — the
    # female root's far corner stands at the connector envelope, 68.7 degrees round,
    # which falls inside the span of a pad aimed at 90 — so pad and root do overlap.
    # That is a union of body material and fuses; what must not overlap is anything
    # that moves, which only the Blender sweep can answer.
    low, high = spec.grip.pad_span_deg
    assert high - low == pytest.approx(spec.grip_pad_arc_deg)
    assert spec.grip.pad_inner_radius_mm < spec.arm_spec.body_outer_diameter_mm / 2

    # Aiming must not have moved the arms apart.
    assert spec.grip_envelope_radius_mm == pytest.approx(OctopusHandSpec().grip_envelope_radius_mm)
    assert spec.arm_station_radius_mm >= spec.minimum_station_radius_mm


def test_softening_the_pad_edge_is_paid_for_out_of_the_gripping_face() -> None:
    """The pad's square top edge goes, and the contact area is what pays for it."""
    spec = OctopusHandV2Spec()
    v1 = OctopusHandSpec()

    assert spec.pad_top_chamfer_mm > 0
    assert spec.grip_flat_face_height_mm == pytest.approx(
        v1.grip_flat_face_height_mm - spec.pad_top_chamfer_mm
    )
    assert spec.grip_flat_face_height_mm > 0, "the chamfers ate the whole gripping face"
    # Five profile points, not V1's four: the extra one is that top chamfer.
    assert len(spec.grip.pad_profile_mm) == 5
    # The cost is bounded — softening an edge must not cost a fifth of the grip.
    v1_area = 4 * v1.grip_flat_face_height_mm * spec.grip.pad_face_chord_mm
    assert spec.grip.grip_face_area_mm2 > 0.85 * v1_area


def test_terminal_cap_does_not_graze_the_disc_rim_where_the_tip_is_trimmed() -> None:
    """A 45 degree flare puts the cap's radius exactly on the disc's, at the trim plane.

    Measured on real geometry: the cap surface then grazes the trimmed rim edge instead
    of crossing it, and the next Boolean opens twelve boundary edges at the cap's facet
    corners. V1 never noticed because its diagonal pads happen to bury four of the six
    corners in solid material — luck, not design, and it runs out when the pads move.
    """
    spec = OctopusHandV2Spec()
    rim = spec.arm_spec.body_outer_diameter_mm / 2

    assert spec.tip_cap_flare_slope_deg < 45.0, "a 45 degree flare is exactly the graze"
    assert abs(spec.tip_cap_radius_at_mm(spec.tip_feature_base_z_mm) - rim) > 0.05
    # It must still narrow-then-widen the printable way round.
    assert 0 < spec.tip_cap_flare_slope_deg <= 45
    assert spec.tip_cap_max_radius_mm > spec.tip_cap_base_radius_mm


def test_tip_cable_bores_follow_the_tendons_now_that_the_pads_have_moved() -> None:
    """In V1 these were the same list by coincidence. Aiming the pads broke that.

    A bore on a cardinal would cross no tendon pair at all, so the bores are read
    from the tendon headings directly — which happens to give V1's answer, from a
    reason that survives the pads moving.
    """
    spec = OctopusHandV2Spec()

    tendon_headings = sorted(
        math.degrees(math.atan2(y, x)) % 360 for x, y in spec.arm_spec.tendon_positions_mm
    )
    assert spec.tip_cable_bore_angles_deg == (tendon_headings[0], tendon_headings[1])
    for heading in spec.tip_cable_bore_angles_deg:
        assert heading not in spec.grip_pad_angles_deg
    assert spec.tip_cable_bore_angles_deg == OctopusHandSpec().tip_cable_bore_angles_deg


def test_plate_has_no_square_edges_left_and_pays_for_it_out_of_the_corner() -> None:
    """Softening the plate spends the surplus that turning the pentagon won.

    The corner is cut back along each arm's own heading, so every millimetre of
    truncation comes straight out of the material standing behind that arm's socket.
    The two are asserted together because reading either alone hides the trade.
    """
    spec = OctopusHandV2Spec()

    assert spec.palm_corner_flat_radius_mm == pytest.approx(
        spec.palm_circumradius_mm - spec.palm_corner_truncation_mm
    )
    assert spec.socket_heading_clearance_mm > spec.palm_wall_mm
    # Still ahead of V1, which had exactly one wall and no stem at all.
    assert spec.socket_heading_clearance_mm > OctopusHandSpec().palm_wall_mm

    # The rim chamfer prints off the bed unsupported, and survives the mesh weld.
    assert spec.palm_chamfer_slope_deg == pytest.approx(45.0)
    assert spec.palm_rim_chamfer_mm > spec.weld_distance_mm
    assert 2 * spec.palm_rim_chamfer_mm < spec.palm_thickness_mm
    # And the stem stands on flat top face, not out on the chamfer.
    assert spec.stem_outer_radius_mm <= spec.palm_top_face_reach_mm


def test_plate_envelope_is_read_off_the_outline_not_off_a_nominal_radius() -> None:
    """A truncation flat is a chord: its ends stand further out than its middle.

    Exactly the trap the grip pads sprang on V1, where spacing the arms on the pad's
    face radius let neighbouring pads meet at their corners. So the enclosing radius
    comes from the outline's own vertices.
    """
    spec = OctopusHandV2Spec()

    assert len(spec.palm_outline_vertices_mm) == 2 * spec.arm_count
    assert spec.palm_corner_flat_half_width_mm > 0
    assert spec.palm_enclosing_radius_mm > spec.palm_corner_flat_radius_mm
    assert spec.palm_enclosing_radius_mm < spec.palm_circumradius_mm
    assert spec.palm_across_corners_mm == pytest.approx(2 * spec.palm_enclosing_radius_mm)

    # The outline and the boundary function are two derivations of one shape.
    for x, y in spec.palm_outline_vertices_mm:
        boundary = spec.palm_boundary_radius_at_mm(math.degrees(math.atan2(y, x)))
        assert math.hypot(x, y) == pytest.approx(boundary, abs=1e-9)

    # With the plate this much smaller, the arms are what the bed has to hold.
    assert spec.upright_footprint_mm == pytest.approx(
        2 * (spec.arm_station_radius_mm + spec.grip_envelope_radius_mm)
    )
    assert spec.upright_footprint_mm < OctopusHandSpec().upright_footprint_mm


def test_each_arm_gets_its_own_wire_bore_beside_the_socket() -> None:
    """Wiring reaches a finger without borrowing a tendon hole or the palm channel.

    The bore sits inboard of its arm rather than on the arm's axis. On the axis it
    would line up with the channel running up the arm, which is tempting, but the
    socket's two root feet are buried in the plate either side of that axis and a
    bore there undercuts the feet the ears stand on.
    """
    spec = OctopusHandV2Spec()

    assert len(spec.arm_wire_bore_positions_mm) == spec.arm_count
    assert spec.arm_wire_bore_station_offset_mm == pytest.approx(
        spec.arm_spec.root_profile_mm[0][2] + spec.palm_wall_mm + spec.arm_wire_bore_radius_mm
    )
    for angle, (bore_x, bore_y) in zip(
        spec.arm_station_angles_deg, spec.arm_wire_bore_positions_mm, strict=True
    ):
        # On its own arm's heading, and inboard of it.
        assert math.degrees(math.atan2(bore_y, bore_x)) % 360 == pytest.approx(angle % 360)
        assert math.hypot(bore_x, bore_y) < spec.arm_station_radius_mm
        # Clear of the socket root feet it was moved inboard to avoid.
        assert spec.arm_station_radius_mm - math.hypot(bore_x, bore_y) >= (
            spec.arm_spec.root_profile_mm[0][2] + spec.arm_wire_bore_radius_mm
        )

    # It is a hole in an already-crowded plate: everything it could break into.
    assert spec.arm_wire_bore_closest_tendon_gap_mm > spec.palm_wall_mm
    first, second = spec.arm_wire_bore_positions_mm[:2]
    assert math.dist(first, second) > 2 * (spec.arm_wire_bore_radius_mm + spec.palm_wall_mm)
    assert math.hypot(*first) - spec.arm_wire_bore_radius_mm > (
        spec.wire_channel_diameter_mm / 2 + spec.palm_wall_mm
    )


def test_reinforcing_stem_braces_the_socket_and_never_needs_support() -> None:
    """The surplus V2 wins at the corner, spent as a buttress behind the socket."""
    spec = OctopusHandV2Spec()

    # It starts outboard of the socket root it braces, not inside it.
    assert spec.stem_inner_radius_mm > spec.arm_station_radius_mm
    assert spec.stem_inner_radius_mm == pytest.approx(
        spec.arm_station_radius_mm + spec.arm_spec.root_profile_mm[0][2]
    )
    # It tapers outward, so the ramp is an upward-looking face all the way.
    assert spec.stem_top_z_mm(spec.stem_inner_radius_mm) > spec.stem_top_z_mm(
        spec.stem_outer_radius_mm
    )
    assert spec.stem_top_z_mm(spec.stem_outer_radius_mm) == pytest.approx(
        spec.palm_top_face_z_mm + spec.stem_edge_height_mm
    )
    assert spec.stem_edge_height_mm > 0, "a feather edge is welded away, not printed"
    assert 0 < spec.stem_slope_deg < 90
    # And it stays on the plate it stands on.
    assert spec.stem_outer_radius_mm < spec.palm_boundary_radius_at_mm(
        spec.arm_station_angles_deg[0]
    )


def test_stem_stays_under_everything_the_base_joint_sweeps_over_it() -> None:
    """Static clearance is not the question — the arm's underside comes down here.

    A hinge turns about its pin, so as the base joint opens, the first body's disc
    swings out and down across the plate. The narrowest point of that swept floor is
    a throat partway out; a stem sized against the arm at rest would sit inside it.
    """
    spec = OctopusHandV2Spec()

    assert spec.stem_headroom_mm >= spec.stem_clearance_mm

    # The throat is real and is not at either end, which is what makes a straight
    # "check the arm at rest" test worthless here.
    floors = [
        (radius, floor)
        for radius in spec.stem.sample_radii_mm
        if (floor := spec.base_joint_swept_floor_mm(radius)) is not None
    ]
    assert len(floors) > 1
    throat_radius, throat_floor = min(
        floors, key=lambda pair: pair[1] - spec.stem_top_z_mm(pair[0])
    )
    assert spec.stem_inner_radius_mm < throat_radius <= spec.stem_outer_radius_mm
    assert throat_floor < spec.base_joint_swept_floor_mm(spec.stem_inner_radius_mm)

    # Far enough out the arm never passes at all — that is where the corner lives.
    assert spec.base_joint_swept_floor_mm(spec.palm_circumradius_mm) is None


def test_v1_is_untouched_by_everything_v2_does() -> None:
    """V1 is a checksum-controlled delivery whose contracts must stay green.

    V2 subclasses it, so a default leaking upward would silently re-dimension a
    package that has already been published and judged.
    """
    v1 = OctopusHandSpec()

    assert v1.max_bed_mm == 220.0
    assert v1.palm_inradius_mm == pytest.approx(61.42, abs=0.01)
    assert v1.palm_circumradius_mm == pytest.approx(75.92, abs=0.01)
    assert v1.palm_across_corners_mm == pytest.approx(151.84, abs=0.01)
    assert v1.upright_footprint_mm == pytest.approx(151.84, abs=0.01)
    # V1 sized by its flats: an edge faced every arm, so the corners fell between
    # them. This is the property V2 overrides, asserted here in its V1 form.
    assert v1.palm_inradius_mm == pytest.approx(
        v1.arm_station_radius_mm + v1.arm_spec.connector_envelope_radius_mm + v1.palm_wall_mm
    )


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"max_bed_mm": 90.0}, id="upright envelope exceeds the declared bed"),
        pytest.param({"arm_count": 2}, id="two arms is not a hand"),
        pytest.param({"arm_station_radius_mm": 20.0}, id="neighbouring arms would intersect"),
        pytest.param({"palm_thickness_mm": 3.0}, id="palm too thin to carry the socket roots"),
        # On V1's larger plate this widening only ever merged neighbouring reliefs.
        # V2's plate is smaller, so the relief breaks out of the rim first — the
        # discriminating case for the guard V2 adds.
        pytest.param(
            {"cable_relief_widening_mm": 6.0}, id="a tendon hole reaches past the palm edge"
        ),
        pytest.param({"stem_height_mm": 14.0}, id="stem reaches into the swept envelope"),
        pytest.param({"stem_length_mm": 20.0}, id="stem runs out under the swinging arm"),
        pytest.param({"stem_edge_height_mm": 8.0}, id="stem does not taper at all"),
        pytest.param({"stem_half_width_mm": 9.0}, id="stem is wide enough to foul the ears"),
        pytest.param({"arm_wire_bore_diameter_mm": 18.0}, id="wire bore breaks into a tendon hole"),
        pytest.param({"arm_wire_bore_diameter_mm": 22.0}, id="wire bores run into each other"),
        # Fires before V1's own "channel breaks into the tendon holes" guard, because
        # the arm bores sit inboard of the tendon ring and meet the channel first.
        pytest.param({"wire_channel_diameter_mm": 52.0}, id="wire bore meets the central channel"),
        pytest.param(
            {"palm_corner_truncation_mm": 5.0}, id="truncation cuts into the socket's wall"
        ),
        pytest.param({"palm_rim_chamfer_mm": 3.0}, id="rim chamfers meet inside the plate"),
        pytest.param(
            {"palm_rim_chamfer_mm": 0.002}, id="chamfer is finer than the mesh weld distance"
        ),
        pytest.param({"stem_length_mm": 15.0}, id="stem runs off the chamfered edge"),
        pytest.param({"tip_cap_flare_mm": 3.0}, id="cap flare grazes the disc rim"),
    ],
)
def test_v2_spec_rejects_geometry_that_cannot_be_built_or_printed(changes) -> None:
    with pytest.raises(ValueError):
        OctopusHandV2Spec(**changes)
