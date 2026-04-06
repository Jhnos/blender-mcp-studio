#!/usr/bin/env bash
# run_blender.sh — 啟動 Blender 並自動啟用 BlenderMCP addon + 開啟 server
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART="$SCRIPT_DIR/blender_autostart.py"

echo "🦊 啟動 Blender 5.1 + BlenderMCP addon..."
/Applications/Blender.app/Contents/MacOS/Blender --python "$AUTOSTART" &
BLENDER_PID=$!

echo "   Blender PID: $BLENDER_PID"
echo "   等待 server 啟動（port 9876）..."

# Wait for port 9876 to be open
for i in $(seq 1 20); do
    if nc -z localhost 9876 2>/dev/null; then
        echo "   ✅ Blender MCP server 就緒！"
        break
    fi
    echo "   ... 等待中 ($i/20)"
    sleep 1
done

echo ""
echo "現在可以執行："
echo "  conda run -n blender-mcp python scripts/demo_cat_stand.py"
