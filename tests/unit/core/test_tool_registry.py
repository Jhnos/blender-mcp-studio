"""Tests for ToolSchemaRegistry and CommandParser validation."""

from __future__ import annotations

import pytest

from src.core.domain.command import Command, CommandParser
from src.core.domain.tool_registry import ToolSchema, ToolSchemaRegistry


# ── ToolSchema tests ──────────────────────────────────────────────────────────

def test_schema_valid_when_all_required_present() -> None:
    schema = ToolSchema(name="create_object", required=frozenset(["type"]))
    errors = schema.validate({"type": "CUBE", "name": "MyCube"})
    assert errors == []


def test_schema_error_when_required_missing() -> None:
    schema = ToolSchema(name="create_object", required=frozenset(["type"]))
    errors = schema.validate({})
    assert any("type" in e for e in errors)


def test_schema_no_required_always_valid() -> None:
    schema = ToolSchema(name="get_scene_info", required=frozenset())
    assert schema.validate({}) == []
    assert schema.validate({"extra": "anything"}) == []


# ── ToolSchemaRegistry tests ──────────────────────────────────────────────────

def test_registry_unknown_tool_passes_through() -> None:
    registry = ToolSchemaRegistry()
    errors = registry.validate("totally_unknown_tool", {"foo": "bar"})
    assert errors == []


def test_registry_known_tool_validates() -> None:
    registry = ToolSchemaRegistry()
    registry.register(ToolSchema(name="delete_object", required=frozenset(["name"])))

    errors_missing = registry.validate("delete_object", {})
    assert errors_missing != []

    errors_ok = registry.validate("delete_object", {"name": "Cube"})
    assert errors_ok == []


def test_registry_from_yaml_loads_tools(tmp_path) -> None:
    yaml_content = """
tools:
  - name: test_tool
    required: [param_a]
    optional: [param_b]
    description: Test tool
"""
    f = tmp_path / "schemas.yaml"
    f.write_text(yaml_content)
    registry = ToolSchemaRegistry.from_yaml(str(f))

    assert registry.is_known("test_tool")
    assert not registry.is_known("other_tool")
    assert registry.validate("test_tool", {}) != []
    assert registry.validate("test_tool", {"param_a": "x"}) == []


# ── CommandParser with validation ─────────────────────────────────────────────

def test_commandparser_returns_command_on_valid_json() -> None:
    text = '{"tool_name": "get_scene_info", "arguments": {}}'
    cmd = CommandParser.from_llm_output(text)
    assert cmd is not None
    assert cmd.tool_name == "get_scene_info"


def test_commandparser_returns_none_on_no_json() -> None:
    assert CommandParser.from_llm_output("No JSON here") is None


def test_commandparser_returns_none_on_missing_tool_name() -> None:
    assert CommandParser.from_llm_output('{"arguments": {}}') is None


def test_commandparser_returns_command_even_with_schema_violations() -> None:
    """Schema violations log a warning but do NOT block the command."""
    # Inject a strict registry
    registry = ToolSchemaRegistry()
    registry.register(ToolSchema(name="strict_tool", required=frozenset(["must_have"])))
    CommandParser._registry = registry

    try:
        cmd = CommandParser.from_llm_output('{"tool_name": "strict_tool", "arguments": {}}')
        assert cmd is not None  # Not blocked — Blender decides the final error
        assert cmd.tool_name == "strict_tool"
    finally:
        CommandParser._registry = None  # Reset to default
