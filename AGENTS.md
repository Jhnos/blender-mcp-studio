# Blender MCP Studio — project instructions

> Global rules: `~/.Codex/AGENTS.md`. This file contains only repository-specific constraints.

Blender MCP Studio exposes one Blender runtime to Web REST/WS, Streamable HTTP MCP,
and the stdio proxy. Keep every delivery path client-neutral and backed by the same
application services.

## Start and resume here

1. Read `docs/tasks/00_INDEX.md`. Open the linked `ACTIVE` or `AWAITING-ACCEPTANCE` task if
   there is one. Follow the index for the next action and honour any explicit pause or
   wait. `WAITING-ON-USER` is outside active execution.
2. Read that task's hand-off section, then run `git log --oneline -5`.
3. Before debugging, search `docs/LESSONS_LEARNED.md` and any project memory feedback
   for the failure class. Apply an existing prevention check first.
4. Open `docs/README.md` and load only the topic files its "when to read" column
   names for this step. Load archived campaign material only when the task names it.
   Do not rescan the repository to reconstruct finished work.

## Architecture constraints

- Follow DDD + Hexagonal Architecture: domain/application must not import FastAPI,
  FastMCP, Zustand, or `bpy`; adapters translate external protocols.
- REST and every MCP host share one `AppRuntime` and one serialized Blender socket.
- Add capabilities through narrow ports and injected services. Do not expose arbitrary
  `execute_code` as a public MCP tool.
- Preserve public DTO compatibility unless an approved task explicitly changes it.
- Use the project skill `.agents/skills/blender-mcp-studio/SKILL.md` for recurring
  development, deployment, and real-Blender verification workflows.

## Commands and gates

```bash
scripts/ci.sh          # T1 static + T2 Python/Web tests; required before commit
scripts/ci.sh --real   # T3 core model/MCP/slicing; no live LLM; requires the Blender addon
scripts/ci.sh --chat   # Independent real conversation suite (Ollama + Blender)
scripts/ci.sh --all    # Core then conversation, sequentially
bash deploy/launchd/install.sh all   # render, install, and restart production services
bash scripts/run_dev.sh              # foreground development
```

The local `scripts/ci.sh` is the only CI; there are no GitHub Actions. New behavior starts
with a discriminating failing test. A skipped real tier is not acceptance evidence.

## Runtime SSOT

Use [runtime configuration](docs/10-runtime-ssot.md) for service addresses, ports and
the registry. Use [deployment](docs/12-deployment.md) to verify installed and loaded
state. LaunchAgent templates are under `deploy/launchd/`. Production Web uses the
built bundle, and Vite HMR is for foreground development.

## Knowledge and checkpoint discipline

- Progress lives only in `docs/tasks/00_INDEX.md`; accepted tasks move to
  `docs/tasks/archive/`. Historical campaigns live under `docs/archive/`.
- `docs/KNOWLEDGE.md` is a navigation map, not a second architecture or progress ledger.
- Keep `AGENTS.md`/`CLAUDE.md` under 200 lines and project-authored `SKILL.md` near 150 lines;
  split or archive instead of compressing meaning.
- Keep reusable failure classes in `docs/LESSONS_LEARNED.md`. Keep raw logs with their
  verification run, and use the task index for current progress.
- Keep generated caches, `web/dist`, runtime databases, `.env`, secrets and local agent
  settings out of Git. Follow the artifact cleanup rules in `docs/KNOWLEDGE.md`.
- At a milestone: update the task hand-off, run the 5S scan and gates, bump `VERSION`, update
  `CHANGELOG.md`, commit, then run
  `bash "$HOME/.codex/skills/milestone-checkpoint/scripts/checkpoint_check.sh" .`.

## Compact instructions

When compacting, preserve the active task, modified files, exact checks and results,
unresolved failures with attempted approaches, and decisions with reasons.
