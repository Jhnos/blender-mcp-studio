"""Where each chain hangs, computed once and read by both the palm and the assembly.

The thumb's basis matrix was built twice in `palm_v3_geometry.py`, from the same
spec, in two functions. Here it is built once, without Blender, and the assembly
and the palm cuts read the same tuple.
"""

import math

import pytest

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.naming import NamingPolicy
from src.core.planning.station_plan import station_plan

PALM = AnthropomorphicPalmSpec()
NAMING = NamingPolicy("HJ_", "V3")


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_five_stations_in_contract_order_at_the_spec_positions() -> None:
    stations = station_plan(PALM, NAMING)

    assert [station.label for station in stations] == ["F1", "F2", "F3", "F4", "T"]
    assert [station.origin_mm for station in stations[:4]] == [
        (-45.0, 0.0, 0.0),
        (-15.0, 0.0, 0.0),
        (15.0, 0.0, 0.0),
        (45.0, 0.0, 0.0),
    ]
    assert stations[4].origin_mm == pytest.approx((-71.0, -22.0, -30.0))


def test_row_stations_hang_straight_and_the_thumb_uses_the_spec_frame() -> None:
    stations = station_plan(PALM, NAMING)
    identity = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

    for station in stations[:4]:
        assert station.basis == identity
    axis, pad = PALM.thumb_frame
    across, basis_pad, basis_axis = stations[4].basis
    assert basis_axis == pytest.approx(axis)
    assert basis_pad == pytest.approx(pad)
    # Orthonormal, right-handed: across = axis × pad as the generator built it.
    assert _dot(across, pad) == pytest.approx(0.0, abs=1e-12)
    assert _dot(across, axis) == pytest.approx(0.0, abs=1e-12)
    assert math.hypot(*across) == pytest.approx(1.0)


def test_every_chain_is_lifted_one_full_joint_above_its_root() -> None:
    """Base unit meets the root at an ordinary joint: two joint offsets up."""
    stations = station_plan(PALM, NAMING)

    assert {station.lift_mm for station in stations} == {54.0}
    assert stations[0].chain is PALM.finger
    assert stations[4].chain is PALM.thumb
