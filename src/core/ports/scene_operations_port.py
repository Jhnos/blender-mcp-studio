"""Incoming ports for client-neutral Blender scene operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.core.domain.scene_operations import (
    BlenderStatus,
    CreateObjectSpec,
    MaterialSpec,
    ModifyObjectSpec,
    ObjectDetails,
    OperationReceipt,
    SceneSummary,
    ViewportImage,
)


@runtime_checkable
class SceneQueryPort(Protocol):
    async def status(self) -> BlenderStatus: ...

    async def get_scene_info(self) -> SceneSummary: ...

    async def get_object_info(self, name: str) -> ObjectDetails: ...

    async def get_viewport_screenshot(self, max_size: int = 800) -> ViewportImage: ...


@runtime_checkable
class SceneCommandPort(Protocol):
    async def create_object(self, spec: CreateObjectSpec) -> OperationReceipt: ...

    async def modify_object(self, spec: ModifyObjectSpec) -> OperationReceipt: ...

    async def delete_object(self, name: str) -> OperationReceipt: ...

    async def apply_material(self, spec: MaterialSpec) -> OperationReceipt: ...
