#!/usr/bin/env bash
# integrate_tailnet.sh — Blender MCP Studio × MHH Tailnet 整合腳本
# 冪等：重複執行安全，已設定項目會跳過
#
# 執行方式：
#   cd /Users/bearmacmini/Desktop/Blender_MCP_drawer
#   bash scripts/integrate_tailnet.sh
#
# 完成後驗證（均走 Tailscale URL）：
#   curl -sf https://bearmacminimac-mini.tail56c751.ts.net/blender/
#   curl -sf https://bearmacminimac-mini.tail56c751.ts.net/blender/api/health

set -euo pipefail

# ── 常數 ─────────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB_DIR="$ROOT/web"
DEPLOY_DIR="$ROOT/deploy"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
MHH_SERVICES="$HOME/MacHomeHub/config/services.yaml"
TAILSCALE_HOST="bearmacminimac-mini.tail56c751.ts.net"

API_PORT=17823
WEB_PORT=19147
BLENDER_TCP_PORT=9876

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*" >&2; }

echo ""
echo "========================================="
echo "  Blender MCP Studio — Tailnet 整合腳本"
echo "========================================="
echo ""

# ── Step 1：修改 vite.config.ts ───────────────────────────────────────
echo "Step 1: 修改 vite.config.ts"
VITE_CONFIG="$WEB_DIR/vite.config.ts"

if grep -q "base: '/blender'" "$VITE_CONFIG"; then
  warn "vite.config.ts 已含 base: '/blender'，跳過"
else
  # 備份
  cp "$VITE_CONFIG" "${VITE_CONFIG}.bak"

  # 用 Python 做精確替換（避免 sed 跨平台問題）
  python3 - <<'PYEOF'
import re, pathlib

path = pathlib.Path("web/vite.config.ts")
content = path.read_text()

new_content = '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  base: '/blender',
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/ws': { target: 'ws://localhost:17823', ws: true },
      '/api': { target: 'http://localhost:17823' },
    },
  },
})
'''

path.write_text(new_content)
print("vite.config.ts 已更新")
PYEOF

  info "vite.config.ts 已修改（備份：${VITE_CONFIG}.bak）"
fi

# ── Step 2：修改 useWebSocket.ts ─────────────────────────────────────
echo ""
echo "Step 2: 修改 useWebSocket.ts"
WS_HOOK="$WEB_DIR/src/hooks/useWebSocket.ts"

if grep -q "import.meta.env.BASE_URL" "$WS_HOOK"; then
  warn "useWebSocket.ts 已含動態 BASE_URL，跳過"
else
  cp "$WS_HOOK" "${WS_HOOK}.bak"

  python3 - <<'PYEOF'
import pathlib

path = pathlib.Path("web/src/hooks/useWebSocket.ts")
content = path.read_text()

old_line = "const WS_URL = '/ws/chat'  // via Vite proxy → localhost:8001"
new_lines = """// 動態推導 WebSocket URL，支援 Tailscale sub-path（/blender）
// BASE_URL 由 Vite base config 注入：dev=/blender/, prod=/blender/
const _base = import.meta.env.BASE_URL.replace(/\\/$/, '') // e.g. '/blender'
const _proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = `${_proto}//${location.host}${_base}/ws/chat`"""

if old_line in content:
    content = content.replace(old_line, new_lines)
    path.write_text(content)
    print("useWebSocket.ts 已更新")
else:
    print("WARNING: 找不到預期的 WS_URL 行，請手動確認 useWebSocket.ts")
PYEOF

  info "useWebSocket.ts 已修改（備份：${WS_HOOK}.bak）"
fi

# ── Step 3：建立 deploy/ 目錄與 plist 檔案 ───────────────────────────
echo ""
echo "Step 3: 建立 launchd plist 檔案"
mkdir -p "$DEPLOY_DIR"

# 3a. API plist
API_PLIST="$DEPLOY_DIR/com.blender-mcp.api.plist"
if [[ -f "$API_PLIST" ]]; then
  warn "com.blender-mcp.api.plist 已存在，跳過"
else
  # 找 conda Python 路徑
  CONDA_PYTHON=$(conda run -n blender-mcp which python 2>/dev/null || echo "")
  if [[ -z "$CONDA_PYTHON" ]]; then
    warn "找不到 conda env 'blender-mcp' 的 Python，plist 使用 /usr/bin/env python3（需確認）"
    CONDA_PYTHON="/usr/bin/env python3"
  fi

  cat > "$API_PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.blender-mcp.api</string>

  <key>ProgramArguments</key>
  <array>
    <string>${CONDA_PYTHON}</string>
    <string>-c</string>
    <string>import uvicorn; uvicorn.run('api.main:app', host='127.0.0.1', port=${API_PORT}, log_level='info')</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${ROOT}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>CORS_ORIGINS</key>
    <string>https://${TAILSCALE_HOST},http://localhost:${WEB_PORT}</string>
    <key>BLENDER_HOST</key>
    <string>localhost</string>
    <key>BLENDER_PORT</key>
    <string>${BLENDER_TCP_PORT}</string>
  </dict>

  <key>StandardOutPath</key>
  <string>/tmp/blender-mcp-api.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/blender-mcp-api.err</string>

  <key>RunAtLoad</key>
  <false/>
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
PLIST_EOF

  info "com.blender-mcp.api.plist 已建立"
fi

# 3b. Web (Vite) plist
WEB_PLIST="$DEPLOY_DIR/com.blender-mcp.web.plist"
NODE_BIN=$(which node 2>/dev/null || echo "/usr/local/bin/node")

if [[ -f "$WEB_PLIST" ]]; then
  warn "com.blender-mcp.web.plist 已存在，跳過"
else
  cat > "$WEB_PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.blender-mcp.web</string>

  <key>ProgramArguments</key>
  <array>
    <string>${NODE_BIN}</string>
    <string>node_modules/.bin/vite</string>
    <string>--port</string>
    <string>${WEB_PORT}</string>
    <string>--logLevel</string>
    <string>warn</string>
    <string>--host</string>
    <string>127.0.0.1</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${WEB_DIR}</string>

  <key>StandardOutPath</key>
  <string>/tmp/blender-mcp-web.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/blender-mcp-web.err</string>

  <key>RunAtLoad</key>
  <false/>
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
PLIST_EOF

  info "com.blender-mcp.web.plist 已建立"
fi

# ── Step 4：安裝 plist 到 LaunchAgents ───────────────────────────────
echo ""
echo "Step 4: 安裝 plist 到 ~/Library/LaunchAgents/"

for PLIST_FILE in "$API_PLIST" "$WEB_PLIST"; do
  PLIST_NAME="$(basename "$PLIST_FILE")"
  DEST="$LAUNCH_AGENTS/$PLIST_NAME"

  # 如果已 load，先 unload
  if launchctl list | grep -q "${PLIST_NAME%.plist}" 2>/dev/null; then
    launchctl unload "$DEST" 2>/dev/null || true
    warn "已 unload 舊的 ${PLIST_NAME%.plist}"
  fi

  cp "$PLIST_FILE" "$DEST"
  launchctl load "$DEST"
  info "$PLIST_NAME 已安裝並 load"
done

# ── Step 5：加入 MHH services.yaml ───────────────────────────────────
echo ""
echo "Step 5: 更新 MHH services.yaml"

if [[ ! -f "$MHH_SERVICES" ]]; then
  error "找不到 $MHH_SERVICES，請確認 MacHomeHub 路徑"
  echo "  跳過 MHH services.yaml 更新（可手動加入，見 docs/INTEGRATION.md §3.5）"
else
  if grep -q "Blender MCP Studio" "$MHH_SERVICES"; then
    warn "MHH services.yaml 已含 Blender MCP Studio，跳過"
  else
    cp "$MHH_SERVICES" "${MHH_SERVICES}.bak"

    cat >> "$MHH_SERVICES" <<YAML_EOF

  - name: "Blender MCP Studio"
    icon: "🎨"
    description: "Blender AI 建模工作室（React + FastAPI）"
    primary:
      port: ${WEB_PORT}
      funnel_path: "/blender/"
      open_url: "https://${TAILSCALE_HOST}/blender/"
      strip_prefix: false
      health_endpoints:
        - path: "/blender/api/health"
          url: "https://${TAILSCALE_HOST}/blender/api/health"
      auto_intervene: false
      expected_process: "node"
    internal:
      - name: "Blender MCP API"
        port: ${API_PORT}
        expected_process: "python3"
YAML_EOF

    info "MHH services.yaml 已更新（備份：${MHH_SERVICES}.bak）"
  fi
fi

# ── 完成 ─────────────────────────────────────────────────────────────
echo ""
echo "========================================="
echo "  整合完成！請依序執行以下驗證："
echo "========================================="
echo ""
echo "1. 啟動服務："
echo "   launchctl start com.blender-mcp.api"
echo "   launchctl start com.blender-mcp.web"
echo ""
echo "2. 重啟 MHH（讓 services.yaml 生效）："
echo "   # 在 MacHomeHub 目錄執行 ./run.sh serve，或 launchctl kickstart MHH"
echo ""
echo "3. 驗證（走 Tailscale URL）："
echo "   curl -sf https://${TAILSCALE_HOST}/blender/api/health"
echo "   curl -sf https://${TAILSCALE_HOST}/blender/ | grep -o '<div id=\"root\"'"
echo ""
echo "4. 瀏覽器開啟："
echo "   https://${TAILSCALE_HOST}/blender/"
echo ""
