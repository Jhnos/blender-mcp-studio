# Client-neutral MCP implementation status

> 回 [README](README.md) · 架構 SSOT [architecture.html](../architecture.html) ·
> 執行清單 [implementation plan](../superpowers/plans/2026-07-18-client-neutral-mcp-layer.md)

本檔是此 campaign 的唯一進度源。

| Phase | 狀態 | Evidence |
|---|---|---|
| Domain values + ports | Done | `9cc924d` |
| Shared application service | Done | `9caa260` |
| Eight-tool FastMCP adapter | Done | `5fb61b9` |
| Shared runtime + `/mcp` mount | Done | `0b48f0f` |
| `/blender/mcp` + stdio proxy | Done | `0f10edd` |
| Protocol/client-neutral gates | Done | `d281e58` |
| Real verifier + CI hook | Implemented; machine run pending | `61ef37c`; addon `9876` offline, so `--real` explicitly SKIP |
| Client/architecture/integration docs | Done | `MCP_CLIENTS.md` + rendered/guarded `architecture.html` |
| Hermetic CI | Passing | `scripts/ci.sh` |
| Deployment / real Blender acceptance | Not yet claimed | Requires merged/deployed code and listening addon |

## Handoff

1. Read this file, then [architecture.html](../architecture.html).
2. Use [MCP_CLIENTS.md](../MCP_CLIENTS.md) for client configuration.
3. Run `scripts/ci.sh` before any commit.
4. After deployment and Blender startup, run `scripts/ci.sh --real`; only a real
   PASS may move the final row to Done.
