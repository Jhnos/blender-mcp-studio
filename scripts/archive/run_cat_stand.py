"""
run_cat_stand.py — 走完真實架構路徑建立黑貓手機架。

路徑：MockLLM → ConversationalModelingUseCase → BlenderMCPAdapter → Blender socket
conda run -n blender-mcp python scripts/run_cat_stand.py
"""

from __future__ import annotations
import asyncio, textwrap

from src.core.domain.session import Session
from src.core.ports.llm_port import LLMPort, LLMResponse
from src.core.domain.session import Message
from src.core.use_cases.conversational_modeling import ConversationalModelingUseCase
from src.adapters.mcp.blender_mcp_adapter import BlenderMCPAdapter

CAT_BPY_CODE = textwrap.dedent("""
import bpy, math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def make_mat(name, rgba=(0.02,0.02,0.02,1), roughness=0.9):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bsdf.inputs[0].default_value = rgba
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

black  = make_mat("Black",  (0.02,0.02,0.02,1))
white  = make_mat("White",  (1.0, 1.0, 1.0, 1))
pink   = make_mat("Pink",   (0.9, 0.3, 0.4, 1))
purple = make_mat("Purple", (0.4, 0.1, 0.8, 1))

def assign(obj, mat):
    if obj.data.materials: obj.data.materials[0] = mat
    else: obj.data.materials.append(mat)

bpy.ops.mesh.primitive_cylinder_add(radius=3.2, depth=0.4, location=(0,0,0.2))
base = bpy.context.active_object; base.name = "Base"; assign(base, black)

bpy.ops.mesh.primitive_uv_sphere_add(radius=1.6, location=(0,0,2.0))
body = bpy.context.active_object; body.name = "CatBody"
body.scale.y = 0.85; body.scale.z = 1.1
bpy.ops.object.transform_apply(scale=True); assign(body, black)

bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=(0,-0.3,4.0))
head = bpy.context.active_object; head.name = "CatHead"; assign(head, black)

for side, x in [("Left",-0.7),("Right",0.7)]:
    bpy.ops.mesh.primitive_cone_add(radius1=0.35, depth=0.65, location=(x,-0.3,5.15))
    ear = bpy.context.active_object; ear.name = f"Ear{side}"
    ear.rotation_euler[1] = math.radians(-15 if side=="Left" else 15)
    assign(ear, black)

for side, x in [("Left",-0.4),("Right",0.4)]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(x,-1.35,4.05))
    eye = bpy.context.active_object; eye.name = f"Eye{side}"; assign(eye, white)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(x,-1.58,4.06))
    pupil = bpy.context.active_object; pupil.name = f"Pupil{side}"; assign(pupil, black)

bpy.ops.mesh.primitive_cone_add(radius1=0.1, depth=0.1, location=(0,-1.48,3.88))
nose = bpy.context.active_object; nose.name = "Nose"
nose.rotation_euler[0] = math.radians(90); assign(nose, pink)

bpy.ops.curve.primitive_bezier_curve_add(location=(1.5,0,0.6))
tail = bpy.context.active_object; tail.name = "Tail"
tail.data.bevel_depth = 0.18; tail.data.bevel_resolution = 4
pts = tail.data.splines[0].bezier_points
pts[0].co=(0,0,0); pts[0].handle_right=(0,1.5,1.5)
pts[1].co=(-1.2,0.5,3.5); pts[1].handle_left=(-1.8,0.5,2.5)
tail.data.materials.append(black)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0,-2.15,2.2))
slot = bpy.context.active_object; slot.name = "PhoneSlot"
slot.scale.x=0.45; slot.scale.y=0.06; slot.scale.z=0.85; assign(slot, purple)

for i,(x,angle) in enumerate([(-0.5,15),(-0.5,0),(-0.5,-15),(0.5,15),(0.5,0),(0.5,-15)]):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.018, depth=0.65, location=(x,-1.5,3.88))
    w = bpy.context.active_object; w.name = f"Whisker_{i}"
    w.rotation_euler[0]=math.radians(90); w.rotation_euler[2]=math.radians(angle)
    w.data.materials.append(black)

all_names = [o.name for o in bpy.context.scene.objects]
print(f"SUCCESS {len(all_names)} objects: {all_names}")
""").strip()


class MockCatLLM(LLMPort):
    """直接回傳 execute_code 指令，繞過真實 LLM。"""
    async def chat(self, messages: list[Message], system_prompt: str | None = None) -> LLMResponse:
        import json
        content = json.dumps({"tool_name": "execute_code", "arguments": {"code": CAT_BPY_CODE}})
        return LLMResponse(content=content, provider="mock", model="mock-cat-v1")

    @property
    def provider_name(self) -> str: return "mock"
    @property
    def model_name(self) -> str: return "mock-cat-v1"


async def main() -> None:
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  🐱  黑貓手機架 — 真實架構路徑")
    print("  Session → UseCase → MockLLM → BlenderMCPAdapter → Blender")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    blender = BlenderMCPAdapter()
    await blender.connect()
    print("  ✅ BlenderMCPAdapter 連線成功")

    use_case = ConversationalModelingUseCase(llm=MockCatLLM(), blender=blender)

    session = Session().add_message("user", "幫我建立一個可愛搞笑的黑貓手機架，適合3D列印")
    print(f"  💬 使用者：{session.last_user_message()}")
    print("  ⚙️  執行 Use Case...\n")

    updated, reply = await use_case.execute(session)

    # 印出 Blender 執行結果（從 reply 中不好看，直接查 scene）
    print(f"  📨 LLM→Blender 執行完成，Session 訊息數：{len(updated.messages)}")

    scene = await blender.get_scene_info()
    objs = scene.get("objects", []) if isinstance(scene, dict) else []
    print(f"\n  🔍 Blender 場景：{len(objs)} 個物件")
    for o in objs:
        print(f"     • {o['name']:<20} [{o['type']}]")

    await blender.disconnect()
    print("\n  ✅ 完成！請看 Blender 視窗 🎉")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


if __name__ == "__main__":
    asyncio.run(main())
