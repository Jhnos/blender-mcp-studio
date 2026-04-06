#!/usr/bin/env bash
# install_blender_addon.sh — 下載並安裝 ahujasid/blender-mcp addon
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
ADDON_DIR="$ROOT/blender_addon"

ADDON_URL="https://raw.githubusercontent.com/ahujasid/blender-mcp/main/addon.py"
ADDON_FILE="$ADDON_DIR/addon.py"

echo "⬇️  下載 blender-mcp addon..."
curl -fsSL "$ADDON_URL" -o "$ADDON_FILE"

echo ""
echo "✅ Addon 已下載至: $ADDON_FILE"
echo ""
echo "接下來在 Blender 中安裝："
echo "  1. Edit > Preferences > Add-ons > Install..."
echo "  2. 選擇: $ADDON_FILE"
echo "  3. 啟用 'Interface: Blender MCP'"
echo "  4. 3D View 側欄 (N) > BlenderMCP > Connect to Claude"
