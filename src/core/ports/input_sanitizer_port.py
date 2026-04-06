"""InputSanitizerPort — abstract interface for sanitizing user inputs.

Prevents prompt injection attacks where a user embeds instructions
meant to hijack the LLM's system prompt or tool definitions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SanitizeResult:
    """Result of input sanitization."""

    clean: bool
    sanitized_text: str
    detections: tuple[str, ...]


class InputSanitizerPort(ABC):
    """Sanitizes user-supplied text before it is sent to the LLM."""

    @abstractmethod
    def sanitize(self, text: str) -> SanitizeResult:
        """Check and sanitize user input for injection patterns.

        Returns SanitizeResult with clean=True if no issues detected,
        or clean=False with detections list and a sanitized version of the text.
        The sanitized_text is always safe to use (issues stripped or escaped).
        """
