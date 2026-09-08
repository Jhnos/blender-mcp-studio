"""One tendon has to close three joints, and only arithmetic can say whether it can.

The failure this file exists to catch is invisible to every other check: each
phalanx is watertight, each joint sweeps without collision, the whole finger
passes readiness — and it never closes, because the cable the actuator can pull
is shorter than the cable the three joints together demand. Nothing about a
single part is wrong. The defect lives in the sum.

So the sum is a named quantity with a rejection branch, not a comment.
"""

import math

import pytest

from src.core.domain.finger_v3 import SingleTendonFingerSpec


def test_the_tendon_a_finger_needs_is_the_sum_of_what_each_joint_takes() -> None:
    """Bending a joint by theta over moment arm r eats r*theta of cable.

    Asserted against the arithmetic rather than a copied constant, so the test
    still means something when the moment arms are retuned.
    """
    spec = SingleTendonFingerSpec()

    full = math.radians(spec.link.maximum_articulation_deg)
    expected = sum(arm * full for arm in spec.moment_arms_mm)

    assert spec.tendon_travel_mm == pytest.approx(expected)
    assert spec.tendon_travel_mm > 0


def test_a_finger_whose_tendon_outruns_its_actuator_is_refused() -> None:
    """The whole point: a finger that can never close must fail loudly at build time.

    Every per-part check stays green in this configuration, which is exactly why
    the rejection has to live here.
    """
    with pytest.raises(ValueError, match="actuator stroke"):
        SingleTendonFingerSpec(actuator_stroke_mm=1.0)


def test_the_shipped_finger_closes_within_its_actuator_stroke() -> None:
    """The should-pass half. Without it, an always-raising guard looks identical."""
    spec = SingleTendonFingerSpec()

    assert spec.tendon_travel_mm <= spec.actuator_stroke_mm


def test_the_finger_bends_in_one_plane_unlike_the_chain_it_borrows_from() -> None:
    """The borrowed link geometry is right; the borrowed *chain rule* is not.

    `HingePhalanxSpec` stacks its units 0/90/0/90 so the assembly bends about
    alternating axes — correct for a tentacle, wrong for a finger, which must
    curl in a single plane or it cannot oppose a thumb. Composition is what lets
    V3 keep the link and replace the rule; inheritance would have carried the
    rule along silently.

    Asserted as a difference from the borrowed value, not just as "all zero" —
    two things that are supposed to differ need an assertion that says so, or a
    future edit can quietly make them the same again.
    """
    spec = SingleTendonFingerSpec()

    assert set(spec.joint_rotations_deg) == {0.0}
    assert len(spec.joint_rotations_deg) == spec.link.assembly_unit_count
    assert spec.joint_rotations_deg != spec.link.assembly_rotations_deg


def test_the_moment_arms_shrink_towards_the_fingertip() -> None:
    """Proximal joint gets the largest arm, so the finger curls base-first.

    Reverse the order and the fingertip curls before the knuckle does: the
    finger closes into a hook from the wrong end and rolls objects out of the
    hand instead of wrapping them. Nothing in the mesh is wrong when that
    happens, which is why it is checked on the numbers.
    """
    spec = SingleTendonFingerSpec()

    arms = spec.moment_arms_mm
    assert all(nearer > further for nearer, further in zip(arms, arms[1:], strict=False)), arms


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {"moment_arms_mm": (4.0, 5.5, 7.0)},
            id="arms growing towards the tip curl the finger from the wrong end",
        ),
        pytest.param(
            {"moment_arms_mm": (5.5, 5.5, 5.5)},
            id="equal arms leave the closing order undetermined",
        ),
        pytest.param(
            {"moment_arms_mm": (7.0, 5.5)},
            id="one arm short of the joint count",
        ),
        pytest.param(
            {"actuator_stroke_mm": 1.0},
            id="an actuator that cannot pull the cable the joints need",
        ),
    ],
)
def test_a_finger_that_cannot_work_is_refused_at_construction(
    overrides: dict[str, object],
) -> None:
    """Each case is a configuration that passes every per-part check and still fails."""
    with pytest.raises(ValueError):
        SingleTendonFingerSpec(**overrides)  # type: ignore[arg-type]


def test_the_v3_finger_is_not_a_subtype_of_the_octopus_hand() -> None:
    """V3 borrows a link, not a lineage.

    Every octopus spec assumes radial symmetry and biaxial joints. A finger has
    neither, so inheriting from one would produce a subtype that cannot honour
    its supertype's invariants — and it would drag the alternating-axis chain
    rule along silently, which is precisely the thing V3 has to replace.

    Both-sided: the same predicate is run against a pair that genuinely *is* a
    subtype, so a predicate that has degenerated into "always true" is caught
    here rather than passing forever.
    """
    from src.core.domain.octopus_hand import OctopusHandSpec
    from src.core.domain.octopus_hand_v2 import OctopusHandV2Spec

    def descends_from_octopus(cls: type) -> bool:
        return issubclass(cls, OctopusHandSpec)

    assert not descends_from_octopus(SingleTendonFingerSpec)
    # The should-fire half: V2 really is a subtype of V1, so the predicate works.
    assert descends_from_octopus(OctopusHandV2Spec)


def test_both_ends_of_a_phalanx_turn_about_the_same_axis() -> None:
    """Stacking unrotated is only coherent if the two ends actually mate.

    The borrowed link puts its male lug on X and its female fork on Y, so the
    0/90 alternation in its chain rule is not decoration — it is what lets a
    male end enter the next unit's female end at all. Saying "V3 stacks its
    units unrotated" while keeping perpendicular ends describes a finger whose
    parts cannot be assembled: every dimension checks out, every part prints,
    and the second phalanx will not go on the first.

    So the planar decision and the shared-axis decision are one decision, and
    this is the assertion that keeps them together.
    """
    spec = SingleTendonFingerSpec()

    assert spec.male_hinge_axis == spec.female_hinge_axis
    # And it is genuinely a departure from the link it borrows dimensions from.
    assert spec.link.male_hinge_axis != spec.link.female_hinge_axis


def test_a_planar_finger_with_perpendicular_ends_is_refused() -> None:
    """The two decisions cannot drift apart later without something going red."""
    spec = SingleTendonFingerSpec()

    stacked_unrotated = set(spec.joint_rotations_deg) == {0.0}
    ends_mate = spec.male_hinge_axis == spec.female_hinge_axis
    assert stacked_unrotated is ends_mate, (
        "a finger stacked unrotated needs both hinge ends on one axis; "
        "one of these was changed without the other"
    )


def test_a_moment_arm_leaves_wall_between_the_tendon_and_the_pin() -> None:
    """The tendon and the pin share one small cross-section, and both need wall.

    A moment arm is just how far the tendon runs from the joint axis, so shrinking
    it walks the tendon bore straight into the pin bore. The first draft of this
    spec shipped arms of 5.5 and 4.0 mm, which leave 1.85 and 0.35 mm of material
    against a 2.4 mm minimum — and nothing else would have caught it, because
    each bore is individually legal and the mesh is watertight either way.
    """
    spec = SingleTendonFingerSpec()
    link = spec.link

    floor = link.printed_pin_bore_mm / 2 + link.minimum_wall_mm + link.tendon_hole_diameter_mm / 2
    for arm in spec.moment_arms_mm:
        assert arm >= floor, f"moment arm {arm} runs the tendon into the pin's wall"
    assert spec.smallest_usable_moment_arm_mm == pytest.approx(floor)


def test_a_moment_arm_stays_inside_the_body_it_is_drilled_through() -> None:
    """The other end of the same squeeze: too far out and the bore leaves the finger."""
    spec = SingleTendonFingerSpec()
    link = spec.link

    ceiling = link.body_depth_mm / 2 - link.minimum_wall_mm - link.tendon_hole_diameter_mm / 2
    for arm in spec.moment_arms_mm:
        assert arm <= ceiling, f"moment arm {arm} breaks out through the body wall"
    assert spec.largest_usable_moment_arm_mm == pytest.approx(ceiling)


@pytest.mark.parametrize(
    "arms",
    [
        pytest.param((7.1, 5.5, 4.0), id="the arms this spec originally shipped with"),
        pytest.param((7.1, 6.6, 2.0), id="a tendon bore inside the pin bore"),
        pytest.param((9.0, 8.0, 7.0), id="a tendon bore outside the body"),
    ],
)
def test_moment_arms_outside_the_usable_window_are_refused(arms: tuple[float, ...]) -> None:
    with pytest.raises(ValueError, match="moment arm"):
        SingleTendonFingerSpec(moment_arms_mm=arms)
