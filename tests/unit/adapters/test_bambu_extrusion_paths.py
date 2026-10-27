"""Streaming Bambu moves retain modal state without treating purge or retraction as model paths."""

import pytest

from src.adapters.slicing.gcode_paths import iter_extrusions

PREFIX = [
    "; FEATURE: Custom",
    "G90",
    "M83",
    "G92 E0",
    "G0 X10 Y10 Z.2",
    "; CHANGE_LAYER",
    "; LAYER_HEIGHT: .2",
    "; LINE_WIDTH: .5",
    "; FEATURE: Support",
]


def parse(*lines, prefix=PREFIX):
    return list(iter_extrusions([*prefix, *lines]))


def test_compact_words_and_inline_comments_yield_actual_model_extrusion():
    (one,) = parse("g1x11e.2 ; travel is not the feature name")
    assert one.start_mm == (10, 10, 0.2) and one.end_mm == (11, 10, 0.2)
    assert (one.role, one.width_mm, one.height_mm, one.layer_index) == ("Support", 0.5, 0.2, 0)


def test_retraction_unretraction_and_travel_update_state_without_becoming_deposition():
    paths = parse("G1 E-1", "G1 E1", "G0 X20 Y20", "G1 X21 E.2")
    assert len(paths) == 1 and paths[0].start_mm == (20, 20, 0.2)


def test_absolute_extrusion_and_retraction_use_previous_counter():
    paths = parse("M82", "G1 X11 E10", "G1 X12 E11", "G1 X13 E9", "G1 X14 E10")
    assert len(paths) == 3 and paths[-1].start_mm[0] == 13


def test_global_relative_mode_also_makes_e_relative_as_in_bambu_processor():
    paths = parse("G91", "M82", "G1 X1 Y-1 E.2", "G1 X1 E.2")
    assert [p.end_mm for p in paths] == [(11, 9, 0.2), (12, 9, 0.2)]


def test_g92_coordinate_reset_preserves_physical_position_and_changes_absolute_origin():
    (one,) = parse("G92 X0", "G1 X1 E1")
    assert one.start_mm == (10, 10, 0.2) and one.end_mm == (11, 10, 0.2)


def test_arc_uses_relative_center_even_with_absolute_endpoints():
    (one,) = parse("G3 X11 Y11 I0 J1 E1")
    assert one.center_xy_mm == (10, 11) and one.end_mm == (11, 11, 0.2)
    assert not one.clockwise
    assert one.measure().xy_length_mm > 1.5


def test_same_endpoint_arc_is_a_full_circle_not_unretraction():
    (one,) = parse("G2 I1 J0 E2")
    assert one.start_mm == one.end_mm and one.measure().xy_length_mm > 6


def test_custom_purge_is_excluded_but_still_updates_the_start_of_following_print_moves():
    paths = parse("; FEATURE: Custom", "G1 X30 E5", "; FEATURE: Brim", "G1 X31 E1")
    assert len(paths) == 1 and paths[0].role == "Brim" and paths[0].start_mm[0] == 30


@pytest.mark.parametrize(
    "command",
    [
        "G20",
        "G5 X11 Y11 E1",
        "G1 Xnan E1",
        "G1 X11 X12 E1",
        "G2 X11 R1 E1",
        "G18\nG2 X11 I1 E1",
        "G90.1\nG2 X11 I1 E1",
    ],
)
def test_unknown_units_geometry_and_malformed_words_fail_closed(command):
    with pytest.raises(ValueError):
        parse(*command.splitlines())


@pytest.mark.parametrize("omitted", ["; CHANGE_LAYER", "; LINE_WIDTH: .5", "; LAYER_HEIGHT: .2"])
def test_missing_deposition_metadata_cannot_be_substituted_with_assumed_defaults(omitted):
    with pytest.raises(ValueError):
        parse("G1 X11 E1", prefix=[p for p in PREFIX if p != omitted])


def test_absolute_e_without_a_known_previous_counter_cannot_be_certified():
    with pytest.raises(ValueError):
        parse("M82", "G1 X11 E1", prefix=[p for p in PREFIX if p != "G92 E0"])


@pytest.mark.parametrize("command", ["G5.1 X500 E1", "N100 G1 X500 E1", "G1 X11 G91 Y1 E1"])
def test_unparsed_print_blocks_cannot_silently_disappear_from_the_envelope(command):
    with pytest.raises(ValueError):
        parse(command)


def test_bambu_p1_arc_hop_updates_z_without_becoming_a_deposition_path():
    paths = parse("G3 Z.6 I-1.169 J-.339 P1 F36000", "G1 Z.4", "G1 X11 E.1")
    assert len(paths) == 1 and paths[0].start_mm == (10, 10, 0.4)


def test_multiturn_deposition_cannot_be_mistaken_for_a_single_arc():
    with pytest.raises(ValueError):
        parse("G3 X11 Y11 I0 J1 P1 E1")


def test_object_annotations_bind_each_path_to_its_current_slice_label():
    paths = parse("; OBJECT_ID: 32", "G1 X11 E.2", "; OBJECT_ID: 36", "G1 X12 E.2")
    assert [p.object_id for p in paths] == [32, 36]


def test_shared_object_sentinel_is_explicitly_unassigned_not_a_model_identity():
    (one,) = parse("; OBJECT_ID: -1", "G1 X11 E.2")
    assert one.object_id is None
