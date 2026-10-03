"""Reusable electrode configurations change data, not generator source."""

from dataclasses import FrozenInstanceError, replace

import pytest

from src.core.domain.lab_station import ELECTRODE_ASSEMBLIES, ProbeHeadSpec


def test_existing_and_cable_layout_share_the_same_module_contract() -> None:
    baseline = ELECTRODE_ASSEMBLIES["baseline"]
    candidate = ELECTRODE_ASSEMBLIES["cable-clearance"]
    assert baseline.head("capillary") == candidate.head("capillary")
    assert baseline.head("pH_temp").jaw_origin_mm == (0, 0, -38)
    assert candidate.head("pH_temp").jaw_origin_mm == (-14, 0, -38)
    assert baseline.vessel_shift_mm == (3.5, 0, 0)
    assert candidate.vessel_shift_mm == (3.5, -6, 0)
    assert baseline.head("pH_temp").mount_offset_mm == candidate.head("pH_temp").mount_offset_mm


def test_custom_variant_moves_jaw_and_probe_from_one_coordinate_definition() -> None:
    head = replace(ProbeHeadSpec(dual=True), forward_mm=12, inward_mm=4)
    assert head.jaw_origin_mm == (-12, -4, -38)
    assert head.probe_shift_mm(1) == (4, 12, 0)
    assert head.probe_shift_mm(-1) == (-4, 12, 0)
    with pytest.raises(ValueError):
        head.probe_shift_mm(0)


def test_neck_retains_jaw_overlap_and_clears_shifted_clamp_bolt() -> None:
    head = ELECTRODE_ASSEMBLIES["cable-clearance"].head("pH_temp")
    x, y, z = head.neck_center_mm
    width, depth, height = head.neck_size_mm
    assert z - height / 2 == -32
    assert z - height / 2 < head.jaw_origin_mm[2] + 9
    assert x - width / 2 < head.jaw_origin_mm[0] + head.jaw.jaw_width_mm / 2
    assert y - depth / 2 < head.jaw.jaw_depth_mm / 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("forward_mm", -1),
        ("forward_mm", float("nan")),
        ("inward_mm", float("inf")),
        ("inward_mm", 25),
    ],
)
def test_invalid_configuration_is_rejected_before_scene_mutation(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        replace(ProbeHeadSpec(), **{field: value})


def test_registry_cannot_be_mutated_and_unknown_head_is_not_silently_pH() -> None:
    with pytest.raises(TypeError):
        ELECTRODE_ASSEMBLIES["typo"] = ELECTRODE_ASSEMBLIES["baseline"]  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        ELECTRODE_ASSEMBLIES["baseline"].capillary.forward_mm = 5  # type: ignore[misc]
    with pytest.raises(ValueError, match="head"):
        ELECTRODE_ASSEMBLIES["baseline"].head("unknown")
