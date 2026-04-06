"""Text3DGenerationPort — abstract interface for text-to-3D generation.

ISP: narrow port. Adapters implement Hunyuan3D, Hyper3D Rodin, or any other
text-to-3D service. The port returns raw GLB bytes — Blender import is the
caller's responsibility.

Configuration:
  HUNYUAN3D_ENDPOINT — base URL for local Hunyuan3D server (default: http://localhost:8080)
  HUNYUAN3D_API_KEY  — optional API key (for cloud endpoints)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Text3DResult:
    """Result from a text-to-3D generation request."""

    glb_bytes: bytes          # raw GLB file content
    prompt: str               # original prompt
    provider: str             # e.g. "hunyuan3d", "hyper3d"
    generation_time_s: float  # elapsed seconds


class Text3DGenerationPort(ABC):
    """Port for text-to-3D mesh generation."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        steps: int = 20,
        guidance_scale: float = 7.5,
    ) -> Text3DResult:
        """Generate a 3D mesh from a text prompt.

        Returns:
            Text3DResult with raw GLB bytes ready for Blender import.

        Raises:
            RuntimeError: if the endpoint is unavailable or generation fails.
        """
