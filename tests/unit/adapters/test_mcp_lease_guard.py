"""Scene-changing MCP tools refuse while a design run stage holds the shared Blender lease."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client

from src.adapters.mcp_server import create_mcp_server
from src.core.domain.design_run import StageName
from src.core.domain.mechanical_generation import BuiltPart, InstanceBuild, InstanceSummary
from src.core.use_cases.blender_lease import BlenderLease
from tests.unit.adapters.test_mcp_server import FakeSceneService

BUSY = "Blender is busy with design run stage mechanism; retry later"

GUARDED = {
    "create_object": {"object_type": "MESH"},
    "modify_object": {"name": "Cube"},
    "delete_object": {"name": "Cube"},
    "apply_material": {"object_name": "Cube", "material_name": "M"},
    "check_print_readiness": {},
    "run_verification_suite": {"suite_id": "s1"},
    "build_instance": {"slug": "hand-a"},
}
READ_ONLY = {
    "get_scene_info": {},
    "get_object_info": {"name": "Cube"},
    "blender_status": {},
}


class SlowCatalog:
    def __init__(self, lease: BlenderLease) -> None:
        self.lease = lease
        self.seen_holder: object = None
        self.release = asyncio.Event()

    async def list_instances(self):
        return (InstanceSummary("hand-a", "hand", ("a.stl",), "models/hand-a"),)

    async def build(self, slug):
        self.seen_holder = self.lease.holder
        await self.release.wait()
        return InstanceBuild(slug, "models/hand-a", (BuiltPart("a.stl", 12, (1.0, 2.0, 3.0)),))


def _server(lease: BlenderLease, catalog=None):
    scene = FakeSceneService()
    verification = AsyncMock()
    return (
        create_mcp_server(
            scene,
            scene,
            scene,
            verification,
            generation=catalog or SlowCatalog(lease),
            lease=lease,
        ),
        scene,
        verification,
    )


async def test_scene_tool_returns_busy_during_design_stage() -> None:
    lease = BlenderLease()
    mcp, scene, verification = _server(lease)
    async with Client(mcp) as client, lease.hold(StageName.MECHANISM):
        for name, args in GUARDED.items():
            result = await client.call_tool(name, args, raise_on_error=False)
            assert result.is_error, name
            assert result.content[0].text == BUSY, name
        for name, args in READ_ONLY.items():
            result = await client.call_tool(name, args, raise_on_error=False)
            assert not result.is_error, name
    assert [c[0] for c in scene.calls] == ["get_scene_info", "get_object_info", "status"]
    verification.run.assert_not_called()


async def test_scene_tools_run_normally_when_lease_is_free() -> None:
    lease = BlenderLease()
    mcp, scene, _ = _server(lease)
    async with Client(mcp) as client:
        result = await client.call_tool("create_object", {"object_type": "MESH"})
    assert not result.is_error and scene.calls[0][0] == "create_object"


async def test_build_instance_holds_lease() -> None:
    lease = BlenderLease()
    catalog = SlowCatalog(lease)
    mcp, _, _ = _server(lease, catalog)
    async with Client(mcp) as client:
        call = asyncio.create_task(client.call_tool("build_instance", {"slug": "hand-a"}))
        for _ in range(200):
            await asyncio.sleep(0.005)
            if catalog.seen_holder is not None:
                break
        assert catalog.seen_holder == "build_instance" and lease.holder == "build_instance"
        order: list[str] = []

        async def pipeline_stage() -> None:
            async with lease.hold(StageName.PRINT):
                order.append("stage")

        stage = asyncio.create_task(pipeline_stage())
        await asyncio.sleep(0.02)
        assert order == []  # the later pipeline stage waits instead of interleaving
        catalog.release.set()
        await call
        await stage
    assert order == ["stage"] and lease.holder is None


async def test_try_hold_busy_with_queued_waiter() -> None:
    lease = BlenderLease()
    ran: list[str] = []

    async def waiter() -> None:
        async with lease.hold(StageName.PRINT):
            ran.append("waiter")

    async with lease.hold(StageName.MECHANISM):
        queued = asyncio.create_task(waiter())
        await asyncio.sleep(0)  # the waiter is now queued on the lock
    # Released, with no await since: the lock is free but the woken waiter has not run.
    async with lease.try_hold(StageName.PRINT) as acquired:
        assert acquired is False
        assert ran == []  # and try_hold did not queue behind it
    await queued
    async with lease.try_hold(StageName.PRINT) as acquired:
        assert acquired is True


@pytest.mark.parametrize("holder", [StageName.PRINT, StageName.MECHANISM])
def test_busy_message_names_the_stage(holder: StageName) -> None:
    from src.adapters.mcp_server.errors import busy_message

    assert (
        busy_message(holder) == f"Blender is busy with design run stage {holder.value}; retry later"
    )
