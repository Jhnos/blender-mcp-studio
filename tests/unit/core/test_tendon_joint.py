from dataclasses import FrozenInstanceError

import pytest

from src.core.domain.tendon_joint import TendonJointSpec


def test_two_cells_expose_four_rotational_degrees_of_freedom() -> None:
    spec = TendonJointSpec(cell_count=2)

    assert spec.degrees_of_freedom == 4
    assert spec.axis_names == ("J1_X", "J1_Y", "J2_X", "J2_Y")


def test_four_tendon_holes_are_symmetric_and_inside_the_printable_wall() -> None:
    spec = TendonJointSpec()

    assert spec.tendon_positions_mm == (
        (-10.0, -10.0),
        (-10.0, 10.0),
        (10.0, -10.0),
        (10.0, 10.0),
    )
    assert spec.edge_wall_mm >= spec.minimum_wall_mm


def test_socket_clearance_is_diametral_and_fdm_printable() -> None:
    spec = TendonJointSpec(pin_diameter_mm=5.0, radial_clearance_mm=0.3)

    assert spec.socket_diameter_mm == pytest.approx(5.6)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"radial_clearance_mm": 0.1}, "clearance"),
        ({"minimum_wall_mm": 0.7}, "wall"),
        ({"tendon_radius_mm": 19.0}, "tendon holes"),
        ({"cell_count": 0}, "cell_count"),
    ],
)
def test_unprintable_specs_fail_loudly(overrides: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        TendonJointSpec(**overrides)


def test_spec_is_immutable() -> None:
    spec = TendonJointSpec()

    with pytest.raises(FrozenInstanceError):
        spec.pin_diameter_mm = 6.0  # type: ignore[misc]
