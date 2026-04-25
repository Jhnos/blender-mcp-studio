#!/usr/bin/env bash
#
# uninstall.sh — bootout the Blender MCP LaunchAgents and archive the installed
# plists.  The plists are moved to <name>.plist.deprecated.YYYYMMDD rather than
# deleted, so a previous install is recoverable for one rollback step.
#
# Usage:
#   bash deploy/launchd/uninstall.sh              # both services
#   bash deploy/launchd/uninstall.sh api          # api only
#   bash deploy/launchd/uninstall.sh web          # web only
#
set -euo pipefail

TARGET_DIR="${HOME}/Library/LaunchAgents"
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"

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
        ;;
      *)
        echo "${out}"
        ;;
    esac
  fi
  return 0
}

_uninstall_one() {
  local label="$1"
  local target="${TARGET_DIR}/${label}.plist"
  local service="${DOMAIN}/${label}"

  _safe_bootout "${service}"

  if [[ -f "${target}" ]]; then
    local stamp archive n
    stamp="$(date +%Y%m%d)"
    archive="${target}.deprecated.${stamp}"
    if [[ -e "${archive}" ]]; then
      n=1
      while [[ -e "${archive}.${n}" ]]; do n=$((n + 1)); done
      archive="${archive}.${n}"
    fi
    mv "${target}" "${archive}"
    echo "archived: ${archive}"
  else
    echo "nothing to remove: ${target} does not exist"
  fi

  echo "service ${service} booted out."
}

main() {
  local which="${1:-all}"
  case "${which}" in
    all)
      _uninstall_one com.blender-mcp.api
      _uninstall_one com.blender-mcp.web
      ;;
    api)
      _uninstall_one com.blender-mcp.api
      ;;
    web)
      _uninstall_one com.blender-mcp.web
      ;;
    *)
      echo "usage: $0 [all|api|web]" >&2
      exit 2
      ;;
  esac
}

main "$@"
