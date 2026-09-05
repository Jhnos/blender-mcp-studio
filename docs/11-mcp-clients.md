# 11 — MCP clients：連線契約、工具目錄、host 設定

> 回導航 [[README]] · 相關 [[10-runtime-ssot]]、[[01-architecture]]、[[30-verification]]
>
> 埠與環境變數見 [[10-runtime-ssot]]；安全邊界的完整說明見 [[01-architecture]]；
> 驗證判準見 [[30-verification]]。本檔只講「client 怎麼接、接到什麼」。

## Contents

- [Transport](#transport)
- [Connection contract](#connection-contract)
- [Tool catalog](#tool-catalog)
- [Client configuration examples](#codex-configuration-example)

## Transport

- 協定：MCP Streamable HTTP，經 initialize 協商。
- Server 模式：stateless HTTP。
- Legacy SSE：**不對外開放**。
- 相容路徑：`scripts/run_mcp_stdio_proxy.py` 使用 FastMCP `create_proxy` 與
  `transport="stdio"`。
- 結果型別：typed result 用 structured text/JSON；PNG 用 MCP image content。

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
| `check_print_readiness` | Read | Inspect visible meshes for slicing risks and millimetre metrics without changing the scene |
| `create_object` | Write | Create a mesh cube, curve, light, or camera |
| `modify_object` | Destructive write | Change transforms or visibility |
| `delete_object` | Destructive write | Permanently remove one object |
| `apply_material` | Destructive write | Create/update and assign a Principled BSDF material |

`execute_code` is intentionally not public. The internal Blender adapter may use
it after translating a curated domain operation, but no MCP client can submit
arbitrary Python.

### 工具契約（註記與逾時）

| Tool | Read-only | Destructive | Idempotent | Max timeout |
|---|---:|---:|---:|---:|
| `blender_status` | yes | no | yes | 5 s |
| `get_scene_info` | yes | no | yes | 10 s |
| `get_object_info` | yes | no | yes | 10 s |
| `get_viewport_screenshot` | yes | no | yes | 30 s |
| `check_print_readiness` | yes | no | yes | 30 s |
| `create_object` | no | no | no | 30 s |
| `modify_object` | no | yes | yes | 30 s |
| `delete_object` | no | yes | no | 30 s |
| `apply_material` | no | yes | no | 30 s |

所有工具都設 `openWorldHint=false`。名稱有長度上限，向量恰好三個有限數字，
顏色是 `[0,1]` 的 RGBA，變異類 schema 拒絕額外屬性。
**Tool annotation 只是建議性的**——實際邊界由 identity middleware 與 registry 強制。

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
        "/Users/bearmacmini/Blender_MCP_drawer/scripts/run_mcp_stdio_proxy.py"
      ],
      "env": {
        "BLENDER_MCP_URL": "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"
      }
    }
  }
}
```

## 接上之後

**安全邊界**（identity、Host/Origin、protocol version、九項工具相等性、公網散布的
前提）完整說明見 [[01-architecture]] 的安全邊界一節。這裡只提醒 client 開發者三件事：

- `/mcp` **不是** identity exemption。缺少可信 Tailnet identity 的請求會收到 HTTP 401。
- `clientInfo.name` 不改變 authorization、capabilities、schema 或工具目錄。
- 這是私有 Tailnet 部署，不是公開 connector。

**驗證**：對 MCP URL 發 GET 得到 HTTP 200 **不算證據**——前端 fallback 也會回 200。
必須跑真正的 initialize 與 `tools/list`。完整判準與指令見 [[30-verification]]。
