# Changelog

本專案所有值得注意的變更記錄於此。格式依 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)；
版號依全域 version-management 規範（base36 固定寬度 VXX.XX.XXX；任何修改至少 bump 段3）。

## [Unreleased]

### Added

- Added project task/checkpoint SSOT, knowledge 5S budgets, and a repository-specific
  `blender-mcp-studio` Skill.
- Established the base36 `VERSION` release SSOT and exposed it through FastAPI metadata.
- Added a machine gate for broken local Markdown links, including archived documentation.

### Changed

- Consolidated agent instructions in `AGENTS.md`, with `CLAUDE.md` importing the shared rules.
- Archived the completed 2026-07 campaign and replaced the legacy knowledge monolith with a
  current navigation map.
- Made production startup delegate to launchd and reserved Vite port 5173 for foreground dev.

### Deprecated

### Removed

- Removed stale local agent permission entries and generated cache/build artifacts from the
  working directory; secrets, dependencies, runtime databases, and launch configuration remain.

### Fixed

- Made `install.sh all` wait for measured Blender addon readiness before starting the API,
  preventing a one-shot startup connection from remaining disconnected after a cold boot.

### Security
