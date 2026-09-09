"""Outgoing port for running one registered instance's generator."""

from __future__ import annotations

from typing import Protocol

from src.core.domain.hand_instances import HandInstance
from src.core.domain.mechanical_generation import InstanceBuild, InstanceSummary


class InstanceBuilderPort(Protocol):
    """Runs a generator somewhere that has `bpy` and reports what it made.

    Takes the whole `HandInstance`, not a slug: the adapter must not look
    anything up. Everything the generated code is allowed to depend on comes
    from the registry entry the application already resolved, which is what
    keeps the request body out of the code Blender runs.

    Returns a typed DTO. A port that answered with `object` would push decoding
    the external dialect back into the use case — that is DEFERRALS D-001, and
    it was paid off once already.
    """

    async def build_instance(self, instance: HandInstance) -> InstanceBuild: ...


class InstanceCatalogPort(Protocol):
    """Incoming application boundary shared by any delivery adapter."""

    async def list_instances(self) -> tuple[InstanceSummary, ...]: ...

    async def build(self, slug: str) -> InstanceBuild: ...
