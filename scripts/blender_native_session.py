"""Isolate a verified native scene without replacing the operator's active file.

Internal Blender execution primitive, not a public script/path interface. The
application owns the source snapshot, output directory, recipe and Blender lease.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from collections.abc import Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from types import MappingProxyType, TracebackType
from typing import Literal

import bpy

from src.core.domain.native_revision import (
    NativeSceneError,
    NativeSceneRestorationError,
    SourceArtifact,
)
from src.infrastructure.narrowing import as_mapping, as_sequence


def _ids() -> set[bpy.types.ID]:
    return set(bpy.data.user_map())


def _value(value: object, names: Mapping[bpy.types.ID, str]) -> object:
    if isinstance(value, bpy.types.ID):
        return (value.bl_rna.identifier, names.get(value, value.name), value.as_pointer())
    convert = getattr(value, "to_dict", None) or getattr(value, "to_list", None)
    if callable(convert):
        value = convert()
    mapping = as_mapping(value)
    if mapping is not None:
        return {key: _value(item, names) for key, item in mapping.items()}
    sequence = as_sequence(value)
    if sequence is not None:
        return [_value(item, names) for item in sequence]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise NativeSceneError("unsupported original custom-property value")


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class NativeSceneSession:
    def __init__(self, source: Path, expected: SourceArtifact) -> None:
        self._source = source.resolve()
        self._expected = expected
        self._active = False
        self._closed = False
        self._restoration_verified = False
        self._original: set[bpy.types.ID] = set()
        self._names: dict[bpy.types.ID, str] = {}
        self._objects: dict[str, bpy.types.Object] = {}
        self._override: AbstractContextManager[object] | None = None
        self._pending: tuple[Path, Path] | None = None

    @property
    def restoration_verified(self) -> bool:
        """True only after the full original snapshot matched following cleanup."""
        return self._restoration_verified

    @property
    def objects(self) -> Mapping[str, bpy.types.Object]:
        if not self._active:
            raise NativeSceneError("native scene session is not active")
        return MappingProxyType(self._objects)

    @property
    def scene(self) -> bpy.types.Scene:
        if not self._active:
            raise NativeSceneError("native scene session is not active")
        return self._scene

    def _check_source(self) -> None:
        if (
            self._source.suffix.lower() != ".blend"
            or type(self._expected.size_bytes) is not int
            or self._expected.size_bytes <= 0
            or not isinstance(self._expected.sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self._expected.sha256) is None
        ):
            raise NativeSceneError("invalid native snapshot identity")
        try:
            with self._source.open("rb") as handle:
                before = os.fstat(handle.fileno())
                if before.st_size != self._expected.size_bytes:
                    raise NativeSceneError("native snapshot size mismatch")
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
                after = os.fstat(handle.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ) or digest != self._expected.sha256:
                raise NativeSceneError("native snapshot fingerprint mismatch")
        except OSError as exc:
            raise NativeSceneError("native snapshot is unavailable") from exc

    def _drivers(self, obj: bpy.types.ID) -> object:
        animation = getattr(obj, "animation_data", None)
        if animation is None:
            return None
        return {
            "action": _value(animation.action, self._names),
            "drivers": [
                [
                    curve.data_path,
                    curve.array_index,
                    curve.mute,
                    curve.driver.type,
                    curve.driver.expression,
                    curve.driver.use_self,
                    [
                        [
                            variable.name,
                            variable.type,
                            [
                                [
                                    _value(target.id, self._names),
                                    target.data_path,
                                    target.bone_target,
                                    target.transform_type,
                                    target.transform_space,
                                    getattr(target, "rotation_mode", None),
                                ]
                                for target in variable.targets
                            ],
                        ]
                        for variable in curve.driver.variables
                    ],
                ]
                for curve in animation.drivers
            ],
        }

    def _property_ui(self, obj: bpy.types.ID) -> object:
        result: dict[str, object] = {}
        keys = obj.keys()
        for key in keys:
            try:
                result[key] = _value(obj.id_properties_ui(key).as_dict(), self._names)
            except TypeError:
                result[key] = None  # Group properties have no editable UI metadata.
        return result

    def _snapshot(self) -> str:
        rows = []
        for obj in self._original:
            props = _value(dict(obj.items()), self._names)
            row: dict[str, object] = {
                "id": _value(obj, self._names),
                "props": props,
                "property_ui": self._property_ui(obj),
                "drivers": self._drivers(obj),
            }
            if isinstance(obj, bpy.types.Object):
                row.update(
                    basis=[tuple(v) for v in obj.matrix_basis],
                    parent_inverse=[tuple(v) for v in obj.matrix_parent_inverse],
                    parent=_value(obj.parent, self._names),
                    rotation_mode=obj.rotation_mode,
                    visibility=[obj.hide_render, obj.hide_viewport],
                    data=_value(obj.data, self._names),
                )
            if isinstance(obj, bpy.types.Mesh):
                row["mesh"] = _hash(
                    [
                        [tuple(v.co) for v in obj.vertices],
                        [tuple(e.vertices) for e in obj.edges],
                        [(tuple(p.vertices), p.material_index) for p in obj.polygons],
                        [_value(m, self._names) for m in obj.materials],
                    ]
                )
            rows.append(row)
        rows.sort(key=lambda row: str(row["id"]))
        layers = []
        for scene in self._original:
            if not isinstance(scene, bpy.types.Scene):
                continue
            for layer in scene.view_layers:
                layers.append(
                    [
                        self._names[scene],
                        layer.name,
                        _value(layer.objects.active, self._names),
                        sorted(
                            (
                                self._names[obj],
                                obj.select_get(view_layer=layer),
                                obj.hide_get(view_layer=layer),
                            )
                            for obj in layer.objects
                        ),
                    ]
                )
        return _hash(
            {
                "ids": rows,
                "layers": sorted(layers),
                "file": bpy.data.filepath,
                "window_scene": _value(self._window.scene, self._names) if self._window else None,
            }
        )

    def __enter__(self) -> NativeSceneSession:
        if self._active or self._closed:
            raise NativeSceneError("native scene sessions cannot be reused")
        self._check_source()
        if bpy.data.filepath and Path(bpy.data.filepath).resolve() == self._source:
            raise NativeSceneError("native input must be a separate verified snapshot")
        self._original = _ids()
        if any(item.library for item in self._original):
            raise NativeSceneError("original linked data cannot be safely namespaced")
        if any(obj.mode != "OBJECT" for obj in bpy.data.objects):
            raise NativeSceneError("native revision requires original objects in object mode")
        self._names = {item: item.name for item in self._original}
        self._window = bpy.context.window
        self._layer = bpy.context.view_layer
        self._window_scene = self._window.scene if self._window else None
        self._window_layer = self._window.view_layer if self._window else None
        self._layer.update()
        self._before = self._snapshot()
        try:
            prefix = "__native_" + uuid.uuid4().hex[:16]
            for index, item in enumerate(self._original):
                if item.is_property_readonly("name"):
                    if not isinstance(item, bpy.types.VectorFont) or item.filepath != "<builtin>":
                        raise NativeSceneError("original ID cannot be safely namespaced")
                else:
                    item.name = f"{prefix}_{index:06d}"
            try:
                with bpy.data.libraries.load(str(self._source), link=False) as (source, target):
                    target.scenes = source.scenes
                    source_names = tuple(source.objects)
                    target.objects = list(source_names)
            except (OSError, RuntimeError, ValueError) as exc:
                raise NativeSceneError("native snapshot could not be loaded") from exc
            if len(target.scenes) != 1 or not target.objects or not all(target.objects):
                raise NativeSceneError("native input must contain one complete scene")
            if any(item.library for item in _ids() - self._original):
                raise NativeSceneError("native input contains external linked data")
            self._scene = target.scenes[0]
            self._objects = {obj.name: obj for obj in target.objects}
            if set(self._scene.objects) != set(target.objects):
                raise NativeSceneError("native scene does not contain every source object")
            if len(self._objects) != len(target.objects) or set(self._objects) != set(source_names):
                raise NativeSceneError("native object identities are ambiguous")
            self._override = bpy.context.temp_override(
                scene=self._scene,
                view_layer=self._scene.view_layers[0],
                collection=self._scene.collection,
                layer_collection=self._scene.view_layers[0].layer_collection,
            )
            self._override.__enter__()
            self._active = True
            bpy.context.view_layer.update()
            return self
        except BaseException:
            self._restore()
            raise

    def _boundaries(self) -> None:
        current = _ids()
        if not self._original <= current:
            raise NativeSceneRestorationError("original ID was removed during native revision")
        try:
            expected_objects = set(self._objects.values())
            if not expected_objects <= current or set(self._scene.objects) != expected_objects:
                raise NativeSceneError("native object identity population changed")
            if any(obj.name != name for name, obj in self._objects.items()):
                raise NativeSceneError("native object identity name changed")
        except ReferenceError as exc:
            raise NativeSceneError("native object identity was replaced or removed") from exc
        staged = current - self._original
        for used, users in bpy.data.user_map().items():
            if (used in self._original and users & staged) or (
                used in staged and users & self._original
            ):
                raise NativeSceneError("native revision has a cross-boundary dependency")
        if self._snapshot() != self._before:
            raise NativeSceneRestorationError("original data changed during native revision")

    def write_native(self, output: Path) -> None:
        if not self._active or self._pending is not None:
            raise NativeSceneError("native output requires one active, unsaved session")
        output = output.absolute()
        if output.resolve() == self._source or output.exists() or output.is_symlink():
            raise NativeSceneError("native output must be new and distinct from its source")
        if output.suffix.lower() != ".blend" or not output.parent.is_dir():
            raise NativeSceneError("native output requires an existing job directory")
        self._check_source()
        self._boundaries()
        descriptor, name = tempfile.mkstemp(
            prefix=".native-pending-", suffix=".blend", dir=output.parent
        )
        os.close(descriptor)
        temporary = Path(name)
        try:
            bpy.data.libraries.write(
                str(temporary),
                {self._scene, *self._objects.values()},
                path_remap="NONE",
                compress=True,
            )
            self._pending = temporary, output
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def _restore(self) -> None:
        try:
            if self._override is not None:
                self._override.__exit__(None, None, None)
                self._override = None
            self._active = False
            if self._window is not None:
                self._window.scene = self._window_scene
                self._window.view_layer = self._window_layer
            current = _ids()
            missing = self._original - current
            bpy.data.batch_remove(ids=current - self._original)
            for item in self._original & _ids():
                if item.name != self._names[item]:
                    item.name = self._names[item]
            self._layer.update()
            if missing or _ids() != self._original or self._snapshot() != self._before:
                raise NativeSceneRestorationError(
                    "original scene restoration could not be verified"
                )
            self._restoration_verified = True
        except (RuntimeError, ReferenceError, ValueError, AttributeError) as exc:
            raise NativeSceneRestorationError("original scene restoration failed") from exc
        finally:
            self._closed = True

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> Literal[False]:
        try:
            self._restore()
            if kind is None and self._pending is not None:
                self._check_source()
                try:
                    os.link(*self._pending)  # Atomic no-overwrite publication after restoration.
                except OSError as exc:
                    raise NativeSceneError(
                        "native output could not be published exclusively"
                    ) from exc
        finally:
            if self._pending is not None:
                self._pending[0].unlink(missing_ok=True)
        return False
