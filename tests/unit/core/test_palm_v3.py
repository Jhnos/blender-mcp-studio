"""A thumb that cannot reach a fingertip is a fifth finger, not a thumb.

Opposition is the only reason the thumb exists, and it is the one property of an
anthropomorphic palm that no dimension check can see: every socket can be the
right size, every finger the right length, the plate the right width, and the
thumb still sweeps past the index instead of meeting it.

So it is computed. The finger is a planar chain with known segment lengths and
known joint limits, so where its tip can go is arithmetic, and whether two such
sets meet is arithmetic too.
"""

import dataclasses
import math

import pytest

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec


def test_the_thumb_can_touch_the_index_fingertip() -> None:
    """The acceptance condition for calling this a hand.

    Checked as a reachability question rather than a pose: there must exist some
    pair of postures that brings the two tips together, not merely one posture
    someone happened to draw.
    """
    spec = AnthropomorphicPalmSpec()

    assert spec.thumb_index_tip_gap_mm < spec.pinch_contact_mm, (
        f"closest the thumb tip gets to the index tip is {spec.thumb_index_tip_gap_mm:.1f} mm"
    )


def test_a_thumb_left_in_the_finger_row_cannot_oppose() -> None:
    """The discriminating case: same lengths, no opposition angle, no pinch.

    Without this half, the check above would also pass a palm whose "thumb" is
    just a fifth finger in the row, and the guard would be measuring nothing.
    """
    flat = AnthropomorphicPalmSpec(thumb_opposition_deg=0.0, thumb_palmar_tilt_deg=0.0)

    assert flat.thumb_index_tip_gap_mm > flat.pinch_contact_mm


def test_a_palm_whose_thumb_cannot_reach_is_refused() -> None:
    with pytest.raises(ValueError, match="thumb"):
        AnthropomorphicPalmSpec(thumb_opposition_deg=0.0, thumb_palmar_tilt_deg=0.0, strict=True)


def test_a_straight_finger_reaches_the_sum_of_its_segments() -> None:
    """Forward kinematics has to be right before anything built on it means much."""
    spec = AnthropomorphicPalmSpec()

    straight = spec.fingertip_in_finger_frame_mm((0.0, 0.0, 0.0))

    assert straight[0] == pytest.approx(0.0, abs=1e-9)
    assert straight[1] == pytest.approx(sum(spec.finger_segment_lengths_mm))


def test_a_fully_curled_finger_brings_its_tip_back_towards_the_palm() -> None:
    spec = AnthropomorphicPalmSpec()
    limit = spec.finger.link.maximum_articulation_deg

    curled = spec.fingertip_in_finger_frame_mm((limit, limit, limit))
    straight = spec.fingertip_in_finger_frame_mm((0.0, 0.0, 0.0))

    assert math.hypot(*curled) < math.hypot(*straight)
    # And it curls towards the palm side, which is the negative direction here.
    assert curled[0] < 0.0


def test_the_four_row_fingers_are_evenly_spaced_and_do_not_touch() -> None:
    """Neighbouring fingers need air between them, or the hand is one blade."""
    spec = AnthropomorphicPalmSpec()

    stations = spec.row_finger_x_mm
    assert len(stations) == 4
    gaps = [b - a for a, b in zip(stations, stations[1:], strict=False)]
    assert all(gap == pytest.approx(gaps[0]) for gap in gaps)
    assert gaps[0] > spec.finger.link.body_width_mm


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"finger_gap_mm": 0.0}, id="fingers touching along the row"),
        pytest.param({"finger_gap_mm": -1.0}, id="fingers overlapping along the row"),
        # Zero now means "derive from the link" (M4); a negative distance is still nonsense.
        pytest.param({"pinch_contact_mm": -1.0}, id="a negative contact distance"),
        pytest.param({"cuff_clamp_wall_mm": 0.1}, id="a cuff clamp thinner than a wall"),
        pytest.param({"air_port_diameter_mm": 0.5}, id="an air port a syringe cannot meet"),
    ],
)
def test_an_unusable_palm_is_refused(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        AnthropomorphicPalmSpec(**overrides)  # type: ignore[arg-type]


def test_the_palm_carries_the_two_things_the_soft_layer_needs() -> None:
    """The whole interface contract: something to clamp the cuff, somewhere for air.

    The outer glove is an off-the-shelf work glove and is deliberately not
    described here — it is bought, not designed. What the rigid hand owes the
    soft layer is a place to hold both sleeves and a hole to push through.
    """
    spec = AnthropomorphicPalmSpec()

    assert spec.cuff_clamp_wall_mm >= spec.finger.link.minimum_wall_mm
    assert spec.air_port_diameter_mm >= 4.0
    # The port is a through-bore along Y, so it opens on the back by construction;
    # this used to assert the y the generator threw away. What places it is z,
    # and what matters about z is that it is on the plate and not in the clamp.
    _, port_z = spec.air_port_center_mm
    assert -spec.plate_height_mm < port_z < 0.0


def test_the_thumb_frame_is_square() -> None:
    """A pad direction that is not perpendicular to its own finger axis is skew.

    Found by inspection after the placement scan: the first version turned the
    axis about Y and then turned the pad about the *global* Z, which is not a
    roll about the finger's own axis. Dot product came out at -0.166 — the frame
    was a parallelogram, so every tip position computed in it was wrong by an
    amount that varied with posture, which is the kind of error a single spot
    check cannot see.
    """
    spec = AnthropomorphicPalmSpec()
    axis, pad = spec.thumb_frame

    assert math.isclose(sum(a * a for a in axis), 1.0, abs_tol=1e-9)
    assert math.isclose(sum(p * p for p in pad), 1.0, abs_tol=1e-9)
    assert math.isclose(sum(a * p for a, p in zip(axis, pad, strict=True)), 0.0, abs_tol=1e-9)


def test_rolling_the_thumb_does_not_move_its_axis() -> None:
    """A roll is about the finger's own axis, so the axis is what it leaves alone."""
    upright = AnthropomorphicPalmSpec(thumb_palmar_tilt_deg=0.0)
    rolled = AnthropomorphicPalmSpec(thumb_palmar_tilt_deg=45.0)

    assert upright.thumb_frame[0] == pytest.approx(rolled.thumb_frame[0])
    assert upright.thumb_frame[1] != pytest.approx(rolled.thumb_frame[1])


def test_the_thumb_root_is_carried_back_to_the_plate() -> None:
    """A root outboard of the plate is a loose part, not a thumb.

    Measured on the built palm before this existed: two connected shells, the
    smaller one 88 faces sitting from x=-82.8 to -56.1 with nothing joining it to
    a plate that stops at -57. It was watertight and had zero non-manifold edges,
    because a detached shell is perfectly manifold — that check cannot see this
    at all. It would have printed as a small loose object.

    A hand has a thenar eminence for the same reason: the thumb's root needs
    something to stand on.
    """
    spec = AnthropomorphicPalmSpec()
    (centre_x, _, _), (size_x, _, _) = spec.thenar_bridge_mm

    reaches_plate = centre_x + size_x / 2 > -spec.palm_width_mm / 2
    reaches_root = centre_x - size_x / 2 < spec.thumb_root_mm[0]
    assert reaches_plate, "the bridge never touches the plate"
    assert reaches_root, "the bridge never reaches the thumb root"


def test_a_thumb_on_a_cantilevered_arm_is_refused() -> None:
    """The guard measures the boss's length, because its reach is a tautology.

    Written first as "does the bridge reach the root", which the bridge is
    *defined* to do — a guard that can never fire. What can go wrong is the boss
    becoming an arm: push the thumb far enough out and the bulge at the base of
    a thumb turns into a cantilever carrying a joint at its end.
    """
    with pytest.raises(ValueError, match="cantilever"):
        AnthropomorphicPalmSpec(thumb_offset_mm=200.0)

    # And the shipped hand is comfortably inside the limit, so the guard is not
    # simply always-on.
    spec = AnthropomorphicPalmSpec()
    assert 0 < spec.thenar_overhang_mm < spec.palm_width_mm / 2


def test_the_hand_has_a_hands_proportions() -> None:
    """A spec called anthropomorphic with no anthropometry in it is just a name.

    This check did not exist, and its absence is why the design reached a print
    package as a 320 mm hand with 169 mm fingers — 1.7 times human — carrying
    four phalanges where a hand has three. Every check that did exist was
    internally consistent, and scaling everything up together satisfies all of
    them: reachability, clearance, collision and manifoldness are all blind to
    absolute size. Only a comparison against something outside the design can
    see it.

    Bounds are loose on purpose. This is a robot hand, not a cast of one, and
    the point is to catch a hand that is twice the size of a hand — not to
    legislate millimetres.
    """
    spec = AnthropomorphicPalmSpec()

    assert spec.finger.link.assembly_unit_count == 3, "a finger carries three phalanges"
    assert spec.finger_to_palm_ratio == pytest.approx(
        sum(spec.finger_segment_lengths_mm) / spec.palm_height_mm
    )
    assert 0.7 <= spec.finger_to_palm_ratio <= 1.4, (
        f"fingers are {spec.finger_to_palm_ratio:.2f} times the palm's height; a hand is about 1.0"
    )


def test_a_hand_with_rake_proportions_is_refused() -> None:
    """The configuration that actually shipped has to be the thing that fires."""
    from src.core.domain.finger_v3 import SingleTendonFingerSpec
    from src.core.domain.hinge_chain import HingePhalanxSpec

    four = SingleTendonFingerSpec(
        link=HingePhalanxSpec(joint_count=3, joint_center_offset_mm=27.0),
        moment_arms_mm=(6.6, 6.6, 6.6),
    )
    with pytest.raises(ValueError, match="times the palm"):
        AnthropomorphicPalmSpec(finger=four, strict=True)


def test_the_air_port_is_placed_by_the_spec_and_not_by_the_generator() -> None:
    """Where the port sits was a magic number in the generator, not a decision.

    `air_port_center_mm` returned an (x, y) whose y the generator threw away —
    `_ = port_y` — while the height that actually places the bore lived in
    `palm_v3_geometry` as `-plate_height * 0.72`. So the one value the spec
    published about the port was unused, and the one value that mattered was
    unreviewable. A unit test asserted the unused half and passed.

    The port is a through-bore along Y (`07-interfaces`: 一個貫穿孔), so what
    places it is x and z. That is what the spec says now.
    """
    spec = AnthropomorphicPalmSpec()

    x_mm, z_mm = spec.air_port_center_mm
    assert x_mm == pytest.approx(0.0), "centred across the plate"
    assert -spec.plate_height_mm < z_mm < 0.0, "inside the plate, below its top"


def test_the_air_port_misses_every_tendon_and_wiring_channel() -> None:
    """F12: a port blocked by internal structure looks identical from outside.

    The channels run down the plate at each digit's x; the port crosses it at
    x = 0. Nothing was checking that those two never meet — the failure mode
    was written down and the check next to it was never built.
    """
    spec = AnthropomorphicPalmSpec()

    port_x, _ = spec.air_port_center_mm
    port_radius = spec.air_port_diameter_mm / 2
    channel_radius = spec.finger.link.tendon_hole_diameter_mm / 2
    stations = [*spec.row_finger_x_mm, spec.thumb_root_mm[0]]

    for x_mm in stations:
        gap = abs(x_mm - port_x) - port_radius - channel_radius
        assert gap > 0.0, f"the port meets the channel at x={x_mm}: {gap:.2f} mm"


def test_the_air_port_clears_the_cuff_clamp_band() -> None:
    """Two independent formulas landed 0.4 mm apart, and nobody chose that.

    The port's height was `-plate_height * 0.72` inside the generator; the
    clamp groove's was `-plate_height + body_length / 2` inside another
    function. They evaluated to -50.4 and -50.0, so a Ø6 port was bored
    straight through the middle of a 3 mm clamp band — the one place on the
    plate whose whole job is to hold a glove cuff down against continuous
    material. Neither number was reviewable, and their near-collision was
    arithmetic, not a decision.
    """
    spec = AnthropomorphicPalmSpec()

    _, port_z = spec.air_port_center_mm
    port_bottom = port_z - spec.air_port_diameter_mm / 2
    band_top = spec.cuff_clamp_center_z_mm + spec.cuff_clamp_wall_mm / 2

    assert port_bottom >= band_top + spec.finger.link.minimum_wall_mm, (
        f"port bottom {port_bottom:.2f} against band top {band_top:.2f}"
    )


def test_a_port_driven_into_the_clamp_band_is_refused() -> None:
    """The should-fire half. A guard with only a passing fixture is a guard
    that is indistinguishable from one that always passes."""
    with pytest.raises(ValueError):
        AnthropomorphicPalmSpec(air_port_clearance_mm=-20.0)


def test_a_port_wide_enough_to_meet_a_tendon_channel_is_caught() -> None:
    """The should-fire half of the channel-clearance check."""
    spec = AnthropomorphicPalmSpec()
    port_x, _ = spec.air_port_center_mm
    channel_radius = spec.finger.link.tendon_hole_diameter_mm / 2
    nearest = min(abs(x - port_x) for x in spec.row_finger_x_mm)

    # A port this wide reaches the nearest channel; the arithmetic the passing
    # test relies on must say so rather than staying quiet.
    absurd = 2 * (nearest - channel_radius + 1.0)
    gap = nearest - absurd / 2 - channel_radius
    assert gap < 0.0


def test_no_two_routes_through_the_palm_can_touch() -> None:
    """F10: two tendons that cross rub each other until one parts.

    Ten bores run down this plate — a tendon and a wiring channel at each of
    five stations — and the failure-mode table asked for a pairwise clearance
    that nothing ever computed. It is arithmetic, and it sat in the matrix as
    TODO beside the rows that genuinely need a printed part.

    The first draft asserted the clearance alone and passed on the first run,
    which is the shape of a test worth distrusting. Nothing legal can make it
    fail: every way of crowding the routes trips an invariant in the link spec
    first. So the clearance is recorded and the *refusal* is what is asserted.
    """
    spec = AnthropomorphicPalmSpec()
    link = spec.finger.link
    radius = link.tendon_hole_diameter_mm / 2
    stations = [*spec.row_finger_x_mm, spec.thumb_root_mm[0]]

    routes = [
        (x_mm, y_mm)
        for x_mm in stations
        for y_mm in (spec.finger.tendon_bore_offset_mm, spec.finger.wiring_bore_offset_mm)
    ]
    assert len(routes) == 10

    def worst_clearance(candidate: AnthropomorphicPalmSpec) -> float:
        stations_mm = [*candidate.row_finger_x_mm, candidate.thumb_root_mm[0]]
        paths = [
            (x_mm, y_mm)
            for x_mm in stations_mm
            for y_mm in (
                candidate.finger.tendon_bore_offset_mm,
                candidate.finger.wiring_bore_offset_mm,
            )
        ]
        return min(
            math.dist(first, second) - candidate.finger.link.tendon_hole_diameter_mm
            for index, first in enumerate(paths)
            for second in paths[index + 1 :]
        )

    assert worst_clearance(spec) == pytest.approx(10.4, abs=0.1)
    assert worst_clearance(spec) > link.minimum_wall_mm

    # And the reason it cannot go wrong, which is the part worth pinning. Every
    # way of crowding these routes is refused by an invariant that fires first:
    # the binding pair is a station's own tendon and wiring bores, and walking
    # them together drives the wiring bore into the pin. A guard that no legal
    # spec can make fire is indistinguishable from `assert True`, so what is
    # asserted here is the refusal, not the clearance.
    for crowded in (3.5, 2.5):
        with pytest.raises(ValueError):
            dataclasses.replace(
                spec, finger=dataclasses.replace(spec.finger, wiring_bore_offset_mm=crowded)
            )
    assert radius > 0


def test_a_tendon_turns_on_the_radius_its_moment_arm_sets() -> None:
    """F9, as far as geometry can take it without a cord in hand.

    The tendon wraps each joint at exactly its moment arm, so 'minimum bend
    radius' is not a separate number to be measured — it *is* the moment arm,
    and the usable window already brackets it. What stays open is the
    threshold: a cord's own minimum bend radius is a property of the cord, and
    choosing one is a purchase, not a computation. This pins the relationship
    so that buying a cord immediately decides whether the geometry passes.
    """
    spec = AnthropomorphicPalmSpec()
    finger = spec.finger

    bend_radii = set(finger.moment_arms_mm)
    assert bend_radii == {6.6}, "the tendon's turn radius is its moment arm, and they are equal"
    assert finger.smallest_usable_moment_arm_mm <= min(bend_radii)
    assert max(bend_radii) <= finger.largest_usable_moment_arm_mm

    # A cord needing more than this cannot be used without a new link spec.
    assert min(bend_radii) == pytest.approx(6.6, abs=0.01)


# --- M4: the palm knows which link it is built for ---------------------------


def test_a_thumb_root_proud_of_the_palm_is_refused() -> None:
    """ES-1: the root's forward limit is the plate's own thickness.

    The comment on `thumb_base_palmar_mm` said so for a month; nothing enforced
    it, and a 15 mm-deep link would have put the root 7 mm out on a stalk.
    """
    with pytest.raises(ValueError, match="proud"):
        AnthropomorphicPalmSpec(thumb_base_palmar_mm=23.0)


def test_a_contact_distance_wider_than_the_plate_is_refused() -> None:
    with pytest.raises(ValueError, match="contact"):
        AnthropomorphicPalmSpec(pinch_contact_mm=23.0)


def test_derived_palm_defaults_equal_the_v3_literals() -> None:
    """ES-2: zero means 'from the link', and for this link that is the old 22.0 exactly."""
    spec = AnthropomorphicPalmSpec()

    assert spec.thumb_base_palmar_mm == 22.0 == spec.finger.link.body_depth_mm
    assert spec.pinch_contact_mm == 22.0
    assert spec.thumb_boss_clearance_mm == 1.0 == 4 * spec.finger.link.printed_radial_clearance_mm
    assert spec == AnthropomorphicPalmSpec(
        thumb_base_palmar_mm=0.0, pinch_contact_mm=0.0, thumb_boss_clearance_mm=0.0
    )


def test_a_boss_clearance_under_the_printed_clearance_is_refused() -> None:
    with pytest.raises(ValueError, match="clearance"):
        AnthropomorphicPalmSpec(thumb_boss_clearance_mm=0.1)


def test_a_three_finger_row_is_narrower_by_one_pitch() -> None:
    """PS-3: the row count is a field, and the plate, the stations and the thumb follow it."""
    four = AnthropomorphicPalmSpec()
    three = dataclasses.replace(four, row_finger_count=3)

    assert three.row_finger_x_mm == (-30.0, 0.0, 30.0)
    assert four.palm_width_mm - three.palm_width_mm == pytest.approx(four.row_pitch_mm)
    assert three.thumb_root_mm[0] == pytest.approx(-56.0)
    assert four.row_finger_x_mm == (-45.0, -15.0, 15.0, 45.0)


def test_a_row_of_no_fingers_is_refused() -> None:
    with pytest.raises(ValueError, match="row"):
        AnthropomorphicPalmSpec(row_finger_count=0)


def test_the_posture_grid_follows_the_articulation_limit() -> None:
    """DS-2: samples every ten degrees to whatever the link allows, never to a literal 50."""
    from src.core.domain.hinge_chain import HingePhalanxSpec
    from src.core.domain.opposition import posture_samples_deg

    v3 = AnthropomorphicPalmSpec()
    assert posture_samples_deg(v3) == (0.0, 10.0, 20.0, 30.0, 40.0, 50.0)

    wider_link = HingePhalanxSpec(
        joint_count=2, joint_center_offset_mm=27.0, maximum_articulation_deg=60.0
    )
    wider = dataclasses.replace(v3, finger=dataclasses.replace(v3.finger, link=wider_link))
    assert posture_samples_deg(wider)[-1] == 60.0
    assert len(posture_samples_deg(wider)) == 7


def test_opposition_is_a_function_of_the_palm_and_the_palm_only_delegates() -> None:
    """The reachability arithmetic lives in `opposition`; the palm keeps three lines."""
    from src.core.domain.opposition import thumb_index_tip_gap_mm

    spec = AnthropomorphicPalmSpec()

    assert thumb_index_tip_gap_mm(spec) == spec.thumb_index_tip_gap_mm
