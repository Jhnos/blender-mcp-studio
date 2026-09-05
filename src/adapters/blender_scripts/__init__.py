"""Blender script anti-corruption layer.

Every ``bpy`` statement the REST layer needs lives here, behind named operations.
Delivery adapters call ``select_object(...)``; they never build script text.
"""

from src.adapters.blender_scripts.history_scripts import run_history_action
from src.adapters.blender_scripts.material_scripts import apply_hdri, apply_texture
from src.adapters.blender_scripts.object_scripts import (
    import_gltf,
    select_object,
    update_object,
)
from src.adapters.blender_scripts.runner import ScriptOutcome, quote, run_script
from src.adapters.blender_scripts.snapshot_scripts import restore_snapshot, save_snapshot

__all__ = [
    "ScriptOutcome",
    "apply_hdri",
    "apply_texture",
    "import_gltf",
    "quote",
    "restore_snapshot",
    "run_history_action",
    "run_script",
    "save_snapshot",
    "select_object",
    "update_object",
]
