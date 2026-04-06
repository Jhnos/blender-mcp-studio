"""ToolSchemaRegistry — validates Command arguments against known Blender tool schemas.

DDD: domain knows what arguments each tool requires. Invalid commands fail fast
in the domain, not silently in Blender at runtime.

Schemas are loaded from config/tool_schemas.yaml (data-driven, not hardcoded).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolSchema:
    """Schema for a single Blender MCP tool."""
    name: str
    required: frozenset[str] = field(default_factory=frozenset)
    optional: frozenset[str] = field(default_factory=frozenset)
    description: str = ""

    def validate(self, arguments: dict[str, object]) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: list[str] = []
        for req in self.required:
            if req not in arguments:
                errors.append(f"missing required argument '{req}'")
        return errors


class ToolSchemaRegistry:
    """Registry of known Blender tool schemas. Unknown tools pass through."""

    def __init__(self) -> None:
        self._schemas: dict[str, ToolSchema] = {}

    def register(self, schema: ToolSchema) -> None:
        self._schemas[schema.name] = schema

    def validate(self, tool_name: str, arguments: dict[str, object]) -> list[str]:
        """Validate arguments against the schema for tool_name.

        Returns a list of error messages. Empty list = valid.
        Unknown tools always return empty (no schema = no constraint).
        """
        schema = self._schemas.get(tool_name)
        if schema is None:
            return []  # Unknown tools pass through
        return schema.validate(arguments)

    def is_known(self, tool_name: str) -> bool:
        return tool_name in self._schemas

    @classmethod
    def from_yaml(cls, path: str) -> ToolSchemaRegistry:
        """Load schemas from a YAML file."""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        registry = cls()
        for tool_def in data.get("tools", []):
            registry.register(ToolSchema(
                name=tool_def["name"],
                required=frozenset(tool_def.get("required", [])),
                optional=frozenset(tool_def.get("optional", [])),
                description=tool_def.get("description", ""),
            ))
        return registry

    @classmethod
    def default(cls) -> ToolSchemaRegistry:
        """Return registry loaded from the default config path."""
        from pathlib import Path
        yaml_path = Path(__file__).parents[3] / "config" / "tool_schemas.yaml"
        if yaml_path.exists():
            return cls.from_yaml(str(yaml_path))
        logger.warning("tool_schemas.yaml not found, using empty registry")
        return cls()
