#!/usr/bin/env bash
# run_dev.sh — foreground development only; production is managed by launchd.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
API_PORT=19505
WEB_PORT=5173
DEV_PYTHON="${CI_PYTHON:-${HOME}/miniconda3/envs/blender-mcp/bin/python}"

for port in "${API_PORT}" "${WEB_PORT}"; do
  if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null; then
    echo "error: port ${port} is already in use; stop the conflicting service first" >&2
    exit 1
  fi
done

cleanup() {
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "${PROJECT_ROOT}"
"${DEV_PYTHON}" -m uvicorn api.main:app --reload --host 127.0.0.1 --port "${API_PORT}" &
BACKEND_PID=$!

npm --prefix web run dev -- --host 127.0.0.1 --port "${WEB_PORT}" &
FRONTEND_PID=$!

echo "API: http://127.0.0.1:${API_PORT}"
echo "Web: http://127.0.0.1:${WEB_PORT}/blender/"
echo "Press Ctrl+C to stop both foreground processes."
wait
