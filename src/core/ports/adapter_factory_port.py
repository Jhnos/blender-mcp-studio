"""AdapterFactoryPort — abstract factory for runtime adapter creation.

DIP: high-level modules depend on this abstraction, not concrete factories.
Enables testing with mock factories and runtime provider switching.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.ports.blender_port import BlenderPort
from src.core.ports.llm_port import LLMChatPort


class AdapterFactoryPort(ABC):
    """Abstract factory for creating LLM and Blender adapters."""

    @abstractmethod
    def build_llm_adapter(self, provider: str | None = None) -> LLMChatPort:
        """Create an LLM adapter. Falls back to LLM_PROVIDER env var."""

    @abstractmethod
    def build_blender_adapter(
        self, host: str | None = None, port: int | None = None
    ) -> BlenderPort:
        """Create a Blender adapter. Falls back to BLENDER_HOST/PORT env vars."""
