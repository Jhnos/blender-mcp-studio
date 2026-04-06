"""Command value object — an immutable Blender instruction."""

from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Command(BaseModel):
    """Immutable value object representing a single Blender operation."""

    model_config = {"frozen": True}

    tool_name: str = Field(..., description="MCP tool name (e.g. 'create_object')")
    arguments: dict[str, object] = Field(
        default_factory=dict, description="Tool arguments"
    )

    def __str__(self) -> str:
        return f"Command({self.tool_name}, args={self.arguments})"


class CommandParser:
    """Domain service: extract and validate a Command from free-text LLM output.

    Validates arguments against ToolSchemaRegistry (loaded lazily from YAML).
    Invalid-but-parseable commands are logged and returned with a warning;
    they are not silently discarded so the use case can decide what to do.
    """

    _JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
    _registry = None  # lazy-loaded singleton

    @classmethod
    def _get_registry(cls):
        if cls._registry is None:
            from src.core.domain.tool_registry import ToolSchemaRegistry
            cls._registry = ToolSchemaRegistry.default()
        return cls._registry

    @classmethod
    def from_llm_output(cls, text: str) -> Command | None:
        """Parse the first JSON block in *text* into a validated Command.

        Returns None if no valid command block is found or parsing fails.
        Logs a warning if the command has schema violations but still returns it
        (Blender will surface the real error; we don't block valid-looking commands).
        """
        match = cls._JSON_RE.search(text)
        if not match:
            return None
        try:
            data = json.loads(match.group())
            command = Command(
                tool_name=data["tool_name"],
                arguments=data.get("arguments", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return None

        errors = cls._get_registry().validate(command.tool_name, command.arguments)
        if errors:
            logger.warning(
                "Command '%s' has schema violations: %s",
                command.tool_name,
                "; ".join(errors),
            )
        return command
