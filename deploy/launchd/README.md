# launchd / LaunchAgent SSOT — Blender MCP Studio

This directory is the **single source of truth** for the three macOS LaunchAgents
that run Blender MCP Studio in the background.

```
deploy/launchd/
├── com.blender-mcp.api.plist     # FastAPI service on port 19505 (template)
├── com.blender-mcp.web.plist     # Vite production preview on port 19504 (template)
├── com.blender-mcp.blender.plist # Blender + addon socket on port 9876 (template)
├── install.sh                    # render → ~/Library/LaunchAgents/ → bootstrap
├── uninstall.sh                  # bootout + archive (.deprecated.YYYYMMDD)
└── README.md                     # you are here
```

The installed copies under `~/Library/LaunchAgents/` are **derived state**.
If the templates and the installed plists ever diverge, the templates win —
re-run `install.sh` to reconcile. See `docs/ENGINEERING_STANDARDS.md §11`.

## Placeholders

| Placeholder         | Meaning                                                    | Default                                            |
| ------------------- | ---------------------------------------------------------- | -------------------------------------------------- |
| `__PROJECT_ROOT__`  | Repo root                                                  | computed from `install.sh` location                |
| `__HOME__`          | `$HOME`                                                    | `$HOME`                                            |
| `__CONDA_PYTHON__`  | Conda env python used by the api service                   | `$HOME/miniconda3/envs/blender-mcp/bin/python`     |
| `__NODE_BIN__`      | Node binary used by the web service                        | `/opt/homebrew/opt/node/bin/node` (Apple Silicon)  |

The installer derives `NPM_BIN` beside `NODE_BIN` and builds Web assets before
bootstrapping the preview service. Override `NPM_BIN` explicitly when Node and
npm are installed in different prefixes.

Override the defaults with env vars when invoking `install.sh`:

```bash
# Intel Mac homebrew prefix
NODE_BIN=/usr/local/opt/node/bin/node bash deploy/launchd/install.sh

# different conda env name
CONDA_PYTHON="$HOME/miniconda3/envs/myenv/bin/python" bash deploy/launchd/install.sh
```

## Install / re-install

```bash
cd ~/Desktop/Blender_MCP_drawer
bash deploy/launchd/install.sh        # both services
bash deploy/launchd/install.sh api    # api only
bash deploy/launchd/install.sh web    # web only
```

`install.sh` is idempotent. It:

1. Substitutes placeholders in the template.
2. Lints the rendered plist with `plutil -lint`.
3. `launchctl bootout`s any existing instance (noise from
   "service not loaded" / EIO is swallowed by `_safe_bootout`).
4. Atomically moves the rendered file into `~/Library/LaunchAgents/`.
5. Bounded-retries the known post-bootout `launchctl bootstrap` EIO race, then
   `enable` + `kickstart -k` to start it.

## Verify

```bash
# rendered file matches what's installed?
diff \
  <(plutil -convert xml1 -o - ~/Library/LaunchAgents/com.blender-mcp.api.plist) \
  <(plutil -convert xml1 -o - <(sed \
      -e "s|__PROJECT_ROOT__|$HOME/Desktop/Blender_MCP_drawer|g" \
      -e "s|__HOME__|$HOME|g" \
      -e "s|__CONDA_PYTHON__|$HOME/miniconda3/envs/blender-mcp/bin/python|g" \
      -e "s|__NODE_BIN__|/opt/homebrew/opt/node/bin/node|g" \
      deploy/launchd/com.blender-mcp.api.plist))

# services running?
launchctl print "gui/$(id -u)/com.blender-mcp.api" | head -40
launchctl print "gui/$(id -u)/com.blender-mcp.web" | head -40
lsof -iTCP:19505 -sTCP:LISTEN   # api
lsof -iTCP:19504 -sTCP:LISTEN   # web
```

A clean diff means the installed plist is faithful to the SSOT.

## MCP endpoint and stdio compatibility

The API owns one shared Blender connection and serves standards-compliant MCP
Streamable HTTP internally at `http://127.0.0.1:19505/mcp`. Vite forwards the
Tailnet sub-path without buffering or rewriting MCP headers:

```text
https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp
```

The external endpoint is protected by the same Tailnet identity gate as the
REST API. Hosts that only launch stdio MCP servers can use the transport bridge:

```bash
$HOME/miniconda3/envs/blender-mcp/bin/python \
  "$HOME/Desktop/Blender_MCP_drawer/scripts/run_mcp_stdio_proxy.py"
```

Override the upstream endpoint when needed:

```bash
BLENDER_MCP_URL=https://another-tailnet-host.example/blender/mcp \
  $HOME/miniconda3/envs/blender-mcp/bin/python \
  "$HOME/Desktop/Blender_MCP_drawer/scripts/run_mcp_stdio_proxy.py"
```

The bridge only converts stdio to Streamable HTTP. It never creates a second
Blender adapter or addon-socket connection; backend lifecycle remains owned by
the API LaunchAgent.

## Web deployment policy

The long-running Web LaunchAgent serves `vite preview` from a fresh production
build. This keeps `@vite/client` and its unsupported `vite-hmr` WebSocket out of
the Tailnet page while preserving application WebSockets such as
`/blender/ws/chat`. `vite.config.ts` shares one proxy map between dev and preview,
so REST, chat WebSocket, and MCP routes do not drift. Manual `npm run dev` keeps
normal hot-module replacement and the development-only `?mock` browser harness.

## Uninstall

```bash
bash deploy/launchd/uninstall.sh        # both
bash deploy/launchd/uninstall.sh api
bash deploy/launchd/uninstall.sh web
```

The installed plist is moved to
`~/Library/LaunchAgents/<label>.plist.deprecated.YYYYMMDD` (not deleted), so
one rollback step is always available.

## Why a template instead of committing the rendered file?

The plist must reference absolute paths (launchd doesn't expand `$HOME`
or `~`). Hard-coding `/Users/bearmacmini/...` into the repo makes the
file user-specific and prevents anyone else from cloning it cleanly.
The template + `install.sh` pattern keeps the repo portable while
preserving SSOT — same approach used by sibling projects (whisper-api-server,
MHH, LIG).

## Known non-portable values still in the templates

The api plist hard-codes a Tailscale hostname in `CORS_ORIGINS`:

```
https://bearmacminimac-mini.tail56c751.ts.net
```

This is deployment-specific config rather than a path. Edit the template
directly if your Tailscale hostname differs, then re-run `install.sh`.
