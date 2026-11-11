"""Raw Blender coordinates must survive conversion to millimetres."""

import importlib.util
import struct
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from src.verification.mesh_integrity import require_triangle_surface


def single(value: float) -> float:
    return struct.unpack("f", struct.pack("f", value))[0]


class StoredVector:
    def __init__(self, values: tuple[float, float, float]) -> None:
        self.values = tuple(single(value) for value in values)

    def __iter__(self) -> Iterator[float]:
        return iter(self.values)

    def __mul__(self, scale: float) -> tuple[float, ...]:
        return tuple(single(value * scale) for value in self.values)


def load_oracle(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setitem(sys.modules, "bpy", ModuleType("bpy"))
    path = Path(__file__).resolve().parents[3] / "scripts/verify/native_scene_oracle.py"
    spec = importlib.util.spec_from_file_location("surface_capture_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_millimetre_capture_preserves_a_thin_closed_face(monkeypatch: pytest.MonkeyPatch) -> None:
    oracle = load_oracle(monkeypatch)
    # Actual stored-coordinate separation that Vector * 1000 rounded away.
    coordinates = [
        (-0.002261269371956587, 0.005948036909103394, 0.07900000363588333),
        (-0.0020287183579057455, 0.00559999980032444, 0.07899999618530273),
        (-0.0020287183579057455, 0.00559999980032444, 0.07900000363588333),
        (0.01, 0.01, 0.10),
    ]
    vertices = [SimpleNamespace(co=StoredVector(point)) for point in coordinates]
    faces = [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]
    calls: list[str] = []
    data = SimpleNamespace(
        vertices=vertices,
        loop_triangles=[SimpleNamespace(vertices=face) for face in faces],
        calc_loop_triangles=lambda: calls.append("triangulated"),
    )
    obj = SimpleNamespace(type="MESH", data=data)
    before = [tuple(vertex.co) for vertex in vertices]
    legacy = {"vertices": [list(vertex.co * 1000) for vertex in vertices], "faces": faces}
    with pytest.raises(ValueError, match="Zero-area triangle"):
        require_triangle_surface(legacy)

    surface = oracle.mesh_surface_mm(obj)

    assert require_triangle_surface(surface) == {"vertices": 4, "triangles": 4}
    assert surface["vertices"][1] != surface["vertices"][2]
    assert surface["vertices"][0][2] == before[0][2] * 1000.0
    assert [tuple(vertex.co) for vertex in vertices] == before
    assert calls == ["triangulated"]


def test_surface_capture_rejects_non_mesh(monkeypatch: pytest.MonkeyPatch) -> None:
    oracle = load_oracle(monkeypatch)
    with pytest.raises(ValueError, match="MESH"):
        oracle.mesh_surface_mm(SimpleNamespace(type="CURVE"))
