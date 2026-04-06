"""Unit tests for Command value object."""

import pytest

from src.core.domain.command import Command


def test_command_is_immutable() -> None:
    cmd = Command(tool_name="create_object", arguments={"type": "CUBE"})
    with pytest.raises(Exception):
        cmd.tool_name = "delete_object"  # type: ignore[misc]


def test_command_str_representation() -> None:
    cmd = Command(tool_name="create_object", arguments={"type": "SPHERE"})
    assert "create_object" in str(cmd)


def test_command_default_empty_arguments() -> None:
    cmd = Command(tool_name="get_scene_info")
    assert cmd.arguments == {}


def test_command_equality() -> None:
    cmd1 = Command(tool_name="create_object", arguments={"type": "CUBE"})
    cmd2 = Command(tool_name="create_object", arguments={"type": "CUBE"})
    assert cmd1 == cmd2
