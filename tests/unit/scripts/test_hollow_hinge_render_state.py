import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


def test_render_views_restores_assembly_camera_before_blend_is_saved(monkeypatch, tmp_path):
    render = SimpleNamespace(resolution_x=1200, resolution_y=1500, filepath="assembly.png")
    scene = SimpleNamespace(render=render, display=SimpleNamespace(shading=SimpleNamespace()))
    fake_bpy = SimpleNamespace(
        context=SimpleNamespace(scene=scene),
        ops=SimpleNamespace(render=SimpleNamespace(render=lambda **kwargs: None)),
    )
    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=object, Vector=object))
    source = Path(__file__).resolve().parents[3] / "scripts/hollow_hinge_render.py"
    module_spec = importlib.util.spec_from_file_location("render_state_fixture", source)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    monkeypatch.setattr(module, "look_at", lambda *args: None)
    camera = SimpleNamespace(
        location=(0.145, -0.270, 0.145),
        rotation_euler=(1.0, 2.0, 3.0),
        data=SimpleNamespace(ortho_scale=0.226),
    )

    module.render_views(
        tmp_path,
        camera,
        [],
        SimpleNamespace(objects=[]),
        [],
        [],
        [],
        SimpleNamespace(hide_render=True),
        (0.0, 0.0, 0.0),
    )

    assert camera.location == (0.145, -0.270, 0.145)
    assert camera.rotation_euler == (1.0, 2.0, 3.0)
    assert camera.data.ortho_scale == 0.226
    assert (render.resolution_x, render.resolution_y) == (1200, 1500)
