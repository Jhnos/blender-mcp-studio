"""VisionPort — abstract interface for vision/multimodal LLM analysis.

Enables iterative refinement: capture Blender viewport → analyze → refine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class VisionAnalysis:
    """Result of a vision model analysis."""

    description: str
    suggestions: tuple[str, ...]
    provider: str
    model: str


class VisionPort(ABC):
    """Analyze image bytes using a vision-capable LLM."""

    @abstractmethod
    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 1024,
    ) -> VisionAnalysis:
        """Analyze an image with a natural language prompt."""
