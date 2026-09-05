"""Blender dialect for applying Poly Haven assets as world HDRI or texture."""

from __future__ import annotations

from src.adapters.blender_scripts.runner import ScriptOutcome, quote, run_script
from src.core.ports.blender_port import BlenderPort

_APPLY_HDRI_CODE = """\
import bpy, urllib.request, tempfile

url = "{url}"
ext = url.rsplit(".", 1)[-1]
tmp = tempfile.mktemp(suffix="." + ext)
urllib.request.urlretrieve(url, tmp)

# Apply as World HDRI
world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
bg   = nt.nodes.new("ShaderNodeBackground")
env  = nt.nodes.new("ShaderNodeTexEnvironment")
out  = nt.nodes.new("ShaderNodeOutputWorld")
env.image = bpy.data.images.load(tmp)
nt.links.new(env.outputs[0], bg.inputs[0])
nt.links.new(bg.outputs[0], out.inputs[0])
print(f"hdri_applied:{tmp}")
"""

_APPLY_TEXTURE_CODE = """\
import bpy, urllib.request, tempfile

url = "{url}"
ext = url.rsplit(".", 1)[-1]
tmp = tempfile.mktemp(suffix="." + ext)
urllib.request.urlretrieve(url, tmp)

obj = bpy.context.active_object
if obj is None or obj.type != "MESH":
    print("no_active_mesh")
else:
    mat = obj.active_material
    if mat is None:
        mat = bpy.data.materials.new(name="PolyHaven_Mat")
        obj.data.materials.append(mat)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex  = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(tmp)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    print(f"texture_applied:{tmp}")
"""


async def apply_hdri(blender: BlenderPort, url: str) -> ScriptOutcome:
    """Download an HDRI and set it as the world environment texture."""
    return await run_script(blender, _APPLY_HDRI_CODE.format(url=quote(url)))


async def apply_texture(blender: BlenderPort, url: str) -> ScriptOutcome:
    """Download a texture and wire it into the active object's base colour."""
    return await run_script(blender, _APPLY_TEXTURE_CODE.format(url=quote(url)))
