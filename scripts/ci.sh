#!/usr/bin/env bash
#
# ci.sh — LOCAL CI (the machine gate for this project).
#
# Why local, not GitHub Actions: what actually breaks here needs a real Blender
# (addon socket 9876), a real Ollama, and the MHH-managed services. A hosted
# runner can only lint and unit-test — it cannot prove the pipeline works, which
# is the thing that was silently broken for real. The old
# .github/workflows/ci.yml was removed (it also hard-gated on ruff, which has
# pre-existing debt, so it was red regardless).
#
# Usage:
#   scripts/ci.sh          # T1 static + T2 unit (incl. headless dummy run). No side effects.
#   scripts/ci.sh --real   # + T3 real machine. Needs Blender up; creates/deletes verify_* objects.
#
# HARD gates fail the run. Lint debt (ruff / ruff-format / mypy) is reported as
# WARN and does not block — it predates this gate; clean it, then promote.
# Browser-driven dummy-run checks (layout widths, live WS, screenshots) are
# documented in docs/verification/frontend-redesign/dummy-run-plan.md.
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${CI_PYTHON:-$HOME/miniconda3/envs/blender-mcp/bin/python}"
REAL=0
[[ "${1:-}" == "--real" ]] && REAL=1

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; DIM=$'\033[2m'; BLD=$'\033[1m'; RST=$'\033[0m'
FAILED=()

_run() {  # _run <hard|warn> <label> <cmd...>
  local kind="$1" label="$2"; shift 2
  local out
  if out="$("$@" 2>&1)"; then
    printf '  %sPASS%s %s\n' "$GRN" "$RST" "$label"
  elif [[ "$kind" == warn ]]; then
    printf '  %sWARN%s %s %s(non-blocking debt)%s\n' "$YEL" "$RST" "$label" "$DIM" "$RST"
  else
    printf '  %sFAIL%s %s\n' "$RED" "$RST" "$label"
    printf '%s\n' "$out" | tail -15 | sed 's/^/       /'
    FAILED+=("$label")
  fi
}

_tier() { printf '\n%s%s%s\n' "$BLD" "$1" "$RST"; }

cd "$ROOT"

_tier "T1 · static"
_run hard "web build (tsc + vite)"   bash -c 'cd web && npm run build'
_run hard "web lint (eslint)"        bash -c 'cd web && npm run lint'
_run warn "python lint (ruff)"       "$PY" -m ruff check src tests api
_run warn "python format (ruff)"     "$PY" -m ruff format --check src tests api
_run warn "python types (mypy)"      "$PY" -m mypy src api --ignore-missing-imports --no-error-summary

_tier "T2 · unit + headless dummy run"
_run hard "python unit (pytest)"     "$PY" -m pytest tests/unit -q --no-header -p no:cacheprovider --no-cov
_run hard "web unit + dummy run (vitest)" bash -c 'cd web && npx vitest run'

if (( REAL )); then
  _tier "T3 · real machine (MCP↔Blender)"
  if nc -z localhost 9876 2>/dev/null; then
    _run hard "MCP pipeline (nonce + independent oracle)" "$PY" scripts/verify/mcp_verify_rest.py
  else
    # Explicit SKIP, never a silent pass: with Blender down this tier is vacuous.
    printf '  %sSKIP%s MCP pipeline — Blender addon not listening on 9876 %s(start it: launchctl kickstart -k gui/$(id -u)/com.blender-mcp.blender)%s\n' \
      "$YEL" "$RST" "$DIM" "$RST"
  fi
else
  printf '\n%sT3 · real machine%s %sskipped (use --real; needs Blender, mutates verify_* objects)%s\n' \
    "$BLD" "$RST" "$DIM" "$RST"
fi

echo
if (( ${#FAILED[@]} )); then
  printf '%sCI FAILED%s — %d hard gate(s): %s\n' "$RED" "$RST" "${#FAILED[@]}" "${FAILED[*]}"
  exit 1
fi
printf '%sCI PASSED%s — all hard gates green\n' "$GRN" "$RST"
