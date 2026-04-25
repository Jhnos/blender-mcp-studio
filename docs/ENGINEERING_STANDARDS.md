# Engineering Standards — Blender MCP Studio

This document captures cross-project engineering conventions that apply to
this repo. It mirrors the standards maintained in sibling projects
(whisper-api-server, MHH, LIG); when those evolve, this file should be
updated to stay aligned.

## §1 Scope

Blender MCP Studio is a single-host service that exposes Blender automation
via an MCP-style HTTP API (port 17823) plus a Vite dev-server frontend
(port 19147). Both run as per-user macOS LaunchAgents on the maintainer's
M4. The standards below are intentionally lightweight — sized for a
one-machine service — but are still binding.

## §11 launchd plist SSOT

Any macOS `launchd` plist that is installed on the maintainer's machine for
this project **MUST** have its source under version control in this repo.
The installed copy under `~/Library/LaunchAgents/` is *derived state*; the
file in the repo is authoritative.

Concretely:

1. **Location.** Templates live in `deploy/launchd/`. One `*.plist` template
   per service, alongside `install.sh` and `uninstall.sh`.
2. **No absolute paths in the template.** Use placeholders that `install.sh`
   substitutes at install time. Current placeholders:
   - `__PROJECT_ROOT__` — repo root (e.g. `/Users/<you>/Desktop/Blender_MCP_drawer`)
   - `__HOME__` — the user's `$HOME`
   - `__CONDA_PYTHON__` — conda env python for the api service
   - `__NODE_BIN__` — node binary for the web service
   Add new placeholders only when needed; keep the surface small.
3. **install.sh is idempotent.** It must:
   - Lint the rendered plist with `plutil -lint` before installing.
   - `launchctl bootout` any existing service first, swallowing benign
     errors ("service not loaded", EIO, ENOENT) via a `_safe_bootout`
     helper.
   - Atomically replace the file in `~/Library/LaunchAgents/`.
   - `launchctl bootstrap` + `enable` + `kickstart -k` the new instance.
4. **uninstall.sh archives, doesn't delete.** It must move the installed
   plist to `<name>.plist.deprecated.YYYYMMDD` (with a counter suffix if
   that path already exists), so one rollback step is always available.
5. **No drift.** A clean diff between
   `plutil -convert xml1 -o -` of the installed plist and the rendered
   template is the contract. CI / pre-commit checks may enforce this in
   the future; for now it is checked manually after every change.
6. **Don't bypass install.sh.** Editing
   `~/Library/LaunchAgents/<label>.plist` directly is forbidden — it
   silently re-introduces drift. Always edit the template, then re-run
   `install.sh`.

See `deploy/launchd/README.md` for usage.

## Other standards

Other engineering standards (logging, dependency pinning, secret handling,
etc.) are inherited from the cross-project conventions and will be
documented here as they become relevant to this service.
