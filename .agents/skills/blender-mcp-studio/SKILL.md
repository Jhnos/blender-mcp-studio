---
name: blender-mcp-studio
description: Develop, diagnose, deploy, or verify this repository's client-neutral Blender MCP Studio across its DDD application layer, Blender adapters, REST/MCP delivery, React WebUI, launchd services, and real-Blender gates. Use for changes involving Blender tools, scene operations, print readiness, exports, Web UI controls, MCP catalog or annotations, addon socket behavior, ports 19504/19505/9876, Tailscale `/blender`, or production service verification.
---

# Blender MCP Studio workflow

Use this skill only inside the Blender MCP Studio repository. Treat `AGENTS.md` as the
binding repository policy and this skill as the task-specific execution path.

## Orient without rescanning

1. Read `docs/tasks/00_INDEX.md`.
2. Read the linked `ACTIVE` or `AWAITING-ACCEPTANCE` task and its hand-off.
3. Run `git log --oneline -5` and `git status --short --branch`.
4. Before debugging, search `docs/LESSONS_LEARNED.md` for the failure class.
5. Open only the architecture or client document named by the task.

Completed implementation plans live in `docs/archive/`; never infer active work from them.

## Preserve the architecture

- Keep domain values immutable and framework-free.
- Put orchestration and validation in application services behind narrow ports.
- Put `bpy`, addon dialect, HTTP, FastMCP, and UI framework knowledge in adapters/delivery.
- Inject the same service instance into REST and MCP through one `AppRuntime`.
- Keep the Blender socket serialized; do not create a second transport owner.
- Extend public MCP behavior through curated typed tools. Never publish arbitrary
  `execute_code`, host-name conditionals, or WebUI-only contracts.
- Keep Web command definitions pure and inject callbacks; mutation feedback belongs in the
  operation lifecycle store, not component-local toast state.

## Develop test-first

For each behavior, complete one RED→GREEN→REFACTOR loop before starting the next:

1. Name the observable contract and write one discriminating failing test.
2. Run the smallest test command and confirm it fails for the intended reason.
3. Implement the minimum change without weakening the test.
4. Re-run the focused test, then the nearest contract suite.
5. Refactor only while green.

Useful focused commands:

```bash
$HOME/miniconda3/envs/blender-mcp/bin/python -m pytest <test-path> -q --no-cov
npm --prefix web test -- --run <test-path>
npm --prefix web run lint
npm --prefix web run build
```

## Follow the change path

For a new public Blender capability, normally change these seams in order:

```text
domain value → narrow port → application service → Blender adapter
             → AppRuntime composition → REST/MCP delivery → Web consumer
```

Do not add a delivery-specific shortcut around the service. Add catalog and annotation tests
when MCP changes; add unit conversion and independent-oracle checks when geometry changes.

For a Web-only workflow, keep domain parsing/validation separate from React, route requests
through existing typed actions, and test keyboard, accessibility, stale state, and failure paths.

## Deploy through the SSOT

Production services are LaunchAgents sourced from `deploy/launchd/`. Never edit installed
plists directly and never substitute a detached dev process for production evidence.

```bash
bash deploy/launchd/install.sh all
launchctl print gui/$(id -u)/com.blender-mcp.web
lsof -nP -iTCP:19504 -iTCP:19505 -iTCP:9876 -sTCP:LISTEN
curl -fsS http://127.0.0.1:19505/api/health
```

The long-running Web service must load hashed production assets, not `/@vite/client`. Manual
development uses `bash scripts/run_dev.sh` and Web port 5173.

## Verify in layers

1. Run focused tests while iterating.
2. Run `scripts/ci.sh` before every commit.
3. Run `scripts/ci.sh --real` for Blender/MCP/geometry changes; a SKIP is not acceptance.
4. For UI or deployment changes, inspect the formal `/blender` page, browser console, served
   asset URLs, and application behavior. A rendered page alone is insufficient evidence.
5. Prefer public REST/MCP for the behavior under test and use the addon socket only as an
   independent oracle in verification scripts.

## Generated mechanical artifacts

For generated mechanical artifacts, reuse the contract-driven workflow in
`docs/verification/generated-artifacts.md` and `scripts/verify/contracts/`. Keep specification,
Blender geometry, presentation, export and evidence assessment separate. Add a model contract
rather than copying the socket/MCP harness. Check world-space collisions and sampled motion;
never infer printability or load capacity from a render. Generated outputs belong in ignored
`tmp/`, not source control. Obtain independent visual evidence after final geometry changes.

## Close the milestone

- Update the task hand-off with verified facts, open failures, and one next step.
- Run the knowledge 5S scanner; archive accepted task/campaign material.
- Update `VERSION` and `CHANGELOG.md` through the version-management tools.
- Commit without unrelated files, run the checkpoint checker, then push without force.
