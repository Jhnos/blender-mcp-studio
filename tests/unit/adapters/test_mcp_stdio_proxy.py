"""Contract tests for the client-neutral HTTP-to-stdio compatibility bridge."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import scripts.run_mcp_stdio_proxy as stdio_proxy

PROJECT_ROOT = Path(__file__).parents[3]


def test_stdio_proxy_uses_canonical_url_and_stdio_transport(monkeypatch) -> None:
    proxy = MagicMock()
    create_proxy = MagicMock(return_value=proxy)
    monkeypatch.delenv("BLENDER_MCP_URL", raising=False)
    monkeypatch.setattr(stdio_proxy, "create_proxy", create_proxy)

    stdio_proxy.main()

    create_proxy.assert_called_once_with(
        "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp",
        name="blender-mcp-studio-stdio",
    )
    proxy.run.assert_called_once_with(transport="stdio")


def test_stdio_proxy_accepts_endpoint_override(monkeypatch) -> None:
    proxy = MagicMock()
    create_proxy = MagicMock(return_value=proxy)
    monkeypatch.setenv("BLENDER_MCP_URL", "https://mcp.example.test/custom")
    monkeypatch.setattr(stdio_proxy, "create_proxy", create_proxy)

    stdio_proxy.main()

    assert create_proxy.call_args.args[0] == "https://mcp.example.test/custom"


def test_stdio_proxy_never_owns_the_blender_socket() -> None:
    source = (PROJECT_ROOT / "scripts" / "run_mcp_stdio_proxy.py").read_text()

    assert "9876" not in source
    assert "BlenderMCPAdapter" not in source
    assert "build_blender_adapter" not in source


def test_vite_routes_blender_mcp_before_api_without_buffer_hooks() -> None:
    source = (PROJECT_ROOT / "web" / "vite.config.ts").read_text()

    mcp_position = source.index("'/blender/mcp'")
    api_position = source.index("'/blender/api'")
    mcp_block = source[mcp_position:api_position]

    assert mcp_position < api_position
    assert "target: 'http://localhost:19505'" in mcp_block
    assert "changeOrigin: false" in mcp_block
    assert "path.replace(/^\\/blender/, '')" in mcp_block
    assert "buffer" not in mcp_block.lower()
    assert "headers" not in mcp_block.lower()
