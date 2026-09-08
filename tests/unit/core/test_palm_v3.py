"""A thumb that cannot reach a fingertip is a fifth finger, not a thumb.

Opposition is the only reason the thumb exists, and it is the one property of an
anthropomorphic palm that no dimension check can see: every socket can be the
right size, every finger the right length, the plate the right width, and the
thumb still sweeps past the index instead of meeting it.

So it is computed. The finger is a planar chain with known segment lengths and
known joint limits, so where its tip can go is arithmetic, and whether two such
sets meet is arithmetic too.
"""

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
        pytest.param({"pinch_contact_mm": 0.0}, id="a contact distance of nothing"),
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
    assert spec.air_port_center_mm[1] > 0.0, "the port belongs on the back, clear of the grasp"


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
