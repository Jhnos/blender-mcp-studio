"""Millimetre close-ups must not inherit Blender's 100 mm near clipping plane."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


def test_camera_keeps_small_pin_closeups_in_front_of_near_plane(monkeypatch):
    monkeypatch.setitem(sys.modules, "bpy", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mathutils", SimpleNamespace(Matrix=object, Vector=object))
    source = Path(__file__).resolve().parents[3] / "scripts/hollow_hinge_render.py"
    module_spec = importlib.util.spec_from_file_location("camera_fixture", source)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    camera = SimpleNamespace(data=SimpleNamespace(clip_start=0.1, clip_end=1000))
    module.configure_mechanical_camera(camera)
    assert camera.data.clip_start == 0.0001
    assert camera.data.clip_end == 2.0
    assert camera.data.clip_start < 0.006 < camera.data.clip_end
