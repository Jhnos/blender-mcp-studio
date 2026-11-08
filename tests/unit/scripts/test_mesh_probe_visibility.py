"""Read-only probes must work on deliberately hidden manufacturing layouts."""

from scripts.verify.mesh_probe_verify_real import probe_code


def test_ray_probe_reads_mesh_data_without_requiring_visible_evaluated_object():
    code = probe_code({})
    assert "body.ray_cast" not in code
    assert "local_tree.ray_cast" in code
    assert "local_mesh.from_mesh(body.data)" in code
    assert "local_mesh.free()" in code


def test_section_probe_is_closed_data_and_does_not_write_a_mesh_back():
    import ast

    from scripts.verify.mesh_probe_verify_real import section_probe_code

    config = {"owners": ["part'; forbidden()"], "frame": "frame", "planes_x_mm": [0.2]}
    code = section_probe_code(config)
    tree = ast.parse(code)
    inner = ast.parse(ast.literal_eval(tree.body[0].value.args[0]))
    assert ast.literal_eval(inner.body[0].value) == config
    assert "editable.from_mesh(part.data)" in code
    assert ".to_mesh(" not in code and "editable.free()" in code


def test_invalid_section_requests_are_rejected_before_engine_access():
    import pytest

    from scripts.verify.mesh_probe_verify_real import section_probe_code

    good = {"owners": ["part"], "frame": "frame", "planes_x_mm": [0.2]}
    for changes in (
        {"owners": []},
        {"owners": "part"},
        {"owners": ["part", "part"]},
        {"frame": None},
        {"planes_x_mm": [True]},
        {"planes_x_mm": [float("nan")]},
        {"planes_x_mm": list(range(33))},
        {"extra": "code"},
    ):
        with pytest.raises(ValueError):
            section_probe_code({**good, **changes})


def test_section_probe_does_not_share_the_callers_script_namespace():
    import ast

    from scripts.verify.mesh_probe_verify_real import section_probe_code

    program = ast.parse(
        section_probe_code({"owners": ["part"], "frame": "frame", "planes_x_mm": [0.1]})
    )
    call = program.body[0].value
    assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "exec"
    assert isinstance(call.args[1], ast.Dict) and not call.args[1].keys
