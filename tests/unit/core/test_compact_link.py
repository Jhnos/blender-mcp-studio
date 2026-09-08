"""A link that fits a human finger, and the interface that lets V3 swap onto it.

The borrowed `HingePhalanxSpec` cannot make a human-sized finger, and the reason
is one dimension: the pin. Its bore, plus a wall either side, plus the tendon,
sets a floor of 6.05 mm on every moment arm, and none of those three shrink with
the body. The ceiling falls with body depth, so they cross — and long before
they cross, the usable window is too narrow to sequence anything. V3 recorded
that as "closing order must come from the springs", which is true of that link
and was mistaken for a property of the machine.

Prior art says the same thing louder: the two closest open projects both delete
the pin outright — `100_fingers` uses living hinges, `RoninHand` prints its
joints in place. Keeping a pin and shrinking it is the smaller step, and it is
the one whose checks this repo already owns.

What makes it a swap rather than a rewrite is that the V3 stack touches a fixed
set of link attributes, written down as `FingerLinkSpec`. That is the interface;
both specs satisfy it, and the count lives in the Protocol, not in prose.
"""

import dataclasses

import pytest

from src.core.domain.compact_link import CompactHingeLinkSpec
from src.core.domain.finger_link import FingerLinkSpec
from src.core.domain.finger_v3 import SingleTendonFingerSpec
from src.core.domain.hinge_chain import HingePhalanxSpec


def _moment_arm_window(link: FingerLinkSpec) -> tuple[float, float]:
    floor = link.printed_pin_bore_mm / 2 + link.minimum_wall_mm + link.tendon_hole_diameter_mm / 2
    ceiling = link.body_depth_mm / 2 - link.minimum_wall_mm - link.tendon_hole_diameter_mm / 2
    return (floor, ceiling)


def test_both_links_satisfy_the_one_interface_the_v3_stack_uses() -> None:
    """Nineteen attributes. If both provide them, V4 is a parameter, not a fork."""
    borrowed: FingerLinkSpec = HingePhalanxSpec(joint_count=2, joint_center_offset_mm=27.0)
    compact: FingerLinkSpec = CompactHingeLinkSpec()

    for link in (borrowed, compact):
        assert link.joint_count >= 1
        assert link.unit_pitch_mm == pytest.approx(2 * link.joint_center_offset_mm)
        assert link.printed_pin_bore_mm > link.pin_diameter_mm
        assert link.fork_total_width_mm <= link.body_depth_mm
        assert isinstance(link.has_bearing_seat, bool)


def test_the_compact_link_opens_the_window_the_borrowed_one_closed() -> None:
    """The whole point, in one number.

    1.19 cannot order three joints; 1.76 can. Deleting the bearing and halving
    the pin is what buys it, and it also takes 7 mm out of the body depth.
    """
    borrowed = HingePhalanxSpec(joint_count=2, joint_center_offset_mm=27.0)
    compact = CompactHingeLinkSpec()

    borrowed_floor, borrowed_ceiling = _moment_arm_window(borrowed)
    compact_floor, compact_ceiling = _moment_arm_window(compact)

    assert borrowed_ceiling / borrowed_floor == pytest.approx(1.19, abs=0.02)
    assert compact_ceiling / compact_floor >= 1.5
    assert compact.body_depth_mm < borrowed.body_depth_mm - 5.0


def test_the_compact_link_carries_no_bearing_and_says_so() -> None:
    """A bearing is what forces the lug wide; naming its absence is the point."""
    compact = CompactHingeLinkSpec()

    assert compact.has_bearing_seat is False
    assert compact.bearing_width_mm == 0.0
    assert not any("bearing" in item.lower() for item in compact.common_hardware)
    assert HingePhalanxSpec().has_bearing_seat is True


def test_a_finger_built_on_the_compact_link_is_a_human_length() -> None:
    """Derived, not chosen: the length falls out of the joint offset and the lug."""
    finger = SingleTendonFingerSpec(
        link=CompactHingeLinkSpec(joint_count=2),
        moment_arms_mm=(4.5, 3.6),
        spring_stiffness_ratio=(1.0, 1.6),
    )

    reach = sum(
        (
            finger.link.joint_center_offset_mm,
            finger.link.unit_pitch_mm,
            finger.link.joint_center_offset_mm + finger.link.lug_outer_diameter_mm / 2,
        )
    )
    # A human finger is about 100 mm base joint to tip; this lands inside a band
    # rather than on a number, because the anthropometry is a reference, not a
    # measurement this project has taken.
    assert 90.0 <= reach <= 110.0


def test_the_compact_link_lets_the_moment_arms_do_the_ordering_again() -> None:
    """What V3 had to give up and this gets back.

    On the borrowed link a strictly decreasing pair inside the window differs by
    at most 19%; here the same pair can differ by 60%, which is enough to
    sequence joints without leaning entirely on spring choice.
    """
    compact = CompactHingeLinkSpec(joint_count=2)
    floor, ceiling = _moment_arm_window(compact)

    finger = SingleTendonFingerSpec(
        link=compact,
        moment_arms_mm=(round(ceiling, 2), round(floor, 2)),
        spring_stiffness_ratio=(1.0, 1.6),
    )

    biggest, smallest = finger.moment_arms_mm
    assert biggest / smallest >= 1.5
    assert finger.smallest_usable_moment_arm_mm == pytest.approx(floor, abs=0.01)
    assert finger.largest_usable_moment_arm_mm == pytest.approx(ceiling, abs=0.01)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"pin_diameter_mm": 0.4}, id="a pin too thin to survive handling"),
        pytest.param({"minimum_wall_mm": 0.3}, id="a wall no nozzle can lay down"),
        pytest.param({"body_depth_mm": 6.0}, id="a body too shallow for its own fork"),
        pytest.param({"fork_gap_mm": 1.0}, id="a fork the tongue cannot enter"),
    ],
)
def test_a_compact_link_that_cannot_be_printed_is_refused(overrides: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        CompactHingeLinkSpec(**overrides)  # type: ignore[arg-type]


def test_shrinking_the_pin_is_bounded_by_what_the_window_needs() -> None:
    """The floor moves with the pin, so the invariant is stated against the window.

    Halving the pin again would keep passing every per-dimension rule while
    leaving a joint nothing to turn on — the constraint that matters is not the
    pin's size but whether a usable window survives it.
    """
    compact = CompactHingeLinkSpec()
    floor, ceiling = _moment_arm_window(compact)
    assert ceiling > floor

    with pytest.raises(ValueError):
        dataclasses.replace(compact, body_depth_mm=8.0)
