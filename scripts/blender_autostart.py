"""
blender_autostart.py
Blender 啟動腳本：自動啟用 blender_mcp addon 並啟動 socket server（port 9876）。

使用方式（由 run_blender.sh 呼叫）：
  /Applications/Blender.app/Contents/MacOS/Blender --python scripts/blender_autostart.py
"""

import bpy


def autostart():
    # Enable addon
    bpy.ops.preferences.addon_enable(module="blender_mcp")
    bpy.ops.wm.save_userpref()

    # Small delay then start server
    def _start():
        try:
            bpy.ops.blendermcp.start_server()
            print("[AutoStart] ✅ BlenderMCP server started on port 9876")
        except Exception as e:
            print(f"[AutoStart] ❌ Failed to start server: {e}")
        return None  # don't repeat

    bpy.app.timers.register(_start, first_interval=1.5)


autostart()
