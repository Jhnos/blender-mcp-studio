"""BlenderContextPromptBuilder — loads Blender API context from YAML config.

Constructs enriched system prompts that include:
  - Header (role definition)
  - Blender 5.x bpy API key patterns and pitfalls (few-shot knowledge)
  - Available tool instructions

Data-driven: update config/blender_api_context.yaml to improve generation
quality without changing code.
"""

from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path

import yaml

from src.core.ports.prompt_builder_port import PromptBuilderPort

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = Path(__file__).parent.parent.parent.parent / "config" / "blender_api_context.yaml"


class BlenderContextPromptBuilder(PromptBuilderPort):
    """Builds system prompts enriched with Blender API context from YAML."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or _DEFAULT_CONFIG

    @cached_property
    def _config(self) -> dict[str, str]:
        try:
            with open(self._config_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Could not load blender_api_context.yaml: %s", e)
            return {}

    def build_system_prompt(self, context: dict[str, object] | None = None) -> str:
        """Build a complete system prompt with API context injected.

        Args:
            context: Optional runtime data to append (e.g., current scene objects).
        """
        parts: list[str] = []

        header = self._config.get("header", "").strip()
        if header:
            parts.append(header)

        api_notes = self._config.get("blender_api_notes", "").strip()
        if api_notes:
            parts.append(api_notes)

        tool_instructions = self._config.get("tool_instructions", "").strip()
        if tool_instructions:
            parts.append(tool_instructions)

        if context:
            scene_objects = context.get("scene_objects")
            if scene_objects:
                parts.append(f"\n## Current Scene Objects\n{scene_objects}")

        return "\n\n".join(parts)
