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
# HARD gates fail the run. There are no WARN gates left: ruff was cleaned and
# promoted on 2026-07-15, mypy (strict) on 2026-07-17.
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
# A failure that leaves nothing on disk cannot be diagnosed later. The terminal
# tail is for whoever is watching; this is for the flake nobody saw.
CI_LOG_DIR="${CI_LOG_DIR:-$ROOT/tmp/ci-logs}"

_run() {  # _run <hard|warn> <label> <cmd...>
  local kind="$1" label="$2"; shift 2
  local out
  if out="$("$@" 2>&1)"; then
    printf '  %sPASS%s %s\n' "$GRN" "$RST" "$label"
  elif [[ "$kind" == warn ]]; then
    printf '  %sWARN%s %s %s(non-blocking debt)%s\n' "$YEL" "$RST" "$label" "$DIM" "$RST"
  else
    local slug log
    slug="$(printf '%s' "$label" | tr -cs 'A-Za-z0-9' '-' | tr 'A-Z' 'a-z' | sed 's/-*$//')"
    mkdir -p "$CI_LOG_DIR"
    log="$CI_LOG_DIR/$(date +%Y%m%d-%H%M%S)-$slug.log"
    printf '%s\n' "$out" > "$log"
    printf '  %sFAIL%s %s %s(full output: %s)%s\n' "$RED" "$RST" "$label" "$DIM" "$log" "$RST"
    printf '%s\n' "$out" | tail -15 | sed 's/^/       /'
    FAILED+=("$label")
  fi
}

_tier() { printf '\n%s%s%s\n' "$BLD" "$1" "$RST"; }

cd "$ROOT"

_tier "T1 · static"
_run hard "web build (tsc + vite)"   bash -c 'cd web && npm run build'
_run hard "web lint (eslint)"        bash -c 'cd web && npm run lint'
_run hard "python lint (ruff)"       "$PY" -m ruff check src tests api scripts
_run hard "python format (ruff)"     "$PY" -m ruff format --check src tests api scripts
# mypy is strict-mode and clean as of 2026-07-17. Keep it that way: a green run
# here is only worth something if nothing reintroduces `Any` at a JSON boundary
# — see docs/LESSONS_LEARNED.md, "型別檢查器的綠燈可能是 Any 造成的盲區".
_run hard "python types (mypy)"      "$PY" -m mypy src api scripts --ignore-missing-imports --explicit-package-bases --no-error-summary
# mypy is blind to the isinstance(_, dict|list) -> dict[Any, Any] / list[Any] hole
# (a green run can be a zero-check run). This gate makes that class un-silent: every
# hit must route through the narrowing SSOT or carry a `# narrow-ok:` waiver. See the
# script header and docs/LESSONS_LEARNED.md 2026-07-17/18.
_run hard "python container-narrowing" "$PY" scripts/check_container_narrowing.py src api scripts

_tier "T2 · unit + headless dummy run"
# tests/e2e is hermetic (Mock adapters / TestClient — no real Blender or LLM)
# MCP coverage uses the real registry and protocol framing with a fake Blender port.
# The whole directory is now fully green and gated. It was previously ungated,
# which let test_full_pipeline_create_object rot red for a month
# (create_object vs execute_code — a stale assertion, not a bug; the pipeline
# correctly rewrites high-level tools to execute_code since 46fe5b3).
_run hard "python unit + e2e (pytest)" "$PY" -m pytest tests/unit tests/e2e -q --no-header -p no:cacheprovider --no-cov
_run hard "web unit + dummy run (vitest)" bash -c 'cd web && npx vitest run'

if (( REAL )); then
  _tier "T3 · real machine (MCP↔Blender)"
  if nc -z localhost 9876 2>/dev/null; then
    # Deployment artifacts live on this machine only, so this belongs here and
    # not in the hermetic tier: a fresh checkout has no LaunchAgents to inspect.
    _run hard "installed LaunchAgents match this checkout" "$PY" scripts/check_installed_plists.py
    _run hard "REST pipeline (nonce + independent oracle)" "$PY" scripts/verify/mcp_verify_rest.py
    _run hard "MCP protocol (nonce + independent oracle)" "$PY" scripts/verify/mcp_verify_real.py
    # The conversation path — the project's stated Phase 1 — had a verifier that
    # was never referenced here and did not even import. An unreferenced script
    # and a broken one look identical from outside. 5/5 since the scene list
    # stopped being the addon's first ten objects.
    _run hard "chat path (WS + REST, independent oracle)" "$PY" scripts/verify/mcp_verify_chat.py
    _run hard "print readiness (real Blender fixtures)" "$PY" scripts/verify/print_readiness_verify_real.py
    _run hard "batch transform (one Undo, independent oracle)" "$PY" scripts/verify/batch_transform_verify_real.py
    _run hard "lab station fit prototype (not load or assembly acceptance)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/lab_station.json
    _run hard "lab station lift parts (same scene)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/lab_station_lifts.json --skip-generate
    _run hard "lab station clamp parts (same scene)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/lab_station_clamps.json --skip-generate
    _run hard "lab station arm parts (same scene)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/lab_station_arms.json --skip-generate
    _run hard "lab station right arm parts (same scene)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/lab_station_arms_right.json --skip-generate
    _run hard "rotary lift concept motion (not print or load qualification)" "$PY" -m scripts.verify.lab_rotary_verify_real
    _run hard "rotary left support mesh contract" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/lab_rotary_support_capillary.json
    _run hard "rotary right support mesh contract" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/lab_rotary_support_pH_temp.json --skip-generate
    # Every contract under scripts/verify/contracts runs here (DEFERRALS D-004,
    # resolved 2026-09-09 once the hand gates measured seconds, not minutes).
    # Scenes are reused in the documented order: a base contract generates, the
    # contracts after it read that scene with --skip-generate, and the probe
    # contracts measure it read-only. About a minute in total; the pin test
    # refuses a contract file that is not listed here.
    _run hard "inset hinge contract"                "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/inset_hinge.json
    _run hard "inset hinge pins (same scene)"       "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/inset_hinge_pins.json --skip-generate
    _run hard "inset hinge probe (read-only)"       "$PY" scripts/verify/mesh_probe_verify_real.py scripts/verify/contracts/inset_hinge_probe.json
    _run hard "biaxial hinge contract"              "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/biaxial_hinge.json
    _run hard "biaxial hinge PIP (same scene)"      "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/biaxial_hinge_pip.json --skip-generate
    _run hard "biaxial hinge split (same scene)"    "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/biaxial_hinge_split.json --skip-generate
    _run hard "biaxial hinge probe (read-only)"     "$PY" scripts/verify/mesh_probe_verify_real.py scripts/verify/contracts/biaxial_hinge_probe.json
    _run hard "biaxial hinge split probe (read-only)" "$PY" scripts/verify/mesh_probe_verify_real.py scripts/verify/contracts/biaxial_hinge_split_probe.json
    _run hard "hollow side hinge contract"          "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hollow_side_hinge.json
    _run hard "octopus hand V1 contract"            "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/octopus_hand.json
    _run hard "octopus hand V1 tips (same scene)"   "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/octopus_hand_tips.json --skip-generate
    _run hard "octopus hand V2 contract"            "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/octopus_hand_v2.json
    _run hard "octopus hand V2 tips (same scene)"   "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/octopus_hand_v2_tips.json --skip-generate
    # The hand contracts caught ten defects in one campaign while being run by hand;
    # a gate outside ci.sh is a gate that is not run. Order matters: the finger
    # contract reuses the scene the hand contract generated, and the differential
    # reads the STLs that generation exported to tmp/hand-v3. First-run timings are
    # recorded in docs/30-verification.md.
    _run hard "hand-v3 contract (real Blender + MCP)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_v3.json
    _run hard "hand-v3 finger contract (same scene)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_v3_finger.json --skip-generate
    _run hard "hand-v3 regenerated package matches shipped" "$PY" scripts/verify/regenerated_package_matches_shipped.py --package hand-v3
    # The gradient fixture: V3's link, two part numbers, its own namespace. Proves
    # on the real machine that a finger's part-number count is the instance's
    # claim (expected_shared_mesh_count) and not a limit of the generator.
    _run hard "hand-v3 gradient fixture contract" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_v3_gradient.json
    _run hard "hand-v3 gradient fixture finger (same scene)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_v3_gradient_finger.json --skip-generate
    # The three-station instance: the same generator at a finger count it had
    # never been built at, which is the whole reason it exists.
    _run hard "hand-gripper contract" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_gripper.json
    _run hard "hand-gripper finger (same scene)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_gripper_finger.json --skip-generate
    # Published 2026-09-09 on the user's Lane B verdict: from here the shipped bytes
    # are re-derived on every real run, the same rule as hand-v3 and hand-compact.
    _run hard "hand-gripper regenerated package matches shipped" "$PY" scripts/verify/regenerated_package_matches_shipped.py --package hand-gripper
    # The human-scale instance: the compact link through the same generator.
    _run hard "hand-compact contract" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_compact.json
    _run hard "hand-compact finger (same scene)" "$PY" scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_compact_finger.json --skip-generate
    # Published 2026-09-09 on the user's Lane B verdict (D-008): from here the shipped
    # bytes are re-derived on every real run, the same rule as hand-v3.
    _run hard "hand-compact regenerated package matches shipped" "$PY" scripts/verify/regenerated_package_matches_shipped.py --package hand-compact
    # Last on purpose: it empties tmp/hand-compact and rebuilds through the public
    # REST endpoint, so it must not run before the checks that read what the script
    # path generated. Proves the product's own delivery path produces the shipped
    # geometry, not only that a CI-only entry point can.
    _run hard "hand-compact built through the REST delivery path" "$PY" scripts/verify/generation_delivery_verify_real.py --package hand-compact
    # The measured half of the sliver budget. Vertex ordering differs on nearly
    # every boolean step — that is the exact solver, not a defect — so this runs
    # on the budget criterion, not on exact agreement. The checked-in record in
    # docs/hand-framework/determinism.json is what the unit gate compares against.
    _run hard "hand-compact build determinism within budget" "$PY" scripts/verify/build_determinism_probe.py --instance hand-compact --runs 3 --against-budget
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
