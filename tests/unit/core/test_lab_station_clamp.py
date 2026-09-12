"""Assembly requirements for the soft-lined, removable probe jaws."""

from src.core.domain.lab_station import ProbeClampSpec


def test_fasteners_do_not_cross_the_probe_or_break_out_of_jaw_edges() -> None:
    spec = ProbeClampSpec()
    assert spec.split_gap_mm >= 0.6
    assert len(spec.bolt_y_mm) == 2
    for center, radius in spec.bores(True):
        assert radius >= 4.2
        for bolt_y in spec.bolt_y_mm:
            assert abs(bolt_y - center) >= radius + 1.7 + 2
    assert spec.jaw_depth_mm / 2 - max(abs(y) for y in spec.bolt_y_mm) >= 3.3 + 1.5


def test_liner_flange_cannot_pass_through_jaw_bore() -> None:
    spec = ProbeClampSpec()
    for _, bore in spec.bores(True) + spec.bores(False):
        assert spec.liner_outer_radius(bore) < bore
        assert spec.liner_flange_radius(bore) >= bore + 0.8
        assert spec.liner_outer_radius(bore) - spec.liner_inner_radius(bore) >= 0.9


def test_invalid_jaw_geometry_is_rejected_before_blender() -> None:
    import pytest

    for overrides in ({"split_gap_mm": -1}, {"split_gap_mm": float("nan")}, {"jaw_depth_mm": 30}):
        with pytest.raises(ValueError, match="jaw"):
            ProbeClampSpec(**overrides)


def test_screen_sweep_includes_installed_probe_hardware() -> None:
    """Exercise the actual selection expression without importing Blender."""
    import ast
    from pathlib import Path
    from types import SimpleNamespace

    source = ast.parse(Path("scripts/lab_station_motion_check.py").read_text())
    function = next(
        n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "verify_motion"
    )
    assignment = next(
        n
        for n in function.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "fixed" for t in n.targets)
    )
    names = [
        "LS_HW_capillary_jaw_bolt",
        "LS_HW_pH_temp_keeper_nut",
        "LS_CHECK_clamp_copy",
        "LS_DIAG_fixed",
    ]
    objects = [SimpleNamespace(name=name, type="MESH") for name in names]
    namespace = {"bpy": SimpleNamespace(data=SimpleNamespace(objects=objects))}
    selected = eval(
        compile(ast.Expression(assignment.value), "screen-selection", "eval"), namespace
    )
    assert [obj.name for obj in selected] == names[:2]
