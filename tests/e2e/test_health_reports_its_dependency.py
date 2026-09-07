"""`/api/health` must not answer `ok` while the thing it exists to front is unusable.

Observed on the production Mac mini, 2026-09-07: the API answered
`{"status": "ok", "blender": "disconnected"}` for hours. Blender was alive and
listening on 9876 the whole time and direct socket connections to it worked — only the
API's own link was dead. Every contract run died at the readiness step, for V1's
contracts as much as V2's, while the health check kept saying everything was fine.

`docs/LESSONS_LEARNED.md` has already booked this class three times: "health/status 訊號
與其宣稱守護的相依性脫鉤" (2026-07-15), "Process 已啟動不等於它的相依服務已 ready"
(2026-08-11), and "重啟被依賴的服務，不等於依賴它的那一端也回復了" (2026-09-05). The
project's own rule is that a class booked three times stops being a discipline and becomes
a gate, so `status` is derived from the dependency here rather than asserted beside it.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.runtime import AppRuntime
from src.core.domain.command import Command
from src.core.ports.blender_port import BlenderPort
from src.core.ports.mcp_port import ToolResult


class _Blender(BlenderPort):
    """A Blender port whose link state the test dictates."""

    def __init__(self, *, connected: bool) -> None:
        self._connected = connected
        self.connect_calls = 0

    async def connect(self) -> None:
        self.connect_calls += 1

    async def disconnect(self) -> None:
        return None

    async def is_connected(self) -> bool:
        return self._connected

    async def execute(self, command: Command) -> ToolResult:
        return ToolResult(success=True, output="ok")

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        return ToolResult(success=False, output=None, error="unused by health tests")

    async def get_scene_info(self) -> dict[str, object]:
        return {}


class _Exploding(BlenderPort):
    """A link that cannot even be asked — the worst case must not read as healthy."""

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def is_connected(self) -> bool:
        raise RuntimeError("socket is gone")

    async def execute(self, command: Command) -> ToolResult:
        return ToolResult(success=True, output="ok")

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        return ToolResult(success=False, output=None, error="unused by health tests")

    async def get_scene_info(self) -> dict[str, object]:
        return {}


def _runtime(blender: BlenderPort) -> AppRuntime:
    marker = MagicMock()
    return AppRuntime(
        blender=blender,
        scene_operations=marker,
        batch_transform=marker,
        scene_export=marker,
        print_readiness=marker,
        event_bus=marker,
        adapter_factory=marker,
        sandbox=marker,
        sanitizer=marker,
        vision=None,
        prompt_builder=marker,
        session_store=marker,
        snapshot_store=marker,
        polyhaven=marker,
        text3d=None,
        conversational_modeling=marker,
        modeling_pipeline=marker,
        iterative_refinement=None,
    )


def _health(blender: BlenderPort) -> dict[str, str]:
    app = create_app(runtime=_runtime(blender), require_identity=False)
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    return body


def test_health_reports_ok_only_while_blender_is_reachable() -> None:
    body = _health(_Blender(connected=True))

    assert body["blender"] == "connected"
    assert body["status"] == "ok"


@pytest.mark.parametrize(
    "blender",
    [
        pytest.param(_Blender(connected=False), id="the link is down"),
        pytest.param(_Exploding(), id="the link cannot even be asked"),
    ],
)
def test_health_never_says_ok_when_blender_is_unusable(blender: BlenderPort) -> None:
    """The discriminating half: this goes red the moment `status` is hardcoded again."""
    body = _health(blender)

    assert body["blender"] == "disconnected"
    assert body["status"] != "ok", (
        "health answered ok while Blender was unusable — this is the exact response "
        "that let a dead link sit unnoticed on the production machine"
    )
    assert body["status"] == "degraded"
