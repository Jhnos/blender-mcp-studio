"""PromptInjectionSanitizer — detects and neutralizes prompt injection attempts.

Strategy: pattern-match known injection signatures, then escape/strip them.
The sanitized text is always returned (never None) so the use case can proceed
with a safe version. Detections are logged for monitoring.

Patterns detected (data-driven list):
- "Ignore previous instructions" style overrides
- System/assistant role injection in user text
- Hidden unicode direction overrides (RLO/LRO)
- Attempts to reveal or override system prompts
"""

from __future__ import annotations

import logging
import re
import unicodedata

from src.core.ports.input_sanitizer_port import InputSanitizerPort, SanitizeResult

logger = logging.getLogger(__name__)

# (compiled pattern, description, replacement)
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
        "instruction override",
        "[filtered]",
    ),
    (
        re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+", re.I),
        "instruction disregard",
        "[filtered]",
    ),
    (
        re.compile(r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are))\s+", re.I),
        "role override",
        "[filtered] ",
    ),
    (
        re.compile(r"<\s*system\s*>.*?<\s*/\s*system\s*>", re.I | re.DOTALL),
        "system tag injection",
        "[filtered]",
    ),
    (
        re.compile(r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", re.I),
        "LLM special token injection",
        "[filtered]",
    ),
    (
        re.compile(r"(reveal|show|print|output)\s+(your\s+)?(system\s+prompt|instructions?)", re.I),
        "system prompt extraction",
        "[filtered]",
    ),
    (
        re.compile(r"<\|im_start\|>|<\|im_end\|>|\[SYSTEM\]", re.I),
        "chat template injection",
        "[filtered]",
    ),
]

# Unicode direction-override characters used in visual injection attacks
_BIDI_CHARS = frozenset([
    "\u200f",  # RIGHT-TO-LEFT MARK
    "\u200e",  # LEFT-TO-RIGHT MARK
    "\u202a",  # LEFT-TO-RIGHT EMBEDDING
    "\u202b",  # RIGHT-TO-LEFT EMBEDDING
    "\u202c",  # POP DIRECTIONAL FORMATTING
    "\u202d",  # LEFT-TO-RIGHT OVERRIDE
    "\u202e",  # RIGHT-TO-LEFT OVERRIDE (RLO)
    "\u2066",  # LEFT-TO-RIGHT ISOLATE
    "\u2067",  # RIGHT-TO-LEFT ISOLATE
    "\u2068",  # FIRST STRONG ISOLATE
    "\u2069",  # POP DIRECTIONAL ISOLATE
])


class PromptInjectionSanitizer(InputSanitizerPort):
    """Detects and neutralizes common prompt injection patterns."""

    def sanitize(self, text: str) -> SanitizeResult:
        detections: list[str] = []
        sanitized = text

        # 1. Strip dangerous unicode bidi override characters
        cleaned_chars = []
        for ch in sanitized:
            if ch in _BIDI_CHARS:
                detections.append(f"unicode bidi override U+{ord(ch):04X}")
            else:
                cleaned_chars.append(ch)
        sanitized = "".join(cleaned_chars)

        # 2. Normalize unicode (NFC) to prevent homoglyph attacks
        sanitized = unicodedata.normalize("NFC", sanitized)

        # 3. Apply injection pattern filters
        for pattern, description, replacement in _INJECTION_PATTERNS:
            if pattern.search(sanitized):
                detections.append(description)
                sanitized = pattern.sub(replacement, sanitized)

        if detections:
            logger.warning(
                "Prompt injection detected (%d pattern(s)): %s",
                len(detections),
                "; ".join(detections),
            )

        return SanitizeResult(
            clean=not bool(detections),
            sanitized_text=sanitized,
            detections=tuple(detections),
        )
