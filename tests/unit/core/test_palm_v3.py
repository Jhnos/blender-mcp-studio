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
        f"closest the thumb tip gets to the index tip is "
        f"{spec.thumb_index_tip_gap_mm:.1f} mm"
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
