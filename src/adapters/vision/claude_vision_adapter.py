"""Claude Vision adapter — analyzes Blender viewport screenshots via Anthropic API.

Uses Claude's native image content blocks (base64 PNG).
Requires: ANTHROPIC_API_KEY environment variable.
"""

from __future__ import annotations

import re

import anthropic

from src.core.ports.vision_port import VisionAnalysis, VisionPort

_SUGGESTION_RE = re.compile(r"[-•*]\s*(.+)")


class ClaudeVisionAdapter(VisionPort):
    """Sends viewport screenshots to Claude Vision for scene analysis."""

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for ClaudeVisionAdapter")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 1024,
    ) -> VisionAnalysis:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": __import__("base64").b64encode(image_bytes).decode(),
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text: str = response.content[0].text
        suggestions = tuple(m.group(1).strip() for m in _SUGGESTION_RE.finditer(text))
        return VisionAnalysis(
            description=text,
            suggestions=suggestions,
            provider="anthropic",
            model=self._model,
        )
