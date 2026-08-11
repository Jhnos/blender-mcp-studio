# Project knowledge and agent-surface 5S

**Status:** ACTIVE

## Goal

Remove stale project memory and agent-document pollution, establish sustainable 5S and
checkpoint discipline, evaluate project-specific skills, and leave a machine-verified hand-off.

## Context to read

1. `docs/tasks/00_INDEX.md`
2. `AGENTS.md`
3. `docs/KNOWLEDGE.md`
4. `docs/LESSONS_LEARNED.md` only for a matching failure class

## Acceptance checks

- Knowledge 5S scanner reports clean and no completed tasks remain active.
- `AGENTS.md` and `CLAUDE.md` are current, concise, and non-duplicative.
- The project-specific skill validates and points only to existing commands/files.
- Generated caches are removed without deleting `.env`, runtime data, dependencies, or useful
  local launch configuration.
- `scripts/ci.sh` and the checkpoint machine check pass.
- `VERSION` and `CHANGELOG.md` exist; the sealing commit is pushed without force.
- Human acceptance is still required before moving this file to `archive/`.

## Hand-off

### Verified facts

- `knowledge-5s/scripts/doc_bloat_scan.sh .` reported `SCAN CLEAN`; no orphan memory links or
  completed active tasks remain.
- Fixed-cost budgets are below limits: `AGENTS.md` 71 lines, `CLAUDE.md` 7 lines,
  project `SKILL.md` 97 lines, and `docs/KNOWLEDGE.md` 35 lines before final hand-off edits.
- The project Skill validator reported `Skill is valid!` using the project conda Python.
- The Markdown link gate was proven RED with a missing sentinel, caught two real links broken
  by archival, then passed after correction.
- Deployment tests were proven RED before startup ordering and cold-start budget fixes; the
  test-weakening ratchet passed with all recorded tests unchanged.
- `bash deploy/launchd/install.sh all` waited for addon `127.0.0.1:9876` before API startup;
  local health returned `{"status":"ok","blender":"connected"}`.
- `scripts/ci.sh --real` passed static, Python/Web, REST, MCP protocol, print-readiness, and
  one-Undo batch-transform gates on 2026-08-11.
- `version.py current` and validation reported `V01.00.000` / `OK`.

### Open failures

- None. The first real gate run failed because API startup raced Blender readiness; a 30-second
  first fix also timed out against a measured ~40-second cold start. Both approaches and the
  final condition-wait budget are captured in `docs/LESSONS_LEARNED.md` and deployment tests.

### Next step

- In a fresh conversation, read this file and `git log --oneline -5`; confirm the checkpoint
  commit/push, then ask for human acceptance. On acceptance, move this task to
  `docs/tasks/archive/`, update `00_INDEX.md`, bump `VERSION`, update `CHANGELOG.md`, and commit.
