#!/usr/bin/env python3
"""Expose the canonical remote MCP endpoint to stdio-only MCP hosts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastmcp.server import create_proxy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.public_base_url import public_base_url  # noqa: E402


def main() -> None:
    """Run a transport-only proxy; backend ownership stays in the API process."""
    url = os.environ.get("BLENDER_MCP_URL")
    if not url:
        try:
            url = public_base_url() + "/mcp"
        except ValueError:
            print(
                "error: no upstream MCP URL; set BLENDER_MCP_URL, or "
                "BLENDER_MCP_PUBLIC_BASE_URL, or make `tailscale status --self --json` work",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    proxy = create_proxy(url, name="blender-mcp-studio-stdio")
    proxy.run(transport="stdio")


if __name__ == "__main__":
    main()
