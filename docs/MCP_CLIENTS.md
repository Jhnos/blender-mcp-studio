# MCP clients

Blender MCP Studio exposes standard MCP Streamable HTTP at:

`https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp`

The server does not detect or special-case the MCP host. Any client that supports
MCP Streamable HTTP can use the URL while authenticated to the Tailnet.

For a client that only launches stdio servers, run:

`~/miniconda3/envs/blender-mcp/bin/python scripts/run_mcp_stdio_proxy.py`

The stdio process proxies the HTTP MCP endpoint; it does not open another Blender
socket and can coexist with the Web UI and REST API.

## Connection contract

| Capability | Contract |
|---|---|
| Primary transport | MCP Streamable HTTP at the canonical URL above |
| Compatibility transport | Local stdio-to-HTTP proxy; set `BLENDER_MCP_URL` to override its upstream |
| Network boundary | Tailnet membership and the gateway-injected identity are required |
| Structured output | Read tools and mutations return typed MCP `structuredContent` where applicable |
| Screenshots | `get_viewport_screenshot` returns MCP image content with MIME type `image/png` |
| Destructive confirmation | Tool annotations identify destructive operations; the host decides whether to prompt |
| Backend ownership | REST, WebSocket, HTTP MCP, and stdio MCP share one API runtime and one addon socket |

The canonical URL is the server contract. Client configuration filenames and UI
labels can change between host releases; treat the examples below as host setup
examples, not server requirements.

## Tool catalog

| Tool | Kind | Purpose |
|---|---|---|
| `blender_status` | Read | Report whether the shared Blender connection is available |
| `get_scene_info` | Read | Return scene counts and object summaries |
| `get_object_info` | Read | Return transforms, visibility, and materials for one object |
| `get_viewport_screenshot` | Read | Return a bounded PNG viewport capture |
| `create_object` | Write | Create a mesh cube, curve, light, or camera |
| `modify_object` | Destructive write | Change transforms or visibility |
| `delete_object` | Destructive write | Permanently remove one object |
| `apply_material` | Destructive write | Create/update and assign a Principled BSDF material |

`execute_code` is intentionally not public. The internal Blender adapter may use
it after translating a curated domain operation, but no MCP client can submit
arbitrary Python.

## Codex configuration example

Add this to `~/.codex/config.toml` for a personal connection, or to the trusted
project's `.codex/config.toml` for a project-scoped connection:

```toml
[mcp_servers.blender_mcp_studio]
url = "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"
required = true
startup_timeout_sec = 20
tool_timeout_sec = 60
```

Restart or open a new Codex task, then inspect `/mcp`. Codex's current config
schema also supports stdio servers through `command`, `args`, and `env`.

## Claude Code configuration example

Claude Code supports remote HTTP MCP directly:

```bash
claude mcp add --transport http blender-mcp-studio \
  https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp
```

Use `claude mcp list` or `/mcp` to inspect the connection. This syntax follows
the [Claude Code MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp).

## VS Code configuration example

Create `.vscode/mcp.json` or use **MCP: Open User Configuration**:

```json
{
  "servers": {
    "blender-mcp-studio": {
      "type": "http",
      "url": "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"
    }
  }
}
```

VS Code documents `type: "http"` as the Streamable HTTP connection and asks the
user to trust a newly configured server. See the
[VS Code MCP server guide](https://code.visualstudio.com/docs/agent-customization/mcp-servers).

## Cursor configuration example

Cursor's MCP settings support Streamable HTTP. Add a custom MCP server in
**Settings → Tools & MCP** and use the canonical URL. If configuring JSON, follow
the schema shown by the installed Cursor version rather than copying another
host's top-level keys. See the [Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol).

## Generic stdio JSON example

Use this shape for a host that only accepts a local command. Paths are absolute
because GUI-launched clients do not reliably inherit the shell working directory:

```json
{
  "mcpServers": {
    "blender-mcp-studio": {
      "command": "/Users/bearmacmini/miniconda3/envs/blender-mcp/bin/python",
      "args": [
        "/Users/bearmacmini/Desktop/Blender_MCP_drawer/scripts/run_mcp_stdio_proxy.py"
      ],
      "env": {
        "BLENDER_MCP_URL": "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"
      }
    }
  }
}
```

## Security boundaries

- `/mcp` is not an identity exemption. Only `/api/health` remains open for the
  watchdog; MCP requests without the trusted Tailnet identity receive HTTP 401.
- Tool annotations are advisory UX hints, not authorization. The identity gate
  and curated server registry are the enforced controls.
- `clientInfo.name` may be observed for protocol telemetry, but never changes
  authorization, capabilities, schemas, or the tool catalog.
- Host and Origin validation runs before MCP request handling. Unsupported
  `MCP-Protocol-Version` values fail with HTTP 400.
- Legacy SSE is not exposed. Use Streamable HTTP or the stdio proxy.
- This is a private Tailnet deployment, not a public connector. Public Internet
  distribution needs a separate OAuth 2.1/CIMD design, per-user authorization,
  audit logging, rate limits, privacy review, and an explicit product decision.

## Verification

An HTTP 200 from the URL is not sufficient evidence: a frontend fallback can
also return 200. The hermetic tests initialize MCP, list the exact eight tools,
exercise content framing, and compare five client names. On the real machine:

```bash
scripts/ci.sh --real
```

The MCP verifier creates, moves, and deletes a nonce object through the public
MCP URL, while an independent raw addon-socket oracle verifies eight cube
vertices, coordinates, and final deletion. If Blender is offline, the tier prints
an explicit `SKIP`; that is not a real-machine pass.
