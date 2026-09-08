"""Two render forks, one profile type — and the live one must not shift.

`scripts/archive/README.md` records the rule this file enforces: reviving the
hinge-chain render line is done by naming a `PresentationProfile` and turning
each fork into a constant, never by moving the fork back into the live tree.
The two archived render modules differ from the live one by 77 lines with the
same function names in the same order — they were forked from each other, and
abstracting dead code would have been pure waste until something needed it.

Something needs it now, which makes the first risk concrete: the live profile
drives V5, V6 and both octopus hands. If refactoring shifts one of its numbers,
every one of those renders changes and no contract notices, because the
contracts assert that a PNG exists, not what is in it. So the live profile's
values are pinned here against the numbers the live code used before the
refactor.
"""

import pytest

from scripts.presentation_profile import FINGER_PROFILE, MECHANICAL_PROFILE, PresentationProfile


def test_the_live_profile_still_carries_the_numbers_the_render_had_before() -> None:
    """Pinned, because a silent shift here re-renders four delivered models.

    These are transcribed from `hollow_hinge_render.setup_render` as it stood at
    V01.08.001, before it read a profile at all.
    """
    profile = MECHANICAL_PROFILE

    assert profile.prefix == "HH_"
    assert profile.resolution == (1200, 1500)
    assert profile.background_color == (0.008, 0.014, 0.026)
    assert (profile.curvature_ridge, profile.curvature_valley) == (2.0, 1.6)
    assert (profile.floor_size_mm, profile.floor_z_mm) == (300.0, -25.0)
    assert profile.camera_location_mm == (145.0, -270.0, 145.0)
    assert profile.ortho_scale_mm == 226.0
    assert profile.lights == (
        ("KEY", 30.0, 80.0, (90.0, -100.0, 190.0)),
        ("FILL", 16.0, 70.0, (-90.0, -35.0, 100.0)),
        ("RIM", 24.0, 60.0, (35.0, 95.0, 175.0)),
    )


def test_the_finger_profile_is_the_archived_fork_expressed_as_data() -> None:
    """Transcribed from `scripts/archive/hinge_chain_render.setup_render`.

    Reviving the line means keeping what that fork actually looked like, not
    inventing a new one — otherwise the revival is a rewrite wearing the old
    name, and the archived evidence stops describing it.
    """
    profile = FINGER_PROFILE

    assert profile.prefix == "HJ_"
    assert profile.resolution == (1100, 1300)
    assert profile.ortho_scale_mm == 285.0
    assert profile.camera_location_mm == (190.0, -335.0, 205.0)
    assert tuple(name for name, *_ in profile.lights) == ("KEY", "FILL", "RIM")


def test_the_two_profiles_are_actually_different() -> None:
    """A must-differ assertion, because collapsing them is the silent failure.

    Both profiles being well formed and both profiles being the same object look
    identical under every other check in this file.
    """
    assert MECHANICAL_PROFILE != FINGER_PROFILE
    assert MECHANICAL_PROFILE.prefix != FINGER_PROFILE.prefix
    assert MECHANICAL_PROFILE.object_name("CAMERA") != FINGER_PROFILE.object_name("CAMERA")


def test_a_profile_names_its_scene_objects_from_its_own_prefix() -> None:
    """The prefix is what keeps one model's render furniture out of another's."""
    assert MECHANICAL_PROFILE.object_name("FLOOR") == "HH_FLOOR"
    assert FINGER_PROFILE.object_name("FLOOR") == "HJ_FLOOR"
    assert MECHANICAL_PROFILE.light_names == ("HH_KEY", "HH_FILL", "HH_RIM")


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"prefix": "HH"}, id="a prefix that does not end in an underscore"),
        pytest.param({"prefix": ""}, id="an empty prefix collides with every other model"),
        pytest.param({"resolution": (0, 1500)}, id="a zero-width render"),
        pytest.param({"ortho_scale_mm": 0.0}, id="a camera that sees nothing"),
        pytest.param({"lights": ()}, id="no lights at all renders a black frame"),
        pytest.param({"floor_size_mm": -1.0}, id="a negative floor"),
    ],
)
def test_an_unusable_profile_is_refused(overrides: dict[str, object]) -> None:
    """Each of these renders something, and what it renders is useless."""
    fields = {
        "prefix": "HH_",
        "resolution": (1200, 1500),
        "background_color": (0.0, 0.0, 0.0),
        "curvature_ridge": 2.0,
        "curvature_valley": 1.6,
        "floor_size_mm": 300.0,
        "floor_z_mm": -25.0,
        "camera_location_mm": (145.0, -270.0, 145.0),
        "ortho_scale_mm": 226.0,
        "lights": (("KEY", 30.0, 80.0, (90.0, -100.0, 190.0)),),
    }
    fields.update(overrides)
    with pytest.raises(ValueError):
        PresentationProfile(**fields)  # type: ignore[arg-type]


def test_every_spec_the_render_serves_satisfies_its_interface() -> None:
    """The render asks for a stack's height, not for a named class.

    `setup_render` was typed as a union of the two specs that happened to call
    it, which is a list of callers rather than a statement of what it needs — and
    the third caller failed to type-check for a reason no one could act on. It
    reads the unit count and the pitch to aim the camera at the middle of the
    stack, and nothing else.
    """
    from scripts.presentation_profile import StackedAssembly
    from src.core.domain.biaxial_hinge import BiaxialHingeSpec
    from src.core.domain.finger_v3 import SingleTendonFingerSpec
    from src.core.domain.hollow_side_hinge import HollowSideHingeSpec
    from src.core.domain.inset_hinge import InsetHingeSpec

    for spec in (
        HollowSideHingeSpec(),
        InsetHingeSpec(),
        BiaxialHingeSpec(joint_count=4),
        SingleTendonFingerSpec().link,
    ):
        assert isinstance(spec, StackedAssembly), type(spec).__name__
        assert spec.assembly_unit_count >= 1
        assert spec.unit_pitch_mm > 0

    # Should-fire: an object with neither member must not satisfy it.
    assert not isinstance(object(), StackedAssembly)
