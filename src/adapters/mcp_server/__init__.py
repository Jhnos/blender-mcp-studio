"""Public factory for the client-neutral MCP inbound adapter."""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
