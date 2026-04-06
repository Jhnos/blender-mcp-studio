"""GPT-4o Vision adapter — analyzes Blender viewport screenshots.

Uses the OpenAI API (base64 image_url format).
Requires: OPENAI_API_KEY environment variable.
"""

from __future__ import annotations

import base64
import re

import httpx

from src.core.ports.vision_port import VisionAnalysis, VisionPort

_SUGGESTION_RE = re.compile(r"[-•*]\s*(.+)")


class GPT4oVisionAdapter(VisionPort):
    """Sends viewport screenshots to GPT-4o Vision for scene analysis."""

    DEFAULT_MODEL = "gpt-4o"
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for GPT4oVisionAdapter")
        self._api_key = api_key
        self._model = model

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 1024,
    ) -> VisionAnalysis:
        b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        text: str = data["choices"][0]["message"]["content"]
        suggestions = tuple(m.group(1).strip() for m in _SUGGESTION_RE.finditer(text))
        return VisionAnalysis(
            description=text,
            suggestions=suggestions,
            provider="openai",
            model=self._model,
        )
