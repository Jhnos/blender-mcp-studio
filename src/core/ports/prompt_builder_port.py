"""PromptBuilderPort — abstract interface for dynamic system prompt construction.

Enables injecting Blender API context, few-shot examples, and session state
into the LLM system prompt without hardcoding it in the use case.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PromptBuilderPort(ABC):
    """Build a context-aware system prompt for the LLM."""

    @abstractmethod
    def build_system_prompt(self, context: dict[str, object] | None = None) -> str:
        """Return a system prompt enriched with Blender API context.

        Args:
            context: Optional runtime context (e.g., scene object names,
                     current tool list) to inject into the prompt.
        """
