# 技術規格（Technical Specifications）

## 目錄

- [Runtime baseline](#runtime-baseline)
- [Service and route constants](#service-and-route-constants)
- [MCP transport](#mcp-transport)
- [MCP tool contract](#mcp-tool-contract)
- [Domain/application contracts](#domainapplication-contracts)
- [Shared runtime](#shared-runtime)
- [Security](#security)
- [Environment variables](#environment-variables)
- [Verification matrix](#verification-matrix)

## Runtime baseline

| 項目 | 版本／值 | 說明 |
|---|---|---|
| Python | 3.11 | Conda env `blender-mcp` |
| FastMCP | `>=3.4,<4` | MCP server、in-memory client、stdio proxy |
| Pydantic | `>=2.0` | Strict MCP input schemas |
| FastAPI | installed env | REST、WebSocket、ASGI mount |
| Node.js | 20+ | Vite/React frontend |
| Blender | 5.1 | validated addon execution engine |

Dependency declarations are `pyproject.toml` and `environment.yml`. The only CI
entry point is `scripts/ci.sh`.

## Service and route constants

| Service | Listener | Public route |
|---|---|---|
| Vite production preview | `127.0.0.1:19504` | `/blender/` |
| FastAPI | `127.0.0.1:19505` | `/blender/api/*`, `/blender/ws/*`, `/blender/mcp` |
| Blender addon | `127.0.0.1:9876` | none; API-owned raw TCP |

MacHomeHub is configured with `strip_prefix: false`; Vite rewrites `/blender/*`
to the API's internal `/api`, `/ws`, and `/mcp` paths.

## MCP transport

- Protocol: MCP Streamable HTTP, negotiated through initialize.
- Internal endpoint: `http://127.0.0.1:19505/mcp`.
- Canonical endpoint:
  `https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp`.
- Server mode: stateless HTTP.
- Legacy SSE: not exposed.
- Compatibility: `scripts/run_mcp_stdio_proxy.py` uses FastMCP `create_proxy` and
  `transport="stdio"`.
- Result types: structured text/JSON for typed results; MCP image content for PNG.

## MCP tool contract

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

All tools set `openWorldHint=false`. Names are bounded, vectors contain exactly
three finite numbers, colors are RGBA values in `[0,1]`, and mutation schemas
reject additional properties. Tool annotations are advisory; identity middleware
and the registry enforce the actual boundary.

## Domain/application contracts

`SceneQueryPort` defines:

- `status()`
- `get_scene_info()`
- `get_object_info(name)`
- `get_viewport_screenshot(max_size)`

`SceneCommandPort` defines:

- `create_object(spec)`
- `modify_object(spec)`
- `delete_object(name)`
- `apply_material(spec)`

`SceneOperationsService` implements both incoming ports and depends only on
`BlenderPort`. Domain records are frozen/slot dataclasses. External Blender JSON
is narrowed field-by-field without silent `str`, `int`, or `bool` coercion.

`PrintReadinessQueryPort.check(spec)` is implemented by the shared
`PrintReadinessService`; its independent outgoing `PrintReadinessPort.inspect`
is implemented by `BlenderPrintReadinessAdapter`. Reports use millimetres and
bounded 20,000-triangle / 5,000-intersection analysis.

`BatchTransformService` depends on the narrow `SceneBatchCommandPort`. It validates all
targets before mutation and delegates one Blender operator invocation so one Undo restores
the entire batch. REST is the delivery adapter; Web selection state is not Blender selection.

## Shared runtime

`api/runtime.py` is the composition root. `AppRuntime` contains one:

- `BlenderPort`
- `SceneOperationsService`
- `PrintReadinessService`
- `BatchTransformService`
- event bus and adapter factory
- security, prompt, persistence, vision, asset, and text-3D ports

FastAPI publishes compatibility aliases on `app.state`, but their object identity
matches the runtime fields. The FastAPI lifespan owns Blender connect/disconnect;
the combined FastMCP lifespan only owns MCP protocol resources.

## Security

| Control | Enforced behavior |
|---|---|
| Tailnet identity | All HTTP except `/api/health`; `/mcp` missing identity → 401 |
| Host/Origin guard | Strict allowlist derived from loopback and `CORS_ORIGINS` |
| Protocol version | Unsupported `MCP-Protocol-Version` → HTTP 400 |
| Tool surface | Exact nine-tool equality; `execute_code` absent |
| Error mapping | Recoverable domain errors become actionable `ToolError`/HTTP 422 |
| Error masking | Unexpected MCP internals do not expose tracebacks to clients |
| Socket serialization | One `asyncio.Lock` in `BlenderSocketClient` |

Client identity strings do not authorize or select tools. Public distribution is
outside this specification and requires a separate OAuth 2.1/CIMD design.

## Environment variables

```bash
BLENDER_HOST=localhost
BLENDER_PORT=9876
BLENDER_TRANSPORT=socket
API_HOST=127.0.0.1
API_PORT=19505
CORS_ORIGINS=https://bearmacminimac-mini.tail56c751.ts.net
REQUIRE_TAILNET_IDENTITY=1
BLENDER_MCP_URL=https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp
```

`BLENDER_MCP_URL` configures only the optional stdio proxy. It does not change
the API runtime's Blender adapter or socket endpoint.

## Verification matrix

| Tier | Real components | Replaced boundary | Claim |
|---|---|---|---|
| Unit | Domain, service, tool registry | Fake Blender port | validation, routing, error semantics |
| ASGI e2e | FastAPI, FastMCP framing, middleware | Fake Blender port | mount, identity, Origin, protocol, client neutrality |
| Headless UI | React/MDR/Vite tests | Mock HTTP backend | frontend behavior |
| Real machine | Public Tailnet MCP + API + Blender | none | nonce mutation, print fixtures, and one-Undo batch proof with independent socket oracle |

Run `scripts/ci.sh` for hermetic gates and `scripts/ci.sh --real` only when addon
`9876` is available. A real tier `SKIP` is not evidence of Blender mutation.
