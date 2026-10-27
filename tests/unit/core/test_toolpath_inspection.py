"""Software acceptance uses complete bead envelopes and explicit bed-contact witnesses."""

from dataclasses import replace

import pytest

from src.core.domain.extrusion import BuildVolume, ExtrusionPath
from src.core.use_cases.toolpath_inspection import inspect_extrusions

VOLUME = BuildVolume((0, 0, 0), (10, 10, 10))


def path(role="Support", **changes):
    values = dict(
        start_mm=(1, 1, 0.2),
        end_mm=(2, 1, 0.2),
        width_mm=0.5,
        height_mm=0.2,
        role=role,
        layer_index=0,
    )
    values.update(changes)
    return ExtrusionPath(**values)


def test_streamed_report_counts_feature_and_bed_contact_without_collecting_paths():
    def once():
        yield path()
        yield path("Brim")
        yield path("Support interface", start_mm=(1, 1, 0.4), end_mm=(2, 1, 0.4), layer_index=1)

    result = inspect_extrusions(once(), VOLUME, require_support=True, require_brim=True)
    assert result.passed and result.path_count == 3 and result.bed_contact_paths == 2
    assert result.support_paths == 2 and result.brim_paths == 1
    assert result.bed_support_paths == 1 and result.bed_brim_paths == 1
    assert result.minimum_mm == (0.75, 0.75, 0.0)
    assert result.maximum_mm == (2.25, 1.25, 0.4)


def test_centerline_inside_bed_still_fails_when_bead_width_crosses_edge():
    result = inspect_extrusions([path(start_mm=(0.1, 1, 0.2), end_mm=(0.1, 2, 0.2))], VOLUME)
    assert not result.passed and result.outside_paths == 1


def test_arc_endpoints_inside_bed_do_not_hide_an_outside_sweep():
    arc = path(start_mm=(1, 1, 0.2), end_mm=(2, 2, 0.2), center_xy_mm=(1, 2), clockwise=True)
    result = inspect_extrusions([arc], VOLUME)
    assert not result.passed and result.minimum_mm[0] < 0


def test_all_contact_evidence_and_feature_counts_are_retained_after_an_outside_move():
    result = inspect_extrusions([path(end_mm=(20, 1, 0.2)), path("Brim")], VOLUME)
    assert result.path_count == 2 and result.brim_paths == 1 and not result.passed


def test_no_deposition_cannot_be_a_successful_print():
    result = inspect_extrusions(iter(()), VOLUME)
    assert not result.passed and result.path_count == 0 and result.minimum_mm is None


def test_floating_first_layer_requires_a_real_bed_contact_witness():
    result = inspect_extrusions([path(start_mm=(1, 1, 1), end_mm=(2, 1, 1))], VOLUME)
    assert not result.passed and result.bed_contact_paths == 0


def test_brim_above_bed_cannot_count_as_first_layer_adhesion():
    result = inspect_extrusions(
        [path(), path("Brim", start_mm=(1, 1, 1), end_mm=(2, 1, 1))], VOLUME, require_brim=True
    )
    assert not result.passed and result.brim_paths == 1 and result.bed_brim_paths == 0


def test_support_is_optional_until_a_model_contract_requires_it():
    assert inspect_extrusions([path("Outer wall")], VOLUME).passed
    assert not inspect_extrusions([path("Outer wall")], VOLUME, require_support=True).passed


def test_unbounded_feature_names_cannot_make_streaming_analysis_grow_without_limit():
    with pytest.raises(ValueError):
        inspect_extrusions((path(f"role-{i}") for i in range(65)), VOLUME)


@pytest.mark.parametrize("maximum", [(0, 10, 10), (10, float("inf"), 10)])
def test_build_volume_requires_finite_positive_dimensions(maximum):
    with pytest.raises(ValueError):
        BuildVolume((0, 0, 0), maximum)


def test_each_expected_slice_object_needs_its_own_bed_contact():
    values = [
        replace(path(), object_id=8),
        replace(path(start_mm=(1, 1, 1), end_mm=(2, 1, 1)), object_id=12),
    ]
    report = inspect_extrusions(values, VOLUME, expected_object_ids=frozenset({8, 12}))
    assert not report.passed
    assert {o.object_id: o.bed_contact_paths for o in report.objects} == {8: 1, 12: 0}


def test_missing_and_unknown_slice_labels_cannot_be_hidden_by_total_path_count():
    values = [replace(path(), object_id=8), replace(path(), object_id=16)]
    assert not inspect_extrusions(values, VOLUME, expected_object_ids=frozenset({8, 12})).passed


def test_unassigned_model_paths_cannot_qualify_a_named_object_inventory():
    report = inspect_extrusions([path()], VOLUME, expected_object_ids=frozenset({8}))
    assert not report.passed and report.unassigned_paths == 1


def test_complete_named_object_contacts_have_a_discriminating_positive_control():
    report = inspect_extrusions(
        [replace(path(), object_id=i) for i in (8, 12)],
        VOLUME,
        expected_object_ids=frozenset({8, 12}),
    )
    assert report.passed and report.unassigned_paths == 0


def test_disabled_generated_structures_cannot_be_hidden_by_valid_bed_bounds():
    assert not inspect_extrusions([path()], VOLUME, allow_support=False).passed
    assert not inspect_extrusions([path("Brim")], VOLUME, allow_brim=False).passed
    assert inspect_extrusions(
        [path("Outer wall")], VOLUME, allow_support=False, allow_brim=False
    ).passed


def test_accumulated_length_cannot_overflow_finite_report():
    huge = path(start_mm=(0, 0, 0.2), end_mm=(9e307, 0, 0.2))
    with pytest.raises(ValueError, match="accumulated"):
        inspect_extrusions([huge, huge, huge], VOLUME)
