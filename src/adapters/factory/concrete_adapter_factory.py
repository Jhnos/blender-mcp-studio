"""ConcreteAdapterFactory — production implementation of AdapterFactoryPort.

Reads all configuration from environment variables.
High-level code only sees AdapterFactoryPort — never this class directly.
"""

from __future__ import annotations

from src.core.ports.adapter_factory_port import AdapterFactoryPort
from src.core.ports.blender_port import BlenderPort
from src.core.ports.llm_port import LLMChatPort


class ConcreteAdapterFactory(AdapterFactoryPort):
    """Builds adapters from environment configuration."""

    def build_llm_adapter(self, provider: str | None = None) -> LLMChatPort:
        from src.adapters.llm.factory import build_llm_adapter
        return build_llm_adapter(provider=provider)

    def build_blender_adapter(
        self, host: str | None = None, port: int | None = None
    ) -> BlenderPort:
        from src.adapters.mcp.factory import build_blender_adapter
        return build_blender_adapter(host=host, port=port)
