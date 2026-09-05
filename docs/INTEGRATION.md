# Blender MCP Studio — Tailnet 整合

> 最後更新：2026-08-11。架構模型 SSOT 見 [architecture.html](architecture.html)，
> MCP client 設定見 [MCP_CLIENTS.md](MCP_CLIENTS.md)。

## 目錄

- [路徑與服務](#路徑與服務)
- [Prefix contract](#prefix-contract)
- [Lifecycle and ownership](#lifecycle-and-ownership)
- [Tailnet identity and Origin protection](#tailnet-identity-and-origin-protection)
- [LaunchAgent installation](#launchagent-installation)
- [MCP verification](#mcp-verification)
- [Troubleshooting](#troubleshooting)
- [Explicit non-goals](#explicit-non-goals)

## 路徑與服務

| 對外路徑 | 內部路徑 | Owner | 用途 |
|---|---|---|---|
| `/blender/` | Vite production preview `127.0.0.1:19504` | Web LaunchAgent | React UI |
| `/blender/api/*` | FastAPI `127.0.0.1:19505/api/*` | API LaunchAgent | REST |
| `/blender/ws/*` | FastAPI `127.0.0.1:19505/ws/*` | API LaunchAgent | WebSocket |
| `/blender/mcp` | FastAPI `127.0.0.1:19505/mcp` | API LaunchAgent | MCP Streamable HTTP |
| — | Blender addon `127.0.0.1:9876` | Blender LaunchAgent/process | Scene execution |

Canonical URLs:

```text
Web UI: https://bearmacminimac-mini.tail56c751.ts.net/blender/
MCP:    https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp
Health: https://bearmacminimac-mini.tail56c751.ts.net/blender/api/health
```

Ports and routes are SSOT in `~/MacHomeHub/config/services.yaml` and
`deploy/launchd/*.plist`. Port `19147` is retired.

## Prefix contract

MacHomeHub uses `strip_prefix: false`. Vite therefore receives the complete
`/blender/...` path and applies explicit proxy rewrites:

```text
/blender/mcp        → rewrite /mcp        → API :19505
/blender/api/scene  → rewrite /api/scene  → API :19505
/blender/ws/chat    → rewrite /ws/chat    → API :19505
```

The MCP proxy entry appears before `/blender/api` and preserves HTTP methods,
`Accept`, `MCP-Protocol-Version`, and `MCP-Session-Id`. It does not buffer the
stream or replace Host/Origin identity semantics.

## Lifecycle and ownership

The API process builds one `AppRuntime`. REST, WebSocket, and FastMCP receive
aliases to the same `SceneOperationsService` and `BlenderPort`. Startup opens one
addon connection; shutdown closes it once. The optional stdio process forwards to
the HTTP endpoint and never connects to `9876`.

This matters because the addon protocol and scene state are not separate per MCP
host. Codex, Claude, Cursor, VS Code, and the Web UI must converge on the same
serialized socket owner.

## Tailnet identity and Origin protection

Production sets `REQUIRE_TAILNET_IDENTITY=1`. MacHomeHub injects the trusted
`x-mes-identity` header after Tailnet authentication and removes spoofed client
values. `/api/health` is the sole HTTP exemption so the watchdog can probe the
process; `/mcp` is protected.

FastMCP strict Host/Origin protection allows only loopback and configured CORS
hostnames. Unsupported MCP protocol versions receive HTTP 400. This is a private
Tailnet service; it is not an OAuth-enabled public connector.

## LaunchAgent installation

Templates under `deploy/launchd/` are the SSOT. Installed files in
`~/Library/LaunchAgents/` are derived state.

```bash
cd /Users/bearmacmini/Desktop/Blender_MCP_drawer
bash deploy/launchd/install.sh all
```

Verify the processes and exact listeners rather than trusting plist text:

```bash
launchctl list | grep com.blender-mcp
lsof -nP -iTCP:19504 -sTCP:LISTEN
lsof -nP -iTCP:19505 -sTCP:LISTEN
lsof -nP -iTCP:9876  -sTCP:LISTEN
```

Health distinguishes API health from Blender availability:

```bash
curl -s https://bearmacminimac-mini.tail56c751.ts.net/blender/api/health
# {"status":"ok","blender":"connected"}
```

`status: "ok"` alone only proves the API process. The `blender` field must be
`connected` before scene tools can succeed.

## MCP verification

A browser GET or HTTP 200 is not a valid MCP check because Vite can serve an HTML
fallback. Hermetic CI drives real initialize, `tools/list`, content, Origin,
identity, and protocol framing with a fake Blender port:

```bash
scripts/ci.sh
```

The real gate requires Blender and mutates only nonce-prefixed verification
objects, which it removes in `finally`:

```bash
scripts/ci.sh --real
```

It invokes both REST and MCP through the Tailnet URL, then independently reads
Blender truth through socket `9876`. The print-readiness gate additionally seeds
watertight/open/zero-volume/intersecting/thin/overhang/oversized fixtures, compares
REST with MCP, and verifies teardown. When the addon is offline the tier prints
`SKIP`; do not report that as a real-machine pass.

## Troubleshooting

| Symptom | Check |
|---|---|
| MCP returns 401 | Confirm request goes through authenticated Tailnet/MHH, not anonymous Funnel |
| MCP returns 403 | Check request Host/Origin against `CORS_ORIGINS` and allowed hosts |
| MCP initialize fails | Inspect MCP response framing and `MCP-Protocol-Version`; do not use browser GET |
| Health says `disconnected` | Start Blender and addon on `9876`; inspect API warning log |
| Web works but MCP URL shows HTML | Confirm `/blender/mcp` Vite proxy exists before fallback routes |
| stdio host starts but has no tools | Run the proxy with absolute Python/script paths and check Tailnet reachability |

## Explicit non-goals

- No public Internet multi-user distribution.
- No legacy SSE endpoint.
- No client-name-specific behavior.
- No public arbitrary `execute_code` tool.
- No second Blender connection for stdio or a particular MCP host.
