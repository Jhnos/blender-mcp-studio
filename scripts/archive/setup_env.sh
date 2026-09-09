#!/usr/bin/env bash
# setup_env.sh — 建立 conda 環境並安裝所有依賴
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

echo "🐍 建立 conda 環境 'blender-mcp'..."
conda env create -f "$ROOT/environment.yml" || conda env update -f "$ROOT/environment.yml"

echo "📦 安裝 Python 套件（editable）..."
conda run -n blender-mcp pip install -e "$ROOT[dev]"

echo "🌐 安裝前端依賴..."
cd "$ROOT/web" && npm install

echo ""
echo "✅ 環境建立完成！"
echo ""
echo "下一步："
echo "  1. 複製 .env.example 為 .env 並填入 API Key"
echo "  2. 安裝 Blender addon: scripts/install_blender_addon.sh"
echo "  3. 啟動開發環境: scripts/run_dev.sh"
