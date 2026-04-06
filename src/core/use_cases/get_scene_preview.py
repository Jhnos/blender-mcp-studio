"""GetScenePreviewUseCase — fetches a viewport screenshot from Blender.

SRP: single concern — invoke Blender tool, read file, return bytes.
All file I/O and HTTP concerns are separated from this use case.
"""

from __future__ import annotations

import os
import tempfile

from src.core.ports.blender_port import BlenderPort


class GetScenePreviewUseCase:
    """Returns raw PNG bytes for the current Blender viewport, or None on failure."""

    def __init__(self, blender: BlenderPort) -> None:
        self._blender = blender

    async def execute(self, max_size: int = 800) -> bytes | None:
        """Call Blender for a viewport screenshot and return PNG bytes.

        Returns None if Blender is unavailable or the call fails.
        """
        tmp = tempfile.mktemp(suffix=".png")
        try:
            result = await self._blender.call_tool(
                "get_viewport_screenshot",
                {"filepath": tmp, "max_size": max_size, "format": "png"},
            )
            if result.success and os.path.exists(tmp):
                with open(tmp, "rb") as f:
                    return f.read()
        except Exception:
            pass
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return None
