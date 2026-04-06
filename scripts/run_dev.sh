#!/usr/bin/env bash
# run_dev.sh — 同時啟動 FastAPI backend 和 Vite 前端
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 啟動 FastAPI backend (port 8000)..."
conda run -n blender-mcp uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "🌐 啟動 Vite 前端 (port 5173)..."
cd "$ROOT/web" && npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 開發環境啟動！"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服務"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
