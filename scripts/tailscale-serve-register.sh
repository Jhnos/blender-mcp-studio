#!/usr/bin/env bash
# tailscale-serve-register.sh
# 冪等：確保 Tailscale Serve 有 /blender 路由指向 Vite (port 19504)
# 重複執行安全（已設定則跳過）
#
# 用途：MacHomeHub 透過 https://<本機 tailnet 主機>/blender/
#       存取 Blender MCP Studio。Vite production preview 負責把 /blender/api 和
#       /blender/ws 代理到 FastAPI (port 19505)。
#
# 執行：bash scripts/tailscale-serve-register.sh

set -euo pipefail

WEB_PORT=19504
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${CONDA_PYTHON:-python3}"
# 主機名只來自 BLENDER_MCP_PUBLIC_BASE_URL 或 `tailscale status --self --json`，不寫死
TAILSCALE_HOST="$(cd "${PROJECT_ROOT}" && "${PYTHON_BIN}" -c 'from src.infrastructure.public_base_url import public_host; print(public_host())' 2>/dev/null)" || TAILSCALE_HOST=""
if [[ -z "${TAILSCALE_HOST}" ]]; then
  echo "error: 無法取得本機 Tailscale 主機名；請設定 BLENDER_MCP_PUBLIC_BASE_URL 或確認 'tailscale status --self --json' 可用（必要時設 CONDA_PYTHON）" >&2
  exit 1
fi
MOUNT_PATH="/blender"
# Target 必須含 /blender，讓 Tailscale 剝除前綴後路徑仍正確
# 行為: /blender/api/health → 剝除 /blender → /api/health → 加 target → /blender/api/health
TARGET="http://127.0.0.1:${WEB_PORT}${MOUNT_PATH}"

echo "── Blender MCP Studio × Tailscale Serve ──"

# 已有正確路由就跳過（含 /blender 前綴的 target）
if tailscale serve status 2>/dev/null | grep -q "${MOUNT_PATH}.*${TARGET}"; then
  echo "✓  路由已存在且正確：${MOUNT_PATH} → ${TARGET}"
else
  tailscale serve --bg --set-path "${MOUNT_PATH}" "${TARGET}"
  echo "✓  已設定路由：${MOUNT_PATH} → ${TARGET}"
fi

echo ""
tailscale serve status | grep -E "^https:|${MOUNT_PATH}|^\|-- /"

echo ""
echo "驗證（約 5 秒後可達）："
echo "  curl -sf https://${TAILSCALE_HOST}${MOUNT_PATH}/api/health && echo OK"
echo "  open   https://${TAILSCALE_HOST}${MOUNT_PATH}/"
