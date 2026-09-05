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
NPM_BIN="${NPM_BIN:-$(dirname "${NODE_BIN}")/npm}"
BLENDER_BIN="${BLENDER_BIN:-/Applications/Blender.app/Contents/MacOS/Blender}"

_build_web_assets() {
  "${NPM_BIN}" --prefix "${PROJECT_ROOT}/web" run build
}

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

_wait_for_unload() {
  local service="$1" attempt
  for attempt in {1..20}; do
    if ! launchctl print "${service}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "error: launchd service did not unload in time: ${service}" >&2
  return 1
}

_wait_for_listener() {
  local host="$1" port="$2" label="$3" attempt
  # A measured cold Blender 5.1 launch on the target M4 took about 40 seconds.
  # Keep the wait bounded but leave enough margin for preference/addon startup.
  for attempt in {1..180}; do
    if nc -z "${host}" "${port}" >/dev/null 2>&1; then
      echo "ready:     ${label} (${host}:${port})"
      return 0
    fi
    sleep 0.5
  done
  echo "error: ${label} did not listen on ${host}:${port} within 90 seconds" >&2
  return 1
}

# launchd can keep a just-booted-out service in its internal deregistration
# window briefly. An immediate bootstrap then returns EIO even though the
# rendered plist is valid. Retry only that bounded local registration step;
# fail loudly after five attempts and never hide a genuine invalid plist.
_bootstrap_with_retry() {
  local domain="$1" target="$2"
  local attempt out

  for attempt in 1 2 3 4 5; do
    if out="$(launchctl bootstrap "${domain}" "${target}" 2>&1)"; then
      return 0
    fi
    if [[ "${attempt}" -eq 5 ]]; then
      echo "${out}" >&2
      return 1
    fi
    sleep 0.5
  done
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
    -e "s|__BLENDER_BIN__|${BLENDER_BIN}|g" \
    "${template}" > "${tmp}"

  if ! plutil -lint "${tmp}" >/dev/null; then
    echo "error: rendered plist failed plutil -lint: ${label}" >&2
    return 1
  fi

  _safe_bootout "${service}"
  _wait_for_unload "${service}"

  mv "${tmp}" "${target}"
  trap - RETURN

  _bootstrap_with_retry "${DOMAIN}" "${target}"
  launchctl enable "${service}" 2>/dev/null || true
  launchctl kickstart -k "${service}" 2>/dev/null || true

  echo "installed: ${target}"
  echo "service:   ${service}"
}

main() {
  local which="${1:-all}"
  case "${which}" in
    all)
      _build_web_assets
      _install_one com.blender-mcp.blender
      _wait_for_listener "127.0.0.1" "9876" "Blender addon"
      _install_one com.blender-mcp.api
      _install_one com.blender-mcp.web
      ;;
    blender)
      # Restarting Blender kills the socket the API process is holding. The API
      # connects once at startup and does not reconnect, so it would keep
      # answering with a dead socket: /api/health reports "disconnected" while
      # scene reads fail as malformed payloads rather than as "Blender is
      # unreachable". Rebuild the dependency in the same order `all` uses.
      _install_one com.blender-mcp.blender
      _wait_for_listener "127.0.0.1" "9876" "Blender addon"
      _install_one com.blender-mcp.api
      ;;
    api)
      _install_one com.blender-mcp.api
      ;;
    web)
      _build_web_assets
      _install_one com.blender-mcp.web
      ;;
    *)
      echo "usage: $0 [all|blender|api|web]" >&2
      exit 2
      ;;
  esac

  echo
  echo "verify with:"
  echo "  launchctl print ${DOMAIN}/com.blender-mcp.blender | head -40"
  echo "  launchctl print ${DOMAIN}/com.blender-mcp.api | head -40"
  echo "  launchctl print ${DOMAIN}/com.blender-mcp.web | head -40"
  echo "  lsof -iTCP:9876  -sTCP:LISTEN   # blender addon (engine)"
  echo "  lsof -iTCP:19505 -sTCP:LISTEN   # api"
  echo "  lsof -iTCP:19504 -sTCP:LISTEN   # web"
}

main "$@"
