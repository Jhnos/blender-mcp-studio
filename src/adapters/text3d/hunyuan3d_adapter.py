"""Hunyuan3DAdapter — text-to-3D via local Hunyuan3D server or HuggingFace Gradio Space.

Supports two modes (selected via HUNYUAN3D_MODE env var):
  - "local"   : POST http://<endpoint>/generate  (local server, fastest)
  - "gradio"  : HuggingFace Gradio Space API via gradio_client (default, no GPU needed)

Environment variables:
  HUNYUAN3D_MODE        "local" | "gradio"  (default: gradio)
  HUNYUAN3D_ENDPOINT    base URL for local mode (default: http://localhost:8080)
  HUNYUAN3D_HF_SPACE    HuggingFace Space ID (default: tencent/Hunyuan3D-2)
  HUNYUAN3D_API_KEY     HF token for private spaces (optional)
"""

from __future__ import annotations

import logging
import os
import time

from src.core.ports.text3d_port import Text3DGenerationPort, Text3DResult

logger = logging.getLogger(__name__)

_DEFAULT_HF_SPACE = "tencent/Hunyuan3D-2"
_DEFAULT_LOCAL_URL = "http://localhost:8080"


class Hunyuan3DAdapter(Text3DGenerationPort):
    """Adapter for Hunyuan3D-2 text-to-3D generation.

    Gracefully returns RuntimeError if the service is unavailable —
    callers should catch and surface a friendly error to the user.
    """

    def __init__(
        self,
        mode: str | None = None,
        endpoint: str | None = None,
        hf_space: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._mode = (mode or os.environ.get("HUNYUAN3D_MODE", "gradio")).lower()
        self._endpoint = endpoint or os.environ.get("HUNYUAN3D_ENDPOINT", _DEFAULT_LOCAL_URL)
        self._hf_space = hf_space or os.environ.get("HUNYUAN3D_HF_SPACE", _DEFAULT_HF_SPACE)
        self._api_key = api_key or os.environ.get("HUNYUAN3D_API_KEY", "")

    async def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        steps: int = 20,
        guidance_scale: float = 7.5,
    ) -> Text3DResult:
        t0 = time.monotonic()
        if self._mode == "local":
            glb_bytes = await self._generate_local(prompt, negative_prompt, steps, guidance_scale)
        else:
            glb_bytes = await self._generate_gradio(prompt, negative_prompt, steps, guidance_scale)
        elapsed = time.monotonic() - t0
        return Text3DResult(
            glb_bytes=glb_bytes,
            prompt=prompt,
            provider="hunyuan3d",
            generation_time_s=elapsed,
        )

    async def _generate_local(
        self, prompt: str, negative_prompt: str, steps: int, guidance: float
    ) -> bytes:
        """POST to local Hunyuan3D HTTP server, return raw GLB bytes."""
        import httpx
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{self._endpoint.rstrip('/')}/generate", json=payload)
            resp.raise_for_status()
            # Server returns GLB binary directly
            content_type = resp.headers.get("content-type", "")
            if "json" in content_type:
                # Some servers return {"glb_url": "..."} or {"glb_base64": "..."}
                data = resp.json()
                if "glb_base64" in data:
                    import base64
                    return base64.b64decode(data["glb_base64"])
                if "glb_url" in data:
                    dl = await client.get(data["glb_url"])
                    dl.raise_for_status()
                    return dl.content
                raise RuntimeError(f"Unexpected JSON response: {list(data.keys())}")
            return resp.content

    async def _generate_gradio(
        self, prompt: str, negative_prompt: str, steps: int, guidance: float
    ) -> bytes:
        """Use gradio_client to call the HuggingFace Space API."""
        try:
            from gradio_client import Client  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "gradio_client not installed. Run: pip install gradio-client"
            ) from exc

        import asyncio

        kwargs: dict = {"hf_token": self._api_key} if self._api_key else {}

        def _sync_call() -> bytes:
            client = Client(self._hf_space, **kwargs)
            # Hunyuan3D-2 Space API: predict(prompt, negative_prompt, ...) → glb file path
            result = client.predict(
                prompt,
                negative_prompt,
                steps,
                guidance,
                api_name="/generate",
            )
            # Result may be a file path or dict with "value"
            if isinstance(result, dict):
                path = result.get("value") or result.get("path", "")
            else:
                path = str(result)

            with open(path, "rb") as f:
                return f.read()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)


def build_text3d_adapter() -> Hunyuan3DAdapter | None:
    """Factory: return None if Hunyuan3D is not configured (graceful degradation)."""
    mode = os.environ.get("HUNYUAN3D_MODE", "gradio")
    if mode == "local" and not os.environ.get("HUNYUAN3D_ENDPOINT"):
        logger.info("Hunyuan3D local mode but no endpoint configured — text3d disabled")
        return None
    return Hunyuan3DAdapter()
