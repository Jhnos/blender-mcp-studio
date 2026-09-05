"""Blender dialect for saving and restoring .blend snapshots."""

from __future__ import annotations

from src.adapters.blender_scripts.runner import ScriptOutcome, quote, run_script
from src.core.ports.blender_port import BlenderPort

_SAVE_CODE = """\
import bpy, tempfile, os, datetime
blend_dir = os.path.join(os.path.expanduser('~'), '.blender_mcp_studio', 'snapshots')
os.makedirs(blend_dir, exist_ok=True)
ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')
blend_path = os.path.join(blend_dir, f'snap_{ts}.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)
print(blend_path)
"""

_RESTORE_CODE = """\
import bpy
bpy.ops.wm.open_mainfile(filepath='{blend_path}')
print('restored')
"""


async def save_snapshot(blender: BlenderPort) -> ScriptOutcome:
    """Write the current scene to a timestamped .blend and print its path."""
    return await run_script(blender, _SAVE_CODE)


async def restore_snapshot(blender: BlenderPort, blend_path: str) -> ScriptOutcome:
    """Open a previously saved .blend, replacing the current scene."""
    return await run_script(blender, _RESTORE_CODE.format(blend_path=quote(blend_path)))
