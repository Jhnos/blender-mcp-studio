"""HTTP delivery adapter for building registered mechanical instances.

The slug is the whole input. There is no request body on purpose: a body would
be a second thing that could reach the code Blender runs, and the reason
`execute_code` is not a public tool is that no client gets to author that code.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Request

from src.core.domain.mechanical_generation import InstanceBuild, InstanceSummary
from src.core.ports.mechanical_generation_port import InstanceCatalogPort

router = APIRouter(prefix="/api")


@dataclass(frozen=True, slots=True)
class InstanceCatalog:
    instances: tuple[InstanceSummary, ...]


@router.get("/instances")
async def list_instances(request: Request) -> InstanceCatalog:
    service: InstanceCatalogPort = request.app.state.mechanical_generation
    return InstanceCatalog(instances=await service.list_instances())


@router.post("/instances/{slug}/build")
async def build_instance(slug: str, request: Request) -> InstanceBuild:
    service: InstanceCatalogPort = request.app.state.mechanical_generation
    return await service.build(slug)
