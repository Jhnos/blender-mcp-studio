# Blender MCP Studio — project instructions

> Global rules: `~/.Codex/AGENTS.md`. This file contains only repository-specific constraints.

Blender MCP Studio exposes one Blender runtime to Web REST/WS, Streamable HTTP MCP,
and the stdio proxy. Keep every delivery path client-neutral and backed by the same
application services.

## Start and resume here

1. Read `docs/tasks/00_INDEX.md` and the linked `ACTIVE` or `AWAITING-ACCEPTANCE` task.
2. Read that task's hand-off section, then run `git log --oneline -5`.
3. Before debugging, search `docs/LESSONS_LEARNED.md` for the same failure class.
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
scripts/ci.sh --real   # T3 REST/MCP/readiness/batch checks; requires addon on 9876
bash deploy/launchd/install.sh all   # render, install, and restart production services
bash scripts/run_dev.sh              # foreground development: API 19505 + Web 5173
```

The local `scripts/ci.sh` is the only CI; there are no GitHub Actions. New behavior starts
with a discriminating failing test. A skipped real tier is not acceptance evidence.

## Runtime SSOT

- Ports: API `19505`, production Web `19504`, Blender addon socket `9876`.
- Tailscale: `https://bearmacminimac-mini.tail56c751.ts.net/blender` with prefix retained.
- Service registry: `~/MacHomeHub/config/services.yaml`.
- LaunchAgent source: `deploy/launchd/*.plist`; installed plists are derived state.
- Long-running Web uses a production build with `vite preview`; Vite HMR is manual dev only.

Verify loaded state, not just source files:

```bash
launchctl print gui/$(id -u)/com.blender-mcp.web
lsof -nP -iTCP:19504 -iTCP:19505 -iTCP:9876 -sTCP:LISTEN
curl -fsS http://127.0.0.1:19505/api/health
```

## Knowledge and checkpoint discipline

- Progress lives only in `docs/tasks/00_INDEX.md`; accepted tasks move to
  `docs/tasks/archive/`. Historical campaigns live under `docs/archive/`.
- `docs/KNOWLEDGE.md` is a navigation map, not a second architecture or progress ledger.
- Keep `AGENTS.md`/`CLAUDE.md` under 200 lines and project-authored `SKILL.md` near 150 lines;
  split or archive instead of compressing meaning.
- Generated caches, `web/dist`, runtime databases, `.env`, and local agent settings are not
  source. Never commit secrets or derived state.
- At a milestone: update the task hand-off, run the 5S scan and gates, bump `VERSION`, update
  `CHANGELOG.md`, commit, then run
  `bash "$HOME/.codex/skills/milestone-checkpoint/scripts/checkpoint_check.sh" .`.

## Compact instructions

When compacting, preserve the active task, modified files, exact checks and results,
unresolved failures with attempted approaches, and decisions with reasons.
