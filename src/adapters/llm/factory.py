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

import logging
import os
from collections.abc import Callable

from src.core.ports.llm_port import LLMPort
from src.infrastructure.config_loader import load_llm_providers
from src.infrastructure.narrowing import as_int, as_str, as_str_keyed

logger = logging.getLogger(__name__)

_SOURCE = "llm_providers.yaml"


def _get_provider_cfg(provider: str) -> dict[str, object]:
    """Load provider config from llm_providers.yaml; return empty dict if missing."""
    try:
        cfg = load_llm_providers()
    except FileNotFoundError:
        return {}

    # Deliberately not `dig(cfg, "providers", provider)`: dig cannot tell "key
    # absent" from "key present but malformed", and a broken config file must
    # not degrade to {} in silence.
    providers_raw: object = cfg.get("providers")
    if providers_raw is None:
        return {}
    providers = as_str_keyed(providers_raw, context=_SOURCE)
    if providers is None:
        logger.warning(
            "%s: 'providers' is %s, expected a mapping — ignoring",
            _SOURCE,
            type(providers_raw).__name__,
        )
        return {}

    provider_raw: object = providers.get(provider)
    if provider_raw is None:
        return {}
    provider_cfg = as_str_keyed(provider_raw, context=_SOURCE)
    if provider_cfg is None:
        logger.warning(
            "%s: provider '%s' is %s, expected a mapping — ignoring",
            _SOURCE,
            provider,
            type(provider_raw).__name__,
        )
        return {}
    return provider_cfg


def _cfg_str(cfg: dict[str, object], key: str) -> str:
    """Read a string-valued config key; empty (falsy) when absent or not a string."""
    value: object = cfg.get(key)
    if value is None:
        return ""
    narrowed = as_str(value)
    if narrowed is None:
        logger.warning(
            "%s: '%s' is %s, expected a string — ignoring", _SOURCE, key, type(value).__name__
        )
        return ""
    return narrowed


def _cfg_int(cfg: dict[str, object], key: str) -> int:
    """Read an int-valued config key; 0 (falsy) when absent or not an integer."""
    value: object = cfg.get(key)
    if value is None:
        return 0
    narrowed = as_int(value)
    if narrowed is None:
        logger.warning(
            "%s: '%s' is %s, expected an integer — ignoring", _SOURCE, key, type(value).__name__
        )
        return 0
    return narrowed


def _build_ollama() -> LLMPort:
    from src.adapters.llm.ollama_adapter import OllamaAdapter

    yaml_cfg = _get_provider_cfg("ollama")
    # SSOT: model from llm_providers.yaml; env var overrides for machine-specific use
    model = (
        os.environ.get("OLLAMA_MODEL") or _cfg_str(yaml_cfg, "model") or OllamaAdapter.DEFAULT_MODEL
    )
    base_url = (
        os.environ.get("OLLAMA_BASE_URL")
        or _cfg_str(yaml_cfg, "base_url")
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
        or _cfg_str(yaml_cfg, "model")
        or AnthropicAdapter.DEFAULT_MODEL,
        max_tokens=int(
            os.environ.get("ANTHROPIC_MAX_TOKENS")
            or _cfg_int(yaml_cfg, "max_tokens")
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
        model=os.environ.get("DEEPSEEK_MODEL") or _cfg_str(yaml_cfg, "model") or "deepseek-chat",
        base_url=os.environ.get("DEEPSEEK_BASE_URL")
        or _cfg_str(yaml_cfg, "base_url")
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
