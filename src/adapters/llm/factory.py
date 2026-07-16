"""LLM adapter factory — single source of truth for provider selection.

Uses a registry dict (OCP: add providers without modifying this function).

Usage:
    from src.adapters.llm.factory import build_llm_adapter
    llm = build_llm_adapter()

Provider is read from LLM_PROVIDER env var (default: ollama).
Model/params are read from config/llm_providers.yaml (SSOT); env vars override only
machine-specific values (base_url, api_key).
"""

from __future__ import annotations

import os
from collections.abc import Callable

from src.core.ports.llm_port import LLMPort
from src.infrastructure.config_loader import load_llm_providers


def _get_provider_cfg(provider: str) -> dict:
    """Load provider config from llm_providers.yaml; return empty dict if missing."""
    try:
        cfg = load_llm_providers()
        return cfg.get("providers", {}).get(provider, {})
    except FileNotFoundError:
        return {}


def _build_ollama() -> LLMPort:
    from src.adapters.llm.ollama_adapter import OllamaAdapter

    yaml_cfg = _get_provider_cfg("ollama")
    # SSOT: model from llm_providers.yaml; env var overrides for machine-specific use
    model = os.environ.get("OLLAMA_MODEL") or yaml_cfg.get("model") or OllamaAdapter.DEFAULT_MODEL
    base_url = (
        os.environ.get("OLLAMA_BASE_URL")
        or yaml_cfg.get("base_url")
        or OllamaAdapter.DEFAULT_BASE_URL
    )
    return OllamaAdapter(model=model, base_url=base_url)


def _build_anthropic() -> LLMPort:
    from src.adapters.llm.anthropic_adapter import AnthropicAdapter

    yaml_cfg = _get_provider_cfg("anthropic")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
    return AnthropicAdapter(
        model=os.environ.get("ANTHROPIC_MODEL")
        or yaml_cfg.get("model")
        or AnthropicAdapter.DEFAULT_MODEL,
        max_tokens=int(
            os.environ.get("ANTHROPIC_MAX_TOKENS")
            or yaml_cfg.get("max_tokens")
            or AnthropicAdapter.DEFAULT_MAX_TOKENS
        ),
        api_key=api_key,
    )


def _build_deepseek() -> LLMPort:
    from src.adapters.llm.ollama_adapter import OllamaAdapter

    yaml_cfg = _get_provider_cfg("deepseek")
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("LLM_PROVIDER=deepseek but DEEPSEEK_API_KEY is not set")
    return OllamaAdapter(
        model=os.environ.get("DEEPSEEK_MODEL") or yaml_cfg.get("model") or "deepseek-chat",
        base_url=os.environ.get("DEEPSEEK_BASE_URL")
        or yaml_cfg.get("base_url")
        or "https://api.deepseek.com",
    )


# Registry: add new providers here without touching build_llm_adapter()
_PROVIDER_REGISTRY: dict[str, Callable[[], LLMPort]] = {
    "ollama": _build_ollama,
    "anthropic": _build_anthropic,
    "deepseek": _build_deepseek,
}


def build_llm_adapter(provider: str | None = None) -> LLMPort:
    """Instantiate the correct LLM adapter from the registry.

    Args:
        provider: Override provider name. Falls back to LLM_PROVIDER env var, then "ollama".
    """
    _provider = (provider or os.environ.get("LLM_PROVIDER", "ollama")).lower()
    builder = _PROVIDER_REGISTRY.get(_provider)
    if builder is None:
        known = ", ".join(_PROVIDER_REGISTRY)
        raise ValueError(f"Unknown LLM provider '{_provider}'. Known: {known}")
    return builder()


def register_llm_provider(name: str, builder: Callable[[], LLMPort]) -> None:
    """Register a custom LLM provider at runtime (OCP extension point)."""
    _PROVIDER_REGISTRY[name.lower()] = builder
