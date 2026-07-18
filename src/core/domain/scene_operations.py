"""Immutable values for client-neutral Blender scene operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ObjectType(StrEnum):
    """Object kinds supported by the first public scene-operation contract."""

    MESH = "MESH"
    CURVE = "CURVE"
    LIGHT = "LIGHT"
    CAMERA = "CAMERA"


@dataclass(frozen=True, slots=True)
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_list(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass(frozen=True, slots=True)
class ColorRGBA:
    red: float
    green: float
    blue: float
    alpha: float = 1.0

    def as_list(self) -> list[float]:
        return [self.red, self.green, self.blue, self.alpha]


@dataclass(frozen=True, slots=True)
class CreateObjectSpec:
    object_type: ObjectType
    name: str | None = None
    location: Vector3 = Vector3()
    scale: Vector3 = Vector3(1.0, 1.0, 1.0)


@dataclass(frozen=True, slots=True)
class ModifyObjectSpec:
    name: str
    location: Vector3 | None = None
    rotation: Vector3 | None = None
    scale: Vector3 | None = None
    visible: bool | None = None


@dataclass(frozen=True, slots=True)
class MaterialSpec:
    object_name: str
    material_name: str
    color: ColorRGBA | None = None
    metallic: float | None = None
    roughness: float | None = None


@dataclass(frozen=True, slots=True)
class SceneObjectSummary:
    name: str
    object_type: str
    location: Vector3


@dataclass(frozen=True, slots=True)
class SceneSummary:
    name: str
    object_count: int
    materials_count: int
    objects: tuple[SceneObjectSummary, ...]


@dataclass(frozen=True, slots=True)
class ObjectDetails:
    name: str
    object_type: str
    location: Vector3
    rotation: Vector3
    scale: Vector3
    visible: bool
    materials: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OperationReceipt:
    operation: str
    object_name: str
    message: str


@dataclass(frozen=True, slots=True)
class ViewportImage:
    png_bytes: bytes
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class BlenderStatus:
    connected: bool
    endpoint: str = "Blender addon socket"
