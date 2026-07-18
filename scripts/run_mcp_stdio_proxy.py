#!/usr/bin/env python3
"""Expose the canonical remote MCP endpoint to stdio-only MCP hosts."""

from __future__ import annotations

import os

from fastmcp.server import create_proxy

DEFAULT_URL = "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"


def main() -> None:
    """Run a transport-only proxy; backend ownership stays in the API process."""
    url = os.environ.get("BLENDER_MCP_URL", DEFAULT_URL)
    proxy = create_proxy(url, name="blender-mcp-studio-stdio")
    proxy.run(transport="stdio")


if __name__ == "__main__":
    main()
