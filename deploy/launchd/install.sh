#!/usr/bin/env bash
#
# install.sh — render the SSOT plists for Blender MCP (api + web) with current
# $HOME / repo path / interpreter paths and bootstrap them into the user's
# LaunchAgents domain.
#
# Idempotent: safe to re-run after editing the plist templates.
#
# Usage:
#   bash deploy/launchd/install.sh                # both services
#   bash deploy/launchd/install.sh api            # api only
#   bash deploy/launchd/install.sh web            # web only
#
# Override interpreter paths with env vars (defaults shown):
#   CONDA_PYTHON="${HOME}/miniconda3/envs/blender-mcp/bin/python"
#   NODE_BIN="/opt/homebrew/opt/node/bin/node"
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET_DIR="${HOME}/Library/LaunchAgents"
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"

CONDA_PYTHON="${CONDA_PYTHON:-${HOME}/miniconda3/envs/blender-mcp/bin/python}"
NODE_BIN="${NODE_BIN:-/opt/homebrew/opt/node/bin/node}"

# launchctl bootout returns non-zero / noisy errors when the service isn't
# loaded. Treat the following as success: not loaded (5 / 113), EIO (5),
# ENOENT (3), in-progress (signal already delivered).
_safe_bootout() {
  local svc="$1"
  local out
  out="$(launchctl bootout "${svc}" 2>&1 || true)"
  if [[ -n "${out}" ]]; then
    case "${out}" in
      *"Could not find service"*|\
      *"No such process"*|\
      *"Input/output error"*|\
      *"Operation now in progress"*)
        # benign — service simply wasn't loaded
        ;;
      *)
        echo "${out}"
        ;;
    esac
  fi
  return 0
}

_install_one() {
  local label="$1"
  local template="${SCRIPT_DIR}/${label}.plist"
  local target="${TARGET_DIR}/${label}.plist"
  local service="${DOMAIN}/${label}"

  if [[ ! -f "${template}" ]]; then
    echo "error: template not found: ${template}" >&2
    return 1
  fi

  mkdir -p "${TARGET_DIR}"

  local tmp
  tmp="$(mktemp "${target}.XXXXXX")"
  trap 'rm -f "${tmp}"' RETURN
  sed \
    -e "s|__PROJECT_ROOT__|${PROJECT_ROOT}|g" \
    -e "s|__HOME__|${HOME}|g" \
    -e "s|__CONDA_PYTHON__|${CONDA_PYTHON}|g" \
    -e "s|__NODE_BIN__|${NODE_BIN}|g" \
    "${template}" > "${tmp}"

  if ! plutil -lint "${tmp}" >/dev/null; then
    echo "error: rendered plist failed plutil -lint: ${label}" >&2
    return 1
  fi

  _safe_bootout "${service}"

  mv "${tmp}" "${target}"
  trap - RETURN

  launchctl bootstrap "${DOMAIN}" "${target}"
  launchctl enable "${service}" 2>/dev/null || true
  launchctl kickstart -k "${service}" 2>/dev/null || true

  echo "installed: ${target}"
  echo "service:   ${service}"
}

main() {
  local which="${1:-all}"
  case "${which}" in
    all)
      _install_one com.blender-mcp.api
      _install_one com.blender-mcp.web
      ;;
    api)
      _install_one com.blender-mcp.api
      ;;
    web)
      _install_one com.blender-mcp.web
      ;;
    *)
      echo "usage: $0 [all|api|web]" >&2
      exit 2
      ;;
  esac

  echo
  echo "verify with:"
  echo "  launchctl print ${DOMAIN}/com.blender-mcp.api | head -40"
  echo "  launchctl print ${DOMAIN}/com.blender-mcp.web | head -40"
  echo "  lsof -iTCP:17823 -sTCP:LISTEN   # api"
  echo "  lsof -iTCP:19147 -sTCP:LISTEN   # web"
}

main "$@"
