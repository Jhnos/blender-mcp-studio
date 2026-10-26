# Blender MCP Studio — Claude Code entry

@AGENTS.md

Claude-specific local launch configuration may live in `.claude/launch.json`; local
permissions stay untracked. Do not duplicate project rules here—`AGENTS.md` is the shared
project instruction SSOT for Codex, Claude Code, and human maintainers.

The application service selects the current workstation from one declaration. Call
`run_design_pipeline` without `spec` to verify the current model; supply a spec only when
intentionally choosing a historical/custom model. Do not infer a revision from filenames.

The declaration is `models/lab-station/model-spec.json`; deliverables are Git-tracked under
`models/`. Client setup is in `docs/11-mcp-clients.md`, verification in `docs/30-verification.md`,
and task progress in `docs/tasks/00_INDEX.md`. Read `models/lab-station/README.md` for the
selection contract. These are navigation links, not separate copies of the selected version.
