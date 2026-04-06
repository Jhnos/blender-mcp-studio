#!/bin/bash
# start_services.sh — 啟動所有開發服務（API + Vite）
# 自動選用空閒 port，不干擾其他服務

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

API_PORT=17823
WEB_PORT=19147

echo "🚀 Blender MCP Studio 服務啟動"
echo "================================"

# ── 檢查 port 是否已在用 ────────────────────────────────────────────
for PORT in $API_PORT $WEB_PORT; do
  if lsof -i :"$PORT" -t &>/dev/null; then
    echo "⚠️  Port $PORT 已佔用，跳過啟動"
  fi
done

# ── FastAPI ──────────────────────────────────────────────────────────
if ! lsof -i :"$API_PORT" -t &>/dev/null; then
  echo "▶  FastAPI → localhost:$API_PORT"
  cd "$ROOT"
  nohup conda run -n blender-mcp python -c \
    "import uvicorn; uvicorn.run('api.main:app', host='127.0.0.1', port=$API_PORT)" \
    < /dev/null > /tmp/api_${API_PORT}.log 2>&1 &
  disown $!
  sleep 5
  if curl -sf http://localhost:$API_PORT/api/health > /dev/null; then
    echo "   ✅ API 就緒"
  else
    echo "   ❌ API 啟動失敗，查看 /tmp/api_${API_PORT}.log"
  fi
fi

# ── Vite ─────────────────────────────────────────────────────────────
if ! lsof -i :"$WEB_PORT" -t &>/dev/null; then
  echo "▶  Vite   → localhost:$WEB_PORT"
  cd "$ROOT/web"
  nohup node node_modules/.bin/vite --port $WEB_PORT --logLevel warn \
    < /dev/null > /tmp/vite_${WEB_PORT}.log 2>&1 &
  disown $!
  sleep 4
  if curl -sf http://localhost:$WEB_PORT > /dev/null; then
    echo "   ✅ Vite 就緒"
  else
    echo "   ❌ Vite 啟動失敗，查看 /tmp/vite_${WEB_PORT}.log"
  fi
fi

echo ""
echo "================================"
echo "🌐  UI  → http://localhost:$WEB_PORT"
echo "📡  API → http://localhost:$API_PORT"
echo "================================"
open "http://localhost:$WEB_PORT" 2>/dev/null || true
