"""VisionAdapter factory — picks the right vision adapter from environment."""

from __future__ import annotations

import os

from src.core.ports.vision_port import VisionPort


def build_vision_adapter(provider: str | None = None) -> VisionPort | None:
    """Instantiate a VisionPort from environment config.

    Returns None if no vision provider is configured, allowing the caller
    to degrade gracefully (skip vision analysis).

    Priority:
      1. `provider` argument (explicit)
      2. VISION_PROVIDER env var ('openai' | 'anthropic')
      3. Auto-detect: OPENAI_API_KEY → openai; ANTHROPIC_API_KEY → anthropic
    """
    _provider = provider or os.environ.get("VISION_PROVIDER") or _detect_provider()
    if _provider is None:
        return None

    if _provider == "openai":
        from src.adapters.vision.gpt4o_vision_adapter import GPT4oVisionAdapter
        return GPT4oVisionAdapter(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=os.environ.get("VISION_MODEL", GPT4oVisionAdapter.DEFAULT_MODEL),
        )
    if _provider == "anthropic":
        from src.adapters.vision.claude_vision_adapter import ClaudeVisionAdapter
        return ClaudeVisionAdapter(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            model=os.environ.get("VISION_MODEL", ClaudeVisionAdapter.DEFAULT_MODEL),
        )

    raise ValueError(f"Unknown VISION_PROVIDER: '{_provider}'. Use 'openai' or 'anthropic'.")


def _detect_provider() -> str | None:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None
