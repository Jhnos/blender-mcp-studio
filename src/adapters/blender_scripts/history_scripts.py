"""Blender dialect for the undo/redo stack."""

from __future__ import annotations

from typing import Literal

from src.adapters.blender_scripts.runner import ScriptOutcome, run_script
from src.core.ports.blender_port import BlenderPort

_CALLS: dict[str, str] = {
    "undo": "bpy.ops.ed.undo()",
    "redo": "bpy.ops.ed.undo_redo()",
}


async def run_history_action(
    blender: BlenderPort, action: Literal["undo", "redo"]
) -> ScriptOutcome:
    """Step the Blender undo stack one entry in ``action``'s direction."""
    code = f"import bpy\n{_CALLS[action]}\nprint('{action} ok')"
    return await run_script(blender, code)
