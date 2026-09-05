"""Tests for the shared generator entry-point wrapper.

The wrapper hides every object the generator did not create so renders and
exports capture only the new geometry, then restores visibility in `finally`.
That restore is the part worth testing: a generator that raises half-way must
not leave the operator staring at an empty viewport.

`bpy` is stubbed the way the other script tests stub it — the module under test
is loaded from source with a fake `bpy` in `sys.modules`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

SOURCE = Path(__file__).resolve().parents[3] / "scripts" / "blender_generator_runner.py"


class FakeObject:
    def __init__(self, name: str, hide_render: bool = False, hide_viewport: bool = False) -> None:
        self.name = name
        self.hide_render = hide_render
        self.hide_viewport = hide_viewport


def _load(
    monkeypatch: pytest.MonkeyPatch, objects: list[FakeObject]
) -> tuple[ModuleType, list[str]]:
    collections: list[FakeObject] = []
    removed: list[str] = []

    fake_bpy = SimpleNamespace(
        data=SimpleNamespace(
            objects=_ListWithRemove(objects, removed),
            collections=_ListWithRemove(collections, removed),
        ),
        context=SimpleNamespace(scene=SimpleNamespace(objects=objects)),
    )
    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)

    spec = importlib.util.spec_from_file_location("generator_runner_fixture", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, removed


class _ListWithRemove(list[FakeObject]):
    """A bpy-style collection: iterable, with `remove(obj, do_unlink=...)`."""

    def __init__(self, backing: list[FakeObject], removed: list[str]) -> None:
        super().__init__()
        self._backing = backing
        self._removed = removed

    def __iter__(self) -> Any:
        return iter(self._backing)

    def remove(self, obj: FakeObject, do_unlink: bool = False) -> None:  # type: ignore[override]
        self._removed.append(obj.name)
        self._backing.remove(obj)


def test_clears_only_this_generators_previous_output(monkeypatch: pytest.MonkeyPatch) -> None:
    objects = [FakeObject("HH_body"), FakeObject("UserCube")]
    module, removed = _load(monkeypatch, objects)

    module.run_generator(lambda: None)

    assert removed == ["HH_body"]
    assert [obj.name for obj in objects] == ["UserCube"]


def test_hides_unrelated_objects_while_building(monkeypatch: pytest.MonkeyPatch) -> None:
    user_object = FakeObject("UserCube")
    module, _ = _load(monkeypatch, [user_object])
    seen: list[tuple[bool, bool]] = []

    module.run_generator(lambda: seen.append((user_object.hide_render, user_object.hide_viewport)))

    assert seen == [(True, True)], "the generator must not see unrelated geometry"


def test_restores_the_exact_prior_visibility(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restoring to False for everything would be wrong: prior state is preserved."""
    hidden = FakeObject("AlreadyHidden", hide_render=True, hide_viewport=True)
    visible = FakeObject("Visible")
    module, _ = _load(monkeypatch, [hidden, visible])

    module.run_generator(lambda: None)

    assert (hidden.hide_render, hidden.hide_viewport) == (True, True)
    assert (visible.hide_render, visible.hide_viewport) == (False, False)


def test_restores_visibility_when_the_build_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """The discriminating case: a half-failed build must not hide the user's scene."""
    user_object = FakeObject("UserCube")
    module, _ = _load(monkeypatch, [user_object])

    def failing_build() -> None:
        raise RuntimeError("boolean modifier failed")

    with pytest.raises(RuntimeError, match="boolean modifier failed"):
        module.run_generator(failing_build)

    assert (user_object.hide_render, user_object.hide_viewport) == (False, False)


def test_prefix_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    objects = [FakeObject("XX_old"), FakeObject("HH_keep")]
    module, removed = _load(monkeypatch, objects)

    module.run_generator(lambda: None, "XX_")

    assert removed == ["XX_old"]
