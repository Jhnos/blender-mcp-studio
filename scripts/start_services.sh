#!/usr/bin/env bash
# start_services.sh — reconcile and start the production LaunchAgents.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

bash "${PROJECT_ROOT}/deploy/launchd/install.sh" all

echo
echo "Verifying Blender MCP Studio services..."
for port in 19504 19505 9876; do
  if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null; then
    echo "  listening: ${port}"
  else
    echo "error: expected listener is missing on port ${port}" >&2
    exit 1
  fi
done

curl -fsS http://127.0.0.1:19505/api/health
echo
echo "Studio: http://127.0.0.1:19504/blender/"
