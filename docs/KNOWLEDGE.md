# Project knowledge map

This file is the navigation surface for durable project knowledge. It intentionally contains
no progress snapshots, copied architecture, model recommendations, or service restart recipes.

| Need | Read | Authority |
|---|---|---|
| Current or awaiting work | [`tasks/00_INDEX.md`](tasks/00_INDEX.md) | Task status SSOT |
| System boundaries and ADR summary | [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`architecture.html`](architecture.html) | Current architecture |
| MCP host setup and public tools | [`MCP_CLIENTS.md`](MCP_CLIENTS.md) | Client-neutral contract |
| Engineering and deployment rules | [`ENGINEERING_STANDARDS.md`](ENGINEERING_STANDARDS.md) and [`../deploy/launchd/README.md`](../deploy/launchd/README.md) | Operations contract |
| Recurring implementation workflow | [`../.agents/skills/blender-mcp-studio/SKILL.md`](../.agents/skills/blender-mcp-studio/SKILL.md) | Project-specific Skill |
| Recurring failure classes | [`LESSONS_LEARNED.md`](LESSONS_LEARNED.md) | Newest-first lesson SSOT |
| Completed 2026-07 implementation | [`archive/2026-07-client-neutral-mcp/README.md`](archive/2026-07-client-neutral-mcp/README.md) | Historical evidence |
| Superseded V2 notes | [`archive/legacy-knowledge-2026-08/KNOWLEDGE.md`](archive/legacy-knowledge-2026-08/KNOWLEDGE.md) | Historical only; do not treat as current |

## Placement rules

- Task execution state belongs in one task file; the index only links and labels it.
- A durable architectural decision belongs in architecture/ADR documentation.
- A failure class and its missing guard belong in `LESSONS_LEARNED.md`.
- Machine-specific ports and launchd ownership belong in `AGENTS.md` and deployment SSOT.
- Cross-project practices belong in global skills or global agent rules, not this repository.

No separate project memory directory is currently needed: all surviving facts already have a
single project SSOT above. Add one only when a new cross-session fact cannot be represented by
architecture, task, lesson, or operations documentation; use one topic per file plus an index.

## 5S budgets and cadence

- Agent instruction files: at most 200 lines.
- Project-authored skills: target about 150 lines; details move to references only when needed.
- Active task directory: only `TODO`, `ACTIVE`, `BLOCKED`, or `AWAITING-ACCEPTANCE` tasks.
- Files over 100 lines need a contents list when they are meant for selective reading.
- Run the knowledge 5S scanner at every checkpoint; run a full pass at campaign completion.
