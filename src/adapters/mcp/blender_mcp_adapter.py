"""Blender MCP adapter — wraps socket communication with ahujasid/blender-mcp addon."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from src.adapters.blender_scene_decoding import decode_object_details, decode_scene_summary
from src.adapters.mcp.blender_tool_codegen import is_translatable, translate
from src.adapters.viewport_capture import capture_viewport
from src.core.domain.command import Command
from src.core.domain.exceptions import BlenderConnectionError, SceneOperationError
from src.core.domain.scene_operations import ObjectDetails, SceneSummary, ViewportImage
from src.core.ports.blender_port import BlenderPort
from src.core.ports.code_sandbox_port import CodeSandboxPort
from src.core.ports.mcp_port import MCPPort, ToolDefinition, ToolResult
from src.infrastructure.narrowing import as_str_keyed

logger = logging.getLogger(__name__)

_EXECUTE_CODE_TOOL = "execute_code"


class BlenderSocketClient:
    """Low-level TCP socket client for the Blender MCP addon (ahujasid protocol).

    Protocol (from addon source):
      - Send: raw JSON bytes (no newline), e.g. {"type": "execute_code", "params": {"code": "..."}}
      - Recv: raw JSON bytes (no newline terminator) — buffer until parseable
    """

    def __init__(self, host: str, port: int, timeout: float = 30.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()  # serialize concurrent calls on single socket

    async def connect(self) -> None:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=10.0,
            )
        except (TimeoutError, ConnectionRefusedError, OSError) as e:
            raise BlenderConnectionError(
                f"Cannot connect to Blender at {self._host}:{self._port}"
            ) from e

    async def disconnect(self) -> None:
        """Let go of the socket, tolerating a peer that already tore it down.

        `wait_closed()` re-raises whatever killed the transport, so a socket the addon
        reset raises `ConnectionResetError` *here* — turning "the connection is already
        gone" into "we failed to let go of it", during teardown, where there is nothing
        useful a caller could do about it. The references are dropped first so a raising
        close cannot leave a dead reader and writer behind for the next call to find.
        """
        writer, self._writer, self._reader = self._writer, None, None
        if writer is None:
            return
        writer.close()
        with contextlib.suppress(OSError, ConnectionError):
            await writer.wait_closed()

    async def _redial(self) -> None:
        """Drop whatever is left of the old socket and open a fresh one.

        Closing first matters: `connect()` overwrites the reader and writer, so
        redialling without it would leak the dead pair. `connect()` itself is *not*
        forgiving — an addon that is still absent raises `BlenderConnectionError`
        exactly as it did before any of this existed.
        """
        await self.disconnect()
        await self.connect()

    @staticmethod
    def _decode_response(raw: bytes) -> dict[str, object]:
        """Decode the addon's JSON reply into a genuinely typed mapping.

        Propagates json.JSONDecodeError while the buffer is still incomplete —
        send_command relies on that to keep reading. The ValueError below is
        deliberately not a BlenderConnectionError: a well-formed reply of the
        wrong shape is not a dropped connection, and call_tool's `except
        Exception` should turn it into a failed ToolResult like any other.
        """
        parsed: object = json.loads(raw.decode("utf-8"))
        narrowed = as_str_keyed(parsed, context="Blender response")
        if narrowed is None:
            raise ValueError(f"Blender returned a JSON {type(parsed).__name__}, expected an object")
        return narrowed

    async def send_command(self, payload: dict[str, object]) -> dict[str, object]:
        """Send JSON payload and recv until we have a complete JSON response.

        Acquires _lock to prevent concurrent callers from interleaving
        writes/reads on the shared TCP socket.
        """
        async with self._lock:
            # Detecting a dead peer is not the same as recovering from one. `connect()`
            # is otherwise only ever called at API startup, so before this a dropped
            # link stayed dropped for the life of the process: Blender restarting under
            # a running API left /api/health reporting `disconnected` until the service
            # itself was restarted (observed 2026-09-07). Redialling here rather than in
            # each caller keeps it at the one place every command already funnels
            # through, and also covers an API that started before Blender was ready.
            if not self.is_connected:
                await self._redial()
            if not self._writer or not self._reader:
                raise BlenderConnectionError("Not connected to Blender.")

            data = json.dumps(payload).encode("utf-8")
            raw = b""
            try:
                self._writer.write(data)
                await self._writer.drain()

                async with asyncio.timeout(self._timeout):
                    while True:
                        chunk = await self._reader.read(4096)
                        if not chunk:
                            break
                        raw += chunk
                        try:
                            return self._decode_response(raw)
                        except json.JSONDecodeError:
                            continue
            except ConnectionError as exc:
                # A peer that hangs up politely sends FIN and the loop above sees EOF.
                # One that is *reset* — which is what a socket written to after the
                # addon went away gets — raises here instead, and letting that escape
                # as a bare OSError breaks the same promise the EOF branch keeps: a
                # dropped connection must never reach a caller as anything else.
                # TimeoutError is deliberately not caught; a slow addon is not a gone one.
                raise BlenderConnectionError(
                    f"Blender at {self._host}:{self._port} dropped the connection ({exc})"
                ) from exc
            # Only reachable via the `break` above: the addon sent EOF before a
            # complete reply. Decoding the stump would surface a dropped
            # connection as a *content* error and send the reader hunting for a
            # data-format bug (LESSONS_LEARNED.md, 2026-09-05).
            raise BlenderConnectionError(
                f"Blender at {self._host}:{self._port} closed the connection mid-reply "
                f"({len(raw)} bytes received)"
            )

    @property
    def is_connected(self) -> bool:
        """Whether the addon is still on the other end of this socket.

        `is_closing()` alone only reports whether *we* asked to close, so it
        stays False forever after Blender exits — health would keep reporting
        `connected` with port 9876 shut. The reader reaching EOF is the peer's
        FIN, which is what actually distinguishes the two.
        """
        if self._writer is None or self._reader is None:
            return False
        return not self._writer.is_closing() and not self._reader.at_eof()


class BlenderMCPClient(MCPPort):
    """MCPPort implementation over the BlenderSocketClient.

    Single responsibility: translate MCPPort calls to socket addon protocol.
    Composition over multiple inheritance — BlenderMCPAdapter uses this.
    """

    # Known addon tools (addon has no list_tools endpoint)
    _KNOWN_TOOLS = [
        "get_scene_info",
        "get_object_info",
        "execute_code",
        "get_viewport_screenshot",
    ]

    def __init__(self, socket: BlenderSocketClient) -> None:
        self._socket = socket

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        # Enforcement: a high-level tool here means a caller bypassed the
        # adapter's translation chokepoint. Fail loud rather than hand the addon
        # a name it will reject as "Unknown command type".
        if is_translatable(tool_name):
            logger.error(
                "high-level tool %r reached the socket untranslated — dispatch bypassed",
                tool_name,
            )
            return ToolResult(
                success=False,
                output=None,
                error=f"{tool_name} reached the addon untranslated (translation bypassed)",
            )
        try:
            response = await self._socket.send_command({"type": tool_name, "params": arguments})
            if response.get("status") == "error":
                message: object = response.get("message")
                return ToolResult(
                    success=False,
                    output=None,
                    error=str(message) if message is not None else "Unknown Blender error",
                )
            return ToolResult(
                success=True,
                output=response.get("result") or response,
                error=None,
            )
        except BlenderConnectionError:
            raise
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def list_tools(self) -> list[ToolDefinition]:
        return [ToolDefinition(name=t, description=t) for t in self._KNOWN_TOOLS]

    async def connect(self) -> None:
        await self._socket.connect()

    async def disconnect(self) -> None:
        await self._socket.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._socket.is_connected


class BlenderMCPAdapter(BlenderPort):
    """BlenderPort implementation — composes BlenderMCPClient (MCPPort).

    Single responsibility: translate BlenderPort calls to MCP tool calls.
    Does NOT inherit MCPPort — uses composition instead.

    Security: If a CodeSandboxPort is provided, execute_code calls are
    validated before being sent to Blender. Blocked calls return a failure
    ToolResult without touching the Blender socket.
    """

    def __init__(
        self,
        host: str,
        port: int,
        sandbox: CodeSandboxPort | None = None,
    ) -> None:
        self._socket = BlenderSocketClient(host, port)
        self._mcp = BlenderMCPClient(self._socket)
        self._sandbox = sandbox

    async def connect(self) -> None:
        await self._socket.connect()

    async def disconnect(self) -> None:
        await self._socket.disconnect()

    async def execute(self, command: Command) -> ToolResult:
        return await self._dispatch(command.tool_name, dict(command.arguments))

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        """Expose MCP tool calls for routers that need direct access."""
        return await self._dispatch(tool_name, dict(arguments))

    async def _dispatch(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        """The one point every socket dispatch funnels through.

        High-level modeling tools (create_object, …) are rewritten to
        execute_code here — the addon has no handler for them — so no caller,
        current or future, can reach the addon untranslated. Translation runs
        before the sandbox, so generated bpy code is validated too. This is what
        makes translate's "single choke point" true instead of merely intended:
        both entry points funnel here, and BlenderMCPClient rejects any
        translatable tool that still slips through.
        """
        command = translate(Command(tool_name=tool_name, arguments=arguments))
        if command.tool_name == _EXECUTE_CODE_TOOL and self._sandbox is not None:
            code = str(command.arguments.get("code", ""))
            sandbox_result = self._sandbox.validate(code)
            if not sandbox_result.allowed:
                logger.warning("Blocked execute_code: %s", "; ".join(sandbox_result.violations))
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Security: blocked code ({'; '.join(sandbox_result.violations)})",
                )
        result = await self._mcp.call_tool(command.tool_name, dict(command.arguments))
        if command.tool_name == _EXECUTE_CODE_TOOL and result.success:
            envelope = as_str_keyed(result.output, context=f"{tool_name} execute_code result")
            if envelope is not None and isinstance(envelope.get("result"), str):
                return ToolResult(success=True, output=envelope["result"], error=None)
        return result

    async def scene_summary(self) -> SceneSummary:
        return decode_scene_summary(await self._query("get_scene_info", {}))

    async def object_details(self, name: str) -> ObjectDetails:
        return decode_object_details(await self._query("get_object_info", {"name": name}))

    async def viewport_screenshot(self, max_size: int = 800) -> ViewportImage:
        return await capture_viewport(
            lambda arguments: self._query("get_viewport_screenshot", arguments), max_size
        )

    async def _query(self, tool_name: str, arguments: dict[str, object]) -> object:
        """A read tool's reply payload, or the domain error its failure becomes.

        Through `_dispatch`, so the single chokepoint claim stays true for
        queries as well as commands.
        """
        result = await self._dispatch(tool_name, arguments)
        if not result.success:
            raise SceneOperationError(
                result.error or f"{tool_name} failed without an error message"
            )
        return result.output

    async def is_connected(self) -> bool:
        return self._socket.is_connected
