"""
demo_cat_stand.py — 模擬「黑貓手機架」建模完整流程。

執行方式：
  conda run -n blender-mcp python scripts/demo_cat_stand.py

若 Blender 已開啟且 addon 已連線（port 9876），會實際執行建模。
否則印出模擬流程與 bpy 程式碼。
"""

from __future__ import annotations

import asyncio
import json
import socket
import textwrap
import time


# ─── ANSI colors ────────────────────────────────────────────────────────────
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    RED = "\033[91m"
    DIM = "\033[2m"


def h(text: str, color: str = C.CYAN) -> str:
    return f"{color}{C.BOLD}{text}{C.RESET}"


def p(text: str, indent: int = 0) -> None:
    prefix = "  " * indent
    print(f"{prefix}{text}")


# ─── Blender bpy code for the cat phone stand ───────────────────────────────

CAT_STAND_CODE = textwrap.dedent("""
import bpy
import math

# ── 清場 ──────────────────────────────────────────────
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def new_obj(name, data):
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj

# ── 黑色材質 ─────────────────────────────────────────
def black_mat(name="BlackMatte"):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat

mat = black_mat()

def assign_mat(obj):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

# ── 底座（圓角長方形底盤）────────────────────────────
bpy.ops.mesh.primitive_cylinder_add(radius=3.2, depth=0.4, location=(0,0,0.2))
base = bpy.context.active_object
base.name = "Base"
bpy.ops.object.modifier_add(type='BEVEL')
base.modifiers["Bevel"].width = 0.15
bpy.ops.object.modifier_apply(modifier="Bevel")
assign_mat(base)

# ── 貓身體（胖乎乎橢圓球）────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.6, location=(0,0,2.0))
body = bpy.context.active_object
body.name = "CatBody"
body.scale.y = 0.85
body.scale.z = 1.1
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.modifier_add(type='SUBSURF')
body.modifiers["Subdivision"].levels = 2
bpy.ops.object.modifier_apply(modifier="Subdivision")
assign_mat(body)

# ── 頭部（比身體小一點的球）─────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=(0,-0.3,4.0))
head = bpy.context.active_object
head.name = "CatHead"
bpy.ops.object.modifier_add(type='SUBSURF')
head.modifiers["Subdivision"].levels = 2
bpy.ops.object.modifier_apply(modifier="Subdivision")
assign_mat(head)

# ── 耳朵（左右尖錐）─────────────────────────────────
for side, x in [("Left", -0.7), ("Right", 0.7)]:
    bpy.ops.mesh.primitive_cone_add(radius1=0.35, depth=0.65,
                                     location=(x, -0.3, 5.1))
    ear = bpy.context.active_object
    ear.name = f"Ear{side}"
    ear.rotation_euler[0] = math.radians(10)
    ear.rotation_euler[1] = math.radians(-15 if side=="Left" else 15)
    assign_mat(ear)

# ── 眼睛（白色大圓眼，搞笑效果）─────────────────────
eye_mat = bpy.data.materials.new("EyeWhite")
eye_mat.use_nodes = True
eye_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1,1,1,1)

for side, x in [("Left", -0.4), ("Right", 0.4)]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(x,-1.35,4.05))
    eye = bpy.context.active_object
    eye.name = f"Eye{side}"
    if eye.data.materials:
        eye.data.materials[0] = eye_mat
    else:
        eye.data.materials.append(eye_mat)

# 黑色瞳孔
pupil_mat = bpy.data.materials.new("Pupil")
pupil_mat.use_nodes = True
pupil_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0,0,0,1)

for side, x in [("Left", -0.4), ("Right", 0.4)]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(x,-1.55,4.06))
    pupil = bpy.context.active_object
    pupil.name = f"Pupil{side}"
    if pupil.data.materials:
        pupil.data.materials[0] = pupil_mat
    else:
        pupil.data.materials.append(pupil_mat)

# ── 鼻子（小三角）───────────────────────────────────
bpy.ops.mesh.primitive_cone_add(radius1=0.09, depth=0.08,
                                  location=(0,-1.5,3.88))
nose = bpy.context.active_object
nose.name = "Nose"
nose.rotation_euler[0] = math.radians(90)
nose_mat = bpy.data.materials.new("Nose")
nose_mat.use_nodes = True
nose_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8,0.3,0.4,1)
nose.data.materials.append(nose_mat)

# ── 尾巴（彎曲貝茲曲線）─────────────────────────────
bpy.ops.curve.primitive_bezier_curve_add(location=(1.5, 0, 0.6))
tail_curve = bpy.context.active_object
tail_curve.name = "Tail"
tail_curve.data.bevel_depth = 0.2
tail_curve.data.bevel_resolution = 4
spline = tail_curve.data.splines[0]
pts = spline.bezier_points
pts[0].co = (0, 0, 0)
pts[0].handle_right = (0, 1.5, 1.5)
pts[1].co = (-1.2, 0.5, 3.5)
pts[1].handle_left = (-1.8, 0.5, 2.5)
pts[1].handle_right = (-0.6, 0.5, 4.5)
if tail_curve.data.materials:
    tail_curve.data.materials[0] = mat
else:
    tail_curve.data.materials.append(mat)

# ── 手機槽（在肚子前方的缺口，3D列印插槽）───────────
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,-2.1,2.2))
slot = bpy.context.active_object
slot.name = "PhoneSlot_Cutter"
slot.scale.x = 0.45   # 手機寬度（約45mm）
slot.scale.y = 0.08   # 槽深
slot.scale.z = 0.85   # 手機高度（約85mm）

# Boolean 差集做出槽口
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
bool_mod = body.modifiers.new("PhoneSlot", type='BOOLEAN')
bool_mod.operation = 'DIFFERENCE'
bool_mod.object = slot
bpy.ops.object.modifier_apply(modifier="PhoneSlot")
bpy.data.objects.remove(slot, do_unlink=True)

# ── 鬍鬚（細長圓柱）─────────────────────────────────
for i, (x, y, rot) in enumerate([
    (-0.5, -1.5, 0.3), (-0.5, -1.5, 0.0), (-0.5, -1.5, -0.3),
    ( 0.5, -1.5, 0.3), ( 0.5, -1.5,  0.0), ( 0.5, -1.5, -0.3)
]):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.7,
                                         location=(x, y, 3.88))
    w = bpy.context.active_object
    w.name = f"Whisker_{i}"
    w.rotation_euler[0] = math.radians(90)
    w.rotation_euler[2] = math.radians(rot * 30)
    w.data.materials.append(mat)

print("🐱 可愛黑貓手機架建模完成！")
print("   物件清單：Base, CatBody, CatHead, EarLeft, EarRight,")
print("             EyeLeft, EyeRight, PupilLeft, PupilRight,")
print("             Nose, Tail, Whisker x6")
print("   已內嵌手機插槽（Boolean Cut）供3D列印使用")
""").strip()


# ─── Mock LLM ───────────────────────────────────────────────────────────────

def mock_llm_response() -> dict:
    return {
        "thinking": (
            "使用者要求建立一個可愛搞笑的黑貓手機架，適合3D列印。\n"
            "規劃：\n"
            "  1. 圓底盤（穩定底座）\n"
            "  2. 胖乎乎貓身體（帶手機插槽 boolean cut）\n"
            "  3. 大頭配搞笑大眼睛\n"
            "  4. 尖耳朵 × 2\n"
            "  5. 彎曲尾巴\n"
            "  6. 黑色霧面材質\n"
            "  7. 全部 manifold，無孤立面，適合 FDM 列印"
        ),
        "tool_name": "execute_blender_code",
        "arguments": {
            "code": CAT_STAND_CODE
        }
    }


# ─── Try to connect to Blender socket ───────────────────────────────────────

def try_blender_connect(host: str = "localhost", port: int = 9876) -> socket.socket | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((host, port))
        return s
    except (ConnectionRefusedError, TimeoutError, OSError):
        return None


def blender_exec(sock: socket.socket, code: str) -> dict:
    payload = json.dumps({"type": "execute_code", "code": code}) + "\n"
    sock.sendall(payload.encode())
    sock.settimeout(30)
    raw = b""
    while not raw.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            break
        raw += chunk
    return json.loads(raw.decode())


# ─── Main demo ───────────────────────────────────────────────────────────────

async def main() -> None:
    print()
    print(h("━" * 60))
    print(h("  🎨  Blender MCP Studio — 建模示範"))
    print(h("━" * 60))
    print()

    # Step 1: User input
    user_input = "幫我用 Blender 建立一個可愛搞笑的黑貓手機架模型，適合 3D 列印（FDM），要有底座、胖身體、大眼睛、插槽和彎曲尾巴。"
    p(f"{h('👤 使用者輸入', C.YELLOW)}")
    p(f'"{user_input}"', 1)
    print()
    time.sleep(0.5)

    # Step 2: Session created
    p(f"{h('🔗 Session 建立', C.CYAN)}  →  session_id: demo-cat-001")
    print()
    time.sleep(0.3)

    # Step 3: LLM processing
    p(f"{h('🤖 LLM 分析意圖中...', C.MAGENTA)}")
    time.sleep(0.8)
    response = mock_llm_response()
    p(f"{C.DIM}思考過程：{C.RESET}", 1)
    for line in response["thinking"].split("\n"):
        p(f"{C.DIM}{line}{C.RESET}", 2)
    print()
    time.sleep(0.3)

    # Step 4: Generated command
    p(f"{h('📋 LLM 輸出指令', C.GREEN)}")
    p(f"  tool_name : {C.GREEN}{response['tool_name']}{C.RESET}")
    p(f"  code      : {C.DIM}（{len(response['arguments']['code'].splitlines())} 行 bpy Python 程式碼）{C.RESET}")
    print()

    # Step 5: Try Blender
    p(f"{h('🔌 嘗試連線 Blender (localhost:9876)...', C.CYAN)}")
    sock = try_blender_connect()

    if sock:
        p(f"  {C.GREEN}✅ 連線成功！正在執行建模...{C.RESET}")
        print()
        try:
            result = blender_exec(sock, response["arguments"]["code"])
            sock.close()
            p(f"{h('✅ Blender 執行結果', C.GREEN)}")
            p(str(result), 1)
        except Exception as e:
            p(f"  {C.RED}執行錯誤：{e}{C.RESET}")
    else:
        p(f"  {C.YELLOW}⚠️  Blender 未啟動（port 9876 無回應）{C.RESET}")
        p(f"  {C.DIM}→ 以下是模擬模式：顯示將執行的 bpy 程式碼{C.RESET}")
        print()
        p(f"{h('📄 將在 Blender 執行的 bpy 程式碼：', C.MAGENTA)}")
        print()
        for i, line in enumerate(CAT_STAND_CODE.splitlines(), 1):
            print(f"  {C.DIM}{i:3d}{C.RESET}  {line}")

    print()
    print(h("━" * 60))
    p(f"{h('🐱 黑貓手機架建模流程示範完成！', C.GREEN)}")
    print()
    p("建模物件清單：")
    objects = [
        ("Base", "底座（圓柱 + Bevel）"),
        ("CatBody", "貓身體（胖球 + Boolean 手機槽）"),
        ("CatHead", "貓頭部（大球 + Subdivision）"),
        ("EarLeft / EarRight", "耳朵（尖錐，帶角度）"),
        ("EyeLeft / EyeRight", "搞笑大眼（白球）"),
        ("PupilLeft / PupilRight", "瞳孔（黑球）"),
        ("Nose", "鼻子（粉紅小錐）"),
        ("Tail", "尾巴（Bezier 曲線 + Bevel）"),
        ("Whisker x6", "鬍鬚（細圓柱）"),
        ("PhoneSlot", "手機插槽（Boolean Difference）"),
    ]
    for name, desc in objects:
        p(f"  {C.GREEN}•{C.RESET} {C.BOLD}{name:<30}{C.RESET} {C.DIM}{desc}{C.RESET}")

    print()
    p("3D 列印注意事項：")
    p(f"  {C.YELLOW}→{C.RESET} 材質：PLA 黑色（建議 0.2mm layer height）")
    p(f"  {C.YELLOW}→{C.RESET} 支撐：需要（尾巴和頭部懸空）")
    p(f"  {C.YELLOW}→{C.RESET} 填充：20-30%（確保強度）")
    p(f"  {C.YELLOW}→{C.RESET} 匯出：File > Export > STL")
    print()
    p(f"{C.DIM}啟動真實系統：./scripts/run_dev.sh  →  http://localhost:5173{C.RESET}")
    print()
    print(h("━" * 60))
    print()


if __name__ == "__main__":
    asyncio.run(main())
