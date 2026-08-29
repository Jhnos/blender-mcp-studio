# Changelog

本專案所有值得注意的變更記錄於此。格式依 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)；
版號依全域 version-management 規範（base36 固定寬度 VXX.XX.XXX；任何修改至少 bump 段3）。

## [Unreleased]

### V01.00.002

#### Added

- Added an immutable one-part vertebra contract and Blender generator: three instances share
  one mesh, while two ball-socket interfaces provide four named X/Y rotational axes and four
  continuous tendon routes.

#### Changed

- Replaced the earlier disc-and-cross-gimbal prototype with one repeatable 42 mm vertebra
  carrying a 10.0 mm male ball and 10.6 mm Y-split female socket.
- Removed the whole-part bevel after real MCP analysis exposed slot-edge defects; the final
  report has no non-manifold or intersection findings and retains honest support warnings.

### V01.00.001

#### Added

- Added an immutable, validated two-cell tendon-joint specification with RED-to-GREEN tests
  and a Blender 5.1 generator for three female-yoke discs, two male cross-gimbals, four
  named hinge axes, four continuous tendon routes, and separated print-layout evidence.

#### Changed

- Made concept renders deterministic in a shared Blender runtime by isolating unrelated
  scene objects, using scale-stable Workbench colors, and restoring prior visibility.
- Reduced generated mesh density and removed degenerate gimbal geometry so MCP print
  readiness completes without truncation; remaining support and tip-snap warnings stay
  visible as design-review items.
- Archived the accepted project-knowledge 5S task and opened the tendon-joint task as the
  sole current progress record.

### V01.00.000

#### Added

- Added project task/checkpoint SSOT, knowledge 5S budgets, and a repository-specific
  `blender-mcp-studio` Skill.
- Established the base36 `VERSION` release SSOT and exposed it through FastAPI metadata.
- Added a machine gate for broken local Markdown links, including archived documentation.

#### Changed

- Consolidated agent instructions in `AGENTS.md`, with `CLAUDE.md` importing the shared rules.
- Archived the completed 2026-07 campaign and replaced the legacy knowledge monolith with a
  current navigation map.
- Made production startup delegate to launchd and reserved Vite port 5173 for foreground dev.

#### Deprecated

#### Removed

- Removed stale local agent permission entries and generated cache/build artifacts from the
  working directory; secrets, dependencies, runtime databases, and launch configuration remain.

#### Fixed

- Made `install.sh all` wait for measured Blender addon readiness before starting the API,
  preventing a one-shot startup connection from remaining disconnected after a cold boot.

#### Security
