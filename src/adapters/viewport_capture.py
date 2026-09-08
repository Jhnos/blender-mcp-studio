"""The addon writes a screenshot to a path it is given; turning that into bytes is adapter work.

Both Blender adapters need the same dance — a temporary file, one tool call,
a signature check, a guaranteed delete — and the use case used to do it,
which meant the use case knew that Blender speaks in file paths. It does not
need to.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

from src.adapters.blender_scene_decoding import decode_screenshot_size
from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import ViewportImage

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: Called with the tool's arguments; returns the addon's reply payload.
Query = Callable[[dict[str, object]], Awaitable[object]]


async def capture_viewport(query: Query, max_size: int) -> ViewportImage:
    file_descriptor, raw_path = tempfile.mkstemp(suffix=".png")
    os.close(file_descriptor)
    path = Path(raw_path)
    try:
        metadata = await query({"filepath": raw_path, "max_size": max_size, "format": "png"})
        width, height = decode_screenshot_size(metadata)
        if not path.exists() or path.stat().st_size == 0:
            raise SceneOperationError("Blender reported a screenshot but created no PNG file")
        data = path.read_bytes()
        if not data.startswith(_PNG_SIGNATURE):
            raise SceneOperationError("Blender screenshot is not a PNG file")
        return ViewportImage(png_bytes=data, width=width, height=height)
    finally:
        path.unlink(missing_ok=True)
